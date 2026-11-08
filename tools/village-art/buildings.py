"""Valbrume buildings, all modelled in world units centred on (0,0) footprint, ground z=0."""
import sys, json, time
import numpy as np
from engine import Vol, save2x
from gi import render, trim
S_B = 1.4
import engine; engine.VS_DEFAULT[0] = 1 / S_B
from kit3d import *

B = {}
def bld(name):
    def deco(f): B[name] = f; return f
    return deco

@bld('tavern')
def tavern():
    v = Vol(-52, 52, -48, 50, 0, 150)
    x0, x1, y0, y1 = -34, 34, -28, 28
    v.box(x0, x1, y0, y1, 0, 14, STONE)                       # stone ground floor plinth
    v.box(x0 + 1, x1 - 1, y0 + 1, y1 - 1, 14, 36, PLASTER)    # ground floor
    v.box(x0 - 3, x1 + 3, y0 - 3, y1 + 3, 36, 39, TIMBER)     # jetty beam
    v.box(x0 - 3, x1 + 3, y0 - 3, y1 + 3, 39, 62, PLASTER)    # jettied upper floor
    timber_frame(v, 'y', y1 - 1, x0 + 1, x1 - 1, 14, 36, spacing=13)
    timber_frame(v, 'x', x1 - 1, y0 + 1, y1 - 1, 14, 36, spacing=13)
    timber_frame(v, 'y', y1 + 3, x0 - 3, x1 + 3, 39, 62, spacing=10, braces=True)
    timber_frame(v, 'x', x1 + 3, y0 - 3, y1 + 3, 39, 62, spacing=10)
    v.roof(x0 - 9, x1 + 9, y0 - 10, y1 + 10, 58, 112, ROOF_R, axis='x', th=5, fill=PLASTER, curve=1.15)
    # gable dormer on the left face
    v.box(-8, 10, y1 + 2, y1 + 14, 60, 76, PLASTER)
    timber_frame(v, 'y', y1 + 14, -8, 10, 60, 76, spacing=9, braces=False)
    v.roof(-12, 14, y1 - 2, y1 + 18, 74, 92, ROOF_R, axis='y', th=4, fill=PLASTER)
    window(v, 'y', y1 + 14, -3, 5, 64, 72, shutters=None)
    # ridge cap
    v.box(x0 - 9, x1 + 9, -1.5, 1.5, 110, 114, ROOF_S)
    chimney(v, -20, -6, 80, 128, BRICK, 9)
    chimney(v, 24, 4, 90, 118, STONE_D, 7)
    # windows ground + upper (left face y=y1, right face x=x1)
    door(v, 'y', y1, -6, 6, 22, arch=True)
    for a in (-26, 16):
        window(v, 'y', y1 - 1, a, a + 9, 20, 30, shutters=CLOTH_G)
    for a in (-24, -6, 12):
        window(v, 'y', y1 + 3, a, a + 9, 44, 55, shutters=CLOTH_G)
    for a in (-14, 6):
        window(v, 'x', x1 - 1, a, a + 9, 20, 30)
        window(v, 'x', x1 + 3, a, a + 9, 44, 55, shutters=CLOTH_G)
    # hanging sign with mug emblem
    v.box(x1 + 3, x1 + 18, y1 - 2, y1, 52, 54, METAL)
    v.box(x1 + 8, x1 + 18, y1 - 1.4, y1 - 0.6, 38, 50, WOOD_L)
    v.box(x1 + 11, x1 + 15, y1 - 0.6, y1 + 0.4, 41, 47, GOLD)
    for xx in (x1 + 9, x1 + 17):
        v.box(xx - 0.5, xx + 0.5, y1 - 1.2, y1 - 0.8, 50, 52, METAL)
    lantern(v, -11, y1 + 3, 30); lantern(v, 11, y1 + 3, 30)
    for k, (bx, by) in enumerate(((x1 + 6, y1 - 10), (x1 + 6, y1 - 3), (x1 + 13, y1 + 4))):
        barrel(v, bx, by)
    crate(v, -30, y1 + 4, 8); crate(v, -29, y1 + 4, 6, z=8)
    # bench + table
    v.box(16, 30, y1 + 6, y1 + 9, 4, 5.5, WOOD_L); v.box(17, 18.5, y1 + 6, y1 + 9, 0, 4, TIMBER); v.box(27.5, 29, y1 + 6, y1 + 9, 0, 4, TIMBER)
    return v


def gable_frame(v, face, c, a0, a1, z0, ztop, mat=TIMBER):
    m = (a0 + a1) / 2; hw = (a1 - a0) / 2
    for k in np.arange(-hw, hw, 0.5):
        zt = z0 + (ztop - z0) * (1 - abs(k) / hw)
        if abs(k) < 1 or abs(abs(k) - hw * 0.5) < 0.8:
            fbox(v, face, c, m + k, m + k + 0.5, z0, zt, -0.5, 1, mat)
    fbox(v, face, c, a0, a1, z0 + (ztop - z0) * 0.45, z0 + (ztop - z0) * 0.45 + 1.6, -0.5, 1, mat)

def spire(v, cx, cy, r, z0, z1, mat, finial=GOLD, p=1.7):
    v.cone(cx, cy, r, z0, z1, mat, p=p)
    v.cyl(cx, cy, 0.9, z1 - 2, z1 + 8, finial)
    v.ell(cx, cy, z1 + 4, 2, 2, 2, finial)

@bld('townhall')
def townhall():
    v = Vol(-80, 80, -66, 70, 0, 210)
    x0, x1, y0, y1 = -58, 58, -40, 40
    v.box(x0, x1, y0, y1, 0, 18, STONE)
    v.box(x0 - 2, x1 + 2, y0 - 2, y1 + 2, 0, 4, STONE_D)
    v.box(x0 + 1, x1 - 1, y0 + 1, y1 - 1, 18, 44, PLASTER)
    v.box(x0 - 2, x1 + 2, y0 - 2, y1 + 2, 44, 47, TIMBER)
    v.box(x0 - 2, x1 + 2, y0 - 2, y1 + 2, 47, 70, PLASTER)
    timber_frame(v, 'y', y1 - 1, x0 + 1, x1 - 1, 18, 44, spacing=14)
    timber_frame(v, 'x', x1 - 1, y0 + 1, y1 - 1, 18, 44, spacing=14)
    timber_frame(v, 'y', y1 + 2, x0 - 2, x1 + 2, 47, 70, spacing=11)
    timber_frame(v, 'x', x1 + 2, y0 - 2, y1 + 2, 47, 70, spacing=11)
    # corner stone quoins
    for (cx, cy) in ((x1, y1), (x0, y1), (x1, y0)):
        for zz in range(0, 70, 8):
            v.box(cx - 3, cx + 3, cy - 3, cy + 3, zz, zz + 5, STONE)
    v.roof(x0 - 10, x1 + 10, y0 - 10, y1 + 10, 66, 126, ROOF_B, axis='x', hip=0.9, th=5, fill=PLASTER, curve=1.25)
    v.box(-23, 23, -1.5, 1.5, 123, 128, GOLD)
    for xx in (-23, 23):
        v.ell(xx, 0, 130, 2.5, 2.5, 3.5, GOLD)
    # belfry / clock tower rising from the front of the roof
    bx0, bx1, by0, by1 = -14, 14, 18, 46
    v.box(bx0, bx1, by0, by1, 0, 112, STONE)
    v.box(bx0 - 2, bx1 + 2, by0 - 2, by1 + 2, 110, 116, STONE_D)
    v.box(bx0, bx1, by0, by1, 116, 146, PLASTER)
    timber_frame(v, 'y', by1, bx0, bx1, 116, 146, spacing=7, braces=False)
    timber_frame(v, 'x', bx1, by0, by1, 116, 146, spacing=7, braces=False)
    for face, c in (('y', by1), ('x', bx1)):
        fbox(v, face, c, -6 if face == 'y' else 26, 6 if face == 'y' else 38, 124, 140, -4, 1, 0)
        fbox(v, face, c, -6 if face == 'y' else 26, 6 if face == 'y' else 38, 124, 140, -4, -3, COAL)
    v.box(-2, 2, 30, 34, 120, 137, GOLD)  # bell
    v.roof(bx0 - 6, bx1 + 6, by0 - 6, by1 + 6, 144, 200, ROOF_B, axis='x', hip=1.0, th=4, curve=1.6, fill=PLASTER)
    v.cyl(0, 32, 1, 196, 208, GOLD); v.ell(0, 32, 203, 2.2, 2.2, 2.2, GOLD)
    # clock on the belfry shaft
    v.put((-8, 8, by1, by1 + 2, 84, 100), lambda X, Y, Z: ((X) ** 2 + (Z - 92) ** 2 <= 64) & (Y < by1 + 1.5), GOLD)
    v.put((-8, 8, by1, by1 + 2.5, 84, 100), lambda X, Y, Z: ((X) ** 2 + (Z - 92) ** 2 <= 36) & (Y < by1 + 2), CREAM)
    v.box(-0.5, 0.5, by1 + 1.8, by1 + 2.6, 92, 97, COAL); v.box(0, 4, by1 + 1.8, by1 + 2.6, 91.5, 92.5, COAL)
    door(v, 'y', by1, -8, 8, 34, arch=True)
    window(v, 'y', by1, -5, 5, 56, 70, arch=True)
    window(v, 'x', bx1, 27, 37, 56, 70, arch=True)
    # main facade windows
    for a in (-50, -34, 22, 40):
        window(v, 'y', y1 - 1, a, a + 9, 24, 36, shutters=CLOTH_B)
        window(v, 'y', y1 + 2, a, a + 9, 52, 63, shutters=CLOTH_B)
    for a in (-30, -12, 6, 22):
        window(v, 'x', x1 - 1, a, a + 9, 24, 36, shutters=CLOTH_B)
        window(v, 'x', x1 + 2, a, a + 9, 52, 63, shutters=CLOTH_B)
    # dormers on the roof
    for a in (-40, 30):
        v.box(a - 7, a + 7, y1 - 6, y1 + 6, 70, 86, PLASTER)
        v.roof(a - 10, a + 10, y1 - 10, y1 + 10, 84, 98, ROOF_B, axis='y', th=3, fill=PLASTER)
        window(v, 'y', y1 + 6, a - 3, a + 3, 74, 82, cross=False)
    banner(v, 'y', y1 + 2, -24, 66, 22, 8, CLOTH_B, GOLD, GOLD)
    banner(v, 'y', y1 + 2, 30 - 2, 66, 22, 8, CLOTH_B, GOLD, GOLD) if False else None
    banner(v, 'x', x1 + 2, -2, 66, 22, 8, CLOTH_B, GOLD, GOLD)
    # front steps + lanterns
    for k in range(3):
        v.box(-12 - 3 * (2 - k), 12 + 3 * (2 - k), by1, by1 + 9 - 3 * k, 2 * k, 2 * k + 2, STONE_D)
    lantern(v, -18, by1 + 2, 30); lantern(v, 18, by1 + 2, 30)
    chimney(v, -42, -20, 90, 120, BRICK, 8)
    return v

@bld('magetower')
def magetower():
    v = Vol(-46, 46, -46, 46, 0, 262)
    v.cyl(0, 0, 25, 0, 10, STONE_D)
    v.put((-24, 24, -24, 24, 10, 130), lambda X, Y, Z: X ** 2 + Y ** 2 <= (22 - (Z - 10) * 0.035) ** 2, PAL_ID('tower_st'))
    for ang in (0.4, 1.25, 2.1, 3.0, 3.9, 4.8, 5.6):
        bx, by = 22 * np.cos(ang), 22 * np.sin(ang)
        v.put((bx - 6, bx + 6, by - 6, by + 6, 0, 60), lambda X, Y, Z, bx=bx, by=by: ((X - bx) ** 2 + (Y - by) ** 2 <= 16) & (Z < 60 - 2.2 * np.sqrt((X - bx * 1.25) ** 2 + (Y - by * 1.25) ** 2) * 2.4) , STONE_D)
    # corbelled balcony
    v.cone(0, 0, 21, 112, 130, STONE_D, r1=30, p=1.0) if False else None
    v.put((-31, 31, -31, 31, 112, 132), lambda X, Y, Z: X ** 2 + Y ** 2 <= (19 + (Z - 112) * 0.6) ** 2, STONE_D)
    v.cyl(0, 0, 31, 132, 136, STONE)
    for k in range(20):
        a = k / 20 * 2 * np.pi
        v.cyl(30 * np.cos(a), 30 * np.sin(a), 1.4, 136, 143, STONE)
    v.cyl(0, 0, 31.5, 143, 145.5, STONE, rin=28)
    # upper chamber
    v.cyl(0, 0, 18, 136, 176, PAL_ID('tower_st'))
    for k in range(6):
        a = k / 6 * 2 * np.pi + 0.3
        v.cyl(18 * np.cos(a), 18 * np.sin(a), 2.2, 136, 176, STONE_D)
    v.cyl(0, 0, 20, 174, 179, GOLD)
    # flared curved spire
    v.put((-32, 32, -32, 32, 176, 250), lambda X, Y, Z: (X ** 2 + Y ** 2 <= (2 + 28 * (1 - np.clip((Z - 176) / 74, 0, 1)) ** 2.1) ** 2), PAL_ID('tower_roof'))
    v.cyl(0, 0, 1, 246, 256, GOLD); v.ell(0, 0, 252, 2.5, 2.5, 2.5, GOLD)
    # floating crystal (detached voxels)
    v.put((-5, 5, -5, 5, 236, 262), lambda X, Y, Z: (np.abs(X) + np.abs(Y)) * 1.0 <= 4.2 * (1 - np.abs(Z - 252) / 9) , 0) if False else None
    # windows (arched, magic glow) on the visible faces
    def rwin(ang, z, h, hw, R):
        def m(X, Y, Z, d0, d1, ext=0):
            an = np.arctan2(Y, X); dr = np.hypot(X, Y)
            da = np.abs(((an - ang + np.pi) % (2 * np.pi)) - np.pi) * R
            top = z + h + np.sqrt(np.clip((hw + ext) ** 2 - da ** 2, 0, None))
            return (da <= hw + ext) & (Z >= z - ext) & (Z < top + ext) & (dr >= d0) & (dr <= d1)
        bb = (-R - 6, R + 6, -R - 6, R + 6, z - 3, z + h + hw + 3)
        v.put(bb, lambda X, Y, Z: m(X, Y, Z, R - 1.5, R + 1.6, 1.3), GOLD)
        v.put(bb, lambda X, Y, Z: m(X, Y, Z, R - 3, R + 2), 0)
        v.put(bb, lambda X, Y, Z: m(X, Y, Z, R - 4, R - 2.2), MAGIC)
        v.put(bb, lambda X, Y, Z: m(X, Y, Z, R - 2.5, R - 0.5) & (np.abs(Z - (z + h * 0.55)) < 0.6), GOLD)
    for ang, z in ((0.3, 34), (1.3, 34), (0.8, 68), (1.55, 96), (0.45, 98)):
        rwin(ang, z, 9, 3.2, 22 - (z - 10) * 0.035)
    for ang in (0.35, 0.95, 1.55):
        rwin(ang, 148, 12, 3.2, 18)
    for zz in (62, 92):
        v.cyl(0, 0, 22.6 - (zz - 10) * 0.035, zz, zz + 2.5, STONE_D)
    for ang in (0.2, 1.4):
        cx, cy = 31 * np.cos(ang), 31 * np.sin(ang)
        for zz in np.arange(110, 134, 0.5):
            w = 4.5 if zz > 114 else (zz - 110) * 1.1
            v.put((cx - 6, cx + 6, cy - 6, cy + 6, zz, zz + 0.5), lambda X, Y, Z, cx=cx, cy=cy, w=w, ang=ang: (np.abs(-(X - cx) * np.sin(ang) + (Y - cy) * np.cos(ang)) <= w) & (np.abs((X - cx) * np.cos(ang) + (Y - cy) * np.sin(ang)) < 0.8), PAL[31] and 31)
    # rune band glowing at the base
    v.put((-26, 26, -26, 26, 14, 18), lambda X, Y, Z: (X ** 2 + Y ** 2 <= 22.8 ** 2) & (X ** 2 + Y ** 2 > 20.5 ** 2) & (np.sin(np.arctan2(Y, X) * 22) > 0.2), MAGIC)
    # door
    a = 0.8; cx, cy = 23 * np.cos(a), 23 * np.sin(a)
    v.put((cx - 9, cx + 9, cy - 9, cy + 9, 0, 30), lambda X, Y, Z: ((X - cx) ** 2 + (Y - cy) ** 2 <= 8.5 ** 2) & (Z < 18 + np.sqrt(np.clip(36 - ((X - cx) * 0.7 - (Y - cy) * 0.7) ** 2, 0, None))), 0)
    v.put((cx - 9, cx + 9, cy - 9, cy + 9, 0, 30), lambda X, Y, Z: ((X - cx) ** 2 + (Y - cy) ** 2 <= 8.5 ** 2) & (X ** 2 + Y ** 2 <= 19 ** 2) & (Z < 18 + np.sqrt(np.clip(36 - ((X - cx) * 0.7 - (Y - cy) * 0.7) ** 2, 0, None))), PLANK)
    v.cyl(cx + 4, cy + 4, 4, 0, 1.5, STONE)
    # banners on the balcony
    return v

def PAL_ID(k):
    return {'tower_st': 48, 'tower_roof': 49, 'temple_dome': 50}[k]

PAL[48] = Mat('#8c8aa6', t_stone, params={'c': (0, 0), 'r': 22, 'ch': 6, 'bl': 9, 'moss': 40, 'mossh': 24}, hs=24)
PAL[49] = Mat('#6b3fb0', t_shingle, params={'c': (0, 0), 'r': 24, 'round': True, 'rh': 3.2, 'w': 4.5}, hs=26, light=1.35)
PAL[50] = Mat('#e0a32a', t_shingle, params={'c': (0, 0), 'r': 20, 'round': True, 'rh': 3.0, 'w': 4}, hs=20, light=1.38)

@bld('forge')
def forge():
    v = Vol(-56, 56, -50, 52, 0, 150)
    x0, x1, y0, y1 = -36, 20, -30, 26
    v.box(x0, x1, y0, y1, 0, 40, STONE_D)
    v.roof(x0 - 7, x1 + 7, y0 - 8, y1 + 8, 36, 82, ROOF_S, axis='x', th=4, fill=STONE_D)
    gable_frame(v, 'x', x1, y0, y1, 40, 78)
    # open lean-to smithy on the right
    lx0, lx1 = x1, x1 + 26
    v.box(lx0, lx1, y0 + 4, y1, 0, 2, STONE)
    for (px, py) in ((lx1 - 2, y1 - 4), (lx1 - 2, y0 + 6)):
        v.box(px - 2, px + 2, py - 2, py + 2, 0, 34, TIMBER)
    v.put((lx0 - 2, lx1 + 6, y0, y1 - 2, 30, 50), lambda X, Y, Z: (Z <= 48 - (X - lx0) * 0.55) & (Z > 44 - (X - lx0) * 0.55), ROOF_S)
    barrel(v, lx0 + 8, y0 + 10); barrel(v, lx0 + 8, y0 + 18); crate(v, lx0 + 14, y0 + 8, 8)
    # furnace protruding from the left face with a glowing arched mouth
    fx0, fx1, fy1 = -2, 16, y1 + 12
    v.box(fx0, fx1, y1, fy1, 0, 28, BRICK)
    v.box(fx0 - 1, fx1 + 1, y1, fy1 + 1, 26, 30, STONE_D)
    v.put((fx0 + 3, fx1 - 3, fy1 - 4, fy1 + 1, 2, 20), lambda X, Y, Z: (Z < 12 + np.sqrt(np.clip(25 - (X - 7) ** 2, 0, None))) & (np.abs(X - 7) <= 5), 0)
    v.put((fx0 + 3, fx1 - 3, fy1 - 6, fy1 - 3, 2, 20), lambda X, Y, Z: (Z < 12 + np.sqrt(np.clip(25 - (X - 7) ** 2, 0, None))) & (np.abs(X - 7) <= 5), FIRE)
    v.put((fx0 + 1, fx1 - 1, fy1 - 1, fy1 + 1.5, 0, 22), lambda X, Y, Z: (np.abs(np.hypot(X - 7, np.maximum(Z - 12, 0)) - 6.5) < 1.3) & (Z > 1), STONE)
    v.box(fx0 + 4, fx1 - 4, fy1, fy1 + 3, 0, 3, COAL)
    chimney(v, 7, y1 + 4, 28, 104, BRICK, 10)
    v.box(4, 10, y1 + 1, y1 + 7, 101, 103, FIRE)
    # anvil out front
    ax_, ay_ = x1 + 10, y1 + 6
    v.box(ax_, ax_ + 4, ay_, ay_ + 4, 0, 7, STONE_D)
    v.box(ax_ - 2, ax_ + 7, ay_ - 0.5, ay_ + 4.5, 7, 11, METAL)
    v.box(ax_ + 7, ax_ + 10, ay_ + 1, ay_ + 3, 8.5, 10.5, METAL)
    # tool rack on the wall
    for k in range(4):
        xx = -30 + k * 4
        v.box(xx, xx + 1, y1, y1 + 1.2, 12, 26, WOOD_L)
        v.box(xx - 1, xx + 2, y1, y1 + 1.6, 24 - (k % 2) * 3, 27, METAL)
    # water trough + quench barrel
    barrel(v, lx1 + 4, y1 - 4)
    v.box(lx0 + 2, lx0 + 14, y1 + 2, y1 + 8, 0, 6, PLANK); v.box(lx0 + 3, lx0 + 13, y1 + 3, y1 + 7, 4, 5.5, WATER)
    # door + windows on the stone house
    door(v, 'y', y1, -20, -8, 24, arch=True)
    window(v, 'x', x1, -26, -18, 18, 28)
    # gear sign
    gy = y1 + 1
    v.put((-34, -24, gy, gy + 2, 26, 40), lambda X, Y, Z: (((X + 29) ** 2 + (Z - 33) ** 2) <= (4.6 + 1.3 * (np.sin(np.arctan2(Z - 33, X + 29) * 8) > 0)) ** 2) & (((X + 29) ** 2 + (Z - 33) ** 2) > 2.0 ** 2), GOLD)
    v.box(-30, -28, gy - 1, gy, 38, 46, METAL)
    # log pile + wheel
    for k in range(3):
        v.put((x0 - 10, x0, y1 - 20, y1, 0, 12), lambda X, Y, Z, k=k: ((Z - 3 - k * 3.5) ** 2 + ((Y - (y1 - 16 + (k % 2) * 3.5)) % 7 - 3.5) ** 2 <= 9.5) & (X >= x0 - 9) & (X < x0 - 1) & (Y < y1 - 2 - k * 2), BARK)
    for zz in range(4):
        pass
    lantern(v, -2, y1 + 2, 30)
    return v

@bld('barracks')
def barracks():
    v = Vol(-74, 74, -52, 56, 0, 190)
    x0, x1, y0, y1 = -58, 34, -30, 30
    v.box(x0, x1, y0, y1, 0, 46, STONE)
    v.box(x0 - 2, x1 + 2, y0 - 2, y1 + 2, 44, 49, STONE_D)
    # crenellations
    for a in np.arange(x0 - 2, x1 + 2, 7):
        v.box(a, a + 4, y1 - 2, y1 + 2, 49, 55, STONE_D)
        v.box(a, a + 4, y0 - 2, y0 + 2, 49, 55, STONE_D)
    for a in np.arange(y0 - 2, y1 + 2, 7):
        v.box(x1 - 2, x1 + 2, a, a + 4, 49, 55, STONE_D)
        v.box(x0 - 2, x0 + 2, a, a + 4, 49, 55, STONE_D)
    v.roof(x0 + 2, x1 - 2, y0 + 2, y1 - 2, 46, 78, ROOF_R, axis='x', th=4, fill=STONE)
    # corner keep
    kx, ky = x1, y1 - 6
    v.box(kx - 14, kx + 14, ky - 14, ky + 14, 0, 98, STONE)
    v.box(kx - 16, kx + 16, ky - 16, ky + 16, 96, 102, STONE_D)
    for a in np.arange(-16, 16, 6):
        v.box(kx + a, kx + a + 3.5, ky + 13, ky + 16, 102, 108, STONE_D)
        v.box(kx + 13, kx + 16, ky + a, ky + a + 3.5, 102, 108, STONE_D)
    v.roof(kx - 12, kx + 12, ky - 12, ky + 12, 102, 156, ROOF_R, axis='x', hip=1.0, th=4, curve=1.5, fill=STONE)
    v.cyl(kx, ky, 1, 152, 160, GOLD)
    flag(v, kx, ky, 156, 24, CLOTH_R, 18)
    for zz in (30, 64):
        window(v, 'y', ky + 14, kx - 3, kx + 3, zz, zz + 12, cross=False, sill=False)
        window(v, 'x', kx + 14, ky - 3, ky + 3, zz, zz + 12, cross=False, sill=False)
    # gate
    door(v, 'y', y1, -26, -6, 30, arch=True, leaf=PLANK)
    for a in (-48, 4, 18):
        window(v, 'y', y1, a, a + 4, 22, 34, cross=False, sill=False)
    banner(v, 'y', y1, -38, 44, 26, 9, CLOTH_R, GOLD, GOLD)
    banner(v, 'y', y1, 8, 44, 26, 9, CLOTH_R, GOLD, GOLD) if False else None
    # weapon rack + training dummy
    rx = -58
    v.box(rx, rx + 22, y1 + 8, y1 + 10, 0, 3, TIMBER); v.box(rx, rx + 22, y1 + 8, y1 + 10, 14, 16, TIMBER)
    for k in range(5):
        xx = rx + 2 + k * 4.5
        v.box(xx, xx + 1, y1 + 8.5, y1 + 9.5, 0, 26, WOOD_L)
        v.cone(xx + 0.5, y1 + 9, 1.6, 26, 31, METAL)
    dx, dy = 2, y1 + 18
    v.cyl(dx, dy, 1.2, 0, 28, TIMBER)
    v.box(dx - 8, dx + 8, dy - 1, dy + 1, 20, 22, TIMBER)
    v.ell(dx, dy, 22, 5, 4, 7, HAY); v.ell(dx, dy, 32, 3.5, 3.5, 3.5, HAY)
    v.ell(dx, dy + 0.5, 21, 5.3, 4.3, 3, CLOTH_R)
    return v

@bld('temple')
def temple():
    v = Vol(-64, 64, -60, 72, 0, 210)
    x0, x1, y0, y1 = -40, 40, -40, 34
    for k in range(3):
        v.box(x0 - 8 + 2 * k, x1 + 8 - 2 * k, y0 - 8 + 2 * k, y1 + 26 - 2 * k, 2 * k, 2 * k + 2, MARBLE)
    v.box(x0, x1, y0, y1, 6, 56, MARBLE)
    v.box(x0 - 3, x1 + 3, y0 - 3, y1 + 3, 54, 60, GOLD)
    v.box(x0 - 2, x1 + 2, y0 - 2, y1 + 2, 60, 64, MARBLE)
    # portico with columns on the left (+y) face
    for a in np.linspace(x0 + 4, x1 - 4, 5):
        v.cyl(a, y1 + 16, 3.4, 6, 54, MARBLE)
        v.box(a - 4.5, a + 4.5, y1 + 11.5, y1 + 20.5, 50, 54, MARBLE)
        v.cyl(a, y1 + 16, 4.4, 6, 9, MARBLE)
    v.box(x0 - 3, x1 + 3, y1, y1 + 22, 54, 60, GOLD)
    v.box(x0 - 2, x1 + 2, y1, y1 + 21, 60, 64, MARBLE)
    v.roof(x0 - 4, x1 + 4, y0 - 4, y1 + 22, 64, 92, PAL_ID('temple_dome'), axis='y', th=4, fill=MARBLE)
    # pediment sun disk
    v.put((-9, 9, y1 + 21, y1 + 24, 66, 86), lambda X, Y, Z: (X ** 2 + (Z - 74) ** 2 <= 42) & (Y < y1 + 23), HOLY)
    # drum + dome
    v.cyl(0, -6, 22, 80, 110, MARBLE)
    for k in range(10):
        a = k / 10 * 2 * np.pi
        v.cyl(22 * np.cos(a), -6 + 22 * np.sin(a), 2.4, 80, 110, GOLD)
    v.cyl(0, -6, 24, 108, 112, GOLD)
    v.put((-24, 24, -30, 18, 112, 170), lambda X, Y, Z: (X ** 2 + (Y + 6) ** 2) / 23.0 ** 2 + ((Z - 112) / 44.0) ** 2 <= 1, PAL_ID('temple_dome'))
    v.cyl(0, -6, 4, 152, 166, GOLD); v.cone(0, -6, 3, 166, 186, GOLD, p=1.5)
    v.ell(0, -6, 192, 4.2, 4.2, 4.2, HOLY)
    for ang in (0.6, 1.4):
        cx, cy = 22 * np.cos(ang), -6 + 22 * np.sin(ang)
        v.put((cx - 4, cx + 4, cy - 4, cy + 4, 86, 104), lambda X, Y, Z, cx=cx, cy=cy: ((X - cx) ** 2 + (Y - cy) ** 2 <= 9) & (Z < 102), HOLY)
    # holy windows on the cella
    for a in (-4,):
        window(v, 'x', x1, -26, -18, 18, 38, frame=GOLD, glass=HOLY, arch=True, cross=False, sill=False)
        window(v, 'x', x1, -2, 6, 18, 38, frame=GOLD, glass=HOLY, arch=True, cross=False, sill=False)
        window(v, 'x', x1, 20, 28, 18, 38, frame=GOLD, glass=HOLY, arch=True, cross=False, sill=False)
    door(v, 'y', y1, -8, 8, 30, frame=GOLD, leaf=PLANK, arch=True)
    # braziers
    for bx in (x0 - 4, x1 + 4):
        v.cyl(bx, y1 + 30, 1.5, 0, 14, METAL); v.cone(bx, y1 + 30, 4.5, 14, 18, GOLD, r1=4.5) if False else v.cyl(bx, y1 + 30, 4, 14, 18, GOLD)
        v.cone(bx, y1 + 30, 3.4, 18, 26, FIRE, p=1.3)
    return v

@bld('barn')
def barn():
    v = Vol(-56, 60, -44, 48, 0, 140)
    x0, x1, y0, y1 = -40, 40, -26, 26
    v.box(x0, x1, y0, y1, 0, 4, STONE)
    v.box(x0 + 1, x1 - 1, y0 + 1, y1 - 1, 4, 40, PAL_ID('barn_pl'))
    # gambrel roof (convex profile) along y so the gable faces right
    v.roof(x0 - 6, x1 + 6, y0 - 5, y1 + 5, 38, 96, ROOF_S, axis='y', th=5, curve=0.6, fill=PAL_ID('barn_pl'))
    for zz in (40,):
        pass
    gable_frame(v, 'y', y1 - 1, x0, x1, 40, 92, mat=CREAM) if False else None
    # big X doors on the left face and the hayloft
    for (a0, a1) in ((-14, 14),):
        fbox(v, 'y', y1 - 1, a0, a1, 4, 34, -2, 1.2, CREAM)
        fbox(v, 'y', y1 - 1, a0 + 2, a1 - 2, 6, 32, -3, 1.4, 0)
        fbox(v, 'y', y1 - 1, a0 + 2, a1 - 2, 6, 32, -3, -1, PAL_ID('barn_pl'))
        for s in np.linspace(0, 1, 60):
            for sg in (0, 1):
                xx = a0 + 2 + (a1 - a0 - 4) * (s if sg else 1 - s); zz = 6 + 26 * s
                fbox(v, 'y', y1 - 1, xx - 1, xx + 1, zz - 1, zz + 1, -1.5, 0.6, CREAM)
        fbox(v, 'y', y1 - 1, -0.6, 0.6, 6, 32, -1.5, 0.6, CREAM)
    for face, c, a0, a1 in (('y', y1 - 1, -38, -26), ('y', y1 - 1, 26, 38), ('x', x1 - 1, -12, 0)):
        window(v, face, c, a0 + 3, a1 - 3, 16, 26, frame=CREAM, cross=True)
    # hayloft on the right gable
    fbox(v, 'x', x1 + 1, -9, 9, 50, 70, -1, 1, CREAM); fbox(v, 'x', x1 + 1, -7, 7, 52, 68, -4, 2, 0)
    v.ell(x1 - 3, 0, 52, 3, 7, 4, HAY)
    v.box(x1 - 2, x1 + 12, -1, 1, 74, 76, TIMBER)
    v.box(x1 + 10, x1 + 11, -0.5, 0.5, 60, 74, ROPE)
    # hay bales + cart wheel
    for (hx_, hy_, hz) in ((x1 + 6, y1 + 6, 0), (x1 + 14, y1 + 2, 0), (x1 + 9, y1 + 3, 8)):
        v.box(hx_, hx_ + 9, hy_, hy_ + 7, hz, hz + 8, HAY)
        v.box(hx_ + 2, hx_ + 3, hy_ - 0.3, hy_ + 7.3, hz, hz + 8.3, ROPE)
    v.put((x0 - 4, x0 + 10, y1 + 2, y1 + 4, 0, 16), lambda X, Y, Z: (np.abs(np.hypot(X - x0 - 3, Z - 7.5) - 6.5) < 1.1) | ((np.hypot(X - x0 - 3, Z - 7.5) < 6.5) & ((np.abs(X - x0 - 3) < 0.6) | (np.abs(Z - 7.5) < 0.6))), PLANK)
    return v

PAL[51] = Mat('#a33a2a', t_plank, params={'w': 4}, hs=26)
_old = PAL_ID
def PAL_ID(k):
    return {'tower_st': 48, 'tower_roof': 49, 'temple_dome': 50, 'barn_pl': 51}[k]

def stall(cloth):
    v = Vol(-30, 30, -24, 26, 0, 70)
    x0, x1, y0, y1 = -20, 20, -12, 12
    for (px, py) in ((x0, y0), (x1 - 2, y0), (x0, y1 - 2), (x1 - 2, y1 - 2)):
        v.box(px, px + 2, py, py + 2, 0, 40 if py < 0 else 30, TIMBER)
    v.box(x0, x1, y0, y1 + 2, 12, 14, WOOD_L)
    v.box(x0, x1, y1, y1 + 2, 0, 12, PLANK)
    # awning sloping toward the viewer (+y) with scalloped edge
    v.put((x0 - 3, x1 + 3, y0 - 4, y1 + 2, 30, 48),
          lambda X, Y, Z: (np.abs(Z - (37 + (Y - y0) * 0.32)) < 1.0) & (Y < y1 - 4 - (np.sin((X - x0) * 0.8) > 0) * 1.5), cloth)
    for px in (x0, x1 - 2):
        v.box(px, px + 2, y1 - 6, y1 - 4, 0, 44, TIMBER)
    # produce
    for k, (mat, cx) in enumerate(((APPLE, -14), (PUMPKIN, -3), (CABBAGE, 9))):
        crate(v, cx - 4.5, y1 - 10, 9, PLANK, z=14)
        for j in range(7):
            ox, oy = (j % 3) * 2.6 - 2.6, (j // 3) * 2.6 - 2.6
            v.ell(cx + ox + 0.4, y1 - 5.5 + oy, 23.5 + (j % 2) * 0.6, 1.8, 1.8, 1.6, mat)
    crate(v, x1 + 2, y1 - 6, 8, PLANK); v.ell(x1 + 6, y1 - 2, 9, 3.5, 3.5, 2, APPLE)
    barrel(v, x0 - 5, y1 + 2, 3.2, 8)
    return v

@bld('stall-red')
def stall_r(): return stall(RED_AWN)
@bld('stall-blue')
def stall_b(): return stall(BLU_AWN)
@bld('stall-green')
def stall_g(): return stall(GRN_AWN)

@bld('well')
def well():
    v = Vol(-22, 22, -22, 22, 0, 70)
    PAL[52] = Mat('#9a8f86', t_stone, params={'c': (0, 0), 'r': 12, 'ch': 4.5, 'bl': 6, 'moss': 40, 'mossh': 10})
    v.cyl(0, 0, 13, 0, 13, 52, rin=9)
    v.cyl(0, 0, 14, 12, 15, STONE_D, rin=9)
    v.cyl(0, 0, 9, 0, 9, WATER)
    for py in (-12, 12):
        v.box(-1.5, 1.5, py - 1.5, py + 1.5, 13, 40, TIMBER)
    v.cyl(0, 0, 0, 0, 0, 0) if False else None
    v.box(-1, 1, -14, 14, 30, 32.5, WOOD_L)
    v.box(-1, 1, 14, 18, 28, 29.5, METAL)
    v.box(-2.5, 2.5, -1.5, 1.5, 20, 25, PLANK); v.box(-0.3, 0.3, -0.3, 0.3, 25, 30, ROPE)
    v.roof(-12, 12, -18, 18, 36, 52, ROOF_R, axis='y', th=3.5)
    v.box(-12, 12, -0.8, 0.8, 50, 53, TIMBER) if False else None
    return v

@bld('noticeboard')
def noticeboard():
    v = Vol(-22, 22, -10, 12, 0, 56)
    for px in (-15, 13):
        v.box(px, px + 2.5, -1, 1.5, 0, 42, TIMBER)
    v.box(-16, 16, -0.5, 1.5, 14, 36, PLANK)
    v.box(-17, 17, -0.6, 2.2, 13, 14.5, TIMBER); v.box(-17, 17, -0.6, 2.2, 35.5, 37, TIMBER)
    papers = [(-13, 18, 8, 9, PAPER), (-3, 24, 7, 9, CREAM), (6, 17, 7, 8, PAPER), (-12, 28, 6, 6, CREAM), (5, 26, 8, 7, PAPER)]
    for (a, z, w, h, m) in papers:
        v.box(a, a + w, 1.5, 2.1, z, z + h, m)
        v.box(a + w / 2 - 0.5, a + w / 2 + 0.5, 2.0, 2.5, z + h - 1.5, z + h - 0.5, CLOTH_R)
    v.roof(-19, 19, -5, 7, 38, 48, ROOF_R, axis='x', th=2.5)
    return v

@bld('campfire')
def campfire():
    v = Vol(-14, 14, -14, 14, 0, 26)
    for k in range(9):
        a = k / 9 * 2 * np.pi
        v.ell(9 * np.cos(a), 9 * np.sin(a), 1.2, 2.8, 2.6, 2.2, STONE_D)
    for a in (0.3, 1.9, 3.5, 5.0):
        c, s = np.cos(a), np.sin(a)
        v.capsule((6 * c, 6 * s, 1.2), (-1 * c, -1 * s, 4.5), 1.4, BARK)
    v.cyl(0, 0, 3.5, 1, 3, COAL)
    v.put((-6, 6, -6, 6, 2, 22), lambda X, Y, Z: (X ** 2 + Y ** 2) <= (4.6 * (1 - (Z - 2) / 18) ** 1.2 + 0.9 * np.sin(Z * 0.9 + np.arctan2(Y, X) * 3)) ** 2, FIRE)
    return v

def canopy(v, cx, cy, cz, r, mat, seed=1, n=9):
    rng = np.random.default_rng(seed)
    blobs = [(cx, cy, cz, r * 0.8)]
    for k in range(n):
        a = rng.uniform(0, 2 * np.pi); e = rng.uniform(-0.6, 0.8)
        d = r * rng.uniform(0.45, 0.7)
        blobs.append((cx + d * np.cos(a) * np.cos(e), cy + d * np.sin(a) * np.cos(e), cz + d * np.sin(e) * 0.8, r * rng.uniform(0.42, 0.58)))
    for (bx, by, bz, br) in blobs:
        v.put((bx - br - 2, bx + br + 2, by - br - 2, by + br + 2, bz - br - 2, bz + br + 2),
              lambda X, Y, Z, bx=bx, by=by, bz=bz, br=br: (X - bx) ** 2 + (Y - by) ** 2 + ((Z - bz) * 1.1) ** 2 <= (br + 1.4 * (hash3(np.floor(X / 2).astype(np.int64), np.floor(Y / 2).astype(np.int64), np.floor(Z / 2).astype(np.int64), 5) - 0.5) * 2) ** 2, mat)

@bld('tree-oak')
def oak():
    v = Vol(-34, 34, -34, 34, 0, 96)
    v.put((-6, 6, -6, 6, 0, 50), lambda X, Y, Z: X ** 2 + Y ** 2 <= (2.6 + 3.2 * np.clip(1 - Z / 9, 0, 1) ** 2) ** 2, BARK)
    v.capsule((0, 0, 30), (10, -4, 46), 1.8, BARK); v.capsule((0, 0, 32), (-9, 6, 44), 1.8, BARK)
    canopy(v, 0, 0, 52, 27, LEAF, seed=3, n=12)
    return v

@bld('tree-pine')
def pine():
    v = Vol(-22, 22, -22, 22, 0, 110)
    v.cyl(0, 0, 2.4, 0, 30, BARK)
    for k, (z0, r) in enumerate(((16, 19), (36, 16), (54, 12.5), (70, 9))):
        v.put((-r - 2, r + 2, -r - 2, r + 2, z0, z0 + 30),
              lambda X, Y, Z, z0=z0, r=r: np.hypot(X, Y) <= (r * (1 - (Z - z0) / 30) + 1.4 * np.sin(np.arctan2(Y, X) * 9) * (1 - (Z - z0) / 30)), LEAF_D)
    return v

@bld('bush')
def bush():
    v = Vol(-18, 18, -18, 18, 0, 26)
    canopy(v, 0, 0, 8, 11, LEAF_F, seed=7, n=7)
    return v

@bld('tree-autumn')
def autumn():
    v = Vol(-26, 26, -26, 26, 0, 80)
    v.put((-6, 6, -6, 6, 0, 40), lambda X, Y, Z: X ** 2 + Y ** 2 <= (2.2 + 2.6 * np.clip(1 - Z / 8, 0, 1) ** 2) ** 2, BARK)
    canopy(v, 0, 0, 50, 19, LEAF_A, seed=11, n=9)
    return v

@bld('rocks')
def rocks():
    v = Vol(-18, 18, -16, 16, 0, 18)
    for (x, y, rx, ry, rz) in ((-4, -2, 9, 7, 9), (6, 4, 6, 5, 6), (-9, 7, 4, 4, 4), (9, -6, 3.5, 3, 3)):
        v.put((x - rx - 2, x + rx + 2, y - ry - 2, y + ry + 2, 0, rz + 2),
              lambda X, Y, Z, x=x, y=y, rx=rx, ry=ry, rz=rz: ((X - x) / rx) ** 2 + ((Y - y) / ry) ** 2 + (Z / rz) ** 2 <= 1 - 0.25 * (hash3(np.floor(X / 3).astype(np.int64), np.floor(Y / 3).astype(np.int64), np.floor(Z / 3).astype(np.int64), 9)), STONE_D)
    v.put((-16, 16, -14, 14, 0, 10), lambda X, Y, Z: (Z > 6) & (hash3(np.floor(X / 2).astype(np.int64), np.floor(Y / 2).astype(np.int64), np.zeros_like(X, dtype=np.int64), 3) > 0.7) & (v.m[0:1, 0:1, 0:1].size > 0) & False, MOSS)
    return v

def fence(axis):
    v = Vol(-20, 20, -20, 20, 0, 18)
    for k in (-15, 0, 15):
        if axis == 'x': v.box(k - 1.2, k + 1.2, -1.2, 1.2, 0, 15, TIMBER); v.cone(k, 0, 1.3, 15, 17, TIMBER)
        else: v.box(-1.2, 1.2, k - 1.2, k + 1.2, 0, 15, TIMBER); v.cone(0, k, 1.3, 15, 17, TIMBER)
    for zz in (5, 11):
        if axis == 'x': v.box(-16, 16, -0.6, 0.6, zz, zz + 2, WOOD_L)
        else: v.box(-0.6, 0.6, -16, 16, zz, zz + 2, WOOD_L)
    return v

@bld('fence-x')
def fx(): return fence('x')
@bld('fence-y')
def fy(): return fence('y')

def build(name):
    t = time.time()
    s = {'magetower': 1.3}.get(name, S_B)
    engine.VS_DEFAULT[0] = 1 / s
    v = B[name]()
    r = trim(render(v, PAL, S=s))
    print(name, 'rendered', r['color'].shape, 'anchor', r['anchor'], f'{time.time() - t:.1f}s', flush=True)
    return r

if __name__ == '__main__':
    import os
    OUT = os.environ.get('OUT', 'assets')
    os.makedirs(OUT, exist_ok=True)
    meta = {}
    if os.path.exists(OUT + '/meta.json'): meta = json.load(open(OUT + '/meta.json'))
    for name in (sys.argv[1:] or list(B)):
        r = build(name)
        from PIL import Image
        save2x(r['color'], f'{OUT}/b-{name}.png')
        save2x(r['shadow'], f'{OUT}/b-{name}-shadow.png')
        save2x(r['emis'], f'{OUT}/b-{name}-night.png')
        save2x(r['nightlit'], f'{OUT}/b-{name}-nightlit.png')
        save2x(r['cast'], f'{OUT}/b-{name}-cast.png')
        meta['b-' + name] = {'w': int(r['color'].shape[1]), 'h': int(r['color'].shape[0]), 'ax': int(r['anchor'][0]), 'ay': int(r['anchor'][1])}
        json.dump(meta, open(OUT + '/meta.json', 'w'), indent=1)
