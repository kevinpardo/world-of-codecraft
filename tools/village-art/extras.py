"""2D pieces (markers, rings, UI frame, ground tiles) and voxel icons, same palette rules."""
import json, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from engine import Vol, render, trim, save2x, ramp, outline_of, vnoise2, hash3, BAYER, hx
from tex import *

FONT = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'mods', 'world-of-codecraft', 'fonts') + '/'

def mask_from(rows):
    return np.array([[c == 'X' for c in r] for r in rows])

def shade_glyph(m, rp, pad=3):
    h, w = m.shape
    H, W = h + pad * 2, w + pad * 2
    out = np.zeros((H, W, 4), np.float32)
    M = np.zeros((H, W), bool); M[pad:pad + h, pad:pad + w] = m
    yy, xx = np.mgrid[0:H, 0:W]
    lv = 5.2 - (yy - pad) / h * 3.2
    up = np.roll(M, 1, 0); lf = np.roll(M, 1, 1); dn = np.roll(M, -1, 0); rt = np.roll(M, -1, 1)
    lv = lv + (~up) * 1.2 + (~lf) * 0.6 - (~dn) * 1.0 - (~rt) * 0.8
    lv = lv + BAYER[yy % 4, xx % 4] * 0.3
    idx = np.clip(np.round(lv), 0, len(rp) - 1).astype(int)
    out[M, :3] = rp[idx[M]]; out[M, 3] = 255
    ol = outline_of(rp)
    edge = (~M) & (np.roll(M, 1, 0) | np.roll(M, -1, 0) | np.roll(M, 1, 1) | np.roll(M, -1, 1))
    out[edge, :3] = ol; out[edge, 3] = 255
    # soft glow halo (2 steps)
    from scipy import ndimage
    near = ndimage.binary_dilation(M | edge, iterations=2) & ~(M | edge)
    out[near, :3] = rp[5]; out[near, 3] = 70
    return out.astype(np.uint8)

EXCL = ['..XXXXX..', '.XXXXXXX.', '.XXXXXXX.', '.XXXXXXX.', '..XXXXX..', '..XXXXX..', '..XXXXX..', '...XXX...',
        '...XXX...', '...XXX...', '....X....', '.........', '...XXX...', '..XXXXX..', '..XXXXX..', '...XXX...']
QUES = ['...XXXXX...', '..XXXXXXX..', '.XXXX.XXXX.', '.XXX...XXX.', '.XXX...XXX.', '.......XXX.', '......XXXX.',
        '.....XXXX..', '....XXXX...', '....XXX....', '....XXX....', '...........', '....XXX....', '...XXXXX...',
        '...XXXXX...', '....XXX....']

def ring(w, h, col_ramp, thick=2, ticks=True):
    W, H = w + 6, h + 6
    yy, xx = np.mgrid[0:H, 0:W] + 0.5
    cx, cy = W / 2, H / 2
    d = np.sqrt(((xx - cx) / (w / 2)) ** 2 + ((yy - cy) / (h / 2)) ** 2)
    band = (d <= 1.0) & (d >= 1.0 - thick / (h / 2) * 1.1)
    out = np.zeros((H, W, 4), np.float32)
    front = yy > cy
    lv = np.where(front, 4.6, 2.6) + (xx < cx) * 0.6
    idx = np.clip(np.round(lv + BAYER[(yy.astype(int)) % 4, xx.astype(int) % 4] * 0.4), 0, 6).astype(int)
    out[band, :3] = col_ramp[idx[band]]; out[band, 3] = 255
    inner = (d < 1.0 - thick / (h / 2) * 1.1)
    out[inner, :3] = col_ramp[4]; out[inner, 3] = 46
    if ticks:
        for (tx, ty) in ((cx, 1.5), (cx, H - 2.5), (2.5, cy), (W - 3.5, cy)):
            out[int(ty) - 1:int(ty) + 2, int(tx) - 1:int(tx) + 2, :3] = col_ramp[6]; out[int(ty) - 1:int(ty) + 2, int(tx) - 1:int(tx) + 2, 3] = 255
    return out.astype(np.uint8)

def icons():
    res = {}
    v = Vol(-12, 12, -12, 12, 0, 16, vs=0.5)
    for k, (x, y, n) in enumerate(((0, 0, 7), (-5, 4, 4), (5, -3, 3), (4, 6, 2))):
        for j in range(n):
            v.cyl(x + 0.3 * np.sin(j * 1.7), y + 0.3 * np.cos(j * 2.1), 4.2, j * 1.6, j * 1.6 + 1.3, GOLD)
            v.cyl(x + 0.3 * np.sin(j * 1.7), y + 0.3 * np.cos(j * 2.1), 3.2, j * 1.6 + 1.2, j * 1.6 + 1.5, GOLD)
    v.ell(-1, -5, 2.4, 2.6, 2.6, 2.4, PAL[21] and 21)  # a gem
    res['icon-gold'] = v
    v = Vol(-14, 14, -12, 12, 0, 16, vs=0.5)
    logs = ((0, -5, 2.8), (0, 0, 2.8), (0, 5, 2.8), (0, -2.5, 7.3), (0, 2.5, 7.3), (0, 0, 11.8))
    for (x, y, z) in logs:
        v.put((-11, 11, y - 3, y + 3, z - 3, z + 3), lambda X, Y, Z, y=y, z=z: ((Y - y) ** 2 + (Z - z) ** 2 <= 2.5 ** 2) & (np.abs(X) < 9.5), BARK)
        v.put((-11, 11, y - 3, y + 3, z - 3, z + 3), lambda X, Y, Z, y=y, z=z: ((Y - y) ** 2 + (Z - z) ** 2 <= 2.0 ** 2) & (np.abs(X) < 10) & (np.abs(X) >= 9.5), WOOD_L)
    res['icon-wood'] = v
    return res

# ---------------------------------------------------------------- ground tiles (seamless in iso)
GR = ramp('#5f9a3a', hs=30, light=1.3, dark=0.3)
GR2 = ramp('#4f8a3c', hs=30, light=1.3, dark=0.3)
DR = ramp('#9a7650', hs=22)
CB = ramp('#9c958c', hs=24, light=1.18)
WR = ramp('#2f80b4', hs=14, light=1.35)
SO = ramp('#7a5434', hs=22)
WH = ramp('#d6ae4a', hs=16, light=1.25)

def ground_tex(kind, x, y, sx, sy, variant=0, macro=0):
    """x,y world coords (float arrays); sx,sy screen px for dithering. Returns RGB float. Period 32 world units."""
    P = 32
    if kind == 'grass':
        n = vnoise2(x, y, 16, 1, P) * 1.4 + vnoise2(x, y, 8, 2, P) * 0.9 + vnoise2(x, y, 4, 3, P) * 0.5
        lv = 2.2 + n + macro
        h = hash3(np.floor(x).astype(np.int64) % P, np.floor(y).astype(np.int64) % P, np.zeros_like(x, dtype=np.int64), 4 + variant)
        lv = lv + (h > 0.90) * 0.9 - (h < 0.06) * 0.7
        # grass tufts: 3x3 world cells, lit blade tips, shaded roots (micro contrast)
        cx = np.floor(x / 3) * 3 + 1.5 + (hash3(np.floor(x / 3).astype(np.int64) % 11, np.floor(y / 3).astype(np.int64) % 11, np.zeros_like(x, dtype=np.int64), 61) - 0.5) * 1.6
        cy = np.floor(y / 3) * 3 + 1.5
        du = (x - cx) - (y - cy); dv = ((x - cx) + (y - cy)) / 2
        tuft = (np.abs(du) < 1.3 - dv * 0.25) & (dv > -2.0) & (dv < 1.0)
        on = hash3(np.floor(x / 3).astype(np.int64) % 11, np.floor(y / 3).astype(np.int64) % 11, np.ones_like(x, dtype=np.int64), 62) > 0.45
        lv = lv + np.where(tuft & on, np.where(dv < -0.8, 1.2, np.where(dv > 0.3, -1.1, 0.3)), 0)
        lv = lv + BAYER[sy % 4, sx % 4] * 0.35
        idx = np.clip(np.round(lv), 0, 6).astype(int)
        mix = vnoise2(x, y, 16, 9, P) > 0.62
        c = np.where(mix[..., None], GR2[idx], GR[idx])
        if variant:  # flowers away from tile edges
            fx, fy = x % P, y % P
            inner = (fx > 4) & (fx < 28) & (fy > 4) & (fy < 28)
            fl = inner & (hash3(np.floor(x).astype(np.int64) % P, np.floor(y).astype(np.int64) % P, np.ones_like(x, dtype=np.int64), 30 + variant) > 0.985)
            fcol = np.array([hx('#f4e9c8'), hx('#f2c94c'), hx('#d86a8a')][variant % 3], np.float32)
            c = np.where(fl[..., None], fcol, c)
        return c
    if kind == 'dirt':
        n = vnoise2(x, y, 8, 11, P) * 1.2 + vnoise2(x, y, 4, 12, P) * 0.6
        lv = 2.4 + n + macro
        h = hash3(np.floor(x).astype(np.int64) % P, np.floor(y).astype(np.int64) % P, np.zeros_like(x, dtype=np.int64), 13)
        lv = lv + (h > 0.93) * 2.0 - (h < 0.05) * 1.0
        lv = lv - (np.abs(((x + y * 0.0) % 16) - 8) < 0.7) * 0.0
        lv = lv + BAYER[sy % 4, sx % 4] * 0.3
        return DR[np.clip(np.round(lv), 0, 6).astype(int)]
    if kind == 'paved':
        s = 8.0
        gx = np.floor(x / s); gy = np.floor((y + (gx % 2) * s / 2) / s)
        fx = x - gx * s; fy = (y + (gx % 2) * s / 2) - gy * s
        sid = hash3(gx.astype(np.int64) % 4, gy.astype(np.int64) % 4, np.zeros_like(x, dtype=np.int64), 21)
        lv = 3.0 + (sid - 0.5) * 1.6 + macro * 0.6
        lv = lv + (fx < 1.6) * 0.9 + (fy < 1.6) * 0.6 - (fx > s - 1.6) * 0.8 - (fy > s - 1.6) * 0.8
        mortar = (fx < 0.6) | (fy < 0.6)
        lv = np.where(mortar, 0.6, lv)
        lv = lv + BAYER[sy % 4, sx % 4] * 0.3
        return CB[np.clip(np.round(lv), 0, 6).astype(int)]
    if kind == 'water':
        n = vnoise2(x, y, 16, 31, P) * 1.0 + vnoise2(x, y, 8, 32, P) * 0.6
        lv = 2.0 + n + macro
        wv = np.sin((x - y) * 0.55 + vnoise2(x, y, 8, 33, P) * 6.0) + np.sin(x * 0.39 + y * 0.39 + variant)
        lv = lv + (wv > 1.55) * 2.6 + (wv > 1.85) * 1.0
        lv = lv + BAYER[sy % 4, sx % 4] * 0.3
        return WR[np.clip(np.round(lv), 0, 6).astype(int)]
    if kind == 'crop':
        row = (y % 8)
        furrow = np.abs(row - 4)
        lv = 3.2 - furrow * 0.5 + vnoise2(x, y, 4, 41, P) * 0.6 + macro * 0.5
        c = SO[np.clip(np.round(lv + BAYER[sy % 4, sx % 4] * 0.3), 0, 6).astype(int)]
        # plants: little sprouts on each ridge, lit top / shadow bottom, mixed wheat + greens
        px_ = np.floor(x / 3); h = hash3(px_.astype(np.int64) % 32, np.floor(y / 8).astype(np.int64) % 4, np.zeros_like(x, dtype=np.int64), 42)
        fx = x - px_ * 3
        plant = (furrow > 1.2) & (furrow < 3.6) & (fx > 0.4) & (fx < 2.6) & (h > 0.18)
        lvp = 2.6 + (furrow - 1.2) * 1.0 + (h - 0.5) * 1.5
        green = (np.floor(y / 16) % 2 == 1)
        pc = np.where(green[..., None], GR[np.clip(np.round(lvp + 0.3), 0, 6).astype(int)], WH[np.clip(np.round(lvp), 0, 6).astype(int)])
        return np.where(plant[..., None], pc, c)
    raise KeyError(kind)

def tile(kind, variant=0):
    H, W = 32, 64
    v, u = np.mgrid[0:H, 0:W]
    uc = u + 0.5 - 32; vc = v + 0.5
    x = vc + uc / 2; y = vc - uc / 2
    inside = (x >= 0) & (x < 32) & (y >= 0) & (y < 32)
    c = ground_tex(kind, x, y, u, v, variant)
    out = np.zeros((H, W, 4), np.uint8)
    out[..., :3] = c.astype(np.uint8); out[..., 3] = inside * 255
    return out

def ui_frame(W=260, Hh=150, title='Valbrume'):
    out = np.zeros((Hh, W, 4), np.float32)
    yy, xx = np.mgrid[0:Hh, 0:W]
    WD = ramp('#7a4a28', hs=24); GD = PAL[13].ramp; IR = ramp('#4a4658', hs=14)
    # background: dark planks
    plank = (yy // 12)
    lv = 1.4 + (hash3(plank, plank * 3, plank * 0, 7) - 0.5) * 0.8 + np.sin(xx * 0.21 + plank * 2.1 + np.sin(xx * 0.05) * 3) * 0.35
    lv = np.where(yy % 12 == 0, 0.2, lv); lv = np.where(yy % 12 == 1, lv + 0.6, lv)
    out[..., :3] = WD[np.clip(np.round(lv + BAYER[yy % 4, xx % 4] * 0.3), 0, 6).astype(int)]; out[..., 3] = 255
    # border: 8 px carved wood with bevel + gold inner trim
    d = np.minimum(np.minimum(xx, W - 1 - xx), np.minimum(yy, Hh - 1 - yy))
    lt = (xx < W - 1 - xx) & (yy < Hh - 1 - yy)
    bl = 3.6 + np.where((xx + yy) < (W - 1 - xx + Hh - 1 - yy), 1.0, -1.0) * (d < 8) + (hash3(xx // 3, yy // 3, xx * 0, 3) - 0.5) * 0.6
    border = (d >= 1) & (d < 8)
    out[border, :3] = WD[np.clip(np.round(bl[border] - (d[border] > 5) * 0.8), 0, 6).astype(int)]
    out[d == 0, :3] = outline_of(WD)
    gt = (d == 8) | (d == 9)
    out[gt, :3] = GD[np.where(d[gt] == 8, 5, 3)]
    out[d == 10, :3] = WD[0]
    # corner ornaments (gold diamonds + rivets)
    for (cx, cy) in ((6, 6), (W - 7, 6), (6, Hh - 7), (W - 7, Hh - 7)):
        dd = np.abs(xx - cx) + np.abs(yy - cy)
        m = dd <= 7
        out[m, :3] = GD[np.clip(6 - dd[m] // 2 - ((xx[m] - cx + yy[m] - cy) > 0) * 2, 0, 6)]
        out[dd == 8, :3] = outline_of(GD)
        out[(dd <= 1), :3] = IR[1]
    for k in range(20, W - 20, 24):
        for cy in (3, Hh - 4):
            out[cy - 1:cy + 1, k - 1:k + 1, :3] = IR[5]; out[cy:cy + 1, k:k + 1, :3] = IR[2]
    # header plate: red cloth ribbon with gold edges and swallowtails
    hx0, hx1, hy0, hy1 = 40, W - 40, 12, 32
    rb = ramp('#b8352c', hs=24)
    for y in range(hy0 - 2, hy1 + 2):
        for x in range(hx0 - 14, hx1 + 14):
            inside_main = hx0 <= x < hx1 and hy0 <= y < hy1
            tail = (hx0 - 14 <= x < hx0 or hx1 <= x < hx1 + 14) and hy0 + 3 <= y < hy1 + 1 and not (abs(y - (hy0 + hy1 + 4) / 2) < (14 - min(abs(x - hx0 + 14), abs(hx1 + 13 - x))) * 0.5 and (x < hx0 - 6 or x > hx1 + 5))
            if inside_main or tail:
                l = 3.5 + (1.2 if y < (hy0 + hy1) / 2 else -0.4) - (0.0 if inside_main else 1.2)
                out[y, x, :3] = rb[int(np.clip(round(l + BAYER[y % 4, x % 4] * 0.4), 0, 6))]
                if inside_main and (y in (hy0, hy1 - 1)):
                    out[y, x, :3] = GD[5 if y == hy0 else 2]
    img = Image.fromarray(out.astype(np.uint8))
    dr = ImageDraw.Draw(img); dr.fontmode = '1'
    f = ImageFont.truetype(FONT + 'Jacquard24-Regular.ttf', 24)
    tw = dr.textlength(title, font=f)
    tx, ty = W / 2 - tw / 2, hy0 - 7
    dr.text((tx + 1, ty + 1), title, font=f, fill=tuple(int(c) for c in outline_of(rb)))
    dr.text((tx, ty), title, font=f, fill=tuple(int(c) for c in GD[5]))
    # body text sample
    f2 = ImageFont.truetype(FONT + 'Jersey15-Regular.ttf', 15)
    pr = PAL[36].ramp
    dr.rectangle((20, 44, W - 21, Hh - 21), fill=tuple(int(c) for c in pr[5]), outline=tuple(int(c) for c in WD[0]))
    dr.line((21, Hh - 22, W - 22, Hh - 22), fill=tuple(int(c) for c in pr[3]))
    dr.text((28, 48), 'Aelith, mage elfe', font=f2, fill=tuple(int(c) for c in WD[1]))
    dr.text((28, 66), 'Tour des mages  -  En quete', font=f2, fill=tuple(int(c) for c in ramp('#3f8a3a')[2]))
    dr.text((28, 84), 'Quete : refonte du bourg', font=f2, fill=tuple(int(c) for c in WD[2]))
    # health/progress bar
    bx0, by0 = 28, 108
    dr.rectangle((bx0, by0, W - 30, by0 + 7), fill=tuple(int(c) for c in WD[0]))
    gg = ramp('#4fb04a', hs=24)
    for x in range(bx0 + 1, int(bx0 + (W - 30 - bx0) * 0.68)):
        for y in range(by0 + 1, by0 + 7):
            dr.point((x, y), fill=tuple(int(c) for c in gg[5 if y < by0 + 3 else 3]))
    return np.array(img)

if __name__ == '__main__':
    os.makedirs('assets', exist_ok=True)
    meta = json.load(open('assets/meta.json')) if os.path.exists('assets/meta.json') else {}
    Y = ramp('#f2c230', hs=30, light=1.25, dark=0.35); Q = ramp('#ffd65a', hs=18, light=1.3, dark=0.35)
    save2x(shade_glyph(np.kron(mask_from(EXCL), np.ones((2, 2), bool)), Y), 'assets/m-blocked.png')
    save2x(shade_glyph(np.kron(mask_from(QUES), np.ones((2, 2), bool)), Q), 'assets/m-done.png')
    save2x(ring(54, 27, ramp('#4fc04a', hs=24)), 'assets/ring-selected.png')
    save2x(ring(54, 27, ramp('#f2c230', hs=24)), 'assets/ring-blocked.png')
    save2x(ring(54, 27, ramp('#e8b040', hs=20), thick=1, ticks=False), 'assets/ring-done.png')
    for name, v in icons().items():
        r = trim(render(v, PAL, ao_strength=0.3, dither=0.15, ground=False))
        save2x(r['color'], f'assets/{name}.png')
    for k in ('grass', 'dirt', 'paved', 'water', 'crop'):
        save2x(tile(k), f'assets/t-{k}.png')
    save2x(tile('grass', 1), 'assets/t-grass-flowers.png')
    save2x(ui_frame(), 'assets/ui-panel.png')
    print('ok')
