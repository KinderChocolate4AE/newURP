from shepherd.scripts.b0_v3_mappo_preflight import _run_cfg, _source_s


def test_preflight_config_has_no_kinetic_commit_head():
    cfg = _run_cfg(64)
    assert cfg["mappo"]["limiter_commit"] is False
    assert cfg["mappo"]["coma_mix"] == 0.0
    assert cfg["loop"]["total_env_steps"] == 64


def test_source_s_comes_from_requested_cell():
    m = {"units": [
        {"cell_id": "a", "s_lo": 0},
        {"cell_id": "b", "s_lo": 300},
    ]}
    assert _source_s(m, "b") == 300

