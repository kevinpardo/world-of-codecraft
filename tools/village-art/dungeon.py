"""Dungeon hall background for the Herdr mod: one voxel scene through the village engine.

The scene is rendered in the village iso projection, then every column is sheared by u/2 rows so the
back wall runs horizontally across the strip (screen x = x - y, screen y = y - z). Torch light, rune glow
and the dungeon grading are applied in screen space on top.
Writes mods/world-of-codecraft/art/donjon/salle.png (3200x800) and meta.json (logical 1600x400 anchors).
"""
import os, json, sys
import numpy as np
from multiprocessing import Pool
from PIL import Image
from scipy import ndimage
import engine
engine.VS_DEFAULT[0] = 1.0
from engine import Vol, Mat, BAYER, hx, vnoise2
from gi import render
from tex import *
from tex import h1, h2, blob3

W, H = 1600, 400
FZ = 3                      # floor top height
YW = 215                    # back wall front face
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'mods', 'world-of-codecraft', 'art', 'donjon')

# ---------------------------------------------------------------- extra textures + materials
def seg_hit(fx, fy, ax, ay, bx, by, r=0.7):
    dx, dy = bx - ax, by - ay
    t = np.clip(((fx - ax) * dx + (fy - ay) * dy) / (dx * dx + dy * dy + 1e-6), 0, 1)
    return (fx - ax - t * dx) ** 2 + (fy - ay - t * dy) ** 2 < r * r

def stone_cracks(fx, fy, ry, col, cw):
    # short angular crack with a branch inside a few flagstones
    has = h2(ry, col, 70) < 0.22
    x = 4 + h2(ry, col, 71) * (cw - 8); y = 3 + h2(ry, col, 72) * 16
    ang = h2(ry, col, 73) * 6.28
    hit = np.zeros(len(fx), bool); nodes = []
    for k in range(4):
        sgn = np.where(h2(ry, col, 80 + k) < 0.5, -1, 1)
        ang = ang + sgn * (0.9 + h2(ry, col, 90 + k) * 0.8)
        ln = 3 + h2(ry, col, 100 + k) * 4
        nx, ny = x + np.cos(ang) * ln, y + np.sin(ang) * ln * 0.7
        hit |= seg_hit(fx, fy, x, y, nx, ny)
        nodes.append((nx, ny, ang)); x, y = nx, ny
    bx0, by0, ba = nodes[1]
    hit |= seg_hit(fx, fy, bx0, by0, bx0 + np.cos(ba + 1.1) * 5, by0 + np.sin(ba + 1.1) * 3.5)
    return hit & has

def t_flags(P, n, p, lv):
    ry = np.floor(P[:, 1] / 22)
    xs = P[:, 0] + h1(ry, 3) * 60
    cw = 34 + h1(ry, 8) * 14
    col = np.floor(xs / cw)
    fx = xs - col * cw; fy = P[:, 1] - ry * 22
    mortar = (fx < 1.2) | (fy < 1.2)
    off = (h2(ry, col, 4) - 0.5) * 2.0
    off = np.where(mortar, -2.4, off)
    off = np.where(~mortar & (fy > 19.5), off - 0.5, off)
    off = np.where(blob3(P, 1.0, 5) > 0.94, off - 0.7, off)
    crack = stone_cracks(fx, fy, ry, col, cw)
    wall = np.clip(1 - (P[:, 1] - YW) / 60, 0, 1)
    m = (vnoise2(P[:, 0], P[:, 1], 18, 31) * 0.7 + wall * 0.5) > 0.9
    off = np.where(crack & ~mortar, off - 2.2, off)
    swap = np.where(mortar, 0, np.where(m, 40, 0))
    return off, swap

FLOOR = 60; WALL = 61; PIER = 62; BONE = 63; CIRCLE = 64
CIRC = (490, 330, 56)
PAL[FLOOR] = Mat('#7b7380', t_flags, hs=24)
PAL[WALL] = Mat('#716a79', t_stone, params={'ch': 8, 'bl': 14, 'moss': 40, 'mossh': 34}, hs=24)
PAL[PIER] = Mat('#9a8f86', t_stone, params={'ch': 9, 'bl': 18}, hs=26)
PAL[BONE] = Mat('#ddd2b8', t_noise, light=1.1, hs=14)
PAL[CIRCLE] = Mat('#4d4760', t_noise, hs=20)
for i, cx in enumerate((70, 1530)):
    PAL[70 + i] = Mat('#9a8f86', t_stone, params={'ch': 9, 'bl': 18}, hs=26)
BOOKS = [CLOTH_R, CLOTH_B, CLOTH_G, CLOTH_P, CLOTH_Y, WOOD_L, TIMBER, PAPER]

# ---------------------------------------------------------------- helpers
def at(sx, sy):
    """World (x, y) of the floor point drawn at screen (sx, sy)."""
    y = sy + FZ
    return sx + y, y

def screen(x, y, z):
    return x - y, y - z

def arch_mask(X, Z, xc, w, h, grow=0):
    hs = h - w / 2
    r = w / 2 + grow
    return (np.abs(X - xc) <= r) & ((Z < hs) | ((X - xc) ** 2 + (Z - hs) ** 2 <= r * r))

def alcove(v, sx, w, h, depth, trim=True):
    xc = sx + YW
    bb = (xc - w / 2 - 1, xc + w / 2 + 1, YW - depth, YW + 1, FZ, FZ + h + 1)
    v.put(bb, lambda X, Y, Z: arch_mask(X, Z - FZ, xc, w, h) & (Y >= YW - depth), 0)
    if trim:
        hs = h - w / 2
        v.put((xc - w / 2 - 8, xc + w / 2 + 8, YW - 1, YW + 5, FZ, FZ + h + 9),
              lambda X, Y, Z: arch_mask(X, Z - FZ, xc, w, h, 7) & ~arch_mask(X, Z - FZ, xc, w, h, 0) & (Y >= YW - 1) & (Y < YW + 4), PIER)
        v.box(xc - 4, xc + 4, YW - 1, YW + 6, FZ + h + 4, FZ + h + 11, PIER)

def pier(v, sx, w=36):
    xc = sx + YW
    v.box(xc - w / 2, xc + w / 2, YW, YW + 11, FZ, 226, PIER)
    v.box(xc - w / 2 - 4, xc + w / 2 + 4, YW, YW + 14, FZ, FZ + 10, PIER)
    v.box(xc - w / 2 - 4, xc + w / 2 + 4, YW, YW + 14, 150, 158, PIER)
    v.box(xc - w / 2 - 2, xc + w / 2 + 2, YW, YW + 13, 148, 150, STONE_D)

def torch(v, sx, z=108):
    """Wall sconce on the front of a pier. Returns the flame centre in screen px."""
    xc = sx + YW; y = YW + 11
    v.box(xc - 1.5, xc + 1.5, y, y + 6, z - 4, z - 1, METAL)
    v.box(xc - 1.5, xc + 1.5, y, y + 2, z - 14, z - 1, METAL)
    v.cone(xc, y + 6, 4.2, z - 1, z + 6, METAL, r1=3.0)
    v.cone(xc, y + 6, 5.2, z + 5, z + 30, FIRE, p=1.4)
    return screen(xc, y + 6, z + 14)

def bar(v, x0, x1, y0, y1, z0, z1, mat): v.box(x0, x1, y0, y1, z0, z1, mat)

def barrel(v, sx, sy, r=7, h=17):
    x, y = at(sx, sy)
    v.put((x - r - 2, x + r + 2, y - r - 2, y + r + 2, FZ, FZ + h),
          lambda X, Y, Z: ((X - x) ** 2 + (Y - y) ** 2) <= (r + 1.6 * np.sin(np.clip((Z - FZ) / h, 0, 1) * np.pi)) ** 2, PLANK)
    for zz in (FZ + 3, FZ + h - 5):
        v.cyl(x, y, r + 1.6 * np.sin((zz - FZ + 1) / h * np.pi) + 0.5, zz, zz + 1.5, METAL)
    v.cyl(x, y, r - 1, FZ + h - 0.5, FZ + h, TIMBER)

def crate(v, sx, sy, s=15, z=0):
    x, y = at(sx, sy)
    v.box(x, x + s, y, y + s, FZ + z, FZ + z + s, PLANK)
    for zz in (FZ + z, FZ + z + s - 1.5):
        v.box(x - 0.4, x + s + 0.4, y - 0.4, y + s + 0.4, zz, zz + 1.5, TIMBER)
    for k in (0.3, s - 1.5):
        v.box(x + k, x + k + 1.2, y - 0.4, y + s + 0.4, FZ + z, FZ + z + s, TIMBER)

def bones(v, sx, sy, rng, n=8, spread=18):
    x0, y0 = at(sx, sy)
    for _ in range(n):
        x = x0 + rng.uniform(-spread, spread); y = y0 + rng.uniform(-spread * 0.4, spread * 0.4)
        a = rng.uniform(0, 3.14); l = rng.uniform(5, 10)
        v.capsule((x, y, FZ + 1.2), (x + np.cos(a) * l, y + np.sin(a) * l * 0.5, FZ + 1.2), 1.1, BONE)
    v.ell(x0 + 2, y0 + 2, FZ + 3.2, 3.6, 3.2, 3.2, BONE)
    v.box(x0 + 1, x0 + 4, y0 + 3.5, y0 + 5, FZ + 1.5, FZ + 3, COAL)

def books(v, xc, y, zrows, xl, xr, rng):
    for z0, z1 in zrows:
        x = xl
        while x < xr - 3:
            w = rng.integers(2, 6); hgt = rng.integers(9, int(z1 - z0 - 1))
            if rng.random() < 0.08:
                x += w; continue
            v.box(x, x + w, y - 6, y, z0, z0 + hgt, BOOKS[rng.integers(0, len(BOOKS))])
            x += w

# ---------------------------------------------------------------- scene
WALL_PIERS = (190, 460, 1140, 1410)
def build(v):
    rng = np.random.default_rng(5)
    flames = []
    # floor + back wall
    v.box(v.o[0], v.hi[0], 188, v.hi[1], 0, FZ, FLOOR)
    v.box(v.o[0], v.hi[0], 190, YW, 0, 227, WALL)
    # horizontal cornice band
    v.box(v.o[0], v.hi[0], YW, YW + 3, 150, 156, PIER)
    v.box(v.o[0], v.hi[0], YW, YW + 5, 156, 158, STONE_D)
    # alcoves: bookshelf (left), portcullis (centre), bones and chains (right)
    alcove(v, 330, 112, 132, 15)
    alcove(v, 800, 150, 132, 24)
    alcove(v, 1270, 112, 132, 15)
    for sx in WALL_PIERS:
        pier(v, sx)
        flames.append(torch(v, sx))
    # bookshelf
    xc = 330 + YW; yb = YW - 3
    zr = [(FZ + 2 + 19 * k, FZ + 2 + 19 * (k + 1)) for k in range(4)]
    for k in range(5):
        v.box(xc - 52, xc + 52, YW - 12, yb + 2, FZ + 19 * k, FZ + 19 * k + 2, TIMBER)
    for sx_ in (-52, 50):
        v.box(xc + sx_, xc + sx_ + 2, YW - 12, yb + 2, FZ, FZ + 78, TIMBER)
    books(v, xc, yb, zr, xc - 49, xc + 49, rng)
    v.ell(xc, YW - 7, FZ + 100, 4.2, 4.2, 4.2, MAGIC)
    v.box(xc - 6, xc + 6, YW - 9, YW - 5, FZ + 94, FZ + 96, METAL)
    # portcullis
    xc = 800 + YW; hs = 132 - 75
    def bars(X, Y, Z):
        zz = Z - FZ
        inner = arch_mask(X, zz, xc, 150, 132, -2)
        vert = ((X - xc + 75) % 10) < 2.4
        hor = (np.abs(zz - 28) < 1.4) | (np.abs(zz - 76) < 1.4) | (np.abs(zz - 110) < 1.4)
        return inner & (vert | hor) & (Y >= YW - 11) & (Y < YW - 8)
    v.put((xc - 76, xc + 76, YW - 11, YW - 8, FZ, FZ + 134), bars, METAL)
    # right alcove: chains, skeleton
    xc = 1270 + YW
    for dx in (-24, 22):
        for i in range(26):
            z = FZ + 116 - i * 3.2
            if i % 2: v.box(xc + dx - 0.6, xc + dx + 0.6, YW - 9 - 1.6, YW - 9 + 1.6, z, z + 3.6, METAL)
            else: v.box(xc + dx - 1.6, xc + dx + 1.6, YW - 9 - 0.6, YW - 9 + 0.6, z, z + 3.6, METAL)
        v.box(xc + dx - 3, xc + dx + 3, YW - 10.5, YW - 7.5, FZ + 29, FZ + 33, METAL)
    sx0, sy0 = 1270, 238
    bones(v, sx0, sy0 - 14, rng, 9, 22)
    # foreground pillars
    for i, sx_ in enumerate((70, 1530)):
        x, y = at(sx_, 352)
        v.box(x - 17, x + 17, y - 17, y + 17, FZ, FZ + 10, PIER)
        v.cyl(x, y, 11.5, FZ + 10, 227, 70 + i)
        v.box(x - 15, x + 15, y - 15, y + 15, 196, 206, PIER)
    PAL[70].p = {'c': at(70, 352), 'r': 22, 'ch': 9, 'bl': 18}
    PAL[71].p = {'c': at(1530, 352), 'r': 22, 'ch': 9, 'bl': 18}
    # lectern
    x, y = at(420, 246)
    v.box(x - 4, x + 4, y - 3, y + 3, FZ, FZ + 20, TIMBER)
    v.box(x - 7, x + 7, y - 5, y + 5, FZ, FZ + 3, STONE_D)
    v.put((x - 10, x + 10, y - 7, y + 8, FZ + 18, FZ + 31), lambda X, Y, Z: (np.abs(X - x) <= 9) & (np.abs(Y - y) <= 6.5) & (Z >= FZ + 19 + (Y - y) * 0.45) & (Z < FZ + 22.5 + (Y - y) * 0.45), WOOD_L)
    v.put((x - 10, x + 10, y - 7, y + 8, FZ + 18, FZ + 31), lambda X, Y, Z: (np.abs(X - x) <= 7) & (np.abs(Y - y) <= 4.5) & (Z >= FZ + 22 + (Y - y) * 0.45) & (Z < FZ + 23.6 + (Y - y) * 0.45), PAPER)
    # brazier
    x, y = at(1400, 262)
    for a in (0.4, 2.5, 4.6):
        v.capsule((x + np.cos(a) * 9, y + np.sin(a) * 9, FZ + 1), (x + np.cos(a) * 4, y + np.sin(a) * 4, FZ + 20), 1.5, METAL)
    v.cone(x, y, 11, FZ + 18, FZ + 30, METAL, p=0.6, r1=7)
    v.cyl(x, y, 9.5, FZ + 29, FZ + 31, COAL)
    v.cone(x, y, 8, FZ + 30, FZ + 52, FIRE, p=1.5)
    flames.append(screen(x, y, FZ + 38))
    # rune circle
    cx, cy = at(1190, 320); R = 34
    def rune(X, Y, Z):
        d = np.sqrt((X - cx) ** 2 + (Y - cy) ** 2)
        ang = np.arctan2(Y - cy, X - cx)
        ring = (np.abs(d - R) < 1.2) | (np.abs(d - R * 0.55) < 0.9)
        spokes = (d < R * 0.55) & (np.abs(np.sin(ang * 3)) < 0.1) & (d > 3)
        ticks = (np.abs(d - R * 0.8) < 3.0) & (np.abs(np.sin(ang * 6 + 0.5)) < 0.12)
        return ring | spokes | ticks
    v.put((cx - R - 2, cx + R + 2, cy - R - 2, cy + R + 2, FZ, FZ + 1.2), rune, MAGIC)
    # summoning circle engraved in the central floor
    cx2, cy2 = at(CIRC[0], CIRC[1]); R2 = CIRC[2]
    def circ(X, Y, Z):
        d = np.sqrt((X - cx2) ** 2 + (Y - cy2) ** 2); ang = np.arctan2(Y - cy2, X - cx2)
        ring = (np.abs(d - R2) < 1.6) | (np.abs(d - R2 * 0.7) < 1.0)
        star = (np.abs(d - R2 * 0.85) < 6) & (np.abs(np.sin(ang * 2.5)) < 0.09)
        spokes = (d < R2 * 0.7) & (d > R2 * 0.2) & (np.abs(np.sin(ang * 5)) < 0.06)
        return ring | star | spokes
    v.put((cx2 - R2 - 2, cx2 + R2 + 2, cy2 - R2 - 2, cy2 + R2 + 2, FZ, FZ + 1.2), circ, CIRCLE)
    # props
    barrel(v, 150, 300); barrel(v, 182, 286, 6.5, 16); crate(v, 118, 276); crate(v, 124, 277, 12, 15)
    crate(v, 1498, 292, 16); barrel(v, 1470, 304)
    bones(v, 1010, 372, rng, 5, 14); bones(v, 540, 384, rng, 4, 12)
    return flames

# ---------------------------------------------------------------- chunked render
CW = 160; M = 44
def render_chunk(ua):
    xa = ua - M + 188 - 100; xb = ua + CW + M + 414 + 20
    v = Vol(xa, xb, 188, 414, 0, 228)
    build(v)
    r = render(v, PAL, S=1.0, ground=False, outline=True, nightlights=False)
    col, em, (ax, ay) = r['color'], r['emis'], r['anchor']
    mm = (r['matmap'] == CIRCLE).astype(np.uint8) * 255
    om = np.zeros((H, CW), np.uint8)
    oc = np.zeros((H, CW, 4), np.uint8); oe = np.zeros((H, CW, 4), np.uint8)
    for k in range(CW):
        u = ua + k
        px = u + ax
        if px < 0 or px >= col.shape[1]: continue
        dst = np.arange(col.shape[0]) - ay - (u >> 1)
        ok = (dst >= 0) & (dst < H)
        oc[dst[ok], k] = col[ok, px]; oe[dst[ok], k] = em[ok, px]; om[dst[ok], k] = mm[ok, px]
    return ua, oc, oe, om

def flame_points():
    v = Vol(0, 4, 188, 192, 0, 4)
    return build(v)

# ---------------------------------------------------------------- lighting
def light_field(Xg, Yg, lx, ly, rx, ry):
    d = np.sqrt(((Xg - lx) / rx) ** 2 + ((Yg - ly) / ry) ** 2)
    return np.clip(1 - d, 0, 1) ** 2

def grade(rgb, emis, flames, summon=False, cmask=None):
    Yg, Xg = np.mgrid[0:H, 0:W].astype(np.float32)
    lum = rgb @ np.array([0.3, 0.55, 0.15], np.float32)
    tint = np.array([0.34, 0.30, 0.60] if summon else [0.36, 0.38, 0.55], np.float32)
    if summon:
        emis = emis.copy(); cold = emis[..., 0] > emis[..., 2]
        emis[cold, :3] = (emis[cold, :3] * np.array([0.55, 0.7, 0.95])).astype(np.uint8)
        emis[cmask > 0] = (199, 125, 255, 255)
    base = rgb * tint + lum[..., None] * np.array([0.05, 0.06, 0.12], np.float32) + np.array([5, 7, 18], np.float32)
    add = np.zeros((H, W, 3), np.float32)
    def L(lx, ly, rx, ry, col, k):
        add[...] += light_field(Xg, Yg, lx, ly, rx, ry)[..., None] * np.array(col, np.float32) * k
    warm = (110, 130, 230) if summon else (255, 150, 62)
    fk = 0.45 if summon else 1.15
    for (fx, fy) in flames:
        L(fx, fy + 28, 230, 175, warm, fk)
        L(fx, fy + 6, 90, 70, (150, 170, 255) if summon else (255, 190, 100), fk * 0.6)
    if summon:
        L(CIRC[0], CIRC[1], 380, 190, (168, 107, 255), 1.5)
        L(CIRC[0], 150, 480, 190, (168, 107, 255), 0.9)
        L(CIRC[0], CIRC[1], 130, 85, (230, 190, 255), 0.8)
    L(1190, 322, 150, 105, (168, 107, 255), 0.85)
    L(330, 140, 110, 100, (168, 107, 255), 0.55)
    L(800, 300, 560, 120, (150, 150, 190), 0.4 if summon else 0.55)
    if not summon: L(800, 305, 360, 85, (255, 190, 120), 0.35)
    e = emis[..., :3].astype(np.float32) * (emis[..., 3:4] / 255)
    g1 = np.stack([ndimage.gaussian_filter(e[..., k], 3) for k in range(3)], -1) * (4.0 if summon else 3.0)
    g2 = np.stack([ndimage.gaussian_filter(e[..., k], 20) for k in range(3)], -1) * (13.0 if summon else 9.0)
    bay = BAYER[(Yg.astype(int)) % 4, (Xg.astype(int)) % 4][..., None]
    step = 22.0
    lit_add = np.floor((add + g1 * 0.6 + g2) / step + bay * 0.9 + 0.5) * step
    out = base + lit_add * (rgb / 255 * 0.85 + 0.15)
    # vignette: darker top and sides
    vx = np.clip((np.abs(Xg - 800) - 430) / 370, 0, 1) ** 1.4
    vy = np.clip((130 - Yg) / 130, 0, 1) * 0.35 + np.clip((Yg - 365) / 35, 0, 1) * 0.25
    out *= (1 - 0.5 * vx - vy)[..., None]
    out[(emis[..., 3] > 160)] = emis[(emis[..., 3] > 160), :3]
    if summon:
        rg = np.random.default_rng(11)
        for _ in range(55):
            mx = int(CIRC[0] + rg.normal(0, 85)); my = int(rg.uniform(120, CIRC[1] + 15)); sz = int(rg.choice([1, 1, 2]))
            if 0 <= mx < W - 2 and 0 <= my < H - 2:
                out[my:my + sz, mx:mx + sz] = (236, 214, 255) if sz == 2 else (190, 140, 255)
    return np.clip(out, 0, 255).astype(np.uint8)

# ---------------------------------------------------------------- main
def main():
    col = np.zeros((H, W, 4), np.uint8); emis = np.zeros((H, W, 4), np.uint8); cm = np.zeros((H, W), np.uint8)
    starts = list(range(0, W, CW))
    with Pool(min(len(starts), os.cpu_count() or 4)) as p:
        for ua, oc, oe, om in p.imap_unordered(render_chunk, starts):
            col[:, ua:ua + CW] = oc; emis[:, ua:ua + CW] = oe; cm[:, ua:ua + CW] = om
    flames = [(round(float(a)), round(float(b))) for a, b in flame_points()]
    rgb = grade(col[..., :3].astype(np.float32), emis, flames)
    rgb2 = grade(col[..., :3].astype(np.float32), emis, flames, True, cm)
    os.makedirs(OUT, exist_ok=True)
    Image.fromarray(rgb).resize((W * 2, H * 2), Image.NEAREST).save(os.path.join(OUT, 'salle.png'))
    Image.fromarray(rgb2).resize((W * 2, H * 2), Image.NEAREST).save(os.path.join(OUT, 'salle-invocation.png'))
    meta = {'size': [W, H], 'hero': [640, 335], 'foe': [860, 335], 'dummy': [860, 335],
            'shelf': [430, 292], 'rest': [1190, 322],
            'allies': [[572, 338], [520, 300], [470, 350], [415, 312]], 'circle': [CIRC[0], CIRC[1]],
            'torches': [list(f) for f in flames], 'floor': [236, 392]}
    json.dump(meta, open(os.path.join(OUT, 'meta.json'), 'w'), indent=2)
    if '--debug' in sys.argv:
        from PIL import ImageDraw
        im = Image.fromarray(rgb).convert('RGB'); d = ImageDraw.Draw(im)
        for k, c in (('hero', 'cyan'), ('foe', 'red'), ('dummy', 'orange'), ('shelf', 'lime'), ('rest', 'magenta')):
            x, y = meta[k]; d.rectangle([x - 14, y - 55, x + 14, y], outline=c); d.ellipse([x - 3, y - 3, x + 3, y + 3], fill=c); d.text((x - 12, y + 4), k, fill=c)
        for x, y in meta['torches']: d.ellipse([x - 3, y - 3, x + 3, y + 3], outline='yellow')
        d.line([0, meta['floor'][0], W, meta['floor'][0]], fill='white'); d.line([0, meta['floor'][1], W, meta['floor'][1]], fill='white')
        for k, a in enumerate(meta['allies']): d.rectangle([a[0] - 14, a[1] - 55, a[0] + 14, a[1]], outline='white'); d.text((a[0] - 3, a[1] + 4), str(k + 1), fill='white')
        im.save(sys.argv[sys.argv.index('--debug') + 1])
        im2 = Image.fromarray(rgb2).convert('RGB'); d2 = ImageDraw.Draw(im2)
        for k, a in enumerate(meta['allies']): d2.rectangle([a[0] - 14, a[1] - 55, a[0] + 14, a[1]], outline='white'); d2.text((a[0] - 3, a[1] + 4), str(k + 1), fill='white')
        for k, c in (('hero', 'cyan'), ('foe', 'red')): x, y = meta[k]; d2.rectangle([x - 14, y - 55, x + 14, y], outline=c)
        im2.save(sys.argv[sys.argv.index('--debug') + 1].replace('.png', '-inv.png'))
    print(json.dumps(meta))

if __name__ == '__main__':
    main()
