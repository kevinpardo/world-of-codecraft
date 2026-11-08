"""v2 renderer: same voxel -> iso ray cast + ramps, plus a global-illumination-ish light model.

New vs v1:
- soft sun shadows (4 jittered sun rays) and soft ground shadows with dithered steps
- hemispheric sky light with real sky visibility (7 rays per pixel): eaves, overhangs, crevices go dark
- multi-scale ambient occlusion + a cavity map (worn convex edges, dark concave seams)
- warm bounce light from the grass on lower walls, dirt/damp gradient where walls meet the ground
- colour temperature: warm in sun, cool sky tint in shade (pixel-crisp multiplicative tint on the ramp colour)
- per-texel micro contrast + large-scale colour drift on big surfaces ("texture" slider)
- night: local light layer (light falloff from windows, lanterns, fires onto nearby surfaces)
- render scale S: model units -> logical px (buildings can be scaled without changing their design)
"""
import numpy as np
from scipy import ndimage
from engine import L, BAYER, hash3, outline_of, hx

SUN_JIT = [L]
for a in (0.0, 1.57, 3.14, 4.71):
    d = L + 0.07 * np.array([np.cos(a), np.sin(a), -0.3 * np.cos(a)]); SUN_JIT.append(d / np.linalg.norm(d))
SUN_JIT = SUN_JIT[1:]
SKY = [np.array([0, 0, 1.0])]
for k in range(6):
    a = k / 6 * 2 * np.pi + 0.3
    d = np.array([np.cos(a) * 0.62, np.sin(a) * 0.62, 0.78]); SKY.append(d / np.linalg.norm(d))
GSKY = []
for k in range(6):
    a = k / 6 * 2 * np.pi
    d = np.array([np.cos(a) * 0.85, np.sin(a) * 0.85, 0.52]); GSKY.append(d / np.linalg.norm(d))

def blob(P, sc, seed):
    q = np.floor(P / sc).astype(np.int64)
    return hash3(q[:, 0], q[:, 1], q[:, 2], seed)

def march(vol, occ, P0, D, maxd, step=None):
    """1.0 where the ray P0 + tD (0<t<maxd) hits an occupied voxel. Slab-clipped to the volume."""
    vs = vol.vs; o = vol.o; hi = vol.hi; shp = np.array(vol.shape)
    step = step or vs * 0.8
    with np.errstate(divide='ignore', invalid='ignore'):
        inv = np.where(np.abs(D) > 1e-9, 1.0 / D, 1e12)
    t0 = (o - P0) * inv; t1 = (hi - P0) * inv
    tn = np.max(np.minimum(t0, t1), 1); tf = np.min(np.maximum(t0, t1), 1)
    tn = np.maximum(tn, 0); tf = np.minimum(tf, maxd)
    res = np.zeros(len(P0), np.float32)
    act = np.nonzero(tf > tn)[0]
    t = tn[act].astype(np.float32)
    while act.size:
        P = P0[act] + D * t[:, None]
        idx = np.floor((P - o) / vs).astype(np.int64)
        ok = np.all((idx >= 0) & (idx < shp), 1)
        hit = np.zeros(act.size, bool); ii = idx[ok]
        hit[ok] = occ[ii[:, 0], ii[:, 1], ii[:, 2]]
        res[act[hit]] = 1
        t = t + step
        keep = (~hit) & (t < tf[act])
        act = act[keep]; t = t[keep]
    return res

def render(vol, mats, S=1.0, shadows=True, ground=True, outline=True, pad=4, amb=0.5, ao_strength=0.55,
           dither=0.4, micro=1.0, nightlights=True, skyrange=60, sdf=None):
    vs = vol.vs; o, hi = vol.o, vol.hi
    cs = np.array([[x, y, z] for x in (o[0], hi[0]) for y in (o[1], hi[1]) for z in (o[2], hi[2])])
    u = S * (cs[:, 0] - cs[:, 1]); v = S * ((cs[:, 0] + cs[:, 1]) / 2 - cs[:, 2])
    umin, umax = int(np.floor(u.min())) - pad, int(np.ceil(u.max())) + pad
    vmin, vmax = int(np.floor(v.min())) - pad, int(np.ceil(v.max())) + pad
    if ground and shadows:
        umax += int(S * hi[2] / L[2] * (abs(L[0]) + abs(L[1]))) + 2
        vmax += int(S * 14)
    W, H = umax - umin, vmax - vmin
    U, V = np.meshgrid(np.arange(W) + umin + 0.5, np.arange(H) + vmin + 0.5)
    U = U.ravel() / S; V = V.ravel() / S
    bx = (2 * V + U) / 2; by = (2 * V - U) / 2
    base = np.stack([bx, by, np.zeros_like(U)], 1)
    occ = vol.m > 0
    tlo = np.max(np.stack([o[0] - bx, o[1] - by, o[2] - 0 * bx]), 0)
    thi = np.min(np.stack([hi[0] - bx, hi[1] - by, hi[2] - 0 * bx]), 0)
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
        occh = np.zeros(act.size, bool); ii = idx[ok]
        occh[ok] = occ[ii[:, 0], ii[:, 1], ii[:, 2]]
        hit[act[occh]] = True; th[act[occh]] = t[occh]
        t = t - step
        keep = (~occh) & (t >= tlo[act])
        act = act[keep]; t = t[keep]
    hi_ = np.nonzero(hit)[0]
    a = th[hi_]; b = a + step
    for _ in range(6):
        m = (a + b) / 2
        P = base[hi_] + m[:, None]
        idx = np.clip(np.floor((P - o) / vs).astype(np.int64), 0, shp - 1)
        oc = occ[idx[:, 0], idx[:, 1], idx[:, 2]]
        a = np.where(oc, m, a); b = np.where(oc, b, m)
    P = base[hi_] + a[:, None]
    idx = np.clip(np.floor((P - o) / vs - 1e-4).astype(np.int64), 0, shp - 1)
    mid = vol.m[idx[:, 0], idx[:, 1], idx[:, 2]]
    occf = occ.astype(np.float32)
    if sdf is not None:
        # refine onto the zero crossing of the trilinear SDF, normals = SDF gradient (smooth, organic)
        lo_t = a - step; hi_t = a + step
        for _ in range(8):
            mt = (lo_t + hi_t) / 2
            Pm = base[hi_] + mt[:, None]
            dv = ndimage.map_coordinates(sdf, ((Pm - o) / vs - 0.5).T, order=1, mode='nearest')
            lo_t = np.where(dv < 0, mt, lo_t); hi_t = np.where(dv < 0, hi_t, mt)
        a = lo_t
        P = base[hi_] + a[:, None]
        sm = ndimage.gaussian_filter(sdf, 0.6)
        gx, gy, gz = np.gradient(sm)
        cc = ((P - o) / vs - 0.5).T
        n = np.stack([ndimage.map_coordinates(g, cc, order=1, mode='nearest') for g in (gx, gy, gz)], 1)
    else:
        sm = ndimage.gaussian_filter(occf, 1.25)
        gx, gy, gz = np.gradient(sm)
        cc = ((P - o) / vs - 0.5).T
        n = -np.stack([ndimage.map_coordinates(g, cc, order=1, mode='nearest') for g in (gx, gy, gz)], 1)
    n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-6
    flat = np.zeros(len(mid), bool)
    for k, mt in mats.items():
        if mt.flat: flat |= mid == k
    if flat.any():
        nf = n[flat]; ax = np.argmax(np.abs(nf), 1)
        nn = np.zeros_like(nf); nn[np.arange(len(nf)), ax] = np.sign(nf[np.arange(len(nf)), ax]); n[flat] = nn
    emis_mask = np.zeros(len(mid), bool)
    for k, mt in mats.items():
        if mt.emissive is not None: emis_mask |= mid == k
    # ---------------- light transport
    off = P + n * vs * 1.3
    lam = n @ L
    if shadows:
        sunv = np.zeros(len(mid), np.float32)
        lit_side = (lam > 0) & ~emis_mask
        for D in SUN_JIT:
            r = np.ones(len(mid), np.float32)
            r[lit_side] = 1 - march(vol, occ, off[lit_side] + D * vs * 0.6, D, 400)
            sunv += r / len(SUN_JIT)
    else:
        sunv = np.ones(len(mid), np.float32)
    skyv = np.zeros(len(mid), np.float32); cnt = np.zeros(len(mid), np.float32)
    ne = ~emis_mask
    for D in SKY:
        w = np.clip(n @ D, 0, 1) + 0.15
        r = np.ones(len(mid), np.float32)
        r[ne] = 1 - march(vol, occ, off[ne], D, skyrange, step=vs * 1.2)
        skyv += r * w; cnt += w
    skyv /= cnt
    # AO: two scales + ground plane
    a1 = ndimage.map_coordinates(ndimage.gaussian_filter(occf, 2.5 / vs * 0.5), (((P + n * 2.0) - o) / vs - 0.5).T, order=1, mode='constant')
    a2 = ndimage.map_coordinates(ndimage.gaussian_filter(occf, 6.0 / vs * 0.5), (((P + n * 5.0) - o) / vs - 0.5).T, order=1, mode='constant')
    zg = np.clip(P[:, 2], 0, None)
    gro = np.exp(-zg / 5.0) * (1 - np.clip(n[:, 2], 0, 1))
    ao = np.clip(1 - ao_strength * (np.clip(a1 * 2.0 - 0.2, 0, 1) * 0.6 + np.clip(a2 * 2.2 - 0.25, 0, 1) * 0.5) - 0.35 * gro, 0.25, 1)
    # cavity (curvature) map
    cav = ndimage.map_coordinates(ndimage.gaussian_filter(occf, 0.9), (((P + n * vs * 1.1) - o) / vs - 0.5).T, order=1, mode='constant')
    hemi = 0.65 + 0.35 * n[:, 2]
    sun = np.clip(lam, 0, 1) * sunv
    bounce = 0.16 * (1 - np.clip(n[:, 2], 0, 1)) * np.exp(-zg / 16.0) * (0.4 + 0.6 * skyv)
    ambient = amb * (0.4 + 0.6 * skyv) * hemi * ao
    val = ambient + 0.62 * sun * (0.8 + 0.2 * ao) + bounce
    sunfrac = np.clip((0.62 * sun) / (val + 1e-3), 0, 1)
    level = val * 6.0 - 0.1
    # surface detail: worn convex edges, dark seams, per-texel grain, large-scale drift, grime toward the ground
    det = np.zeros(len(mid), np.float32)
    det += np.where(cav < 0.10, 0.55, 0) - np.clip(cav - 0.32, 0, 1) * 2.4
    det += micro * ((blob(P, 1.0 * max(vs, 0.5), 3) - 0.5) * 0.25 + (blob(P + 0.5, 2.3, 4) - 0.5) * 0.3)
    drift = (blob(P, 13.0, 5) - 0.5) * 0.10 + (blob(P + 6, 29.0, 6) - 0.5) * 0.08
    grime = np.clip(1 - zg / 9.0, 0, 1) * (1 - np.clip(n[:, 2], 0, 1))
    det -= grime * 0.5
    # ---------------- colour
    px = (U[hi_] * S - umin).astype(int); py = (V[hi_] * S - vmin).astype(int)
    px = np.clip(np.round(U[hi_] * S - umin - 0.5).astype(int), 0, W - 1); py = np.clip(np.round(V[hi_] * S - vmin - 0.5).astype(int), 0, H - 1)
    out = np.zeros((H, W, 4), np.float32); emis = np.zeros((H, W, 4), np.float32)
    matmap = np.zeros((H, W), np.int32); depth = np.full((H, W), -1e9, np.float32); nz = np.zeros((H, W), np.float32)
    matmap[py, px] = mid; depth[py, px] = a; nz[py, px] = n[:, 2]
    colors = np.zeros((len(mid), 3), np.float32)
    for k, mt in mats.items():
        sel = np.nonzero(mid == k)[0]
        if not sel.size: continue
        lv = level[sel].copy()
        swap = None
        if mt.tex is not None:
            r = mt.tex(P[sel], n[sel], mt.p, lv)
            if isinstance(r, tuple): offv, swap = r
            else: offv = r
            lv = lv + offv * mt.p.get('texamp', 1.3)
        if mt.emissive is not None:
            lv = mt.emissive + (lv - level[sel]) + (level[sel] - 3) * 0.2
        else:
            lv = lv + det[sel] * mt.p.get('detail', 1.0)
        lv = lv + BAYER[py[sel] % 4, px[sel] % 4] * dither
        ri = np.clip(np.round(lv), 0, len(mt.ramp) - 1).astype(int)
        col = mt.ramp[ri].copy()
        if swap is not None:
            for sk in np.unique(swap):
                if sk == 0: continue
                msk = swap == sk; m2 = mats[int(sk)]
                col[msk] = m2.ramp[np.clip(np.round(lv[msk]), 0, len(m2.ramp) - 1).astype(int)]
        if mt.emissive is None:
            sf = sunfrac[sel][:, None]; sk_ = (skyv[sel] * hemi[sel])[:, None]
            tint = 1 + sf * np.array([0.06, 0.015, -0.07]) + (1 - sf) * sk_ * np.array([-0.07, -0.01, 0.09])
            tint = tint + (bounce[sel] / 0.16)[:, None] * np.array([0.0, 0.06, -0.05]) * (1 - sf)
            tint = tint + grime[sel][:, None] * np.array([-0.02, -0.05, -0.09])
            tint = tint * (1 + drift[sel])[:, None]
            col = col * tint
        colors[sel] = col
        if mt.night is not None:
            nc = np.array(hx(mt.night), np.float32)
            emis[py[sel], px[sel], :3] = nc; emis[py[sel], px[sel], 3] = 255
    out[py, px, :3] = np.clip(colors, 0, 255); out[py, px, 3] = 255
    hitmap = out[..., 3] > 0
    # rim light on top-left exposed edges
    up = np.zeros_like(hitmap); up[1:] = hitmap[:-1]
    lf = np.zeros_like(hitmap); lf[:, 1:] = hitmap[:, :-1]
    rimm = hitmap & (~up | ~lf) & (nz > -0.2)
    ys, xs = np.nonzero(rimm)
    for yy, xx in zip(ys, xs):
        mt = mats.get(int(matmap[yy, xx]))
        if mt is None or not mt.rim or mt.emissive is not None: continue
        out[yy, xx, :3] = np.clip(out[yy, xx, :3] * 1.18 + 10, 0, 255)
    if outline:
        thr = 5.5 * max(1.0, vs * 2)
        for dy, dx in ((0, 1), (1, 0), (0, -1), (-1, 0)):
            nb = np.roll(np.roll(depth, dy, 0), dx, 1)
            edge = hitmap & (nb - depth > thr) & (nb > -1e8)
            ys, xs = np.nonzero(edge)
            for yy, xx in zip(ys, xs):
                mt = mats.get(int(matmap[yy, xx]))
                if mt is None or mt.emissive is not None: continue
                out[yy, xx, :3] = mt.ramp[0] * 0.85 + mt.outline * 0.15
        o2 = out.copy()
        for dy, dx in ((0, 1), (1, 0), (0, -1), (-1, 0)):
            src_hit = np.roll(np.roll(hitmap, dy, 0), dx, 1)
            src_mat = np.roll(np.roll(matmap, dy, 0), dx, 1)
            cand = (~hitmap) & src_hit & (o2[..., 3] == 0)
            ys, xs = np.nonzero(cand)
            for yy, xx in zip(ys, xs):
                mt = mats.get(int(src_mat[yy, xx]))
                if mt is None: continue
                col = mt.outline if mt.emissive is None else mt.ramp[0]
                o2[yy, xx, :3] = col; o2[yy, xx, 3] = 255
        out = o2
    # ---------------- night local lights (falloff onto nearby surfaces)
    nightlit = np.zeros((H, W, 4), np.float32)
    if nightlights:
        lights = []
        for k, mt in mats.items():
            if mt.night is None: continue
            pts = np.argwhere(vol.m == k)
            if len(pts):
                if len(pts) > 260: pts = pts[np.random.default_rng(1).choice(len(pts), 260, replace=False)]
                lights.append((pts * vs + o + vs / 2, np.array(hx(mt.night), np.float32)))
        if lights:
            acc = np.zeros((len(mid), 3), np.float32)
            R = 26.0
            for (pts, col) in lights:
                wsum = np.zeros(len(mid), np.float32)
                for ch in range(0, len(pts), 64):
                    Lp = pts[ch:ch + 64]
                    d = Lp[None, :, :] - P[:, None, :]
                    dist = np.linalg.norm(d, axis=2) + 1e-3
                    fall = np.clip(1 - dist / R, 0, 1) ** 2
                    ndl = np.clip(np.einsum('nk,nlk->nl', n, d) / dist, 0, 1) * 0.8 + 0.2
                    wsum += (fall * ndl).sum(1)
                acc += np.clip(wsum / 14.0, 0, 1)[:, None] * col
            sel = ~emis_mask
            nightlit[py[sel], px[sel], :3] = np.clip(acc[sel], 0, 255)
            nightlit[py[sel], px[sel], 3] = 255 * (acc[sel].max(1) > 2)
    # ---------------- ground layer: soft shadow + contact AO
    shadow = np.zeros((H, W, 4), np.float32)
    cast = np.zeros((H, W, 4), np.float32)
    if ground:
        gb = base.copy()
        gb[:, 2] = 0.05
        sh = np.zeros(N, np.float32)
        if shadows:
            for D in SUN_JIT:
                sh += march(vol, occ, gb + D * 0.5, D, 400) / len(SUN_JIT)
        gocc = np.zeros(N, np.float32)
        for D in GSKY:
            gocc += march(vol, occ, gb + D * 0.5, D, 34, step=vs * 1.2) / len(GSKY)
        cast = np.zeros((H, W, 4), np.float32); cast[..., 3] = (sh * 255).reshape(H, W)
        alpha = np.clip(np.maximum(sh * 0.46, 0) + gocc * 0.34 * (1 - sh * 0.5), 0, 0.62)
        Vi = np.arange(H)[:, None].repeat(W, 1).ravel(); Ui = np.tile(np.arange(W), H)
        alpha = np.floor(alpha * 10 + BAYER[Vi % 4, Ui % 4] * 0.9 + 0.5) / 10
        shadow[..., 0] = 26; shadow[..., 1] = 20; shadow[..., 2] = 56; shadow[..., 3] = np.clip(alpha, 0, 0.62).reshape(H, W) * 255
    return dict(color=out.astype(np.uint8), shadow=shadow.astype(np.uint8), emis=emis.astype(np.uint8),
                nightlit=nightlit.astype(np.uint8), cast=cast.astype(np.uint8), anchor=(-umin, -vmin), depth=depth, matmap=matmap)

def trim(layers, keys=('color', 'shadow', 'emis', 'nightlit', 'cast')):
    a = np.zeros(layers['color'].shape[:2], bool)
    for k in keys: a |= layers[k][..., 3] > 0
    ys, xs = np.nonzero(a)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    for k in keys: layers[k] = layers[k][y0:y1, x0:x1]
    ax, ay = layers['anchor']; layers['anchor'] = (ax - x0, ay - y0)
    return layers
