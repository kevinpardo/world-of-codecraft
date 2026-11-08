"""Extend the baked village map north and south for the immersive layout, without touching it.

  uvx --with pillow --with numpy python tools/extend_world.py

The village (art/monde/jour-*.png, nuit-*.png: 3000x400 logical, PNG at 2x) stays exactly as baked.
This script paints two new bands around it from the village's own pixels and cut-outs:
  north (400 logical): a forest getting denser away from the village, the two dirt paths that leave the
    map continued, trees with cast shadows (light from the top left);
  south (400 logical): the fields continued on the left, the river flowing on down-left on the right, the
    paved square fading into grass below the market, scattered oaks, bushes and rocks;
  seams: a row of trees / bushes standing across each border hides the trees the bake cut at the edges
    (kept clear of the buildings' spires and of the paths).
Night versions come from a day->night colour map fitted on the baked day/night tiles.
Writes art/monde/{nord,sud}-{0,1,2}-{jour,nuit}.png (1000x400 logical each), lisiere-{nord,sud}-{jour,nuit}.png
(the seam overlays, 3000 wide) and terre-data.js.
"""
import json, os, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

MOD = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "mods", "world-of-codecraft")
MONDE = os.path.join(MOD, "art", "monde")
S = 2  # PNG pixels per logical px
W, H = 3000, 400  # the village, logical
EXT = 400  # each new band, logical
rng = random.Random(7)


def load_world(kind):
    im = Image.new("RGB", (W * S, H * S))
    for k in range(3):
        im.paste(Image.open(os.path.join(MONDE, f"{kind}-{k}.png")).convert("RGB"), (k * 1000 * S, 0))
    return im


day, night = load_world("jour"), load_world("nuit")
D = np.asarray(day).astype(np.float32)
N = np.asarray(night).astype(np.float32)


def cut(name, kind="jour"):
    return Image.open(os.path.join(MONDE, f"avant-{name}-{kind}.png")).convert("RGBA")


TREES = ["tree-pine", "tree-oak", "tree-oak-1", "tree-oak-2", "tree-autumn"]
SMALL = ["bush", "bush-1", "bush-2", "bush-3", "rocks", "rocks-1", "rocks-2"]
sprites = {n: cut(n) for n in TREES + SMALL if os.path.exists(os.path.join(MONDE, f"avant-{n}-jour.png"))}

# ------------------------------------------------------------------ texture samples

def is_grass(block):
    r, g, b = block[..., 0], block[..., 1], block[..., 2]
    green = (g > r + 4) & (g > b + 8)
    return green.mean() > 0.9 and block[..., :3].std() < 30


def find_patches(test, size=56, step=28, limit=80):
    """Logical windows of pure ground found by `test`, as 2x crops."""
    out = []
    for y in range(0, H - size, step):
        for x in range(0, W - size, step):
            blk = D[y * S:(y + size) * S, x * S:(x + size) * S]
            if test(blk):
                out.append(day.crop((x * S, y * S, (x + size) * S, (y + size) * S)))
    rng.shuffle(out)
    return out[:limit]


grass = find_patches(is_grass, size=40, step=20, limit=160)
print("grass patches:", len(grass))


def grass_mean(rows):
    """The mean colour of the grass in some rows of the village (to match the bands to it)."""
    blk = D[rows]
    r, g, b = blk[..., 0], blk[..., 1], blk[..., 2]
    m = (g > r + 4) & (g > b + 8)
    return blk[m].mean(0)


def match(im, target):
    """Shift a band's colours so its grass averages `target`."""
    a = np.asarray(im.convert("RGB")).astype(np.float32)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    m = (g > r + 4) & (g > b + 8)
    gain = target / np.maximum(1, a[m].mean(0))
    return Image.fromarray(np.clip(a * gain, 0, 255).astype(np.uint8))


def feather(band, edge_rows, at_bottom, depth=50):
    """Hide the border: the village's edge rows mirrored into the band, fading into it over `depth`."""
    d = depth * S
    src = day.crop((0, 0, W * S, d)) if at_bottom else day.crop((0, H * S - d, W * S, H * S))
    src = src.transpose(Image.FLIP_TOP_BOTTOM).filter(ImageFilter.GaussianBlur(7 * S))  # colours only, no reflections
    ramp = np.linspace(1, 0, d, dtype=np.float32) ** 1.4
    if at_bottom:
        ramp = ramp[::-1]
    mask = Image.fromarray((np.repeat(ramp[:, None], W * S, 1) * 255).astype(np.uint8))
    band.paste(src.convert("RGBA"), (0, band.height - d if at_bottom else 0), mask)


def synth(w, h, patches, size=40):
    """Ground: patches laid with jitter and feathered edges, so no seam or repeat shows."""
    base = Image.new("RGB", (w * S, h * S), tuple(int(c) for c in np.asarray(patches[0]).reshape(-1, 3).mean(0)))
    ps = size * S
    mask = Image.new("L", (ps, ps), 0)
    m = np.zeros((ps, ps), np.float32)
    yy, xx = np.mgrid[0:ps, 0:ps]
    edge = np.minimum.reduce([xx, yy, ps - 1 - xx, ps - 1 - yy]).astype(np.float32)
    m = np.clip(edge / (ps * 0.25), 0, 1)
    mask = Image.fromarray((m * 255).astype(np.uint8))
    step = int(size * 0.62) * S
    for y in range(-ps // 2, h * S, step):
        for x in range(-ps // 2, w * S, step):
            p = rng.choice(patches)
            if rng.random() < 0.5:
                p = p.transpose(Image.FLIP_LEFT_RIGHT)
            base.paste(p, (x + rng.randint(-8, 8), y + rng.randint(-8, 8)), mask)
    return base


# ------------------------------------------------------------------ painting helpers

def shadow(canvas, x, y, w):
    """A soft cast shadow at a trunk's foot, pushed down-right (light from the top left)."""
    sh = Image.new("L", (int(w * 1.1) + 20, int(w * 0.45) + 20), 0)
    ImageDraw.Draw(sh).ellipse((10, 10, sh.width - 10, sh.height - 10), fill=95)
    sh = sh.filter(ImageFilter.GaussianBlur(6))
    dark = Image.new("RGBA", sh.size, (20, 34, 18, 0))
    dark.putalpha(sh)
    canvas.alpha_composite(dark, (int(x - sh.width * 0.35), int(y - sh.height * 0.55)))


def place_sprite(canvas, name, fx, fy, oy=0, shade=True):
    """A cut-out standing with its foot at (fx, fy) in canvas pixels (2x); oy shifts the canvas origin."""
    sp = sprites[name]
    if rng.random() < 0.5 and not name.startswith("rocks"):
        sp = sp.transpose(Image.FLIP_LEFT_RIGHT)
    if shade and name in TREES:
        shadow(canvas, fx + sp.width * 0.15, fy + oy, sp.width * 0.8)
    canvas.alpha_composite(sp, (int(fx - sp.width / 2), int(fy + oy - sp.height + 4)))


def poisson(n, box, dmin, keep):
    pts = []
    tries = 0
    x0, y0, x1, y1 = box
    while len(pts) < n and tries < n * 60:
        tries += 1
        p = (rng.uniform(x0, x1), rng.uniform(y0, y1))
        if keep(p) and all((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2 > dmin ** 2 for q in pts):
            pts.append(p)
    return pts


def dist_to_poly(p, poly):
    best = 1e9
    for (ax, ay), (bx, by) in zip(poly, poly[1:]):
        dx, dy = bx - ax, by - ay
        t = max(0, min(1, ((p[0] - ax) * dx + (p[1] - ay) * dy) / (dx * dx + dy * dy)))
        best = min(best, ((p[0] - ax - t * dx) ** 2 + (p[1] - ay - t * dy) ** 2) ** 0.5)
    return best


def stroke(canvas, poly, width, tex, oy):
    """A band (path, river) along a polyline, filled with a texture crop, soft edges."""
    m = Image.new("L", canvas.size, 0)
    ImageDraw.Draw(m).line([(x * S, (y + oy) * S) for x, y in poly], fill=255, width=width * S, joint="curve")
    m = m.filter(ImageFilter.GaussianBlur(2 * S))
    fill = Image.new("RGB", canvas.size)
    tw, th = tex.size
    for y in range(0, canvas.height, th):
        for x in range(0, canvas.width, tw):
            fill.paste(tex, (x, y))
    canvas.paste(fill, (0, 0), m)
    return m


def crop(x, y, w, h):
    return day.crop((x * S, y * S, (x + w) * S, (y + h) * S))


# ------------------------------------------------------------------ north: forest and paths

SPIRES = [560, 1235, 2000, 2490]  # building tops near the north edge: keep the seam row clear
PATHS_N = [[(905, 0), (880, -120), (930, -260), (900, -400)], [(2455, 0), (2430, -150), (2480, -280), (2450, -400)]]
dirt = crop(2440, 4, 26, 22)

north = match(synth(W, EXT, grass), grass_mean(slice(0, 24 * S))).convert("RGBA")
feather(north, None, at_bottom=True)
for poly in PATHS_N:
    stroke(north, poly, 34, dirt, EXT)
trees_n = poisson(900, (0, -EXT + 10, W, 10), 34,
                  lambda p: min(dist_to_poly(p, poly) for poly in PATHS_N) > 42 and rng.random() < (0.0 if p[1] > -40 else 0.12 + 0.88 * ((-p[1] - 40) / (EXT - 40)) ** 0.8))
for fx, fy in sorted(trees_n, key=lambda p: p[1]):
    name = rng.choice(["tree-pine", "tree-pine", "tree-oak", "tree-oak-1", "tree-oak-2"] + (["tree-autumn"] if rng.random() < 0.15 else []))
    place_sprite(north, name, fx * S, fy * S, oy=EXT * S)

# ------------------------------------------------------------------ south: fields, river, square, meadow

def spline(pts, n=24):
    """A smooth curve through points (Catmull-Rom)."""
    P = [pts[0]] + pts + [pts[-1]]
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for k in range(n):
            t = k / n
            out.append(tuple(0.5 * ((2 * p1[j]) + (-p0[j] + p2[j]) * t + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t * t
                                     + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t ** 3) for j in range(2)))
    return out + [pts[-1]]


RIVER = spline([(2820, 396), (2735, 470), (2650, 560), (2580, 680), (2500, 806)])
water = crop(2880, 340, 30, 20)

south = match(synth(W, EXT, grass), grass_mean(slice((H - 24) * S, H * S))).convert("RGBA")
feather(south, None, at_bottom=False)
# the river: dark bank, then the water
stroke(south, RIVER, 132, crop(2700, 300, 20, 14), -H)
stroke(south, RIVER, 112, water, -H)
trees_s = poisson(110, (0, 40, W, EXT - 6), 80,
                  lambda p: dist_to_poly(p, RIVER) > 90 and rng.random() < 0.2 + 0.5 * (p[1] / EXT))
for fx, fy in sorted(trees_s, key=lambda p: p[1]):
    r = rng.random()
    name = rng.choice(["tree-oak", "tree-oak-1", "tree-oak-2", "tree-autumn"]) if r < 0.3 else rng.choice(SMALL)
    place_sprite(south, name, fx * S, fy * S)

# ------------------------------------------------------------------ seams

SEAM_UP, SEAM_DOWN = 240, 80  # the seam overlays span border - 240 .. border + 80 (tall trees fit)


def seam(y_border, y_from, y_to, names, avoid):
    """An overlay band standing across a border: things rooted near it, drawn over both sides."""
    band = Image.new("RGBA", (W * S, (SEAM_UP + SEAM_DOWN) * S), (0, 0, 0, 0))
    pts = poisson(140, (0, y_from, W, y_to), 40, lambda p: all(abs(p[0] - a) > r for a, r in avoid))
    for fx, fy in sorted(pts, key=lambda p: p[1]):
        place_sprite(band, rng.choice(names), fx * S, (fy - (y_border - SEAM_UP)) * S)
    return band


seam_n = seam(0, 8, 46, ["tree-pine", "tree-oak", "tree-oak-1", "tree-oak-2"],
              [(x, 95) for x in SPIRES] + [(905, 50), (2455, 50), (735, 80)])
seam_s = seam(400, 404, 436, ["bush", "bush-1", "bush-2", "bush-3", "rocks", "rocks-1"],
              [(1420, 120), (1700, 150), (1880, 120), (960, 110), (2830, 150), (480, 250), (760, 50), (2120, 120)])

# ------------------------------------------------------------------ night: a colour map fitted on the bake

sample = np.random.default_rng(3).choice(D.shape[0] * D.shape[1], 200000, replace=False)
d = D.reshape(-1, 3)[sample]
n = N.reshape(-1, 3)[sample]
ok = n.sum(1) < d.sum(1)  # leave out the lit windows and glows
A = np.hstack([d[ok], np.ones((ok.sum(), 1))])
M, *_ = np.linalg.lstsq(A, n[ok], rcond=None)


def to_night(im):
    a = np.asarray(im.convert("RGBA")).astype(np.float32)
    rgb = a[..., :3].reshape(-1, 3)
    out = np.hstack([rgb, np.ones((rgb.shape[0], 1))]) @ M
    a[..., :3] = np.clip(out, 0, 255).reshape(a.shape[0], a.shape[1], 3)
    return Image.fromarray(a.astype(np.uint8), "RGBA")


# ------------------------------------------------------------------ write

for name, band in (("nord", north), ("sud", south)):
    for k in range(3):
        tile = band.crop((k * 1000 * S, 0, (k + 1) * 1000 * S, EXT * S))
        tile.convert("RGB").save(os.path.join(MONDE, f"{name}-{k}-jour.png"), optimize=True)
        to_night(tile).convert("RGB").save(os.path.join(MONDE, f"{name}-{k}-nuit.png"), optimize=True)
for name, band in (("nord", seam_n), ("sud", seam_s)):
    band.save(os.path.join(MONDE, f"lisiere-{name}-jour.png"), optimize=True)
    to_night(band).save(os.path.join(MONDE, f"lisiere-{name}-nuit.png"), optimize=True)
with open(os.path.join(MOD, "terre-data.js"), "w") as f:
    f.write("// Generated by tools/extend_world.py: the bands painted around the village (immersive layout), logical px.\n")
    f.write("// nord-k / sud-k tiles are 1000 x EXT; the seam overlays are 3000 wide, from border - seamUp to border + seamDown.\n")
    f.write("export const EXT = " + json.dumps({"nord": EXT, "sud": EXT, "tiles": [0, 1, 2], "seamUp": SEAM_UP, "seamDown": SEAM_DOWN}) + ";\n")
print("night map:\n", np.round(M, 3))
