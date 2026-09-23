# Glove URDF + viewer

Interactive viewer for the kinematic model of the Project Homunculus sensor
glove (Onshape assembly `glove_non_diametric`), to check that it articulates.
The model itself lives one level up, in [`../model/`](../model/).

```bash
python3 view_glove.py              # 3D view + one slider per joint
python3 view_glove.py --self-test  # no windows: parse, mesh resolution, FK
python3 check_urdf.py ../model/glove_non_diametric.urdf
```

The viewer opens a meshcat render in the browser (`http://127.0.0.1:7000/static/`)
and a slider window, one column per finger. Drag a slider; `F` makes a fist, `R`
zeroes everything, `Q` quits. `--tint` colors each finger chain a flat color
instead of using the export's own materials, which helps when you want to see
which parts belong to which chain. `--no-browser` just prints the URL.

Needs `numpy`, `scipy`, `meshcat` and `pygame`. The viewer is standard-library
plus those four; nothing here imports from LeRobot.

## Layout

| Path | What |
| --- | --- |
| `view_glove.py` | The viewer: URDF parser, forward kinematics, meshcat scene, sliders |
| `check_urdf.py` | Structural validator: link/joint tree, DOF count, mesh existence, optional MuJoCo compile |
| `../model/glove_non_diametric.urdf` | **The working model.** 129 links, 128 joints, 23 revolute DOF |
| `../model/meshes/printed/` | The 3D-printed parts, split per joint like [`../print/individual_stls/`](../print/individual_stls/): `MCP/`, `PIP/`, `DIP/`, `palm/` |
| `../model/meshes/hardware/` | M2 screws and nuts |
| `../model/meshes/electronics/` | PCB, ESP32 module, connectors and passives |
| `onshape/config.json` | onshape-to-robot config — document ID and assembly name, i.e. how to re-export |

Only `view_glove.py` and `../model/` are needed to run the viewer. `check_urdf.py`
is a separate tool and `onshape/config.json` only matters when re-exporting.

## Model

23 DOF across five chains: abduction + MCP + PIP + DIP for each of four fingers,
and a 7-joint thumb. The viewer detects those chains from the kinematic tree
rather than from link names, so it also works on re-exports that get named
differently.

Two things to know about the geometry. The STL vertices are in Onshape
part-studio coordinates, so a part's own frame can sit 25 cm away from its
triangles — don't assume a link origin is anywhere near the mesh you see.
And the export names parts inconsistently within a finger: one chain's links are
`pip_1`, `pip_2`, `_dip_2_1` with no finger name at all, which is why one slider
column is labelled `revolute_4` instead of `pinky`.

## Re-exporting

`onshape/config.json` holds the document ID and assembly name for
onshape-to-robot. If you re-export, run `check_urdf.py` on the result before
anything else — a previous export of this same assembly came out with **0
joints** because the Onshape mates were Fastened rather than Revolute/Slider,
which silently merges every part into one rigid body. Mates must be named
`dof_<name>` for the exporter to emit joints.

Note that mesh filenames are not stable across export runs (they gain and lose
trailing underscores), so a new URDF needs its own mesh folder rather than
reusing `../model/meshes/`.
