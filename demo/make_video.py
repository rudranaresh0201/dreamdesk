"""Tweet video: real footage from the sandbox plus real results. Nothing is mocked: the app footage is a recording
of the sandbox's private screen (scripts/record_demo.sh, val split), the exploration graph is the first 100 real
clicks of seed 6, and the numbers come from experiments/*_results.md.

  .venv/bin/python demo/make_video.py --goal 7 --out demo/dreamdesk.mp4
"""
import argparse
import json
import pickle
import subprocess

import networkx as nx
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1920, 1080, 30
BG, FG, DIM = (11, 13, 18), (236, 239, 244), (138, 146, 160)
DREAM, MAP, RAND = (94, 214, 196), (246, 160, 82), (120, 128, 140)
GOOD, BAD = (110, 220, 130), (240, 100, 100)
FONT = "/usr/share/fonts/truetype/noto/NotoSans-{}.ttf"
_fonts = {}


def font(size, bold=False):
    k = (size, bold)
    if k not in _fonts:
        _fonts[k] = ImageFont.truetype(FONT.format("Bold" if bold else "Regular"), size)
    return _fonts[k]


def ease(x):
    x = min(1.0, max(0.0, x))
    return 1 - (1 - x) ** 3


def fade(c, a):
    return tuple(int(BG[i] + (c[i] - BG[i]) * a) for i in range(3))


def text(d, xy, s, size, color=FG, bold=False, a=1.0, anchor="la"):
    f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size) if s[:1] in "✓✗" else font(size, bold)
    d.text(xy, s, font=f, fill=fade(color, a), anchor=anchor)


def canvas():
    im = Image.new("RGB", (W, H), BG)
    return im, ImageDraw.Draw(im)


def clip_frames(path, start, end, n, crop=(890, 550)):
    """n frames evenly spread over [start, end] seconds of the recording, cropped to the app window."""
    dur = end - start
    fps = n / dur
    cmd = ["ffmpeg", "-loglevel", "error", "-ss", f"{start:.3f}", "-t", f"{dur:.3f}", "-i", path,
           "-vf", f"crop={crop[0]}:{crop[1]}:0:0,fps={fps:.5f}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    size = crop[0] * crop[1] * 3
    frames = [Image.frombytes("RGB", crop, raw[i:i + size]) for i in range(0, len(raw) - size + 1, size)]
    while len(frames) < n:
        frames.append(frames[-1])
    return frames[:n]


def events(folder, goal):
    start = float(open(f"{folder}/start.txt").read())
    ev = [json.loads(l) for l in open(f"{folder}/events.jsonl")]
    ev = [dict(e, t=e["t"] - start) for e in ev if e["goal"] == goal]
    return ev


def short(k):
    role, _, name = k.partition(": ")
    return (name or role).strip() or role


# ---------- scenes ----------

def s_title(n):
    for i in range(n):
        im, d = canvas()
        t = i / FPS
        text(d, (W // 2, 440), "I dropped a tiny agent into an app it had never seen.", 64, bold=True,
             a=ease(t / 0.6), anchor="mm")
        text(d, (W // 2, 560), "No LLM.  No human.  No GPU.", 48, DREAM, a=ease((t - 1.2) / 0.6), anchor="mm")
        yield im


def explore_graph(path, clicks=100):
    data = pickle.load(open(path, "rb"))
    tr = data["transitions"]["train"][:clicks]
    g = nx.DiGraph()
    for k, t in enumerate(tr):
        g.add_edge(t[0], t[4], k=k)
    pos = nx.spring_layout(g.to_undirected(), seed=3, k=0.35, iterations=200)
    xy = np.array(list(pos.values()))
    lo, hi = xy.min(0), xy.max(0)
    box = (1060, 140, 1820, 940)
    pos = {n: (box[0] + (p[0] - lo[0]) / (hi[0] - lo[0]) * (box[2] - box[0]),
               box[1] + (p[1] - lo[1]) / (hi[1] - lo[1]) * (box[3] - box[1])) for n, p in pos.items()}
    return tr, pos


def s_explore(n, tr, pos):
    grow = int(n * 0.62)
    for i in range(n):
        im, d = canvas()
        t = i / FPS
        k = min(len(tr), int(len(tr) * i / grow) + 1)
        seen = set()
        for j, e in enumerate(tr[:k]):
            a, b = pos[e[0]], pos[e[4]]
            d.line([a, b], fill=fade(DREAM, 0.35 if j < k - 1 else 1.0), width=2 if j < k - 1 else 4)
            seen |= {e[0], e[4]}
        for s in seen:
            x, y = pos[s]
            d.ellipse([x - 7, y - 7, x + 7, y + 7], fill=DREAM)
        x, y = pos[tr[k - 1][4]]
        d.ellipse([x - 16, y - 16, x + 16, y + 16], outline=FG, width=3)
        text(d, (120, 330), "First it explores.", 60, bold=True, a=ease(t / 0.5))
        text(d, (120, 420), "Random clicks in the real app:", 40, DIM, a=ease(t / 0.5))
        text(d, (120, 480), f"{k} / 100", 120, DREAM, bold=True, a=ease(t / 0.5))
        text(d, (120, 640), f"{len(seen)} screens found", 40, DIM, a=ease(t / 0.5))
        b = ease((i - grow) / (FPS * 0.6))
        text(d, (120, 760), "Then it trains a model of the app", 44, FG, a=b)
        text(d, (120, 820), "in its head. A dream.", 44, DREAM, bold=True, a=b)
        yield im


def chip(d, x, y, s, size=36, color=FG, a=1.0, box=DIM):
    w = d.textlength(s, font=font(size, True))
    d.rounded_rectangle([x, y, x + w + 48, y + size + 34], radius=14, outline=fade(box, a), width=3)
    text(d, (x + 24, y + 14), s, size, color, bold=True, a=a)
    return x + w + 48


def s_task(n, keys):
    for i in range(n):
        im, d = canvas()
        t = i / FPS
        text(d, (W // 2, 300), "Now a task it has never seen:", 56, bold=True, a=ease(t / 0.5), anchor="mm")
        text(d, (W // 2, 380), "make these show up on one screen", 40, DIM, a=ease(t / 0.5), anchor="mm")
        widths = [d.textlength(short(k), font=font(38, True)) + 48 for k in keys]
        x = (W - sum(widths) - 40 * (len(keys) - 1)) / 2
        for j, k in enumerate(keys):
            x = chip(d, x, 470, short(k), 38, a=ease((t - 0.6 - 0.25 * j) / 0.4)) + 40
        a = ease((t - 1.8) / 0.5)
        text(d, (W // 2, 660), "While exploring it saw each of these.", 40, FG, a=a, anchor="mm")
        text(d, (W // 2, 720), "Never all together.", 40, MAP, bold=True, a=a, anchor="mm")
        yield im


def panel(im, frame, x, y, w):
    h = int(frame.height * w / frame.width)
    im.paste(frame.resize((w, h), Image.LANCZOS), (x, y))
    return h


def s_split(n, keys, mframes, dframes, mev, dev, mt, dt):
    """Map (left) and dream (right) on the same goal, each in its own real recording. mt/dt: clip [start, end]."""
    pw, py = 900, 180
    mend = next(e for e in mev if e["ev"] == "end")
    dend = next(e for e in dev if e["ev"] == "end")
    dacts = [e for e in dev if e["ev"] == "act"]
    play = len(mframes)  # play both clips, then hold their last real frame with the outcome stamped
    for i in range(n):
        im, d = canvas()
        u = min(1.0, i / max(1, play - 1))
        k = min(i, play - 1)
        h = panel(im, mframes[k], 40, py, pw)
        panel(im, dframes[k], W - 40 - pw, py, pw)
        text(d, (40, 70), "THE MAP", 44, MAP, bold=True)
        text(d, (40, 125), "replays screens it memorised", 30, DIM)
        text(d, (W - 40 - pw, 70), "THE DREAM", 44, DREAM, bold=True)
        text(d, (W - 40 - pw, 125), "plans inside its model of the app", 30, DIM)
        # clocks: where each recording is now
        mnow = mt[0] + u * (mt[1] - mt[0])
        dnow = dt[0] + u * (dt[1] - dt[0])
        mclicks = sum(1 for e in mev if e["ev"] == "act" and e["t"] <= mnow)
        dclicks = sum(1 for e in dacts if e["t"] <= dnow)
        y = py + h + 30
        text(d, (40, y), f"clicks: {mclicks}", 34, FG, bold=True)
        text(d, (W - 40 - pw, y), f"clicks: {dclicks}", 34, FG, bold=True)
        # the dream's plan, as it was logged: the action it chose and what it imagined would newly appear
        if dclicks:
            e = dacts[dclicks - 1]
            prev = set(dacts[dclicks - 2]["imagined"] or []) if dclicks > 1 else None
            new = sorted(set(e["imagined"] or []) - prev) if prev is not None else []
            want = [short(k) for k in keys]
            new = list(dict.fromkeys([short(k) for k in new if short(k) in want] or [short(k) for k in new]))[:2]
            act = e["action"].replace("press ", "").replace("toggle button", "").replace("button", "").strip()
            text(d, (W - 40 - pw + 260, y), f"dream: press {act}", 32, DREAM)
            if new:
                text(d, (W - 40 - pw + 260, y + 50), "imagines: + " + ", + ".join(new), 32, DREAM)
        if i >= play - 1:  # both clips have reached the end of their episode
            a = ease((i - play + 1) / (FPS * 0.3))
            for x0, e, mark in ((40, mend, "✗  lost after 10 clicks"), (W - 40 - pw, dend, "✓  done in 2 clicks")):
                ok = e["success"]
                mark = (f"✓  done in {e['steps']} clicks" if ok else f"✗  lost after {e['steps']} clicks")
                c = GOOD if ok else BAD
                cx, cy = x0 + pw // 2, py + h - 80
                d.rounded_rectangle([cx - 330, cy - 50, cx + 330, cy + 50], radius=20, fill=fade((20, 22, 28), a),
                                    outline=fade(c, a), width=4)
                text(d, (cx, cy), mark, 52, c, bold=True, a=a, anchor="mm")
        text(d, (W // 2, H - 60), "real app, real clicks, played back at different speeds", 26, DIM, anchor="mm")
        yield im


def s_foresight(n):
    for i in range(n):
        im, d = canvas()
        t = i / FPS
        text(d, (W // 2, 200), "Bonus: the dream knows when it will fail.", 58, bold=True, a=ease(t / 0.5), anchor="mm")
        text(d, (W // 2, 280), "Before a single real click.", 40, DIM, a=ease(t / 0.5), anchor="mm")
        rows = [("dream says: never", 0.10, BAD), ("dream says: always", 0.87, GOOD)]
        for j, (lab, v, c) in enumerate(rows):
            a = ease((t - 0.8 - 0.6 * j) / 0.5)
            y = 420 + j * 190
            text(d, (300, y + 20), lab, 44, FG, bold=True, a=a)
            grow = ease((t - 1.0 - 0.6 * j) / 1.0)
            d.rectangle([800, y, 800 + int(800 * v * grow), y + 90], fill=fade(c, a))
            text(d, (820 + int(800 * v * grow), y + 45), f"{round(100 * v * grow)}% real success", 40, c, bold=True,
                 a=a, anchor="lm")
        text(d, (W // 2, 900), "1,770 real runs on sealed test data  ·  AUROC 0.88", 32, DIM, a=ease((t - 2.4) / 0.5),
             anchor="mm")
        yield im


def s_result(n):
    data = {"seen": [27.2, 43.3, 47.0], "combo": [9.1, 2.4, 13.9]}
    arms = [("random", RAND), ("map", MAP), ("dream", DREAM)]
    for i in range(n):
        im, d = canvas()
        t = i / FPS
        text(d, (W // 2, 120), "The map memorises. The dream holds up.", 62, bold=True, a=ease(t / 0.5), anchor="mm")
        base, scale = 860, 9
        for g, (kind, sub) in enumerate([("seen", "goal screen seen while exploring"),
                                          ("combo", "pieces seen, never together")]):
            gx = 330 + g * 760
            grow = ease((t - 0.6 - 1.4 * g) / 1.2)
            a = ease((t - 0.4 - 1.4 * g) / 0.4)
            for j, (arm, c) in enumerate(arms):
                v = data[kind][j]
                x = gx + j * 190
                top = base - int(v * scale * 1.4 * grow)
                d.rectangle([x, top, x + 140, base], fill=fade(c, a))
                text(d, (x + 70, top - 40), f"{v * grow:.0f}%", 40, c, bold=True, a=a, anchor="mm")
                text(d, (x + 70, base + 40), arm, 34, FG, a=a, anchor="mm")
            text(d, (gx + 260, base + 115), f"{kind} tasks", 40, FG, bold=True, a=a, anchor="mm")
            text(d, (gx + 260, base + 165), sub, 28, DIM, a=a, anchor="mm")
        a = ease((t - 3.6) / 0.6)
        text(d, (1350, 700), "below random", 26, MAP, bold=True, a=a, anchor="mm")
        yield im


def s_end(n):
    for i in range(n):
        im, d = canvas()
        t = i / FPS
        text(d, (W // 2, 440), "DreamDesk", 96, DREAM, bold=True, a=ease(t / 0.6), anchor="mm")
        text(d, (W // 2, 560), "an agent that dreams up the apps it uses", 44, FG, a=ease((t - 0.5) / 0.6), anchor="mm")
        text(d, (W // 2, 660), "no LLM  ·  $0  ·  one laptop", 36, DIM, a=ease((t - 1.0) / 0.6), anchor="mm")
        yield im


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--goal", type=int, required=True)
    ap.add_argument("--dream", default="runs/demo/planner")
    ap.add_argument("--map", default="runs/demo/graph")
    ap.add_argument("--explore", default="data/budget_s6/B100/files.pkl")
    ap.add_argument("--out", default="demo/dreamdesk.mp4")
    args = ap.parse_args()

    dev, mev = events(args.dream, args.goal), events(args.map, args.goal)
    keys = dev[0]["keys"]
    assert mev[0]["keys"] == keys, "map and dream recordings have different goals"
    pad = -0.35  # the app is closed about 0.15 s before the logged end (blackdetect); stop before that
    dt = (dev[0]["t"] + 0.2, next(e for e in dev if e["ev"] == "end")["t"] + pad)
    mt = (mev[0]["t"] + 0.2, next(e for e in mev if e["ev"] == "end")["t"] + pad)
    split_n = int(FPS * 11)
    play_n = int(FPS * 8.5)
    mframes = clip_frames(f"{args.map}/real.mp4", *mt, play_n)
    dframes = clip_frames(f"{args.dream}/real.mp4", *dt, play_n)
    tr, pos = explore_graph(args.explore)

    scenes = [s_title(int(FPS * 3.5)), s_explore(int(FPS * 6), tr, pos), s_task(int(FPS * 4), keys),
              s_split(split_n, keys, mframes, dframes, mev, dev, mt, dt), s_result(int(FPS * 7)),
              s_foresight(int(FPS * 5.5)), s_end(int(FPS * 3))]
    ff = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                           "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "slow", "-crf", "18",
                           "-pix_fmt", "yuv420p", "-movflags", "+faststart", args.out], stdin=subprocess.PIPE)
    count = 0
    for sc in scenes:
        for im in sc:
            ff.stdin.write(im.tobytes())
            count += 1
    ff.stdin.close()
    ff.wait()
    print(f"{args.out}: {count / FPS:.1f} s, {W}x{H}")


if __name__ == "__main__":
    main()
