"""capturer-F1 BC-SNR 실험의 봉인·한 요인·pairing·gate 회귀검사.

torch-free: manifest 봉인, namespace 분리, 한 요인 소스 diff, pairing/coverage, gate,
CuBLAS 거부. torch 표시: F1 손실의 최적점, 그리고 smoke 경로 전체 (두 objective 의
초기 상태·minibatch·FIRE head·limiter·log_std·norm 동일성 + RL update 0회).
"""
import ast
import difflib
import json
import pathlib

import pytest

from scripts.b0_v3_capturer_f1 import (CONTROL, F1, PASS, STOP, apply_gate,
                                       pair_keys, require_cublas, scenario_plan,
                                       signature)
from scripts.b0_v3_capturer_f1_manifest import MANIFEST, build
from shepherd.scripts.b2_manifest import load as load_b2

ROOT = pathlib.Path(__file__).resolve().parents[1]
PILOT_MANIFEST = ROOT / "artifacts" / "marl" / "b0_v3_pilot_manifest.json"
B5_MANIFEST = ROOT / "artifacts" / "marl" / "b5_limiter_only" / "manifest.json"


def test_manifest_file_matches_builder_and_hash_is_stable():
    m = build()
    assert json.loads(MANIFEST.read_text(encoding="utf-8")) == m == build()
    assert m["manifest_hash"] == json.loads(MANIFEST.read_text(encoding="utf-8"))["manifest_hash"]
    assert m["schema"] == "b0-v3-capturer-f1-manifest-v1"
    assert m["prerequisites"]["b0_v3_hash"] == "5e7b5b486b9d8a4a"
    assert m["prerequisites"]["bc_dataset_hash"] == "b48aad5eab4a92bd"
    assert m["evaluation"]["episodes_total"] == 2 * 2 * 28 * 10
    assert m["promotion"] == "none; W6 remains closed"


def test_eval_namespace_is_disjoint_from_pilot_and_b5():
    pilot = json.loads(PILOT_MANIFEST.read_text(encoding="utf-8"))
    b5 = json.loads(B5_MANIFEST.read_text(encoding="utf-8"))
    ev = build()["evaluation"]
    assert (ev["seed0"], ev["namespace"]) == (81000, "b0v3_capturer_f1_eval_v1")
    others = [(pilot[k]["seed0"], pilot[k]["seed_ns"])
              for k in ("initialization", "training", "evaluation")]
    others += [(b5[k]["seed0"], b5[k]["seed_ns"]) for k in ("training", "evaluation")]
    assert pilot["evaluation"]["seed0"] == 61000 and b5["evaluation"]["seed0"] == 71000
    assert ev["seed0"] not in {s for s, _ in others}
    assert ev["namespace"] not in {n for _, n in others}
    # torch seed 범위 (seed 1 까지 +1e6) 도 다른 namespace 의 seed0 와 겹치지 않는다
    lo, hi = ev["seed0"], ev["seed0"] + 1_000_000 + 279
    assert not any(lo <= s <= lo + 279 or 1_000_000 + lo <= s <= hi for s, _ in others)


def _body(path: pathlib.Path, name: str) -> list:
    src = path.read_text(encoding="utf-8")
    fn = next(n for n in ast.walk(ast.parse(src))
              if isinstance(n, ast.FunctionDef) and n.name == name)
    lines = ast.get_source_segment(src, fn).splitlines()[1:]    # def 줄 제외
    doc = ast.get_docstring(fn)
    out = [ln.strip() for ln in lines if ln.strip()]
    if doc:
        out = out[1:] if out[0].endswith('"""') else out
    return [ln for ln in out if not ln.startswith(("import ", "from "))]


def test_f1_changes_only_the_axis_objective():
    pilot = _body(ROOT / "shepherd" / "scripts" / "b0_v3_mappo_pilot.py",
                  "initialize_from_bc")
    f1 = _body(ROOT / "scripts" / "b0_v3_capturer_f1.py", "initialize_from_bc_f1")
    diff = [d for d in difflib.ndiff(pilot, f1) if d[:1] in "+-"]
    removed = sorted(d[2:] for d in diff if d[0] == "-")
    added = [d[2:] for d in diff if d[0] == "+"]
    assert removed == sorted([
        "pa = pred_axis / pred_axis.norm(dim=-1, keepdim=True).clamp_min(1e-9)",
        "ta = at[idx] / at[idx].norm(dim=-1, keepdim=True).clamp_min(1e-9)",
        "axis_loss = (1.0 - (pa * ta).sum(-1)).mean()",
    ])
    assert added == ["axis_loss = unit_axis_mse(pred_axis, at[idx])"]


def test_paired_plan_covers_28x10_and_is_objective_independent():
    m, b2 = build(), load_b2()
    for seed in (0, 1):
        plan = scenario_plan(m, b2, seed)
        assert len(plan) == 280
        assert len({p["cell_id"] for p in plan}) == 28
        assert [p["scenario_id"] for p in plan] == list(range(280))
        assert all(p["scenario_id"] // 10 == p["cell_index"] for p in plan)
        assert all(p["env_seed"] == 81000 + p["scenario_id"] for p in plan)
        assert all(p["torch_seed"] == 81000 + 1_000_000 * seed + p["scenario_id"]
                   for p in plan)
        # 결정론: 두 objective 가 같은 plan 을 받는다 (plan 은 objective 를 모른다)
        assert pair_keys(plan) == pair_keys(scenario_plan(m, b2, seed))
    p0, p1 = scenario_plan(m, b2, 0), scenario_plan(m, b2, 1)
    assert [r[:4] for r in pair_keys(p0)] == [r[:4] for r in pair_keys(p1)]
    assert signature(p0) != signature(p1)                 # torch seed 만 다르다
    # 사전 고정 trace 4건이 plan 의 해당 scenario 와 일치
    by_sid = {p["scenario_id"]: p["cell_id"] for p in p0}
    assert all(by_sid[sid] == cid for cid, sid in m["traces"]["scenarios"])


def _counts(n_c, n_f, x_c, x_f, h_c, h_f):
    mk = lambda n, x, h: {"N": n, "clean_crossing_episodes": x, "H_illegal": h}
    return {CONTROL: mk(n_c, x_c, h_c), F1: mk(n_f, x_f, h_f)}


OK = {"lineage": True, "pairing": True, "finite": True, "completion": True}


def test_gate_requires_per_seed_increase_and_pooled_h_illegal():
    good = {0: _counts(9, 20, 25, 60, 21, 20), 1: _counts(8, 12, 20, 30, 20, 21)}
    assert apply_gate(good, OK, [0, 1])["decision"] == PASS      # pooled H 41 <= 41
    tie_n = {0: good[0], 1: _counts(8, 8, 20, 30, 20, 20)}        # seed1 N 동률
    assert apply_gate(tie_n, OK, [0, 1])["decision"] == STOP
    no_x = {0: _counts(9, 20, 25, 25, 21, 20), 1: good[1]}        # seed0 crossing 동률
    assert apply_gate(no_x, OK, [0, 1])["decision"] == STOP
    more_h = {0: _counts(9, 20, 25, 60, 21, 22), 1: good[1]}      # pooled H 43 > 41
    g = apply_gate(more_h, OK, [0, 1])
    assert g["decision"] == STOP and not g["clauses"]["pooled_H_illegal_not_increased"]
    assert apply_gate(good, {**OK, "pairing": False}, [0, 1])["decision"] == STOP


def test_cuda_requires_deterministic_cublas(monkeypatch):
    m = build()
    monkeypatch.delenv("CUBLAS_WORKSPACE_CONFIG", raising=False)
    with pytest.raises(SystemExit):
        require_cublas("cuda", m)
    assert require_cublas("cpu", m) is None
    for val in (":4096:8", ":16:8"):
        monkeypatch.setenv("CUBLAS_WORKSPACE_CONFIG", val)
        assert require_cublas("cuda", m) == val
    monkeypatch.setenv("CUBLAS_WORKSPACE_CONFIG", ":0:0")
    with pytest.raises(SystemExit):
        require_cublas("cuda:0", m)


@pytest.mark.torch
def test_unit_axis_mse_is_minimal_at_the_unit_teacher_axis():
    torch = pytest.importorskip("torch", reason="F1 loss needs torch")
    from scripts.b0_v3_capturer_f1 import unit_axis_mse
    teacher = torch.tensor([[0.3, -0.4, 0.0], [0.0, 0.0, 2.0]])
    unit = teacher / teacher.norm(dim=-1, keepdim=True)
    assert float(unit_axis_mse(unit, teacher)) == 0.0
    # 방향이 맞아도 크기가 틀리면 벌점 — cosine 손실이 못 보던 오차
    assert float(unit_axis_mse(0.162 * unit, teacher)) == pytest.approx(
        (1 - 0.162) ** 2 / 3, rel=1e-6)
    assert float(unit_axis_mse(2.0 * unit, teacher)) > 0.0


@pytest.mark.torch
def test_smoke_is_one_factor_and_never_updates(tmp_path, monkeypatch):
    """smoke 전체 경로: 두 objective 의 동일성 검사가 전부 참이고 PPO update 0회."""
    pytest.importorskip("torch", reason="BC reconstruction needs torch")
    from shepherd.scripts.train_m4 import M4Runner
    from shepherd.train.mappo import MAPPOTrainer
    from scripts.b0_v3_capturer_f1 import run_seed

    def boom(*a, **k):
        raise AssertionError("RL update must never run in capturer-F1")
    monkeypatch.setattr(MAPPOTrainer, "update", boom)
    monkeypatch.setattr(M4Runner, "update", boom, raising=False)
    monkeypatch.setattr(M4Runner, "collect_rollout", boom, raising=False)
    s = run_seed(0, "cpu", smoke=True, out_root=tmp_path)

    assert all(s["identity_checks"].values()), s["identity_checks"]
    tf = s["teacher_fit"]
    assert tf[CONTROL]["initial_state"] == tf[F1]["initial_state"]
    assert tf[CONTROL]["minibatch_sequence_hash"] == tf[F1]["minibatch_sequence_hash"]
    assert tf[CONTROL]["bc_metrics"]["steps"] == 400
    assert "original post-BC checkpoint" in tf[CONTROL]["anchor"]["basis"]
    traj = s["self_trajectory"]
    assert pair_keys(traj[CONTROL]["records"]) == pair_keys(traj[F1]["records"])
    assert traj[CONTROL]["n"] == traj[F1]["n"] == 2
    pv = s["provenance"]
    assert pv["rl_updates"] == 0 and "cublas_workspace_config" in pv
    assert {"torch_version", "cuda_version", "device", "deterministic_algorithms",
            "code_commit", "code_dirty_scoped"} <= set(pv)
    assert not (tmp_path / "smoke" / "seed0" / ".done").exists()
