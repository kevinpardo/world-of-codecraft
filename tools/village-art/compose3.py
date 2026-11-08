"""v3 compositor: same as v2, but small props and heroes receive cast shadows PER PIXEL (projected along the sun
direction onto the cast-shadow layers of the OTHER objects), instead of one darkening value per sprite that also
counted the sprite's own contact shadow (the 'dark veil')."""
import os, sys
import numpy as np
from PIL import Image
from scipy import ndimage
import compose2 as C2
import compose as C
from engine import over, BAYER, L

A = 'assets/'
W, H = C2.W, C2.H
load = C.load
SHC = np.array([26, 20, 56], np.float32)
KU = -(L[0] - L[1]) / L[2]          # screen shift of the shadow-catching ground point per unit of height
KV = -((L[0] + L[1]) / 2) / L[2]

def bbox(name, u, v, suffix=''):
    m = C2.META[name]
    return int(u - m['ax']), int(v - m['ay'])

def receive(c, name, u, v, objects, idx, night):
    """darken pixels of sprite c (uint8 RGBA, local) where another object's cast shadow falls on them."""
    m = C2.META[name]; x0, y0 = int(u - m['ax']), int(v - m['ay'])
    hh, ww = c.shape[:2]
    zmax = max(1, v - y0)
    wx0, wx1 = x0 - 2, x0 + ww + int(KU * zmax) + 4
    wy0, wy1 = y0 - 4, int(v) + 6
    loc = np.zeros((wy1 - wy0, wx1 - wx0), np.float32)
    for j, (n2, u2, v2, dp2, ex2) in enumerate(objects):
        if j == idx or not os.path.exists(A + n2 + '-cast.png'): continue
        m2 = C2.META[n2]; ax0, ay0 = int(u2 - m2['ax']), int(v2 - m2['ay'])
        s = load(n2 + '-cast')
        sh_, sw_ = s.shape[:2]
        ix0, iy0 = max(wx0, ax0), max(wy0, ay0); ix1, iy1 = min(wx1, ax0 + sw_), min(wy1, ay0 + sh_)
        if ix1 <= ix0 or iy1 <= iy0: continue
        # a caster only shadows receivers standing behind its front edge is not required: the cast layer is ground-truth
        loc[iy0 - wy0:iy1 - wy0, ix0 - wx0:ix1 - wx0] = np.maximum(loc[iy0 - wy0:iy1 - wy0, ix0 - wx0:ix1 - wx0], s[iy0 - ay0:iy1 - ay0, ix0 - ax0:ix1 - ax0, 3] / 255)
    if not loc.any(): return c
    loc = ndimage.gaussian_filter(loc, 2.5)
    ys, xs = np.nonzero(c[..., 3] > 0)
    py = ys + y0; px = xs + x0
    z = np.clip(v - py, 0, None)
    gx = np.round(px + KU * z).astype(int) - wx0; gy = np.round(v + KV * z).astype(int) - wy0
    ok = (gx >= 0) & (gx < loc.shape[1]) & (gy >= 0) & (gy < loc.shape[0])
    k = np.zeros(len(ys), np.float32); k[ok] = loc[gy[ok], gx[ok]]
    k = np.floor(k * 4 + BAYER[py % 4, px % 4] * 0.6 + 0.5) / 4  # stepped like the ground shadow
    k = np.clip(k, 0, 1) * (0.46 if not night else 0.2)
    c = c.copy()
    col = c[ys, xs, :3].astype(np.float32)
    c[ys, xs, :3] = np.clip(col * (1 - k[:, None]) + SHC * k[:, None], 0, 255).astype(np.uint8)
    return c

def compose(night=False, objects=None, effects=None):
    g, kind = C2.ground()
    img = np.zeros((H, W, 4), np.float32); img[..., :3] = g; img[..., 3] = 255
    emis = np.zeros((H, W, 4), np.float32); nl = np.zeros((H, W, 3), np.float32)
    sh = np.zeros((H, W), np.float32)
    for (name, u, v, dp, extra) in objects:
        m = C2.META[name]; s = load(name + '-shadow')
        x0, y0 = int(u - m['ax']), int(v - m['ay'])
        hh, ww = s.shape[:2]
        ys0, xs0 = max(0, y0), max(0, x0); ys1, xs1 = min(H, y0 + hh), min(W, x0 + ww)
        if ys1 > ys0 and xs1 > xs0:
            sh[ys0:ys1, xs0:xs1] = np.maximum(sh[ys0:ys1, xs0:xs1], s[ys0 - y0:ys1 - y0, xs0 - x0:xs1 - x0, 3] / 255)
    shd = sh * (0.45 if night else 1.0)
    img[..., :3] = img[..., :3] * (1 - shd[..., None]) + SHC * shd[..., None]
    order = sorted(range(len(objects)), key=lambda i: objects[i][2] + objects[i][3])
    for i in order:
        name, u, v, dp, extra = objects[i]
        m = C2.META[name]; x0, y0 = int(u - m['ax']), int(v - m['ay'])
        for (kind_, ename, eu, ev) in extra.get('under', []):
            e = load(ename); over(img, e, int(eu - e.shape[1] / 2), int(ev - e.shape[0] / 2)); over(emis, e, int(eu - e.shape[1] / 2), int(ev - e.shape[0] / 2), 0.6)
        c = load(name)
        if dp <= 10:
            c = receive(c, name, u, v, objects, i, night)
        hh, ww = c.shape[:2]
        ys0, xs0 = max(0, y0), max(0, x0); ys1, xs1 = min(H, y0 + hh), min(W, x0 + ww)
        if ys1 > ys0 and xs1 > xs0:
            a = c[ys0 - y0:ys1 - y0, xs0 - x0:xs1 - x0, 3] > 0
            emis[ys0:ys1, xs0:xs1][a] = 0; nl[ys0:ys1, xs0:xs1][a] = 0
            if os.path.exists(A + name + '-nightlit.png'):
                ln = load(name + '-nightlit')[ys0 - y0:ys1 - y0, xs0 - x0:xs1 - x0]
                msk = ln[..., 3] > 0
                nl[ys0:ys1, xs0:xs1][msk] = ln[msk][:, :3]
        over(img, c, x0, y0)
        if os.path.exists(A + name + '-night.png'):
            e = load(name + '-night')
            if e[..., 3].any(): over(emis, e, x0, y0)
        for (ename, eu, ev) in extra.get('above', []):
            e = load(ename); over(img, e, int(eu - e.shape[1] / 2), int(ev - e.shape[0])); over(emis, e, int(eu - e.shape[1] / 2), int(ev - e.shape[0]))
    for fx in (effects or []):
        fx(img, emis)
    rgb = img[..., :3]
    if night:
        lum = rgb @ np.array([0.3, 0.55, 0.15])
        nightc = rgb * np.array([0.20, 0.25, 0.46]) + lum[..., None] * np.array([0.05, 0.07, 0.16]) + np.array([6, 9, 26])
        e = emis[..., :3] * (emis[..., 3:4] / 255)
        em = emis[..., 3] > 160
        g1 = np.stack([ndimage.gaussian_filter(e[..., k], 3) for k in range(3)], -1) * 3.4
        g2 = np.stack([ndimage.gaussian_filter(e[..., k], 22) for k in range(3)], -1) * 11.0
        v_, u_ = np.mgrid[0:H, 0:W]
        glow = np.clip(np.floor((g1 + g2) / 16 + BAYER[v_ % 4, u_ % 4][..., None] * 0.9) * 16, 0, 255)
        nlq = np.floor(nl / 24 + BAYER[v_ % 4, u_ % 4][..., None] * 0.8) * 24
        lit = nightc + (glow + nlq * 0.9) * (rgb / 255 * 0.85 + 0.15)
        lit[em] = emis[em, :3]
        rgb = lit
    return np.clip(rgb, 0, 255).astype(np.uint8)

if __name__ == '__main__':
    O, E = C2.scene()
    day = compose(False, O, E)
    out = next((a for a in sys.argv[1:] if not a.startswith('--')), '')
    C2.save2(day, f'mock-wide{out}.png'); C2.save2(day[:, 500:2500], f'mock{out}.png')
    if '--day' not in sys.argv:
        night = compose(True, O, E)
        C2.save2(night, f'mock-wide-night{out}.png'); C2.save2(night[:, 500:2500], f'mock-night{out}.png')
    print('ok')
