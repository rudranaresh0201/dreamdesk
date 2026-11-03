"""The neural world model: given a screen and an action, which elements vanish and which appear.

  screen + action
     |  every element encoded from its features: role, name, text, states, depth
     |  (features, not ids, so it can handle elements and apps it hasn't seen)
     v
  transformer over [action token, element 1, element 2, ...]   (a set: no positions)
     |-- per element: does it vanish?
     |-- action token -> 4 queries; score every element in the app's bank: does it appear?
     v
  next screen = screen - vanished + appeared

The bank is every element seen in this app's training data. Five members with different seeds and
bootstrap samples form the ensemble; their disagreement is the uncertainty used later in the dream.

Train:     python3 -m dreamdesk.world_model train --data data/wm --out runs/wm --seed 0
"""
import argparse
import json
import math
import random
import time
import zlib
from pathlib import Path

import torch
import torch.nn as nn
import torch.nn.functional as F

from .atspi_backend import STATES
from .wm_data import load
from .wm_eval import App

STATE_LIST = sorted(STATES)
BUCKETS = 1 << 14
MAX_ELEMENTS = 1024  # longer screens keep their extra elements unchanged
VERBS = {"press": 0, "focus": 1, "type": 2}
APPEAR_HEADS = 4
CONFIG = {"d": 128, "layers": 2, "heads": 4, "ff": 256, "lr": 3e-4, "batch": 16, "batch_elements": 4096, "epochs": 8, "pos_weight": 10.0}


def trigrams(s):
    s = f"^{s.lower()[:60]}$"
    grams = {s[i:i + 3] for i in range(max(1, len(s) - 2))}
    return [zlib.crc32(g.encode()) % BUCKETS for g in grams]


class Features:
    """Feature tensors for every element id of one app, built once."""

    def __init__(self, app, roles):
        n = len(app.tokens)
        self.role = torch.zeros(n, dtype=torch.long)
        self.states = torch.zeros(n, len(STATE_LIST) + 1)
        self.depth = torch.zeros(n, dtype=torch.long)
        name_idx, name_off, text_idx, text_off = [], [], [], []
        for i, (role, name, text, pressable, states) in enumerate(app.tokens):
            self.role[i] = roles.setdefault(role, len(roles))
            for s in states:
                if s in STATE_LIST:
                    self.states[i, STATE_LIST.index(s)] = 1
            self.states[i, -1] = float(pressable)
            self.depth[i] = min(app.depth.get(i, 0), 31)
            name_off.append(len(name_idx)); name_idx += trigrams(name)
            text_off.append(len(text_idx)); text_idx += trigrams(text)
        self.name = (torch.tensor(name_idx), torch.tensor(name_off))
        self.text = (torch.tensor(text_idx), torch.tensor(text_off))


class WorldModel(nn.Module):
    def __init__(self, n_roles=128, d=128, layers=2, heads=4, ff=256, **_):
        super().__init__()
        self.role = nn.Embedding(n_roles, d)
        self.states = nn.Linear(len(STATE_LIST) + 1, d)
        self.depth = nn.Embedding(32, d)
        self.name = nn.EmbeddingBag(BUCKETS, d, mode="mean")
        self.text = nn.EmbeddingBag(BUCKETS, d, mode="mean")
        self.norm = nn.LayerNorm(d)
        self.verb = nn.Embedding(len(VERBS), d)
        self.word = nn.EmbeddingBag(BUCKETS, d, mode="mean")
        self.is_target = nn.Parameter(torch.zeros(d))
        self.action_marker = nn.Parameter(torch.randn(d) * 0.02)
        layer = nn.TransformerEncoderLayer(d, heads, ff, dropout=0.1, batch_first=True, norm_first=True)
        self.encoder = nn.TransformerEncoder(layer, layers)
        self.vanish = nn.Sequential(nn.Linear(d, d), nn.GELU(), nn.Linear(d, 1))
        self.query = nn.Sequential(nn.Linear(2 * d, d), nn.GELU(), nn.Linear(d, APPEAR_HEADS * d))
        self.key = nn.Sequential(nn.Linear(d, d), nn.GELU(), nn.Linear(d, APPEAR_HEADS * d))
        self.key_bias = nn.Linear(d, 1)

    def embed(self, f, ids):
        """Encode element ids from their features."""
        ni, no = f.name
        ti, to = f.text
        name = self._bag(self.name, ni, no, ids)
        text = self._bag(self.text, ti, to, ids)
        return self.norm(self.role(f.role[ids]) + self.states(f.states[ids]) + self.depth(f.depth[ids]) + name + text)

    @staticmethod
    def _bag(bag, idx, off, ids):
        ends = torch.cat([off[1:], torch.tensor([len(idx)])])
        flat_ids = ids.reshape(-1)
        starts, stops = off[flat_ids], ends[flat_ids]
        lengths = stops - starts
        gather = torch.repeat_interleave(starts, lengths) + (torch.arange(int(lengths.sum())) -
                 torch.repeat_interleave(torch.cumsum(lengths, 0) - lengths, lengths))
        offsets = torch.cumsum(lengths, 0) - lengths
        out = bag(idx[gather], offsets)
        return out.reshape(*ids.shape, -1)

    def forward(self, f, screens, mask, targets, verbs, words, bank):
        """screens: B x N element ids (padded), mask: B x N true where real, targets: B (index into N),
        verbs: B, words: list of trigram lists, bank: K element ids. Returns vanish logits B x N, appear logits B x K."""
        x = self.embed(f, screens)
        x = x + (torch.arange(x.shape[1])[None, :] == targets[:, None]).unsqueeze(-1) * self.is_target
        real = torch.tensor([[1.0 if w else 0.0] for w in words])
        padded = [w if w else [0] for w in words]  # EmbeddingBag needs one index per bag; zeroed below
        word_idx = torch.tensor([g for w in padded for g in w], dtype=torch.long)
        word_off = torch.tensor([0] + [len(w) for w in padded[:-1]]).cumsum(0)
        w = self.word(word_idx, word_off) * real
        target_vec = x[torch.arange(len(targets)), targets]
        a = self.action_marker + self.verb(verbs) + w + target_vec
        h = self.encoder(torch.cat([a[:, None], x], 1), src_key_padding_mask=torch.cat([torch.zeros_like(mask[:, :1]), ~mask], 1))
        vanish = self.vanish(h[:, 1:]).squeeze(-1)
        q = self.query(torch.cat([h[:, 0], (h[:, 1:] * mask[..., None]).sum(1) / mask.sum(1, keepdim=True)], -1))
        e = self.embed(f, bank)
        d = e.shape[-1]
        qh = q.view(len(q), APPEAR_HEADS, d)
        kh = self.key(e).view(len(bank), APPEAR_HEADS, d)
        # each head is one "kind of change" (a menu opens, a page switches, ...); an element appears if any head says so
        scores = torch.einsum("bhd,khd->bhk", qh, kh) / math.sqrt(d)
        appear = scores.max(1).values + self.key_bias(e).squeeze(-1)[None]
        return vanish, appear


class Prepared:
    """One app ready for the model: features, bank, and the train split as screen-id lists."""

    def __init__(self, data, roles):
        self.app = App(data)
        self.ordered = [[i for i, _ in s] for s in data["screens"]]
        self.f = Features(self.app, roles)
        bank = set()
        for t in self.app.transitions["train"]:
            bank |= self.app.screens[t[0]] | self.app.screens[t[4]]
        self.bank_ids = sorted(bank)
        self.bank = torch.tensor(self.bank_ids)
        self.bank_pos = {e: k for k, e in enumerate(self.bank_ids)}


def batch_inputs(p, screens, ts):
    """screens: list of element-id lists; ts: transitions (for the action). Returns model inputs."""
    rows, targets = [], []
    for s, t in zip(screens, ts):
        s = list(s)
        if t[2] in s:
            s.remove(t[2])
        s = [t[2]] + s[:MAX_ELEMENTS - 1]  # the target always first, so it's never cut off
        rows.append(s)
        targets.append(0)
    n = max(len(r) for r in rows)
    ids = torch.zeros(len(rows), n, dtype=torch.long)
    mask = torch.zeros(len(rows), n, dtype=torch.bool)
    for b, r in enumerate(rows):
        ids[b, :len(r)] = torch.tensor(r)
        mask[b, :len(r)] = True
    verbs = torch.tensor([VERBS[t[1]] for t in ts])
    words = [trigrams(t[3]) if t[3] else [] for t in ts]
    return rows, ids, mask, torch.tensor(targets), verbs, words


def run_model(model, p, screens, ts):
    rows, ids, mask, targets, verbs, words = batch_inputs(p, screens, ts)
    vanish, appear = model(p.f, ids, mask, targets, verbs, words, p.bank)
    return rows, mask, vanish, appear


def token_batches(p, ts):
    """Group transitions of similar length, at most CONFIG["batch"] of them and about
    CONFIG["batch_elements"] elements per batch, so one long screen doesn't blow up attention memory."""
    out = []
    for i in range(0, len(ts), 256):  # sort only within chunks, so batches still mix
        chunk = sorted(ts[i:i + 256], key=lambda t: len(p.ordered[t[0]]))
        batch, longest = [], 0
        for t in chunk:
            n = min(len(p.ordered[t[0]]), MAX_ELEMENTS)
            if batch and (len(batch) == CONFIG["batch"] or max(longest, n) * (len(batch) + 1) > CONFIG["batch_elements"]):
                out.append(batch)
                batch, longest = [], 0
            batch.append(t)
            longest = max(longest, n)
        if batch:
            out.append(batch)
    return out


def train(args):
    torch.manual_seed(args.seed)
    random.seed(args.seed)
    torch.set_num_threads(args.threads)
    roles = {}
    apps = [Prepared(load(p), roles) for p in sorted(Path(args.data).glob("*.pkl"))]
    model = WorldModel(**CONFIG)
    opt = torch.optim.AdamW(model.parameters(), lr=CONFIG["lr"], weight_decay=0.01)
    rng = random.Random(args.seed)
    # bootstrap sample per member, so members disagree where data is thin
    items = [(k, rng.choice(p.app.transitions["train"])) for k, p in enumerate(apps) for _ in p.app.transitions["train"]]
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    log = open(out / f"train_seed{args.seed}.log", "a")
    total = None
    step = 0
    for epoch in range(args.epochs):
        rng.shuffle(items)
        by_app = {}
        for k, t in items:
            by_app.setdefault(k, []).append(t)
        batches = []
        for k, ts in by_app.items():
            batches += [(k, b) for b in token_batches(apps[k], ts)]
        rng.shuffle(batches)
        if total is None:
            total = args.epochs * len(batches)
        if args.limit:
            batches = batches[:args.limit]
        model.train()
        t0, losses = time.time(), []
        for k, ts in batches:
            p = apps[k]
            lr = CONFIG["lr"] * min(1.0, (step + 1) / 200) * 0.5 * (1 + math.cos(math.pi * min(step, total) / total))
            for g in opt.param_groups:
                g["lr"] = lr
            rows, mask, vanish, appear = run_model(model, p, [p.ordered[t[0]] for t in ts], ts)
            y_vanish = torch.zeros_like(vanish)
            y_appear = torch.zeros_like(appear)
            appear_mask = torch.ones_like(appear, dtype=torch.bool)
            for b, (r, t) in enumerate(zip(rows, ts)):
                after = p.app.screens[t[4]]
                for j, e in enumerate(r):
                    y_vanish[b, j] = float(e not in after)
                    if e in p.bank_pos:
                        appear_mask[b, p.bank_pos[e]] = False  # already on screen: can't appear
                for e in after - set(r):
                    if e in p.bank_pos:
                        y_appear[b, p.bank_pos[e]] = 1.0
            lv = F.binary_cross_entropy_with_logits(vanish[mask], y_vanish[mask], pos_weight=torch.tensor(CONFIG["pos_weight"]))
            la = F.binary_cross_entropy_with_logits(appear[appear_mask], y_appear[appear_mask], pos_weight=torch.tensor(CONFIG["pos_weight"]))
            loss = lv + la
            opt.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            losses.append(loss.item())
            step += 1
        msg = {"epoch": epoch, "loss": round(sum(losses) / len(losses), 4), "seconds": round(time.time() - t0), "batches": len(batches)}
        print(json.dumps(msg), flush=True)
        log.write(json.dumps(msg) + "\n")
        log.flush()
        torch.save({"model": model.state_dict(), "config": CONFIG, "roles": roles, "epoch": epoch, "seed": args.seed},
                   out / f"member_seed{args.seed}.pt")


class Neural:
    """Wraps trained members for wm_eval: averages their probabilities, then thresholds."""
    name = "world-model"

    def __init__(self, paths, data_dir, vanish_threshold=0.5, appear_threshold=0.5, threads=8):
        torch.set_num_threads(threads)
        self.members = []
        roles = None
        for path in paths:
            ck = torch.load(path, weights_only=False)
            m = WorldModel(**ck["config"])
            m.load_state_dict(ck["model"])
            m.eval()
            self.members.append(m)
            roles = ck["roles"]
        self.roles = dict(roles)
        self.data_dir = Path(data_dir)
        self.vt, self.at = vanish_threshold, appear_threshold
        self.prepared = {}

    def fit(self, app):
        if app.name not in self.prepared:
            self.prepared[app.name] = Prepared(load(self.data_dir / f"{app.name}.pkl"), self.roles)

    @torch.no_grad()
    def probabilities(self, app, screens, ts):
        p = self.prepared[app.name]
        ordered = [sorted(s, key=lambda e: p.app.depth.get(e, 0)) for s in screens]
        outs = []
        for m in self.members:
            rows, mask, vanish, appear = run_model(m, p, ordered, ts)
            outs.append((torch.sigmoid(vanish), torch.sigmoid(appear)))
        return p, rows, mask, outs

    def predict_batch(self, app, screens, ts):
        p, rows, mask, outs = self.probabilities(app, screens, ts)
        v = torch.stack([o[0] for o in outs]).mean(0)
        a = torch.stack([o[1] for o in outs]).mean(0)
        result = []
        for b, (r, s) in enumerate(zip(rows, screens)):
            gone = {e for j, e in enumerate(r) if v[b, j] > self.vt}
            present = set(s)
            came = {p.bank_ids[k] for k in torch.nonzero(a[b] > self.at).flatten().tolist() if p.bank_ids[k] not in present}
            result.append(frozenset((present - gone) | came))
        return result

    def predict(self, app, screen, t):
        return self.predict_batch(app, [screen], [t])[0]


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    tr = sub.add_parser("train")
    tr.add_argument("--data", default="data/wm")
    tr.add_argument("--out", default="runs/wm")
    tr.add_argument("--seed", type=int, required=True)
    tr.add_argument("--epochs", type=int, default=CONFIG["epochs"])
    tr.add_argument("--threads", type=int, default=8)
    tr.add_argument("--limit", type=int, default=0, help="batches per epoch, for a speed check")
    ev = sub.add_parser("eval")
    ev.add_argument("--data", default="data/wm")
    ev.add_argument("--members", nargs="+", required=True)
    ev.add_argument("--split", default="val", choices=["train", "val", "test"])
    ev.add_argument("--vanish", type=float, default=0.5)
    ev.add_argument("--appear", type=float, default=0.5)
    ev.add_argument("--threads", type=int, default=8)
    args = ap.parse_args()
    if args.cmd == "train":
        train(args)
    else:
        evaluate_members(args)


def evaluate_members(args):
    from .wm_eval import evaluate, summary
    model = Neural(args.members, args.data, args.vanish, args.appear, args.threads)
    fmt = lambda x: f"{x:.3f}" if x is not None else "  -  "
    print(f"split {args.split}, thresholds vanish {args.vanish} appear {args.appear}, {len(model.members)} members")
    print(f"{'app':13} | h=1 all  unvisited (n) | h=5 all  unvisited (n) | ms per prediction")
    for p in sorted(Path(args.data).glob("*.pkl")):
        app = App(load(p))
        model.fit(app)
        t0 = time.time()
        one, many = evaluate(model, app, args.split)
        ms = 1000 * (time.time() - t0) / (len(one) + 5 * len(many))
        a, b = summary(one), summary(many)
        print(f"{app.name:13} | {fmt(a['all'])}  {fmt(a['unvisited'])} ({a['n_unvisited']:4}) | "
              f"{fmt(b['all'])}  {fmt(b['unvisited'])} ({b['n_unvisited']:4}) | {ms:.1f}", flush=True)


if __name__ == "__main__":
    main()
