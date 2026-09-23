#!/usr/bin/env python3
"""Build left_hand.stl / right_hand.stl print plates from the glove URDF.

Takes every printed part the URDF uses (meshes/printed/, one copy per instance),
lays each on the face with the most bed contact, and packs them onto one plate.
The URDF is a left hand; the right plate is its mirror image.

    python make_plates.py
    python make_plates.py --gap 4

Needs numpy and scipy.
"""

from __future__ import annotations

import argparse
import os
import struct
import sys

import numpy as np
from scipy.spatial import ConvexHull

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "visualizer"))
from view_glove import DEFAULT_URDF, URDF  # noqa: E402

STL_DT = np.dtype([("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")])
ROT90 = np.array([[0, -1, 0], [1, 0, 0], [0, 0, 1.0]])


def load_stl(path: str) -> np.ndarray:
    b = open(path, "rb").read()
    if b[:5] == b"solid" and b"facet" in b[:400]:
        v = [l.split()[1:4] for l in b.decode().splitlines() if l.strip().startswith("vertex")]
        return np.array(v, dtype=float).reshape(-1, 3, 3)
    n = struct.unpack("<I", b[80:84])[0]
    return np.frombuffer(b, STL_DT, n, 84)["v"].astype(float)


def save_stl(path: str, tris: np.ndarray, name: bytes):
    n = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-15)
    a = np.zeros(len(tris), STL_DT)
    a["n"], a["v"] = n, tris
    with open(path, "wb") as f:
        f.write(name.ljust(80, b"\0") + struct.pack("<I", len(tris)) + a.tobytes())


def rot_to(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Rotation matrix taking unit vector a onto unit vector b."""
    v, c = np.cross(a, b), a @ b
    if np.linalg.norm(v) < 1e-9:
        if c > 0:
            return np.eye(3)
        p = np.cross(a, np.eye(3)[np.argmin(abs(a))])
        p /= np.linalg.norm(p)
        return 2 * np.outer(p, p) - np.eye(3)
    K = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    return np.eye(3) + K + K @ K / (1 + c)


def to_origin(t: np.ndarray) -> np.ndarray:
    return t - t.reshape(-1, 3).min(0)


def lay_flat(tris: np.ndarray) -> np.ndarray:
    """Put the largest face lying on the convex hull down on z=0, long side along y."""
    pts = tris.reshape(-1, 3)
    n = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    area = np.linalg.norm(n, axis=1) / 2
    n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-15)
    best, best_area = None, -1.0
    for c in np.unique(np.round(ConvexHull(pts).equations[:, :3], 3), axis=0):
        c /= np.linalg.norm(c)
        on_plane = (n @ c > 0.999) & (np.abs(tris[:, 0] @ c - (pts @ c).max()) < 0.02)
        a = area[on_plane].sum()
        if a > best_area * 1.02 or (a > best_area * 0.98 and np.ptp(pts @ c) < np.ptp(pts @ best)):
            best, best_area = c, a
    t = tris @ rot_to(best, np.array([0, 0, -1.0])).T

    hull = t.reshape(-1, 3)[:, :2]
    hull = hull[ConvexHull(hull).vertices]
    best_ang, best_rect = 0.0, np.inf
    for e in np.roll(hull, -1, 0) - hull:
        ang = -np.arctan2(e[1], e[0])
        cs, sn = np.cos(ang), np.sin(ang)
        rect = np.ptp(hull @ np.array([[cs, sn], [-sn, cs]]), 0).prod()
        if rect < best_rect - 1e-9:
            best_ang, best_rect = ang, rect
    cs, sn = np.cos(best_ang), np.sin(best_ang)
    t = t @ np.array([[cs, -sn, 0], [sn, cs, 0], [0, 0, 1]]).T
    ext = np.ptp(t.reshape(-1, 3), 0)
    return to_origin(t @ ROT90.T if ext[0] > ext[1] else t)


def pack(parts: list[tuple[np.ndarray, np.ndarray]], width: float, gap: float, cell: float = 0.5):
    """Bottom-left fill of padded bounding boxes on a grid; parts come as (upright, turned 90)."""
    nx = int(np.ceil(width / cell))
    occ = np.zeros((2000, nx), bool)
    placed = []
    for variants in sorted(parts, key=lambda v: -np.prod(v[0].reshape(-1, 3).max(0)[:2])):
        best = None
        for t in variants:
            w, h = t.reshape(-1, 3).max(0)[:2]
            gw, gh = int(np.ceil((w + gap) / cell)), int(np.ceil((h + gap) / cell))
            if gw > nx:
                continue
            cs = np.pad(occ, ((1, 0), (1, 0))).cumsum(0).cumsum(1)
            hits = cs[gh:, gw:] - cs[:-gh, gw:] - cs[gh:, :-gw] + cs[:-gh, :-gw]
            ys, xs = np.nonzero(hits == 0)
            if not len(ys):
                continue
            k = np.lexsort((xs, ys))[0]
            cand = (ys[k] + gh, xs[k], ys[k], t, gw, gh)
            if best is None or cand[:2] < best[:2]:
                best = cand
        if best is None:
            return None
        _, gx, gy, t, gw, gh = best
        occ[gy : gy + gh, gx : gx + gw] = True
        placed.append(t + [gx * cell, gy * cell, 0])
    return np.concatenate(placed)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("urdf", nargs="?", default=DEFAULT_URDF)
    p.add_argument("--gap", type=float, default=3.0, help="min spacing between parts, mm")
    p.add_argument("--out", default=HERE, help="output directory")
    args = p.parse_args()

    u = URDF(args.urdf)
    meshes = [v.mesh for vl in u.visuals.values() for v in vl if f"{os.sep}printed{os.sep}" in v.mesh]
    flat = {m: lay_flat(load_stl(m) * 1000.0) for m in set(meshes)}  # URDF meshes are in metres
    parts = [(flat[m], to_origin(flat[m] @ ROT90.T)) for m in sorted(meshes)]

    plates = (pack(parts, w, args.gap) for w in np.arange(150, 260, 2.0))
    plate = min((t for t in plates if t is not None), key=lambda t: (np.ptp(t[:, :, :2].reshape(-1, 2), 0).max(),
                                                                     np.ptp(t[:, :, :2].reshape(-1, 2), 0).prod()))
    lo, hi = plate.reshape(-1, 3).min(0), plate.reshape(-1, 3).max(0)
    plate -= [(lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, 0]

    save_stl(os.path.join(args.out, "left_hand.stl"), plate, b"homunculus left hand")
    save_stl(os.path.join(args.out, "right_hand.stl"), (plate * [-1, 1, 1])[:, [0, 2, 1]], b"homunculus right hand")
    w, h = np.ptp(plate[:, :, :2].reshape(-1, 2), 0)
    print(f"{len(meshes)} parts per hand, plate {w:.1f} x {h:.1f} x {hi[2] - lo[2]:.1f} mm -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
