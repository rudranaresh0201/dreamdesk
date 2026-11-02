"""Summarises Arm A exactly as pre-registered in experiments/arm_a_prereg.md.

Run:  .venv/bin/python -m dreamdesk.report_arm_a runs/arm_a
"""
import json
import statistics as stats
import sys
from collections import Counter
from pathlib import Path

SEEDS = range(5)
EXPECTED = {"test": 100, "train": 50}


def quantile(values, q):
    """Linear interpolation between sorted values."""
    ordered = sorted(values)
    position = q * (len(ordered) - 1)
    low = int(position)
    high = min(low + 1, len(ordered) - 1)
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def spread(values):
    return f"median {stats.median(values):.1f}, p10 {quantile(values, 0.1):.1f}, p90 {quantile(values, 0.9):.1f}"


def read(folder, name, expected):
    records = [json.loads(line) for line in (folder / f"{name}.jsonl").open(encoding="utf-8")]
    if len(records) != expected:
        raise SystemExit(f"INCOMPLETE: {name} has {len(records)} of {expected} episodes")
    return records


def rate(records):
    return 100 * sum(r["success"] for r in records) / len(records)


def main():
    folder = Path(sys.argv[1])
    test = {s: read(folder, f"seed{s}_test", EXPECTED["test"]) for s in SEEDS}
    train = {s: read(folder, f"seed{s}_train", EXPECTED["train"]) for s in SEEDS}
    randoms = read(folder, "random_test", EXPECTED["test"])
    trained = {s: json.loads((folder / f"seed{s}_train.json").read_text()) for s in SEEDS}

    test_rates = [rate(test[s]) for s in SEEDS]
    train_rates = [rate(train[s]) for s in SEEDS]
    print("Real-app success, percent")
    print(f"  held-out, BC:   {spread(test_rates)}   by seed {test_rates}")
    print(f"  train-side, BC: {spread(train_rates)}   by seed {train_rates}")
    print(f"  held-out, random player: {rate(randoms):.1f}")

    offline = [100 * trained[s]["test_acc"] for s in SEEDS]
    print(f"Offline held-out press accuracy: {spread(offline)}   ({trained[0]['test_presses']} presses)")
    print(f"Training: {trained[0]['train_presses']} presses, best epochs {[trained[s]['best_epoch'] for s in SEEDS]}, longest {max(trained[s]['seconds'] for s in SEEDS):.0f} s")

    print("Held-out success by op, percent")
    for op in "+*-":
        rates = [rate([r for r in test[s] if r["op"] == op]) for s in SEEDS]
        n = sum(r["op"] == op for r in test[0])
        print(f"  {op}: {spread(rates)}   (n={n} per seed)")

    failures = [r for s in SEEDS for r in test[s] if not r["success"]]
    print(f"Held-out failures across seeds: {len(failures)} of {5 * EXPECTED['test']}")
    print(f"  errored: {sum(r.get('errored', False) for r in failures)}, app closed: {sum(r['app_closed'] for r in failures)}")
    wrong = [r["first_wrong"] for r in failures if r["first_wrong"]]
    print(f"  first wrong press at step: {sorted(Counter(w['step'] for w in wrong).items())}")
    print(f"  most common first mistakes (pressed, expected): {Counter((w['pressed'], w['expected']) for w in wrong).most_common(8)}")
    no_mistake = sum(r["first_wrong"] is None and not r.get("errored", False) for r in failures)
    print(f"  failed with no wrong press: {no_mistake}")
    wrong_then_won = sum(r["first_wrong"] is not None and r["success"] for s in SEEDS for r in test[s])
    print(f"  recovered and won after a wrong press: {wrong_then_won}")

    gate = quantile(test_rates, 0.1) > rate(randoms)
    print(f"Gate (p10 held-out above the random player): {'PASS' if gate else 'FAIL'}")


if __name__ == "__main__":
    main()
