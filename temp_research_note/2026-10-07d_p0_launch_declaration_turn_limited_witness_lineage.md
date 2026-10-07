# 2026-10-07d — P0 발사 선언 (결과 전): turn-limited witness = 별도 계보, 기준·특징·집계 고정

사용자 ② 결재 (2026-10-07, docs/126 §6) 에 따라 P0a/P0b 착수. 본 노트가 **결과 전 선언**
(스크립트 `scripts/fs1_p0_fidelity_probe.py` + 러너 `run_fs1_p0_probe.sh`, 실행 = server4).

## P0a — 판정-모델 변형 선언

- witness 변형: `attacker_turn_limited=True` (viability.py 기구현 경로, params
  `viability.turn_limited` RESERVED 의 소생). **계보 w_bk / w8 로 명명 — 기존 isotropic
  계보 (1.5a·phase2·pilot) 와 pooling 금지.** 비발사 프로브라 rollout 동역학은 witness
  조회와 무관 → 세 계보는 같은 tick 에서 paired 로만 비교.
- **ω primary (w_bk) = backend slew 실측값** (runtime 조회, 기대 10.0; docs/103 §dead-param
  감사). 근거: witness ⊇ 실제 공격자 기동이어야 보장-포획 **하한** 의미론이 유지됨.
  ω=8.0 (w8) = params dead 등재값, 감도 secondary 로만 보고.
- 프로토콜: 1.5a 와 동일 (SEED0=268000, 3 cell × 4 적응 공격자 = 12 slot, 24 ep,
  발사 금지, 창 = LOADED ∧ d≤16). 1.5a 와의 bit-identity 는 주장하지 않음 (참조만).
- **사전 기준 (docs/126 그대로 + 집계 고정)**: slot 별 "ep 당 robust step 수 (worst≥1 ∧
  ¬boxed, 창 0 ep 포함, 24 ep)" 의 중앙값 → **12 slot 중앙값들의 중앙값 ≥ 4 step (0.2 s),
  계보 w_bk** → `AXIS3_VALID` (③축 유효 = "net 보강 없이 학습 가능 영역" 후보), 미달 →
  `AXIS3_NULL`. max 연속 run 중앙값은 병기 보고 (판정엔 불사용).
- wiring 자기검증: 직접 `V.v_shot` 호출 (turn off) 이 `inn._vshot` 과 bit-exact 임을
  slot 당 3 tick assert — 통과 못 하면 run 전체 무효.

## P0b — 창 감지 회귀 선언

- 같은 rollout 의 window tick. **label primary = robust_base (기존 계보)**, secondary =
  robust_w_bk. 특징 7 = d, closing (fin 방향 접근속도), p_feasible(base), limiter-att
  거리 4 (정렬). 로지스틱 (numpy IRLS, L2 1e-3), **ep 짝=train / 홀=test** (ep 단위 누수
  방지), slot 별 AUC + pooled 는 보고용.
- 기술 문턱 (게이트 아님, arm C ①/② 배분 참고): slot AUC 중앙값 ≥ 0.8 → "감지 가능성
  높음" (arm C-① 증류 충분 쪽), 미달 → 창 생성 비중↑ 쪽. **arm C 자체는 ③ 게이트 사슬
  미결재 상태 — P0b 는 입력 준비일 뿐 착수 승인 아님.**

## 운영

- server4 `.venv-l2`, tmux `p0`, BLAS 1스레드. harvest = origin 커밋
  "science(fs1): harvest P0 fidelity probe". 발사 전 `--eps 2` smoke (pin dry-run 유사 —
  wiring assert 가 여기서 걸림). 산출 = `artifacts/fs1/p0/probe.json` + `rows.npz`
  (per-tick rows — P0b 재분석·viz 용).
- viz-first: harvest 후 rows.npz 로 창 타임라인 (base vs w_bk) 시각화 먼저, 수치 해석은
  그 다음.
