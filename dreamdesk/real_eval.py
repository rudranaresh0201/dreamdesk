"""Stage 4 real-app test: drop an agent into the real app (inside the sandbox) and see if it reaches goals.

Every agent gets the same goals (from a held-out seed's recordings, see goals.py), the same fresh start
(the app is relaunched), the same actions as the explorers, and at most dream.MAX_STEPS steps.

Agents:
  random    a random allowed action each step
  graph     a map of the training exploration: exact screens (as goal-key sets) joined by the actions seen
            between them. Locate the real screen at the most similar map screen, plan the shortest path
            to a screen that showed the most goal elements together, and follow it. Replan when the
            path runs out or its next action isn't offered. No path: a random action. (Two earlier versions oscillated between screens: abstract
            screens can't tell dialogs apart, and replanning every step flips between paths when the
            real screen never matches a map screen exactly. Both fixed before any pilot.)
  achiever  the policy trained in the dream (achiever.py), sampling from its action distribution

Run inside the sandbox, e.g.
  scripts/sandbox.sh --out runs/real python3 -m dreamdesk.real_eval --app clocks --agent random \
      --split val --goals 20 --out runs/real
"""
import argparse
import json
import random
import time
from collections import Counter, defaultdict, deque
from pathlib import Path

from .apps import APPS
from .collect import snapshot
from .core import DeskEnv
from .dream import MAX_STEPS
from .explore import NoTask, usable
from .goals import GoalSet, goal_key
from .wm_data import load, token
from .wm_eval import App


def pick_goals(app, split, n, seed=0):
    """The same n scorable goals for every agent: seen and novel, never unreachable."""
    goals = [g for g in GoalSet(app, split).goals if g["kind"] != "unreachable"]
    rng = random.Random(f"{app.name}-{split}-pick-{seed}")
    return rng.sample(goals, min(n, len(goals)))


def real_keys(elements):
    return {goal_key(token(r)) for r in snapshot(elements, detail=True)}


class RandomAgent:
    def __init__(self, app, rng, **_):
        self.rng = rng

    def act(self, elements, actions, goal):
        return self.rng.choice(actions)


class GraphAgent:
    """A map of training exploration at the level of exact screens (as goal-key sets), with actions
    as edges. The real screen is located at the most similar map screen (Jaccard), then BFS to the
    nearest screen that showed the most goal elements together; take the first step, look again."""

    def __init__(self, app, rng, **_):
        self.app, self.rng = app, rng
        self.node = {}  # goal-key set -> node index
        self.keys = []
        self.edges = defaultdict(Counter)  # node -> Counter of (action key, next node)
        for t in app.transitions["train"]:
            a, b = self.node_of(app.screens[t[0]]), self.node_of(app.screens[t[4]])
            self.edges[a][(app.action(t)[1], b)] += 1
        self.cache = {}

    def node_of(self, screen):
        k = frozenset(goal_key(self.app.tokens[i]) for i in screen)
        if k not in self.node:
            self.node[k] = len(self.keys)
            self.keys.append(k)
        return self.node[k]

    def locate(self, keys):
        n = self.node.get(frozenset(keys))
        if n is not None:
            return n
        return max(self.edges, key=lambda m: len(keys & self.keys[m]) / len(keys | self.keys[m]))

    def plan(self, start, goal):
        """Shortest path (list of action keys) from start to a screen showing the most goal elements."""
        g = set(goal["keys"])
        if goal["keys"] not in self.cache:
            overlap = [len(g & k) for k in self.keys]
            best = max(overlap, default=0)
            self.cache[goal["keys"]] = {n for n, v in enumerate(overlap) if v == best} if best else set()
        targets = self.cache[goal["keys"]] - {start}  # here already and not done: look elsewhere
        back = {start: None}
        q = deque([start])
        while q:
            n = q.popleft()
            if n in targets:
                path = []
                while back[n] is not None:
                    n, act = back[n]
                    path.append(act)
                return path[::-1]
            for act, nxt in self.outcomes(n):
                if nxt not in back:
                    back[nxt] = (n, act)
                    q.append(nxt)
        return []

    def outcomes(self, n):
        """Each action's most common next screen only. Rarer outcomes are mostly late effects of an
        earlier action recorded on this step (e.g. a dialog opening one step late), not real edges."""
        best = {}
        for (act, nxt), c in self.edges[n].items():
            if act not in best or c > best[act][1]:
                best[act] = (nxt, c)
        return [(act, nxt) for act, (nxt, _) in best.items()]

    def act(self, elements, actions, goal):
        """Follow the current plan; replan when it runs out, the goal changed, or its next step isn't offered."""
        if getattr(self, "goal", None) is not goal:
            self.path, self.goal = [], goal
        for attempt in range(2):
            if self.path:
                step = self.path[0]
                for a in actions:
                    if (a.verb, a.element.role, a.element.name, a.text) == step:
                        self.path = self.path[1:]
                        return a
            if attempt == 0:
                self.path = self.plan(self.locate(real_keys(elements)), goal)
        return self.rng.choice(actions)


class AchieverAgent:
    """Maps real elements to the training vocabulary (new ones get new ids and features), then asks the policy."""

    def __init__(self, app, rng, ckpt=None, **_):
        import torch
        from .achiever import Achiever
        from .world_model import MAX_ELEMENTS, Features
        self.torch, self.Features, self.MAX = torch, Features, MAX_ELEMENTS
        ck = torch.load(ckpt, weights_only=False)
        self.roles = dict(ck["roles"])
        self.model = Achiever(n_roles=len(self.roles) + 8, **ck["config"])
        self.model.load_state_dict(ck["model"])
        self.model.eval()
        torch.manual_seed(rng.randrange(1 << 30))
        self.app = app
        self.tokens = list(app.tokens)
        self.vocab = {t: i for i, t in enumerate(self.tokens)}
        self.depth = dict(app.depth)
        self.key_to_id = {}
        for s in GoalSet.train_screen_ids(app):
            for e in app.screens[s]:
                self.key_to_id.setdefault(goal_key(app.tokens[e]), e)
        self.f, self.dirty = None, True

    def id_of(self, row):
        tok = token(row)
        i = self.vocab.get(tok)
        if i is None:
            i = self.vocab[tok] = len(self.tokens)
            self.tokens.append(tok)
            self.depth[i] = row[0].count(".")
            self.dirty = True
        return i

    def act(self, elements, actions, goal):
        rows = snapshot(elements, detail=True)
        ids = [self.id_of(r) for r in rows]
        by_elem = {id(e): i for e, i in zip(elements, ids)}
        if self.dirty:
            self.f = self.Features(self, self.roles)
            self.dirty = False
        row = sorted(set(ids), key=lambda e: self.depth.get(e, 0))[:self.MAX]
        pos = {e: j for j, e in enumerate(row)}
        triples, real = [], []
        for a in actions:
            e = by_elem.get(id(a.element))
            if e is None or e not in pos:
                continue
            tr = (a.verb, pos[e], a.text)
            if tr not in triples:
                triples.append(tr)
                real.append(a)
        if not triples:
            return actions[0]
        gids = [self.key_to_id[k] for k in goal["keys"]]
        with self.torch.no_grad():
            logp, _ = self.model(self.f, [(gids, row, triples)])
        k = int(self.torch.distributions.Categorical(logits=logp[0]).sample())
        return real[k]


AGENTS = {"random": RandomAgent, "graph": GraphAgent, "achiever": AchieverAgent}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--app", required=True, choices=sorted(APPS))
    ap.add_argument("--agent", required=True, choices=sorted(AGENTS))
    ap.add_argument("--ckpt", default=None)
    ap.add_argument("--name", default=None, help="label for the output file (default: the agent)")
    ap.add_argument("--split", default="val")
    ap.add_argument("--goals", type=int, default=20)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--data", default="data/wm")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    spec = APPS[args.app]
    app = App(load(Path(args.data) / f"{args.app}.pkl"))
    goals = pick_goals(app, args.split, args.goals)
    rng = random.Random(f"{args.app}-{args.agent}-{args.seed}")
    agent = AGENTS[args.agent](app, rng, ckpt=args.ckpt)
    env = DeskEnv(spec.backend(), max_steps=MAX_STEPS, blocked_names=spec.blocked_names(), words=spec.words)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{args.app}_{args.name or args.agent}_{args.split}_seed{args.seed}.jsonl"
    wins, t0 = 0, time.time()
    with open(path, "x") as f:
        for gi, goal in enumerate(goals):
            elements = env.reset(NoTask())
            keys = set(goal["keys"])
            done = keys <= real_keys(elements)
            steps, taken, error = 0, [], None
            while not done and steps < MAX_STEPS:
                actions = usable(env)
                if not actions:
                    break
                a = agent.act(elements, actions, goal)
                taken.append(a.describe())
                try:
                    elements, _, _, info = env.act(a)
                except Exception as err:
                    error = str(err)[:200]
                    break
                steps += 1
                if not elements or info["app_closed"]:
                    break
                done = keys <= real_keys(elements)
            wins += done
            f.write(json.dumps({"goal": gi, "kind": goal["kind"], "goal_steps": goal["steps"], "keys": goal["keys"],
                                "success": done, "steps": steps, "actions": taken, "error": error}, ensure_ascii=False) + "\n")
            f.flush()
            print(f"{args.app} {args.name or args.agent}: goal {gi + 1}/{len(goals)} {'WIN ' if done else 'miss'} in {steps} steps "
                  f"({wins} wins, {time.time() - t0:.0f} s)", flush=True)
    env.backend.stop()
    print(f"finished: {wins}/{len(goals)} goals, {time.time() - t0:.0f} s", flush=True)


if __name__ == "__main__":
    main()
