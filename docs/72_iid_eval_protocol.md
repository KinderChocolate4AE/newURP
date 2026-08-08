# 72 — IID 대역 paired 평가 프로토콜 (headline + docs/71 ablation 공용) — 동결

**2026-08-08/09 · docs/71 r1 비준 직후, LS-off 결과가 하나도 나오기 전에
평가 규약을 먼저 잠근다. 구현 = `shepherd/scripts/eval_iid.py` +
`shepherd/scripts/analyze_ls_commit.py`, 잠금 = `tests/test_eval_iid.py`
(P72a~g).**

## 1. 잠금 문장 (원문 — 이것이 계약이다)

> **training seed 는 policy replication 을 식별하고, IID episode ID 는 world
> replication 을 식별한다. 두 축은 독립이며 동일 IID episode 는 모든 arm ×
> training-seed 평가에서 bit-identical world draw 를 생성한다.**

## 2. 구현된 규약

| 축 | 값 | 코드 |
|---|---|---|
| world namespace | `build_m4_env(seed=0, episode=ep, threat_layer="iid")` — 고정 master seed 0, `ep` 이 draw identity | `eval_iid.EVAL_WORLD_SEED` |
| simulation RNG | `run_episode(seed=ep)` (controller 비의존) | `eval_iid.eval_episodes` |
| policy identity | `(arm, training_seed)` — ckpt 로만 들어온다 | `eval_iid._policy_runner` |
| policy 표본추출 RNG | `torch.manual_seed(POLICY_RNG_BASE + ep)`, base 700_000_000 (학습 namespace 와 분리) | 같음 |
| 대역 | **headline = iid 10000..10299**, **ablation = iid 10300..10599** — 그 외 대역은 거부 | `eval_iid.BANDS` |
| regime | rollout **전에** world spec 에서 `regime_of(a_att, tau, net_radius)`. 결과로 재계산 금지 | `eval_iid.eval_episodes` |
| p_net | `NET_CAPTURE + CAPTURE_WITH_CONTACT` — 정의는 `m4_env.label_rates` 한 군데 | `label_rates` |
| confirmatory seeds | `(1, 2, 3, 4)` 상수. `INDEX_SEED = 0` 은 primary CI 에서 제외 | `analyze_ls_commit` |
| bootstrap | 최상위 = training seed 재표집, 그 안에서 **paired** episode 재표집. 시드 간 pooling 금지. B=10000, rng(7) | `analyze_ls_commit._boot` |
| 판정식 | **two-sided 95% CI 하한 > 0** (one-sided 95% 하한도 병기) | `primary()` |

### 2.1 판정식 해석 고지 (docs/71 §1.2 문구 해소)

docs/71 은 "seed-resampled 95% bootstrap confidence-interval lower bound" 라고만
적었고 two-sided 2.5% 하한인지 one-sided 5% 하한인지 명시하지 않았다.
**더 보수적인 two-sided 95% CI 하한(2.5 분위)을 판정식으로 채택**하고,
리포 기존 관례(`analyze_gate_a`)의 one-sided 95% 하한은 함께 보고만 한다.
이 선택은 결과 열람 전에 코드로 고정됐다.

## 3. 산출 provenance (파일 하나로 자기증명)

`arm · band · training_seed · action_profile ("accel3+commit" / "accel3" /
"scripted") · limiter_commit · eval_layer · eval_world_seed · episode_start/end ·
shard_offset/shard_n/shard_complete · distribution_hash · world_contract_hash ·
train_contract_hash · checkpoint_hash · checkpoint_steps · policy_rng_base ·
git_head · counts · label_rates · by_regime · rows[]`

`rows[]` 각 행에 **`world_hash`** (episode 별 world 정체성: threat draw +
attacker/spawn/standby + cell) 를 싣는다 — 두 팔의 같은 행이 같은 world 였는지
사후에 증명된다. contract hash 는 분포 참조까지만 보므로 이 열이 따로 필요하다.

## 4. 판정 금지 조건 (예외를 던진다 — 조용히 넘어가지 않는다)

- 같은 episode 의 두 팔 `world_hash` 불일치 → paired 무효
- 같은 episode 의 두 팔 `regime` 불일치 → pre-treatment 라벨 위반
- 대역 불완전 (샤드 누락 / 중복 / 대역 외 episode)
- confirmatory seed {1,2,3,4} 중 하나라도 두 팔 평가 부재 → 9 런 완주 전 판정 금지

## 5. 실행 순서 (docs/71 §2 승인 순서)

1. `pytest tests/test_m4_wiring.py -k p71` (LS-off 잠금 4항) + `tests/test_eval_iid.py`
2. LS-off smoke (`smoke_v3_train --config configs/l2_mappo_nocommit.yaml`)
3. `pytest tests/test_contract_parity.py tests/test_arc_baseline.py`
   → **1~3 GREEN 후에만** LS-off 학습 착수 (LS-live seeds 1..4 는 1~3 GREEN 시 착수 가능)
4. 9 런 (LS-live 1..4 · LS-off 0..4), 곡선 중간 중단·재선택 없음
5. 전 런 완주 후 **일괄** IID 평가 10 정책 (`eval_iid`, 샤딩 허용)
6. `analyze_ls_commit` 1 회 → seed0 은 index 블록으로 병기, primary = seeds 1..4

```bash
# 5) 정책 팔 (서버). 샤딩 예: 300 판을 4 샤드로
python -m shepherd.scripts.eval_iid --arm ls-live --training-seed 1 \
    --policy-checkpoint results/m4_v3_train_LS/seed1 \
    --episode-start 10300 --episodes 300 --shard-offset 0 --shard-n 75 \
    --device cuda --out results/iid_abl/ls-live_seed1_s0.json
python -m shepherd.scripts.eval_iid --arm ls-off --training-seed 1 \
    --config configs/l2_mappo_nocommit.yaml \
    --policy-checkpoint results/m4_v3_train_LS_off/seed1 \
    --episode-start 10300 --episodes 300 --device cuda \
    --out results/iid_abl/ls-off_seed1.json
# 6) primary
python -m shepherd.scripts.analyze_ls_commit --eval-dir results/iid_abl \
    --out results/iid_abl/primary_delta_shape.json
```

## 6. 미결 (열지 않은 것)

- headline 대역(10000..10299) 재평가는 이 러너로 **가능**하지만 docs/63 headline
  수치를 대체하지 않는다 — 별도 판단 없이 돌리지 않는다.
- hold / arc(c5) 팔의 ablation 대역 평가는 참조용(문맥 floor)이며 primary 식에
  들어가지 않는다. 돌릴 경우에도 Δ_shape 정의는 LS-off − LS-live 그대로다.
