"""Planning inside the dream: beam search through the world-model ensemble's predictions, instead of a learned policy.

From the current screen, every allowed action is imagined with the ensemble; the WIDTH most promising imagined
screens (most goal elements showing, then least summed member disagreement x LAMBDA) are expanded again, up to
DEPTH steps. The first imagined path that shows every goal element is returned (shortest first; among equally
short ones, the least uncertain). If none does, the path to the best partial screen.

In the real app (real_eval's PlannerAgent) the plan is followed while the real screens look like the imagined
ones, and redone from the real screen when they don't.

  python3 -m dreamdesk.planner --app clocks --split val --goals 20      # planner success inside the dream
"""
import argparse
import json
import random
import statistics as stats
import time

from .dream import MAX_STEPS, Dream

WIDTH, DEPTH, LAMBDA = 8, 5, 0.0


def plan(dream, screen, goal, depth=DEPTH, width=WIDTH, lam=LAMBDA):
    """Returns (actions, imagined screens after each action). goal: set of goal keys."""
    need = len(goal)
    beams = [(screen, [], [], 0.0)]
    best = (len(goal & dream.keys(screen)), 0.0, [], [])
    for _ in range(depth):
        cands = [(b, a) for b, beam in enumerate(beams) for a in dream.actions(beam[0])]
        if not cands:
            break
        nxt, dis = dream.predict([beams[b][0] for b, _ in cands], [(None, *a) for _, a in cands])
        full, scored, seen = [], [], {}
        for (b, a), s, d in zip(cands, nxt, dis):
            _, path, imagined, cost = beams[b]
            hit = len(goal & dream.keys(s))
            item = (hit, cost + lam * d, path + [a], imagined + [s], s)
            if hit == need:
                full.append(item)
            elif s not in seen or (hit, -item[1]) > (seen[s][0], -seen[s][1]):
                seen[s] = item
        if full:
            h, c, p, im, _ = min(full, key=lambda x: x[1])
            return p, im
        scored = sorted(seen.values(), key=lambda x: (-x[0], x[1]))[:width]
        if scored and (scored[0][0], -scored[0][1]) > (best[0], -best[1]):
            best = scored[0][:4]
        beams = [(s, p, im, c) for _, c, p, im, s in scored]
    return best[2], best[3]


def dream_eval(args):
    """Plan and act inside the dream itself (an optimistic check: the planner searches the same model it is
    scored in). The real test is real_eval --agent planner."""
    from .goals import GoalSet
    from .real_eval import pick_goals
    from .world_model import Neural
    th = json.load(open(args.thresholds))
    wm = Neural(args.members, args.data, th["vanish"], th["appear"], args.threads)
    out = {}
    for app in args.apps:
        d = Dream(wm, app, args.data, seed=args.seed)
        goals = pick_goals(d.app, args.split, args.goals, rule=args.rule)
        rng = random.Random(args.seed)
        wins, t0 = [], time.time()
        for g in goals:
            screen = d.app.screens[rng.choice(d.starts)]
            keys = set(g["keys"])
            ok = keys <= d.keys(screen)
            for step in range(MAX_STEPS):
                if ok:
                    break
                path, _ = plan(d, screen, keys, min(args.depth, MAX_STEPS - step), args.width, args.lam)
                if not path:
                    break
                (screen,), _ = d.predict([screen], [(None, *path[0])])
                ok = keys <= d.keys(screen)
            wins.append(ok)
        out[app] = wins
        print(f"{app:13} planner success in the dream {stats.mean(wins):.3f} over {len(goals)} goals, "
              f"{(time.time() - t0) / len(goals):.1f} s per goal", flush=True)
    if args.out:
        json.dump(out, open(args.out, "w"))


def main():
    from .achiever import APPS
    ap = argparse.ArgumentParser()
    ap.add_argument("--apps", nargs="+", default=APPS)
    ap.add_argument("--split", default="val")
    ap.add_argument("--goals", type=int, default=20)
    ap.add_argument("--rule", default="new")
    ap.add_argument("--width", type=int, default=WIDTH)
    ap.add_argument("--depth", type=int, default=DEPTH)
    ap.add_argument("--lam", type=float, default=LAMBDA)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--data", default="data/wm")
    ap.add_argument("--members", nargs="+", default=[f"runs/wm/member_seed{k}.pt" for k in range(5)])
    ap.add_argument("--thresholds", default="runs/wm/thresholds.json")
    ap.add_argument("--out", default=None)
    dream_eval(ap.parse_args())


if __name__ == "__main__":
    main()
