# 77 — Phase III 실행 워크플로 (다른 세션에서 그대로 이어받는 문서) — 2026-08-09

**이 문서 하나로 다음 세션이 대화 없이 이어갈 수 있게 쓴다.**
계약 정본 = `docs/74` r3.2 · 판정 로그 = `docs/73` r3.2 · 청사진 = `docs/75` v3.1 ·
선행연구 = `docs/76` v2. 이 문서는 **실행 순서와 명령어**만 담는다.

- 봉인: `PIVOT_LOCK_R32_2026-08-09` · `protocol_hash 069cade39836cdd1`
- 격자: `lattice_hash bd9ffa741d7b79ee` (Z_master 8415 점)
- **Phase III 지도 셀 = 0 개** (아직 지도 없음)

---

## 0. 지금 상태 (2026-08-09 기준)

| 항목 | 상태 |
|---|---|
| 게이트 1 (Z_master + Π 선봉인) | ✅ `artifacts/phase3/lattice_spec.json` |
| 게이트 2·3 (measure 수렴/allocation) | 🔄 **수정판 재실행 중** (30 ep · stride 5) → `results/phase3/measure_harness.json` |
| 게이트 2·3 1 차 (probe 없음) | ✅ PASS, 감사 보존 `results/phase3/measure_harness_v1_noprobe.json` |
| 서버 MARL 9 런 (Phase I ablation) | 🔄 진행 중 · **미열람** |
| scope 선언 · τ anchor · OSF timestamp | ❌ 미완 (§2 에 배치) |

**1 차 실측 (참고, 수정판으로 대체 예정)**: `V_hold` 8k→32k median 0.0020 / p95 0.0058
(기준 0.02/0.05) · allocation worst p95 0.0088 (기준 0.05) · 결정 뒤집힘 0 ·
informative 78/2129 (3.7%).

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
1. **scope 선언 한 줄** — `docs/74 §3.0` 신설(정의부 **맨 앞**):
   > 이 envelope 는 **kill-sphere 기반 회피집합 봉쇄라는 단일 협력 채널**에 대한 것이다.
   > 채널이 하나인 것은 결과가 아니라 **scope 선언**이며, COOP 셀 부재는 "협력이
   > 불가능하다" 가 아니라 "이 채널에서 협력이 certifiably 필요한 영역이 없다" 로만
   > 읽는다. (결과 후에 붙이면 변명이 된다 — **셀 생성 전에** 넣는다.)
   - 부분 실증: `kappa = r_kill/rho` 가 core 축이므로 **"채널을 강화해도 안 열린다"**
     는 보일 수 있다 (채널 종류가 아니라 세기에 대한 강건성).
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
- `Z_master` 부분집합(core 2D slice, N ∈ {1, 4}) × 에피소드 20~30.
- 계산은 **[D] 상한 + 값싼 constructive 하한**만. 라벨 5 종의 **prevalence** 보고
  (`p_FREE / p_SINGLE / p_COOP / p_INF / p_AMB`) — **단일 색 지도 금지**.
- **읽는 법**:
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
