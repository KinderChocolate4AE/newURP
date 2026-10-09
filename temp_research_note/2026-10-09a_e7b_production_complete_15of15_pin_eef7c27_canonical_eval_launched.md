# 2026-10-09a — E7-b 생산 완료 (15/15 rc=0, pin `eef7c27`) · 정본 평가 발사 (server4 tmux e7b)

## 1. 생산 완료 (JAX 보고 — main 세션 부재로 파일 경유 전달)

- 10-08 12:17–22:06, server4 GPU0 (4090) 1장. ckpt 15 + judge exploiter 15, 총 2.3 GB,
  경로 `server4:/data/hjhong/fs1jax/e7b/<variant>/s<seed>/`. jseed = 277000 + vi·1000 + seed.
- **pin `eef7c27`** (newURP-jax, 존재 확인) = `5d19d24` 미러 + 보조 ratio 통계 허용치
  1e-4 → 5e-4. 근거 수치: server4 (glibc 2.31) torch-XLA ratio 차 1.7e-4 (0.98049 vs 0.98032,
  `test_ppo_update_matches_torch[def-0.05-5-8192]`). 계약 (b) 기준 (params max|Δ| ≤ 1e-4, 상대 Δ
  ≤ 1e-2) 은 변경 없이 통과. parity 34/35 (실패 1 = golden 바이트 가드, 기존 기록) + 가드형
  f32 McNemar PASS (worst |z| 2.138) + 비기본 1변형 f64 step-exact.
- **BC 래퍼 (재현 근거)** `server4:/data/hjhong/fs1jax/runs/bc_variant.py` — 정본
  `shepherd.fs1.bc` 무수정, `B.FS1Spec = functools.partial(FS1Spec, tau_scale, theta_scale, aim)`
  만 교체 후 `B.main(argv)`. 호출 `bc_variant.py TAU THETA AIM --out <slot>/bc --episodes 3000
  --workers 8 --seed <seed> --stack r4p --mu 0.35 --nu 1.0`. spawn 워커는 부모의 spec.__dict__
  를 받으므로 변형 필드 전달됨. (`__main__` 가드 = 첫 발사 spawn 재귀 사건의 교정.)

## 2. train-side 최종 (판정 아님 — 확률 정책)

| 변형 | 방어 승률 시작 → 최종 | 최종 NET 비율 | 착취자 최종 관통 (s0/s1/s2) |
|---|---|---|---|
| t0.7_h1.0_cv | ~.79 → .48–.53 | 48–51% | .87 / .92 / .93 |
| t0.7_h1.5_cv | ~.76 → .42–.60 | 44–58% | .92 / .94 / .93 |
| t0.5_h1.0_cv | ~.53 → .47–.53 | 46–50% | .87 / .94 / .92 |
| t0.5_h1.5_cv | ~.53 → .53–.57 | 51–55% | .89 / .87 / .86 |
| t0.5_h1.0_ma | ~.55 → .46–.52 | 45–50% | .89 / .84 / .90 |
| (참고) 현행 세계 m0.35 | ~.34 → .09–.20 | 3–14% | .97–.99 |

- 15 slot 중 7 이 관통 ≤ .90. 착취자 출발 .27–.60 → 수렴 .84–.94 — "0.05 → 0.99" 서명 소멸.
- τ0.7 은 공진화로 하락 후 안정, τ0.5 는 하락 거의 없음. AUC .98–.99, lab_pos ~0.9–1.1%.
- ma 조준이 착취자 관통 최저 (.84–.90) 이나 cv 와의 차이는 seed 산포 안 — 효과 주장 보류.
  (E7-a 프로브에서는 ma 가 창을 줄였음 — 정본에서 방향 확인 필요.)

## 3. 정본 평가 발사

- 산출물이 이미 server4 에 있어 strip·전송 생략 (strip 은 전송용 절차였음).
- runner `scripts/run_fs1_e7b_eval.sh` + readout `scripts/fs1_e7b_readout.py` (`eeba1d3`):
  15 slot × {learned_det (판정), learned_sto, fin12_fb, kfirst50 (scripted 전이 참조)} vs ex_judge,
  240판 paired, seed0 = 276000 + vi·1000, 변형 플래그 + `--coop-window`. readout 은 meta 의 변형
  플래그가 manifest 변형과 일치하는지 검사 (불일치 = slot 무효).
- smoke (t0.5_h1.0_ma/s0, 4판, 판정 시드대 밖 280000): 변형 플래그·coop·d_shot 기록 정상.
- **발사 12:44, server4 tmux `e7b`.** 완료 신호 = origin "harvest E7-b canonical eval
  (manifest 543cd9e4b3582687)".
