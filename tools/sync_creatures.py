"""Cut the validated creature sheets (tools/sources/) into the mod's sprites. Re-runnable.

  uvx --with pillow --with numpy python tools/sync_creatures.py

Sources (GPT Image 2.6, 08/11/2026, style ref = tools/sources/ref-style.png):
  creatures-planche-1.png   3 rows (imp, wolf, goblin) x 3 poses (ready, attack, hit) on flat green
  corbeau.png               row 1: 4 flight frames, row 2: perched, cawing (optional)
Writes art/creatures/<name>/<pose>{,-g}{,-n}.png at 2x (1 art px = 1 logical px; -g = mirrored to face
right, -n = night grade) and creatures-data.js (logical w, h and feet anchor per sprite).
"""
import json, os
import numpy as np
from PIL import Image

MOD = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "mods", "world-of-codecraft")
SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sources")
OUT = os.path.join(MOD, "art", "creatures")

# name -> (sheet, rows, cols, row, logical height, poses by column)
CREATURES = {
    "diablotin": ("creatures-planche-1.png", 3, 3, 0, 46, ["pret", "attaque", "touche"]),
    "loup": ("creatures-planche-1.png", 3, 3, 1, 40, ["pret", "attaque", "touche"]),
    "gobelin": ("creatures-planche-1.png", 3, 3, 2, 56, ["pret", "attaque", "touche"]),
    # Lot 2 (08/11/2026)
    "sanglier": ("creatures-planche-2.png", 3, 3, 0, 40, ["pret", "attaque", "touche"]),
    "golem": ("creatures-planche-2.png", 3, 3, 1, 50, ["pret", "attaque", "touche"]),
    "spectre": ("creatures-planche-2.png", 3, 3, 2, 54, ["pret", "attaque", "touche"]),
    "troll": ("creatures-planche-3.png", 3, 3, 0, 92, ["pret", "attaque", "touche"]),
    "mannequin": ("creatures-planche-3.png", 3, 3, 1, 46, ["pret", "touche", "abattu"]),
    "pigeon": ("creatures-planche-3.png", 3, 3, 2, 26, ["vol0", "vol1", "perche"]),
    # Lot 3 (08/11/2026): village life. None = a column to skip; the scale comes from the first used one.
    "paysanne": ("ambiance-1.png", 4, 2, 0, 60, ["debout", "pas"]),
    "fermier": ("ambiance-1.png", 4, 2, 1, 62, ["debout", "pas"]),
    "garde": ("ambiance-1.png", 4, 2, 2, 66, ["debout", "pas"]),
    "marchand": ("ambiance-1.png", 4, 2, 3, 64, ["debout", "pas"]),
    "poule": ("ambiance-2.png", 4, 2, 0, 17, ["debout", "picore"]),
    "chat": ("ambiance-2.png", 4, 2, 1, 17, ["assis", "marche"]),
    "cerf": ("ambiance-2.png", 4, 2, 2, 38, ["broute", "alerte"]),
    "moineau": ("ambiance-2.png", 4, 3, 3, 11, ["vol0", "vol1", None]),
    "poisson": ("ambiance-2.png", 4, 3, 3, 22, [None, None, "saut"]),
}
RAVEN = ("corbeau.png", 24)  # logical height of a flying frame


def night(im):
    """Same grade as sync_heroes.py (the world's night, softened so units stay readable)."""
    a = np.asarray(im.convert("RGBA")).astype(np.float32)
    rgb = a[..., :3]
    lum = rgb @ np.array([0.3, 0.55, 0.15], np.float32)
    nc = rgb * np.array([0.20, 0.25, 0.46]) + lum[..., None] * np.array([0.05, 0.07, 0.16]) + np.array([6, 9, 26])
    a[..., :3] = np.clip(nc * 0.62 + rgb * np.array([0.42, 0.46, 0.62]) * 0.38, 0, 255)
    return Image.fromarray(a.astype(np.uint8), "RGBA")


def keyed(path):
    """The sheet with its flat background made transparent (colour distance to the corner pixel)."""
    a = np.asarray(Image.open(path).convert("RGBA")).astype(np.int32).copy()
    d = np.abs(a[..., :3] - a[4, 4, :3]).sum(-1)
    a[..., 3] = np.where(d < 46, 0, 255)
    return Image.fromarray(a.astype(np.uint8), "RGBA")


GRAIN = {"ambiance-1.png": 4}  # finer grouping where sprites nearly touch (pitchfork vs spear)


def components(sheet, k=12):
    """Bounding boxes of the sprites in a keyed sheet: opaque pixels grouped by a coarse grid flood."""
    a = np.asarray(sheet)[..., 3] > 0
    H, W = a.shape
    # k = coarse cell: merges a sprite's detached bits (sparks, claws)
    g = a[: H // k * k, : W // k * k].reshape(H // k, k, W // k, k).any(axis=(1, 3))
    seen = np.zeros_like(g)
    boxes = []
    for y in range(g.shape[0]):
        for x in range(g.shape[1]):
            if g[y, x] and not seen[y, x]:
                st, pts = [(y, x)], []
                seen[y, x] = True
                while st:
                    cy, cx = st.pop()
                    pts.append((cy, cx))
                    for dy in (-1, 0, 1):
                        for dx in (-1, 0, 1):
                            ny, nx = cy + dy, cx + dx
                            if 0 <= ny < g.shape[0] and 0 <= nx < g.shape[1] and g[ny, nx] and not seen[ny, nx]:
                                seen[ny, nx] = True
                                st.append((ny, nx))
                ys, xs = zip(*pts)
                if len(pts) > 20:
                    boxes.append((min(xs) * k, min(ys) * k, (max(xs) + 1) * k, (max(ys) + 1) * k))
    return boxes


def cell_boxes(sheet, rows, cols, k=12):
    """Sprites sorted into a rows x cols grid by their centres."""
    W, H = sheet.size
    grid = {}
    for b in components(sheet, k):
        cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
        r, c = int(cy / H * rows), int(cx / W * cols)
        old = grid.get((r, c))
        if old is None or (b[2] - b[0]) * (b[3] - b[1]) > (old[2] - old[0]) * (old[3] - old[1]):
            grid[(r, c)] = b
    return grid


def shrink(im, h2):
    """Down to h2 px tall (2x file), crisp alpha."""
    im = im.crop(im.getbbox())
    w2 = max(1, round(im.width * h2 / im.height))
    out = im.resize((w2, h2), Image.LANCZOS)
    a = np.asarray(out).copy()
    a[..., 3] = np.where(a[..., 3] > 110, 255, 0)
    return Image.fromarray(a, "RGBA")


def save(im, d, name):
    os.makedirs(d, exist_ok=True)
    for flip in (False, True):
        x = im.transpose(Image.FLIP_LEFT_RIGHT) if flip else im
        base = os.path.join(d, name + ("-g" if flip else ""))
        x.save(base + ".png", optimize=True)
        night(x).save(base + "-n.png", optimize=True)


def main():
    data = {}
    sheets = {}
    for name, (sheet, rows, cols, row, lh, poses) in CREATURES.items():
        if not os.path.exists(os.path.join(SRC, sheet)):
            print("missing", sheet)
            continue
        key = (sheet, rows, cols)
        if key not in sheets:
            sk = keyed(os.path.join(SRC, sheet))
            sheets[key] = (sk, cell_boxes(sk, rows, cols, GRAIN.get(sheet, 12)))
        sk, grid = sheets[key]
        # one scale for the creature: its first pose is lh tall, the others keep their proportion
        ref = grid[(row, next(c for c, p in enumerate(poses) if p))]
        k = (lh * 2) / (ref[3] - ref[1])
        data[name] = {}
        for c, pose in enumerate(poses):
            if not pose:
                continue
            b = grid[(row, c)]
            im = shrink(sk.crop(b), max(2, round((b[3] - b[1]) * k)))
            save(im, os.path.join(OUT, name), pose)
            w, h = im.width // 2, im.height // 2
            data[name][pose] = {"w": w, "h": h, "ax": w // 2, "ay": h - 1}
    rp = os.path.join(SRC, RAVEN[0])
    if os.path.exists(rp):
        sk = keyed(rp)
        boxes = sorted(components(sk), key=lambda b: (round((b[1] + b[3]) / 2 / (sk.height / 2)), b[0]))
        names = ["vol0", "vol1", "vol2", "vol3", "perche", "croasse"]
        top = [b for b in boxes if (b[1] + b[3]) / 2 < sk.height / 2][:4]
        bot = [b for b in boxes if (b[1] + b[3]) / 2 >= sk.height / 2][:2]
        hmax = max(b[3] - b[1] for b in top)
        k = (RAVEN[1] * 2) / hmax
        data["corbeau"] = {}
        for n, b in zip(names, top + bot):
            im = shrink(sk.crop(b), max(2, round((b[3] - b[1]) * k)))
            save(im, os.path.join(OUT, "corbeau"), n)
            w, h = im.width // 2, im.height // 2
            data["corbeau"][n] = {"w": w, "h": h, "ax": w // 2, "ay": h - 1}
    with open(os.path.join(MOD, "creatures-data.js"), "w") as f:
        f.write("// Generated by tools/sync_creatures.py: creature sprites in art/creatures/ (logical px, feet anchor).\n")
        f.write("// Files: <pose>.png faces left, <pose>-g.png faces right, -n = night.\n")
        f.write("export const CREATURES = " + json.dumps(data) + ";\n")
    print(json.dumps(data, indent=1))


if __name__ == "__main__":
    main()
