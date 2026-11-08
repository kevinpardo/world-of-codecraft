"""World of Codecraft: the interface art (frames, bars, plaques, buttons, gems, banners,
icons, hero portraits), drawn by code with the same rules as the village sprites (direction A):

- 1 art px = 1 logical px, saved at 2x (nearest);
- every material is a 7-step hue-shifted ramp (darks drift to blue-violet, lights to yellow);
- light from the top-left; each piece is a height field, shaded from its normals, with ambient
  occlusion, cast shadows, worn convex edges (cavity), a lit lip on top-left steps, dark creases;
- Bayer 4x4 dithering only at ramp boundaries; 1 px coloured outline outside the silhouette.

Stretchable pieces are corners + edge strips that are uniform along their length: the mod crops
them (never stretches them), so a frame fits any size with no seam and no blur.

Run: <venv with numpy, scipy, pillow>/bin/python tools/ui.py  (from the mod folder)
Hero portraits need HEROES (the validated sprites folder); set it with the env var HEROES.
"""
import colorsys, json, os, sys
import numpy as np
from scipy import ndimage
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'art', 'ui')
HEROES = os.environ.get('HEROES', '')
os.makedirs(OUT, exist_ok=True)

BAYER = (np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) / 16.0) - 0.47
L = np.array([-0.45, -0.55, 0.70]); L = L / np.linalg.norm(L)  # image space: x right, y down, z up


def hx(h):
    h = h.lstrip('#'); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def ramp(base, n=7, cool=232, warm=48, dark=0.30, light=1.32, hs=22):
    """Hue-shifted 7-step ramp, the village's rule."""
    r, g, b = [c / 255 for c in hx(base)]
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    out = []; mid = (n - 1) / 2
    for k in range(n):
        t = (k - mid) / mid
        hh = h * 360; target = cool if t < 0 else warm
        d = ((target - hh + 180) % 360) - 180
        hh = (hh + d * min(1, abs(t)) * hs / 90) % 360
        vv = v * (1 + (light - 1) * t) if t > 0 else v * (1 + (1 - dark) * t)
        ss = s * (1 + 0.18 * -t) if t > 0 else min(1, s * (1 + 0.25 * -t))
        if t > 0.6: ss *= 0.85
        rr, gg, bb = colorsys.hsv_to_rgb(hh / 360, max(0, min(1, ss)), max(0, min(1, vv)))
        out.append((rr * 255, gg * 255, bb * 255))
    return np.array(out, dtype=np.float32)


def outline_of(rp):
    """The darkest step, darkened and pushed toward purple (the village's outline rule)."""
    h, s, v = colorsys.rgb_to_hsv(*(rp[0] / 255))
    hh = h * 360; d = ((262 - hh + 180) % 360) - 180; hh += d * 0.35
    r, g, b = colorsys.hsv_to_rgb((hh % 360) / 360, min(1, s * 1.1 + 0.1), v * 0.55)
    return np.array([r * 255, g * 255, b * 255], dtype=np.float32)


def h2(a, b, seed=0):
    a = np.asarray(a).astype(np.int64); b = np.asarray(b).astype(np.int64)
    h = (a * 73856093) ^ (b * 19349663) ^ (seed * 83492791)
    h = (h ^ (h >> 13)) * 1274126177; h = h ^ (h >> 16)
    return (h & 0xFFFF).astype(np.float32) / 65535.0


# ------------------------------------------------------------------ materials
class Mat:
    def __init__(self, base, tex='none', spec=0.0, bias=0.0, amp=1.0, flat=False, emit=False, **kw):
        self.rp = kw.pop('rp', None)
        if self.rp is None: self.rp = ramp(base, **kw)
        self.ol = outline_of(self.rp)
        self.tex, self.spec, self.bias, self.amp, self.flat, self.emit = tex, spec, bias, amp, flat, emit


M = {}
def mat(name, *a, **k):
    M[name] = Mat(*a, **k); return name

mat('wood', '#6b3f26', tex='grain', hs=24, bias=-0.6, amp=0.7)
mat('wooddk', '#4f2e1e', tex='grain', hs=24, bias=-0.4, amp=0.6)
mat('iron', '#58546a', tex='iron', spec=2.2, hs=16, bias=-0.3)
mat('irondk', '#3f3c4c', tex='iron', spec=1.0, hs=14)
mat('gold', '#e0a32a', tex='gold', spec=2.2, hs=30, light=1.30)
mat('leather', '#4a2c22', tex='leather', hs=20, bias=-0.2, amp=0.25)
mat('parch', '#e8d6b0', tex='parch', hs=16)
mat('lacquer', '#8e2a2a', tex='iron', spec=1.4, hs=26)
mat('steel', '#4c4a62', tex='iron', spec=2.0, hs=16)
mat('enamel', '#2b2230', flat=True)
mat('vellum', '#e9dcbc', flat=True)
mat('bone', '#efe2c0', spec=1.2, hs=18)
mat('void', '#241c2c', tex='none', hs=10)
GEM = {'working': '#3fcf5a', 'blocked': '#e8343a', 'done': '#f2b62a', 'idle': '#a9a1c4', 'sapphire': '#3f72e0', 'amethyst': '#9a55e8'}
for k, v in GEM.items(): mat('gem-' + k, v, spec=3.0, hs=26, light=1.38, dark=0.22)
CLOTH = ["#7a1f2b", "#2f4a7a", "#2f6b4a", "#6b3a8a", "#8a5a1f", "#1f6b6b", "#8a2f5a", "#4a5a2f"]  # kit.js COLORS
for i, c in enumerate(CLOTH): mat(f'cloth{i}', c, tex='cloth', hs=26, light=1.4, bias=0.25)


# ------------------------------------------------------------------ canvas
class Cv:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.H = np.zeros((h, w), np.float32)
        self.M = np.full((h, w), '', dtype=object)
        self.A = np.zeros((h, w), bool)
        self.T = np.zeros((h, w), np.float32)   # extra texture/level offset
        self.G = np.zeros((h, w), np.float32)   # grain direction: 0 along x, 1 along y
        self.yy, self.xx = np.mgrid[0:h, 0:w]

    def put(self, mask, height, m, add=False, tex=0.0):
        mask = mask.astype(bool)
        hh = np.broadcast_to(np.asarray(height, np.float32), mask.shape)
        self.H[mask] = (self.H[mask] + hh[mask]) if add else hh[mask]
        self.M[mask] = m; self.A |= mask
        if np.ndim(tex): self.T[mask] = np.asarray(tex)[mask]
        else: self.T[mask] = tex


def sup(draw_fn, w, h, ss=6):
    """A mask drawn with PIL at ss x supersampling, then thresholded (crisp pixel edges)."""
    im = Image.new('L', (w * ss, h * ss), 0)
    draw_fn(ImageDraw.Draw(im), ss)
    a = np.array(im.resize((w, h), Image.BOX)) / 255.0
    return a > 0.5


def disc(cv, cx, cy, r):
    return (cv.xx + 0.5 - cx) ** 2 + (cv.yy + 0.5 - cy) ** 2 <= r * r


def dome(cv, cx, cy, r, top=1.0):
    d2 = ((cv.xx + 0.5 - cx) ** 2 + (cv.yy + 0.5 - cy) ** 2) / (r * r)
    return np.sqrt(np.clip(1 - d2, 0, 1)) * r * top


def edge_dist(w, h, x0=0, y0=0, x1=None, y1=None):
    x1 = w if x1 is None else x1; y1 = h if y1 is None else y1
    yy, xx = np.mgrid[0:h, 0:w]
    dx = np.minimum(xx - x0, x1 - 1 - xx); dy = np.minimum(yy - y0, y1 - 1 - yy)
    return np.minimum(dx, dy).astype(np.float32), (dy > dx)  # distance, True where a vertical side is nearest


def shift(A, dy, dx, fill):
    out = np.full_like(A, fill)
    h, w = A.shape
    ys, yd = (slice(0, h - dy), slice(dy, h)) if dy >= 0 else (slice(-dy, h), slice(0, h + dy))
    xs, xd = (slice(0, w - dx), slice(dx, w)) if dx >= 0 else (slice(-dx, w), slice(0, w + dx))
    out[yd, xd] = A[ys, xs]
    return out


# ------------------------------------------------------------------ the renderer
def render(cv, k=2.1, ao=0.45, cast=0.9, dither=0.42, outline=True, rim=True, crease=1.25, bg=None):
    H = cv.H.copy(); A = cv.A
    Hf = np.where(A, H, 0)
    gy, gx = np.gradient(ndimage.gaussian_filter(Hf, 0.45))
    nx, ny, nz = -gx * k, -gy * k, np.ones_like(H)
    nn = np.sqrt(nx * nx + ny * ny + nz * nz); nx, ny, nz = nx / nn, ny / nn, nz / nn
    dif = np.clip(nx * L[0] + ny * L[1] + nz * L[2], 0, 1)
    lv = 3.2 + (dif - L[2]) * 5.0
    # ambient occlusion (local height deficit) and worn convex edges
    lv -= np.clip(ndimage.gaussian_filter(Hf, 2.5) - Hf, 0, 4) * ao
    lv += np.clip(Hf - ndimage.gaussian_filter(Hf, 1.0), 0, 2) * 0.5
    # cast shadow: something higher toward the light (top-left)
    if cast:
        sh = np.zeros_like(A)
        for s in range(1, 7):
            sh |= shift(Hf, s, s, -1e9) > Hf + s * 0.85
        lv -= sh * 1.35 * cast
    yy, xx = cv.yy, cv.xx
    col = np.zeros((cv.h, cv.w, 4), np.float32)
    names = set(cv.M[A].tolist())
    for name in names:
        m = M[name]; sel = A & (cv.M == name)
        l = lv.copy()
        if m.tex == 'grain':
            along = np.where(cv.G > 0.5, yy, xx); across = np.where(cv.G > 0.5, xx, yy)
            seg = np.floor(along / 41.0 + h2(across, 3, 5) * 3)
            streak = (h2(across, seg, 11) - 0.5) * 1.1
            dark = (h2(across * 3 + 1, np.floor(along / 9.0), 12) > 0.86) * -0.7
            l += (streak + dark) * m.amp + (h2(xx, yy, 13) - 0.5) * 0.35
        elif m.tex == 'iron':
            l += (h2(xx, yy, 21) > 0.93) * -0.6 + (h2(xx // 2, yy // 2, 22) - 0.5) * 0.3
        elif m.tex == 'gold':
            l += (h2(xx, yy, 31) > 0.97) * 0.6
        elif m.tex == 'leather':
            l += ((h2(xx // 2, yy // 2, 41) - 0.5) * 0.7 + (h2(xx, yy, 42) > 0.9) * -0.5) * m.amp
        elif m.tex == 'parch':
            l += (h2(xx // 3, yy // 3, 51) - 0.5) * 0.5 * m.amp
        elif m.tex == 'cloth':
            l += ((xx + yy) % 3 == 0) * -0.25 + (h2(xx, yy, 61) > 0.92) * -0.4
        if m.spec:
            Hh = np.array([-0.35, -0.45, 1.0]); Hh /= np.linalg.norm(Hh)
            sp = np.clip(nx * Hh[0] + ny * Hh[1] + nz * Hh[2], 0, 1) ** 12 * m.spec
            l += sp
        l += m.bias + cv.T
        if not m.flat: l += BAYER[yy % 4, xx % 4] * dither
        idx = np.clip(np.round(l), 0, 6).astype(int)
        if m.flat: idx = np.full_like(idx, 3)
        col[sel, :3] = m.rp[idx[sel]]
        col[sel, 3] = 255
    # creases (a step up right next to it, toward the light) and lit lips (a step down after it)
    if crease:
        up = np.maximum(shift(Hf, 1, 0, -1e9), shift(Hf, 0, 1, -1e9))
        dn = np.maximum(shift(Hf, -1, 0, -1e9), shift(Hf, 0, -1, -1e9))
        cre = A & (up - Hf > crease)
        lip = A & (Hf - np.maximum(shift(Hf, 1, 0, 1e9), shift(Hf, 0, 1, 1e9)) > crease)
        cre2 = A & (dn - Hf > crease * 1.6)
        for name in names:
            m = M[name]
            if m.flat: continue
            s1 = cre & (cv.M == name); col[s1, :3] = m.rp[0]
            s3 = cre2 & (cv.M == name) & ~s1; col[s3, :3] = m.rp[1]
            if rim:
                s2 = lip & (cv.M == name) & ~s1; col[s2, :3] = m.rp[6] * 0.6 + col[s2, :3] * 0.4
    # coloured outline outside the silhouette
    if outline:
        nb = [shift(A, 1, 0, False), shift(A, -1, 0, False), shift(A, 0, 1, False), shift(A, 0, -1, False)]
        edge = ~A & (nb[0] | nb[1] | nb[2] | nb[3])
        src = [shift(cv.M, 1, 0, ''), shift(cv.M, -1, 0, ''), shift(cv.M, 0, 1, ''), shift(cv.M, 0, -1, '')]
        for y, x in zip(*np.nonzero(edge)):
            for s in src:
                if s[y, x]:
                    col[y, x, :3] = M[s[y, x]].ol; col[y, x, 3] = 255; break
    if bg is not None:
        col[col[..., 3] == 0] = bg
    return col


def save(arr, name):
    a = np.clip(arr, 0, 255).astype(np.uint8)
    Image.fromarray(a).resize((a.shape[1] * 2, a.shape[0] * 2), Image.NEAREST).save(os.path.join(OUT, name + '.png'), optimize=True)


META = {}


# ------------------------------------------------------------------ frame profiles
def profile_cadre(d, al=None):
    """Panel frame, 14 px: riveted iron rim, carved oak moulding with a twisted rope, gold bead, shadowed lip."""
    al = np.zeros_like(d) if al is None else al
    hh = np.zeros_like(d); mm = np.full(d.shape, '', object)
    a = d < 3; hh[a] = 3.0 + np.sin(np.pi * np.clip(d[a] / 3, 0, 1)) * 1.6; mm[a] = 'iron'
    riv = a & (((al + 0.5) % 24 - 12) ** 2 + (d - 1.0) ** 2 < 2.6)
    hh[riv] += 1.4; mm[riv] = 'gold'
    b = (d >= 3) & (d < 10)
    t = (d - 3) / 7.0
    rope = (np.abs(t - 0.5) < 0.3) & b
    tw = ((al + d * 1.0) % 5) / 5.0
    hh[b] = (2.0 + np.sin(np.pi * t) * 2.2)[b]
    hh[rope] = (3.4 + np.sin(np.pi * tw) * 1.6)[rope]
    mm[b] = 'wood'
    c = (d >= 10) & (d < 12); hh[c] = 3.4 + np.sin(np.pi * (d[c] - 10) / 2) * 0.9; mm[c] = 'gold'
    e = (d >= 12) & (d < 14); hh[e] = 1.4 - (d[e] - 12) * 0.5; mm[e] = 'wooddk'
    return hh, mm


def profile_fin(rimmat, beadmat='gold'):
    def f(d, al=None):
        hh = np.zeros_like(d); mm = np.full(d.shape, '', object)
        a = d < 2; hh[a] = 2.4 + np.sin(np.pi * np.clip(d[a] / 2, 0, 1)) * 0.9; mm[a] = rimmat
        b = (d >= 2) & (d < 3); hh[b] = 2.6; mm[b] = beadmat
        c = (d >= 3) & (d < 5); hh[c] = 1.2 - (d[c] - 3) * 0.4; mm[c] = 'irondk'
        return hh, mm
    return f


# ------------------------------------------------------------------ ornaments
def corner_ornament(C, gem='sapphire', big=True):
    """Gold filigree corner cap for the top-left corner (flipped for the others, then lit)."""
    cv = Cv(C, C)
    s = C / 34.0
    K = lambda *v: [c * s for c in v]
    plate = sup(lambda d, k: d.polygon([(0, 0), (22 * s * k, 0), (22 * s * k, 5 * s * k), (5 * s * k, 22 * s * k), (0, 22 * s * k)], fill=255), C, C)
    leaves = sup(lambda d, k: (
        d.arc([20 * s * k, 0 * s * k, 33 * s * k, 11 * s * k], 140, 360, fill=255, width=int(2.4 * s * k)),
        d.arc([0 * s * k, 20 * s * k, 11 * s * k, 33 * s * k], 90, 310, fill=255, width=int(2.4 * s * k)),
        d.ellipse([28 * s * k, 4 * s * k, 33 * s * k, 9 * s * k], fill=255),
        d.ellipse([4 * s * k, 28 * s * k, 9 * s * k, 33 * s * k], fill=255),
        d.polygon([(14 * s * k, 14 * s * k), (24 * s * k, 17 * s * k), (17 * s * k, 24 * s * k)], fill=255)), C, C)
    dist = ndimage.distance_transform_edt(plate)
    cv.put(plate, 4.0 + np.clip(dist, 0, 3) * 0.55, 'gold')
    lv = leaves & ~plate
    cv.put(lv, 4.2 + np.clip(ndimage.distance_transform_edt(lv), 0, 1.5) * 1.4, 'gold')
    # engraved line following the plate edge
    eng = plate & (np.abs(dist - 3.6) < 0.55)
    cv.H[eng] -= 1.6
    ring = disc(cv, 9 * s, 9 * s, 7.0 * s)
    cv.put(ring, 6.2 + np.sin(np.clip((np.sqrt((cv.xx + .5 - 9 * s) ** 2 + (cv.yy + .5 - 9 * s) ** 2) - 4.6 * s) / (2.4 * s), 0, 1) * np.pi) * 1.4, 'gold')
    g = disc(cv, 9 * s, 9 * s, 4.8 * s)
    cv.put(g, 7.0 + dome(cv, 9 * s, 9 * s, 4.8 * s, 1.1), 'gem-' + gem)
    for (rx, ry) in ((19 * s, 2.6 * s), (2.6 * s, 19 * s)):
        r = disc(cv, rx, ry, 1.9 * s); cv.put(r, 5.6 + dome(cv, rx, ry, 1.9 * s, 1.2), 'iron')
    return cv


def stud(cv, cx, cy, r, m='gold', base=0.0):
    msk = disc(cv, cx, cy, r); cv.put(msk, base + 2.0 + dome(cv, cx, cy, r), m)


# ------------------------------------------------------------------ nine-piece frames
def frame9(name, profile, C, t, orn=None, L=2400, fill=None):
    """Corners (C x C) and edge strips (L long, t thick) of one frame, all lit the same way."""
    def canvas(w, h):
        cv = Cv(w, h)
        d, vert = edge_dist(w, h)
        hh, mm = profile(d, np.where(vert, cv.yy, cv.xx).astype(np.float32))
        ins = mm != ''
        cv.H[ins] = hh[ins]; cv.M[ins] = mm[ins]; cv.A |= ins
        cv.G = vert.astype(np.float32)
        if fill: cv.put(~ins, 0.0, fill)
        return cv
    # corners: a small canvas with the ornaments in its four corners
    S = 3 * C
    cv = canvas(S, S)
    if orn:
        o = orn(C)
        for fy in (0, 1):
            for fx in (0, 1):
                Hh, Mm, Aa = o.H, o.M, o.A
                if fx: Hh, Mm, Aa = Hh[:, ::-1], Mm[:, ::-1], Aa[:, ::-1]
                if fy: Hh, Mm, Aa = Hh[::-1], Mm[::-1], Aa[::-1]
                ys = slice(S - C, S) if fy else slice(0, C); xs = slice(S - C, S) if fx else slice(0, C)
                sub = Aa
                cv.H[ys, xs][sub] = Hh[sub]; cv.M[ys, xs][sub] = Mm[sub]; cv.A[ys, xs][sub] = True
    col = render(cv, outline=False)
    save(col[:C, :C], f'{name}-tl'); save(col[:C, S - C:], f'{name}-tr')
    save(col[S - C:, :C], f'{name}-bl'); save(col[S - C:, S - C:], f'{name}-br')
    # long strips: wide and tall canvases, cropped away from their ends
    W = L + 2 * C
    hcv = canvas(W, max(2 * t + 4, 40)); hc = render(hcv, outline=False)
    save(hc[:t, C:C + L], f'{name}-t'); save(hc[-t:, C:C + L], f'{name}-b')
    vcv = canvas(max(2 * t + 4, 40), W); vc = render(vcv, outline=False)
    save(vc[C:C + L, :t], f'{name}-l'); save(vc[C:C + L, -t:], f'{name}-r')
    META[name] = {'C': C, 't': t, 'L': L}


def bar3(name, H, C, body, caps=None, L=2400, variants=None):
    """A horizontal bar of any width: left cap, a long middle strip (cropped), right cap."""
    def canvas(w):
        cv = Cv(w, H); body(cv);
        if caps: caps(cv)
        return cv
    cv = canvas(3 * C + 40); col = render(cv, outline=False)
    save(col[:, :C], f'{name}-l'); save(col[:, -C:], f'{name}-r')
    wcv = Cv(L + 2 * C, H); body(wcv); wc = render(wcv, outline=False)
    save(wc[:, C:C + L], f'{name}-m')
    META[name] = {'C': C, 'H': H, 'L': L}


# ------------------------------------------------------------------ the pieces
def pieces():
    # big panel frame (left column, terminal area, command panel)
    frame9('cadre', profile_cadre, 34, 14, orn=lambda C: corner_ornament(C, 'sapphire'))

    # thin rails around the terminal area: same moulding, a compact corner boss (fits in 14 px)
    def boss(C):
        cv = Cv(C, C)
        sq = (cv.xx < C - 1) & (cv.yy < C - 1)
        dd = np.minimum(np.minimum(cv.xx, cv.yy), np.minimum(C - 2 - cv.xx, C - 2 - cv.yy)).astype(np.float32)
        cv.put(sq, 3.6 + np.clip(dd, 0, 2) * 0.7, 'gold')
        c = (C - 1) / 2
        g = disc(cv, c, c, 3.6); cv.put(g, 6.4 + dome(cv, c, c, 3.6), 'gem-sapphire')
        return cv
    frame9('baguette', profile_cadre, 14, 14, orn=boss)

    # small frames: cards, chips, minimap, portraits
    def small_orn(gemname):
        def f(C):
            cv = Cv(C, C)
            p = sup(lambda d, k: d.polygon([(0, 0), (8 * k, 0), (8 * k, 3 * k), (3 * k, 8 * k), (0, 8 * k)], fill=255), C, C)
            cv.put(p, 3.4 + np.clip(ndimage.distance_transform_edt(p), 0, 2) * 0.6, 'gold')
            g = disc(cv, 3.2, 3.2, 2.2); cv.put(g, 5.0 + dome(cv, 3.2, 3.2, 2.2), 'gem-' + gemname)
            return cv
        return f
    frame9('fin', profile_fin('iron'), 10, 5, orn=small_orn('sapphire'))
    frame9('fin-or', profile_fin('gold', 'gold'), 10, 5, orn=small_orn('done'))
    frame9('fin-rubis', profile_fin('lacquer'), 10, 5, orn=small_orn('blocked'))

    # top bar beam, 48 px
    def beam(cv):
        y = cv.yy; x = cv.xx; w = cv.w
        hh = np.zeros((cv.h, w), np.float32); mm = np.full((cv.h, w), '', object)
        a = y < 3; hh[a] = 4.2; mm[a] = 'iron'
        b = (y >= 3) & (y < 37); t = (y - 3) / 34.0
        hh[b] = (3.4 + np.sin(np.pi * t) * 1.0)[b]; mm[b] = 'wood'
        P = 192; px = x % P
        strap = b & (px < 14)
        panel = b & (px >= 20) & (px < P - 6) & (y >= 9) & (y < 31)
        hh[panel] -= 1.8
        q = (px - 20) % 28 - 14
        dd = np.abs(q) + np.abs(y - 19.5) * 1.25
        loz = panel & (dd < 9.5) & (px >= 26) & (px < P - 12)
        hh[loz] = (hh + 1.0 + np.clip(9.5 - dd, 0, 3) * 0.45)[loz]
        inner = loz & (np.abs(dd - 4.5) < 0.6); hh[inner] -= 1.2
        hh[strap] = 4.8; mm[strap] = 'iron'
        c = (y >= 37) & (y < 40); hh[c] = 3.8 + np.sin(np.pi * (y[c] - 37) / 3) * 0.9; mm[c] = 'gold'
        e = (y >= 40) & (y < 45); hh[e] = 3.0; mm[e] = 'irondk'
        f = y >= 45; hh[f] = 1.0 - (y[f] - 45) * 0.3; mm[f] = 'wooddk'
        cv.H[:] = hh; cv.M[:] = mm; cv.A[:] = True; cv.G[:] = 0
        cv.T[f] = -(y[f] - 44) * 0.7
        for x0 in range(0, w, P):
            for yy0 in (8.5, 31.5): stud(cv, x0 + 7, yy0, 2.0, 'gold', 4.8)
        for x0 in range(36, w, 48):
            stud(cv, x0 + 0.5, 42.5, 1.6, 'iron', 3.0)
    bar3('poutre', 48, 24, beam, L=3600)

    # pane header, 30 px: calm and focused
    def header(focus):
        def body(cv):
            y = cv.yy; x = cv.xx
            cv.A[:] = True; cv.G[:] = 0
            cv.H[:] = 2.0; cv.M[:] = 'leather'
            top = y < 2; cv.H[top] = 3.2; cv.M[top] = 'gold' if focus else 'iron'
            mid = (y >= 2) & (y < 26); cv.H[mid] = (2.0 + np.sin(np.pi * (y - 2) / 24) * 0.5)[mid]
            st = ((y == 4) | (y == 23)) & ((x % 6) < 3); cv.put(st, cv.H + 0.7, 'parch' if focus else 'bone'); cv.T[st] = -1.2
            bead = (y >= 26) & (y < 28); cv.H[bead] = 3.0; cv.M[bead] = 'gold' if focus else 'iron'
            lo = y >= 28; cv.H[lo] = 1.4; cv.M[lo] = 'irondk'
        return body
    def hcaps(focus):
        def caps(cv):
            for cx in (7.5, cv.w - 7.5):
                br = (np.abs(cv.xx + 0.5 - cx) < 6) & (cv.yy >= 1) & (cv.yy < 28)
                cv.put(br, 3.4, 'iron'); cv.G[br] = 1
                g = disc(cv, cx, 14.5, 3.4); cv.put(g, 5 + dome(cv, cx, 14.5, 3.4), 'gem-' + ('done' if focus else 'sapphire'))
                stud(cv, cx, 4.5, 1.4, 'gold', 3.4); stud(cv, cx, 24.5, 1.4, 'gold', 3.4)
        return caps
    for focus in (0, 1):
        nm = 'entete' + ('-focus' if focus else '')
        bar3(nm, 30, 16, header(focus), hcaps(focus))

    # section heading plate (Quartiers, Carte, Unité choisie), 30 px
    def plate(cv):
        y = cv.yy; cv.A[:] = True; cv.G[:] = 0
        cv.M[:] = 'wooddk'; cv.H[:] = 2.0
        rim = (y < 2) | (y >= 28); cv.M[rim] = 'gold'; cv.H[rim] = 2.8
        cv.H[y == 2] = 1.6; cv.H[y == 27] = 1.6
        mid = (y >= 3) & (y < 27); cv.M[mid] = 'void'; cv.H[mid] = 1.2
    def pcaps(cv):
        for side in (0, 1):
            cx = 9 if side == 0 else cv.w - 9
            fl = sup(lambda d, k: d.polygon([((cx - 8) * k, 15 * k), (cx * k, 3 * k), ((cx + 8) * k, 15 * k), (cx * k, 27 * k)], fill=255), cv.w, 30)
            cv.put(fl, 3.2 + np.clip(ndimage.distance_transform_edt(fl), 0, 3) * 0.6, 'gold')
            g = disc(cv, cx, 15, 3.2); cv.put(g, 6 + dome(cv, cx, 15, 3.2), 'gem-amethyst')
    bar3('bandeau', 30, 20, plate, pcaps)

    # buttons with text, 28 px: normal / hover / pressed; iron and gold (alert) faces
    def button(face, state):
        def body(cv):
            w = cv.w; cv.A[:] = False
            d, _ = edge_dist(w, 28, 1, 1, w - 1, 27)
            ins = d >= 0
            rim = ins & (d < 2); bev = ins & (d >= 2) & (d < 4); fl = ins & (d >= 4)
            inv = state == 'p'
            dome_y = np.sin(np.pi * np.clip((cv.yy - 4) / 19.0, 0, 1)) * (1.0 if not inv else -0.8)
            cv.put(rim, 3.6 + np.sin(np.pi * np.clip(d / 2, 0, 1)) * 0.6, 'gold')
            cv.put(bev, (3.4 - (d - 2) * 0.7) if not inv else (1.0 + (d - 2) * 0.5), face)
            cv.put(fl, 2.0 + dome_y, face)
            cv.T[fl] = -0.6
            if state == 'h': cv.T[ins] += 0.9
            if state == 'p': cv.T[ins] -= 0.6
            for xx0 in (3.5, w - 3.5):
                for yy0 in (3.5, 24.5): stud(cv, xx0, yy0, 1.5, 'gold', 3.6)
        return body
    for face in ('steel', 'lacquer'):
        for st in ('n', 'h', 'p'):
            nm = f"btn{'-or' if face == 'lacquer' else ''}-{st}"
            bar3(nm, 28, 8, button(face, st), L=800)

    # square icon buttons (pane controls), 24 x 22
    for st in ('n', 'h', 'p'):
        cv = Cv(24, 22)
        d, _ = edge_dist(24, 22, 1, 1, 23, 21)
        ins = d >= 0; inv = st == 'p'
        cv.put(ins & (d < 1.5), 2.8, 'gold' if st == 'h' else 'iron')
        cv.put(ins & (d >= 1.5) & (d < 3.5), (2.6 - (d - 1.5) * 0.6) if not inv else (1.2 + (d - 1.5) * 0.5), 'iron')
        cv.put(ins & (d >= 3.5), 1.4, 'iron')
        if st == 'h': cv.T[ins] += 0.8
        if st == 'p': cv.T[ins] -= 0.6
        save(render(cv), f'bouton-{st}')

    # parchment scroll for the current district and quest, 34 px
    def scroll(cv):
        y = cv.yy; cv.A[:] = False
        body = (y >= 3) & (y < 31)
        cv.put(body, 2.0, 'parch'); cv.G[:] = 0
        t = (y - 3) / 28.0
        cv.H[body] = 2.0 + np.sin(np.pi * t[body]) * 0.6
        flat = (y >= 7) & (y < 27); cv.M[flat] = 'vellum'
        edge = body & ~flat; cv.T[edge] = 0
    def scaps(cv):
        for cx in (6.5, cv.w - 6.5):
            roll = (np.abs(cv.xx + 0.5 - cx) < 5.5) & (cv.yy >= 0) & (cv.yy < 34)
            prof = np.sqrt(np.clip(1 - ((cv.xx + 0.5 - cx) / 5.5) ** 2, 0, 1)) * 4.5
            cv.put(roll, 2.5 + prof, 'parch'); cv.G[roll] = 1
            for yk in (0, 1, 32, 33):
                r = roll & (cv.yy == yk); cv.M[r] = 'gold'
    bar3('rouleau', 34, 14, scroll, scaps)

    # resource plaque, 118 x 40 (and 170 x 40 for the hour): ornate frame, icon socket, flat enamel
    for nm, W in (('plaque', 136), ('plaque-l', 170)):
        cv = Cv(W, 40)
        d, vert = edge_dist(W, 40, 1, 1, W - 1, 39)
        ins = d >= 0
        hh, mm = profile_fin('iron')(d)
        m2 = ins & (mm != ''); cv.H[m2] = hh[m2]; cv.M[m2] = mm[m2]; cv.A |= m2; cv.G = vert.astype(np.float32)
        inner = ins & (d >= 5); cv.put(inner, 0.6, 'enamel')
        # socket for the icon
        sk = disc(cv, 20, 20, 15.5); cv.put(sk, 1.0 + 0 * cv.H, 'void'); cv.T[sk] = -0.6 + np.clip(((cv.xx - 20) + (cv.yy - 20)) / 20, -1, 1)[sk] * -0.6
        ring = disc(cv, 20, 20, 17.5) & ~sk; cv.put(ring, 3.2 + np.sin(np.clip((np.sqrt((cv.xx + .5 - 20) ** 2 + (cv.yy + .5 - 20) ** 2) - 15.5) / 2, 0, 1) * np.pi) * 1.0, 'gold')
        for (sx, sy) in ((4.5, 4.5), (W - 4.5, 4.5), (4.5, 35.5), (W - 4.5, 35.5)):
            stud(cv, sx, sy, 2.0, 'gold', 2.4)
        save(render(cv), nm)

    # medallion for the session count, 32 x 32
    cv = Cv(32, 32)
    r = np.sqrt((cv.xx + 0.5 - 16) ** 2 + (cv.yy + 0.5 - 16) ** 2)
    cv.put(r < 15, 3.0 + np.sin(np.clip((15 - r) / 3, 0, 1) * np.pi) * 1.2, 'iron')
    cv.put((r < 12.2) & (r >= 10.4), 4.0, 'gold')
    cv.put(r < 10.4, 1.2, 'enamel')
    for a in range(8):
        ang = a * np.pi / 4 + np.pi / 8; stud(cv, 16 + np.cos(ang) * 13.4, 16 + np.sin(ang) * 13.4, 1.2, 'gold', 3.0)
    save(render(cv), 'medaillon')

    # cartouche behind the title, 284 x 42
    CW = 284
    cv = Cv(CW, 42)
    shape = sup(lambda d, k: d.polygon([(8 * k, 1 * k), ((CW - 8) * k, 1 * k), ((CW - 1) * k, 21 * k), ((CW - 8) * k, 41 * k), (8 * k, 41 * k), (1 * k, 21 * k)], fill=255), CW, 42)
    dd = ndimage.distance_transform_edt(shape)
    hh, mm = profile_fin('gold', 'gold')(dd.astype(np.float32))
    m2 = shape & (mm != ''); cv.H[m2] = hh[m2]; cv.M[m2] = mm[m2]; cv.A |= m2
    cv.put(shape & (dd >= 5), 0.6, 'enamel')
    save(render(cv), 'cartouche')


MARKS = {
    'quete': ['.XXX.', 'XXXXX', 'XXXXX', 'XXXXX', '.XXX.', '.XXX.', '.XXX.', '..X..', '..X..', '.....', '.XXX.', '.XXX.'],
    'rendu': ['.XXXXX.', 'XXX.XXX', 'XX...XX', '.....XX', '....XXX', '...XXX.', '..XXX..', '..XX...', '..XX...', '.......', '..XX...', '..XX...'],
}


def marks():
    for k, rows in MARKS.items():
        m = glyph(rows)
        rp = M['gem-done'].rp if k == 'rendu' else ramp('#ffd23f', hs=30, light=1.25, dark=0.35)
        h, w = m.shape; P = 2
        out = np.zeros((h + 2 * P, w + 2 * P, 4), np.float32)
        Mm = np.zeros((h + 2 * P, w + 2 * P), bool); Mm[P:P + h, P:P + w] = m
        yy, xx = np.mgrid[0:h + 2 * P, 0:w + 2 * P]
        lv = 5.6 - (yy - P) / h * 3.0 + (~shift(Mm, 1, 0, False)) * 1.0 - (~shift(Mm, -1, 0, False)) * 1.0
        idx = np.clip(np.round(lv), 0, 6).astype(int)
        out[Mm, :3] = rp[idx[Mm]]; out[Mm, 3] = 255
        edge = ~Mm & (shift(Mm, 1, 0, False) | shift(Mm, -1, 0, False) | shift(Mm, 0, 1, False) | shift(Mm, 0, -1, False))
        out[edge, :3] = outline_of(rp); out[edge, 3] = 255
        near = ndimage.binary_dilation(Mm | edge, iterations=1) & ~(Mm | edge)
        out[near, :3] = rp[5]; out[near, 3] = 80
        save(out, f'marque-{k}')


def gems():
    for st in ('working', 'blocked', 'done', 'idle'):
        for size, nm in ((12, ''), (9, '-s')):
            P = 3
            cv = Cv(size + 2 * P, size + 2 * P)
            c = (size + 2 * P) / 2
            if st == 'blocked':  # a cut diamond shape for "needs you"
                m = (np.abs(cv.xx + 0.5 - c) + np.abs(cv.yy + 0.5 - c)) <= size / 2 + 0.3
                hh = (size / 2 - np.abs(cv.xx + 0.5 - c) - np.abs(cv.yy + 0.5 - c)) * 0.9 + 3
                cv.put(m, hh, 'gem-blocked')
            else:
                m = disc(cv, c, c, size / 2)
                cv.put(m, 3 + dome(cv, c, c, size / 2, 1.0), 'gem-' + st)
                # facet table
                tb = disc(cv, c, c, size / 4.2); cv.H[tb] = cv.H[tb].max()
            col = render(cv, ao=0.2, cast=0)
            # sparkle and glow halo (2 steps), like the markers
            rp = M['gem-' + st].rp
            sp = int(c - size / 4), int(c - size / 4)
            col[sp[1], sp[0], :3] = [255, 255, 245]
            near = ndimage.binary_dilation(col[..., 3] > 0, iterations=2) & (col[..., 3] == 0)
            if st != 'idle':
                col[near, :3] = rp[5]; col[near, 3] = 70
            save(col, f'gemme-{st}{nm}')


# ------------------------------------------------------------------ icons
def glyph(rows):
    return np.array([[ch == 'X' for ch in r] for r in rows])


def emboss(mask, matname, pad=1, height=2.5):
    h, w = mask.shape
    cv = Cv(w + 2 * pad, h + 2 * pad)
    m = np.zeros((h + 2 * pad, w + 2 * pad), bool); m[pad:pad + h, pad:pad + w] = mask
    dd = ndimage.distance_transform_edt(m)
    cv.put(m, height + np.clip(dd, 0, 2) * 0.6, matname)
    return render(cv, ao=0.2, cast=0)


ICONS = {
    'split-r': ['XXXXXXXXXXX', 'X....X....X', 'X....X....X', 'X....X....X', 'X....X....X', 'X....X....X', 'X....X....X', 'X....X....X', 'XXXXXXXXXXX'],
    'split-d': ['XXXXXXXXXXX', 'X.........X', 'X.........X', 'X.........X', 'XXXXXXXXXXX', 'X.........X', 'X.........X', 'X.........X', 'XXXXXXXXXXX'],
    'zoom': ['XXXX...XXXX', 'XX.......XX', 'X.X.....X.X', 'X.........X', '...........', 'X.........X', 'X.X.....X.X', 'XX.......XX', 'XXXX...XXXX'],
    'close': ['XX.......XX', 'XXX.....XXX', '.XXX...XXX.', '..XXX.XXX..', '...XXXXX...', '..XXX.XXX..', '.XXX...XXX.', 'XXX.....XXX', 'XX.......XX'],
    'plus': ['...XXX...', '...XXX...', '...XXX...', 'XXXXXXXXX', 'XXXXXXXXX', 'XXXXXXXXX', '...XXX...', '...XXX...', '...XXX...'],
    'suivant': ['XX...XX...', 'XXX..XXX..', '.XXX..XXX.', '..XXX..XXX', '..XXX..XXX', '.XXX..XXX.', 'XXX..XXX..', 'XX...XX...'],
}


def icons():
    for k, rows in ICONS.items():
        save(emboss(glyph(rows), 'bone', 1, 2.0), f'ic-{k}')
    # hourglass 20 x 26: gold frame, glass, sand
    cv = Cv(22, 28)
    fr = sup(lambda d, k: (d.rectangle([2 * k, 1 * k, 20 * k, 4 * k], fill=255), d.rectangle([2 * k, 23 * k, 20 * k, 26 * k], fill=255),
                           d.rectangle([3 * k, 4 * k, 5 * k, 23 * k], fill=255), d.rectangle([17 * k, 4 * k, 19 * k, 23 * k], fill=255)), 22, 28)
    gl = sup(lambda d, k: d.polygon([(6 * k, 4 * k), (16 * k, 4 * k), (12 * k, 13.5 * k), (16 * k, 23 * k), (6 * k, 23 * k), (10 * k, 13.5 * k)], fill=255), 22, 28)
    sand = gl & (((cv.yy >= 9) & (cv.yy < 13)) | (cv.yy >= 18) | ((np.abs(cv.xx + 0.5 - 11) < 1) & (cv.yy >= 13)))
    cv.put(gl, 2.0, 'gem-idle'); cv.T[gl] = 0.6
    cv.put(sand, 2.6, 'parch'); cv.T[sand] = 0.6
    cv.put(fr, 3.2 + 0 * cv.H, 'gold')
    for x in (4, 18):
        for y in (2.5, 24.5): stud(cv, x, y, 1.2, 'gold', 3.2)
    save(render(cv), 'ic-sablier')
    # heroes: a winged helm, 26 x 22
    cv = Cv(26, 22)
    helm = sup(lambda d, k: (d.pieslice([5 * k, 2 * k, 21 * k, 22 * k], 180, 360, fill=255), d.rectangle([5 * k, 12 * k, 21 * k, 20 * k], fill=255)), 26, 22)
    slit = sup(lambda d, k: (d.rectangle([8 * k, 11 * k, 18 * k, 13 * k], fill=255), d.rectangle([12 * k, 13 * k, 14 * k, 18 * k], fill=255)), 26, 22)
    wingL = sup(lambda d, k: d.polygon([(5 * k, 9 * k), (0, 2 * k), (1 * k, 7 * k), (0, 9 * k), (2 * k, 12 * k), (5 * k, 13 * k)], fill=255), 26, 22)
    dd = ndimage.distance_transform_edt(helm)
    cv.put(helm, 3 + np.clip(dd, 0, 5) * 0.7, 'iron')
    cv.put(helm & (np.abs(cv.xx + 0.5 - 13) < 1.5) & (cv.yy < 11), 6.5, 'gold')
    cv.put(slit, 1.0, 'void')
    cv.put(wingL, 4.0, 'gold'); cv.put(wingL[:, ::-1], 4.0, 'gold')
    save(render(cv), 'ic-heros')
    # sun and moon, 20 x 20
    cv = Cv(20, 20)
    rays = sup(lambda d, k: [d.polygon([(10 * k + np.cos(a) * 9.5 * k, 10 * k + np.sin(a) * 9.5 * k), (10 * k + np.cos(a + 0.35) * 5 * k, 10 * k + np.sin(a + 0.35) * 5 * k), (10 * k + np.cos(a - 0.35) * 5 * k, 10 * k + np.sin(a - 0.35) * 5 * k)], fill=255) for a in np.arange(8) * np.pi / 4], 20, 20)
    cv.put(rays, 3.0, 'gold')
    cv.put(disc(cv, 10, 10, 5.5), 3 + dome(cv, 10, 10, 5.5), 'gem-done')
    save(render(cv, cast=0), 'ic-soleil')
    cv = Cv(20, 20)
    moon = disc(cv, 10, 10, 8) & ~disc(cv, 13.5, 7.5, 7)
    cv.put(moon, 3 + dome(cv, 10, 10, 8, 0.5), 'bone')
    save(render(cv, cast=0), 'ic-lune')
    # crest: heater shield, sapphire field, gold border, crossed quill and sword, 30 x 36
    cv = Cv(30, 36)
    sh = sup(lambda d, k: d.polygon([(1 * k, 1 * k), (29 * k, 1 * k), (29 * k, 18 * k), (24 * k, 28 * k), (15 * k, 35 * k), (6 * k, 28 * k), (1 * k, 18 * k)], fill=255), 30, 36)
    dd = ndimage.distance_transform_edt(sh)
    cv.put(sh, 3 + np.clip(dd, 0, 6) * 0.25, 'gold')
    field = sh & (dd > 2.6)
    cv.put(field, 2.4 + np.clip(dd, 0, 8) * 0.12, 'gem-sapphire'); cv.T[field] = -1.2
    sword = sup(lambda d, k: (d.line([(8 * k, 7 * k), (22 * k, 27 * k)], fill=255, width=int(2.4 * k)), d.line([(7 * k, 21 * k), (15 * k, 15 * k)], fill=255, width=int(2 * k))), 30, 36)
    quill = sup(lambda d, k: (d.polygon([(22 * k, 6 * k), (25 * k, 8 * k), (12 * k, 25 * k), (9 * k, 27 * k), (10 * k, 24 * k)], fill=255)), 30, 36)
    cv.put(quill & field, 4.0, 'bone'); cv.put(sword & field, 4.6, 'gold')
    cv.put(disc(cv, 15, 31, 1.5) & sh, 5, 'gem-blocked')
    save(render(cv), 'blason')


# ------------------------------------------------------------------ district banners
CHARGES = {
    'etoile': lambda d, k: d.polygon([(5.5 * k + np.cos(a) * r * k, 5.5 * k + np.sin(a) * r * k) for i, a in enumerate(np.arange(10) * np.pi / 5 - np.pi / 2) for r in [5.4 if i % 2 == 0 else 2.3]], fill=255),
    'lune': lambda d, k: (d.ellipse([0.5 * k, 0.5 * k, 10.5 * k, 10.5 * k], fill=255), d.ellipse([3.5 * k, -0.5 * k, 12.5 * k, 8.5 * k], fill=0)),
    'tour': lambda d, k: (d.rectangle([2.5 * k, 3 * k, 8.5 * k, 11 * k], fill=255), d.rectangle([1.5 * k, 0.5 * k, 3.5 * k, 3 * k], fill=255), d.rectangle([4.5 * k, 0.5 * k, 6.5 * k, 3 * k], fill=255), d.rectangle([7.5 * k, 0.5 * k, 9.5 * k, 3 * k], fill=255), d.rectangle([4.5 * k, 7 * k, 6.5 * k, 11 * k], fill=0)),
    'cle': lambda d, k: (d.ellipse([0.5 * k, 0.5 * k, 6 * k, 6 * k], fill=255), d.ellipse([2.2 * k, 2.2 * k, 4.3 * k, 4.3 * k], fill=0), d.line([(4.5 * k, 4.5 * k), (10.5 * k, 10.5 * k)], fill=255, width=int(1.8 * k)), d.line([(8 * k, 8 * k), (6.5 * k, 9.8 * k)], fill=255, width=int(1.6 * k))),
    'chene': lambda d, k: (d.ellipse([0.5 * k, 0.5 * k, 10.5 * k, 7.5 * k], fill=255), d.rectangle([4.5 * k, 6 * k, 6.5 * k, 11 * k], fill=255)),
    'coupe': lambda d, k: (d.pieslice([1 * k, -4 * k, 10 * k, 6.5 * k], 0, 180, fill=255), d.rectangle([4.7 * k, 6 * k, 6.3 * k, 9 * k], fill=255), d.rectangle([2.5 * k, 9 * k, 8.5 * k, 10.8 * k], fill=255)),
    'epee': lambda d, k: (d.rectangle([4.6 * k, 0, 6.4 * k, 8 * k], fill=255), d.rectangle([1.5 * k, 7 * k, 9.5 * k, 8.6 * k], fill=255), d.rectangle([4.6 * k, 8.6 * k, 6.4 * k, 11 * k], fill=255)),
    'soleil': lambda d, k: ([d.line([(5.5 * k, 5.5 * k), (5.5 * k + np.cos(a) * 5.5 * k, 5.5 * k + np.sin(a) * 5.5 * k)], fill=255, width=int(1.4 * k)) for a in np.arange(8) * np.pi / 4], d.ellipse([2.3 * k, 2.3 * k, 8.7 * k, 8.7 * k], fill=255)),
}


def banners():
    W, H = 26, 40
    for ci in range(len(CLOTH)):
        for cname, draw in CHARGES.items():
            cv = Cv(W, H)
            cloth = sup(lambda d, k: d.polygon([(3 * k, 4 * k), (23 * k, 4 * k), (23 * k, 38 * k), (13 * k, 31 * k), (3 * k, 38 * k)], fill=255), W, H)
            # folds: gentle vertical waves, lit from the left
            wave = np.sin((cv.xx + 0.5) / 20 * 2 * np.pi * 1.5) * 1.1
            cv.put(cloth, 2.0 + wave, f'cloth{ci}')
            bd = cloth & ~ndimage.binary_erosion(cloth, iterations=2)
            cv.put(bd & (cv.yy > 5), 2.6 + wave, 'gold')
            ch = np.zeros((H, W), bool)
            c11 = sup(draw, 11, 11)
            ch[11:22, 7:18] = c11
            cv.put(ch & cloth, 3.6 + wave, 'gold')
            rod = (cv.yy >= 1) & (cv.yy < 4) & (cv.xx >= 0) & (cv.xx < W)
            cv.put(rod, 4.5, 'wood'); cv.M[rod & ((cv.xx < 2) | (cv.xx >= W - 2))] = 'gold'
            save(render(cv), f'banniere-{ci}-{cname}')


# ------------------------------------------------------------------ portraits
RACE = {'elfe': 'elf', 'orque': 'orc', 'humain': 'human', 'mort-vivant': 'undead', 'nain': 'dwarf'}
CLS = {'mage': 'mage', 'artificier': 'artificer', 'guerrier': 'warrior', 'pretre': 'priest', 'rodeur': 'ranger', 'voleur': 'rogue'}
HR = {'human': 80, 'elf': 83, 'orc': 86, 'undead': 78, 'dwarf': 64}
FIX = {'human-priest': 8, 'undead-priest': 5, 'dwarf-priest': 8, 'dwarf-mage': 11, 'undead-warrior': 3, 'human-mage': 3, 'human-warrior': 5, 'dwarf-artificer': 4}


def head_of(a, ax, ay, race, key):
    al = a[..., 3] > 128
    top = ay - HR[race]; x0 = max(0, ax - 12)
    y1 = top + int(0.07 * HR[race]); y2 = top + int(0.15 * HR[race])
    reg = a[y1:y2, x0:ax + 13].astype(int); A = al[y1:y2, x0:ax + 13]
    R, G, B = reg[..., 0], reg[..., 1], reg[..., 2]
    glow = A & (((R > 200) & (G > 150) & (B < 120)) | ((R > 150) & (B > 180) & (G < 120)))
    cnt = A.sum(0); runs = []; s = None
    for i, v in enumerate(list(cnt) + [0]):
        if v >= 3 and s is None: s = i
        if v < 3 and s is not None: runs.append((s, i)); s = None
    def score(rr):
        s, e = rr; g = glow[:, s:e].sum() / max(1, A[:, s:e].sum()); return (e - s) * (1 - 1.5 * g) - abs((s + e) / 2 + x0 - ax) * 0.15
    cx = x0 + sum(max(runs, key=score)) // 2 if runs else ax
    return cx, top + int(0.11 * HR[race])


def portrait_bg(S, tone='#2c2440'):
    rp = ramp(tone, hs=20)
    yy, xx = np.mgrid[0:S, 0:S]
    r = np.sqrt((xx + 0.5 - S * 0.42) ** 2 + (yy + 0.5 - S * 0.36) ** 2) / S
    lv = 4.0 - r * 5.0 + BAYER[yy % 4, xx % 4] * 0.5
    out = np.zeros((S, S, 4), np.float32)
    out[..., :3] = rp[np.clip(np.round(lv), 0, 6).astype(int)]; out[..., 3] = 255
    return out


def over(dst, src, x, y):
    h, w = src.shape[:2]
    a = src[..., 3:4] / 255.0
    dst[y:y + h, x:x + w, :3] = dst[y:y + h, x:x + w, :3] * (1 - a) + src[..., :3] * a
    dst[y:y + h, x:x + w, 3] = np.maximum(dst[y:y + h, x:x + w, 3], src[..., 3])


def bezel(S, mat_rim='gold', gem=None):
    """A square portrait bezel S x S: gold rim (2), dark inner edge (1); transparent inside."""
    cv = Cv(S, S)
    d, vert = edge_dist(S, S)
    rim = d < 2; cv.put(rim, 3.0 + np.sin(np.pi * np.clip(d / 2, 0, 1)) * 0.8, mat_rim)
    inn = d == 2; cv.put(inn, 1.2, 'irondk')
    for (x, y) in ((1, 1), (S - 2, 1), (1, S - 2), (S - 2, S - 2)):
        cv.put(disc(cv, x + 0.5, y + 0.5, 1.6), 4.5, mat_rim)
    if gem:
        g = disc(cv, S / 2, S - 1.5, 2.2); cv.put(g, 5.0 + dome(cv, S / 2, S - 1.5, 2.2), 'gem-' + gem)
    return render(cv, outline=False, cast=0.5)


def portraits():
    if not HEROES or not os.path.isdir(HEROES):
        print('portraits skipped (set HEROES)'); return
    meta = json.load(open(os.path.join(HEROES, 'meta.json')))
    os.makedirs(os.path.join(OUT, 'heros'), exist_ok=True)
    for fr, race in RACE.items():
        for fc, cl in CLS.items():
            key = f'{race}-{cl}'; m = meta[key]
            a = np.array(Image.open(os.path.join(HEROES, key + '.png')).convert('RGBA'))[::2, ::2].astype(np.float32)
            cx, cy = head_of(a, m['ax'], m['ay'], race, key)
            cx += FIX.get(key, 0)
            P = 60
            pad = np.zeros((a.shape[0] + 2 * P, a.shape[1] + 2 * P, 4), np.float32); pad[P:-P, P:-P] = a
            for S, nm, dy in ((26, 'p26', 2), (22, 'p22', 2)):
                inner = S - 6
                out = np.zeros((S, S, 4), np.float32)
                over(out, portrait_bg(S), 0, 0)
                y0 = cy - inner // 2 + dy + P; x0 = cx - inner // 2 + P
                # the crop runs to the bottom edge so the shoulders fill the frame
                crop = pad[y0:y0 + S, x0 - 3:x0 - 3 + S]
                over(out, crop, 0, 0)
                over(out, bezel(S), 0, 0)
                save(out, f'heros/{fr}-{fc}-{nm}')
            # full figure for the unit card: 64 x 96 framed
            W, H = 66, 98
            out = np.zeros((H, W, 4), np.float32)
            bgp = portrait_bg(max(W, H), '#2a2338')
            out[:] = bgp[:H, :W]
            # floor glow ellipse
            yy, xx = np.mgrid[0:H, 0:W]
            fl = (((xx + 0.5 - W / 2) / 24) ** 2 + ((yy + 0.5 - (H - 9)) / 5) ** 2) <= 1
            out[fl, :3] = out[fl, :3] * 0.55
            fig = a
            fx = int(W / 2 - m['ax']); fy = int(H - 8 - m['ay'])
            fh, fw = fig.shape[:2]
            sx0 = max(0, -fx); sy0 = max(0, -fy)
            sub = fig[sy0:min(fh, H - fy), sx0:min(fw, W - fx)]
            over(out, sub, max(0, fx), max(0, fy))
            fr9 = np.zeros((H, W, 4), np.float32)
            cvf = Cv(W, H); d, vert = edge_dist(W, H)
            hh, mm = profile_fin('gold', 'gold')(d)
            ins = (mm != '') & (d < 4); cvf.H[ins] = hh[ins]; cvf.M[ins] = mm[ins]; cvf.A |= ins; cvf.G = vert.astype(np.float32)
            for (x, y) in ((3, 3), (W - 4, 3), (3, H - 4), (W - 4, H - 4)):
                stud(cvf, x + 0.5, y + 0.5, 2.6, 'gold', 2.6)
            over(out, render(cvf, outline=False), 0, 0)
            save(out, f'heros/{fr}-{fc}-carte')


if __name__ == '__main__':
    what = sys.argv[1:] or ['pieces', 'marks', 'gems', 'icons', 'banners', 'portraits']
    for w in what: globals()[w]()
    mp = os.path.join(OUT, 'meta.json')
    old = json.load(open(mp)) if os.path.exists(mp) else {}
    old.update(META); json.dump(old, open(mp, 'w'), indent=1)
    print('ok', what)
