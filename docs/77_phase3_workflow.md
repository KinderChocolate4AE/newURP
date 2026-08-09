# 77 — Phase III 실행 워크플로 (다른 세션에서 그대로 이어받는 문서) — 2026-08-09

**이 문서 하나로 다음 세션이 대화 없이 이어갈 수 있게 쓴다.**
계약 정본 = `docs/74` **r3.3** · 판정 로그 = `docs/73` **r3.3** · 청사진 = `docs/75` v3.1 ·
선행연구 = `docs/76` v2. 이 문서는 **실행 순서와 명령어**만 담는다.

- 봉인: `PIVOT_LOCK_R33_2026-08-09` · `protocol_hash e69dab93fb712694`
  (r3.2 = `069cade39836cdd1`, manifest 보존 = `artifacts/pivot_lock_r32_2026-08-09.json`)
- **r3.3 변경**: 협력 채널 scope 선언 정밀화 (docs/74 §3.0 채널 대장 · docs/73 §1.5).
  `U^rel < θ` 를 산문으로 옮길 때 **`via the static blockade channel` 한정 강제**.
- 격자: `lattice_hash bd9ffa741d7b79ee` (Z_master 8415 점)
- **Phase III 지도 셀 = 0 개** (아직 지도 없음)

---

## 0. 지금 상태 (2026-08-09 저녁 갱신 — [A]~[E] 이행 세션)

| 항목 | 상태 |
|---|---|
| 게이트 1 (Z_master + Π 선봉인) | ✅ `artifacts/phase3/lattice_spec.json` |
| **[A] 게이트 2·3 수정판 (probe 포함)** | ✅ **PASS** (30 ep · stride 5) → `results/phase3/measure_harness.json` (r3.3 스탬프) |
| 게이트 2·3 1 차 (probe 없음) | ✅ 감사 보존 `results/phase3/measure_harness_v1_noprobe.json` |
| **[B] scope 선언** | ✅ docs/74 §3.0 (r3.3 채널 대장 포함) |
| **[B] τ anchor** | ✅ **확보** — Huang et al. 2022 (arXiv 2207.14420) 원문 정독: 20 m 급 우주 net 20 m/s 사출 전개 **0.6–1.5 s** (Fig 9·10) → τ=0.30 s 문헌 bracket 내. `docs/76` Tier 4-7a |
| **[C] 게이트 9 독립 judge** | ✅ **PASS** — `shepherd/scripts/judge_crosscheck.py` · 123 상태 × 307,992 witness × 3 판정, max\|m1−m2\| ≤ 6e-10 m (eps 1e-6), 불일치 0 → `results/phase3/judge_crosscheck.json` |
| **[D] 게이트 6 unblockable + screen** | ✅ — `shepherd/scripts/cert_unblockable.py` + soundness test 8/8 (`tests/test_cert_unblockable.py`). **G=0 ⇒ 상한 0 조임** 포함. screen=0 = 95.1% (117/123) → `results/phase3/cert_unblockable.json` |
| **[E] coarse pilot** | 🔶 스크립트 완성 (`shepherd/scripts/coarse_pilot.py`, 전 스텝 + 해석적 교전 pre-screen) · 로컬 preview 1 ep → `coarse_pilot_preview.json`. **본실행 (20~30 ep) = 서버 샤딩** (§2[E]) |
| 서버 MARL 9 런 (Phase I ablation) | 🔄 진행 중 · **미열람** |
| OSF timestamp (r3.3 manifest) | ❌ 유일 잔여 감사 항목 + **커밋·태그 `PIVOT_LOCK_R33_2026-08-09` 미생성** (사용자 트랙) |

**[A] 수정판 실측 (확정)**: `V_hold` 8k→32k median 0.0020 / p95 0.0058 · **`V_probe`
median 0.0038 / p95 0.0099** (기준 0.02/0.05) · allocation worst p95 **0.0141**
(seed_shift-probe; 기준 0.05) · 결정 뒤집힘 0 · informative 78/2129 (3.7%).
probe 에서 `substep_2x` 비영 (0.0025) 확인 — 공허 변이 함정 해소. `seg_1` 은 probe
에서도 ~0.0001 → **dogleg 가중 한계 기록 유지** (§4-3).

**[E] 교훈 2 건 (preview 2 회 실패에서)**: (i) G=0 상태에서 unblockable 상한이 1.0
으로 공허해져 전셀 AMB — G=0 ⇒ 상한 0 으로 조임 (sound tightening, test 로 봉인).
(ii) stride 표집은 접근 구간이 지배해 전셀 INF 단일색 — stride 폐기, 전 스텝 +
해석적 교전 pre-screen (`|p_att−apex| > range_max·sec θ + |v|τ + aτ²/2 ⇒ INF 공짜`)
으로 교체. 본실행도 이 방식.

---

## 1. 실행 순서 (재배치판 — 분기 판정을 앞으로 당긴다)

원 순서(docs/75 §1)는 certificate 를 전부 만든 뒤 지도라 **어느 분기인지가 가장 늦게**
나온다. 격자·라벨·판정식·measure 는 이미 봉인됐으므로 **계산 순서와 replicate 수만**
바꾼다 (docs/74 §7 위반 아님 — 정의·축·규칙은 불변).

```
[A] 게이트 2·3 마무리          ← 지금 돌고 있음
[B] scope 선언 + τ anchor      ← 계산 0, publishability 에 가장 큰 레버
[C] 게이트 9 독립 judge         ← pilot 신뢰의 전제
[D] 게이트 6 unblockable mass   ← 이게 곧 전 스텝 cheap screen (1석 2조)
[E] ★ coarse pilot             ← **여기서 분기가 보인다 (A/B/C 중 어디인지)**
[F] 비싼 것들 (7 relaxation · 4·5 MILP · 8 joint 4A) — pilot 이 지목한 좌표에만
[G] 게이트 10 iso-Π → 12 refinement → 13 cooperation audit → 14 certified map
[H] 15 Stage-2 freeze → 16·17 C5 (Gamma) → 18 robustness → 19 보고서/arXiv
```

---

## 2. 단계별 실행

### [A] 게이트 2·3 마무리
```bash
python -m shepherd.scripts.measure_harness --episodes 30 --stride 5 \
    --out results/phase3/measure_harness.json
```
- **통과 기준**: `V_hold` **와** `V_probe` 둘 다 8k→32k median ≤ 0.02 · p95 ≤ 0.05,
  allocation worst p95 ≤ 0.05.
- **실패 시**: 현 R-map protocol **종료**. P/set-based 는 `Phase III-B` 새 hash
  (docs/74 §5.1). 지도 만들지 말 것.
- 산출물 확인: `n_informative` · `gate3.variants.*.shift_V_probe` 가 **0 이 아닌지**
  (0 이면 그 변이는 공허 — §4 함정 참조).

### [B] scope 선언 + τ anchor (계산 0)
1. **scope 선언 — ✅ 완료 (r3.3, `docs/74 §3.0`).** 최초 초안의 "단일 협력 채널" 문구는
   **사실과 달라 폐기**했다. docs/46 이 채널 3 종을 이미 계측했으므로 §3.0 은
   **채널 대장 + 항등식 + 사전 예측 + 읽는 법** 으로 확장됐다. 핵심:
   > 시스템의 협력 채널은 **셋** — (i) 봉쇄 · (ii) 횡압(실측 **음수**) · (iii) 체류(6배).
   > **fixed-state certificate 는 정의상 채널 (i) 만 측정한다** (`V^rel_{<=N} − V_0`
   > ≡ docs/46 채널 (i) 의 배치 최적화값 — 근사가 아니라 **항등식**).
   > 따라서 `L^reach` 는 협력 가치의 **보수적** 하한이고 (COOP certificate 는 그대로
   > sound), `U^rel_{<=N} < θ` 는 **차단 채널에 한한** 불가능만 지지한다.
   - **negative claim 시 `via the static blockade channel` 강제** (docs/74 §3.4·§5-1B·§7).
   - **사전 예측 등재** (docs/74 §3.0.3): 채널 (i) 은 `r_kill≈0.75` 에서 0, `≈3.0` 에서
     발현 → 지도는 `kappa` 축을 따라 구조를 가질 것. 낮은 `kappa` `p_INF` 지배 예상.
     **[E] pilot 에서 이 예측을 먼저 확인한다.** 빗나가도 정의는 안 바꾼다 (§7).
   - 부분 실증: `kappa = r_kill/rho` 가 core 축이므로 **"채널을 강화해도 안 열린다"**
     는 보일 수 있다 (채널 *종류*가 아니라 *세기*에 대한 강건성). 종류에 대한 일반화 불가.
2. **τ anchor 문헌 1 편** (docs/76 §6-10 을 **우선순위 2 로 승격**):
   우주 tethered-net 전개시간 모델 또는 공개 C-UAS 의 sense→decide latency.
   - 성공 시: τ 가 "저자가 고른 값" → **문헌 bracket** 이 되고 `chi` 축 전체의 지위가
     바뀐다. desk-reject 문장(docs/73 §4)의 가장 큰 항목이 빠진다.
   - 실패해도 진행 가능 — 그때는 "requirement" 금지(docs/74 §6) 유지.

### [C] 게이트 9 — 독립 judge cross-check
- cone containment · witness kill · threshold feasibility 를 **독립 구현**으로 재계산.
- 판정: **signed geometric margin** 비교 `|m1 − m2| ≤ eps` (1e-6 m / 무차원 1e-9).
  predicate 불일치는 `|m| ≤ eps` 인 boundary case 에서만 허용,
  **boundary 에서 먼 불일치 1 건이면 지도 중단·버그 감사.**
- 신규 파일 제안: `shepherd/scripts/judge_crosscheck.py`.

### [D] 게이트 6 — unblockable bad mass = cheap screen
- bad path witness `j` 의 blocker tube `B_j = gamma_j ⊕ Ball(r_kill)`.
  `B_j ∩ D = ∅` 이면 어떤 배치로도 못 지운다 → `v_max ≤ G/(G+U)`.
- **같은 코드가 docs/74 §3.1 의 전 스텝 sound screen** 이다:
  `screen(e,t) = 1[U^cheap_{≤N}(e,t) ≥ θ]`, screen=0 이면 `C_N=0` 보장(false negative 불가).
- soundness unit test 필수 (값이 약한 것은 실패가 아니다).
- 신규 파일 제안: `shepherd/scripts/cert_unblockable.py`.

### [E] ★ coarse pilot — 분기 판정
- 구현: `shepherd/scripts/coarse_pilot.py` (선언 = 모듈 docstring 1~5. 전 스텝 스캔 +
  해석적 교전 pre-screen — stride 아님). **본실행은 서버 샤딩** (셀당 1 ep ≈ 1.5~2 분):
  ```bash
  # 40 셀 x 20 ep -> 4 샤드 (tmux + ntfy, long-run policy)
  python -m shepherd.scripts.coarse_pilot --episodes 20 --cells 0:10  --out results/phase3/coarse_pilot_0_10.json
  python -m shepherd.scripts.coarse_pilot --episodes 20 --cells 10:20 --out results/phase3/coarse_pilot_10_20.json
  python -m shepherd.scripts.coarse_pilot --episodes 20 --cells 20:30 --out results/phase3/coarse_pilot_20_30.json
  python -m shepherd.scripts.coarse_pilot --episodes 20 --cells 30:40 --out results/phase3/coarse_pilot_30_40.json
  ```
- `Z_master` 부분집합(core 2D slice, N ∈ {1, 4}) × 에피소드 20~30.
- 계산은 **[D] 상한 + 값싼 constructive 하한**만. 라벨 5 종의 **prevalence** 보고
  (`p_FREE / p_SINGLE / p_COOP / p_INF / p_AMB`) — **단일 색 지도 금지**.
- **읽는 법** (★ cheap 도구 한계: `U^rel_{<=1}` 이 없으므로 **p_COOP 는 구조적으로 0**
  — COOP 신호는 `p_coop_candidate` (1 구 후보 불가 & N 구 constructive 가능) 로 읽고,
  확정은 [F] 게이트 7 이후):
  - `p_COOP > 0` 인 셀 존재 → 분기 정상, [F] 로 (그 좌표에 비싼 계산 집중)
  - `p_INF` 지배 → 분기 ①-B (negative systems result 가능)
  - `p_SINGLE` 지배 + COOP 부재 → 분기 ①-A
  - **`p_AMB` 지배 → 분기 ①-C = 결론 없음.** solver 고도화가 아니라 **문제 정의 단순화**
    가 정답 (docs/75 리스크 3). 여기서 6 개월 태우지 말 것.
- pilot 결과로 **정의·축·measure·선택규칙을 바꾸지 않는다** (docs/74 §7).

### [F]~[H] 이후
docs/75 §1 게이트 7·4·5·8 → 10 → 12 → 13 → 14 → 15 → 16·17 → 18 → 19 그대로.
Stage-2 는 `theta_S2 = 0.90` 고정 · 동일 N · matched control(normalized L∞) ·
primary = `Gamma = δ_COOP − (δ_FREE+δ_HARD)/2`, 성공 = `LCB95(Gamma) > 0`.

---

## 3. 매 산출물 규칙 (어기면 무효)

```python
from shepherd.scripts.pivot_manifest import stamp
out.update(stamp(artifact="...", lattice_hash="bd9ffa741d7b79ee"))
```
`protocol_hash · code_commit · judge_commit · scenario_manifest_hash · map_spec_hash ·
lattice_hash · generated_at` — **하나라도 없으면 그 artifact 는 결과로 쓰지 않는다.**

금지 (docs/74 §7): 결과 본 뒤 정의·격자·축·measure·선택규칙·반증조건 수정 /
Phase II 산출물을 confirmatory 인용 / docs/71 블록 재해석 / **감사 태그 이동** /
시간(12/18)을 이유로 bar 낮추기 / `L^ctrl` 을 fixed-state sandwich 에 넣기.

---

## 4. 알려진 함정 2 개 (지도에서도 재발한다 — 매번 확인)

1. **informative 희석** — 접근 초반 원거리 상태는 어떤 설정에서도 `v_shot = 0` 이라
   자명하게 일치한다. 그대로 통계에 넣으면 **게이트가 공짜 통과**(실측: median 이
   0.0020 → 0.00008 로 25 배 희석). 판정은 `0 < v < 1` 인 상태에서.
2. **봉쇄 비활성** — `n_t`(경로 서브스텝)·dogleg family 는 **kill 구 봉쇄 판정에만**
   쓰인다. 아무것도 안 막는 배치에서 변이를 재면 정확히 0 이 나와 **변이가 공허**해진다.
   → 반드시 **부분 봉쇄가 활성인 배치**(현 probe: 공칭 경로 옆 `1.2·r_kill`, blocked
   평균 0.59)에서 함께 판정. 산출물의 `blocked_frac` 을 항상 같이 찍는다.
   - 실패 이력(재현 금지): 공격자 중심 정사면체 → blocked 0% / 경로 위 정확히 →
     blocked 100% → `boxed_in` 으로 `v=1.0` 인공값.
3. (기록) `seg_1` 변이는 witness 내용이 바뀌는데도(endpoint 해시 상이) 점수 변화가
   정확히 0 이었다 — 테스트 상태에서 dogleg witness 가 비율을 못 바꿨다는 뜻.
   **dogleg family 가중 자체를 코드 수정 없이 바꿀 수 없다**는 한계를 산출물에 남길 것.

---

## 5. 병렬 트랙 (Phase III 와 섞지 않는다)

- **서버 MARL 9 런**: 완주 → `analyze_ls_commit` 1 회 → **기존 primary·기존 라벨**로만
  판정. 인용은 *"motivated, but does not validate"* · Phase III 는
  *"mechanism-consistent explanation"* 까지만 (docs/74 §6).
- **KSAS 추계 초록**: docs/75 §6 구조. 금지 문장 3 개 — "결정대역은 36–39 였다" /
  "1 기면 충분함을 발견" / "MARL 실패 원인은 전개지연".
- **OSF 외부 timestamp**: `artifacts/pivot_lock_2026-08-09.json` (r3.2) 업로드.
  남은 유일한 감사 미완 항목.

---

## 6. 빠른 참조 (명령어)

```bash
# 게이트 1 재생성 (격자·Π)
python -m shepherd.scripts.lattice_spec --out artifacts/phase3/lattice_spec.json
# 게이트 2·3
python -m shepherd.scripts.measure_harness --episodes 30 --stride 5 \
    --out results/phase3/measure_harness.json
# 계약 테스트
python -m pytest tests/test_phase3_gates.py tests/test_eval_iid.py -q
# manifest 재봉인 (계약 파일을 고쳤을 때만. 태그는 새 이름으로)
python -m shepherd.scripts.pivot_manifest --out artifacts/pivot_lock_2026-08-09.json
git tag -a PIVOT_LOCK_R33_2026-08-09 -m "..."      # ★ 기존 태그 이동 금지
```
