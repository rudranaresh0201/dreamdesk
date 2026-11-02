"""Records real calculator episodes for behaviour cloning and the world model.

Three kinds of player, because each teaches something different:
  expert  always succeeds: shows what good looks like
  noisy   expert with random mistakes: shows off-path states and how the app reacts
  random  presses anything: covers odd states the others never reach

Run one worker on a private desktop:
  scripts/private.sh 90 python3 -m dreamdesk.collect --worker 0 --episodes 100
"""
import argparse
import gzip
import json
import random
import time
from pathlib import Path

from .calculator import BLOCKED, ComputeTask, is_test_task, make_backend
from .core import DeskEnv

POLICY_MIX = [("expert", 0.3), ("noisy", 0.5), ("random", 0.2)]
TEST_FRACTION = 0.1
NOISE = 0.25
MAX_STEPS = 15


def sample_task(rng, want_test):
    while True:
        a, op, b = rng.randint(0, 99), rng.choice("+*-"), rng.randint(0, 99)
        if is_test_task(a, op, b) == want_test:
            return ComputeTask(a, op, b)


def snapshot(elements):
    return [[e.path, e.role, e.name, e.text, e.pressable] for e in elements]


def choose(env, policy, plan, rng):
    """Return the index of the element to press, and how far along the expert's plan we are."""
    options = env.pressable()
    if policy == "random" or not plan or (policy == "noisy" and rng.random() < NOISE):
        return rng.randrange(len(options)), plan
    wanted, rest = plan[0], plan[1:]
    for i, element in enumerate(options):
        if element.name == wanted:
            return i, rest
    return rng.randrange(len(options)), rest


def play_episode(env, policy, split, rng, episode_id):
    task = sample_task(rng, split == "test")
    start_obs = env.reset(task)
    plan = task.expert_presses()
    record = {
        "id": episode_id,
        "split": split,
        "policy": policy,
        "task": {"a": task.a, "op": task.op, "b": task.b},
        "start": snapshot(start_obs),
        "steps": [],
    }
    done, reward = False, 0.0
    while not done:
        index, plan = choose(env, policy, plan, rng)
        target = env.pressable()[index]
        action = {"index": index, "path": target.path, "name": target.name, "n_options": len(env.pressable())}
        t0 = time.perf_counter()
        elements, reward, done, info = env.step(index)
        record["steps"].append({
            "action": action,
            "next": snapshot(elements),
            "reward": reward,
            "done": done,
            "changed": info["changed"],
            "app_closed": info["app_closed"],
            "ms": round((time.perf_counter() - t0) * 1000, 1),
        })
    record["success"] = reward == 1.0
    return record


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker", type=int, required=True)
    parser.add_argument("--episodes", type=int, required=True)
    parser.add_argument("--out", default="data/calculator")
    parser.add_argument("--seed-offset", type=int, default=0)
    args = parser.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    seed = 1000 * args.worker + args.seed_offset
    rng = random.Random(seed)
    env = DeskEnv(make_backend(), max_steps=MAX_STEPS, blocked_names=BLOCKED)
    policies, weights = zip(*POLICY_MIX)
    path = out / f"worker{args.worker}_seed{seed}.jsonl.gz"

    errors = 0
    start = time.perf_counter()
    # "x" refuses to reuse a seed: appending after a cut-off gzip file would corrupt what follows.
    with gzip.open(path, "xt", encoding="utf-8") as f:
        for n in range(args.episodes):
            policy = rng.choices(policies, weights)[0]
            split = "test" if rng.random() < TEST_FRACTION else "train"
            try:
                record = play_episode(env, policy, split, rng, f"w{args.worker}s{seed}e{n}")
            except Exception as err:  # discard the broken episode and restart the app next time
                errors += 1
                print(f"worker {args.worker}: episode {n} discarded: {err}", flush=True)
                if errors > 20:
                    raise
                continue
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            f.flush()
            if (n + 1) % 25 == 0:
                print(f"worker {args.worker}: {n + 1} episodes, {time.perf_counter() - start:.0f} s", flush=True)
    env.backend.stop()
    print(f"worker {args.worker}: finished, {errors} discarded, {time.perf_counter() - start:.0f} s", flush=True)


if __name__ == "__main__":
    main()
