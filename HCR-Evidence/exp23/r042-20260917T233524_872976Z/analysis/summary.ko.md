# EXP-23 / R042 — ID와 경로 역할 분리

## 결론

관찰 분류: `supports_role_alignment_with_measured_trajectory_reversal`.
ID 재명명 후 min/max 비용 관계가 뒤집힌 순열: 6/6.
모든 4조건군 tick spread=0: True.
같은 순열의 4조건 모두 최종 결과 동일: True.
교차 scheduler의 측정된 canonical 궤적 동일: True.

## 관찰

| ID 배치 | Scheduler | 최소 tick | 최대 tick | Spread | 평균 tick |
|---|---|---:|---:|---:|---:|
| identity | edge_id_min | 102 | 102 | 0 | 102.00 |
| identity | edge_id_max | 170 | 170 | 0 | 170.00 |
| swap_SD | edge_id_min | 170 | 170 | 0 | 170.00 |
| swap_SD | edge_id_max | 102 | 102 | 0 | 102.00 |

## 해석과 대안 설명

배열 순열 불변성, ID 재명명 민감도, 절대 native 계산비용을 분리한다. min 자체의 일반적 우월성을 가정하지 않는다.
비용 관계가 역전되어도, 교차 scheduler의 inverse-ID 궤적과 초기 관측이 함께 대응하는지 comparisons.csv를 확인해야 한다.
pre_competitive_probe는 첫 경쟁 frontier와 그 이전 readout만 비교한다. 전체 초기 상태 동치의 증명은 아니다.
초기 probe 또는 교차 궤적이 다르면 scheduler 외 ID 영향도 설명 후보로 남는다.

## 검증과 실패의 구분

identity parent 회귀: 12/12. audit 성공은 반전/정답/불변성 성공을 뜻하지 않는다.
오답과 abstention은 결과로 보존한다. schema/reference/runtime 실패는 failure.json으로 분리하고 최초 실패에서 중단한다.

## 현재 주장 가능한 범위

고정된 toy topology 1개, ID 배치 2개, 배열 순열 6개, scheduler 2개의 24 paired 조건이다. 독립 문제 24개 또는 LLM 실험이 아니다.
D_DAG는 검산된 proof 의존 깊이이며 tick 수나 계산 단계 수로 대체하지 않는다.
native ticks, scheduler 작업량, selector 작업량, wall time을 별도로 보고한다. 전체 시간·전력 절감률을 주장하지 않는다.
raw ID와 inverse-ID 투영을 함께 보존하며 평가용 투영은 실행 state 또는 proof를 고치지 않는다.
