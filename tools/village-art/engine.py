"""Valbrume pixel-art HD engine.

Voxel models -> per-pixel iso ray cast (2:1 dimetric, u = x - y, v = (x + y)/2 - z),
quantised to hand-authored 7-step colour ramps with hue shifting, textured per material,
top-left light with cast shadows + ambient occlusion, selective coloured outlines, rim light.
1 world unit = 1 logical pixel horizontally. Output at 1x logical; save2x doubles (nearest).
"""
import colorsys
import numpy as np
from scipy import ndimage
from PIL import Image

L = np.array([-0.30, 0.42, 0.86]); L = L / np.linalg.norm(L)

# ---------------------------------------------------------------- colour ramps
def hx(h):
    h = h.lstrip('#'); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))

def ramp(base, n=7, cool=232, warm=48, dark=0.30, light=1.32, hs=22):
    """Hue-shifted ramp: darks drift to blue-violet and saturate, lights drift to yellow."""
    r, g, b = [c / 255 for c in hx(base)]
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    out = []
    mid = (n - 1) / 2
    for k in range(n):
        t = (k - mid) / mid  # -1 .. 1
        hh = h * 360
        target = cool if t < 0 else warm
        d = ((target - hh + 180) % 360) - 180
        hh = (hh + d * min(1, abs(t)) * hs / 90) % 360
        vv = v * (1 + (light - 1) * t) if t > 0 else v * (1 + (1 - dark) * t)
        ss = s * (1 + 0.18 * -t) if t > 0 else min(1, s * (1 + 0.25 * -t))
        if t > 0.6:
            ss *= 0.85
        rr, gg, bb = colorsys.hsv_to_rgb(hh / 360, max(0, min(1, ss)), max(0, min(1, vv)))
        out.append((int(rr * 255), int(gg * 255), int(bb * 255)))
    return np.array(out, dtype=np.float32)

def outline_of(rp):
    c = rp[0] / 255
    h, s, v = colorsys.rgb_to_hsv(*c)
    hh = h * 360; d = ((262 - hh + 180) % 360) - 180; hh += d * 0.35
    r, g, b = colorsys.hsv_to_rgb((hh % 360) / 360, min(1, s * 1.1 + 0.1), v * 0.55)
    return np.array([r * 255, g * 255, b * 255], dtype=np.float32)

# ---------------------------------------------------------------- noise
def hash3(ix, iy, iz, seed=0):
    h = (ix.astype(np.int64) * 73856093) ^ (iy.astype(np.int64) * 19349663) ^ (iz.astype(np.int64) * 83492791) ^ (seed * 2654435761)
    h = (h ^ (h >> 13)) * 1274126177
    h = h ^ (h >> 16)
    return (h & 0xFFFF).astype(np.float32) / 65535.0

def vnoise2(x, y, scale, seed=0, period=None):
    xs, ys = x / scale, y / scale
    x0, y0 = np.floor(xs), np.floor(ys)
    fx, fy = xs - x0, ys - y0
    fx = fx * fx * (3 - 2 * fx); fy = fy * fy * (3 - 2 * fy)
    def g(a, b):
        a = a.astype(np.int64); b = b.astype(np.int64)
        if period:
            p = int(round(period / scale)); a = a % p; b = b % p
        return hash3(a, b, np.zeros_like(a), seed)
    return (g(x0, y0) * (1 - fx) * (1 - fy) + g(x0 + 1, y0) * fx * (1 - fy)
            + g(x0, y0 + 1) * (1 - fx) * fy + g(x0 + 1, y0 + 1) * fx * fy)

BAYER = (np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) + 0.5) / 16 - 0.5

# ---------------------------------------------------------------- materials
class Mat:
    def __init__(self, base, tex=None, n=7, emissive=None, night=None, flat=False, rim=True, params=None, rp=None, **kw):
        self.ramp = rp if rp is not None else ramp(base, n, **kw)
        self.outline = outline_of(self.ramp)
        self.tex = tex; self.emissive = emissive; self.night = night
        self.flat = flat; self.rim = rim; self.p = params or {}

# ---------------------------------------------------------------- volume
VS_DEFAULT = [1.0]
class Vol:
    def __init__(self, x0, x1, y0, y1, z0, z1, vs=None):
        vs = VS_DEFAULT[0] if vs is None else vs
        self.vs = vs
        self.o = np.array([x0, y0, z0], dtype=np.float32)
        self.shape = tuple(int(np.ceil((b - a) / vs)) for a, b in ((x0, x1), (y0, y1), (z0, z1)))
        self.m = np.zeros(self.shape, np.uint8)
        self.hi = self.o + np.array(self.shape) * vs

    def put(self, bbox, fn, mat):
        x0, x1, y0, y1, z0, z1 = bbox
        sl = []
        for a, b, o, n in ((x0, x1, self.o[0], self.shape[0]), (y0, y1, self.o[1], self.shape[1]), (z0, z1, self.o[2], self.shape[2])):
            i0 = max(0, int(np.floor((a - o) / self.vs)) - 1); i1 = min(n, int(np.ceil((b - o) / self.vs)) + 1)
            sl.append(slice(i0, max(i0, i1)))
        if any(s.stop <= s.start for s in sl):
            return
        X, Y, Z = np.meshgrid(*[(np.arange(s.start, s.stop) + 0.5) * self.vs + self.o[k] for k, s in enumerate(sl)], indexing='ij')
        mask = fn(X, Y, Z)
        sub = self.m[sl[0], sl[1], sl[2]]
        if callable(mat):
            vals = mat(X, Y, Z)
            sub[mask] = vals[mask]
        else:
            sub[mask] = mat

    # primitives -------------------------------------------------------
    def box(self, x0, x1, y0, y1, z0, z1, mat):
        self.put((x0, x1, y0, y1, z0, z1), lambda X, Y, Z: (X >= x0) & (X < x1) & (Y >= y0) & (Y < y1) & (Z >= z0) & (Z < z1), mat)

    def cyl(self, cx, cy, r, z0, z1, mat, rin=None):
        def f(X, Y, Z):
            d = (X - cx) ** 2 + (Y - cy) ** 2
            m = (d <= r * r) & (Z >= z0) & (Z < z1)
            if rin: m &= d > rin * rin
            return m
        self.put((cx - r, cx + r, cy - r, cy + r, z0, z1), f, mat)

    def cone(self, cx, cy, r0, z0, z1, mat, p=1.0, r1=0.0):
        def f(X, Y, Z):
            t = np.clip((Z - z0) / (z1 - z0), 0, 1)
            rr = r1 + (r0 - r1) * (1 - t) ** p
            return ((X - cx) ** 2 + (Y - cy) ** 2 <= rr * rr) & (Z >= z0) & (Z < z1)
        self.put((cx - r0, cx + r0, cy - r0, cy + r0, z0, z1), f, mat)

    def ell(self, cx, cy, cz, rx, ry, rz, mat):
        self.put((cx - rx, cx + rx, cy - ry, cy + ry, cz - rz, cz + rz),
                 lambda X, Y, Z: ((X - cx) / rx) ** 2 + ((Y - cy) / ry) ** 2 + ((Z - cz) / rz) ** 2 <= 1, mat)

    def capsule(self, a, b, r, mat):
        a = np.array(a, float); b = np.array(b, float)
        lo = np.minimum(a, b) - r; hi = np.maximum(a, b) + r
        ab = b - a; l2 = max(1e-6, ab @ ab)
        def f(X, Y, Z):
            px, py, pz = X - a[0], Y - a[1], Z - a[2]
            t = np.clip((px * ab[0] + py * ab[1] + pz * ab[2]) / l2, 0, 1)
            dx, dy, dz = px - t * ab[0], py - t * ab[1], pz - t * ab[2]
            return dx * dx + dy * dy + dz * dz <= r * r
        self.put((lo[0], hi[0], lo[1], hi[1], lo[2], hi[2]), f, mat)

    def roof(self, x0, x1, y0, y1, z0, ztop, mat, axis='x', hip=0.0, th=4.0, fill=None, curve=1.0):
        """Gable (hip=0) or hipped roof over rect; ridge along `axis`. curve>1 = concave flared eaves."""
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        hw = (y1 - y0) / 2 if axis == 'x' else (x1 - x0) / 2
        def height(X, Y):
            if axis == 'x':
                d = np.abs(Y - cy) / hw
                if hip: d = np.maximum(d, (np.abs(X - cx) - ((x1 - x0) / 2 - hw * hip)) / (hw * hip))
            else:
                d = np.abs(X - cx) / hw
                if hip: d = np.maximum(d, (np.abs(Y - cy) - ((y1 - y0) / 2 - hw * hip)) / (hw * hip))
            d = np.clip(d, 0, 1.5)
            return z0 + (ztop - z0) * np.clip(1 - d, 0, 1) ** curve
        def f(X, Y, Z):
            h = height(X, Y)
            inside = (X >= x0) & (X < x1) & (Y >= y0) & (Y < y1) & (Z >= z0) & (Z <= h)
            return inside & (Z > h - th)
        self.put((x0, x1, y0, y1, z0, ztop + 1), f, mat)
        if fill:
            self.put((x0 + th, x1 - th, y0 + th, y1 - th, z0, ztop), lambda X, Y, Z: (Z <= height(X, Y) - th + 1) & (X >= x0 + th) & (X < x1 - th) & (Y >= y0 + th) & (Y < y1 - th), fill)

    def carve_box(self, *a):
        self.box(*a, 0)

# ---------------------------------------------------------------- renderer
def render(vol, mats, shadows=True, ground=True, outline=True, pad=4, amb=0.34, tex_seed=0, ao_strength=0.55, dither=0.45):
    vs = vol.vs
    o, hi = vol.o, vol.hi
    cs = np.array([[x, y, z] for x in (o[0], hi[0]) for y in (o[1], hi[1]) for z in (o[2], hi[2])])
    u = cs[:, 0] - cs[:, 1]; v = (cs[:, 0] + cs[:, 1]) / 2 - cs[:, 2]
    umin, umax = int(np.floor(u.min())) - pad, int(np.ceil(u.max())) + pad
    vmin, vmax = int(np.floor(v.min())) - pad, int(np.ceil(v.max())) + pad
    # shadow reach to the right
    if ground and shadows:
        zmax = hi[2]
        sh = zmax / L[2]
        umax += int(sh * (abs(L[0]) + abs(L[1]))) + 2
    W, H = umax - umin, vmax - vmin
    U, V = np.meshgrid(np.arange(W) + umin + 0.5, np.arange(H) + vmin + 0.5)
    U = U.ravel(); V = V.ravel()
    bx = (2 * V + U) / 2; by = (2 * V - U) / 2; bz = np.zeros_like(U)
    base = np.stack([bx, by, bz], 1)
    occ = vol.m > 0
    tlo = np.max(np.stack([o[0] - bx, o[1] - by, o[2] - bz]), 0)
    thi = np.min(np.stack([hi[0] - bx, hi[1] - by, hi[2] - bz]), 0)
    N = U.size
    hit = np.zeros(N, bool); th = np.full(N, -1e9, np.float32)
    act = np.nonzero(thi > tlo)[0]
    step = vs * 0.5
    t = thi[act] - 1e-3
    shp = np.array(vol.shape)
    while act.size:
        P = base[act] + t[:, None]
        idx = np.floor((P - o) / vs).astype(np.int64)
        ok = np.all((idx >= 0) & (idx < shp), 1)
        occh = np.zeros(act.size, bool)
        ii = idx[ok]
        occh[ok] = occ[ii[:, 0], ii[:, 1], ii[:, 2]]
        if occh.any():
            hit[act[occh]] = True; th[act[occh]] = t[occh]
        t = t - step
        keep = (~occh) & (t >= tlo[act])
        act = act[keep]; t = t[keep]
    # refine (binary search between t and t+step)
    hi_ = np.nonzero(hit)[0]
    a = th[hi_]; b = a + step
    for _ in range(5):
        m = (a + b) / 2
        P = base[hi_] + m[:, None]
        idx = np.clip(np.floor((P - o) / vs).astype(np.int64), 0, shp - 1)
        oc = occ[idx[:, 0], idx[:, 1], idx[:, 2]]
        a = np.where(oc, m, a); b = np.where(oc, b, m)
    th[hi_] = a
    P = base[hi_] + a[:, None]
    idx = np.clip(np.floor((P - o) / vs - 1e-4).astype(np.int64), 0, shp - 1)
    mid = vol.m[idx[:, 0], idx[:, 1], idx[:, 2]]
    # normals from smoothed occupancy
    sm = ndimage.gaussian_filter(occ.astype(np.float32), 1.25)
    gx, gy, gz = np.gradient(sm)
    c = ((P - o) / vs - 0.5).T
    n = -np.stack([ndimage.map_coordinates(g, c, order=1, mode='nearest') for g in (gx, gy, gz)], 1)
    n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-6
    # flat-shaded materials snap to the dominant axis
    flat = np.zeros(len(mid), bool)
    for k, mt in mats.items():
        if mt.flat: flat |= mid == k
    if flat.any():
        nf = n[flat]; ax = np.argmax(np.abs(nf), 1)
        nn = np.zeros_like(nf); nn[np.arange(len(nf)), ax] = np.sign(nf[np.arange(len(nf)), ax]); n[flat] = nn
    lam = n @ L
    # cast shadows
    lit = np.ones(len(mid), np.float32)
    if shadows:
        lit = 1 - march_shadow(vol, occ, P + n * vs * 1.2 + L * vs * 0.6)
    # ambient occlusion: smoothed occupancy probe + ground proximity
    big = ndimage.gaussian_filter(occ.astype(np.float32), 4.0 / vs * 0.6)
    probe = P + n * 3.0
    cc = ((probe - o) / vs - 0.5).T
    aoo = ndimage.map_coordinates(big, cc, order=1, mode='constant')
    gro = np.clip(1 - (P[:, 2] - 0) / 10, 0, 1) * (1 - np.abs(n[:, 2]))
    ao = np.clip(1 - ao_strength * np.clip(aoo * 2.2 - 0.25, 0, 1) - 0.32 * gro, 0.3, 1)
    val = (amb + (1 - amb) * np.clip(lam, 0, 1) * lit) * ao
    val += 0.10 * np.clip(-lam, 0, 1) * (n[:, 2] < 0.3)  # bounce light into shadow side
    # textures
    px = (U[hi_] - umin).astype(int); py = (V[hi_] - vmin).astype(int)
    level = val * 6.0 - 0.2
    out = np.zeros((H, W, 4), np.float32)
    emis = np.zeros((H, W, 4), np.float32)
    matmap = np.zeros((H, W), np.int32); depth = np.full((H, W), -1e9, np.float32)
    nz = np.zeros((H, W), np.float32)
    matmap[py, px] = mid; depth[py, px] = a + 0  # larger = nearer
    nz[py, px] = n[:, 2]
    rampidx = np.zeros(len(mid), np.float32)
    colors = np.zeros((len(mid), 3), np.float32)
    for k, mt in mats.items():
        sel = np.nonzero(mid == k)[0]
        if not sel.size: continue
        lv = level[sel].copy()
        swap = None
        if mt.tex is not None:
            r = mt.tex(P[sel], n[sel], mt.p, lv)
            if isinstance(r, tuple): off, swap = r
            else: off = r
            lv = lv + off
        if mt.emissive is not None:
            lv = mt.emissive + (lv - level[sel]) + (level[sel] - 3) * 0.25
        lv = lv + BAYER[py[sel] % 4, px[sel] % 4] * dither
        ri = np.clip(np.round(lv), 0, len(mt.ramp) - 1).astype(int)
        col = mt.ramp[ri]
        if swap is not None:
            for sk in np.unique(swap):
                if sk == 0: continue
                msk = swap == sk; m2 = mats[int(sk)]
                l2 = np.clip(np.round(lv[msk]), 0, len(m2.ramp) - 1).astype(int)
                col[msk] = m2.ramp[l2]
        colors[sel] = col
        if mt.night is not None:
            nc = np.array(hx(mt.night), np.float32)
            emis[py[sel], px[sel], :3] = nc; emis[py[sel], px[sel], 3] = 255
    out[py, px, :3] = colors; out[py, px, 3] = 255
    hitmap = out[..., 3] > 0
    # rim light: top-left exposed edge pixels facing up/left
    up = np.zeros_like(hitmap); up[1:] = hitmap[:-1]
    lf = np.zeros_like(hitmap); lf[:, 1:] = hitmap[:, :-1]
    rimm = hitmap & (~up | ~lf)
    if rimm.any():
        ys, xs = np.nonzero(rimm)
        for yy, xx in zip(ys, xs):
            mt = mats.get(int(matmap[yy, xx]))
            if mt is None or not mt.rim or mt.emissive is not None: continue
            if nz[yy, xx] > -0.2:
                c0 = out[yy, xx, :3]
                d = np.abs(mt.ramp - c0).sum(1); i = int(np.argmin(d))
                out[yy, xx, :3] = mt.ramp[min(len(mt.ramp) - 1, i + 1)]
    if outline:
        # interior depth edges: the farther pixel gets its darkest step
        for dy, dx in ((0, 1), (1, 0), (0, -1), (-1, 0)):
            nb = np.roll(np.roll(depth, dy, 0), dx, 1)
            nbm = np.roll(np.roll(matmap, dy, 0), dx, 1)
            edge = hitmap & (nb - depth > 5.5 * max(1, vs * 2)) & (nb > -1e8)
            ys, xs = np.nonzero(edge)
            for yy, xx in zip(ys, xs):
                mt = mats.get(int(matmap[yy, xx]))
                if mt is None or mt.emissive is not None: continue
                out[yy, xx, :3] = mt.ramp[0] * 0.9 + mt.outline * 0.1
        # outer silhouette, drawn on the empty pixel outside (1 px)
        o2 = out.copy()
        for dy, dx in ((0, 1), (1, 0), (0, -1), (-1, 0), (1, 1), (-1, -1), (1, -1), (-1, 1)):
            src_hit = np.roll(np.roll(hitmap, dy, 0), dx, 1)
            src_mat = np.roll(np.roll(matmap, dy, 0), dx, 1)
            diag = dy != 0 and dx != 0
            cand = (~hitmap) & src_hit & (o2[..., 3] == 0)
            if diag:
                continue
            ys, xs = np.nonzero(cand)
            for yy, xx in zip(ys, xs):
                mt = mats.get(int(src_mat[yy, xx]))
                if mt is None: continue
                col = mt.outline
                if mt.emissive is not None:
                    col = mt.ramp[0]
                # selective: lighter outline on the lit (upper-left) side
                if dy == 1 or dx == 1:
                    col = col * 0.6 + mt.ramp[0] * 0.4 if (dy == 1 and nz[yy - 1 if yy > 0 else 0, xx] > 0.3) else col
                o2[yy, xx, :3] = col; o2[yy, xx, 3] = 255
        out = o2
    # ground shadow + contact AO layer
    shadow = np.zeros((H, W, 4), np.float32)
    if ground:
        gb = base.copy()
        sh = march_shadow(vol, occ, gb + L * 0.8) if shadows else np.zeros(N)
        g_ao = ndimage.gaussian_filter(occ[:, :, :max(1, int(8 / vs))].any(2).astype(np.float32), 3.0 / vs)
        cc = ((gb[:, :2] - o[:2]) / vs - 0.5).T
        gao = ndimage.map_coordinates(g_ao, cc, order=1, mode='constant')
        alpha = np.clip(np.maximum(sh * 0.42, np.clip(gao * 0.9, 0, 0.5)), 0, 0.55)
        alpha = np.round(alpha * 4) / 4 * 0.55 / 0.55  # quantise to pixel-art steps
        al = alpha.reshape(H, W)
        shadow[..., 0] = 24; shadow[..., 1] = 18; shadow[..., 2] = 52; shadow[..., 3] = al * 255
    anchor = (-umin, -vmin)  # pixel of world origin (0,0,0)
    return dict(color=out.astype(np.uint8), shadow=shadow.astype(np.uint8), emis=emis.astype(np.uint8), anchor=anchor,
                depth=depth, matmap=matmap)

def march_shadow(vol, occ, P0, maxd=None):
    vs = vol.vs; o = vol.o; shp = np.array(vol.shape)
    if maxd is None: maxd = (vol.hi[2] - P0[:, 2].min()) / L[2] + 2
    res = np.zeros(len(P0), np.float32)
    act = np.arange(len(P0)); t = np.zeros(len(P0), np.float32)
    # skip rays that never enter the bbox
    step = vs * 0.75
    while act.size:
        P = P0[act] + L * t[:, None]
        idx = np.floor((P - o) / vs).astype(np.int64)
        ok = np.all((idx >= 0) & (idx < shp), 1)
        o_ = np.zeros(act.size, bool); ii = idx[ok]
        o_[ok] = occ[ii[:, 0], ii[:, 1], ii[:, 2]]
        res[act[o_]] = 1
        t = t + step
        keep = (~o_) & (P[:, 2] < vol.hi[2]) & (t < maxd)
        act = act[keep]; t = t[keep]
    return res

# ---------------------------------------------------------------- output helpers
def trim(layers, keys=('color', 'shadow', 'emis')):
    a = np.zeros(layers['color'].shape[:2], bool)
    for k in keys: a |= layers[k][..., 3] > 0
    ys, xs = np.nonzero(a)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    for k in keys: layers[k] = layers[k][y0:y1, x0:x1]
    ax, ay = layers['anchor']; layers['anchor'] = (ax - x0, ay - y0)
    return layers

def save2x(arr, path):
    Image.fromarray(arr).resize((arr.shape[1] * 2, arr.shape[0] * 2), Image.NEAREST).save(path)

def over(dst, src, x, y, opacity=1.0):
    """alpha composite src (uint8 RGBA) onto dst float RGBA at integer x,y."""
    h, w = src.shape[:2]; H, W = dst.shape[:2]
    x0, y0 = max(0, x), max(0, y); x1, y1 = min(W, x + w), min(H, y + h)
    if x1 <= x0 or y1 <= y0: return
    s = src[y0 - y:y1 - y, x0 - x:x1 - x].astype(np.float32)
    a = s[..., 3:4] / 255 * opacity
    d = dst[y0:y1, x0:x1]
    d[..., :3] = d[..., :3] * (1 - a) + s[..., :3] * a
    d[..., 3:4] = np.maximum(d[..., 3:4], a * 255)
