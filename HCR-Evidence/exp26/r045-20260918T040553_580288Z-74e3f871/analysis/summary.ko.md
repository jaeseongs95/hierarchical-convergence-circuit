# EXP-26 / R045 — 최종 지원 경로의 직접 회로 사용

## 결론

본 실험 12조건 / 회로 gate 6쌍. 주 분석은 supported_len2의 2쌍이며 ID 대조를 독립 문제 반복으로 세지 않는다.
아래 표는 사전 예측을 실제 기록에 적용한 결과다. 미적용·오답·보류는 보고하고, 효과를 audit 성공 조건으로 요구하지 않는다.

| 예측 | pair 지지 | pair 예측 실패 | 평가 불가 |
|---|---:|---:|---:|
| H_direct | 2 | 0 | 0 |
| H_expansion | 2 | 0 | 0 |
| H_kernel | 0 | 2 | 0 |
| H_decision_same | 0 | 2 | 0 |
| H_outcome | 2 | 0 | 0 |
| H_no_match | 2 | 0 | 0 |
| H_no_match_ticks | 2 | 0 | 0 |
| H_conflict_reject | 2 | 0 | 0 |
| H_conflict_no_false_positive | 2 | 0 | 0 |

## 관찰

| 조건 | ID | 직접 사용 ON | ON ticks | OFF ticks | Δpool | Δdecision | ON/OFF expansion |
|---|---|---|---:|---:|---:|---:|---|
| supported_len2 | identity | True | 67 | 33 | 34 | 0 | 1/2 |
| supported_len2 | fresh_ids | True | 67 | 33 | 34 | 0 | 1/2 |
| no_match_len1 | identity | False | 29 | 29 | 0 | 0 | 1/1 |
| no_match_len1 | fresh_ids | False | 29 | 29 | 0 | 0 | 1/1 |
| conflict_len2 | identity | None | 58 | 28 | 30 | 0 | 2/2 |
| conflict_len2 | fresh_ids | None | 58 | 28 | 30 | 0 | 2/2 |

## 해석

H_direct는 양성 채택 경로에 explicit circuit use가 기록됐는지를 본다. ON에 macro action이 있었다는 것만으로 직접 사용으로 세지 않는다.
H_expansion과 H_kernel은 직접 사용과 비검열 조건에서 각각 평가한다. H_decision_same은 decision program·drives와 모든 기록된 tick state의 서명이 같은지 비교하는 경쟁 설명의 예측이다.
결과가 다르거나 예산 종료인 pair의 비용도 삭제하지 않되, 같은 성능에서의 효율 향상으로 표현하지 않는다.

## 대안 설명과 판별 범위

single-path 입력은 경로 경쟁에 의한 우회를 제거한다. host가 실행 궤적을 고정하거나 회로 승자를 지정하지 않는다.
len1 미매칭 대조는 topology가 다른 별도 진단이다. len2와의 차이를 순수 matching 비용이나 D_DAG 인과효과라고 부르지 않는다.
conflict_len2는 같은 topology의 관측 하나만 반전한 정적 대조다. 실제 mismatch 거부, activation 거부, pool 미형성을 candidate_exposure.csv에서 구분한다. 같은 session의 수정·재학습 실험은 아니다.

## 현재 주장 가능한 범위

고정된 native toy 입력 2개 topology, 3개 관측 조건에서의 회로 지원 분기 총효과다. 학습 memory·config·scheduler·selector는 유지한다.
D_DAG는 독립 검산된 선택 proof 깊이다. path edge 수, expansion 수, kernel ticks와 동일시하지 않는다.
wall time은 별도 기록이며 energy·peak memory·최소 goal proof DAG 동형성은 null이다. pool/decision tick 차이는 관찰 비용 분해이지 pool을 제거한 반사실 실험이 아니다.
EXP25 부모 raw 재검산 및 native 회귀·self-test 결과는 새 연구 모집단에 합산하지 않는다.
