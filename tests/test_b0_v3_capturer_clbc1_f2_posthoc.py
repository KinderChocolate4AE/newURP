from scripts.b0_v3_capturer_clbc1_f2_posthoc import analyze, fire_groups, paired


def _row(sid, outcome, robust=None, crossing=0):
    fire = robust is not None
    return {"scenario_id": sid, "bin": "N" if outcome == "CAPTURED" else "F_other",
            "outcome": outcome, "fire": fire, "clean_crossings": crossing,
            "policy_input_at_fire": None if not fire else {
                "v_shot_soft": 1.0, "v_shot_worst": float(bool(robust))},
            "accepted_fire_judge": None if not fire else {
                "robust_ready": robust, "v_shot_soft": 1.0,
                "ang_att_teacher_deg": 3.0, "ang_cmd_teacher_deg": 4.0,
                "t": 10, "boxed_in": False}}


def test_fire_groups_uses_authoritative_event():
    got = fire_groups([_row(0, "CAPTURED", True),
                       _row(1, "SPENT_FAIL", False),
                       _row(2, "PENETRATED")])
    assert got["accepted_FIRE"] == 2
    assert got["capture_per_FIRE"] == .5
    assert got["robust_ready_matches_N"]
    assert got["by_terminal"]["N"]["robust_ready"] == 1
    assert got["policy_input_vs_authoritative_robust"]["both"] == 1


def test_paired_reports_f2_only_fire_outcomes():
    control = [_row(0, "PENETRATED"), _row(1, "CAPTURED", True)]
    f2 = [_row(0, "SPENT_FAIL", False), _row(1, "CAPTURED", True)]
    got = paired(control, f2)
    assert got["FIRE_discordance"]["f2_only"] == 1
    assert got["f2_only_FIRE_outcomes"] == {"SPENT_FAIL": 1}


def test_harvested_readout_is_lineaged_and_paired():
    got = analyze()
    assert got["manifest_hash"] == "567f134a862335ce"
    assert got["sealed_decision"] == "STOP_F2"
    assert got["lineage_and_pairing_valid"]
