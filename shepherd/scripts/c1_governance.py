"""C-1 governance primitives — seed namespace, evidence identity, result tiers.

Three engineering defects in this campaign (deployment off-by-one, witness-blind RNG
seeds, an "independent" verifier that shared the net-cone predicate) were all
preventable by a central contract rather than by a deeper experiment.  This module
is that contract.  Everything downstream derives seeds and identities from here.

1. SEED NAMESPACE
   Seeds are derived from a stable SHA-256 over a named tuple, never from Python's
   `hash()` (which is salted per process).  Two MODES, because the two uses are
   genuinely different:

     paired    : the attacker stream is INDEPENDENT of witness_id, so different
                 defenders face the identical attacker draw -- common random
                 numbers, fair difficulty comparison.
     diversity : the attacker stream DEPENDS on witness_id, so different defenders
                 get decorrelated searches -- basin discovery.

   Using `paired` for a diversity claim (which is what Phase 1J-1N did implicitly)
   makes raw/unique artifact counts overstate search diversity.

2. EVIDENCE IDENTITY
   Two hashes, deliberately separate:

     attack_policy_hash   : the attacker control sequence alone.  Two scenarios CAN
                            legitimately share one, as Phase 1N observed.
     evidence_bundle_hash : scenario/config, defender trajectory, attacker control
                            AND trajectory, reset + every seed, fire step, verifier
                            version, verdict and margin, dynamics/config hash.
                            This is what identifies a witness; it must differ
                            whenever any of those differ.

3. RESULT TIERS
   One word must not carry several meanings.  Evidence strength and generality are
   reported on two independent axes.
"""
from __future__ import annotations
import hashlib, json
import numpy as np

PROTOCOL_VERSION = "c1-D0-2026-07-25"

# ---- result tiers (never collapse these into "certified"/"robust"/"exact") ----
STRENGTH_TIERS = ("SEARCH_CANDIDATE",                    # optimizer said so; no verifier
                  "NUMERICALLY_VERIFIED_COUNTEREXAMPLE",  # independent verifier, float roots
                  "INTERVAL_CERTIFIED_COUNTEREXAMPLE")    # rational/Bernstein certificate
GENERALITY_TIERS = ("FIXED_CONDITION",                   # one reset, one condition
                    "MULTI_RESET",                        # several independent resets
                    "DISTRIBUTION_LEVEL")                 # sealed reset set, distributional claim


def _digest(*parts) -> str:
    h = hashlib.sha256()
    for p in parts:
        h.update(str(p).encode()); h.update(b"\x1f")
    return h.hexdigest()


def derive_seed(*, base_seed: int, scenario_id: str, witness_id: str, reset_id: int,
                attacker_class: str, restart_id: int, mode: str,
                protocol_version: str = PROTOCOL_VERSION) -> int:
    """Stable 63-bit seed.  `mode` decides whether witness_id enters the stream.

    mode='paired'    -> witness_id EXCLUDED  (common random numbers across defenders)
    mode='diversity' -> witness_id INCLUDED  (decorrelated search per defender)
    """
    if mode not in ("paired", "diversity"):
        raise ValueError("mode must be 'paired' or 'diversity'")
    wid = witness_id if mode == "diversity" else "<paired:witness-independent>"
    d = _digest(protocol_version, scenario_id, wid, reset_id, attacker_class,
                restart_id, base_seed, mode)
    return int(d[:16], 16) & ((1 << 63) - 1)


def attack_policy_hash(seg_acc) -> str:
    """Hash of the attacker control sequence ALONE.  Shared values are legitimate."""
    a = np.asarray(seg_acc, float)
    return hashlib.sha256(np.ascontiguousarray(a.round(12)).tobytes()).hexdigest()[:16]


def evidence_bundle_hash(*, scenario_id, config_sha, defender_traj, attacker_seg_acc,
                         attacker_traj, reset_id, seeds: dict, fire_step,
                         verifier_version, verdict, margin_m, dynamics_sha) -> str:
    """Hash of the FULL evidence bundle.  Changing any one field must change this."""
    def arr(x):
        return hashlib.sha256(
            np.ascontiguousarray(np.asarray(x, float).round(12)).tobytes()).hexdigest()
    payload = {"protocol": PROTOCOL_VERSION, "scenario_id": scenario_id,
               "config_sha": config_sha, "defender_traj": arr(defender_traj),
               "attack_policy": attack_policy_hash(attacker_seg_acc),
               "attacker_traj": arr(attacker_traj), "reset_id": reset_id,
               "seeds": {k: int(v) for k, v in sorted(seeds.items())},
               "fire_step": fire_step, "verifier_version": verifier_version,
               "verdict": verdict, "margin_m": round(float(margin_m), 12),
               "dynamics_sha": dynamics_sha}
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:24]


def label(strength: str, generality: str) -> str:
    if strength not in STRENGTH_TIERS:
        raise ValueError(strength)
    if generality not in GENERALITY_TIERS:
        raise ValueError(generality)
    return "%s / %s" % (strength, generality)
