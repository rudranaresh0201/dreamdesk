"""Arm A: behaviour cloning. Learn to press what the scripted expert pressed.

Run:  .venv/bin/python -m dreamdesk.bc --seed 0
Trains on the train split only. The real-app test is in evaluate.py.
"""
import argparse
import gzip
import json
import random
import time
import zlib
from pathlib import Path

import torch
import torch.nn.functional as F

from .calculator import BLOCKED, ComputeTask
from .policy import PointerPolicy, build_vocab, collate, encode


def read_episodes(folder):
    """Read every complete episode. A file cut off mid-write still gives what came before."""
    episodes = []
    for path in sorted(Path(folder).glob("*.jsonl.gz")):
        with gzip.open(path, "rt", encoding="utf-8") as f:
            try:
                for line in f:
                    episodes.append(json.loads(line))
            except (EOFError, json.JSONDecodeError):
                pass
    return episodes


def expert_examples(episodes):
    """One (goal, tree, action index) example per expert press."""
    examples = []
    for ep in episodes:
        t = ep["task"]
        goal = ComputeTask(t["a"], t["op"], t["b"]).expression
        rows = ep["start"]
        for step in ep["steps"]:
            allowed = [r[2] for r in rows if r[4] and r[2] not in BLOCKED]
            action = step["action"]
            if allowed[action["index"]] != action["name"]:
                raise ValueError(f"{ep['id']}: recorded index doesn't match the button pressed")
            examples.append({"goal": goal, "rows": rows, "action": action["index"], "episode": ep["id"]})
            rows = step["next"]
    return examples


def is_validation(episode_id):
    return zlib.crc32(episode_id.encode()) % 10 == 0


def make_samples(examples, chars, roles):
    samples = []
    for ex in examples:
        sample = encode(ex["goal"], ex["rows"], BLOCKED, chars, roles)
        sample["target"] = sample["options"][ex["action"]]
        samples.append(sample)
    return samples


def run_batches(model, samples, batch_size, optimizer=None):
    """One pass over the data. Returns the mean loss and the share of presses that match the expert."""
    order = list(range(len(samples)))
    if optimizer:
        random.shuffle(order)
    total_loss, correct = 0.0, 0
    for start in range(0, len(order), batch_size):
        chunk = [samples[i] for i in order[start:start + batch_size]]
        target = torch.stack([s["target"] for s in chunk])
        with torch.set_grad_enabled(optimizer is not None):
            scores = model(collate(chunk))
            loss = F.cross_entropy(scores, target, reduction="sum")
        if optimizer:
            optimizer.zero_grad()
            (loss / len(chunk)).backward()
            optimizer.step()
        total_loss += loss.item()
        correct += (scores.argmax(1) == target).sum().item()
    return total_loss / len(samples), correct / len(samples)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--data", default="data/calculator")
    parser.add_argument("--out", default="runs/arm_a")
    parser.add_argument("--epochs", type=int, default=150)
    parser.add_argument("--patience", type=int, default=25)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--threads", type=int, default=4)
    args = parser.parse_args()

    torch.set_num_threads(args.threads)
    torch.manual_seed(args.seed)
    random.seed(args.seed)

    expert = [e for e in read_episodes(args.data) if e["policy"] == "expert"]
    train_side = [e for e in expert if e["split"] == "train"]
    val_eps = [e for e in train_side if is_validation(e["id"])]
    train_eps = [e for e in train_side if not is_validation(e["id"])]
    test_eps = [e for e in expert if e["split"] == "test"]
    train_ex, val_ex, test_ex = map(expert_examples, (train_eps, val_eps, test_eps))

    # Vocabularies come from training data only, so unseen text becomes <unk> at test time.
    chars = build_vocab(c for ex in train_ex for c in ex["goal"] + "".join(r[2] + r[3] for r in ex["rows"]))
    roles = build_vocab(r[1] for ex in train_ex for r in ex["rows"])
    train, val = make_samples(train_ex, chars, roles), make_samples(val_ex, chars, roles)
    print(f"episodes train {len(train_eps)} val {len(val_eps)} test {len(test_eps)}; presses train {len(train)} val {len(val)} test {len(test_ex)}", flush=True)

    model = PointerPolicy(len(chars), len(roles))
    print(f"parameters: {sum(p.numel() for p in model.parameters())}", flush=True)
    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    checkpoint = out / f"seed{args.seed}.pt"
    best_loss, best_epoch, history = float("inf"), 0, []
    start = time.perf_counter()
    for epoch in range(1, args.epochs + 1):
        model.train()
        train_loss, train_acc = run_batches(model, train, args.batch_size, optimizer)
        model.eval()
        val_loss, val_acc = run_batches(model, val, args.batch_size)
        history.append({"epoch": epoch, "train_loss": train_loss, "train_acc": train_acc, "val_loss": val_loss, "val_acc": val_acc})
        if val_loss < best_loss:
            best_loss, best_epoch = val_loss, epoch
            torch.save({"model": model.state_dict(), "chars": chars, "roles": roles}, checkpoint)
        if epoch % 5 == 0 or epoch == 1:
            print(f"epoch {epoch}: train loss {train_loss:.3f} acc {train_acc:.3f}, val loss {val_loss:.3f} acc {val_acc:.3f}, {time.perf_counter() - start:.0f} s", flush=True)
        if epoch - best_epoch >= args.patience:
            break

    model.load_state_dict(torch.load(checkpoint, map_location="cpu", weights_only=True)["model"])
    model.eval()
    result = {"seed": args.seed, "best_epoch": best_epoch, "best_val_loss": best_loss, "seconds": time.perf_counter() - start,
              "train_presses": len(train), "history": history}
    if test_ex:
        test_loss, test_acc = run_batches(model, make_samples(test_ex, chars, roles), args.batch_size)
        result.update(test_presses=len(test_ex), test_loss=test_loss, test_acc=test_acc)
    (out / f"seed{args.seed}_train.json").write_text(json.dumps(result))
    print(f"finished: best epoch {best_epoch}, val loss {best_loss:.3f}", flush=True)


if __name__ == "__main__":
    main()
