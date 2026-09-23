[![YouTube](https://img.shields.io/badge/YouTube-Video-red?logo=youtube)](https://www.youtube.com/watch?v=iPtgvh6fNdQ)
[![Discord](https://img.shields.io/badge/Discord-Join-blue?logo=discord)](https://discord.gg/5bphCGJUGA)

# Project Homunculus

![Project Homunculus Logo](glove/homunculus.png)

Project Homunculus is open-source, low-cost hardware for capturing human hand and arm motion and turning it into robot commands. It has two parts. The first is a Hall-effect VR glove that tracks finger joints with magnetic sensors instead of cameras or external tracking stations. The second is a 7-DOF exoskeleton arm for whole-body teleoperation. Together they let you drive dexterous hands and humanoids directly from your own body, so you can collect demonstration data for robot learning without motion-capture rigs or expensive commercial gloves.

The glove is built from off-the-shelf parts (SS49E Hall sensors, an ESP32-C3, a 16-channel multiplexer) and costs well under $100 in materials. It streams joint data at over 300 Hz and needs no external infrastructure: you put it on and go. Everything is included so you can build, modify, and extend it yourself: firmware, a 3D-printable enclosure, the PCB design, and a Unity visualizer. The project predates much of the recent wave of teleoperation gloves and has been cited as prior art in humanoid teleoperation research (HOMIE, RSS 2025).

## Repository layout

| Path | Description |
|------|-------------|
| [`glove/`](glove/) | **Hall Effect VR Glove** — firmware, 3D-printable enclosure, PCB design, Unity hand visualizer, and experimental tools. |
| [`exo/`](exo/) | **Exoskeleton Arm** *(submodule)* — 7-DOF whole-body control device with CAD, firmware, URDF models, and PCB files. |