# LS-off 배선 + IID 평가 프로토콜 동결 — 서버 GREEN 대기 (학습 미착수)

**2026-08-08/09 · docs/71 r1 비준·동결 후 핸드오프 세션. 구현만 했다 —
학습 런 0, 결과 0. docs/72 신설(평가 규약 동결).**

## 한 일

1. **LS-off 배선** (docs/71 §0.1④): `cfg.limiter_commit=False` 면 limiter live
   dims = `LIVE_DIMS(0,1,2)` 프로파일 → `pad_env_action` 이 idx3(commit)=0 을
   결정적으로 주입. 어댑터 3곳 + 평가 패딩 + `lim_scale`(3축) 이 한 프로파일로
   움직인다. `summary.json` 에 `limiter_commit` 키.
   commit head 는 원래부터 부재였다 (mappo.py:312 GaussianActor) — 이 커밋이
   고친 것은 **env 프로파일이 무조건 commit-live 였던 불일치**다.
2. **config**: `configs/l2_mappo_nocommit.yaml` = l2_mappo.yaml + 한 줄
   (yaml diff 0 을 테스트가 검증).
3. **§2.1 잠금 4항** (p71a~d, torch mark): env 수신 commit==0(학습·평가) ·
   logp = 3축 Normal 그 자체 · entropy 이산항 없음 + commit 진단키 부재 ·
   연속 mean MLP 초기값/클립/스케일 = LS-live 동일.
4. **IID paired 평가 러너** `eval_iid.py` + **primary 판정기**
   `analyze_ls_commit.py` + 잠금 `tests/test_eval_iid.py`(P72a~g, 9 통과).
   규약 = docs/72. 핵심: world = (seed 0, episode) 뿐 / policy = (arm,
   training_seed) / 두 축 독립 / 대역은 선언된 둘만 / regime 은 rollout 전
   pre-treatment / confirmatory seeds (1,2,3,4) 상수 · index seed 0 배제 /
   bootstrap 최상위 = training seed + nested paired (pooling 금지).
   판정식 = **two-sided 95% CI 하한 > 0** (docs/71 §1.2 의 "95% CI 하한"
   중의성을 보수적으로 해소, 결과 열람 전 고정).

## 검증 상태 (정직)

- 로컬 full suite: 551 passed / 1 failed(**기존** `test_fire_audit::p63c` —
  torch 부재 환경 기지 실패) / 64 skipped(torch mark).
- p71b~d 는 **로컬 미실행** (torch 없음) → 서버 GREEN 이 LS-off 학습의 전제.
- `eval_iid` 는 scripted 팔(hold/arc)로만 로컬 실측 (10300~10302, 3판) —
  정책 팔 경로는 서버 첫 실행이 처음이다.
- 부수 관찰: 서브셋으로 pytest 를 돌리면 `test_p40*` 3건이 실패한다.
  원인은 내 변경이 아니라 `tests/test_a3e.py` 가 심는 가짜 torch 스텁 순서
  의존성(conftest 주석에 이미 기록된 그 함정) — 전체 실행 시 통과.

## 다음 (docs/72 §5 순서 그대로)

1~3 서버 GREEN → LS-live seeds 1..4 + LS-off seeds 0..4 (9런, tmux 샤딩) →
전 런 완주 후 **일괄** IID 10300..10599 평가 → `analyze_ls_commit` 1회.

금지선 재확인: 곡선 보고 중단·재선택 · 결과 본 뒤 대역/판정식 변경 ·
LS-off 성공 시에도 headline 교체 (docs/71 §3).
