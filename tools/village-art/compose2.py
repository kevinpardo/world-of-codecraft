"""v2 mock-ups: buildings at S=1.4, 70-90 px heroes, GI ground, local night lights, shadows on units.
World strip 3000x400 logical (mock-wide*.png); mock.png / mock-night.png = the 2000x400 camera view."""
import json, os
import numpy as np
from PIL import Image
from scipy import ndimage
import compose as C
from engine import over, vnoise2, hash3, BAYER, hx, ramp
from extras import ground_tex, DR, WR

A = 'assets/'
META = json.load(open(A + 'meta.json'))
W, H = 3000, 400
C.W, C.H = W, H
U0, V0 = 1500, 200
C.U0, C.V0 = U0, V0
load = C.load
s2w = C.s2w

def ground():
    v, u = np.mgrid[0:H, 0:W]
    x, y = s2w(u + 0.5, v + 0.5)
    nz = (vnoise2(x, y, 6, 51) - 0.5) * 5 + (vnoise2(x, y, 2.5, 52) - 0.5) * 2
    kind = np.zeros((H, W), int)
    paths = [[(0, 330), (200, 320), (420, 372), (640, 345), (900, 330), (1060, 360)],
             [(1060, 360), (1350, 380), (1500, 372)],
             [(1720, 360), (1900, 350), (2150, 372), (2330, 340), (2560, 330), (2700, 300)],
             [(860, 260), (900, 140), (950, 0)], [(1650, 250), (1700, 120), (1760, 0)], [(2350, 280), (2420, 150), (2460, 0)]]
    for p in paths:
        pw = [s2w(*q) for q in p]
        for a, b in zip(pw[:-1], pw[1:]):
            d = C.seg_dist(x, y, a, b)
            kind = np.where(d + nz < 17, 1, kind)
    cx, cy = s2w(1560, 350)
    sq = np.maximum(np.abs(x - cx) / 170, np.abs(y - cy) / 120)
    kind = np.where(sq + nz / 60 < 1, 2, kind)
    for (fu, fv, a_, b_) in ((150, 380, 80, 48), (330, 400, 60, 36), (40, 300, 40, 30)):
        fx, fy = s2w(fu, fv)
        kind = np.where((np.abs(x - fx) < a_) & (np.abs(y - fy) < b_), 4, kind)
    rx, _ = s2w(2780, 400)
    xr = rx + np.sin(y / 60) * 12
    d = np.abs(x - xr) - 26 + nz * 0.4
    kind = np.where(d < 0, 3, kind)
    out = np.zeros((H, W, 3), np.float32)
    mac_all = (vnoise2(x, y, 70, 91) - 0.5) * 1.8 + (vnoise2(x, y, 23, 92) - 0.5) * 0.9
    for k, name in enumerate(('grass', 'dirt', 'paved', 'water', 'crop')):
        m = kind == k
        if m.any():
            mac = mac_all[m]
            t1 = ground_tex(name, x[m], y[m], u[m], v[m], macro=mac)
            t2 = ground_tex(name, x[m] + 11, y[m] + 19, u[m], v[m], macro=mac)
            sel = vnoise2(x[m], y[m], 30, 93) > 0.5
            out[m] = np.where(sel[:, None], t1, t2)
    # large-scale hue drift on grass (dry ochre patches / lush blue-green hollows)
    hue = vnoise2(x, y, 55, 94) - 0.5
    g = kind == 0
    dry = np.array([1.07, 1.02, 0.86]); lush = np.array([0.92, 1.0, 1.05])
    tint = np.where((hue > 0)[..., None], 1 + (dry - 1) * np.clip(hue * 2.4, 0, 1)[..., None], 1 + (lush - 1) * np.clip(-hue * 2.4, 0, 1)[..., None])
    out[g] = out[g] * tint[g]
    # warm sun / cool sky on the ground: soft cloud-light modulation, quantised + dithered
    cl = vnoise2(x, y, 120, 95)
    q = np.floor((cl - 0.5) * 6 + BAYER[v % 4, u % 4] * 0.8) / 6
    out = out * (1 + q[..., None] * np.array([0.10, 0.08, 0.04]))
    fl = (kind == 0) & (hash3(np.floor(x).astype(np.int64), np.floor(y).astype(np.int64), np.zeros_like(u), 77) > 0.996)
    cols = np.array([hx('#f4e9c8'), hx('#f2c94c'), hx('#d86a8a'), hx('#9fb6ff')], np.float32)
    out[fl] = cols[(hash3(u[fl], v[fl], v[fl] * 0, 3) * 4).astype(int) % 4]
    gm = kind == 0
    border = (~gm) & (np.roll(gm, 1, 0) | np.roll(gm, 2, 0)) & (kind != 3)
    out[border] = out[border] * 0.82
    # grass blades overhanging path edges (lit tips)
    over_ = gm & ~np.roll(gm, -1, 0) & (hash3(u, v, u * 0, 5) > 0.5)
    out[np.roll(over_, 1, 0) & ~gm] = out[np.roll(over_, 1, 0) & ~gm] * 0.6 + np.array(hx('#7fb850')) * 0.4
    bank = (d >= 0) & (d < 2.2); out[bank] = DR[1]
    foam = (d < 0) & (d > -1.6); out[foam] = WR[6] * 0.9
    sh_ = (d < -1.6) & (d > -7); out[sh_] = out[sh_] * 0.72 + WR[5] * 0.28
    fe = (kind == 4) & ~(np.roll(kind, 1, 0) == 4); out[fe] = DR[1]
    return np.clip(out, 0, 255), kind

def compose(night=False, objects=None, effects=None):
    g, kind = ground()
    img = np.zeros((H, W, 4), np.float32); img[..., :3] = g; img[..., 3] = 255
    emis = np.zeros((H, W, 4), np.float32)
    nl = np.zeros((H, W, 3), np.float32)
    sh = np.zeros((H, W), np.float32)
    for (name, u, v, dp, extra) in objects:
        m = META[name]; s = load(name + '-shadow')
        x0, y0 = int(u - m['ax']), int(v - m['ay'])
        hh, ww = s.shape[:2]
        ys0, xs0 = max(0, y0), max(0, x0); ys1, xs1 = min(H, y0 + hh), min(W, x0 + ww)
        if ys1 > ys0 and xs1 > xs0:
            sh[ys0:ys1, xs0:xs1] = np.maximum(sh[ys0:ys1, xs0:xs1], s[ys0 - y0:ys1 - y0, xs0 - x0:xs1 - x0, 3] / 255)
    shc = np.array([26, 20, 56], np.float32)
    shd = sh * (0.45 if night else 1.0)
    img[..., :3] = img[..., :3] * (1 - shd[..., None]) + shc * shd[..., None]
    for (name, u, v, dp, extra) in sorted(objects, key=lambda o: o[2] + o[3]):
        m = META[name]
        x0, y0 = int(u - m['ax']), int(v - m['ay'])
        for (kind_, ename, eu, ev) in extra.get('under', []):
            e = load(ename); over(img, e, int(eu - e.shape[1] / 2), int(ev - e.shape[0] / 2)); over(emis, e, int(eu - e.shape[1] / 2), int(ev - e.shape[0] / 2), 0.6)
        c = load(name).copy()
        # small objects standing in a building's cast shadow get darkened (shadow received)
        if dp <= 10 and 0 <= int(v) - 2 < H and 0 <= int(u) < W:
            k_ = sh[max(0, int(v) - 2), int(u)]
            if k_ > 0.2:
                c[..., :3] = (c[..., :3] * (1 - 0.55 * k_) + shc * 0.55 * k_).astype(np.uint8)
        hh, ww = c.shape[:2]
        ys0, xs0 = max(0, y0), max(0, x0); ys1, xs1 = min(H, y0 + hh), min(W, x0 + ww)
        if ys1 > ys0 and xs1 > xs0:
            a = c[ys0 - y0:ys1 - y0, xs0 - x0:xs1 - x0, 3] > 0
            emis[ys0:ys1, xs0:xs1][a] = 0
            nl[ys0:ys1, xs0:xs1][a] = 0
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
        glow = g1 + g2
        v_, u_ = np.mgrid[0:H, 0:W]
        glow = np.floor(glow / 16 + BAYER[v_ % 4, u_ % 4][..., None] * 0.9) * 16
        glow = np.clip(glow, 0, 255)
        # local lights baked per building (falloff onto walls), quantised
        nlq = np.floor(nl / 24 + BAYER[v_ % 4, u_ % 4][..., None] * 0.8) * 24
        lit = nightc + (glow + nlq * 0.9) * (rgb / 255 * 0.85 + 0.15)
        lit[em] = emis[em, :3]
        rgb = lit
    return np.clip(rgb, 0, 255).astype(np.uint8)

def scene():
    O = []
    def b(name, u, v, dp=30, **extra): O.append(('b-' + name, u, v, dp, extra))
    rng = np.random.default_rng(4)
    keep_out = [(30, 330, 60, 260), (380, 720, 0, 400), (700, 980, 60, 230), (1050, 1500, 0, 320), (1420, 1760, 40, 260), (1800, 2250, 0, 330), (2220, 2700, 30, 290)]
    placed = []
    for k in range(600):
        u = int(rng.integers(-30, W + 30)); v = int(rng.integers(10, 175))
        if any(a <= u <= b_ and c <= v + 40 <= d for (a, b_, c, d) in keep_out): continue
        if any(abs(u - pu) < 40 and abs(v - pv) < 18 for pu, pv in placed): continue
        placed.append((u, v))
        b(['tree-pine', 'tree-pine', 'tree-oak', 'tree-pine', 'tree-autumn'][k % 5], u, v, 6)
    b('barn', 180, 230)
    b('magetower', 560, 348, 30)
    b('forge', 860, 215)
    b('townhall', 1280, 290, 60)
    b('tavern', 1610, 245)
    b('temple', 2030, 292, 45)
    b('barracks', 2470, 262)
    b('well', 1470, 390, 10); b('noticeboard', 1060, 380, 6); b('campfire', 1598, 352, 4)
    b('stall-red', 1730, 395, 10); b('stall-blue', 1860, 390, 10); b('stall-green', 960, 400, 10)
    for (t, u, v) in (('tree-oak', 2960, 395), ('tree-oak', 2900, 260), ('tree-autumn', 760, 398), ('bush', 2250, 380), ('bush', 2600, 395),
                      ('bush', 390, 270), ('rocks', 2400, 385), ('rocks', 700, 390), ('tree-oak', 1800, 300), ('bush', 2700, 250), ('tree-pine', 2990, 330),
                      ('rocks', 2650, 230), ('tree-autumn', 2860, 170)):
        b(t, u, v, 8)
    for k in range(5):
        b('fence-x', 60 + k * 44, 318 + k * 22, 2)
    E = []
    def hero(name, u, v, state):
        extra = {'under': [], 'above': []}
        m = META[name]; top = v - m['ay']
        if state == 'selected': extra['under'].append(('ring', 'ring-selected', u, v))
        if state == 'blocked':
            extra['under'].append(('ring', 'ring-blocked', u, v))
            extra['above'].append(('m-blocked', u, v - 92))
            E.append(C.fx_bubble(u + 52, v - 70, "A l'aide !"))
        if state == 'done':
            extra['under'].append(('ring', 'ring-done', u, v))
            extra['above'].append(('m-done', u, v - 92))
            E.append(C.fx_points(u, v, [hx('#ffe28a'), hx('#fff2c0'), hx('#e0a32a')], 11, (20, 80), seed=u, shape='star'))
        if state == 'idle': E.append(C.fx_z(u + 12, v - 66))
        O.append((name, u, v, 3, extra))
    hero('h-elf-mage-work', 690, 372, 'selected'); E.append(C.fx_magic(712, 345))
    hero('h-dwarf-artificer-work', 1010, 300, 'work'); E.append(C.fx_points(1030, 290, [hx('#ffd25a'), hx('#ffa12b'), hx('#fff2a8')], 12, (12, 30), seed=3))
    hero('h-orc-warrior-stand', 2350, 362, 'blocked')
    hero('h-human-warrior-work', 2600, 340, 'work')
    hero('h-human-priest-work', 2190, 372, 'done')
    hero('h-human-ranger-work', 420, 340, 'work')
    hero('h-undead-rogue-sit', 1555, 362, 'idle')
    hero('h-orc-rogue-sit', 1640, 372, 'idle')
    hero('h-elf-ranger-stand', 1890, 330, 'work')
    return O, E

def save2(arr, path):
    Image.fromarray(arr).resize((arr.shape[1] * 2, arr.shape[0] * 2), Image.NEAREST).save(path)

if __name__ == '__main__':
    O, E = scene()
    day = compose(False, O, E); night = compose(True, O, E)
    save2(day, 'mock-wide.png'); save2(night, 'mock-wide-night.png')
    save2(day[:, 500:2500], 'mock.png'); save2(night[:, 500:2500], 'mock-night.png')
    print('ok')
