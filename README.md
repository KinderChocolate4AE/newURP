# newURP — Cooperative Shaping of the Exchange Frontier for Non-Destructive Counter-UAS
*(working title; repo/package name `shepherd` is a placeholder — finalize before publishing)*

**Load-bearing claim.** A team of cheap, expendable kamikaze **path-limiter** drones *shapes*
an attacking drone so as to shift the **exchange frontier** of a scarce, irreversible,
miss-is-free **non-destructive net-capturer** — i.e. cooperative shaping makes each scarce
net shot economically worth more, **beating "just buy more nets."** Solved with multi-agent RL.
**Target fidelity: 6-DOF.**

## Status — research preview / WIP (2026-06)
- **Direction + novelty:** pivot + adversarial novelty audit done (`docs/`). Seam verified
  open (~90–94%) against differential-game value, defense-OR economics, herding, counter-UAS;
  defended as an *intersection*. Key conceded prior: Atkinson & Kress 2025 (exchange-frontier backdrop).
- **Thesis demonstrated (torch-free proxy):** see `prototypes/` + `results/` — the shaping lever
  is real; cheap-limiter shaping **dominates** buying nets on the exchange frontier.
- **Next:** 6-DOF MARL — reactive adversary + learned shaping policy + *measured* frontier.

## Design principle — GOAL over MEANS
The research **goal** (exchange-economics of cooperative shaping) lives in `shepherd/game/` and is
**sim-agnostic**. The 6-DOF simulator is a **pluggable backend** behind `shepherd/sim/interface.py`;
the concrete choice (WarSim SE3 / Isaac Lab / PX4-ROS2-Gazebo) is **deferred to lab resourcing**.

## Layout
```
docs/         direction, novelty+prior-art, formalization (the game), action plan, status
shepherd/
  game/       THE GOAL (sim-agnostic): capture-viability (v_shot), exchange economics, roles
  sim/        THE MEANS (pluggable, 6-DOF target): abstract backend interface + backends/
  agents/     reactive adversary + baselines (no-shaping / selection / buy-nets / heuristic)
  train/      MARL training (MAPPO/HAPPO, COMA credit assignment)
  eval/       exchange-frontier, regime-map, figures
prototypes/   numpy proof-of-concept that de-risked the direction (reachset, frontier, exchange game)
results/      figures
experiments/  run configs + scripts (reproducible)
tests/        unit tests (start with game/viability)
```

## License / citation
**TODO** — open publication intended (choose MIT/Apache-2.0). Citation: TBD on preprint.
