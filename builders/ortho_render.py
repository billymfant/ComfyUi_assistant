"""Headless orthographic 6-view renderer for a mesh (.glb/.obj/.ply).

Renders geometrically-correct front/back/left/right/top/bottom views using a small
self-contained numpy orthographic z-buffer rasterizer. No GPU / display / GL context
needed (open3d/pyrender/VTK all require an unavailable headless GL context on this
Windows box), so it runs anywhere the embedded python does.

Proper per-pixel z-buffering (no painter's-algorithm see-through artifacts) + flat
clay shading gives clean modeling-reference turnarounds. Trellis meshes can be millions
of faces; we quadric-decimate first (a proportions reference needs far fewer).

Usage:
    python ortho_render.py MESH.glb OUT_DIR [--size 768] [--faces 60000]
"""
import sys, os, argparse
import numpy as np

# Per view: which world axis projects to (horizontal, vertical, depth) + sign flips.
# Tuple = (h_axis, h_sign, v_axis, v_sign, d_axis, d_sign); camera looks along -depth.
# Calibrated for Trellis2 export (reorient "90 degrees").
VIEWS = {
    "front":  (0,  1, 1, 1, 2,  1),
    "back":   (0, -1, 1, 1, 2, -1),
    "right":  (2, -1, 1, 1, 0,  1),
    "left":   (2,  1, 1, 1, 0, -1),
    "top":    (0,  1, 2, -1, 1,  1),
    "bottom": (0,  1, 2,  1, 1, -1),
}


def load_mesh(path, target_faces=60000):
    import trimesh
    m = trimesh.load(path, force="mesh")
    if m.is_empty or len(m.faces) == 0:
        raise ValueError(f"no geometry in {path}")
    try:
        import open3d as o3d
        om = o3d.geometry.TriangleMesh(
            o3d.utility.Vector3dVector(m.vertices),
            o3d.utility.Vector3iVector(m.faces))
        if len(m.faces) > target_faces:
            om = om.simplify_quadric_decimation(int(target_faces))
        # drop disconnected floaters (gray-slab artifacts): keep only the largest cluster
        om.remove_degenerate_triangles(); om.remove_unreferenced_vertices()
        idx, counts, _ = om.cluster_connected_triangles()
        idx = np.asarray(idx); counts = np.asarray(counts)
        if counts.size > 1:
            keep = counts.argmax()
            om.remove_triangles_by_mask(idx != keep)
            om.remove_unreferenced_vertices()
        m = trimesh.Trimesh(np.asarray(om.vertices), np.asarray(om.triangles), process=False)
    except Exception:
        pass
    v = m.vertices.astype(np.float64)
    v -= (v.min(0) + v.max(0)) / 2.0
    v /= np.max(v.max(0) - v.min(0))
    f = m.faces.astype(np.int64)
    # cull any remaining long sliver triangles (streaks): drop any edge > 8% of model
    tri = v[f]
    e = np.stack([np.linalg.norm(tri[:, 1] - tri[:, 0], axis=1),
                  np.linalg.norm(tri[:, 2] - tri[:, 1], axis=1),
                  np.linalg.norm(tri[:, 0] - tri[:, 2], axis=1)], 1)
    f = f[e.max(1) < 0.08]
    return v, f


def rasterize(V, F, spec, size, bg=250, pad=0.08):
    """Orthographic z-buffer rasterizer (flat clay shading) -> (size,size,3) uint8."""
    ha, hs, va, vs, da, ds = spec
    z = V[:, da] * ds  # camera looks along -z; larger z = closer
    s = size * (1 - 2 * pad)
    px = (V[:, ha] * hs + 0.5) * s + size * pad
    py = (0.5 - V[:, va] * vs) * s + size * pad
    P = np.stack([px, py], 1)

    # flat face-normal shade vs camera direction (smooth, silhouette-readable clay)
    tri = V[F]
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    nl = np.linalg.norm(n, axis=1, keepdims=True); nl[nl == 0] = 1
    n = n / nl
    cam = np.zeros(3); cam[da] = ds
    shade = (0.35 + 0.6 * np.clip(np.abs(n @ cam), 0, 1)) * 255

    img = np.full((size, size, 3), bg, np.uint8)
    zbuf = np.full((size, size), -1e9)
    order = np.argsort(z[F].mean(1))          # far-to-near
    for fi in order:
        i0, i1, i2 = F[fi]
        a, b, c = P[i0], P[i1], P[i2]
        minx = max(int(np.floor(min(a[0], b[0], c[0]))), 0)
        maxx = min(int(np.ceil(max(a[0], b[0], c[0]))), size - 1)
        miny = max(int(np.floor(min(a[1], b[1], c[1]))), 0)
        maxy = min(int(np.ceil(max(a[1], b[1], c[1]))), size - 1)
        if minx > maxx or miny > maxy:
            continue
        xs, ys = np.meshgrid(np.arange(minx, maxx + 1), np.arange(miny, maxy + 1))
        xs = xs.ravel() + 0.5; ys = ys.ravel() + 0.5
        d = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
        if abs(d) < 1e-9:
            continue
        w0 = ((b[1] - c[1]) * (xs - c[0]) + (c[0] - b[0]) * (ys - c[1])) / d
        w1 = ((c[1] - a[1]) * (xs - c[0]) + (a[0] - c[0]) * (ys - c[1])) / d
        w2 = 1 - w0 - w1
        inside = (w0 >= 0) & (w1 >= 0) & (w2 >= 0)
        if not inside.any():
            continue
        gx = xs[inside].astype(int); gy = ys[inside].astype(int)
        depth = w0[inside] * z[i0] + w1[inside] * z[i1] + w2[inside] * z[i2]
        vis = depth > zbuf[gy, gx]
        if not vis.any():
            continue
        gx, gy = gx[vis], gy[vis]
        zbuf[gy, gx] = depth[vis]
        img[gy, gx] = shade[fi]
    return img


def render_six(mesh_path, out_dir, size=768, target_faces=60000):
    os.makedirs(out_dir, exist_ok=True)
    from PIL import Image
    V, F = load_mesh(mesh_path, target_faces)
    out = {}
    for name, spec in VIEWS.items():
        img = rasterize(V, F, spec, size)
        p = os.path.join(out_dir, f"{name}.png")
        Image.fromarray(img).save(p)
        out[name] = p
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mesh"); ap.add_argument("out_dir")
    ap.add_argument("--size", type=int, default=768)
    ap.add_argument("--faces", type=int, default=60000)
    a = ap.parse_args()
    for k, v in render_six(a.mesh, a.out_dir, a.size, a.faces).items():
        print(f"{k:7s} -> {v}")
