"""Material textures + the Valbrume palette (ids are global so every asset shares them)."""
import numpy as np
from engine import Mat, hash3, ramp, hx

def tangent_coords(P, n, p):
    ax = np.argmax(np.abs(n), 1)
    if 'c' in p:  # radial (towers, cones, wells)
        cx, cy = p['c']
        ang = np.arctan2(P[:, 1] - cy, P[:, 0] - cx)
        s = ang * p.get('r', 20)
    else:
        th = np.stack([-n[:, 1], n[:, 0]], 1)
        th /= np.linalg.norm(th, axis=1, keepdims=True) + 1e-6
        s = P[:, 0] * th[:, 0] + P[:, 1] * th[:, 1]
        s = np.where(ax == 2, P[:, 0] + P[:, 1] * 0.37, s)
    return s, ax

def h1(a, seed=0):
    a = np.asarray(a).astype(np.int64)
    return hash3(a, a * 7 + 3, np.zeros_like(a), seed)

def h2(a, b, seed=0):
    return hash3(np.asarray(a).astype(np.int64), np.asarray(b).astype(np.int64), np.zeros_like(np.asarray(a), dtype=np.int64), seed)

def blob3(P, sc, seed=0):
    q = np.floor(P / sc).astype(np.int64)
    return hash3(q[:, 0], q[:, 1], q[:, 2], seed)

# ---------------------------------------------------------------- textures
def t_stone(P, n, p, lv):
    s, ax = tangent_coords(P, n, p)
    z = P[:, 2]
    ch = p.get('ch', 6.0); bl = p.get('bl', 10.0)
    row = np.floor(z / ch)
    s2 = s + h1(row, 5) * bl
    col = np.floor(s2 / (bl * (0.75 + 0.5 * h2(row, np.floor(s2 / bl), 9))))
    fz = z - row * ch; fs = s2 - np.floor(s2 / bl) * bl
    off = (h2(row, col, 1) - 0.5) * 1.1
    mortar = (fz < 1.0) | (fs < 1.0)
    off = np.where(mortar, -1.5, off)
    off = np.where((~mortar) & (fz > ch - 1.2), off + 0.7, off)
    chip = blob3(P, 1.0, 3) > 0.93
    off = np.where(chip & ~mortar, off - 0.8, off)
    # top faces: flagstones
    if 'top' in p or True:
        top = ax == 2
        gx = np.floor((P[:, 0]) / 7); gy = np.floor((P[:, 1] + h1(gx, 2) * 7) / 7)
        fx = P[:, 0] - gx * 7; fy = P[:, 1] + h1(gx, 2) * 7 - gy * 7
        tm = (fx < 1) | (fy < 1)
        toff = np.where(tm, -1.2, (h2(gx, gy, 4) - 0.5) * 0.9)
        off = np.where(top, toff, off)
    swap = None
    if 'moss' in p:
        m = (blob3(P, 3.0, 11) * 0.6 + (1 - np.clip(z / p.get('mossh', 30), 0, 1)) * 0.6) > 0.82
        swap = np.where(m & ~mortar, p['moss'], 0)
        return off, swap
    return off

def t_shingle(P, n, p, lv):
    s, ax = tangent_coords(P, n, p)
    z = P[:, 2]
    rh = p.get('rh', 3.5); w = p.get('w', 5.0)
    row = np.floor(z / rh); fz = (z - row * rh) / rh
    s2 = s + (row % 2) * w * 0.5
    col = np.floor(s2 / w); fs = s2 - col * w
    off = (h2(row, col, 7) - 0.5) * 1.0
    off = np.where(fz > 0.72, off - 1.2, off)          # shadow under the row above
    off = np.where(fz < 0.25, off + 0.6, off)          # lit lip
    off = np.where(fs < 0.9, off - 0.9, off)           # gaps
    if p.get('round'):
        off = off + np.where((fz < 0.4) & ((fs < 1.6) | (fs > w - 1.6)), -0.8, 0)
    if 'moss' in p:
        m = blob3(P, 2.5, 13) > p.get('mossamt', 0.9)
        return off, np.where(m, p['moss'], 0)
    return off

def t_plank(P, n, p, lv):
    s, ax = tangent_coords(P, n, p)
    z = P[:, 2]
    w = p.get('w', 4.0)
    if p.get('horiz'):
        a, b = z, s
    else:
        a, b = s, z
    col = np.floor(a / w); fa = a - col * w
    off = (h1(col, 21) - 0.5) * 0.9
    grain = np.sin(b * 0.9 + h1(col, 22) * 6 + np.sin(b * 0.23 + col) * 2.0)
    off = off + np.where(grain > 0.8, -0.6, 0)
    off = np.where(fa < 0.9, -1.6, off)
    off = np.where((fa > 0.9) & (fa < 1.9), off + 0.4, off)
    # nails / knots
    knot = blob3(P, 1.5, 23) > 0.975
    off = np.where(knot, off - 1.0, off)
    if ax is not None:
        top = ax == 2
        off = np.where(top, (h1(np.floor(P[:, 0] / w), 24) - 0.5) * 0.9 + np.where((P[:, 0] % w) < 0.9, -1.4, 0), off)
    return off

def t_plaster(P, n, p, lv):
    off = (blob3(P, 2.0, 31) - 0.5) * 0.7 + (blob3(P, 5.0, 32) - 0.5) * 0.6
    crack = blob3(P, 1.0, 33) > 0.985
    return np.where(crack, off - 1.2, off)

def t_wood(P, n, p, lv):  # beams, posts
    s, ax = tangent_coords(P, n, p)
    g = np.sin(P[:, 2] * 1.3 + s * 0.2 + blob3(P, 3.0, 41) * 3)
    return (g > 0.6) * -0.7 + (blob3(P, 1.0, 42) > 0.95) * -0.8

def t_metal(P, n, p, lv):
    H = np.array([-0.15, 0.2, 1.0]) + np.array([0.0, 0.7, 0.7]); H /= np.linalg.norm(H)
    spec = np.clip(n @ H, 0, 1) ** 10 * 2.2
    return spec + (blob3(P, 1.0, 51) > 0.96) * -0.6

def t_gold(P, n, p, lv):
    H = np.array([-0.3, 0.6, 1.0]); H /= np.linalg.norm(H)
    spec = np.clip(n @ H, 0, 1) ** 6 * 2.4
    band = (np.floor(P[:, 2] / 2) % 3 == 0) * 0.4 if p.get('bands') else 0
    return spec + band - 0.2

def t_leaf(P, n, p, lv):
    a = blob3(P + 0.0, 2.6, 61); b = blob3(P + 1.3, 4.2, 62)
    off = (a - 0.5) * 1.6 + (b - 0.5) * 0.9
    off = off + np.clip(n[:, 2], 0, 1) * 0.5
    if 'fruit' in p:
        f = blob3(P, 1.5, 63) > 0.975
        return off, np.where(f, p['fruit'], 0)
    return off

def t_cloth(P, n, p, lv):
    s, ax = tangent_coords(P, n, p)
    off = (blob3(P, 1.0, 71) > 0.9) * -0.4
    if 'stripe' in p:
        st = (np.floor(s / p.get('sw', 6)) % 2) == 1
        return off, np.where(st, p['stripe'], 0)
    return off

def t_noise(P, n, p, lv):
    return (blob3(P, p.get('sc', 1.5), 81) - 0.5) * p.get('amp', 0.8)

def t_hay(P, n, p, lv):
    g = np.sin(P[:, 0] * 2.1 + P[:, 1] * 1.7 + blob3(P, 2, 91) * 5)
    return (g > 0.5) * 0.7 - (blob3(P, 1, 92) > 0.85) * 1.0

def t_skin(P, n, p, lv):
    return 0.15

def t_glass(P, n, p, lv):
    # diagonal reflection streak, slightly brighter top
    d = (P[:, 0] - P[:, 1] + P[:, 2] * 1.2) % 9
    return np.where(d < 2.0, 1.5, 0) - 1.0

def t_water(P, n, p, lv):
    return (blob3(P, 2, 99) > 0.8) * 1.2

# ---------------------------------------------------------------- palette (global ids)
PAL = {}
def M(i, *a, **k):
    PAL[i] = Mat(*a, **k); return i

STONE   = M(1, '#9a8f86', t_stone, params={'moss': 40}, hs=26)
STONE_D = M(2, '#6f6875', t_stone, params={'ch': 7, 'bl': 12, 'moss': 40}, hs=24)
PLASTER = M(3, '#e8d6b0', t_plaster, params={'texamp': 0.6, 'detail': 0.6}, light=1.12, hs=18)
TIMBER  = M(4, '#6b3f26', t_wood, hs=24)
ROOF_R  = M(5, '#c4482f', t_shingle, params={'moss': 41, 'mossamt': 0.965}, hs=28, light=1.28)
ROOF_B  = M(6, '#3f6aa8', t_shingle, params={'round': True}, hs=20)
ROOF_V  = M(7, '#6a3fa8', t_shingle, params={'round': True, 'c': (0, 0), 'r': 22}, hs=24)
ROOF_T  = M(8, '#c99a3f', t_hay, hs=16)  # thatch
PLANK   = M(9, '#8a5a34', t_plank, hs=22)
PLANK_R = M(10, '#a8392c', t_plank, hs=26)
WOOD_L  = M(11, '#b88452', t_wood, hs=18)
METAL   = M(12, '#7e8794', t_metal, hs=10, cool=220)
GOLD    = M(13, '#e0a32a', t_gold, hs=20, light=1.4, dark=0.35)
GLASS   = M(14, '#2f4f73', t_glass, night='#ffcf6a', hs=10)
MARBLE  = M(15, '#e9e2d6', t_stone, params={'ch': 8, 'bl': 14}, light=1.1, hs=14)
CLOTH_R = M(16, '#c23a32', t_cloth, hs=24)
CLOTH_B = M(17, '#2e5fa8', t_cloth, hs=22)
CLOTH_W = M(18, '#efe6d2', t_cloth, light=1.1, hs=14)
CLOTH_G = M(19, '#3f8a3a', t_cloth, hs=22)
FIRE    = M(20, '#ff9a2a', t_noise, params={'amp': 2.0, 'sc': 1.2}, emissive=3.4, night='#ffb347', rim=False, rp=np.array([hx(c) for c in ('#7a1d1d', '#c2361c', '#ee6a1d', '#ffa12b', '#ffd25a', '#fff2a8', '#fffbe0')], np.float32))
MAGIC   = M(21, '#b46cff', t_noise, params={'amp': 1.4, 'sc': 2}, emissive=3.3, night='#c77dff', rim=False, rp=np.array([hx(c) for c in ('#2a1660', '#4b26a8', '#7a3cf0', '#a86bff', '#cfa6ff', '#efdcff', '#ffffff')], np.float32))
HOLY    = M(22, '#ffe28a', t_noise, params={'amp': 1.2, 'sc': 2}, emissive=3.2, night='#ffe9a0', rim=False, rp=np.array([hx(c) for c in ('#6b4a10', '#a8781c', '#e0ad2e', '#ffd45e', '#ffeaa0', '#fff8d8', '#ffffff')], np.float32))
LEAF    = M(23, '#4f8f34', t_leaf, hs=30, light=1.38, dark=0.28)
LEAF_D  = M(24, '#2f6a45', t_leaf, hs=28, light=1.35, dark=0.30)
BARK    = M(25, '#5a3a28', t_wood, hs=22)
HAY     = M(26, '#d9b04a', t_hay, hs=14)
DIRT    = M(27, '#8a6a46', t_noise, hs=20)
LEAF_A  = M(28, '#c8892e', t_leaf, hs=24, light=1.3)  # autumn tree
ROOF_G  = M(29, '#3f7f5a', t_shingle, params={'round': True}, hs=22)
ROOF_S  = M(30, '#4a4f63', t_shingle, params={'rh': 3.0, 'w': 6}, hs=18)  # slate
CLOTH_P = M(31, '#7a3fa8', t_cloth, hs=24)
CLOTH_Y = M(32, '#e3b23c', t_cloth, hs=18)
CREAM   = M(33, '#f2e6c4', t_cloth, light=1.08, hs=12)
WATER   = M(34, '#2f7fb0', t_water, hs=14, flat=True)
LEAF_F  = M(35, '#6aa83a', t_leaf, params={'fruit': 16}, hs=30, light=1.35)
PAPER   = M(36, '#efe2bf', t_plaster, light=1.08, hs=10)
BRICK   = M(37, '#9c4a36', t_stone, params={'ch': 4, 'bl': 7}, hs=22)
COAL    = M(38, '#3a3238', t_noise, params={'amp': 1.4}, hs=10)
RED_AWN = M(39, '#efe2c8', t_cloth, params={'stripe': 16, 'sw': 6}, light=1.08)
BLU_AWN = M(42, '#efe2c8', t_cloth, params={'stripe': 17, 'sw': 6}, light=1.08)
MOSS    = M(40, '#5f8a3a', t_noise, hs=24)
MOSS_R  = M(41, '#7a7a3a', t_noise, hs=20)
GRN_AWN = M(43, '#efe2c8', t_cloth, params={'stripe': 19, 'sw': 6}, light=1.08)
ROPE    = M(44, '#c9a46a', t_noise, hs=12)
APPLE   = M(45, '#d8452e', t_noise, params={'amp': 0.5}, hs=20)
PUMPKIN = M(46, '#e07a24', t_noise, params={'amp': 0.6}, hs=18)
CABBAGE = M(47, '#7fb04a', t_leaf, hs=20)
