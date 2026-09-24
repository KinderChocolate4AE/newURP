"""capturer 진단 도구의 회귀검사.

torch-free 부분(발사 인자 관성·trace 렌더)은 로컬에서 돌고, 재구성 결정론은
torch 표시로 서버 venv에서만 돈다. 모듈 자체가 torch를 top-level import하므로
진단 모듈 import는 torch 표시 테스트 안에서만 한다.
"""
import json

import numpy as np
import pytest

from shepherd.m4_env import build_m4_env
from shepherd.scripts.b2_manifest import load as load_b2
from shepherd.scripts.mission_rollout import run_episode
from shepherd.scripts.r2a_stage1 import resolve
from shepherd.scripts.r2b_phase1 import _slices
from shepherd.train.b0_v3_credit import B0V3CreditEnv, B0V3CreditSpec


def _stub_policy(env, fire_bit: float):
    fin = np.array([1.0, 0.0, 0.0, 0.0, fire_bit], np.float32)
    acts = {lid: np.zeros(4, np.float32) for lid in env.limiter_ids}
    acts[env.finisher_id] = fin
    return lambda obs, flags: dict(acts)


def _one_episode(fire_mode: str):
    b2 = load_b2()
    cell = next(c for c in b2["cells"] if c["chi_role"] == "lo_out")
    kw = resolve(_slices()[int(cell["lam_slice"])], cell["chi"], cell["eta"])
    stack = build_m4_env(123, 0, **kw)
    env = B0V3CreditEnv(stack.env, B0V3CreditSpec(beta=0.2))
    r = run_episode(env, stack.scn, stack.lay, seed=123,
                    policy=_stub_policy(env, 1.0), fire_mode=fire_mode,
                    max_steps=40)
    return (r.label, r.outcome, r.steps, r.fire_step, r.clean_crossings,
            r.n_contact)


def test_fire_mode_is_inert_on_the_pure_policy_path():
    """pilot evaluate()가 넘기는 fire_mode='never'는 scripted 역할이 없으면
    발사를 막지 않는다 — 학습 arm 평가 판독의 전제를 못박는다."""
    assert _one_episode("never") == _one_episode("clean")


def test_trace_renderer_writes_a_png(tmp_path):
    pytest.importorskip("matplotlib")
    from scripts.render_capturer_traces import render_trace
    steps = []
    for t in range(12):
        steps.append({
            "t": t, "fsm": "LOADED",
            "p_att": [10.0 - t, 1.0, 0.0], "v_att": [-1.0, 0.0, 0.0],
            "p_fin": [0.0, 0.0, 0.0], "e_fin": [1.0, 0.0, 0.0],
            "p_lims": [[3.0, i, 0.0] for i in range(4)],
            "teacher_axis": [1.0, 0.1, 0.0],
            "v_soft": 0.1 * t / 12, "v_worst": 0.0, "p_feasible": 1.0,
            "clean_prev": t == 8, "fire_event_prev": False,
            "ang_att_teacher_deg": 5.0, "ang_cmd_teacher_deg": 20.0,
            "ang_mean_teacher_deg": 3.0, "fire_prob": 0.1,
        })
    trace = {"schema": "b0-v3-capturer-trace-v1", "mode": "unit",
             "cell_id": "r00c1", "scenario_id": 0, "chi": 0.6, "eta": 2.0,
             "cone_half_angle_rad": 0.212, "cone_range_max": 8.22,
             "theta_fire": 0.9, "target": [0, 0, 0],
             "result": {"bin": "F_other", "label": "TRUNCATED",
                        "outcome": "TRUNCATED", "steps": 12, "fire_step": None,
                        "clean_crossings": 1, "n_contact": 0},
             "steps": steps}
    out = tmp_path / "trace_unit.png"
    render_trace(trace, out)
    assert out.exists() and out.stat().st_size > 0

    trace["arm"] = "clbc1"
    del trace["mode"]
    out_arm = tmp_path / "trace_arm_schema.png"
    render_trace(trace, out_arm)
    assert out_arm.exists() and out_arm.stat().st_size > 0


@pytest.mark.torch
def test_bc_reconstruction_is_deterministic_and_metric_anchored():
    """같은 봉인 dataset·seed에서 두 번 재구성하면 bit-identical이어야 하고,
    검증 앵커는 bc_init.json 지표뿐임이 report에 명시돼야 한다."""
    from scripts.b0_v3_capturer_diagnostic import (_sd_hash, recon_report,
                                                   reconstruct_bc)
    from shepherd.scripts.b0_v3_mappo_pilot import BC_FILE, OUT, load_bc
    from shepherd.scripts.b0_v3_pilot_manifest import load as load_manifest

    manifest, b2 = load_manifest(), load_b2()
    data, _ = load_bc(BC_FILE, manifest)
    r1, _ = reconstruct_bc(manifest, b2, "c0_base", 0, "cpu", data, bc_steps=20)
    r2, _ = reconstruct_bc(manifest, b2, "c0_base", 0, "cpu", data, bc_steps=20)
    assert _sd_hash(r1.tr) == _sd_hash(r2.tr)
    head = [m for m in r1.tr.lim_actor.mean.modules()
            if type(m).__name__ == "Linear"][-1]
    assert float(head.weight.abs().max()) == 0.0

    saved = json.loads((OUT / "c0_base" / "seed0" / "summary.json")
                       .read_text(encoding="utf-8"))
    _, report = recon_report(manifest, b2, "c0_base", 0, "cpu", data,
                             saved["bc_init"])
    assert report["bit_identical_claim"] is False
    assert "저장하지 않았다" in report["original_bc_checkpoint"]
    assert report["double_reconstruction_identical"] is True
    # CPU 재구성은 원본(cuda) 지표와 다를 수 있다 — verdict는 정직하게 갈린다.
    assert report["verdict"] in ("exact-metric-match", "metric-close(<1e-6)",
                                 "metric-mismatch")
