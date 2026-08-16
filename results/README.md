# results/ — canonical artifact pointer

이 파일은 **어떤 산출물이 정본인지** 를 못박는다. 오래된 파일은 **삭제하지 않는다**
(provenance 보존). 대신 아래 표를 먼저 읽고, superseded 산출물에서 수치를 끌어오지 않는다.

## R4 근접거리 측정 계약 (docs/83 §29 · §30)

**적용 범위 구분 — 네 가지를 혼동하지 말 것:**

| | |
|---|---|
| old artifact | **삭제하지 않음** — provenance 보존 |
| old **proximity metrics** (`d_min*`, `t_min`, `range_t_min`, `p_reach`, `closest`) | **superseded** |
| old **outcome labels / 결과확률** (`label`, `P_HK`, `P_net`, `P_PEN`) | **invalidated 아님** — 재측정에서 3600 에피소드 전부 불변 확인 |
| `*_r4` (lead-time 은 `*_r4b`) | **proximity-derived metric 의 canonical source** |

```text
E3 proximity diagnostics:
  canonical:                     results/e3_oracle_r4.json
  supersedes-for-measurement:    results/e3_oracle.json
  reason:                        R4 proximity-measurement contract (docs/83 §29)
  outcome labels:                unchanged

E4-1 (temporal stagger):
  canonical:                     results/e4_stagger_r4.json
  supersedes-for-measurement:    results/e4_stagger.json
  outcome labels:                unchanged

E4-1b (matched mean):
  canonical:                     results/e4b_matched_r4.json
  supersedes-for-measurement:    results/e4b_matched.json
  outcome labels:                unchanged

E4-1c (uniform lead):
  canonical:                     results/e4c_uniform_r4.json
  supersedes-for-measurement:    results/e4c_uniform.json
  outcome labels:                unchanged

lead-time diagnostic:
  canonical:                     results/lead_time_r4b.json      # ★ _r4 아님
  supersedes-for-measurement:    results/lead_time_diag.json
  no-op rerun (인용 금지):        results/lead_time_r4.json
  reason:                        lead_time_diag.py 배선 누락으로 _r4 는 원본과 동일
                                 (docs/83 §30.6 자기신고). 배선 후 실측 = _r4b
  outcome labels:                unchanged
```

**함정**: `lead_time_r4.json` 은 `_r4` 접미사를 갖지만 **교정되지 않은 no-op** 이다.
lead-time 근접거리는 반드시 **`lead_time_r4b.json`** 을 쓴다.

## 인용 규칙

- 보고 수치는 canonical 산출물에서만 가져온다.
- 정정 이력(예: `0.043 → 0.190`)은 **논문 본문/appendix 에 쓰지 않는다**. 최종 값만 쓴다
  (docs/84 §2 — R4 measurement-debug history 는 본문에서 제외).
- 판정/주장 수준의 정본은 `docs/83` 과 `artifacts/audits/claim_registry.tsv` 다.

## reproducibility appendix 문장 (동결)

> **For E3 proximity-derived diagnostics, `results/e3_oracle_r4.json` is the canonical
> artifact. The pre-R4 `results/e3_oracle.json` is retained for provenance only; all
> reported proximity statistics use the R4-corrected measurement contract.**
