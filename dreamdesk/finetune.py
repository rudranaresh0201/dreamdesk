"""Stage 5 step 1b (experiments/finetune_prereg.md): train a dream on a held-out app's first B real steps,
starting from the 7-app prior (fine-tuned) or from random weights (scratch), then score it on val.

Each run saves runs/ft/{arm}_{app}_B{b}_seed{s}.pt and .json and is skipped if its .json exists, so the whole
grid can be stopped and restarted.

  python3 -m dreamdesk.finetune run                    # the 54-model grid
  python3 -m dreamdesk.finetune run --steps 20 --apps logs --budgets 100 --seeds 0 --out runs/ft_smoke
  python3 -m dreamdesk.finetune report                 # tables and the gates
"""
import argparse
import json
import math
import random
import statistics as stats
import time
from pathlib import Path

import torch

from .transfer_eval import BUDGETS, HELD_OUT
from .wm_data import load
from .wm_eval import App, evaluate, summary
from .world_model import CONFIG, Neural, Prepared, WorldModel, batch_loss, token_batches

STEPS, WARMUP = 500, 50
ARMS = ["finetune", "scratch"]


def train_one(arm, data_path, prior, seed, steps, threads):
    torch.manual_seed(seed)
    torch.set_num_threads(threads)
    rng = random.Random(seed)
    model = WorldModel(**CONFIG)
    roles = {}
    if arm == "finetune":
        ck = torch.load(prior, weights_only=False)
        model.load_state_dict(ck["model"])
        roles = dict(ck["roles"])
    p = Prepared(load(data_path), roles)
    opt = torch.optim.AdamW(model.parameters(), lr=CONFIG["lr"], weight_decay=0.01)
    model.train()
    step, losses = 0, []
    while step < steps:
        ts = p.app.transitions["train"][:]
        rng.shuffle(ts)
        batches = token_batches(p, ts)
        rng.shuffle(batches)
        for b in batches:
            if step >= steps:
                break
            lr = CONFIG["lr"] * min(1.0, (step + 1) / WARMUP) * 0.5 * (1 + math.cos(math.pi * step / steps))
            for g in opt.param_groups:
                g["lr"] = lr
            loss = batch_loss(model, p, b)
            opt.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            losses.append(loss.item())
            step += 1
    return model, roles, losses


def run(args):
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    th = json.load(open("runs/wm/thresholds.json"))
    jobs = [(app, b, arm, s) for b in args.budgets for app in args.apps for arm in ARMS for s in args.seeds]
    for k, (app, b, arm, s) in enumerate(jobs):
        name = f"{arm}_{app}_B{b}_seed{s}"
        if (out / f"{name}.json").exists():
            continue
        t0 = time.time()
        folder = Path(args.budget_dir) / f"B{b}"
        model, roles, losses = train_one(arm, folder / f"{app}.pkl", args.prior, s, args.steps, args.threads)
        torch.save({"model": model.state_dict(), "config": CONFIG, "roles": roles, "seed": s, "arm": arm}, out / f"{name}.pt")
        t1 = time.time()
        m = Neural([out / f"{name}.pt"], folder, th["vanish"], th["appear"], args.threads)
        a = App(load(folder / f"{app}.pkl"))
        m.fit(a)
        one, many = evaluate(m, a, args.split)
        r = {"app": app, "budget": b, "arm": arm, "seed": s, "h1": summary(one), "h5": summary(many),
             "loss_first": stats.mean(losses[:20]), "loss_last": stats.mean(losses[-20:]),
             "train_s": round(t1 - t0), "eval_s": round(time.time() - t1)}
        (out / f"{name}.json").write_text(json.dumps(r))
        print(f"[{k + 1}/{len(jobs)}] {time.strftime('%H:%M')} {name:28} loss {r['loss_first']:.3f}->{r['loss_last']:.3f} "
              f"h1 unv {r['h1']['unvisited']:.3f}  h5 unv {r['h5']['unvisited']:.3f}  "
              f"({r['train_s']}s train, {r['eval_s']}s eval)", flush=True)


def report(args):
    res = {}
    for f in Path(args.out).glob("*.json"):
        r = json.loads(f.read_text())
        res.setdefault((r["app"], r["budget"], r["arm"]), []).append(r)
    base = json.loads(Path(args.step1).read_text())
    f = lambda x: f"{x:.3f}" if x is not None else "-"
    lines = ["| App | B | Copy | Memo | Zero-shot | Scratch (seeds) | Fine-tuned (seeds) |", "|---|---|---|---|---|---|---|"]
    gate1 = gate2 = 0
    for app in HELD_OUT:
        for b in BUDGETS:
            cells = [f(base[f"{app}|{b}|{n}"]["h5"]["unvisited"]) for n in ("copy", "memo", "transfer")]
            per = {}
            for arm in ARMS:
                v = [r["h5"]["unvisited"] for r in sorted(res.get((app, b, arm), []), key=lambda r: r["seed"])]
                per[arm] = v
                cells.append(f"**{f(stats.mean(v))}** ({', '.join(f(x) for x in v)})" if v else "-")
            lines.append(f"| {app} | {b} | " + " | ".join(cells) + " |")
            if b == 300 and per["finetune"] and per["scratch"]:
                ft, sc = stats.mean(per["finetune"]), stats.mean(per["scratch"])
                memo, copy = (base[f"{app}|300|{n}"]["h5"]["unvisited"] for n in ("memo", "copy"))
                g1 = ft > max(memo, copy)
                g2 = ft > sc and min(per["finetune"]) > max(per["scratch"])
                gate1 += g1
                gate2 += g2
                print(f"gate {app}: fine-tuned {ft:.3f} vs memo {memo:.3f} -> G1 {'yes' if g1 else 'no'}; "
                      f"vs scratch {sc:.3f} (worst ft {min(per['finetune']):.3f}, best scratch {max(per['scratch']):.3f}) -> G2 {'yes' if g2 else 'no'}")
    print(f"G1 (beats Memo): {gate1} of 3 -> {'PASS' if gate1 >= 2 else 'FAIL'}")
    print(f"G2 (prior helps): {gate2} of 3 -> {'PASS' if gate2 >= 2 else 'FAIL'}")
    print("\nHorizon 5, unvisited windows, val:\n")
    print("\n".join(lines))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--apps", nargs="+", default=HELD_OUT)
    r.add_argument("--budgets", nargs="+", type=int, default=BUDGETS)
    r.add_argument("--seeds", nargs="+", type=int, default=[0, 1, 2])
    r.add_argument("--steps", type=int, default=STEPS)
    r.add_argument("--prior", default="runs/wm7/member_seed0.pt")
    r.add_argument("--budget-dir", default="data/budget")
    r.add_argument("--split", default="val")
    r.add_argument("--threads", type=int, default=6)
    r.add_argument("--out", default="runs/ft")
    p = sub.add_parser("report")
    p.add_argument("--out", default="runs/ft")
    p.add_argument("--step1", default="runs/wm7/transfer_val.json")
    args = ap.parse_args()
    run(args) if args.cmd == "run" else report(args)


if __name__ == "__main__":
    main()
