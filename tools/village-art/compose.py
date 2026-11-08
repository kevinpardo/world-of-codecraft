"""Village strip mock-up (2000x400 logical -> 4000x800) day + night, and the contact sheet."""
import json, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage
from engine import over, vnoise2, hash3, BAYER, hx, ramp
from extras import ground_tex, DR, WR, FONT

A = 'assets/'
META = json.load(open(A + 'meta.json'))
W, H = 2000, 400
U0, V0 = 1000, 200

def load(name):
    im = np.array(Image.open(A + name + '.png').convert('RGBA'))
    return im[::2, ::2]

def s2w(u, v):
    return (v - V0) + (u - U0) / 2, (v - V0) - (u - U0) / 2

def seg_dist(x, y, a, b):
    ax, ay = a; bx, by = b
    dx, dy = bx - ax, by - ay
    t = np.clip(((x - ax) * dx + (y - ay) * dy) / (dx * dx + dy * dy), 0, 1)
    return np.hypot(x - ax - t * dx, y - ay - t * dy)

def ground():
    v, u = np.mgrid[0:H, 0:W]
    x, y = s2w(u + 0.5, v + 0.5)
    nz = (vnoise2(x, y, 6, 51) - 0.5) * 5 + (vnoise2(x, y, 2.5, 52) - 0.5) * 2
    kind = np.full((H, W), 0)  # 0 grass 1 dirt 2 paved 3 water 4 crop
    # paths (screen waypoints -> world)
    paths = [[(0, 300), (160, 270), (330, 300), (520, 300), (700, 290), (820, 300)],
             [(1180, 300), (1350, 285), (1500, 330), (1640, 330), (1760, 290), (1880, 245)],
             [(600, 250), (650, 140), (700, 40), (720, 0)], [(1000, 250), (1060, 140), (1120, 0)],
             [(480, 360), (560, 400)], [(1520, 320), (1430, 400)]]
    for p in paths:
        pw = [s2w(*q) for q in p]
        for a, b in zip(pw[:-1], pw[1:]):
            d = seg_dist(x, y, a, b)
            kind = np.where(d + nz < 15, 1, kind)
    # paved square around the town hall
    cx, cy = s2w(990, 290)
    sq = np.maximum(np.abs(x - cx) / 125, np.abs(y - cy) / 95)
    kind = np.where(sq + nz / 60 < 1, 2, kind)
    # crop fields
    for (fu, fv, a_, b_) in ((150, 345, 70, 44), (300, 372, 54, 34), (40, 280, 40, 30)):
        fx, fy = s2w(fu, fv)
        m = (np.abs(x - fx) < a_) & (np.abs(y - fy) < b_)
        kind = np.where(m, 4, kind)
    # river (constant x line, meandering)
    rx, _ = s2w(1700, 400)
    xr = rx + np.sin(y / 60) * 12
    d = np.abs(x - xr) - 22 + nz * 0.4
    kind = np.where(d < 0, 3, kind)
    out = np.zeros((H, W, 3), np.float32)
    for k, name in enumerate(('grass', 'dirt', 'paved', 'water', 'crop')):
        m = kind == k
        if m.any():
            mac = (vnoise2(x[m], y[m], 70, 91) - 0.5) * 1.8 + (vnoise2(x[m], y[m], 23, 92) - 0.5) * 0.9
            t1 = ground_tex(name, x[m], y[m], u[m], v[m], macro=mac)
            t2 = ground_tex(name, x[m] + 11, y[m] + 19, u[m], v[m], macro=mac)
            sel = vnoise2(x[m], y[m], 30, 93) > 0.5
            out[m] = np.where(sel[:, None], t1, t2)
    # grass flowers sprinkled
    fl = (kind == 0) & (hash3(np.floor(x).astype(np.int64), np.floor(y).astype(np.int64), np.zeros_like(u), 77) > 0.996)
    cols = np.array([hx('#f4e9c8'), hx('#f2c94c'), hx('#d86a8a'), hx('#9fb6ff')], np.float32)
    out[fl] = cols[(hash3(u[fl], v[fl], v[fl] * 0, 3) * 4).astype(int) % 4]
    # edges: grass overhang darkens path borders, shoreline bank + foam
    gm = kind == 0
    border = (~gm) & (np.roll(gm, 1, 0) | np.roll(gm, 2, 0)) & (kind != 3)
    out[border] = out[border] * 0.82
    bank = (d >= 0) & (d < 2.2)
    out[bank] = DR[1]
    foam = (d < 0) & (d > -1.6)
    out[foam] = WR[6] * 0.9
    shallow = (d < -1.6) & (d > -6)
    out[shallow] = out[shallow] * 0.75 + WR[5] * 0.25
    # field fences rendered as sprites later; soft field edge
    fe = (kind == 4) & ~(np.roll(kind, 1, 0) == 4)
    out[fe] = DR[1]
    return out, kind, (x, y)

def compose(night=False, objects=None, effects=None):
    g, kind, _ = ground()
    img = np.zeros((H, W, 4), np.float32); img[..., :3] = g; img[..., 3] = 255
    emis = np.zeros((H, W, 4), np.float32)
    # shadows (union, single darken)
    sh = np.zeros((H, W), np.float32)
    for (name, u, v, dp, extra) in objects:
        m = META[name]; s = load(name + '-shadow')
        x0, y0 = int(u - m['ax']), int(v - m['ay'])
        hh, ww = s.shape[:2]
        ys0, xs0 = max(0, y0), max(0, x0); ys1, xs1 = min(H, y0 + hh), min(W, x0 + ww)
        if ys1 > ys0 and xs1 > xs0:
            sh[ys0:ys1, xs0:xs1] = np.maximum(sh[ys0:ys1, xs0:xs1], s[ys0 - y0:ys1 - y0, xs0 - x0:xs1 - x0, 3] / 255)
    shc = np.array([24, 18, 52], np.float32)
    sh = sh * (0.45 if night else 1.0)
    img[..., :3] = img[..., :3] * (1 - sh[..., None]) + shc * sh[..., None]
    # sprites in depth order
    for (name, u, v, dp, extra) in sorted(objects, key=lambda o: o[2] + o[3]):
        m = META[name]
        x0, y0 = int(u - m['ax']), int(v - m['ay'])
        for (kind_, ename, eu, ev) in extra.get('under', []):
            e = load(ename); over(img, e, int(eu - e.shape[1] / 2), int(ev - e.shape[0] / 2)); over(emis, e, int(eu - e.shape[1] / 2), int(ev - e.shape[0] / 2), 0.6)
        c = load(name)
        # occlude emissive behind opaque pixels
        hh, ww = c.shape[:2]
        ys0, xs0 = max(0, y0), max(0, x0); ys1, xs1 = min(H, y0 + hh), min(W, x0 + ww)
        if ys1 > ys0 and xs1 > xs0:
            a = c[ys0 - y0:ys1 - y0, xs0 - x0:xs1 - x0, 3] > 0
            emis[ys0:ys1, xs0:xs1][a] = 0
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
        em = emis[..., 3] > 0
        # glow: two radii, posterised to pixel-art steps
        g1 = np.stack([ndimage.gaussian_filter(e[..., k], 3) for k in range(3)], -1) * 3.4
        g2 = np.stack([ndimage.gaussian_filter(e[..., k], 20) for k in range(3)], -1) * 10.0
        glow = g1 + g2
        v_, u_ = np.mgrid[0:H, 0:W]
        glow = np.floor(glow / 18 + BAYER[v_ % 4, u_ % 4][..., None] * 0.9) * 18
        glow = np.clip(glow, 0, 255)
        lit = nightc + glow * (rgb / 255 * 0.85 + 0.15)
        lit[em] = emis[em, :3]
        rgb = lit
    return np.clip(rgb, 0, 255).astype(np.uint8)

# ---------------------------------------------------------------- effects
def sparkle(img, x, y, col, size=2):
    pts = [(0, 0)] + [(k, 0) for k in range(-size, size + 1)] + [(0, k) for k in range(-size, size + 1)]
    for dx, dy in pts:
        xx, yy = x + dx, y + dy
        if 0 <= xx < W and 0 <= yy < H:
            img[yy, xx, :3] = col if (dx or dy) else (255, 255, 255); img[yy, xx, 3] = 255

def fx_magic(u, v, emis_too=True):
    rng = np.random.default_rng(int(u))
    def f(img, emis):
        cols = [hx('#cfa6ff'), hx('#a86bff'), hx('#efdcff')]
        for k in range(7):
            x = int(u + rng.integers(-16, 16)); y = int(v - rng.integers(10, 58))
            c = cols[k % 3]; s = 1 + (k % 2)
            sparkle(img, x, y, c, s)
            if emis_too: sparkle(emis, x, y, c, s)
    return f

def fx_points(u, v, cols, n=8, spread=(14, 40), seed=0, shape='dot'):
    rng = np.random.default_rng(seed)
    def f(img, emis):
        for k in range(n):
            x = int(u + rng.integers(-spread[0], spread[0])); y = int(v - rng.integers(4, spread[1]))
            c = cols[k % len(cols)]
            if shape == 'dot':
                img[y:y + 2 if k % 3 == 0 else y + 1, x:x + 1, :3] = c
                emis[y:y + 1, x:x + 1, :3] = c; emis[y:y + 1, x:x + 1, 3] = 255
            else:
                sparkle(img, x, y, c, 1 + k % 2)
                sparkle(emis, x, y, c, 1)
    return f

ZZ = ['XXXX', '..X.', '.X..', 'XXXX']
def fx_z(u, v):
    def f(img, emis):
        for k, (dx, dy, s) in enumerate(((0, 0, 1), (6, -8, 1), (13, -17, 2))):
            for r, row in enumerate(ZZ):
                for c_, ch in enumerate(row):
                    if ch == 'X':
                        for a in range(s):
                            for b in range(s):
                                yy, xx = int(v + dy + r * s + a), int(u + dx + c_ * s + b)
                                img[yy, xx, :3] = (236, 240, 255)
            # outline-ish shadow
    return f

def fx_bubble(u, v, text):
    def f(img, emis):
        pil = Image.fromarray(img.astype(np.uint8))
        d = ImageDraw.Draw(pil); d.fontmode = '1'
        fnt = ImageFont.truetype(FONT + 'Jersey15-Regular.ttf', 15)
        tw = d.textlength(text, font=fnt)
        x0, y0 = int(u - tw / 2 - 5), int(v - 18)
        pr = ramp('#efe2bf', light=1.08, hs=10)
        d.rectangle((x0, y0, x0 + tw + 10, y0 + 15), fill=tuple(int(c) for c in pr[5]), outline=(58, 36, 30))
        d.line((x0 + 1, y0 + 14, x0 + tw + 9, y0 + 14), fill=tuple(int(c) for c in pr[3]))
        d.polygon([(u - 3, y0 + 15), (u + 3, y0 + 15), (u, y0 + 20)], fill=tuple(int(c) for c in pr[5]), outline=(58, 36, 30))
        d.line((u - 2, y0 + 15, u + 2, y0 + 15), fill=tuple(int(c) for c in pr[5]))
        d.text((x0 + 5, y0 - 1), text, font=fnt, fill=(74, 40, 28))
        new = np.array(pil).astype(np.float32)
        ch = np.any(new[..., :3] != img[..., :3].astype(np.uint8), -1)
        img[...] = new
        emis[ch, :3] = new[ch, :3]; emis[ch, 3] = 255
    return f

def scene():
    O = []
    def b(name, u, v, dp=30, **extra): O.append(('b-' + name, u, v, dp, extra))
    # back forest (behind everything)
    rng = np.random.default_rng(4)
    keep_out = [(330, 560, 0, 300), (540, 760, 60, 290), (780, 1190, 20, 320), (1130, 1380, 40, 250), (1380, 1660, 40, 320), (1600, 1960, 40, 260), (60, 290, 60, 240)]
    placed = []
    for k in range(140):
        u = int(rng.integers(-20, 2020)); v = int(rng.integers(30, 150))
        if any(a <= u <= b_ and c <= v + 40 <= d for (a, b_, c, d) in keep_out): continue
        if any(abs(u - pu) < 34 and abs(v - pv) < 16 for pu, pv in placed): continue
        placed.append((u, v))
        t = ['tree-pine', 'tree-pine', 'tree-oak', 'tree-pine', 'tree-autumn'][k % 5]
        b(t, u, v, 6)
    b('barn', 175, 215)
    b('magetower', 430, 286, 26)
    b('forge', 640, 222)
    b('townhall', 965, 240, 48)
    b('tavern', 1255, 200)
    b('temple', 1510, 255, 40)
    b('barracks', 1790, 205)
    # props
    b('well', 1100, 330, 10); b('noticeboard', 850, 330, 6); b('campfire', 975, 352, 4)
    b('stall-red', 1175, 360, 10); b('stall-blue', 1290, 330, 10); b('stall-green', 760, 375, 10)
    for (t, u, v) in (('tree-oak', 1985, 395), ('tree-oak', 40, 395), ('tree-autumn', 600, 395), ('bush', 1400, 375), ('bush', 1625, 395),
                      ('bush', 330, 250), ('rocks', 1700, 380), ('rocks', 520, 380), ('tree-oak', 1385, 255), ('bush', 1640, 230), ('tree-pine', 1990, 330),
                      ('bush', 700, 350), ('rocks', 1900, 215), ('tree-autumn', 2005, 160)):
        b(t, u, v, 8)
    for k in range(6):
        b('fence-x', 80 + k * 32, 300 + k * 16, 2)
    for k in range(3):
        b('fence-y', 236 - k * 32, 395 - k * 16 + 0, 2)
    # heroes: (sprite, u, v, state)
    E = []
    def hero(name, u, v, state, label=None):
        extra = {'under': [], 'above': []}
        m = META[name]
        top = v - m['ay']
        if state == 'selected': extra['under'].append(('ring', 'ring-selected', u, v))
        if state == 'blocked':
            extra['under'].append(('ring', 'ring-blocked', u, v))
            extra['above'].append(('m-blocked', u, v - 50))
            E.append(fx_bubble(u + 40, top + 6, "A l'aide !"))
        if state == 'done':
            extra['under'].append(('ring', 'ring-done', u, v))
            extra['above'].append(('m-done', u - 10, v - 50))
            E.append(fx_points(u, v, [hx('#ffe28a'), hx('#fff2c0'), hx('#e0a32a')], 9, (16, 44), seed=u, shape='star'))
        if state == 'idle': E.append(fx_z(u + 8, top - 18))
        O.append((name, u, v, 3, extra))
    hero('h-elf-mage-work', 476, 330, 'selected'); E.append(fx_magic(470, 330))
    hero('h-dwarf-artificer-work', 712, 300, 'work'); E.append(fx_points(735, 300, [hx('#ffd25a'), hx('#ffa12b'), hx('#fff2a8')], 10, (10, 26), seed=3))
    hero('h-orc-warrior-stand', 1730, 300, 'blocked')
    hero('h-human-warrior-stand', 1868, 262, 'work')
    hero('h-human-priest-work', 1452, 340, 'done')
    hero('h-human-ranger-work', 300, 296, 'work')
    hero('h-undead-rogue-sit', 952, 368, 'idle')
    hero('h-orc-rogue-sit', 1001, 372, 'idle')
    hero('h-elf-ranger-stand', 1210, 268, 'work')
    return O, E

def save2(arr, path):
    Image.fromarray(arr).resize((arr.shape[1] * 2, arr.shape[0] * 2), Image.NEAREST).save(path)

if __name__ == '__main__':
    O, E = scene()
    save2(compose(False, O, E), 'mock.png')
    save2(compose(True, O, E), 'mock-night.png')
    print('mock ok')
