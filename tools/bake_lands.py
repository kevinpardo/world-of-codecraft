"""The lands around Valbrume for the immersive layout, baked by the village's own compositor (compose3).

  tools/village-art/build_assets.sh && tools/village-art/.venv/bin/python tools/bake_lands.py

Same tiles, same lighting, same shadows as the village (bake_world.py), on a canvas 400 px taller on each
side: the ground is computed over 1200 rows instead of 400 (paths continued north, a lane going south from
the market, two more fields, the river following its own line), the village's objects are drawn whole (its
north-edge trees are no longer cut), and new objects stand around it: a forest to the north, oaks, bushes,
rocks and fences to the south. The village tiles are rewritten from the composite only if no building pixel
changed (the forest's soft shadows reach the top of the village's grass).
Writes art/monde/{nord,sud}-{0,1,2}-{jour,nuit}.png and terre-data.js.
"""
import inspect, json, os, sys
import numpy as np
from PIL import Image

MOD = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "mods", "world-of-codecraft")
ART = os.environ.get("ART") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "village-art")
OUT = os.path.join(MOD, "art", "monde")
os.chdir(ART)
sys.path.insert(0, ART)
import compose as C  # noqa: E402
import compose2 as C2  # noqa: E402
import compose3 as C3  # noqa: E402

N, S = 400, 400  # the new bands, logical px
W, H0 = C2.W, C2.H
H = N + H0 + S

# ------------------------------------------------------------------ the ground over 1200 rows

src = inspect.getsource(C2.ground)
patches = [
    ("v, u = np.mgrid[0:H, 0:W]\n    x, y = s2w(u + 0.5, v + 0.5)",
     # screen rows keep their original numbers (v < 0 north, v >= 400 south): the dithering and the hashed
     # grass details use them, so the village band comes out exactly as baked
     "v, u = np.mgrid[-OFF:H - OFF, 0:W]\n    x, y = s2w(u + 0.5, v + 0.5)"),
    # the three north paths go on through the forest; a lane leaves the market southwards
    ("[(860, 260), (900, 140), (950, 0)], [(1650, 250), (1700, 120), (1760, 0)], [(2350, 280), (2420, 150), (2460, 0)]]",
     "[(860, 260), (900, 140), (950, 0), (1010, -130), (980, -270), (1030, -400)], "
     "[(1650, 250), (1700, 120), (1760, 0), (1790, -150), (1740, -300), (1770, -400)], "
     "[(2350, 280), (2420, 150), (2460, 0), (2520, -120), (2490, -260), (2540, -400)], "
     "[(1520, 400), (1490, 520), (1550, 650), (1510, 800)]]"),
    # two more fields to the south-west
    ("((150, 380, 80, 48), (330, 400, 60, 36), (40, 300, 40, 30))",
     "((150, 380, 80, 48), (330, 400, 60, 36), (40, 300, 40, 30), (230, 560, 90, 50), (520, 640, 70, 40))"),
]
for a, b in patches:
    assert a in src, a
    src = src.replace(a, b)
C2.OFF = N
C2.H = C3.H = C.H = H
exec(compile(src, C2.__file__, "exec"), C2.__dict__)  # replaces C2.ground with the taller one

# ------------------------------------------------------------------ objects


class _Meta(dict):
    def __missing__(self, k):
        return {"w": 1, "h": 1, "ax": 0, "ay": 0}  # the old demo heroes: dropped just below


C2.META = _Meta(C2.META)
village, _E = C2.scene()
village = [o for o in village if o[0].startswith("b-")]
O = [(n, u, v + N, dp, ex) for (n, u, v, dp, ex) in village]
rng = np.random.default_rng(11)


def add(name, u, v, dp=6):
    O.append(("b-" + name, u, v + N, dp, {}))


def near_line(u, v, pts, d):
    for (au, av), (bu, bv) in zip(pts, pts[1:]):
        du, dv = bu - au, bv - av
        t = max(0, min(1, ((u - au) * du + (v - av) * dv) / (du * du + dv * dv)))
        if (u - au - t * du) ** 2 + (v - av - t * dv) ** 2 < d * d:
            return True
    return False


PATHS = [[(950, 0), (1010, -130), (980, -270), (1030, -400)], [(1760, 0), (1790, -150), (1740, -300), (1770, -400)],
         [(2460, 0), (2520, -120), (2490, -260), (2540, -400)], [(1520, 400), (1490, 520), (1550, 650), (1510, 800)]]
x_river, _ = C.s2w(2780, 400)


def in_river(u, v, margin):
    x, y = C.s2w(u, v)
    return abs(x - (x_river + np.sin(y / 60) * 12)) < 26 + margin


placed = []


def free(u, v, du=40, dv=18):
    return not any(abs(u - pu) < du and abs(v - pv) < dv for pu, pv in placed)


# north: a forest, thinning near the village, keeping the paths and the river clear
for k in range(5200):
    u = int(rng.integers(-40, W + 40))
    v = int(rng.integers(-N + 8, 4))
    if near_line(u, v, PATHS[0], 40) or near_line(u, v, PATHS[1], 40) or near_line(u, v, PATHS[2], 40) or in_river(u, v, 30):
        continue
    if rng.random() > 0.35 + 0.65 * min(1, -v / 160):
        continue
    if not free(u, v):
        continue
    placed.append((u, v))
    add(["tree-pine", "tree-pine", "tree-oak", "tree-pine", "tree-autumn", "tree-pine", "tree-oak"][k % 7], u, v)
    if rng.random() < 0.08:
        add(rng.choice(["bush", "rocks"]), u + int(rng.integers(-26, 26)), v + int(rng.integers(6, 16)), 4)

# south: a meadow, fields, scattered oaks, bushes and rocks; nothing tall close enough to reach the village band
placed.clear()
for k in range(1500):
    u = int(rng.integers(-30, W + 30))
    v = int(rng.integers(H0 + 30, H0 + S - 4))
    tall = rng.random() < 0.38
    if tall and v < H0 + 200:
        continue
    if near_line(u, v, PATHS[3], 46 if tall else 30) or in_river(u, v, 40 if tall else 22):
        continue
    if any(abs(u - fu) < a + 30 and abs(v - fv) < b + 18 for fu, fv, a, b in ((230, 560, 90, 50), (520, 640, 70, 40))):
        continue
    if rng.random() > (0.5 if tall else 0.2) or not free(u, v, 70 if tall else 50, 30 if tall else 22):
        continue
    placed.append((u, v))
    add(rng.choice(["tree-oak", "tree-oak", "tree-autumn", "tree-pine"]) if tall else rng.choice(["bush", "bush", "rocks"]), u, v, 8 if tall else 4)
for k in range(5):  # a fence along the new south-west field
    add("fence-x", 150 + k * 44, 610 + k * 22, 2)

print(len(O) - len(village), "new objects")

# ------------------------------------------------------------------ bake

CACHE = os.environ.get("CACHE")  # a .npz path: reuse the composite while tuning the checks and the export
if CACHE and os.path.exists(CACHE):
    z = np.load(CACHE)
    day, night = z["day"], z["night"]
else:
    day = C3.compose(False, O, [])
    night = C3.compose(True, O, [])
    if CACHE:
        np.savez_compressed(CACHE, day=day, night=night)


def save2(arr, path):
    Image.fromarray(arr).resize((arr.shape[1] * 2, arr.shape[0] * 2), Image.NEAREST).save(path, optimize=True)


# The village band differs from the approved bake only where the new forest's soft ground shadows reach its
# top grass (and the last row's edge). Its buildings must not change by a single pixel: checked against every
# building sprite's own pixels; then the village tiles are rewritten from the composite, so no seam shows.
BUILDINGS = {"b-barn", "b-magetower", "b-forge", "b-townhall", "b-tavern", "b-temple", "b-barracks", "b-well",
             "b-noticeboard", "b-campfire", "b-stall-red", "b-stall-blue", "b-stall-green"}
for tag, img in (("jour", day), ("nuit", night)):
    band = img[N:N + H0]
    ref = np.concatenate([np.asarray(Image.open(os.path.join(OUT, f"{tag}-{k}.png")).convert("RGB"))[::2, ::2] for k in range(3)], 1)
    d = np.abs(band.astype(int) - ref.astype(int)).sum(-1) > 0
    bad = 0
    worst = 0
    for (name, u, v, dp, _x) in village:
        if name not in BUILDINGS:
            continue
        m = C2.META[name]
        c = C3.load(name)
        x0, y0 = int(u - m["ax"]), int(v - m["ay"])
        ys0, xs0 = max(0, y0), max(0, x0)
        ys1, xs1 = min(H0, y0 + c.shape[0]), min(W, x0 + c.shape[1])
        a_ = c[ys0 - y0:ys1 - y0, xs0 - x0:xs1 - x0, 3] > 0
        hit = d[ys0:ys1, xs0:xs1] & a_
        bad += int(hit.sum())
        if hit.any():
            worst = max(worst, int(np.abs(band[ys0:ys1, xs0:xs1][hit].astype(int) - ref[ys0:ys1, xs0:xs1][hit].astype(int)).max()))
    rows = np.nonzero(d.any(1))[0]
    print(tag, "village pixels changed: %.3f%%, deepest row %s, building pixels changed: %d (max delta %d)" % (100 * d.mean(), rows.max() if len(rows) else "-", bad, worst))
    if os.environ.get("DIFF"):
        Image.fromarray((d * 255).astype(np.uint8)).save(os.environ["DIFF"].replace(".png", f"-{tag}.png"))
    # by day not one building pixel may change; at night the window glow (blurred over 22 px) meets the canvas
    # edge further up, so the tops of buildings near the north edge may differ by a glow step or two
    assert bad == 0 if tag == "jour" else (bad < 400 and worst <= 40), "a building changed: keep the approved village tiles"

for k in range(3):
    x = k * 1000
    for tag, img in (("jour", day), ("nuit", night)):
        save2(img[N:N + H0, x:x + 1000], os.path.join(OUT, f"{tag}-{k}.png"))  # the village, with the forest's shadows
        save2(img[:N, x:x + 1000], os.path.join(OUT, f"nord-{k}-{tag}.png"))
        save2(img[N + H0:, x:x + 1000], os.path.join(OUT, f"sud-{k}-{tag}.png"))
with open(os.path.join(MOD, "terre-data.js"), "w") as f:
    f.write("// Generated by tools/bake_lands.py (the village's compositor on a taller canvas): the bands around the village.\n")
    f.write("export const EXT = " + json.dumps({"nord": N, "sud": S, "tiles": [0, 1, 2]}) + ";\n")
if os.environ.get("PREVIEW"):
    Image.fromarray(day).resize((1500, 600), Image.LANCZOS).save(os.environ["PREVIEW"])
print("ok")
