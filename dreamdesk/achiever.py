"""The achiever: a goal-conditioned policy trained with PPO inside the dream, then used on the real app.

  goal elements + screen elements
     |  each element encoded from its features (role, name, text, states, depth), as in the world model
     v
  transformer over [value token, goal 1..3 (marked), element 1, element 2, ...]
     |-- every allowed action (verb, element, word): one score -> softmax = the policy
     |-- value token -> expected return (the critic)

Reward per step: +1 when every goal element is on the screen (episode ends), STEP_COST otherwise, and in
the penalised arm minus PENALTY x the ensemble's disagreement about that step (MOPO-style). Episodes last
at most dream.MAX_STEPS steps.

Training goals, half and half:
  recorded  goals from training-seed recordings (what the explorers actually reached)
  dreamed   goals made inside the dream by random play: whatever elements appeared after 1-5 steps.
            These include combinations no recording shows, which is the point of a dream.

  python3 -m dreamdesk.achiever train --out runs/ach/dream_seed0 --seed 0 [--penalty 1.0] [--apps clocks ...]
"""
import argparse
import json
import random
import statistics as stats
import time
from pathlib import Path

import torch
import torch.nn as nn
import torch.nn.functional as F

from .dream import Dream
from .goals import GOAL_SIZE, HORIZON, GoalSet
from .world_model import BUCKETS, MAX_ELEMENTS, STATE_LIST, VERBS, Neural, WorldModel, trigrams

CONFIG = {"d": 128, "layers": 2, "heads": 4, "ff": 256, "lr": 3e-4, "episodes": 64, "iterations": 300,
          "ppo_epochs": 4, "minibatch": 128, "clip": 0.2, "gamma": 0.95, "lam": 0.95, "entropy": 0.01,
          "value_coef": 0.5, "step_cost": 0.01, "penalty": 0.0}
APPS = ["calculator", "characters", "clocks", "disk-usage", "files", "font-viewer", "image-viewer", "logs",
        "resources", "text-editor"]


class Achiever(nn.Module):
    def __init__(self, n_roles=128, d=128, layers=2, heads=4, ff=256, **_):
        super().__init__()
        self.role = nn.Embedding(n_roles, d)
        self.states = nn.Linear(len(STATE_LIST) + 1, d)
        self.depth = nn.Embedding(32, d)
        self.name = nn.EmbeddingBag(BUCKETS, d, mode="mean")
        self.text = nn.EmbeddingBag(BUCKETS, d, mode="mean")
        self.norm = nn.LayerNorm(d)
        self.goal_marker = nn.Parameter(torch.randn(d) * 0.02)
        self.value_token = nn.Parameter(torch.randn(d) * 0.02)
        layer = nn.TransformerEncoderLayer(d, heads, ff, dropout=0.0, batch_first=True, norm_first=True)
        self.encoder = nn.TransformerEncoder(layer, layers)
        self.verb = nn.Embedding(len(VERBS), d)
        self.word = nn.EmbeddingBag(BUCKETS, d, mode="mean")
        self.score = nn.Sequential(nn.Linear(d, d), nn.GELU(), nn.Linear(d, 1))
        self.value = nn.Sequential(nn.Linear(d, d), nn.GELU(), nn.Linear(d, 1))

    embed = WorldModel.embed
    _bag = staticmethod(WorldModel._bag)

    def forward(self, f, items):
        """items: list of (goal ids, screen row ids, actions as (verb, row index, word)).
        Returns per-item log-probabilities over its actions (padding gets about -1e9) and values."""
        G = max(len(g) for g, _, _ in items)
        N = max(len(r) for _, r, _ in items)
        B = len(items)
        ids = torch.zeros(B, 1 + G + N, dtype=torch.long)
        mask = torch.zeros(B, 1 + G + N, dtype=torch.bool)
        is_goal = torch.zeros(B, 1 + G + N, 1)
        for b, (g, r, _) in enumerate(items):
            ids[b, 1:1 + len(g)] = torch.tensor(g)
            ids[b, 1 + G:1 + G + len(r)] = torch.tensor(r)
            mask[b, 0] = True
            mask[b, 1:1 + len(g)] = True
            mask[b, 1 + G:1 + G + len(r)] = True
            is_goal[b, 1:1 + len(g)] = 1
        x = self.embed(f, ids) + is_goal * self.goal_marker
        x[:, 0] = self.value_token
        h = self.encoder(x, src_key_padding_mask=~mask)
        value = self.value(h[:, 0]).squeeze(-1)
        A = max(len(a) for _, _, a in items)
        bi, ji, vi, words = [], [], [], []
        for b, (_, _, acts) in enumerate(items):
            for verb, j, word in acts:
                bi.append(b); ji.append(1 + G + j); vi.append(VERBS[verb]); words.append(trigrams(word) if word else [])
        real = torch.tensor([[1.0 if w else 0.0] for w in words])
        padded = [w if w else [0] for w in words]
        w_idx = torch.tensor([t for w in padded for t in w], dtype=torch.long)
        w_off = torch.tensor([0] + [len(w) for w in padded[:-1]]).cumsum(0)
        wv = self.word(w_idx, w_off) * real
        s = self.score(h[torch.tensor(bi), torch.tensor(ji)] + self.verb(torch.tensor(vi)) + wv).squeeze(-1)
        logits = torch.full((B, A), -1e9)  # not -inf: 0 * -inf would put NaNs in the entropy gradient
        pos = torch.tensor([k for _, _, acts in items for k in range(len(acts))])
        logits[torch.tensor(bi), pos] = s
        return F.log_softmax(logits, -1), value


def row_of(dream, screen):
    """Screen element ids in tree order, capped like the world model's input."""
    return sorted(screen, key=lambda e: dream.app.depth.get(e, 0))[:MAX_ELEMENTS]


def item_of(dream, goal_ids, screen):
    row = row_of(dream, screen)
    pos = {e: j for j, e in enumerate(row)}
    acts = [(v, pos[e], w) for v, e, w in dream.actions(screen) if e in pos]
    if not acts:  # nothing allowed: a no-op press on the first element keeps shapes simple
        acts = [("press", 0, "")]
    return (goal_ids, row, acts)


def to_dream_action(item, k):
    _, row, acts = item
    v, j, w = acts[k]
    return (v, row[j], w)


class GoalSource:
    """Training goals for one app: recorded (train seeds) and dreamed (random play in the dream)."""

    def __init__(self, dream, rng):
        self.dream, self.rng = dream, rng
        self.recorded = GoalSet(dream.app, "train").goals
        self.key_to_id = {}
        for e in dream.wm.prepared[dream.app.name].bank_ids:
            self.key_to_id.setdefault(dream.gkey[e], e)
        self.dreamed = []

    def ids(self, goal):
        return [self.key_to_id[k] for k in goal["keys"]]

    def refill(self, n=64):
        """Random play in the dream; each episode yields one goal from what appeared after k steps."""
        d = self.dream
        ks = [self.rng.randint(1, HORIZON) for _ in range(n)]
        screens = d.reset([{"keys": ()}] * n)
        start = [d.keys(s) for s in screens]
        new = [None] * n
        for t in range(HORIZON):
            chosen = [self.rng.choice(d.actions(s) or [("press", next(iter(s)), "")]) for s in d.screens]
            d.done = [False] * n
            nxt, _ = d.predict(d.screens, [(None, *c) for c in chosen])
            d.screens = nxt
            for b in range(n):
                if ks[b] == t + 1:
                    new[b] = sorted(k for k in d.keys(nxt[b]) - start[b] if k in self.key_to_id)
        for b in range(n):
            if new[b]:
                self.dreamed.append({"keys": tuple(sorted(self.rng.sample(new[b], min(GOAL_SIZE, len(new[b]))))), "kind": "dreamed"})
        self.dreamed = self.dreamed[-2000:]

    def sample(self, n):
        out = []
        for _ in range(n):
            if self.recorded and (not self.dreamed or self.rng.random() < 0.5):
                out.append(self.rng.choice(self.recorded))
            else:
                out.append(self.rng.choice(self.dreamed))
        return out


def rollout(model, dream, source, cfg):
    """One batch of dream episodes with the current policy. Returns steps for PPO and stats."""
    goals = source.sample(cfg["episodes"])
    gids = [source.ids(g) for g in goals]
    screens = dream.reset(goals)
    f = dream.wm.prepared[dream.app.name].f
    steps = [[] for _ in goals]  # per episode: (item, action index, logp, value, reward, done)
    wins = [False] * len(goals)
    while not all(dream.done):
        live = [b for b in range(len(goals)) if not dream.done[b]]
        items = [item_of(dream, gids[b], screens[b]) for b in live]
        with torch.no_grad():
            logp, value = model(f, items)
        k = torch.distributions.Categorical(logits=logp).sample()
        chosen = [("press", 0, "")] * len(goals)
        for i, b in enumerate(live):
            chosen[b] = to_dream_action(items[i], int(k[i]))
        screens, success, dis = dream.step(chosen)
        for i, b in enumerate(live):
            r = 1.0 if success[b] else -cfg["step_cost"]
            r -= cfg["penalty"] * dis[b]
            wins[b] = wins[b] or success[b]
            steps[b].append((items[i], int(k[i]), float(logp[i, k[i]]), float(value[i]), r, dream.done[b], success[b]))
    return steps, wins


def advantages(steps, cfg):
    out = []
    for ep in steps:
        adv, nxt = 0.0, 0.0
        rows = []
        for item, k, lp, v, r, done, success in reversed(ep):
            # a timeout isn't a true end, but the dream can't say what comes after: bootstrap with 0 at success,
            # with the value itself at a timeout (so running out of steps isn't punished as a terminal state)
            nv = 0.0 if success else (v if done else nxt)
            delta = r + cfg["gamma"] * nv - v
            adv = delta + cfg["gamma"] * cfg["lam"] * (0.0 if done else adv)
            rows.append((item, k, lp, adv, adv + v))
            nxt = v
        out += rows[::-1]
    return out


def update(model, opt, f, data, cfg, rng):
    stats_ = []
    for _ in range(cfg["ppo_epochs"]):
        rng.shuffle(data)
        for i in range(0, len(data), cfg["minibatch"]):
            mb = data[i:i + cfg["minibatch"]]
            logp, value = model(f, [m[0] for m in mb])
            k = torch.tensor([m[1] for m in mb])
            old = torch.tensor([m[2] for m in mb])
            adv = torch.tensor([m[3] for m in mb])
            ret = torch.tensor([m[4] for m in mb])
            adv = (adv - adv.mean()) / (adv.std() + 1e-8) if len(mb) > 1 else adv
            new = logp[torch.arange(len(mb)), k]
            ratio = torch.exp(new - old)
            pg = -torch.min(ratio * adv, ratio.clamp(1 - cfg["clip"], 1 + cfg["clip"]) * adv).mean()
            p = logp.exp()
            ent = -(p * logp).sum(-1).mean()
            vl = F.mse_loss(value, ret)
            loss = pg + cfg["value_coef"] * vl - cfg["entropy"] * ent
            opt.zero_grad()
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 0.5)
            opt.step()
            stats_.append((float(pg), float(vl), float(ent)))
    return [round(stats.mean(x), 4) for x in zip(*stats_)]


def train(args):
    torch.manual_seed(args.seed)
    torch.set_num_threads(args.threads)
    rng = random.Random(args.seed)
    cfg = dict(CONFIG, penalty=args.penalty, iterations=args.iterations)
    th = json.loads(Path("runs/wm/thresholds.json").read_text())
    wm = Neural(args.members, args.data, th["vanish"], th["appear"], args.threads)
    dreams = {a: Dream(wm, a, args.data, seed=args.seed) for a in args.apps}
    sources = {a: GoalSource(d, rng) for a, d in dreams.items()}
    for s in sources.values():
        s.refill()
    model = Achiever(n_roles=len(wm.roles) + 8, **cfg)
    opt = torch.optim.Adam(model.parameters(), lr=cfg["lr"])
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    log = open(out / "train_log.jsonl", "a")
    t0 = time.time()
    for it in range(cfg["iterations"]):
        app = args.apps[it % len(args.apps)]
        d, s = dreams[app], sources[app]
        if it % (5 * len(args.apps)) < len(args.apps):
            s.refill()
        steps, wins = rollout(model, d, s, cfg)
        data = advantages(steps, cfg)
        losses = update(model, opt, wm.prepared[app].f, data, cfg, rng)
        row = {"it": it, "app": app, "dream_success": round(sum(wins) / len(wins), 3), "steps": len(data),
               "losses": losses, "seconds": round(time.time() - t0)}
        log.write(json.dumps(row) + "\n"); log.flush()
        print(row, flush=True)
        if (it + 1) % 50 == 0 or it + 1 == cfg["iterations"]:
            torch.save({"model": model.state_dict(), "config": cfg, "roles": wm.roles, "apps": args.apps,
                        "it": it, "seed": args.seed}, out / "achiever.pt.tmp")
            (out / "achiever.pt.tmp").rename(out / "achiever.pt")


def dream_eval(args):
    """Success of a trained achiever in the dream on the same goals the real test uses (real_eval.pick_goals),
    each goal tried args.repeats times. Compare with the real result: the gap is how much the dream misleads."""
    from .real_eval import pick_goals
    torch.set_num_threads(args.threads)
    ck = torch.load(args.ckpt, weights_only=False)
    th = json.loads(Path("runs/wm/thresholds.json").read_text())
    wm = Neural(args.members, args.data, th["vanish"], th["appear"], args.threads)
    model = Achiever(n_roles=len(ck["roles"]) + 8, **ck["config"])
    model.load_state_dict(ck["model"])
    model.eval()
    torch.manual_seed(args.seed)
    out = {}
    for app in args.apps:
        d = Dream(wm, app, args.data, seed=args.seed)
        source = GoalSource(d, random.Random(args.seed))
        goals = pick_goals(d.app, args.split, args.goals)
        batch = [g for g in goals for _ in range(args.repeats)]
        source.sample = lambda n, b=batch: b
        cfg = dict(ck["config"], episodes=len(batch))
        _, wins = rollout(model, d, source, cfg)
        per_goal = [sum(wins[i * args.repeats:(i + 1) * args.repeats]) / args.repeats for i in range(len(goals))]
        out[app] = per_goal
        print(f"{app:13} dream success {stats.mean(per_goal):.3f} over {len(goals)} goals x {args.repeats}", flush=True)
    Path(args.out).write_text(json.dumps(out))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["train", "dream_eval"])
    ap.add_argument("--ckpt", default=None)
    ap.add_argument("--split", default="val")
    ap.add_argument("--goals", type=int, default=20)
    ap.add_argument("--repeats", type=int, default=5)
    ap.add_argument("--data", default="data/wm")
    ap.add_argument("--members", nargs="+", default=[f"runs/wm/member_seed{k}.pt" for k in range(5)])
    ap.add_argument("--apps", nargs="+", default=APPS)
    ap.add_argument("--out", required=True, help="train: folder; dream_eval: json file")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--penalty", type=float, default=0.0)
    ap.add_argument("--iterations", type=int, default=CONFIG["iterations"])
    ap.add_argument("--threads", type=int, default=8)
    args = ap.parse_args()
    train(args) if args.cmd == "train" else dream_eval(args)


if __name__ == "__main__":
    main()
