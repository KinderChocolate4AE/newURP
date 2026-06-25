"""shepherd.train — MARL training (THE MEANS).

MAPPO first (HAPPO comparison optional); COMA-style counterfactual difference reward
for limiter credit assignment (an enabler's value = how much it raised the finisher's
per-shot value v_shot). Runs in the lab venv (torch). 6-DOF backend via shepherd.sim.
"""
