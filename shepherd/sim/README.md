# shepherd/sim — pluggable 6-DOF backend (THE MEANS, decide later)

Target fidelity = **6-DOF SE3 rigid-body** (attitude + rate limits matter for reduced-attitude
pointing and for the attacker's agile back-diagonal evasion).

Candidate backends (decide with lab resources — focus on the GOAL first):
- **WarSim SE3** (already exists, offline RotorPy bridge) — fastest path to a 6-DOF backend.
- **Isaac Lab** — GPU-parallel (Huh 2026 uses it); heaviest, best for scale.
- **PX4-ROS2-Gazebo SITL** — the lab's hardware-loop stack; the sim-to-real / physical-AI step.

All implement `interface.EnvBackend`. The choice does not affect `shepherd.game` (sim-agnostic).
