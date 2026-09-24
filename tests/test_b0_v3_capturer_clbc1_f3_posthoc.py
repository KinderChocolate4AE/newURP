from scripts.b0_v3_capturer_clbc1_f3_posthoc import analyze, analyze_seed


def _row(sid, outcome, *, input_robust=None, actual_robust=None, crossing=0):
    fire = actual_robust is not None
    return {"scenario_id": sid, "cell_id": "cell",
            "bin": "N" if outcome == "CAPTURED" else "F_other",
            "outcome": outcome, "fire": fire, "clean_crossings": crossing,
            "policy_input_at_fire": None if input_robust is None else {
                "v_shot_worst": float(input_robust), "p_feasible": 1.0},
            "accepted_fire_judge": None if not fire else {
                "robust_ready": actual_robust}}


def test_seed_analysis_reports_gain_loss_and_draw_flip():
    control = [_row(0, "CAPTURED", input_robust=False, actual_robust=True),
               _row(1, "SPENT_FAIL", input_robust=False, actual_robust=False)]
    f3 = [_row(0, "PENETRATED"),
          _row(1, "SPENT_FAIL", input_robust=True, actual_robust=False)]
    got = analyze_seed(control, f3)
    assert got["N_discordance"]["control_only"] == 1
    assert got["lost_N"][0]["control_policy_input_robust"] is False
    assert got["lost_N"][0]["control_authoritative_robust"] is True
    assert len(got["f3_input_vs_authoritative_draw_flips"]) == 1
    assert got["f3_nonrobust_FIRE_all_explained_by_draw_flip"]


def test_harvested_posthoc_is_lineaged_and_explains_residual_fires():
    got = analyze()
    assert got["manifest_hash"] == "00a9e45ff4b0506d"
    assert got["sealed_decision"] == "PASS_F3_TO_CAPTURER_ONLY_RL_CONTRACT_DRAFT"
    assert got["lineage_and_pairing_valid"]
    assert all(s["f3_nonrobust_FIRE_all_explained_by_draw_flip"]
               for s in got["seeds"].values())
