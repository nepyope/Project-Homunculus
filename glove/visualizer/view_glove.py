#!/usr/bin/env python3
"""Interactive viewer for the glove URDF.

- 3D render in meshcat (opens in your browser)
- pygame window with one slider per movable joint, grouped per finger

    python view_glove.py                    # ../model/glove_non_diametric.urdf
    python view_glove.py path/to.urdf       # any onshape-to-robot export
    python view_glove.py --self-test        # no GUI: parse + FK + mesh check

Drag a slider with the mouse. Keys: R = reset to zero, F = fist, Q/Esc = quit.

Meshes are looked up from the `package://` path relative to the URDF, then in
./meshes and ./assets alongside it. Needs numpy, scipy, meshcat, pygame.
"""

from __future__ import annotations

import argparse
import os
import sys
import xml.etree.ElementTree as ET
from collections import Counter

import numpy as np
from scipy.spatial.transform import Rotation as Rot

pygame = None  # bound by run_gui, kept lazy so --self-test needs no GUI deps

HERE = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.normpath(os.path.join(HERE, "..", "model"))
DEFAULT_URDF = os.path.join(MODEL_DIR, "glove_non_diametric.urdf")

MOVABLE = ("revolute", "prismatic", "continuous")

# Used for --tint and for exports that carry no <material> of their own. One hue
# per kinematic branch off the root, so it works whatever the export named things.
PALETTE = [0xE0555A, 0xE0913D, 0x54C25A, 0x4A9BE8, 0xB57BE8, 0xE0D24A, 0x4AD2D2, 0xE87BB0]
BASE_COLOR = 0x9AA0AA


# --------------------------------------------------------------------------- #
# URDF parsing + forward kinematics
# --------------------------------------------------------------------------- #
def _fvec(s: str, n: int = 3) -> np.ndarray:
    return np.array([float(x) for x in s.split()][:n], dtype=float)


def rpy_xyz_to_T(xyz: np.ndarray, rpy: np.ndarray) -> np.ndarray:
    T = np.eye(4)
    T[:3, :3] = Rot.from_euler("xyz", rpy).as_matrix()  # URDF fixed-axis rpy
    T[:3, 3] = xyz
    return T


class Visual:
    def __init__(self, mesh: str, T_local: np.ndarray, rgba: np.ndarray | None, scale: np.ndarray):
        self.mesh = mesh
        self.T_local = T_local
        self.rgba = rgba  # from <material>, None if the export didn't say
        self.scale = scale
        self.color = BASE_COLOR  # set by URDF.apply_colors


class Joint:
    def __init__(self, name, jtype, parent, child, T_origin, axis, lower, upper):
        self.name = name
        self.jtype = jtype
        self.parent = parent
        self.child = child
        self.T_origin = T_origin
        self.axis = axis
        self.lower = lower
        self.upper = upper


class URDF:
    def __init__(self, path: str, assets_dir: str | None = None):
        self.dir = os.path.dirname(os.path.abspath(path))
        alongside = (self.dir, os.path.join(self.dir, "meshes"), os.path.join(self.dir, "assets"))
        self.search_dirs = [d for d in (assets_dir, *alongside) if d]
        root = ET.parse(path).getroot()
        self.name = root.get("name")

        self.visuals: dict[str, list[Visual]] = {}
        self.missing: list[str] = []
        for link in root.findall("link"):
            vs = []
            for v in link.findall("visual"):
                mesh_el = v.find("geometry/mesh")
                if mesh_el is None:
                    continue
                o = v.find("origin")
                xyz = _fvec(o.get("xyz", "0 0 0")) if o is not None else np.zeros(3)
                rpy = _fvec(o.get("rpy", "0 0 0")) if o is not None else np.zeros(3)
                scale = _fvec(mesh_el.get("scale", "1 1 1"))
                col = v.find("material/color")
                rgba = _fvec(col.get("rgba"), 4) if col is not None and col.get("rgba") else None
                mesh = self._resolve(mesh_el.get("filename"))
                if mesh is None:
                    self.missing.append(mesh_el.get("filename"))
                    continue
                vs.append(Visual(mesh, rpy_xyz_to_T(xyz, rpy), rgba, scale))
            self.visuals[link.get("name")] = vs

        self.joints: list[Joint] = []
        self.children: dict[str, list[Joint]] = {}
        all_children = set()
        link_names = set(self.visuals)
        for j in root.findall("joint"):
            o = j.find("origin")
            xyz = _fvec(o.get("xyz", "0 0 0")) if o is not None else np.zeros(3)
            rpy = _fvec(o.get("rpy", "0 0 0")) if o is not None else np.zeros(3)
            ax = j.find("axis")
            axis = _fvec(ax.get("xyz")) if ax is not None else np.array([1.0, 0.0, 0.0])
            n = np.linalg.norm(axis)
            axis = axis / n if n > 0 else np.array([1.0, 0.0, 0.0])
            lim = j.find("limit")
            lo = float(lim.get("lower", -np.pi)) if lim is not None else -np.pi
            up = float(lim.get("upper", np.pi)) if lim is not None else np.pi
            jt = Joint(
                j.get("name"),
                j.get("type"),
                j.find("parent").get("link"),
                j.find("child").get("link"),
                rpy_xyz_to_T(xyz, rpy),
                axis,
                lo,
                up,
            )
            self.joints.append(jt)
            self.children.setdefault(jt.parent, []).append(jt)
            all_children.add(jt.child)
            link_names |= {jt.parent, jt.child}

        roots = sorted(ln for ln in link_names if ln not in all_children)
        if not roots:
            raise SystemExit("no root link -> the kinematic tree has a cycle")
        self.root = roots[0]
        self.movable = [j for j in self.joints if j.jtype in MOVABLE]
        self.has_materials = any(v.rgba is not None for vl in self.visuals.values() for v in vl)
        self._find_branches()

    def _find_branches(self):
        """Tag every link and joint with the outermost movable chain it hangs off,
        so fingers can be told apart without relying on link names."""
        self.branch_of: dict[str, str | None] = {}
        self.joint_branch: dict[str, str] = {}
        self.branches: list[str] = []
        queue = [(self.root, None)]
        while queue:
            link, branch = queue.pop(0)
            self.branch_of[link] = branch
            for j in self.children.get(link, []):
                b = branch
                if b is None and j.jtype in MOVABLE:
                    b = j.name
                    self.branches.append(b)
                if b is not None:
                    self.joint_branch[j.name] = b
                queue.append((j.child, b))

    def apply_colors(self, tint: bool):
        """Prefer the export's own <material> colors; tint per branch otherwise."""
        hues = {b: PALETTE[i % len(PALETTE)] for i, b in enumerate(self.branches)}
        for link, vlist in self.visuals.items():
            branch = hues.get(self.branch_of.get(link), BASE_COLOR)
            for v in vlist:
                if v.rgba is not None and not tint:
                    r, g, b, _ = (np.clip(v.rgba, 0, 1) * 255).astype(int)
                    v.color = (int(r) << 16) + (int(g) << 8) + int(b)
                else:
                    v.color = branch

    def _resolve(self, fn: str) -> str | None:
        rel = fn.split("://", 1)[-1]
        cands = [os.path.join(self.dir, rel)]
        cands += [os.path.join(d, os.path.basename(rel)) for d in self.search_dirs]
        return next((os.path.abspath(c) for c in cands if os.path.exists(c)), None)

    def fk(self, q: dict[str, float]) -> dict[str, np.ndarray]:
        """World transform of every link, given joint positions q."""
        world = {self.root: np.eye(4)}
        stack = [self.root]
        while stack:
            parent = stack.pop()
            Tp = world[parent]
            for j in self.children.get(parent, []):
                T = Tp @ j.T_origin
                if j.jtype in ("revolute", "continuous"):
                    Rj = np.eye(4)
                    Rj[:3, :3] = Rot.from_rotvec(j.axis * q.get(j.name, 0.0)).as_matrix()
                    T = T @ Rj
                elif j.jtype == "prismatic":
                    Tt = np.eye(4)
                    Tt[:3, 3] = j.axis * q.get(j.name, 0.0)
                    T = T @ Tt
                world[j.child] = T
                stack.append(j.child)
        return world


def fist_pose(urdf: URDF) -> dict[str, float]:
    """Curl every flex joint to ~60% of its upper limit, abduction left alone."""
    q = {}
    for j in urdf.movable:
        curl = "abduction" not in j.name and "cmc" not in j.name
        q[j.name] = 0.6 * j.upper if curl else 0.0
    return q


# --------------------------------------------------------------------------- #
# meshcat scene
# --------------------------------------------------------------------------- #
def build_scene(vis, urdf: URDF):
    import meshcat.geometry as g

    handles = []  # (meshcat_path, link, T_local)
    for link, vlist in urdf.visuals.items():
        for i, v in enumerate(vlist):
            mat = g.MeshLambertMaterial(color=v.color)
            vis[f"robot/{link}/{i}"].set_object(g.StlMeshGeometry.from_file(v.mesh), mat)
            handles.append((f"robot/{link}/{i}", link, v.T_local))
    return handles


def update_scene(vis, handles, world):
    for path, link, T_local in handles:
        vis[path].set_transform(world[link] @ T_local)


# --------------------------------------------------------------------------- #
# pygame slider UI
# --------------------------------------------------------------------------- #
class Slider:
    W = 210
    ROW_H = 26

    def __init__(self, x, y, joint: Joint, color: int):
        self.x, self.y = x, y
        self.name = joint.name
        self.lo, self.up = joint.lower, joint.upper
        self.color = color
        self.val = 0.0
        self.grab = False
        self.track = pygame.Rect(self.x, self.y + 15, self.W, 5)

    def knob_x(self):
        t = (self.val - self.lo) / (self.up - self.lo) if self.up > self.lo else 0.5
        return int(self.x + t * self.W)

    def hit(self, mx, my):
        return abs(mx - self.knob_x()) < 10 and abs(my - (self.y + 17)) < 12

    def set_from_mouse(self, mx):
        t = float(np.clip((mx - self.x) / self.W, 0.0, 1.0))
        self.val = self.lo + t * (self.up - self.lo)

    def draw(self, surf, font):
        rgb = ((self.color >> 16) & 255, (self.color >> 8) & 255, self.color & 255)
        surf.blit(font.render(self.name, True, (205, 205, 215)), (self.x, self.y))
        surf.blit(font.render(f"{self.val:+.2f}", True, rgb), (self.x + self.W + 6, self.y))
        pygame.draw.rect(surf, (62, 64, 74), self.track, border_radius=3)
        pygame.draw.circle(surf, rgb, (self.knob_x(), self.y + 17), 7)


# Words that say which segment a part is rather than which finger it belongs to.
SEGMENT_WORDS = frozenset({"mcp", "pip", "dip", "cmc", "seg", "revolute", "joint", "link"})


def _group_label(branch: str, joints: list[Joint]) -> str:
    """Name a finger column after its moving segments ('ring_pip_1' -> 'ring'). These
    exports name parts inconsistently within one finger, so take the commonest leading
    word rather than a shared prefix, and fall back to the branch's root joint."""
    for names in ([j.child for j in joints], [j.name for j in joints]):
        words = [n.strip("_-").split("_")[0] for n in sorted(names)]
        votes = Counter(w for w in words if len(w) >= 3 and w not in SEGMENT_WORDS)
        if votes:
            return votes.most_common(1)[0][0]
    return branch


def layout(urdf: URDF):
    """One column per kinematic branch, joints in tree order."""
    groups: dict[str, list[Joint]] = {}
    for j in urdf.movable:
        groups.setdefault(urdf.joint_branch.get(j.name, "other"), []).append(j)

    labels = {b: _group_label(b, js) for b, js in groups.items()}
    clashing = {v for v in labels.values() if list(labels.values()).count(v) > 1}
    labels = {b: (b if v in clashing else v) for b, v in labels.items()}

    sliders, headers = [], []
    col_w = Slider.W + 70
    for c, (branch, joints) in enumerate(groups.items()):
        x = 16 + c * col_w
        color = PALETTE[urdf.branches.index(branch) % len(PALETTE)] if branch in urdf.branches else BASE_COLOR
        headers.append((labels[branch], color, x, 46))
        for r, j in enumerate(joints):
            sliders.append(Slider(x, 70 + r * Slider.ROW_H, j, color))
    rows = max(len(v) for v in groups.values())
    return sliders, headers, (len(groups) * col_w + 16, 70 + rows * Slider.ROW_H + 16)


def run_gui(urdf: URDF, open_browser: bool):
    global pygame
    import meshcat
    import pygame

    vis = meshcat.Visualizer()
    print(f"\n  meshcat URL: {vis.url()}\n")
    if open_browser:
        try:
            vis.open()
        except Exception:  # noqa: BLE001 - headless box, URL above still works
            print("  (couldn't launch a browser - open the URL yourself)")
    vis["/Background"].set_property("top_color", [0.10, 0.12, 0.16])
    vis["/Background"].set_property("bottom_color", [0.02, 0.02, 0.04])

    handles = build_scene(vis, urdf)
    print(f"  loaded {len(handles)} meshes")
    q = {j.name: 0.0 for j in urdf.movable}
    update_scene(vis, handles, urdf.fk(q))

    pygame.init()
    pygame.display.set_caption(f"{urdf.name} - {len(urdf.movable)} DOF")
    sliders, headers, (W, H) = layout(urdf)
    screen = pygame.display.set_mode((W, H))
    font = pygame.font.SysFont("dejavusansmono", 12)
    bigfont = pygame.font.SysFont("dejavusans", 14, bold=True)

    clock = pygame.time.Clock()
    dirty = running = True
    while running:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False
            elif e.type == pygame.KEYDOWN:
                if e.key in (pygame.K_q, pygame.K_ESCAPE):
                    running = False
                elif e.key in (pygame.K_r, pygame.K_f):
                    pose = fist_pose(urdf) if e.key == pygame.K_f else {}
                    for s in sliders:
                        s.val = pose.get(s.name, 0.0)
                    dirty = True
            elif e.type == pygame.MOUSEBUTTONDOWN:
                for s in sliders:
                    if s.hit(*e.pos) or s.track.collidepoint(*e.pos):
                        s.grab = True
                        s.set_from_mouse(e.pos[0])
                        dirty = True
            elif e.type == pygame.MOUSEBUTTONUP:
                for s in sliders:
                    s.grab = False
            elif e.type == pygame.MOUSEMOTION:
                for s in sliders:
                    if s.grab:
                        s.set_from_mouse(e.pos[0])
                        dirty = True

        if dirty:
            for s in sliders:
                q[s.name] = s.val
            update_scene(vis, handles, urdf.fk(q))
            dirty = False

        screen.fill((22, 24, 30))
        screen.blit(
            bigfont.render(f"{urdf.name}   [drag | R zero | F fist | Q quit]", True, (235, 235, 245)),
            (16, 16),
        )
        for label, color, x, y in headers:
            rgb = ((color >> 16) & 255, (color >> 8) & 255, color & 255)
            screen.blit(bigfont.render(label, True, rgb), (x, y))
        for s in sliders:
            s.draw(screen, font)
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


def _mesh_points(urdf: URDF, q: dict[str, float]) -> np.ndarray:
    """World position of every visual's origin - a pure joint rotation leaves the
    child link origin put, so meshes are what tell us the pose actually changed."""
    world = urdf.fk(q)
    return np.array([(world[ln] @ v.T_local)[:3, 3] for ln, vl in urdf.visuals.items() for v in vl])


def _subtree_has_visuals(urdf: URDF, joint: Joint) -> bool:
    stack = [joint.child]
    while stack:
        link = stack.pop()
        if urdf.visuals.get(link):
            return True
        stack.extend(c.child for c in urdf.children.get(link, []))
    return False


def self_test(urdf: URDF) -> int:
    """Parse, resolve meshes and move every joint - no GUI, no meshcat."""
    n_vis = sum(len(v) for v in urdf.visuals.values())
    print(f"  links {len(urdf.visuals)}, visuals {n_vis}, movable joints {len(urdf.movable)}")
    if urdf.missing:
        print(f"  FAIL {len(urdf.missing)} unresolved mesh(es), e.g. {urdf.missing[:3]}")
        return 1
    if not urdf.movable:
        print("  FAIL no movable joints -> nothing to articulate")
        return 1

    zero = {j.name: 0.0 for j in urdf.movable}
    p0 = _mesh_points(urdf, zero)
    stuck, bare = [], []
    for j in urdf.movable:
        moved = np.abs(_mesh_points(urdf, {**zero, j.name: 0.5}) - p0).max()
        if moved >= 1e-6:
            continue
        # A joint whose whole subtree carries no <visual> articulates fine, it just
        # has nothing to draw - that's a hole in the export, not broken kinematics.
        (bare if not _subtree_has_visuals(urdf, j) else stuck).append(j.name)
    for name in bare:
        print(f"  warn joint '{name}' has no mesh anywhere below it -> moves nothing on screen")
    if stuck:
        print(f"  FAIL {len(stuck)} joint(s) move nothing downstream: {stuck}")
        return 1

    n_moved = int((np.abs(_mesh_points(urdf, fist_pose(urdf)) - p0) > 1e-6).any(axis=1).sum())
    print(f"  ok   all {len(urdf.movable)} joints articulate")
    print(f"  ok   fist pose repositions {n_moved}/{n_vis} visuals")
    print(f"  ok   all {n_vis} mesh refs resolved")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("urdf", nargs="?", default=DEFAULT_URDF)
    p.add_argument("--assets-dir", default=None, help="mesh dir (default: alongside the urdf and ./assets)")
    p.add_argument("--self-test", action="store_true", help="parse + FK check, no windows")
    p.add_argument("--no-browser", action="store_true", help="print the meshcat URL instead of opening it")
    p.add_argument(
        "--tint", action="store_true", help="one color per finger instead of the export's own colors"
    )
    args = p.parse_args()

    if not os.path.exists(args.urdf):
        print(f"no such file: {args.urdf}")
        return 1

    urdf = URDF(args.urdf, args.assets_dir)
    urdf.apply_colors(tint=args.tint or not urdf.has_materials)
    src = "per-finger tint" if args.tint or not urdf.has_materials else "the export's own materials"
    print(f"Loaded {urdf.name} from {args.urdf}: {len(urdf.movable)} DOF, root '{urdf.root}'")
    print(f"  {len(urdf.branches)} kinematic branch(es), colored by {src}")
    if urdf.missing:
        print(f"  [warn] {len(urdf.missing)} mesh(es) not found, e.g. {urdf.missing[:3]}")
    if not urdf.movable:
        print("  [warn] no movable joints -> nothing to drag (run check_urdf.py on this export)")

    if args.self_test:
        return self_test(urdf)
    run_gui(urdf, open_browser=not args.no_browser)
    return 0


if __name__ == "__main__":
    sys.exit(main())
