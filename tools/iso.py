#!/usr/bin/env python3
"""Isometric pixel art for Valbrume (mods/world-of-codecraft/art).
- terrain.png: the whole village ground baked (grass, paths, square, river, fields, trees),
  1000x170 art px upscaled x4 (2 logical px per art px on a 2x screen).
- iso-*.svg (+ -nuit.svg lights): buildings, and iso.js: their placement manifest.
Projection: tile (i, j) centre at (CX + (i-j)*16, CY + (i+j)*8); 16 'units' per tile edge."""
import os, sys, zlib, struct, math, json, random

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen import Px, OUTLINE

OUT = os.path.expanduser("~/.config/herdr-app/mods/world-of-codecraft/art")
MOD = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "mods", "world-of-codecraft")
W, H = 1000, 200
CX, CY = 500, 110
UP = 4


def hx(*a):
    h = 2166136261
    for ch in repr(a):
        h = ((h ^ ord(ch)) * 16777619) & 0xFFFFFFFF
    h ^= h >> 16; h = (h * 0x7feb352d) & 0xFFFFFFFF; h ^= h >> 15
    return h


def rgb(c):
    return tuple(int(c[k:k + 2], 16) for k in (1, 3, 5))


def shade(c, f):
    r, g, b = rgb(c) if isinstance(c, str) else c
    return "#%02x%02x%02x" % tuple(max(0, min(255, int(v * f))) for v in (r, g, b))


def write_png(path, px, w, h, up):
    raw = bytearray()
    for y in range(h):
        row = bytearray()
        for x in range(w):
            c = px[y][x]
            row += bytes(rgb(c)) * up
        line = b"\x00" + bytes(row)
        raw += line * up
    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w * up, h * up, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 9)) + chunk(b"IEND", b"")
    open(path, "wb").write(png)


# ------------------------------------------------------------------ world plan (tile coords)

BUILDINGS = {
    # name: (i0, j0, a, b)  back corner tile and footprint in tiles
    "hotel": (-2, -2, 4, 4),
    "tour": (-6, 6, 2, 2),
    "atelier": (-13, 9, 3, 3),
    "caserne": (5, -10, 4, 3),
    "temple": (11, -12, 3, 3),
    "taverne": (-7, 0, 3, 3),
    "grange": (-2, 6, 3, 2),
    "etal1": (6, 1, 2, 1),
    "etal2": (8, -1, 2, 1),
    "etal3": (5, 3, 1, 2),
    "panneau": (4, -3, 1, 1),
    "puits": (-4, 2, 1, 1),
}
RIVER_I = (16, 17)
FIELDS = [(-4, 9, 3, 4), (-8, 12, 3, 3)]


def door(name):
    i0, j0, a, b = BUILDINGS[name]
    return i0 + a // 2, j0 + b  # tile in front of the left face's middle


def tile_type(i, j):
    if i in RIVER_I:
        return "eau"
    for (i0, j0, a, b) in FIELDS:
        if i0 <= i < i0 + a and j0 <= j < j0 + b:
            return "champ"
    if -4 <= i <= 4 and -4 <= j <= 4:
        return "place"
    return "herbe"


def paths():
    p = set()
    def line(i0, j0, i1, j1):
        i, j = i0, j0
        while i != i1:
            p.add((i, j)); i += 1 if i1 > i else -1
        while j != j1:
            p.add((i, j)); j += 1 if j1 > j else -1
        p.add((i, j))
    # from each building door to the square
    for n in ("tour", "atelier", "caserne", "temple", "taverne", "grange"):
        di, dj = door(n)
        line(di, dj, max(-4, min(4, di)), max(-4, min(4, dj)))
    # the road across the village, over the bridge
    line(-26, 0, 30, 0)
    line(0, -24, 0, 24)
    return p


# ------------------------------------------------------------------ terrain

def terrain():
    px = [[None] * W for _ in range(H)]
    P = paths()
    tiles = {}
    for y in range(H):
        for x in range(W):
            u = (x + 0.5 - CX) / 16
            v = (y + 0.5 - CY) / 8
            fi, fj = (v + u) / 2, (v - u) / 2
            i, j = round(fi), round(fj)
            di, dj = fi - i, fj - j
            t = tile_type(i, j)
            if t == "herbe" and (i, j) in P:
                t = "chemin"
            if t == "eau" and (i, j) in P:
                t = "pont"
            h = hx(i, j)
            n = hx(x, y) % 100
            if t == "herbe":
                base = ["#5f9a3f", "#5a943b", "#64a044", "#578f39"][h % 4]
                c = base
                if n < 7: c = shade(base, 1.14)
                elif n < 13: c = shade(base, 0.88)
                if (h >> 8) % 23 == 0 and n < 30: c = ["#e8d26a", "#f2f2f2", "#d77ac2"][(h >> 3) % 3]
            elif t == "chemin":
                base = "#a07a4e"
                c = base if n > 12 else shade(base, 0.86 if n < 6 else 1.1)
                if abs(di) > 0.42 or abs(dj) > 0.42:
                    # soft grassy border unless the neighbour is path too
                    ni, nj = i + (1 if di > 0.42 else -1 if di < -0.42 else 0), j + (1 if dj > 0.42 else -1 if dj < -0.42 else 0)
                    if (ni, nj) not in P and tile_type(ni, nj) == "herbe" and n < 55:
                        c = "#6e8f45"
            elif t == "place":
                # paving stones: 2x2 per tile, mortar lines
                si, sj = (fi + 0.5) * 2, (fj + 0.5) * 2
                stone = hx(math.floor(si), math.floor(sj)) % 4
                c = ["#9a948c", "#a8a298", "#8f8a83", "#b0aa9f"][stone]
                if (si % 1) < 0.1 or (sj % 1) < 0.1:
                    c = "#6d6862"
                if i == 0 and j == 0 or (abs(i) + abs(j) <= 1 and n < 0):
                    pass
            elif t == "champ":
                rows = (fj * 3) % 1
                c = "#7a5a32" if rows < 0.45 else ("#c9a640" if (h % 2 == 0) else "#7fae3e")
                if rows < 0.45 and n < 10: c = "#6a4c28"
            elif t == "eau":
                c = "#3f7fc4"
                wave = (x + 2 * y + (h % 7)) % 23
                if wave < 2: c = "#8fc6f0"
                elif wave < 5: c = "#5b9ad8"
                if (i == RIVER_I[0] and di < -0.38) or (i == RIVER_I[1] and di > 0.38):
                    c = "#7a6a4a"  # banks
            elif t == "pont":
                c = "#8a5a2b" if (fi * 4) % 1 > 0.15 else "#5a3a1e"
                if abs(dj) > 0.4: c = "#4a2e17"
            # subtle tile grid on grass and square
            if t in ("herbe",) and (di > 0.46 or dj > 0.46):
                c = shade(c, 0.93)
            px[y][x] = c
    return px


def stamp(px, sprite, ox, oy):
    for yy in range(sprite.h):
        for xx in range(sprite.w):
            c = sprite.g[yy][xx]
            if c is None:
                continue
            X, Y = ox + xx, oy + yy
            if 0 <= X < W and 0 <= Y < H:
                if len(c) == 9:
                    continue
                px[Y][X] = c


def tree(kind, seed):
    rnd = random.Random(seed)
    if kind == "sapin":
        s = Px(16, 28)
        for k in range(22):
            half = min(7, 1 + k // 3 + (k % 3))
            s.r(8 - half, k, 2 * half, 1, "#2f5f3a" if k % 4 else "#3d7548")
            s.r(8 - half, k, 1, 1, "#24492c")
        s.r(7, 22, 2, 4, "#4a2e17")
        s.outline()
        return s, 8, 26
    s = Px(22, 26)
    for (cx, cy, r, col) in [(11, 9, 7, "#3f7d2e"), (7, 12, 5, "#3a7329"), (15, 12, 5, "#3a7329"), (11, 6, 5, "#4f9a38"), (9, 5, 2, "#6fbf4a")]:
        for yy in range(cy - r, cy + r + 1):
            for xx in range(cx - r, cx + r + 1):
                if (xx - cx) ** 2 + (yy - cy) ** 2 <= r * r:
                    s.p(xx, yy, col)
    for k in range(10):
        s.p(rnd.randint(4, 17), rnd.randint(3, 15), "#2e5f22")
    s.r(10, 16, 3, 8, "#5a3a1e"); s.r(10, 16, 1, 8, "#7a4e2a")
    s.outline()
    return s, 11, 23


def rock():
    s = Px(10, 7)
    s.r(1, 2, 8, 4, "#8d8a93"); s.r(2, 1, 5, 2, "#a6a3ab"); s.r(1, 5, 8, 1, "#6b6874")
    s.outline()
    return s, 5, 6


def fence_post():
    s = Px(3, 8); s.r(0, 0, 3, 8, "#8a5a2b"); s.r(0, 0, 3, 1, "#c98b52"); s.outline(); return s


def decorate(px):
    P = paths()
    occupied = set()
    for (i0, j0, a, b) in BUILDINGS.values():
        for i in range(i0 - 2, i0 + a + 2):
            for j in range(j0 - 2, j0 + b + 3):
                occupied.add((i, j))
    items = []
    for i in range(-40, 40):
        for j in range(-40, 40):
            x, y = CX + (i - j) * 16, CY + (i + j) * 8
            if not (-20 < x < W + 20 and -10 < y < H + 30):
                continue
            if tile_type(i, j) != "herbe" or (i, j) in P or (i, j) in occupied:
                continue
            h = hx("deco", i, j)
            v = i + j
            density = 30 if v < -6 else 9 if abs(i - j) > 22 else 5
            if h % 100 < density:
                kind = "sapin" if (h >> 7) % 3 == 0 else "feuillu"
                spr, ax, ay = tree(kind, h)
                items.append((y, spr, x - ax + (h >> 12) % 5 - 2, y - ay + 4))
            elif h % 100 < density + 3:
                spr, ax, ay = rock()
                items.append((y, spr, x - ax, y - ay + 2))
    # fences around the fields
    post = fence_post()
    for (i0, j0, a, b) in FIELDS:
        pts = []
        for i in range(i0, i0 + a + 1):
            pts += [(i, j0), (i, j0 + b)]
        for j in range(j0, j0 + b + 1):
            pts += [(i0, j), (i0 + a, j)]
        for (i, j) in set(pts):
            x, y = CX + (i - j - 0) * 16, CY + (i + j - 1) * 8
            items.append((y, post, x - 1, y - 7))
    items.sort(key=lambda t: t[0])
    for _, spr, ox, oy in items:
        stamp(px, spr, ox, oy)


# ------------------------------------------------------------------ iso building kit

class Iso:
    """A building drawn in its own canvas. Unit coords: i, j along the ground (16 per tile), z up."""

    def __init__(s, a, b, top=120):
        s.a, s.b = a * 16, b * 16
        s.W = (a + b) * 16 + 24
        s.H = top + (a + b) * 8 + 10
        s.ox = b * 16 + 12  # screen x of the back corner (0,0,0)
        s.oy = top
        s.px = Px(s.W, s.H)
        s.lights = Px(s.W, s.H)
        s.smoke = []

    def P(s, i, j, z):
        return s.ox + (i - j), s.oy + (i + j) / 2 - z

    def dot(s, i, j, z, c, layer=None):
        x, y = s.P(i, j, z)
        (layer or s.px).p(int(math.floor(x)), int(math.floor(y)), c)

    def left(s, i0, i1, z0, z1, c, j=None, layer=None, step=0.5):
        """A patch of the left (front-left, j = b) face."""
        j = s.b if j is None else j
        i = i0
        while i < i1:
            z = z0
            while z < z1:
                s.dot(i, j, z, c, layer); z += step
            i += step

    def right(s, j0, j1, z0, z1, c, i=None, layer=None, step=0.5):
        i = s.a if i is None else i
        j = j0
        while j < j1:
            z = z0
            while z < z1:
                s.dot(i, j, z, c, layer); z += step
            j += step

    def top(s, z, c, i0=0, i1=None, j0=0, j1=None):
        i1 = s.a if i1 is None else i1; j1 = s.b if j1 is None else j1
        i = i0
        while i < i1:
            j = j0
            while j < j1:
                s.dot(i, j, z, c); j += 0.5
            i += 0.5

    def box(s, h, L, R, T=None, i0=0, i1=None, j0=0, j1=None):
        i1 = s.a if i1 is None else i1; j1 = s.b if j1 is None else j1
        s.left(i0, i1, 0, h, L, j=j1)
        s.right(j0, j1, 0, h, R, i=i1)
        if T: s.top(h, T, i0, i1, j0, j1)

    def window_l(s, i, z, w=4, h=6, lit="#ffcf5a", frame="#3a2416", j=None):
        s.left(i - 1, i + w + 1, z - 1, z + h + 1, frame, j=j)
        s.left(i, i + w, z, z + h, "#2a2433", j=j)
        s.left(i, i + w, z, z + h, lit, j=j, layer=s.lights)

    def window_r(s, j, z, w=4, h=6, lit="#ffcf5a", frame="#3a2416", i=None):
        s.right(j - 1, j + w + 1, z - 1, z + h + 1, frame, i=i)
        s.right(j, j + w, z, z + h, "#2a2433", i=i)
        s.right(j, j + w, z, z + h, lit, i=i, layer=s.lights)

    def door_l(s, i, w=6, h=11, c="#5a3a1e"):
        s.left(i - 1, i + w + 1, 0, h + 1, "#2a1a0e")
        s.left(i, i + w, 0, h, c)
        s.left(i + w - 2, i + w - 1, h / 2, h / 2 + 1, "#e8c35a")

    def gable(s, z0, rh, c1, c2, over=3, axis="i", i0=0, i1=None, j0=0, j1=None):
        """A gable roof; ridge along `axis`. c1: the slope facing the viewer's left, c2: the other."""
        i1 = s.a if i1 is None else i1; j1 = s.b if j1 is None else j1
        pts = []
        i = i0 - over
        while i <= i1 + over:
            j = j0 - over
            while j <= j1 + over:
                if axis == "i":
                    m = (j0 + j1) / 2; half = (j1 - j0) / 2 + over
                    z = z0 + rh * (1 - abs(j - m) / half)
                    col = c1 if j > m else c2
                    band = int((abs(j - m)) / 3) % 2
                else:
                    m = (i0 + i1) / 2; half = (i1 - i0) / 2 + over
                    z = z0 + rh * (1 - abs(i - m) / half)
                    col = c2 if i > m else c1
                    band = int((abs(i - m)) / 3) % 2
                if band: col = shade(col, 0.88)
                if i in (i0 - over, i1 + over) or abs(i - (i1 + over)) < 0.6 or abs(i - (i0 - over)) < 0.6:
                    col = shade(col, 0.7) if axis == "i" else col
                pts.append((i + j, i, j, z, col))
                j += 0.5
            i += 0.5
        pts.sort()
        for _, i, j, z, col in pts:
            s.dot(i, j, z, col)
        # gable end walls under the roof
        return pts

    def pyramid(s, z0, rh, c1, c2, over=3, cl=None):
        pts = []
        mi, mj = s.a / 2, s.b / 2
        hi, hj = mi + over, mj + over
        i = -over
        while i <= s.a + over:
            j = -over
            while j <= s.b + over:
                di, dj = abs(i - mi) / hi, abs(j - mj) / hj
                z = z0 + rh * (1 - max(di, dj))
                col = (c1 if j > mj else shade(c1, 1.15)) if dj >= di else (c2 if i > mi else shade(c2, 1.15))
                if (int(max(di, dj) * 12)) % 2: col = shade(col, 0.9)
                pts.append((i + j, i, j, z, col))
                j += 0.5
            i += 0.5
        pts.sort()
        for _, i, j, z, col in pts:
            s.dot(i, j, z, col)

    def cylinder(s, r, h, c, cl=None, z0=0, windows=()):
        mi, mj = s.a / 2, s.b / 2
        pts = []
        for k in range(0, 720):
            th = k / 720 * 2 * math.pi
            i, j = mi + r * math.cos(th), mj + r * math.sin(th)
            facing = math.cos(th - math.pi / 4)
            if facing < -0.2:
                continue
            light = math.cos(th - math.pi * 0.75)
            col = shade(c, 0.85 + 0.25 * max(0, light))
            z = z0
            while z < z0 + h:
                band = int(z / 5) % 2 == 0 and (k // 18) % 2 == 0
                pts.append((i + j, i, j, z, shade(col, 0.94) if band else col))
                z += 0.5
        pts.sort()
        for _, i, j, z, col in pts:
            s.dot(i, j, z, col)

    def cone(s, r, z0, rh, c, over=3):
        mi, mj = s.a / 2, s.b / 2
        R = r + over
        pts = []
        steps = 200
        for k in range(steps + 1):
            rr = R * k / steps
            for t in range(0, 360, 1):
                th = math.radians(t)
                i, j = mi + rr * math.cos(th), mj + rr * math.sin(th)
                z = z0 + rh * (1 - rr / R)
                light = math.cos(th - math.pi * 0.75)
                col = shade(c, 0.8 + 0.35 * max(0, light))
                if int(rr / 2.5) % 2: col = shade(col, 0.9)
                pts.append((i + j + z * 0.001, i, j, z, col))
        pts.sort()
        for _, i, j, z, col in pts:
            s.dot(i, j, z, col)

    def save(s, name):
        s.px.outline()
        # crop
        xs = [x for y in range(s.H) for x in range(s.W) if s.px.g[y][x] is not None]
        ys = [y for y in range(s.H) for x in range(s.W) if s.px.g[y][x] is not None]
        x0, x1, y0, y1 = min(xs), max(xs) + 1, min(ys), max(ys) + 1
        for L, suffix in ((s.px, ""), (s.lights, "-nuit")):
            c = Px(x1 - x0, y1 - y0)
            for y in range(y0, y1):
                for x in range(x0, x1):
                    c.g[y - y0][x - x0] = L.g[y][x]
            c.svg(f"iso-{name}{suffix}")
        return {"w": x1 - x0, "h": y1 - y0, "ox": s.ox - x0, "oy": s.oy - y0,
                "smoke": [[round(sx - x0), round(sy - y0)] for sx, sy in s.smoke], "lit": any(any(r) for r in s.lights.g)}


STONE = "#9a96a0"


def b_hotel():
    s = Iso(4, 4, 130)
    s.top(0, "#6d6862")
    s.box(18, "#a39e98", "#857f7a")  # stone ground floor
    for i in range(4, 64, 10):
        s.left(i, i + 1, 0, 18, "#8a857f")
    s.left(0, 64, 18, 40, "#e7d8b4"); s.right(0, 64, 18, 40, "#c9b98f")
    for i in (0, 16, 32, 48, 63):
        s.left(i, i + 1.5, 18, 40, "#5a3a1e")
    for j in (0, 16, 32, 48, 63):
        s.right(j, j + 1.5, 18, 40, "#4a2e17")
    s.left(0, 64, 18, 19.5, "#5a3a1e"); s.right(0, 64, 18, 19.5, "#4a2e17")
    for i in (6, 22, 38, 52):
        s.window_l(i, 25, 6, 8)
    for j in (6, 22, 40, 52):
        s.window_r(j, 25, 5, 8)
    s.window_l(8, 5, 5, 7); s.window_l(48, 5, 5, 7)
    s.door_l(27, 10, 14)
    # banners either side of the door
    s.left(22, 25, 6, 16, "#2f4a7a"); s.left(40, 43, 6, 16, "#7a1f2b")
    s.gable(40, 26, "#a3442e", "#c25a3e", over=4, axis="i")
    # belfry
    sub = 24
    s.box  # noqa
    for (i0, i1, j0, j1) in [(26, 38, 26, 38)]:
        s.left(i0, i1, 58, 76, "#e7d8b4", j=j1); s.right(j0, j1, 58, 76, "#c9b98f", i=i1)
        s.left(i0 + 3, i1 - 3, 64, 72, "#2a2433", j=j1); s.left(i0 + 5, i0 + 7, 64, 70, "#e8c35a", j=j1)
        s.right(j0 + 3, j1 - 3, 64, 72, "#2a2433", i=i1)
    pts = []
    for i2 in [x * 0.5 for x in range(2 * 24, 2 * 41)]:
        for j2 in [x * 0.5 for x in range(2 * 24, 2 * 41)]:
            d = max(abs(i2 - 32) / 9, abs(j2 - 32) / 9)
            if d <= 1:
                pts.append((i2 + j2, i2, j2, 76 + 14 * (1 - d), "#41286f" if j2 > 32 else "#5b3a9c"))
    pts.sort()
    for _, i2, j2, z, c in pts:
        s.dot(i2, j2, z, c)
    s.dot(32, 32, 91, "#e8c35a"); s.dot(32, 32, 92, "#e8c35a"); s.dot(32, 32, 93, "#e8c35a")
    # chimney
    s.left(50, 56, 50, 66, "#74717c", j=12); s.right(6, 12, 50, 66, "#5d5866", i=56); s.top(66, "#3b3542", 50, 56, 6, 12)
    s.smoke.append(s.P(53, 9, 68))
    return s


def b_tour():
    s = Iso(2, 2, 150)
    s.top(0, "#6d6862")
    s.cylinder(13, 56, "#8f8a9e")
    # windows on the visible front of the cylinder
    for z in (14, 32):
        for (th, w) in ((math.pi * 0.25, 1),):
            for dz in range(0, 9):
                for dw in (-2, -1, 0, 1, 2):
                    t2 = th + dw * 0.07
                    i, j = 16 + 13.3 * math.cos(t2), 16 + 13.3 * math.sin(t2)
                    col = "#2a2433" if abs(dw) < 2 and 0 < dz < 8 else "#3a2416"
                    s.dot(i, j, z + dz, col)
                    if abs(dw) < 2 and 0 < dz < 8:
                        s.dot(i, j, z + dz, "#c9a8ff", layer=s.lights)
    # door
    for dz in range(0, 13):
        for dw in (-3, -2, -1, 0, 1, 2, 3):
            t2 = math.pi * 0.5 + dw * 0.07
            i, j = 16 + 13.3 * math.cos(t2), 16 + 13.3 * math.sin(t2)
            s.dot(i, j, dz, "#2a1a0e" if abs(dw) == 3 or dz == 12 else "#5a3a1e")
    s.cone(13, 56, 36, "#5b3a9c", over=4)
    s.dot(16, 16, 93, "#e8c35a"); s.dot(16, 16, 94, "#ffe9a0"); s.dot(16, 16, 95, "#e8c35a")
    return s


def b_atelier():
    s = Iso(3, 3, 110)
    s.top(0, "#5d5866")
    s.box(24, "#a0603e", "#7f4a30")
    for z in range(3, 24, 4):
        s.left(0, 48, z, z + 0.5, "#7a4430"); s.right(0, 48, z, z + 0.5, "#5f3424")
    s.window_l(8, 9, 8, 7)
    # open forge on the right face: glowing
    s.right(14, 34, 0, 16, "#2a1d1a")
    s.right(17, 31, 2, 10, "#5a2a1a")
    s.right(18, 30, 3, 9, "#ff8a2a", layer=s.lights); s.right(21, 27, 4, 7, "#ffd36b", layer=s.lights)
    s.door_l(28, 8, 13)
    s.pyramid(24, 18, "#4a4f5c", "#5b606d", over=3)
    # chimney
    s.left(34, 42, 26, 52, "#74717c", j=12); s.right(4, 12, 26, 52, "#5d5866", i=42); s.top(52, "#2e2a35", 34, 42, 4, 12)
    s.smoke.append(s.P(38, 8, 54))
    # gear sign
    for k in range(16):
        th = k / 16 * 2 * math.pi
        s.dot(24 + 4 * math.cos(th), 48, 18 + 4 * math.sin(th), "#e8c35a")
    s.dot(24, 48, 18, "#e8c35a")
    return s


def b_caserne():
    s = Iso(4, 3, 100)
    s.top(0, "#6d6862")
    s.box(28, "#8f8a93", "#74717c")
    for z in range(4, 28, 6):
        for i in range(0, 64, 8):
            s.left(i + (z // 6 % 2) * 4, i + (z // 6 % 2) * 4 + 0.6, z, z + 6, "#74717c")
        s.left(0, 64, z, z + 0.6, "#74717c"); s.right(0, 48, z, z + 0.6, "#5d5866")
    s.top(28, "#5d5866")
    # crenellations
    for i in range(0, 64, 8):
        s.left(i, i + 4, 28, 33, "#8f8a93"); s.top(33, "#a6a3ab", i, i + 4, 44, 48)
    for j in range(0, 48, 8):
        s.right(j, j + 4, 28, 33, "#74717c"); s.top(33, "#a6a3ab", 60, 64, j, j + 4)
    s.door_l(28, 9, 15, "#4a2e17")
    for i in (8, 46):
        s.window_l(i, 14, 3, 7)
    s.window_r(14, 14, 3, 7); s.window_r(30, 14, 3, 7)
    # flag poles with pennants
    for (i, j, col) in ((6, 6, "#7a1f2b"), (58, 6, "#2f4a7a")):
        for z in range(28, 58):
            s.dot(i, j, z, "#3b3542")
        for dz in range(0, 7):
            for di in range(1, 10 - dz):
                s.dot(i + di, j, 57 - dz, col)
    return s


def b_temple():
    s = Iso(3, 3, 120)
    s.top(0, "#b8b1a0")
    s.box(4, "#c9c0a6", "#a8a08a", "#d8d2c2", -3, 51, -3, 51)
    s.box(30, "#e4ddcb", "#c4bca8")
    for i in (3, 13, 33, 43):
        s.left(i, i + 3, 0, 30, "#f6f1e4"); s.left(i + 3, i + 4, 0, 30, "#b8af96")
    for j in (6, 20, 34):
        s.right(j, j + 3, 0, 30, "#d8d0bc"); s.right(j + 3, j + 4, 0, 30, "#a8a08a")
    s.door_l(20, 8, 16, "#7a4e2a")
    s.window_r(26, 14, 5, 10, lit="#ffe9a0")
    s.pyramid(30, 22, "#d9a93a", "#e8c35a", over=4)
    for z in range(52, 60):
        s.dot(24, 24, z, "#e8c35a")
    for k in range(12):
        th = k / 12 * 2 * math.pi
        s.dot(24 + 3 * math.cos(th) * 0.7, 24 - 3 * math.cos(th) * 0.7, 62 + 3 * math.sin(th), "#ffe27a")
    return s


def b_taverne():
    s = Iso(3, 3, 110)
    s.top(0, "#6d6862")
    s.box(14, "#a39e98", "#857f7a")
    s.left(0, 48, 14, 32, "#e7d8b4"); s.right(0, 48, 14, 32, "#c9b98f")
    for i in (0, 12, 24, 36, 47):
        s.left(i, i + 1.5, 14, 32, "#5a3a1e")
    for j in (0, 16, 32, 47):
        s.right(j, j + 1.5, 14, 32, "#4a2e17")
    for k in range(12):
        s.left(1 + k, 2.5 + k, 15 + k * 1.4, 16.5 + k * 1.4, "#5a3a1e")
    s.window_l(5, 19, 5, 7); s.window_l(28, 19, 5, 7); s.window_l(39, 19, 5, 7)
    s.window_r(8, 19, 5, 7); s.window_r(30, 19, 5, 7)
    s.window_l(4, 3, 5, 6); s.window_r(20, 3, 6, 6)
    s.door_l(16, 8, 12)
    # hanging sign (a mug)
    s.left(30, 38, 9, 14, "#c98b52"); s.left(32, 35, 10, 13, "#e8c35a")
    s.gable(32, 20, "#86361f", "#a3442e", over=3, axis="j")
    s.left(6, 12, 40, 56, "#74717c", j=36); s.right(30, 36, 40, 56, "#5d5866", i=12); s.top(56, "#2e2a35", 6, 12, 30, 36)
    s.smoke.append(s.P(9, 33, 58))
    return s


def b_grange():
    s = Iso(3, 2, 90)
    s.top(0, "#5a3a1e")
    s.box(20, "#9a3b2a", "#7f2f21")
    for i in range(0, 48, 3):
        s.left(i, i + 0.6, 0, 20, "#7f2f21")
    for j in range(0, 32, 3):
        s.right(j, j + 0.6, 0, 20, "#661f15")
    s.left(16, 32, 0, 15, "#e9e3d0")
    s.left(17, 31, 1, 14, "#7f2f21")
    for k in range(13):
        s.left(17 + k, 18 + k, 1 + k, 2 + k, "#e9e3d0"); s.left(30 - k, 31 - k, 1 + k, 2 + k, "#e9e3d0")
    s.gable(20, 16, "#5a3b22", "#6b4a2a", over=3, axis="i")
    return s


def b_etal(name, col, a=2, b=1):
    s = Iso(a, b, 70)
    A, B = a * 16, b * 16
    for (i, j) in ((1, 1), (A - 1, 1), (1, B - 1), (A - 1, B - 1)):
        for z in range(0, 18):
            s.dot(i, j, z, "#5a3a1e")
    # counter with goods
    s.left(1, A - 1, 0, 7, "#8a5a2b", j=B - 1); s.right(1, B - 1, 0, 7, "#6b4422", i=A - 1); s.top(7, "#a8693a", 1, A - 1, 1, B - 1)
    rnd = random.Random(name)
    for k in range(10):
        s.top(8, rnd.choice(["#c8402e", "#e8c35a", "#7fae3e", "#e9e3d0", "#d77ac2", "#ff9b2f"]), 2 + k * (A - 4) / 10, 2 + k * (A - 4) / 10 + 2, 3, B - 3)
    # striped canopy
    pts = []
    i = -2
    while i <= A + 2:
        j = -2
        while j <= B + 2:
            m = B / 2; z = 18 + 6 * (1 - abs(j - m) / (B / 2 + 2))
            c = col if int((i + 2) / 4) % 2 == 0 else "#f2ead6"
            pts.append((i + j, i, j, z, c if j > m else shade(c, 1.1)))
            j += 0.5
        i += 0.5
    pts.sort()
    for _, i, j, z, c in pts:
        s.dot(i, j, z, c)
    return s


def b_panneau():
    s = Iso(1, 1, 60)
    for z in range(0, 22):
        s.dot(3, 14, z, "#5a3a1e"); s.dot(13, 14, z, "#5a3a1e")
    s.left(1, 15, 9, 22, "#8a5a2b", j=14)
    s.left(1, 15, 21, 23, "#5a3a1e", j=14)
    for (i, z, c) in ((3, 12, "#efe2bf"), (8, 14, "#efe2bf"), (11, 11, "#e9d8a8"), (5, 16, "#f6efd8")):
        s.left(i, i + 3, z, z + 4, c, j=14.2)
        s.left(i + 1, i + 2, z + 3, z + 3.6, "#a3242e", j=14.4)
    return s


def b_puits():
    s = Iso(1, 1, 60)
    s.cylinder(6, 7, "#8d8a93")
    s.top(7, "#2a4a7a", 4, 12, 4, 12)
    for z in range(7, 20):
        s.dot(3, 8, z, "#5a3a1e"); s.dot(13, 8, z, "#5a3a1e")
    s.gable(19, 5, "#86361f", "#a3442e", over=2, axis="j", i0=2, i1=14, j0=4, j1=12)
    return s


def bench_and_fire():
    s = Px(14, 12)
    s.r(5, 8, 4, 2, "#5a3a1e"); s.r(3, 9, 8, 2, "#6b6874")
    s.outline(); s.svg("feu-camp")


if __name__ == "__main__":
    px = terrain()
    decorate(px)
    write_png(os.path.join(OUT, "terrain.png"), px, W, H, UP)
    # small minimap copy (x1)
    write_png(os.path.join(OUT, "minicarte.png"), px, W, H, 1)
    makers = {"hotel": b_hotel, "tour": b_tour, "atelier": b_atelier, "caserne": b_caserne, "temple": b_temple,
              "taverne": b_taverne, "grange": b_grange, "panneau": b_panneau, "puits": b_puits,
              "etal1": lambda: b_etal("e1", "#a3242e"), "etal2": lambda: b_etal("e2", "#2f4a7a"), "etal3": lambda: b_etal("e3", "#2f6b4a", 1, 2)}
    man = {}
    for n, f in makers.items():
        sp = f()
        m = sp.save(n)
        i0, j0, a, b = BUILDINGS[n]
        m.update({"i0": i0, "j0": j0, "a": a, "b": b})
        man[n] = m
        top = CY + (i0 + j0 - 1) * 8 - m["oy"]
        front = CY + (i0 + a + j0 + b - 1) * 8
        print(f"{n:8} top={top:5} front={front:5}")
    bench_and_fire()
    js = ("// Generated by iso.py: isometric building sprites and where they stand.\n"
          f"export const WORLD = {{ w: {W}, h: {H}, cx: {CX}, cy: {CY} }};\n"
          f"export const BUILDINGS = {json.dumps(man, indent=1)};\n"
          f"export const RIVER = {json.dumps(list(RIVER_I))};\n")
    open(os.path.join(MOD, "iso-data.js"), "w").write(js)
    print("ok", list(man))
