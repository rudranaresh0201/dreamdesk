"""A small pointer policy: reads the goal and the screen, then scores each pressable element.

Input tokens:  [goal characters...] [on-screen elements...]
Output:        one score per element; only elements the agent may press can be chosen.
"""
import torch
import torch.nn as nn

MAX_CHARS = 24  # characters kept from an element's name or text
MAX_GOAL = 8
MAX_DEPTH = 24
PAD, UNK = 0, 1


def build_vocab(words):
    vocab = {"<pad>": PAD, "<unk>": UNK}
    for word in sorted(set(words)):
        vocab.setdefault(word, len(vocab))
    return vocab


def _chars(text, chars, length):
    ids = [chars.get(c, UNK) for c in text[:length]]
    return ids + [PAD] * (length - len(ids))


def encode(goal, rows, blocked, chars, roles):
    """Turn a goal and a tree snapshot, rows of [path, role, name, text, pressable], into tensors.

    `options` lists the positions of allowed elements, in the same order as DeskEnv.pressable(),
    so options[k] is the element that env.step(k) presses.
    """
    kept = [r for r in rows if r[2] or r[3] or r[4]]
    return {
        "goal": torch.tensor(_chars(goal, chars, MAX_GOAL), dtype=torch.int16),
        "role": torch.tensor([roles.get(r[1], UNK) for r in kept], dtype=torch.int16),
        "depth": torch.tensor([min(r[0].count("."), MAX_DEPTH - 1) for r in kept], dtype=torch.int16),
        "pressable": torch.tensor([bool(r[4]) for r in kept], dtype=torch.bool),
        "name": torch.tensor([_chars(r[2], chars, MAX_CHARS) for r in kept], dtype=torch.int16),
        "text": torch.tensor([_chars(r[3], chars, MAX_CHARS) for r in kept], dtype=torch.int16),
        "options": torch.tensor([i for i, r in enumerate(kept) if r[4] and r[2] not in blocked], dtype=torch.long),
    }


def collate(samples):
    """Pad samples to the longest tree in the batch."""
    size = max(len(s["role"]) for s in samples)
    batch = {"goal": torch.stack([s["goal"] for s in samples]).long()}
    for key in ("role", "depth", "name", "text"):
        shape = (len(samples), size, *samples[0][key].shape[1:])
        batch[key] = torch.zeros(shape, dtype=torch.long)
    batch["pressable"] = torch.zeros(len(samples), size, dtype=torch.bool)
    batch["allowed"] = torch.zeros(len(samples), size, dtype=torch.bool)
    batch["padding"] = torch.ones(len(samples), size, dtype=torch.bool)
    for i, s in enumerate(samples):
        n = len(s["role"])
        for key in ("role", "depth", "name", "text"):
            batch[key][i, :n] = s[key].long()
        batch["pressable"][i, :n] = s["pressable"]
        batch["allowed"][i, s["options"]] = True
        batch["padding"][i, :n] = False
    return batch


class PointerPolicy(nn.Module):
    def __init__(self, n_chars, n_roles, dim=64, layers=3, heads=4):
        super().__init__()
        self.char = nn.Embedding(n_chars, dim, padding_idx=PAD)
        self.char_pos = nn.Embedding(MAX_CHARS, dim)
        self.goal_pos = nn.Embedding(MAX_GOAL, dim)
        self.goal_kind = nn.Parameter(torch.zeros(dim))
        self.role = nn.Embedding(n_roles, dim, padding_idx=PAD)
        self.depth = nn.Embedding(MAX_DEPTH, dim)
        self.pressable = nn.Embedding(2, dim)
        self.name_proj = nn.Linear(dim, dim)
        self.text_proj = nn.Linear(dim, dim)
        self.norm = nn.LayerNorm(dim)
        layer = nn.TransformerEncoderLayer(dim, heads, dim * 2, dropout=0.0, batch_first=True, norm_first=True)
        self.encoder = nn.TransformerEncoder(layer, layers, enable_nested_tensor=False)
        self.score = nn.Linear(dim, 1)

    def _read_chars(self, ids):
        """Add up characters with their positions, so "12" and "21" stay different."""
        positions = torch.arange(ids.shape[-1], device=ids.device)
        vectors = self.char(ids) + self.char_pos(positions)
        return (vectors * (ids != PAD).unsqueeze(-1)).sum(-2)

    def forward(self, batch):
        """Return scores of shape (batch, elements). Choices that aren't allowed score -inf."""
        goal_ids = batch["goal"]
        positions = torch.arange(goal_ids.shape[1], device=goal_ids.device)
        goal = self.char(goal_ids) + self.goal_pos(positions) + self.goal_kind
        elements = (
            self.role(batch["role"])
            + self.depth(batch["depth"])
            + self.pressable(batch["pressable"].long())
            + self.name_proj(self._read_chars(batch["name"]))
            + self.text_proj(self._read_chars(batch["text"]))
        )
        tokens = self.norm(torch.cat([goal, elements], dim=1))
        padding = torch.cat([goal_ids == PAD, batch["padding"]], dim=1)
        out = self.encoder(tokens, src_key_padding_mask=padding)
        scores = self.score(out[:, goal_ids.shape[1]:]).squeeze(-1)
        return scores.masked_fill(~batch["allowed"], float("-inf"))


def load_checkpoint(path):
    saved = torch.load(path, map_location="cpu", weights_only=True)
    model = PointerPolicy(len(saved["chars"]), len(saved["roles"]))
    model.load_state_dict(saved["model"])
    model.eval()
    return model, saved["chars"], saved["roles"]


@torch.no_grad()
def choose_action(model, goal, rows, blocked, chars, roles):
    """Return the index to pass to env.step."""
    sample = encode(goal, rows, blocked, chars, roles)
    best = model(collate([sample]))[0].argmax().item()
    return sample["options"].tolist().index(best)
