from scripts.b0_v3_capturer_clbc1_f3_rl2_posthoc import analyze, analyze_seed


def _row(sid, outcome, *, input_robust=None, actual_robust=None, crossing=0):
    fire = actual_robust is not None
    return {"scenario_id": sid, "cell_id": "cell",
            "bin": "N" if outcome == "CAPTURED" else "F_other",
            "outcome": outcome, "fire": fire, "clean_crossings": crossing,
            "policy_input_at_fire": None if input_robust is None else {
                "v_shot_worst": float(input_robust), "p_feasible": 1.0},
            "accepted_fire_judge": None if not fire else {
                "robust_ready": actual_robust}}


def test_seed_analysis_classifies_draw_flip_vs_interior():
    control = [_row(0, "CAPTURED", input_robust=True, actual_robust=True),
               _row(1, "SPENT_FAIL", input_robust=False, actual_robust=False)]
    ppo = [_row(0, "SPENT_FAIL", input_robust=True, actual_robust=False),
           _row(1, "CAPTURED", input_robust=True, actual_robust=True)]
    got = analyze_seed(control, ppo)
    assert got["nonrobust_kind_counts"]["f3_frozen_control"] == {"interior": 1}
    assert got["nonrobust_kind_counts"]["f3_aim_ppo"] == {"draw_flip": 1}
    assert got["spent_equals_nonrobust"] == {"f3_frozen_control": True,
                                             "f3_aim_ppo": True}
    assert not got["all_nonrobust_are_draw_flips"]["f3_frozen_control"]
    assert got["all_nonrobust_are_draw_flips"]["f3_aim_ppo"]
    assert got["N_discordance"]["control_only"] == 1
    assert got["N_discordance"]["ppo_only"] == 1


def test_harvested_posthoc_attributes_added_nonrobust_to_draw_flips():
    got = analyze()
    assert got["manifest_hash"] == "297d0e271393f388"
    assert got["sealed_decision"] == "STOP_RL2"
    assert got["lineage_and_pairing_valid"]
    for seed in got["seeds"].values():
        assert all(seed["spent_equals_nonrobust"].values())
    s0, s1 = got["seeds"]["0"], got["seeds"]["1"]
    assert s0["nonrobust_kind_counts"]["f3_aim_ppo"] == {"interior": 1, "draw_flip": 3}
    assert s0["nonrobust_kind_counts"]["f3_frozen_control"] == {"interior": 1}
    interior = {arm: [e["scenario_id"] for e in s0["nonrobust_FIRE"][arm]
                      if e["kind"] == "interior"]
                for arm in s0["nonrobust_FIRE"]}
    assert interior["f3_frozen_control"] == interior["f3_aim_ppo"] == [5]
    assert s1["nonrobust_kind_counts"]["f3_frozen_control"] == {}
    assert s1["nonrobust_kind_counts"]["f3_aim_ppo"] == {"draw_flip": 1}
