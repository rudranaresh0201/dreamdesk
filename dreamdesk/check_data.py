"""Checks a collected dataset before anyone trains on it.

Run:  python3 -m dreamdesk.check_data data/calculator
"""
import gzip
import json
import statistics as stats
import sys
from collections import Counter, defaultdict
from pathlib import Path

from .calculator import is_test_task


def main():
    folder = Path(sys.argv[1])
    files = sorted(folder.glob("*.jsonl.gz"))
    episodes, ids, broken_lines = [], set(), 0
    for path in files:
        with gzip.open(path, "rt", encoding="utf-8") as f:
            try:
                for line in f:
                    episodes.append(json.loads(line))
            except (EOFError, json.JSONDecodeError):
                broken_lines += 1
    print(f"files: {len(files)}, episodes: {len(episodes)}, unreadable tails: {broken_lines}")
    print(f"size on disk: {sum(p.stat().st_size for p in files) / 1e6:.1f} MB")

    by_policy = defaultdict(list)
    transitions, step_ms, changed, leaks, dups, closed, wrong_reward = 0, [], [], 0, 0, 0, 0
    pressed = Counter()
    starts = set()
    for ep in episodes:
        by_policy[ep["policy"]].append(ep)
        if ep["id"] in ids:
            dups += 1
        ids.add(ep["id"])
        t = ep["task"]
        if is_test_task(t["a"], t["op"], t["b"]) != (ep["split"] == "test"):
            leaks += 1
        starts.add(json.dumps(ep["start"], ensure_ascii=False))
        for s in ep["steps"]:
            transitions += 1
            step_ms.append(s["ms"])
            changed.append(s["changed"])
            pressed[s["action"]["name"]] += 1
            closed += s["app_closed"]
        rewards = sum(s["reward"] for s in ep["steps"])
        if rewards != float(ep["success"]) or not ep["steps"][-1]["done"]:
            wrong_reward += 1

    print(f"transitions: {transitions}")
    print(f"splits: {Counter(e['split'] for e in episodes)}")
    for name, group in sorted(by_policy.items()):
        wins = sum(e["success"] for e in group)
        print(f"  {name}: {len(group)} episodes, {wins} succeeded ({100 * wins / len(group):.0f}%), median length {stats.median(len(e['steps']) for e in group)}")
    print(f"step ms: median {stats.median(step_ms):.0f}, p90 {sorted(step_ms)[int(0.9 * len(step_ms))]:.0f}")
    no_change = sum(c == 0 for c in changed)
    print(f"elements changed: median {stats.median(changed)}, max {max(changed)}; presses changing nothing: {100 * no_change / len(changed):.0f}%")
    print(f"distinct actions pressed: {len(pressed)}; most common: {pressed.most_common(6)}")
    print(f"distinct start states: {len(starts)}")

    problems = {"train/test leaks": leaks, "duplicate episode ids": dups, "reward mismatches": wrong_reward, "app closed": closed}
    print(f"problems: {problems}")
    expert = by_policy.get("expert", [])
    if expert and not all(e["success"] for e in expert):
        print("WARNING: some expert episodes failed")
    if len(starts) != 1 or leaks or dups or wrong_reward:
        print("VERDICT: FAIL, don't train on this")
    else:
        print("VERDICT: PASS")


if __name__ == "__main__":
    main()
