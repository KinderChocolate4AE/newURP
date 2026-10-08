# 2026-10-08c — **P-ρ2 등록** (E7-b 학습 착수 전 완료): ρ* = 2.81 (4dt 판정선) / 2.43 (3.5dt 이산화 하한), V̄ = 23.01 m/s (세계 스펙 고정)

K1 보조 세션 유도안 (`2026-10-08_P-rho2_rho_star_derivation_k1_session.md` — 본 폴더로
이관) 을 main 이 판정·등록. **docs/129 P-ρ2 의 "E7-b 전 경계 등록" 조건 충족 — 무플래그.**

## 1. 등록 문장 (확정)

> P-ρ2: FS1 se3_cone robust 판정에서, **shell 통과 encounter 조건부** robust 창 tick 수
> 중앙값이 4 이상이 되는 경계는 ρ* = (secθ + tanθ) / (1 − 4·dt·V̄/R_max). **V̄ = 23.01 m/s**
> (세계 스펙 `physics.att_speed` — FS1 경계 cell 고정값, runtime 조회; 선택 자유도 없는
> 유일 순항속도 상수; apex ≈ 정지 가정 = finisher station-keeping) 에서 **ρ\* = 2.813**
> (4dt 판정선) / **2.427** (3.5dt 이산화 허용 하한). 창 폭은 N = N∞·(1 − ρ₀/ρ) 형상
> (1/ρ 선형, **ρ₀ = secθ + tanθ = 1.238 에서 연속 개방**, N∞ = R_max/(V̄·dt) = 7.15 tick)
> 을 따른다.

## 2. main 판정 메모

- **채택 근거**: 유도가 콘 기하 + 구 포함 조건만으로 닫힘 (ρ₀ = secθ + tanθ — 세 몫 분해
  명시), 가정 8개 + 민감도 방향 표기 (A4 포탑 lag 이 최대 민감: dρ₀/dδ = 4.75/rad),
  tick 이산화 근거 (중앙값 ≥ 4 ⇔ T ≥ 3.5dt) 명시. 무결성 메모 자발 공개 포함.
- **V̄ 고정의 정직성**: 공식·E7-a 지도를 본 뒤의 고정이지만, att_speed 는 세계 스펙의
  유일 순항속도 상수라 **선택 자유도가 행사되지 않음** (fin v_max 도 23.01 이나 apex 는
  station-keeping 근사 — A6/A4 가 방향 커버).
- **(d) ma 역효과 유도 = 사후 노출 취급** (보조 세션 자진 신고: git log 헤드라인에 "ma aim
  hurts" 노출). 대칭성 논증 자체는 독립적으로 건전하나 blind 지위는 (a)~(c) 만.
- **겹쳐 그리기 시 metric 주의 (main 몫)**: E7-a probe.json 의 창 중앙값은 **전 ep (창 0
  포함) per-ep 총 robust step** — 등록 모집단 (shell 통과 encounter 조건부, chord 단위)
  과 다름. 머니 커브 overlay 전에 rows.npz 에서 조건부 중앙값을 재계산해야 공정 비교.
  이 재계산은 등록 후 수행 (등록값 변경 불가).
- 참고 (등록과 무관, 사후 관찰): 등록 ρ* = 2.81 은 E7-a 관측 열림 구간 (ρ 2.94 닫힘 ~
  3.93 열림 — 단 위 metric 불일치 상태) 과 같은 자릿수 — 정식 대조는 overlay 재계산에서.

## 3. 처리

- 유도 원문 이관: `temp_research_note/2026-10-08_P-rho2_rho_star_derivation_k1_session.md`
  (보조 세션 산출, repo 밖 임시 폴더 소멸 대비).
- E7-b addendum 에 등록 문장 §1 인용 + overlay 재계산 task 포함 예정.
