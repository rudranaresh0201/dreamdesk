"""Stage 5 step 1: score a world model on held-out apps it never trained on, at each exploration budget
(experiments/transfer_prereg.md). The budget sets the app's element bank and is what Copy and Memo fit on.
The Stage 3 model (trained on the app's full training data) is shown as an in-app reference, not gated.

  python3 -m dreamdesk.transfer_eval --member runs/wm7/member_seed0.pt --out runs/wm7/transfer_val.json
"""
import argparse
import json
from pathlib import Path

from .wm_data import load
from .wm_eval import App, Copy, Memo, evaluate, summary
from .world_model import Neural

HELD_OUT = ["disk-usage", "files", "logs"]
BUDGETS = [100, 300, 1000]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--member", required=True)
    ap.add_argument("--reference", default="runs/wm/member_seed0.pt", help="Stage 3 member, in-app reference")
    ap.add_argument("--budget-dir", default="data/budget")
    ap.add_argument("--split", default="val")
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    th = json.load(open("runs/wm/thresholds.json"))
    res = {}
    print(f"{'app':11} {'B':>5} {'model':9} | h1 all   h1 unv  | h5 all   h5 unv (n)", flush=True)
    for app_name in HELD_OUT:
        for b in BUDGETS:
            folder = Path(args.budget_dir) / f"B{b}"
            app = App(load(folder / f"{app_name}.pkl"))
            models = {"copy": Copy(), "memo": Memo(),
                      "transfer": Neural([args.member], folder, th["vanish"], th["appear"], args.threads)}
            if b == BUDGETS[0]:  # reference: Stage 3 member, trained on this app's full data, its full bank
                models["in-app"] = Neural([args.reference], "data/wm", th["vanish"], th["appear"], args.threads)
            for name, m in models.items():
                full = App(load(Path("data/wm") / f"{app_name}.pkl")) if name == "in-app" else app
                m.fit(full)
                one, many = evaluate(m, app if name != "in-app" else full, args.split)
                a, h = summary(one), summary(many)
                res[f"{app_name}|{b}|{name}"] = {"h1": a, "h5": h}
                f = lambda x: f"{x:.3f}" if x is not None else "  -  "
                print(f"{app_name:11} {b:5} {name:9} | {f(a['all'])}  {f(a['unvisited'])}  | {f(h['all'])}  {f(h['unvisited'])} ({h['n_unvisited']})", flush=True)
            Path(args.out).write_text(json.dumps(res, indent=1))
    gate = 0
    for app_name in HELD_OUT:
        r = {n: res[f"{app_name}|300|{n}"]["h5"]["unvisited"] for n in ("copy", "memo", "transfer")}
        ok = r["transfer"] is not None and r["transfer"] > max(r["copy"] or 0, r["memo"] or 0)
        gate += ok
        print(f"gate {app_name}: transfer {r['transfer']:.3f} vs copy {r['copy']:.3f} memo {r['memo']:.3f} -> {'beats' if ok else 'does not beat'}")
    print(f"GATE: {'GO' if gate >= 2 else 'STOP'} ({gate} of 3 held-out apps)")


if __name__ == "__main__":
    main()
