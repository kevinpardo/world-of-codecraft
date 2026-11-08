"""Reusable architectural pieces (all in world units, visible faces are +x (right) and +y (left))."""
import numpy as np
from tex import *
DOOR_SCALE = 1.22

def fbox(v, face, c, a0, a1, z0, z1, d0, d1, mat):
    """box on a wall: face 'x' -> wall plane x=c (a along y); 'y' -> plane y=c (a along x). d = offset out of the wall."""
    if face == 'x':
        v.box(c + d0, c + d1, a0, a1, z0, z1, mat)
    else:
        v.box(a0, a1, c + d0, c + d1, z0, z1, mat)

def window(v, face, c, a0, a1, z0, z1, frame=TIMBER, glass=GLASS, arch=False, shutters=None, sill=True, cross=True):
    fbox(v, face, c, a0 - 1, a1 + 1, z0 - 1, z1 + 1, -1, 1.2, frame)
    fbox(v, face, c, a0, a1, z0, z1, -3, 1.3, 0)
    fbox(v, face, c, a0, a1, z0, z1, -3, -1.5, glass)
    if arch:
        w = (a1 - a0) / 2; m = (a0 + a1) / 2
        for k in range(int(w) + 2):
            hgt = np.sqrt(max(0, w * w - (k) ** 2))
            for sgn in (-1, 1):
                aa = m + sgn * k
                if face == 'x':
                    v.box(c - 1, c + 1.2, aa - 0.6, aa + 0.6, z1, z1 + hgt + 1.2, frame)
                    v.box(c - 3, c + 1.3, aa - 0.5, aa + 0.5, z1 - 0.1, z1 + hgt, 0)
                    v.box(c - 3, c - 1.5, aa - 0.5, aa + 0.5, z1 - 0.1, z1 + hgt, glass)
                else:
                    v.box(aa - 0.6, aa + 0.6, c - 1, c + 1.2, z1, z1 + hgt + 1.2, frame)
                    v.box(aa - 0.5, aa + 0.5, c - 3, c + 1.3, z1 - 0.1, z1 + hgt, 0)
                    v.box(aa - 0.5, aa + 0.5, c - 3, c - 1.5, z1 - 0.1, z1 + hgt, glass)
    if cross:
        m = (a0 + a1) / 2
        fbox(v, face, c, m - 0.5, m + 0.5, z0, z1 + (a1 - a0) / 2 * arch, -2, -0.3, frame)
        zm = (z0 + z1) / 2
        fbox(v, face, c, a0, a1, zm - 0.5, zm + 0.5, -2, -0.3, frame)
    if sill:
        fbox(v, face, c, a0 - 2, a1 + 2, z0 - 2.2, z0 - 0.8, 0, 2.4, frame)
    if shutters:
        w = (a1 - a0) / 2 + 0.5
        fbox(v, face, c, a0 - 1 - w, a0 - 1, z0, z1, 0, 1.3, shutters)
        fbox(v, face, c, a1 + 1, a1 + 1 + w, z0, z1, 0, 1.3, shutters)

def door(v, face, c, a0, a1, z1, frame=TIMBER, leaf=PLANK, arch=True, studs=METAL):
    z1 = z1 * DOOR_SCALE
    w = (a1 - a0) / 2; m = (a0 + a1) / 2
    top = z1 + (w if arch else 0)
    # surround
    for k in np.arange(-w - 2, w + 2.01, 0.5):
        h = np.sqrt(max(0, (w + 2) ** 2 - k * k)) if arch else 2
        fbox(v, face, c, m + k - 0.5, m + k + 0.5, 0, z1 + h, -0.5, 1.5, frame)
    for k in np.arange(-w, w + 0.01, 0.5):
        h = np.sqrt(max(0, w * w - k * k)) if arch else 0
        fbox(v, face, c, m + k - 0.5, m + k + 0.5, 0, z1 + h, -3, 1.6, 0)
        fbox(v, face, c, m + k - 0.5, m + k + 0.5, 0, z1 + h, -3, -1.6, leaf)
    if studs:
        for zz in (z1 * 0.3, z1 * 0.7):
            fbox(v, face, c, a0 + 0.5, a1 - 0.5, zz, zz + 1.2, -1.8, -1.0, studs)
        fbox(v, face, c, a1 - 3, a1 - 2, z1 * 0.5, z1 * 0.5 + 2, -1.8, -0.6, GOLD)
    # step
    fbox(v, face, c, a0 - 3, a1 + 3, 0, 1.5, 0, 4, STONE)

def timber_frame(v, face, c, a0, a1, z0, z1, spacing=12, braces=True, mat=TIMBER, t=1.6):
    fbox(v, face, c, a0, a1, z0, z0 + 2, -0.5, 1, mat)
    fbox(v, face, c, a0, a1, z1 - 2, z1, -0.5, 1, mat)
    n = max(1, int(round((a1 - a0) / spacing)))
    xs = np.linspace(a0, a1 - t, n + 1)
    for x in xs:
        fbox(v, face, c, x, x + t, z0, z1, -0.5, 1, mat)
    if braces:
        for i in range(n):
            xa, xb = xs[i] + t, xs[i + 1]
            if (i % 2) == 0:
                for s in np.linspace(0, 1, 40):
                    zz = z0 + (z1 - z0) * s
                    xx = xa + (xb - xa) * (s if i % 4 == 0 else 1 - s)
                    fbox(v, face, c, xx - 0.8, xx + 0.8, zz - 0.8, zz + 0.8, -0.5, 1, mat)

def chimney(v, x, y, z0, z1, mat=BRICK, w=7):
    v.box(x - w / 2, x + w / 2, y - w / 2, y + w / 2, z0, z1, mat)
    v.box(x - w / 2 - 1, x + w / 2 + 1, y - w / 2 - 1, y + w / 2 + 1, z1 - 3, z1, STONE_D)
    v.box(x - w / 2 + 1.5, x + w / 2 - 1.5, y - w / 2 + 1.5, y + w / 2 - 1.5, z1 - 2, z1 + 1, 0)
    v.box(x - w / 2 + 1.5, x + w / 2 - 1.5, y - w / 2 + 1.5, y + w / 2 - 1.5, z1 - 5, z1 - 2, COAL)

def lantern(v, x, y, z, glow=FIRE):
    v.box(x - 2, x + 2, y - 2, y + 2, z - 4, z + 1, METAL)
    v.box(x - 1.5, x + 1.5, y - 1.5, y + 1.5, z - 3.5, z + 0.5, glow)
    v.cone(x, y, 3, z + 1, z + 4, METAL)

def banner(v, face, c, a, z_top, length=20, w=7, cloth=CLOTH_R, trim=GOLD, emblem=None):
    fbox(v, face, c, a - w / 2 - 1.5, a + w / 2 + 1.5, z_top - 1, z_top + 1, 0, 3, WOOD_L)
    for zz in np.arange(z_top - length, z_top, 0.5):
        depth = zz - (z_top - length)
        notch = depth < 4
        for k in np.arange(-w / 2, w / 2, 0.5):
            if notch and abs(k) < (4 - depth) * 0.9:
                continue
            mat = trim if (abs(k) > w / 2 - 1.1) else cloth
            fbox(v, face, c, a + k, a + k + 0.5, zz, zz + 0.5, 1, 2, mat)
    if emblem:
        fbox(v, face, c, a - 1.5, a + 1.5, z_top - length * 0.55, z_top - length * 0.55 + 3, 1.6, 2.6, emblem)

def crate(v, x, y, s=7, mat=PLANK, z=0):
    v.box(x, x + s, y, y + s, z, z + s, mat)
    v.box(x - 0.3, x + s + 0.3, y - 0.3, y + s + 0.3, z, z + 1, TIMBER)
    v.box(x - 0.3, x + s + 0.3, y - 0.3, y + s + 0.3, z + s - 1, z + s, TIMBER)

def barrel(v, x, y, r=3.5, h=9, z=0):
    v.put((x - r - 1, x + r + 1, y - r - 1, y + r + 1, z, z + h),
          lambda X, Y, Z: ((X - x) ** 2 + (Y - y) ** 2) <= (r + 0.9 * np.sin(np.clip((Z - z) / h, 0, 1) * np.pi)) ** 2, PLANK)
    for zz in (z + 1.5, z + h - 2.5):
        v.cyl(x, y, r + 0.9 * np.sin((zz - z + 0.5) / h * np.pi) + 0.4, zz, zz + 1, METAL)

def flag(v, x, y, z, h=26, cloth=CLOTH_R, length=14):
    v.cyl(x, y, 0.8, z, z + h, WOOD_L)
    v.ell(x, y, z + h + 1, 1.4, 1.4, 1.4, GOLD)
    for k in np.arange(0, length, 0.5):
        wave = np.sin(k * 0.45) * 1.5
        hh = 8 - k * 0.18
        v.box(x - 0.5 + k * 0.7, x + 0.5 + k * 0.7, y - k * 0.7 + wave - 0.5, y - k * 0.7 + wave + 0.5, z + h - hh - 1, z + h - 1, cloth)
