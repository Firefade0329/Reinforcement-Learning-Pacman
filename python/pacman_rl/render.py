"""Episode replays as GIFs (numpy + Pillow only, no display needed)."""
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from . import maps
from .env import PacmanEnv

CELL = 14
COLORS = {"bg": (0, 0, 0), "wall": (40, 40, 200), "gold": (255, 220, 60), "pac": (255, 235, 0), "ghost": (235, 50, 50)}


def draw_frame(env: PacmanEnv, text: str) -> Image.Image:
    img = Image.new("RGB", (maps.W * CELL, maps.H * CELL + 16), COLORS["bg"])
    d = ImageDraw.Draw(img)
    for y in range(maps.H):
        for x in range(maps.W):
            if maps.WALL[y, x]:
                d.rectangle([x * CELL, y * CELL, (x + 1) * CELL - 1, (y + 1) * CELL - 1], fill=COLORS["wall"])
    for c in np.flatnonzero(env.gold):
        x, y = int(maps.CELL_X[c]), int(maps.CELL_Y[c])
        d.ellipse([x * CELL + 5, y * CELL + 5, x * CELL + 8, y * CELL + 8], fill=COLORS["gold"])
    for g in env.ghosts:
        x, y = int(maps.CELL_X[g]), int(maps.CELL_Y[g])
        d.rectangle([x * CELL + 1, y * CELL + 1, (x + 1) * CELL - 2, (y + 1) * CELL - 2], fill=COLORS["ghost"])
    x, y = int(maps.CELL_X[env.agent]), int(maps.CELL_Y[env.agent])
    d.ellipse([x * CELL + 1, y * CELL + 1, (x + 1) * CELL - 2, (y + 1) * CELL - 2], fill=COLORS["pac"])
    d.text((3, maps.H * CELL + 2), text, fill=(255, 255, 255))
    return img


def record(act, cfg, seed: int, path: Path, label: str, max_steps: int = 1000, every: int = 2):
    """``act(env) -> action``.  Writes a GIF; returns (score, steps, died, won)."""
    env = PacmanEnv(cfg)
    env.reset(seed)
    frames = [draw_frame(env, f"{label}  seed {seed}  score 0")]
    info = {"score": 0, "steps": 0, "died": False, "won": False}
    done = False
    while not done and env.steps < max_steps:
        _, _, term, trunc, info = env.step(int(act(env)))
        done = term or trunc
        if env.steps % every == 0 or done:
            tag = " DIED" if info.get("died") else (" WON" if info.get("won") else "")
            frames.append(draw_frame(env, f"{label}  seed {seed}  step {env.steps}  score {env.score}{tag}"))
    frames += [frames[-1]] * 10
    path.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(path, save_all=True, append_images=frames[1:], duration=60, loop=0, optimize=True)
    return info["score"], info["steps"], bool(info.get("died")), bool(info.get("won"))
