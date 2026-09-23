#!/usr/bin/env python3
"""Validate an onshape-to-robot URDF export.

Run this after every Onshape export to confirm the robot actually articulates
(joints came through), the kinematic tree is sane, and all meshes exist.

    python check_urdf.py                 # checks ./robot.urdf
    python check_urdf.py path/to.urdf    # checks a specific file

Exit code is the number of ERRORS (0 = all good), so it's CI-friendly.

Only needs the Python standard library. If `mujoco` is installed it will also
try to *compile* the URDF (catches duplicate mesh names, bad inertia, etc.).
"""
from __future__ import annotations

import argparse
import os
import sys
import xml.etree.ElementTree as ET

G = "\033[32m"; Y = "\033[33m"; R = "\033[31m"; B = "\033[1m"; X = "\033[0m"
if not sys.stdout.isatty():
    G = Y = R = B = X = ""

errors: list[str] = []
warns: list[str] = []


def err(m):
    errors.append(m); print(f"{R}  ERROR{X} {m}")


def warn(m):
    warns.append(m); print(f"{Y}  WARN {X} {m}")


def ok(m):
    print(f"{G}  ok   {X} {m}")


def head(m):
    print(f"\n{B}{m}{X}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("urdf", nargs="?", default="robot.urdf")
    p.add_argument("--assets-dir", default=None, help="mesh dir (default: alongside the urdf and ./assets)")
    p.add_argument("--no-mujoco", action="store_true", help="skip the MuJoCo compile test")
    p.add_argument("--expect-dofs", type=int, default=None,
                   help="expected number of DOFs; errors if the export doesn't match (e.g. 22)")
    args = p.parse_args()

    if not os.path.exists(args.urdf):
        print(f"{R}no such file:{X} {args.urdf}")
        return 1
    urdf_dir = os.path.dirname(os.path.abspath(args.urdf)) or "."

    try:
        root = ET.parse(args.urdf).getroot()
    except ET.ParseError as e:
        print(f"{R}XML parse error:{X} {e}")
        return 1

    print(f"{B}Checking{X} {args.urdf}")
    print(f"  robot name: {root.get('name')}")

    links = root.findall("link")
    joints = root.findall("joint")
    link_names = [l.get("name") for l in links]

    # ---- links ----
    head(f"Links: {len(links)}")
    dup_links = {n for n in link_names if link_names.count(n) > 1}
    if dup_links:
        err(f"duplicate link names: {sorted(dup_links)}")
    if len(links) == 1:
        warn("only 1 link -> the whole model is a single rigid body (no segments to articulate)")

    # ---- joints ----
    head(f"Joints: {len(joints)}")
    DOF_PER_TYPE = {"revolute": 1, "prismatic": 1, "continuous": 1,
                    "planar": 3, "floating": 6, "fixed": 0}
    by_type: dict[str, int] = {}
    for j in joints:
        jt = j.get("type", "?")
        by_type[jt] = by_type.get(jt, 0) + 1
    for jt, c in sorted(by_type.items()):
        print(f"    {jt}: {c}")
    dof_total = sum(DOF_PER_TYPE.get(jt, 0) * c for jt, c in by_type.items())
    print(f"  {B}DOFs: {dof_total}{X}")
    if args.expect_dofs is not None:
        if dof_total == args.expect_dofs:
            ok(f"DOF count matches expected ({args.expect_dofs})")
        else:
            err(f"DOF count is {dof_total}, expected {args.expect_dofs} "
                f"({'too few - missing dof_ mates?' if dof_total < args.expect_dofs else 'too many'})")

    # THE headline check
    if len(joints) == 0:
        err("0 joints found -> nothing will move. In Onshape, name the mates 'dof_<name>' "
            "(Revolute/Slider), not Fastened. Fastened mates merge parts into one link.")
    elif all(j.get("type") == "fixed" for j in joints):
        err("all joints are 'fixed' -> no articulation. Use Revolute/Slider mates named 'dof_...'.")

    # per-joint detail + validation
    if joints:
        head("Joint detail")
        print(f"    {'name':22} {'type':11} {'axis':10} limits           parent -> child")
    jnames = [j.get("name") for j in joints]
    dup_j = {n for n in jnames if jnames.count(n) > 1}
    if dup_j:
        err(f"duplicate joint names: {sorted(dup_j)}")

    children = set()
    parent_of: dict[str, str] = {}
    edges: dict[str, list[str]] = {}
    for j in joints:
        name = j.get("name"); jt = j.get("type", "?")
        pe = j.find("parent"); ce = j.find("child")
        par = pe.get("link") if pe is not None else None
        chi = ce.get("link") if ce is not None else None
        ax = j.find("axis")
        axis = ax.get("xyz") if ax is not None else "(default 1 0 0)"
        lim = j.find("limit")
        if lim is not None:
            limtxt = f"[{lim.get('lower','?')},{lim.get('upper','?')}]"
        else:
            limtxt = "(none)"
        print(f"    {name:22.22} {jt:11} {axis:10.10} {limtxt:16} {par} -> {chi}")

        if par not in link_names:
            err(f"joint '{name}': parent link '{par}' does not exist")
        if chi not in link_names:
            err(f"joint '{name}': child link '{chi}' does not exist")
        if par == chi:
            err(f"joint '{name}': parent == child ('{par}')")
        if jt in ("revolute", "prismatic") and lim is None:
            warn(f"joint '{name}' is {jt} but has no <limit> -> will behave as unbounded "
                 "(set Limits in the Onshape mate)")
        if jt == "continuous":
            warn(f"joint '{name}' is continuous (free-spinning); set Limits in the mate if it should be bounded")
        if ax is None and jt not in ("fixed",):
            warn(f"joint '{name}' has no <axis> (defaults to 1 0 0) -> check the mate connector Z axis")
        if chi is not None:
            if chi in children:
                err(f"link '{chi}' is the child of more than one joint (kinematic tree must be strict)")
            children.add(chi)
            parent_of[chi] = par
            edges.setdefault(par, []).append(chi)

    # ---- tree / roots ----
    head("Kinematic tree")
    roots = [n for n in link_names if n not in children]
    if len(roots) == 1:
        ok(f"single root link: {roots[0]}")
    elif len(roots) == 0 and links:
        err("no root link (every link is a child) -> there is a cycle")
    else:
        # >1 root: with joints present this means disconnected sub-trees
        if joints:
            err(f"{len(roots)} root links (tree is disconnected): {roots[:8]}"
                f"{' ...' if len(roots) > 8 else ''}")
        else:
            print(f"    {len(roots)} links, no joints (see error above)")

    # reachability + cycle check from the (first) root
    if roots and joints:
        seen = set(); stack = [roots[0]]
        while stack:
            n = stack.pop()
            if n in seen:
                err(f"cycle detected at link '{n}'"); break
            seen.add(n)
            stack.extend(edges.get(n, []))
        orphans = [n for n in link_names if n not in seen and n != roots[0]]
        if orphans:
            err(f"{len(orphans)} link(s) not reachable from root '{roots[0]}': "
                f"{orphans[:8]}{' ...' if len(orphans) > 8 else ''}")

    # ---- meshes ----
    head("Meshes")
    meshes = [m.get("filename") for m in root.iter("mesh") if m.get("filename")]
    uniq = sorted(set(meshes))
    print(f"    {len(meshes)} mesh refs, {len(uniq)} unique files")
    search_dirs = [urdf_dir, os.path.join(urdf_dir, "assets")]
    if args.assets_dir:
        search_dirs.insert(0, args.assets_dir)
    missing = []
    for f in uniq:
        rel = f.replace("package://", "")
        in_pkg = rel.split("/", 1)[-1] if f.startswith("package://") else rel
        cands = [os.path.join(urdf_dir, rel), os.path.join(urdf_dir, in_pkg)]
        cands += [os.path.join(d, os.path.basename(rel)) for d in search_dirs]
        if not any(os.path.exists(c) for c in cands):
            missing.append(f)
    if missing:
        err(f"{len(missing)} mesh file(s) not found, e.g.: {missing[:5]}")
    elif uniq:
        ok(f"all {len(uniq)} mesh files found on disk")

    # ---- optional MuJoCo compile ----
    if not args.no_mujoco:
        head("MuJoCo compile test")
        try:
            import re
            import tempfile
            import mujoco
            src = open(args.urdf).read()
            inject = ('<mujoco><compiler meshdir="assets" strippath="true" '
                      'balanceinertia="true" autolimits="true" discardvisual="false"/></mujoco>')
            src2 = re.sub(r"(<robot[^>]*>)", r"\1\n" + inject, src, count=1)
            tmp = os.path.join(urdf_dir, "_check_urdf_tmp.urdf")
            open(tmp, "w").write(src2)
            try:
                m = mujoco.MjModel.from_xml_path(tmp)
                ok(f"compiles: nbody={m.nbody} njnt={m.njnt} ngeom={m.ngeom} nmesh={m.nmesh} nq={m.nq}")
                if m.njnt == 0:
                    warn("MuJoCo also sees 0 joints (nq=0) -> confirms nothing articulates")
            finally:
                if os.path.exists(tmp):
                    os.remove(tmp)
        except ImportError:
            print("    (mujoco not installed - skipping; the checks above are enough)")
        except Exception as e:  # noqa: BLE001
            err(f"MuJoCo failed to compile the URDF: {type(e).__name__}: {str(e)[:300]}")

    # ---- verdict ----
    head("Summary")
    print(f"  {len(errors)} error(s), {len(warns)} warning(s)")
    if not errors:
        n_moving = sum(c for t, c in by_type.items() if t != "fixed")
        print(f"{G}{B}  PASS{X} - {len(links)} links, {n_moving} moving joint(s). Export looks good.")
    else:
        print(f"{R}{B}  FAIL{X} - fix the errors above and re-export.")
    return len(errors)


if __name__ == "__main__":
    sys.exit(main())
