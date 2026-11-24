#!/usr/bin/env python3
"""Writes mirrored day frames (NN.png -> NN-g.png, facing right) of the poses the dungeon draws
(idle, work, rest) for every hero in mods/world-of-codecraft/art/heros/. Safe to rerun after sync_heroes.py.

  tools/village-art/.venv/bin/python tools/mirror_heroes.py
"""
import glob
import os
import re

from PIL import Image, ImageOps

HEROES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "mods", "world-of-codecraft", "art", "heros")
POSES = ("idle", "work", "rest")

n = size = 0
for pose in POSES:
    for src in sorted(glob.glob(os.path.join(HEROES, "*", pose, "*.png"))):
        if not re.fullmatch(r"\d+\.png", os.path.basename(src)):
            continue
        dst = src[:-4] + "-g.png"
        ImageOps.mirror(Image.open(src).convert("RGBA")).save(dst, optimize=True)
        n += 1
        size += os.path.getsize(dst)
print(f"{n} mirrored frames, {size / 1024:.0f} KiB")
