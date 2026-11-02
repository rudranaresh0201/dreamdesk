"""Checks the environment on the real app: expert, random agent, reset, and cheat protection.

Run:  scripts/private.sh 79 python3 tests/check_calculator.py
"""
import random
import statistics as stats
import sys
import time

sys.path.insert(0, ".")
from dreamdesk.calculator import ComputeTask, make_backend
from dreamdesk.core import DeskEnv


def spread(values):
    values = sorted(values)
    n = len(values)
    return f"median {stats.median(values):.0f}, p10 {values[n // 10]:.0f}, p90 {values[9 * n // 10]:.0f}, n={n}"


def press_by_name(env, name):
    for i, element in enumerate(env.pressable()):
        if element.name == name:
            return env.step(i)
    raise RuntimeError(f"no pressable element named {name!r}")


def main():
    rng = random.Random(0)
    env = DeskEnv(make_backend())

    # 1. Scripted expert on random tasks
    wins, step_ms, reset_ms, changed = 0, [], [], []
    expert_episodes = 25
    for _ in range(expert_episodes):
        task = ComputeTask(rng.randint(0, 99), rng.choice("+*-"), rng.randint(0, 99))
        t0 = time.perf_counter()
        env.reset(task)
        reset_ms.append((time.perf_counter() - t0) * 1000)
        reward = 0
        for name in task.expert_presses():
            t0 = time.perf_counter()
            _, reward, done, info = press_by_name(env, name)
            step_ms.append((time.perf_counter() - t0) * 1000)
            changed.append(info["changed"])
            if done:
                break
        wins += reward == 1.0
        if reward != 1.0:
            print(f"  expert FAILED on {task.description}; displayed: {[e.text for e in env.elements if e.role == 'text'][:2]}")
    print(f"expert success: {wins}/{expert_episodes}")
    print(f"step ms: {spread(step_ms)}")
    print(f"reset ms: {spread(reset_ms)}")
    print(f"changed elements per press: {spread(changed)}, max {max(changed)}")

    # 2. Reset must give the identical state every time
    task = ComputeTask(12, "+", 5)
    signatures = set()
    for _ in range(5):
        signatures.add(tuple(e.key() for e in env.reset(task)))
    print(f"reset identical: {len(signatures) == 1} ({len(signatures)} distinct start states from 5 resets)")

    # 3. Typing the answer directly must not count
    env.reset(ComputeTask(12, "+", 5))
    _, r1, _, _ = press_by_name(env, "1")
    _, r2, _, _ = press_by_name(env, "7")
    print(f"typing the answer 17 without the sum counts as success: {r1 == 1.0 or r2 == 1.0}")

    # 4. A random agent shows how hard the task is
    random_wins, closed = 0, 0
    random_episodes = 10
    for _ in range(random_episodes):
        env.reset(ComputeTask(rng.randint(0, 9), "+", rng.randint(0, 9)))
        done = False
        while not done:
            _, reward, done, info = env.step(rng.randrange(len(env.pressable())))
        random_wins += reward == 1.0
        closed += info["app_closed"]
    print(f"random agent success: {random_wins}/{random_episodes}; app closed itself in {closed} episodes")
    print(f"pressable elements per state: {len(env.pressable()) or 'n/a (app closed)'}")
    env.backend.stop()


if __name__ == "__main__":
    main()
