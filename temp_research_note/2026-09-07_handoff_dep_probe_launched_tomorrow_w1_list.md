# 2026-09-07 — 핸드오프: dep-probe 서버 투입 준비 완료 (140판, ~2h) + 내일 W1 목록

세션 마감 기록. R2b 종결·등록·docs/89 r4 판올림 완료 상태 (당일 노트 2편 참조).

## 오늘 밤 서버 (사용자 실행, ~2h)

plan-level multi-limiter dependence probe (closure r4 §10.4 카드, **실행 전
봉인 커밋 29bc681**). descriptive — necessity ablation 아님.

```bash
cd /data/hjhong/l2/newURP && source .venv-l2/bin/activate && git pull
python -m shepherd.scripts.r2b_c_dep_probe --smoke     # s=2001 배선 재확인
for K in 0 1 2 3 4 5 6 7; do
  tmux new-session -d -s r2bdep$K \
    "python -m shepherd.scripts.r2b_c_dep_probe --run --shard $K --n-shards 8"
done
```

산출 = `artifacts/r2b/c_dep_probe/shard00..07.json` (140 records: 셀별 C_N=1 ∧
accels 앞 5판 × replay 9종). 중단 시 재실행 = resume. ntfy 8건이면 완료.

- **smoke n=1 미리보기 (해석 금지, 기록만)**: s=2001 은 solo[2] 단독 재현 +
  loo[2] 실패 → multi_dependent=0 (solo-sufficient). 협력 어휘 복권에 불리한
  방향의 첫 witness — 140판 비율이 결정.

## 내일 (W1 D1, 9/8) 목록 — 의존 순서

1. **(사용자)** KSAS 형식 마감 착수 (G1, Track W).
2. **dep-probe 회수 + 판독** (아침이면 완료돼 있음) — solo_any / multi_dependent
   / loo 비율 표. **이 결과가 3번의 설계를 결정한다**: multi_dependent 비율이
   낮으면 (단독 기회 지배) "협력 복권" 캠페인 (C_single) 은 접고 단독-기회
   서사로 — 그것도 docs/89 에 무손상 (학습 문제는 "어느 limiter 를 어떻게
   움직일지"로 여전히 성립). 높으면 C_single/C_comp 계약 설계 가치 상승.
3. **(조건부) C_single necessity ablation 계약 초안** — dep-probe 판독 후.
   설계 원칙: 문서 먼저 → 외부 감사 1회 → 봉인 → 서버 (심야 졸속 봉인 금지 —
   late-seal 감사 지적 재발 방지). budget 공정성 (per-j 예산 vs C 의 384) 이
   핵심 쟁점.
4. docs/92 층1 민감도 후보 목록 확정 (W1 항목).
5. B0 v3 초안 선행 (docs/89 r4 §5 — 13항 R_rec 포함, W2 항목 선행).
6. H-4 (랩서버 torch venv) + docs/91 Q3 (NET_SPENT 이벤트 실재 확인) — 위험
   1·2 조기 해소.
7. **(사용자)** Crazyflie 발주 안건 (10/18 한) — W2 교수 미팅 전 준비.

## 상태 스냅샷

- R2b: 종결·등록 (C047~C049) 완료. 정본 = closure 브리프 r4. 계획 정본 =
  docs/89 **r4** (오늘 판올림 — W1 핵심 선행 완료 체크). docs/86~93 은 untracked
  유지 (사용자 패턴 존중 — 커밋 원하면 지시).
- 뷰어: http://127.0.0.1:8777/trajectory_viewer_r2b_c.html (서버 프로세스 로컬
  가동 중; 재부팅 시 viz/ 에서 `python -m http.server 8777`).
- 최근 커밋 29bc681. branch feat/scale-up-v2.
