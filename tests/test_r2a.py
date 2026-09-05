"""paper-R2a lattice / Stage 0 게이트 (docs/87 §4 RED-first 목록: pin 왕복 · co-scale 후
pin pi 불변 · 판정 함수 · hash 안정성) + r4 계약 분리 (R2a-L / R2a-P)."""
import pathlib

import numpy as np
import pytest

from shepherd.scripts import r2a_lattice as L
from shepherd.scripts.r2a_stage0 import chi50_isotonic, pav_decreasing

ROOT = pathlib.Path(__file__).resolve().parents[1]
FROZEN = ROOT / "results/curve_hold_reactive.json"
CELLS = [(0.53, 2.1), (0.61, 3.9)]


def test_pi_roundtrip_bit_exact():
    for chi, eta, tau, rho in [(0.57, 2.1, 0.30, 1.77), (1.2, 3.9, 0.45, 2.30)]:
        a, v = L.dims_from(chi, eta, tau, rho)
        c2, e2 = L.chi_eta(a, v, tau, rho)
        assert abs(c2 - chi) < 1e-12 and abs(e2 - eta) < 1e-12


def test_support_matches_brief_table():
    """브리프 §4.4 tau_B 후보표 (legacy a_min 11) + R-rho support + r4 a_min 7 at tau 0.45."""
    for tb, cmin, emin in [(0.45, 0.629, 2.034), (0.425, 0.561, 1.921),
                           (0.40, 0.497, 1.808), (0.375, 0.437, 1.695)]:
        s = L.support(tb, L.RHO_REF, 11.0)
        assert abs(s["chi"][0] - cmin) < 5e-4 and abs(s["eta"][0] - emin) < 5e-4
    r = L.support(L.TAU_REF, L.RHO_B, 11.0)
    assert abs(r["chi"][1] - 1.526) < 5e-4 and abs(r["eta"][1] - 3.913) < 5e-4
    assert abs(L.support(0.45, L.RHO_REF, 7.0)["chi"][0] - 0.400) < 5e-4
    assert abs(L.support(0.45, L.RHO_REF, 6.0)["chi"][0] - 0.343) < 5e-4


def test_ledger_sim_invariant_dom_target_only():
    rows = L.ledger(0.45, 7.0, CELLS)
    assert len(rows) == 5 * len(CELLS)
    ref = next(r for r in rows if r["impl"] == "R-ref")["pi"]
    for r in rows:
        moved = sorted(k for k in r["pi"] if abs(r["pi"][k] - ref[k]) > 1e-9)
        assert moved == r["target"], r["impl"]
    dom = next(r for r in rows if r["impl"] == "R-rho-DOM")["pi"]
    assert abs(dom["lam"] - 3.574) < 2e-3 and abs(np.degrees(dom["alpha"]) - 15.63) < 0.02
    tdom = next(r for r in rows if r["impl"] == "R-tau-DOM")["pi"]
    assert abs(tdom["k_f_tau"] - 4.0 * 0.45) < 1e-12 and abs(ref["k_f_tau"] - 1.20) < 1e-12


def test_ledger_rejects_leaky_dom():
    """R-tau-DOM 이 k_f 를 co-scale 해버리면 (SIM 누수) ledger 가 거부해야 한다."""
    good, orig = L.impls(0.45), L.impls

    def leaky(tb):
        d = orig(tb)
        d["R-tau-DOM"]["k_f"] = d["R-tau-SIM"]["k_f"]
        return d
    L.impls = leaky
    try:
        with pytest.raises(AssertionError):
            L.ledger(0.45, 7.0, CELLS)
    finally:
        L.impls = orig
    assert L.impls(0.45) == good


def test_select_tau_b_largest_passing_then_d1():
    inside = {"2.1": [0.70, 0.80], "3.9": [0.70, 0.80]}       # 0.45 legacy support 내부
    assert L.select_tau_b(inside, 11.0)["tau_B"] == 0.45
    low = {"3.6": [0.54, 0.64]}          # lo-0.02 = 0.52: 0.425 (0.561) 밖, 0.40 (0.497) 안
    assert L.select_tau_b(low, 11.0)["tau_B"] == 0.40
    hopeless = {"3.6": [0.30, 0.40]}
    g = L.select_tau_b(hopeless, 11.0)
    assert g["tau_B"] is None and g["verdict"].startswith("D-1")
    assert L.select_tau_b({}, 11.0)["tau_B"] is None          # usable 행 0 = 판정 불가
    # r4-B: 같은 envelope 도 pin-확장 (a_min 7) 에서는 0.45 가 살아난다
    stage0_like = {"3.6": [0.44, 0.60]}
    assert L.select_tau_b(stage0_like, 11.0)["tau_B"] is None
    assert L.select_tau_b(stage0_like, 7.0)["tau_B"] == 0.45


def test_micro_grid_shape():
    g = L.micro_grid(0.5523)
    assert len(g) == 11 and g[5] == 0.55 and abs(g[1] - g[0] - 0.02) < 1e-9
    assert L.DELTA_P == 0.10 and L.DELTA_CHI == 0.05 and "NOT slope-derived" in L.DELTA_CHI_RATIONALE
    assert L.H_SUPPORT_MIN == 0.05


def test_select_a_min_buffer_rule():
    """r4-B': Stage 0 꼴 envelope (chi50 0.52 at eta 3.6, W 0.10) 에서 7 은 buffer 0.000
    으로 reject, 6 은 0.057 로 accept — 사후 편의가 아니라 H >= 0.05 규칙."""
    env = {"3.6": [0.42, 0.62]}
    sel = L.select_a_min(env, (7.0, 6.0), (0.45,))
    assert sel["a_min"] == 6.0 and sel["gate"]["tau_B"] == 0.45
    assert [t["accept"] for t in sel["trace"]] == [False, True]
    assert not (sel["trace"][0]["H_support"] >= L.H_SUPPORT_MIN)   # 7: 0.45 탈락 → nan/부족
    assert abs(sel["H_support"] - 0.057) < 2e-3


def test_pav_and_cross50_on_step_data():
    x = np.linspace(0, 1, 40)
    y = (x < 0.5).astype(float)
    y[10], y[30] = 0.0, 1.0                                    # 위반 2건
    fit = pav_decreasing(x, y)
    assert np.all(np.diff(fit) <= 1e-12)
    assert abs(chi50_isotonic(x, y) - 0.5) < 0.05
    assert np.isnan(chi50_isotonic(x, np.ones_like(x)))       # 교차 없음 = censored


@pytest.mark.skipif(not FROZEN.exists(), reason="frozen T1 curve artifact not present")
def test_stage0_hash_stable_and_boundary_pinned():
    from shepherd.scripts.r2a_stage0 import run
    a, b = run(ROOT), run(ROOT)
    assert a["hash"] == b["hash"]
    assert abs(a["pooled_chi50_isotonic"] - 0.565) < 0.005
    on = [r for r in a["rows"].values() if r["on_lattice"]]
    assert len(on) == 7 and not any(r["censored"] for r in on)
    assert all(0.50 < r["chi50_isotonic"] < 0.67 for r in on)


@pytest.mark.skipif(not (ROOT / "artifacts/r2a/stage0_envelope.json").exists()
                    or not (ROOT / "artifacts/r2a/provenance_route_sense.json").exists(),
                    reason="stage0/provenance artifact not built")
def test_contracts_separate_hashes_and_tau_b():
    st0 = ROOT / "artifacts/r2a/stage0_envelope.json"
    lat_l, lat_p = L.build_lattice(st0, "R2a-L"), L.build_lattice(st0, "R2a-P")
    assert lat_l["lattice_hash"] != lat_p["lattice_hash"]
    assert lat_p["a_min"] == 6.0 and lat_p["tau_B"] == 0.45 and lat_p["tau_B_gate"]["verdict"] == "SELECTED"
    assert lat_p["a_min_selection"]["H_support"] >= L.H_SUPPORT_MIN
    assert lat_l["a_min"] == 11.0 and lat_l["tau_B"] == 0.375 and lat_l["tau_B_gate"]["directional_only"]
    assert "never pooled" in lat_l["pooling"]
    for lat in (lat_l, lat_p):     # ledger 는 hash 밖 (셀 파생) — 하지만 pi 검증은 통과해야 한다
        assert all(r["in_bracket"] for r in lat["ledger"]
                   if r["impl"] == "R-ref" and r["chi"] >= 0.41)
    # R2a-P boundary 셀은 전 구현 공통 support (a >= 6) 내부여야 한다
    bcells = {(r["chi"], r["eta"]) for r in lat_p["ledger"] if r["chi"] not in L.CHI_GRID}
    assert bcells and all(r["in_bracket"] for r in lat_p["ledger"] if (r["chi"], r["eta"]) in bcells)


def test_ledger_dimensionless_groups_from_injected_values():
    """봉인 조건 (사용자, 2026-09-05): 주입 차원값에서 계산한 무차원군이 구현별로
    SIM = 전부 invariant / R-tau-DOM = k_f·tau 만 / R-rho-DOM = {lam, alpha} 만 이동."""
    rows = L.ledger(0.45, 6.0, CELLS)
    need = {"tau_lock_tau", "tau_kill_tau", "omega_aim_tau", "omega_slew_tau",
            "jink_freq_tau", "homing_tau", "jink_r_rho", "sig_dt",
            "dx_rho", "r_lat_rho", "x0_rho", "kappa", "q_dec", "k_f_tau", "lam", "alpha"}
    ref = next(r for r in rows if r["impl"] == "R-ref")["pi"]
    assert need <= set(ref)
    expect = {"R-ref": [], "R-tau-SIM": [], "R-rho-SIM": [],
              "R-tau-DOM": ["k_f_tau"], "R-rho-DOM": ["alpha", "lam"]}
    for impl, tgt in expect.items():
        pi = next(r for r in rows if r["impl"] == impl)["pi"]
        moved = sorted(k for k in need if abs(pi[k] - ref[k]) > 1e-9)
        assert moved == tgt, (impl, moved)
    # 1/s 차원 상수가 R-tau 에서 실제로 co-scale 됐는지 (원시값 검사)
    inj = next(r for r in rows if r["impl"] == "R-tau-SIM")["inject"]
    assert abs(inj["omega_aim"] - 2.0 * 0.30 / 0.45) < 1e-9 and abs(inj["tau_lock"] - 0.15) < 1e-9
    assert abs(inj["jink_freq"] - 1.5 * 0.30 / 0.45) < 1e-9
    rho_inj = next(r for r in rows if r["impl"] == "R-rho-SIM")["inject"]
    assert abs(rho_inj["sense_range"] - 30.0 * 2.30 / 1.77) < 1e-9


def test_runtime_norm_invariant_across_all_impls():
    """감사 r2 Q3: layout·판정 길이의 /rho 정규화는 DOM 포함 전 구현 invariant."""
    rows = L.ledger(0.45, 6.0, CELLS)
    ref = next(r for r in rows if r["impl"] == "R-ref")["runtime_norm"]
    assert set(ref) == {"ring_center_rho", "ring_radius_rho", "r_ring_rho", "finisher_rho",
                        "x_fire_rho", "target_r_rho", "r_nk_rho"}
    for r in rows:
        assert all(abs(r["runtime_norm"][k] - ref[k]) < 1e-9 for k in ref), r["impl"]
    assert abs(ref["x_fire_rho"] - 16.0 / 1.77) < 1e-9
    # co-scale 누수 주입 시 ledger 가 거부하는지 (r_ring 을 rho 와 안 맞게)
    orig = L._inject

    def leaky(im):
        d = orig(im)
        d["r_ring"] = 2.1                       # 항상 기준값 = R-rho 계에서 비-co-scale
        return d
    L._inject = leaky
    try:
        with pytest.raises(AssertionError):
            L.ledger(0.45, 6.0, CELLS)
    finally:
        L._inject = orig


def test_conditioning_vector_sealed():
    """감사 r2 Q5/§8: 무차원 행동·판정 상수 봉인 + mu 는 conditioning ratio (inert 아님)."""
    cv = L.CONDITIONING_VECTOR
    ev = cv["evasion"]
    assert (ev["jink_amp"], ev["route_gain"], ev["dodge_amp"], ev["repel_margin"]) ==         (0.6, 0.5, 1.8, 1.0) and ev["react_on_commit"] is True
    assert abs(ev["jink_freq_tau_cycles"] - 0.45) < 1e-12 and "2*pi*f*tau" in ev["jink_phase_convention"]
    cr = cv["capability_ratios"]
    assert (cr["mu_a_lim_over_a_att"], cr["nu_v_lim_over_v_att"], cr["v_adv_max_over_v_att"]) ==         (0.35, 1.0, 1.5)
    assert cv["decision"]["commit_threshold"] == 0.5 and cv["decision"]["hold_arm"] is True


@pytest.mark.skipif(not (ROOT / "artifacts/r2a/provenance_route_sense.json").exists(),
                    reason="provenance artifact not built")
def test_provenance_confirmed_and_new_seal_a2():
    import json
    prov = json.loads((ROOT / "artifacts/r2a/provenance_route_sense.json").read_text(encoding="utf-8"))
    assert prov["verdict"] == "CONFIRMED"
    assert prov["deterministic_replay_ok"] and prov["draw_bitexact_all"]
    assert prov["candidate_label_match"][0] == prov["candidate_label_match"][1]
    assert prov["metric_discriminating_eps_n"] > 0
    st0 = ROOT / "artifacts/r2a/stage0_envelope.json"
    lat = L.build_lattice(st0, "R2a-P")
    assert "A2-reactive" in lat["world"]
    assert lat["supersedes"]["R2a-P"] == "e43036f00679ff77"
    assert lat["lattice_hash"] != "e43036f00679ff77"
    assert "conditional on the sealed A2-reactive" in lat["vocab"]["global"]
    assert any("HARD_KILL" in g for g in lat["stage1_gates"])


def test_attacker_fwd_gain_promotion_bitexact_default():
    """R2a Stage 1: fwd_gain 주입점 — 기본값 = FWD_GAIN (기존 거동 bit-exact),
    비기본값은 A1 위임 금지 (A1 경로는 4.0 하드코딩이므로)."""
    from shepherd.agents.attacker_ladder import (FWD_GAIN, A1_SPEC, AttackerSpec,
                                                 is_a1_equivalent)
    assert AttackerSpec().fwd_gain == FWD_GAIN == 4.0
    assert is_a1_equivalent(A1_SPEC)
    import dataclasses
    assert not is_a1_equivalent(dataclasses.replace(A1_SPEC, fwd_gain=2.6666666666666665))


def test_stage1_resolver_capability_and_cone():
    """resolver: 능력비 3종 덮어쓰기 (draw 파생값 누수 방어) + cone half_angle 재계산."""
    import math
    from shepherd.scripts.r2a_stage1 import MU, NU, ADV_V, resolve, draw_cell_jitter
    ims = L.impls(0.45)
    for name in ("R-tau-SIM", "R-rho-DOM"):
        im = ims[name]
        kw = resolve(im, 0.55, 3.0)
        a, v = L.dims_from(0.55, 3.0, im["tau"], im["rho"])
        x = kw["extra_cfg"]
        assert abs(x["physics.a_lim_max"] - MU * a) < 1e-9
        assert abs(x["train.limits.limiter_v_max"] - NU * v) < 1e-9
        assert abs(x["train.limits.adversary_v_max"] - ADV_V * v) < 1e-9
        assert abs(x["viability.cone.half_angle"]
                   - math.atan(im["rho"] / x["viability.cone.range_max"])) < 1e-12
        assert abs(kw["attacker"].fwd_gain * im["tau"]
                   - (1.20 if not im["target"] else 4.0 * im["tau"])) < 1e-9
    c1 = draw_cell_jitter(1000, 7, 0.56, 3.0)
    assert c1 == draw_cell_jitter(1000, 7, 0.56, 3.0)          # CRN 결정론
    assert abs(c1[0] - 0.56) <= 0.01 and abs(c1[1] - 3.0) <= 0.15


@pytest.mark.skipif(not (ROOT / "artifacts/r2a/stage1_protocol.json").exists(),
                    reason="stage1 protocol not sealed")
def test_stage1_gates_sealed_and_passed():
    import json
    fz = json.loads((ROOT / "artifacts/r2a/stage1_feasibility.json").read_text(encoding="utf-8"))
    pw = json.loads((ROOT / "artifacts/r2a/stage1_pathwise.json").read_text(encoding="utf-8"))
    pr = json.loads((ROOT / "artifacts/r2a/stage1_protocol.json").read_text(encoding="utf-8"))
    assert fz["all_ok"] and all(v["ok"] for v in fz["impls"].values())
    assert pw["tier_a_max_dev"] < pr["pathwise_atol"]           # Tier A 게이트
    for row in pw["eps"].values():                              # DOM 판별력 (power)
        assert row["R-tau-DOM"]["max_dev"] > pr["pathwise_atol"]
        assert row["R-rho-DOM"]["max_dev"] > pr["pathwise_atol"]
    lat = json.loads((ROOT / "artifacts/r2a/lattice_R2a_P.json").read_text(encoding="utf-8"))
    assert len(pr["cells"]) == 6 and pr["lattice_hash"] == lat["lattice_hash"]
    assert lat["supersedes_v3"]["R2a-P"] == "3aa3adef77420d12"      # A-prime 체인
    assert abs(lat["q_dec"]["value"] - 1.0 / 6.0) < 1e-12
    assert "q_dec = 1/6" in lat["vocab"]["global"]


def test_stage1_shard_ranges_and_sentinel_atomic(tmp_path):
    """scenario 샤딩이 [0, 2400) 을 정확히 분할하고, sentinel 이 O_EXCL 원자적인지."""
    import json as _json
    from shepherd.scripts import r2a_stage1 as S
    total = 6 * S.N_CELL
    edges = [(k * total // 8, (k + 1) * total // 8) for k in range(8)]
    assert edges[0][0] == 0 and edges[-1][1] == total
    assert all(a2 == b1 for (_, b1), (a2, _) in zip(edges[:-1], edges[1:]))
    orig = S.SENTINEL
    S.SENTINEL = tmp_path / "HARD_KILL_STOP"
    try:
        S._sentinel_write(3, 777, "R-rho-DOM")
        S._sentinel_write(5, 999, "R-ref")            # 두 번째는 무시돼야 한다
        d = _json.loads(S.SENTINEL.read_text(encoding="utf-8"))
        assert d == {"shard": 3, "scenario": 777, "impl": "R-rho-DOM"}
    finally:
        S.SENTINEL = orig


def test_stage1_qdec_invariant_gate():
    """A-prime: dt_check 는 gate 가 아니라 진단 — 대신 전 구현이 q_dec = 1/6 이어야 한다."""
    from shepherd.scripts.r2a_stage1 import resolve
    for name, im in L.impls(0.45).items():
        kw = resolve(im, 0.55, 3.0)
        q = kw["extra_cfg"]["physics.dt"] / kw["extra_cfg"]["physics.tau_deploy"]
        assert abs(q - 1.0 / 6.0) < 1e-12, name
    assert (ROOT / "artifacts/r2a/stage1_dt_review.json").exists()   # 진단은 공개 상태


def test_stage4_levels_orthogonal():
    """Stage 4: lam 등간격 3레벨, rho/tau/q_dec 불변, 이동 pin = {alpha, lam} 뿐."""
    from shepherd.scripts.r2a_stage1 import _stage4_levels
    lvs = _stage4_levels()
    assert [round(l["lam"], 4) for l in lvs] == [4.6441, 4.109, 3.5739]
    assert [round(l["R_max"], 2) for l in lvs] == [8.22, 7.27, 6.33]
    assert [round(l["alpha_deg"], 2) for l in lvs] == [12.15, 13.68, 15.63]
    ref = L._pins(lvs[0]["im"])
    for lv in lvs[1:]:
        pins = L._pins(lv["im"])
        assert sorted(k for k in pins if abs(pins[k] - ref[k]) > 1e-9) == ["alpha", "lam"]
        assert abs(pins["q_dec"] - 1.0 / 6.0) < 1e-12
        assert lv["im"]["rho"] == L.RHO_REF and lv["im"]["tau"] == L.TAU_REF


@pytest.mark.skipif(not (ROOT / "artifacts/r2a/stage2_protocol.json").exists(),
                    reason="stage2/4 protocols not sealed")
def test_stage24_protocols_sealed():
    import json as _j
    p2 = _j.loads((ROOT / "artifacts/r2a/stage2_protocol.json").read_text(encoding="utf-8"))
    p4 = _j.loads((ROOT / "artifacts/r2a/stage4_protocol.json").read_text(encoding="utf-8"))
    lat_l = _j.loads((ROOT / "artifacts/r2a/lattice_R2a_L.json").read_text(encoding="utf-8"))
    assert p2["contract"] == "R2a-L" and p2["lattice_hash"] == lat_l["lattice_hash"]
    assert len(p2["cells"]) == 84 and p2["impl"] == "R-ref only"
    assert p4["n_per_cell"] == 400 and "NOT inherited" in p4["n_rationale"]
    assert ">= 0.20" in p4["verdict_rules"]["primary_material"]
    assert "not gating" in p4["verdict_rules"]["secondary_dose"]
    assert p2["crn_ns"] == "r2a_s2" and p4["crn_ns"] == "r2a_s4"    # Stage 1 CRN 과 분리


@pytest.mark.skipif(not (ROOT / "artifacts/r2a/lattice_R2a_P3.json").exists(),
                    reason="3-D lattice not sealed")
def test_lattice3d_and_scout_sealed():
    import json as _j
    l3 = _j.loads((ROOT / "artifacts/r2a/lattice_R2a_P3.json").read_text(encoding="utf-8"))
    assert "algebraically locked" in l3["coordinates"]["lam"]          # 단일 DOF
    assert l3["stage3_design"]["n3"] == 680 and "650 floor" in l3["stage3_design"]["n_rule"]
    assert "ONLY after the lambda2 boundary slice" in l3["claim_status"]["unlock_rule"]
    assert "min over sealed family F" in l3["stage3_design"]["family_envelope"]["estimand"]
    assert "EVERY resample" in l3["stage3_design"]["family_envelope"]["bootstrap"]
    sc = _j.loads((ROOT / "artifacts/r2a/scout_l2_protocol.json").read_text(encoding="utf-8"))
    assert sc["status"].startswith("exploratory") and sc["lattice3d_hash"] == l3["lattice_hash"]
    assert len(sc["chi_grid"]) == 8 and abs(sc["R_max"] - 8.22 * 1.77 / 2.30) < 1e-9
