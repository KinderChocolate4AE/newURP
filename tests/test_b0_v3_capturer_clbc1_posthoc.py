"""Pure tests for the read-only CLBC1 post-hoc diagnostic."""
from scripts.b0_v3_capturer_clbc1_posthoc import paired_changes, summarize


def _record(sid, *, fire=False, n=False, worst=0.0, soft=0.0, crossing=0):
    return {
        "scenario_id": sid,
        "fire": fire,
        "bin": "N" if n else "F_other",
        "outcome": "CAPTURED" if n else ("SPENT_FAIL" if fire else "PENETRATED"),
        "clean_crossings": crossing,
        "at_fire": None if not fire else {
            "v_shot_soft": soft,
            "v_shot_worst": worst,
            "fire_prob": 0.8,
            "ang_att_teacher_deg": 4.0,
        },
    }


def test_summarize_separates_soft_only_from_robust_ready_fire():
    rows = [_record(0, fire=True, soft=.95, worst=0),
            _record(1, fire=True, n=True, soft=1, worst=1, crossing=1),
            _record(2)]
    got = summarize(rows)
    assert got["fired"] == 2
    assert got["policy_input_soft_gate_only"] == 1
    assert got["policy_input_robust_ready"] == got["captured_N"] == 1
    assert got["policy_input_robust_matches_N"]["all"]


def test_pairing_reports_direction_without_changing_any_gate():
    replay = [_record(0), _record(1, fire=True, n=True, soft=1, worst=1)]
    clbc1 = [_record(0, fire=True, n=True, soft=1, worst=1),
             _record(1, fire=True, soft=.95, worst=0)]
    got = paired_changes(replay, clbc1)
    assert got["N_discordance"] == {
        "neither": 0, "replay_only": 1, "clbc1_only": 1, "both": 0}
    assert got["terminal_transitions"] == {
        "CAPTURED->SPENT_FAIL": 1, "PENETRATED->CAPTURED": 1}
    assert got["clbc1_only_FIRE_outcomes"] == {"CAPTURED": 1}
