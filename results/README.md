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

## 궤적 뷰어 근접거리 계약 (R-014, 2026-08-17)

```text
trajectory viewer (T1 hard-kill):
  canonical:                     results/viz_traj_t1_hk_r5.json
                                 viz/trajectory_viewer_t1_hk_r5.html
  provenance-retained:           results/viz_traj_t1_hk.json
                                 viz/trajectory_viewer_t1_hk.html
  superseded field scope:        steps[].d_lim_min  (표시용 끝점거리)
  outcome labels / steps /
  commit records:                unchanged
```

구 덤프의 `d_lim_min` 은 **화면 보정 좌표 위의 post-step 끝점 거리**였는데 뷰어가
그것을 *"최근접 limiter"* 로, `<= r_contact` 면 *"(접촉권)"* 까지 붙여 보여줬다.
R4 권위값(`_Driver.d_min`)은 같은 driver 위에 있으면서 덤프되지 않았다.
신규 산출물은 `proximity{d_min, t_min, n_unmeasured, contract}` 와 스텝별
`d_swept_min` 을 싣고, 표시용 값은 `d_lim_min_display` 로 개명해 성격을 밝힌다.

**claim registry C033 과의 관계**: C033 이 인용하는 필드(`commits[].source`,
`d_nom`)는 해소기 산물이라 두 파일에서 **동일**하다. 8/8 에피소드에서 라벨·스텝
수·commit record 가 일치함을 재덤프 시 확인했다. 즉 C033 의 증거는 무효화되지
않는다 -- 바뀐 것은 함께 실린 표시용 근접거리뿐이다.

### reproducibility appendix 문장 (동결)

> **`results/viz_traj_t1_hk_r5.json` is the canonical trajectory-viewer artifact
> under the authoritative proximity measurement contract; the prior file is retained
> for provenance. Outcome labels, steps, and commit records are unchanged.**

## provenance stamp 의 dirty 플래그 (R-025, 2026-08-17)

`pivot_manifest.stamp()` 의 dirty 보고가 **커밋 085ac30 을 기준으로 의미가 바뀐다.**
과거 아티팩트를 backfill 하지 않으므로(docs/81 §1-2) 읽는 쪽이 구분해야 한다.

```text
085ac30 이전:
  code_dirty        git status --porcelain (untracked 포함)
                    => 실행이 자기 출력(results/*.json·log)을 레포에 쓰는 것만으로
                       참이 된다. 모든 실행이 그렇게 하므로 stamped artifact
                       16/16 이 true 였고, "코드를 고쳤다" 와 "파일을 만들었다" 를
                       구분하지 못했다.

085ac30 이후 (3 분할, 독립 명령으로 계산):
  code_dirty        결과를 만든 **실행 코드**가 stamped commit 과 다른가
                    (scope = SCIENCE_CODE_ROOTS, 현재 shepherd/ -- 감사로 확인)
  tracked_dirty     tracked snapshot 전체가 clean 했는가 (docs·tests 포함)
  untracked_present 실행 중 생성된 미추적 산출물이 있었는가
```

**과거 `code_dirty: true` 를 "코드가 오염된 채 실행됐다" 로 읽지 말 것.** 포렌식
결과(각 artifact 의 `code_commit` -> 기록 커밋 사이 `shepherd/` diff):

```text
14/16   차이 0                  -> dirty 는 출력 파일이었다
 2/16   자기 생성기 신규 생성      -> 실행 코드는 code_commit 이 아니라 아래 커밋의 것
          results/e1c_fire_decomp.json   실행 코드 = 633105c
          results/e3_oracle.json         실행 코드 = 717e3c1
        (두 창에서 함께 바뀐 slew_audit.py 변경은 r_perp 필드 **순수 추가**라
         psi/ax 등 기존 값에 영향이 없다)
```

## 인용 규칙

- 보고 수치는 canonical 산출물에서만 가져온다.
- 정정 이력(예: `0.043 → 0.190`)은 **논문 본문/appendix 에 쓰지 않는다**. 최종 값만 쓴다
  (docs/84 §2 — R4 measurement-debug history 는 본문에서 제외).
- 판정/주장 수준의 정본은 `docs/83` 과 `artifacts/audits/claim_registry.tsv` 다.

## reproducibility appendix 문장 (동결)

> **For E3 proximity-derived diagnostics, `results/e3_oracle_r4.json` is the canonical
> artifact. The pre-R4 `results/e3_oracle.json` is retained for provenance only; all
> reported proximity statistics use the R4-corrected measurement contract.**
