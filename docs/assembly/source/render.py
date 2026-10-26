"""Hidden-line drawing of triangle meshes in one parallel projection.

Pipeline per view (all parts already moved by their view offset):
  1. project every triangle with the same orthographic camera;
  2. cull back faces and rasterise a supersampled label/depth buffer (fills, anchor checks);
  3. pick feature edges per mesh: silhouettes, creases (> CREASE_DEG) and tangent edges
     (where a real flat face runs into a faceted fillet/cylinder);
  4. clip every feature edge analytically against every front-facing triangle in front of
     it (exact segment/triangle/plane intervals, no depth-buffer sampling), so visible
     linework is not nibbled at silhouettes;
  5. trace each label region of the buffer into closed even-odd polygons (holes kept) for
     the flat tint fills; the fills sit under the linework.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

CREASE_DEG = 30.0       # facet steps on the CAD's fillets and cylinders are <= 18 deg
REAL_FACE_WIDTH = 0.8   # mm; 2*area/perimeter of a planar region; below this it is a facet strip
DEPTH_EPS = 0.01        # mm along the view axis; coincident surfaces do not hide each other
INSIDE_EPS = 0.02       # px; at real face boundaries occluders shrink, so edges running along them stay
SEAM_EPS = -0.05        # px; across internal seams of a flat face occluders grow, so hidden edges cannot
                        # leak through the triangulation of the face in front
MIN_SEG = 0.35          # px; shorter visible pieces are numerical slivers
MIN_POLYLINE = 2.5      # px; isolated specks (e.g. the 0.2 mm joint seen edge-on) are dropped


@dataclass
class Camera:
    azimuth: float   # degrees, rotation of the eye from the front (-Y) toward +X
    elevation: float  # degrees above the horizon

    def basis(self):
        az, el = math.radians(self.azimuth), math.radians(self.elevation)
        view = np.array([math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el)])
        right = np.cross([0.0, 0.0, 1.0], view)
        right /= np.linalg.norm(right)
        up = np.cross(view, right)
        return view, right, up

    def project(self, pts):
        """Model mm -> (u, v, depth): u right, v down (SVG), depth larger = nearer the eye."""
        view, right, up = self.basis()
        return np.stack([pts @ right, -(pts @ up), pts @ view], axis=-1)


@dataclass
class Mesh:
    """View-independent topology of one region-tinted part mesh."""
    name: str
    tris: np.ndarray                 # (n,3,3) model mm, untransformed
    tint: np.ndarray                 # (n,) tint index per triangle (into the part's tint list)
    verts: np.ndarray = field(init=False)
    faces: np.ndarray = field(init=False)
    normals: np.ndarray = field(init=False)
    edges: np.ndarray = field(init=False)       # (m,2) vertex ids
    edge_faces: np.ndarray = field(init=False)  # (m,2) face ids, -1 for boundary
    feature: np.ndarray = field(init=False)     # (m,) 0 none, 2 crease, 3 tangent

    def __post_init__(self):
        self.verts, inv = np.unique(self.tris.reshape(-1, 3), axis=0, return_inverse=True)
        self.faces = inv.reshape(-1, 3)
        n = np.cross(self.tris[:, 1] - self.tris[:, 0], self.tris[:, 2] - self.tris[:, 0])
        area2 = np.linalg.norm(n, axis=1)
        self.normals = n / np.maximum(area2, 1e-15)[:, None]
        self.area = area2 / 2
        e = np.concatenate([self.faces[:, [0, 1]], self.faces[:, [1, 2]], self.faces[:, [2, 0]]])
        fid = np.tile(np.arange(len(self.faces)), 3)
        key = np.sort(e, axis=1)
        uniq, inv = np.unique(key, axis=0, return_inverse=True)
        order = np.argsort(inv, kind="stable")
        counts = np.bincount(inv, minlength=len(uniq))
        starts = np.concatenate([[0], np.cumsum(counts)[:-1]])
        ef = np.full((len(uniq), 2), -1, dtype=np.int64)
        ef[:, 0] = fid[order][starts]
        two = counts >= 2
        ef[two, 1] = fid[order][starts[two] + 1]
        self.edges, self.edge_faces = uniq, ef
        self.nonmanifold = int((counts > 2).sum())
        self._classify(counts)
        n = len(self.faces)
        # per triangle side k (vertex k -> k+1): is it a seam inside one flat face?
        self.seam = np.stack([self.coplanar[inv[k * n:(k + 1) * n]] for k in range(3)], axis=1)

    def _classify(self, counts):
        f0, f1 = self.edge_faces[:, 0], self.edge_faces[:, 1]
        has2 = f1 >= 0
        cosang = np.ones(len(self.edges))
        cosang[has2] = np.einsum("ij,ij->i", self.normals[f0[has2]], self.normals[f1[has2]])
        # planar regions: union-find over edges whose faces are coplanar
        parent = np.arange(len(self.faces))

        def find(i):
            root = i
            while parent[root] != root:
                root = parent[root]
            while parent[i] != root:
                parent[i], i = root, parent[i]
            return root

        coplanar = has2 & (cosang > 1 - 1e-9)
        self.coplanar = coplanar
        for a, b in zip(f0[coplanar], f1[coplanar]):
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[ra] = rb
        region = np.array([find(i) for i in range(len(self.faces))])
        elen = np.linalg.norm(self.verts[self.edges[:, 0]] - self.verts[self.edges[:, 1]], axis=1)
        border = ~coplanar
        perim = np.zeros(len(self.faces))
        np.add.at(perim, region[f0[border]], elen[border])
        np.add.at(perim, region[f1[border & has2]], elen[border & has2])
        area = np.zeros(len(self.faces))
        np.add.at(area, region, self.area)
        width = 2 * area / np.maximum(perim, 1e-9)
        real = width[region] > REAL_FACE_WIDTH
        self.region, self.real_face = region, real
        feat = np.zeros(len(self.edges), dtype=np.int8)
        crease = has2 & (cosang < math.cos(math.radians(CREASE_DEG)))
        feat[crease] = 2
        soft = has2 & ~crease & ~coplanar
        r0, r1 = real[f0], np.where(has2, real[np.maximum(f1, 0)], False)
        feat[soft & (r0 != r1)] = 3                 # flat face meets a fillet / cylinder facet
        feat[soft & r0 & r1] = 2                     # two genuine faces at a shallow angle
        feat[~has2] = 2                              # open boundary (should not occur)
        tint_change = has2 & (self.tint[f0] != self.tint[np.maximum(f1, 0)])
        feat[tint_change & (feat == 0)] = 2
        self.feature = feat


@dataclass
class Placed:
    """A mesh placed in a view: model-space offset applied."""
    mesh: Mesh
    part: int            # index into the view's part list
    offset: np.ndarray   # (3,) mm


@dataclass
class Frame:
    """Screen mapping for a view: model (u,v) -> output px."""
    scale: float
    ox: float
    oy: float

    def apply(self, uvd):
        out = uvd.copy()
        out[..., 0] = uvd[..., 0] * self.scale + self.ox
        out[..., 1] = uvd[..., 1] * self.scale + self.oy
        return out


def projected_bounds(cam: Camera, placed: list[Placed]):
    pts = np.concatenate([cam.project(p.mesh.verts + p.offset) for p in placed])
    return pts[:, 0].min(), pts[:, 1].min(), pts[:, 0].max(), pts[:, 1].max()


def fit_frame(cam, placed, box):
    """Frame that fits the drawing into box=(x0,y0,x1,y1) px, centred."""
    u0, v0, u1, v1 = projected_bounds(cam, placed)
    x0, y0, x1, y1 = box
    s = min((x1 - x0) / (u1 - u0), (y1 - y0) / (v1 - v0))
    return Frame(s, (x0 + x1) / 2 - s * (u0 + u1) / 2, (y0 + y1) / 2 - s * (v0 + v1) / 2)


# --------------------------------------------------------------------------------------
# rasterisation


def rasterize(screen_tris, labels, width, height, ss):
    """Depth + label buffer. screen_tris (n,3,3) px with depth; labels (n,) int >= 1."""
    W, H = int(math.ceil(width * ss)), int(math.ceil(height * ss))
    depth = np.full((H, W), -np.inf)
    lab = np.zeros((H, W), dtype=np.int32)
    T = screen_tris.copy()
    T[..., :2] *= ss
    for tri, l in zip(T, labels):
        (ax, ay, az), (bx, by, bz), (cx, cy, cz) = tri
        x0 = max(0, int(math.floor(min(ax, bx, cx) - 0.5)))
        x1 = min(W - 1, int(math.ceil(max(ax, bx, cx) - 0.5)))
        y0 = max(0, int(math.floor(min(ay, by, cy) - 0.5)))
        y1 = min(H - 1, int(math.ceil(max(ay, by, cy) - 0.5)))
        if x1 < x0 or y1 < y0:
            continue
        den = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        if abs(den) < 1e-12:
            continue
        xs = np.arange(x0, x1 + 1) + 0.5
        ys = (np.arange(y0, y1 + 1) + 0.5)[:, None]
        w0 = ((by - cy) * (xs - cx) + (cx - bx) * (ys - cy)) / den
        w1 = ((cy - ay) * (xs - cx) + (ax - cx) * (ys - cy)) / den
        w2 = 1 - w0 - w1
        inside = (w0 >= -1e-9) & (w1 >= -1e-9) & (w2 >= -1e-9)
        if not inside.any():
            continue
        z = w0 * az + w1 * bz + w2 * cz
        sub = depth[y0:y1 + 1, x0:x1 + 1]
        win = inside & (z > sub)
        sub[win] = z[win]
        lab[y0:y1 + 1, x0:x1 + 1][win] = l
    return depth, lab


# --------------------------------------------------------------------------------------
# analytic edge visibility


class Occluders:
    def __init__(self, tris, seam, cell=24.0):
        """tris (n,3,3) screen px + depth, front-facing only; seam (n,3) bool per triangle side."""
        self.t = tris
        self.side_eps = np.where(seam, SEAM_EPS, INSIDE_EPS)
        p = tris[..., :2]
        self.lo, self.hi = p.min(1), p.max(1)
        a, b, c = tris[:, 0], tris[:, 1], tris[:, 2]
        # depth plane z = z0 + gx*(x-ax) + gy*(y-ay)
        e1, e2 = b - a, c - a
        det = e1[:, 0] * e2[:, 1] - e1[:, 1] * e2[:, 0]
        ok = np.abs(det) > 1e-12
        det = np.where(ok, det, 1.0)
        self.gx = (e1[:, 2] * e2[:, 1] - e2[:, 2] * e1[:, 1]) / det
        self.gy = (e2[:, 2] * e1[:, 0] - e1[:, 2] * e2[:, 0]) / det
        self.sign = np.sign(det)
        self.ok = ok
        self.cell = cell
        gx0 = np.floor(self.lo / cell).astype(int)
        gx1 = np.floor(self.hi / cell).astype(int)
        self.grid: dict = {}
        for i in np.flatnonzero(ok):
            for gx in range(gx0[i, 0], gx1[i, 0] + 1):
                for gy in range(gx0[i, 1], gx1[i, 1] + 1):
                    self.grid.setdefault((gx, gy), []).append(i)
        self.grid = {k: np.array(v) for k, v in self.grid.items()}

    def candidates(self, A, B):
        lo, hi = np.minimum(A[:2], B[:2]), np.maximum(A[:2], B[:2])
        c0 = np.floor(lo / self.cell).astype(int)
        c1 = np.floor(hi / self.cell).astype(int)
        # walk the cells along the segment only (not the whole bbox)
        n = int(max(c1[0] - c0[0], c1[1] - c0[1])) * 2 + 2
        ts = np.linspace(0, 1, n)
        pts = A[None, :2] + ts[:, None] * (B[:2] - A[:2])[None]
        cells = set()
        for q in np.floor(pts / self.cell).astype(int):
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    cells.add((q[0] + dx, q[1] + dy))
        arrs = [self.grid[c] for c in cells if c in self.grid]
        if not arrs:
            return np.empty(0, dtype=int)
        ids = np.unique(np.concatenate(arrs))
        m = (self.lo[ids, 0] <= hi[0]) & (self.hi[ids, 0] >= lo[0]) & (self.lo[ids, 1] <= hi[1]) & (self.hi[ids, 1] >= lo[1])
        return ids[m]

    def visible_intervals(self, A, B):
        """Visible [t0,t1] pieces of segment A->B (each (x,y,depth))."""
        ids = self.candidates(A, B)
        if len(ids) == 0:
            return [(0.0, 1.0)]
        T = self.t[ids]
        d = B - A
        lo = np.zeros(len(ids))
        hi = np.ones(len(ids))
        for k in range(3):
            P, Q = T[:, k, :2], T[:, (k + 1) % 3, :2]
            ex, ey = Q[:, 0] - P[:, 0], Q[:, 1] - P[:, 1]
            elen = np.hypot(ex, ey)
            s = self.sign[ids]
            a = s * (ex * (A[1] - P[:, 1]) - ey * (A[0] - P[:, 0]))
            b = s * (ex * d[1] - ey * d[0])
            delta = self.side_eps[ids, k] * elen
            lo, hi = _halfplane(lo, hi, a - delta, b)
        # in front: zt(t) - zs(t) > DEPTH_EPS
        a0 = T[:, 0]
        zt0 = a0[:, 2] + self.gx[ids] * (A[0] - a0[:, 0]) + self.gy[ids] * (A[1] - a0[:, 1])
        dzt = self.gx[ids] * d[0] + self.gy[ids] * d[1]
        lo, hi = _halfplane(lo, hi, zt0 - A[2] - DEPTH_EPS, dzt - d[2])
        occ = hi > lo + 1e-9
        if not occ.any():
            return [(0.0, 1.0)]
        iv = sorted(zip(lo[occ].tolist(), hi[occ].tolist()))
        vis, cur = [], 0.0
        for s0, s1 in iv:
            if s0 > cur:
                vis.append((cur, s0))
            cur = max(cur, s1)
            if cur >= 1.0:
                break
        if cur < 1.0:
            vis.append((cur, 1.0))
        return vis


def _halfplane(lo, hi, a, b):
    """Intersect [lo,hi] with {t : a + b t >= 0}."""
    with np.errstate(divide="ignore", invalid="ignore"):
        root = -a / b
    pos, neg, zero = b > 1e-15, b < -1e-15, np.abs(b) <= 1e-15
    lo = np.where(pos, np.maximum(lo, root), lo)
    hi = np.where(neg, np.minimum(hi, root), hi)
    hi = np.where(zero & (a < 0), -1.0, hi)
    return lo, hi


# --------------------------------------------------------------------------------------
# region tracing


def trace_mask(mask):
    """Closed boundary loops (pixel-corner coordinates) of a boolean mask; even-odd fill."""
    m = np.pad(mask, 1)
    H, W = m.shape
    # directed cracks with the inside on the right (image coords, y down)
    nxt = {}
    ys, xs = np.nonzero(m[1:, :] & ~m[:-1, :])        # top edges of inside pixels: going +x
    for y, x in zip(ys + 1, xs):
        nxt.setdefault((x, y), []).append((x + 1, y))
    ys, xs = np.nonzero(m[:-1, :] & ~m[1:, :])        # bottom edges: going -x
    for y, x in zip(ys, xs):
        nxt.setdefault((x + 1, y + 1), []).append((x, y + 1))
    ys, xs = np.nonzero(m[:, :-1] & ~m[:, 1:])        # right edges: going +y
    for y, x in zip(ys, xs):
        nxt.setdefault((x + 1, y), []).append((x + 1, y + 1))
    ys, xs = np.nonzero(m[:, 1:] & ~m[:, :-1])        # left edges: going -y
    for y, x in zip(ys, xs + 1):
        nxt.setdefault((x, y + 1), []).append((x, y))
    loops = []
    while nxt:
        start = next(iter(nxt))
        loop = [start]
        prev_dir = None
        cur = start
        while True:
            outs = nxt.get(cur)
            if not outs:
                break
            if len(outs) == 1 or prev_dir is None:
                j = 0
            else:  # saddle: turn right (keeps diagonal pixels separate)
                def turn(o):
                    dx, dy = o[0] - cur[0], o[1] - cur[1]
                    return prev_dir[0] * dy - prev_dir[1] * dx
                j = max(range(len(outs)), key=lambda i: turn(outs[i]))
            nx = outs.pop(j)
            if not outs:
                del nxt[cur]
            prev_dir = (nx[0] - cur[0], nx[1] - cur[1])
            cur = nx
            if cur == start:
                break
            loop.append(cur)
        if len(loop) >= 4:
            loops.append(np.array(loop, dtype=float) - 1.0)
    return loops


def simplify_loop(pts, tol):
    """Edge midpoints (removes the staircase) then Douglas-Peucker on a closed loop."""
    mid = (pts + np.roll(pts, -1, axis=0)) / 2
    n = len(mid)
    if n < 8:
        return mid
    d = np.linalg.norm(mid - mid[0], axis=1)
    k = int(np.argmax(d))
    a = _dp(mid[: k + 1], tol)
    b = _dp(np.concatenate([mid[k:], mid[:1]]), tol)
    return np.concatenate([a[:-1], b[:-1]])


def _dp(pts, tol):
    keep = np.zeros(len(pts), dtype=bool)
    keep[0] = keep[-1] = True
    stack = [(0, len(pts) - 1)]
    while stack:
        i, j = stack.pop()
        if j <= i + 1:
            continue
        p, q = pts[i], pts[j]
        seg = q - p
        L = np.hypot(*seg)
        r = pts[i + 1:j] - p
        if L < 1e-12:
            dist = np.hypot(r[:, 0], r[:, 1])
        else:
            dist = np.abs(seg[0] * r[:, 1] - seg[1] * r[:, 0]) / L
        k = int(np.argmax(dist))
        if dist[k] > tol:
            keep[i + 1 + k] = True
            stack.append((i, i + 1 + k))
            stack.append((i + 1 + k, j))
    return pts[keep]


def loop_area(p):
    x, y = p[:, 0], p[:, 1]
    return 0.5 * float(np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y))


# --------------------------------------------------------------------------------------
# a whole view


@dataclass
class Drawing:
    fills: list        # [(part, tint, depth_rank, [loops px])]
    lines: list        # [(part, kind, [polyline px])] kind: 1 silhouette, 2 crease, 3 tangent
    depth: np.ndarray
    labels: np.ndarray
    label_info: dict   # label -> (part, tint)
    ss: int
    frame: Frame
    region: tuple
    stats: dict


def draw_view(cam: Camera, placed: list[Placed], frame: Frame, region, ss=3):
    """region = (x0, y0, x1, y1) px of the output canvas that the raster buffer covers."""
    rx0, ry0, rx1, ry1 = region
    view, _, _ = cam.basis()
    all_tris, all_lab, all_seam, label_info = [], [], [], {}
    per_part_screen = []
    for p in placed:
        world = p.mesh.tris + p.offset
        facing = p.mesh.normals @ view
        scr = frame.apply(cam.project(world))
        per_part_screen.append((scr, facing))
        front = facing > 1e-9
        labs = np.zeros(len(world), dtype=np.int32)
        for t in np.unique(p.mesh.tint):
            lid = len(label_info) + 1
            label_info[lid] = (p.part, int(t))
            labs[p.mesh.tint == t] = lid
        all_tris.append(scr[front])
        all_lab.append(labs[front])
        all_seam.append(p.mesh.seam[front])
    T = np.concatenate(all_tris)
    L = np.concatenate(all_lab)
    Tr = T.copy()
    Tr[..., 0] -= rx0
    Tr[..., 1] -= ry0
    depth, labels = rasterize(Tr, L, rx1 - rx0, ry1 - ry0, ss)
    occ = Occluders(T, np.concatenate(all_seam))

    lines = []
    seg_count = 0
    dropped = 0
    for p, (scr, facing) in zip(placed, per_part_screen):
        m = p.mesh
        vs = frame.apply(cam.project(m.verts + p.offset))
        f0, f1 = m.edge_faces[:, 0], m.edge_faces[:, 1]
        fr0 = facing[f0] > 1e-9
        fr1 = np.where(f1 >= 0, facing[np.maximum(f1, 0)] > 1e-9, False)
        sil = (fr0 != fr1)
        kind = np.where(sil, 1, np.where(fr0 | fr1, m.feature, 0))
        segs = {1: [], 2: [], 3: []}
        for ei in np.flatnonzero(kind > 0):
            A, B = vs[m.edges[ei, 0]], vs[m.edges[ei, 1]]
            if np.hypot(*(B[:2] - A[:2])) < 1e-6:
                continue
            for t0, t1 in occ.visible_intervals(A, B):
                P0, P1 = A + t0 * (B - A), A + t1 * (B - A)
                if np.hypot(*(P1[:2] - P0[:2])) >= MIN_SEG:
                    segs[int(kind[ei])].append((P0[:2], P1[:2]))
                    seg_count += 1
        for k, ss_ in segs.items():
            for pl in chain(ss_):
                if np.sum(np.hypot(*np.diff(pl, axis=0).T)) >= MIN_POLYLINE:
                    lines.append((p.part, k, pl))
                else:
                    dropped += 1

    fills = []
    tol = 0.45  # subpixels
    for lid, (part, tint) in label_info.items():
        mask = labels == lid
        if mask.sum() < 3:
            continue
        loops = []
        for lp in trace_mask(mask):
            sp = simplify_loop(lp, tol)
            if len(sp) >= 3 and abs(loop_area(sp)) >= 2.0:
                loops.append(sp / ss + [rx0, ry0])
        if loops:
            fills.append((part, tint, float(np.median(depth[mask])), loops))
    fills.sort(key=lambda f: f[2])
    stats = {"triangles": int(sum(len(p.mesh.tris) for p in placed)), "front_triangles": int(len(T)),
             "visible_segments": seg_count, "polylines": len(lines), "isolated_specks_dropped": dropped,
             "fill_regions": len(fills), "fill_loops": sum(len(f[3]) for f in fills)}
    return Drawing(fills, lines, depth, labels, label_info, ss, frame, region, stats)


def chain(segs, tol=1e-4):
    """Join segments sharing endpoints into polylines."""
    if not segs:
        return []
    key = lambda p: (round(p[0] / tol), round(p[1] / tol))  # noqa: E731
    adj = {}
    for i, (a, b) in enumerate(segs):
        adj.setdefault(key(a), []).append((i, 0))
        adj.setdefault(key(b), []).append((i, 1))
    used = np.zeros(len(segs), dtype=bool)
    out = []
    for i in range(len(segs)):
        if used[i]:
            continue
        used[i] = True
        a, b = segs[i]
        line = [a, b]
        for direction in (1, 0):
            while True:
                end = line[-1] if direction else line[0]
                nxt = None
                for j, side in adj.get(key(end), []):
                    if not used[j]:
                        nxt = (j, side)
                        break
                if nxt is None:
                    break
                j, side = nxt
                used[j] = True
                other = segs[j][1 - side]
                if direction:
                    line.append(other)
                else:
                    line.insert(0, other)
        out.append(np.array(line))
    return out
