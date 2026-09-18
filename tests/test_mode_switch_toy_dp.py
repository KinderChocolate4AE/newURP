"""D1 toy DP 검산 — docs/105 §4.2 완료판정의 실행 형태.

1. tiny case 에서 brute force 와 DP 의 도달가능 벡터집합 일치
2. cue 완전 마스킹 시 두 정책군의 strict gap == 0 (+ Pi_fixed ⊆ Pi_rec)
3. 한 mode 가 모든 branch 에서 지배하는 null 에서 reversal == 0
4. 확률 sanity
"""
import pytest

from shepherd.mode_switch.toy_dp import (
    achievable_brute, achievable_dp, class_summary, default_params, enumerate_policies,
    evaluate, is_fixed, rank_table, split_classes, strict_grid,
)

TINY = dict(T=3, t_cue=1, t_roe=1, tau_net=1)


def test_dp_matches_bruteforce_tiny():
    p = default_params(**TINY)
    assert achievable_dp(p) == achievable_brute(p)


def test_dp_matches_bruteforce_default():
    p = default_params()
    assert achievable_dp(p) == achievable_brute(p)


def test_masked_cue_zero_strict_gap():
    # 후기 관측 전부 마스킹 -> 경로 분기가 없어 rec == fixed (105 §4.2-2)
    p = default_params(t_cue=None)
    rec, fixed = split_classes(p)
    assert len(rec) == len(fixed)           # 모든 정책의 first commit 이 경로독립
    g = strict_grid(p, (0.3, 0.5, 0.7), (1.0, 2.0))
    assert g["n_strict"] == 0


def test_dominant_mode_no_reversal():
    p = default_params(p_net=(0.9, 0.9), p_kin=(0.3, 0.3))
    _, n_rev = rank_table(p)
    assert n_rev == 0


def test_fixed_subset_rec_feasibility():
    p = default_params()
    rec, fixed = split_classes(p)
    assert all(is_fixed(p, pol) for pol in fixed)
    assert len(fixed) < len(rec)
    r, f = class_summary(p, rec), class_summary(p, fixed)
    if f["feasible"]:
        assert r["feasible"]
    if r["feasible"] and f["feasible"]:
        assert r["min_cost"] <= f["min_cost"] + 1e-9


def test_probability_sanity():
    p = default_params()
    for pol in enumerate_policies(p):
        mean, v0, v1 = evaluate(p, pol)
        for v in (mean, v0, v1):
            assert -1e-9 <= v[0] <= 1 + 1e-9
            assert -1e-9 <= v[1] <= 1 + 1e-9
            assert v[0] + v[1] <= 1 + 1e-9
            assert v[2] >= -1e-9


def test_default_has_reversal_and_strict_cell():
    # 기본 계수는 reversal 과 strict cell 이 존재하도록 '설계'된 값 (docs/106 §3:
    # 이 양성은 만들어낸 것이며 G2 증거가 아니다) -- 회귀 감지용으로만 고정.
    p = default_params()
    _, n_rev = rank_table(p)
    assert n_rev >= 1
    g = strict_grid(p, (0.5,), (2.0,))
    assert g["cells"][0][0]["cat"] == 2
