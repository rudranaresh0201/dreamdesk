"""Scores exploration runs: how many distinct screens, actions and transitions each one found.

Run:  python3 -m dreamdesk.coverage data/explore
"""
import gzip
import json
import statistics as stats
import sys
from collections import defaultdict
from pathlib import Path

from .core import Element
from .explore import screen_key


def read_run(path):
    episodes = []
    with gzip.open(path, "rt", encoding="utf-8") as f:
        try:
            for line in f:
                episodes.append(json.loads(line))
        except (EOFError, json.JSONDecodeError):
            pass
    return episodes


def elements_of(rows):
    return [Element(r[0], r[1], r[2], r[3], r[4], None, frozenset(r[5]), tuple(r[6])) for r in rows]


def score(episodes, checkpoints=(100, 250, 500, 1000, 2000)):
    """Counts after every step, reported at checkpoints. Screens are recomputed from the saved
    snapshots with today's screen_key, so a run never depends on the definition it was recorded with."""
    screens, transitions, tried, discovered = set(), set(), set(), set()
    curve, steps, errors, closed, no_change, ms = {}, 0, 0, 0, 0, []
    for ep in episodes:
        screen = screen_key(elements_of(ep["start"]))
        screens.add(screen)
        for row in ep["start"]:
            if row[4] or "editable" in row[5]:
                discovered.add((row[1], row[2]))
        for s in ep["steps"]:
            steps += 1
            tried.add(s["action"])
            if "error" in s:
                errors += 1
                break
            else:
                closed += s["app_closed"]
                no_change += s["changed"] == 0
                ms.append(s["ms"])
                if s["next"]:
                    next_screen = screen_key(elements_of(s["next"]))
                    screens.add(next_screen)
                    transitions.add((screen, s["action"], next_screen))
                    screen = next_screen
                for row in s["next"]:
                    if row[4] or "editable" in row[5]:
                        discovered.add((row[1], row[2]))
            if steps in checkpoints:
                curve[steps] = (len(screens), len(discovered), len(transitions))
    return {"steps": steps, "screens": len(screens), "discovered_elements": len(discovered), "actions_tried": len(tried),
            "transitions": len(transitions), "errors": errors, "app_closed": closed,
            "no_change_pct": round(100 * no_change / max(1, steps - errors)),
            "step_ms_median": round(stats.median(ms)) if ms else None, "curve": curve}


def main():
    rows = []
    for path in sorted(Path(sys.argv[1]).glob("*.jsonl.gz")):
        app, explorer, seed = path.name.replace(".jsonl.gz", "").rsplit("_", 2)
        rows.append((app, explorer, seed, score(read_run(path))))
    print(f"{'app':14} {'explorer':8} {'seed':6} {'steps':>5} {'screens':>7} {'elements':>8} {'transitions':>11} {'no-op %':>7} {'errors':>6} {'ms':>5}")
    for app, explorer, seed, r in rows:
        print(f"{app:14} {explorer:8} {seed:6} {r['steps']:5} {r['screens']:7} {r['discovered_elements']:8} {r['transitions']:11} {r['no_change_pct']:7} {r['errors']:6} {r['step_ms_median'] or 0:5}")
    by = defaultdict(lambda: defaultdict(list))
    for app, explorer, seed, r in rows:
        by[app][explorer].append(r)
    compared = {app: v for app, v in by.items() if v["novelty"] and v["random"]}
    if compared:
        print("\nMedian distinct screens per app, across seeds")
        wins = 0
        for app, v in sorted(compared.items()):
            ns, rs = [r["screens"] for r in v["novelty"]], [r["screens"] for r in v["random"]]
            n, r = stats.median(ns), stats.median(rs)
            wins += n > r
            every = "every novelty seed higher" if min(ns) > max(rs) else "every random seed higher" if min(rs) > max(ns) else "seeds overlap"
            print(f"  {app:14} novelty {n:6.1f} ({len(ns)} seeds)   random {r:6.1f} ({len(rs)} seeds)   {every}")
        print(f"novelty's median beats random's in {wins} of {len(compared)} apps")
        for key in ("discovered_elements", "transitions"):
            w = sum(stats.median(r[key] for r in v["novelty"]) > stats.median(r[key] for r in v["random"]) for v in compared.values())
            print(f"secondary, {key}: novelty's median higher in {w} of {len(compared)} apps")


if __name__ == "__main__":
    main()
