# EXP-10 — R0.2.1 중단·복원·재개 비교

현재 실행이 만든 개발 검증 기록이다. EXP-09의 새 연구 표본이 아니다.

동작 동등성: True

| 조건 | 비교 | 판단·proof·카운터 | 관측 | memory | engine 이벤트 |
|---|---|---|---|---|---|
| budget | legacy/continuous | True | True | True | True |
| budget | legacy/resumed | True | True | True | True |
| main | legacy/continuous | True | True | True | True |
| main | legacy/resumed | True | True | True | True |
| no_reexpansion | legacy/continuous | True | True | True | True |
| no_reexpansion | legacy/resumed | True | True | True | True |
| unknown | legacy/continuous | True | True | True | True |
| unknown | legacy/resumed | True | True | True | True |

## 그대로 보존한 판단

| 조건 | 사례 | 시도 | 출력 | 정답 | primitive D | tick | 확장 |
|---|---|---:|---|---|---:|---:|---:|
| budget | budget | 1 | None | None | None | 0 | 1 |
| main | familiar | 1 | True | True | 3 | 69 | 2 |
| main | counterfactual | 1 | False | True | 2 | 96 | 2 |
| main | longer | 1 | True | True | 4 | 105 | 2 |
| main | branch | 1 | True | True | 2 | 64 | 1 |
| main | weak_conflict | 1 | True | False | 3 | 75 | 1 |
| main | same_score_revision | 2 | False | True | 2 | 39 | 3 |
| main | retention | 1 | True | False | 3 | 88 | 2 |
| no_reexpansion | disabled_revision | 1 | True | False | 3 | 75 | 1 |
| unknown | unknown | 1 | None | None | None | 59 | 2 |

## 검증 범위

legacy는 현재 AdaptiveEngine.infer, continuous는 같은 진행 API의 중단 없는 session, resumed는 각 전이 뒤 실제 JSON 저장·복원을 수행한다.
pool과 판단 settle은 한 dependency step 안에서 완료된다. 임의 tick 중단이나 background cognition을 구현한 실험이 아니다.
cost.wall_seconds는 실제 계산 구간의 누적 시간이며 디스크 대기·세션 복사·검산 비용은 포함하지 않는다. checkpoint_io.jsonl에서 저장/복원 관리 비용(검산·직렬화 포함)을 따로 읽는다.
오수렴·다른 부분회로 재선택·same-score 우회 정답은 동작 보존 대상이다. 이를 정답률 개선으로 집계하지 않는다.
feedback은 generator의 외부 world 평가에서 생성된다. session 자체에는 hidden truth를 넣지 않는다.
