# EXP-29 / R048 — 관측 강도와 초기 상태의 수치 정밀도

## 결론

모집단: `research`. A 14개 공유, B 98조건. 독립 무작위 반복은 없습니다.
실제 A 상태와 fixed 0.99의 비교는 아래 전체 조건에 대해 그대로 보고합니다. 잘못된 결과나 미적용을 효율 개선으로 세지 않습니다.

## A source의 가용성

| 관측 강도 | ID | raw | 채택 | 정답 채택 | ticks | 재사용 가능 |
|---|---|---|---|---|---:|---|
| 0.02 | identity | False | False | False | 88 | False |
| 0.02 | fresh_ids | False | False | False | 88 | False |
| 0.1 | identity | True | True | True | 54 | True |
| 0.1 | fresh_ids | True | True | True | 54 | True |
| 0.25 | identity | True | True | True | 35 | True |
| 0.25 | fresh_ids | True | True | True | 35 | True |
| 0.5 | identity | True | True | True | 33 | True |
| 0.5 | fresh_ids | True | True | True | 33 | True |
| 0.75 | identity | True | True | True | 33 | True |
| 0.75 | fresh_ids | True | True | True | 33 | True |
| 0.92 | identity | True | True | True | 33 | True |
| 0.92 | fresh_ids | True | True | True | 33 | True |
| 1.0 | identity | True | True | True | 33 | True |
| 1.0 | fresh_ids | True | True | True | 33 | True |

## 관찰: 실제 상태 대 고정값

| 강도 | ID | mask | actual | fixed | 차이 | 비교 가능 | 제외가 아닌 미판정 사유 |
|---|---|---|---:|---:|---:|---|---|
| 0.02 | identity | edge | 88 | 88 | 0 | False | A_not_correct_positive_adoption, initialization_not_applied, actual_B_not_correct_adoption, fixed_B_not_correct_adoption |
| 0.02 | identity | prefix | 88 | 88 | 0 | False | A_not_correct_positive_adoption, initialization_not_applied, actual_B_not_correct_adoption, fixed_B_not_correct_adoption |
| 0.02 | identity | both | 88 | 88 | 0 | False | A_not_correct_positive_adoption, initialization_not_applied, actual_B_not_correct_adoption, fixed_B_not_correct_adoption |
| 0.02 | fresh_ids | edge | 88 | 88 | 0 | False | A_not_correct_positive_adoption, initialization_not_applied, actual_B_not_correct_adoption, fixed_B_not_correct_adoption |
| 0.02 | fresh_ids | prefix | 88 | 88 | 0 | False | A_not_correct_positive_adoption, initialization_not_applied, actual_B_not_correct_adoption, fixed_B_not_correct_adoption |
| 0.02 | fresh_ids | both | 88 | 88 | 0 | False | A_not_correct_positive_adoption, initialization_not_applied, actual_B_not_correct_adoption, fixed_B_not_correct_adoption |
| 0.1 | identity | edge | 41 | 38 | 3 | True |  |
| 0.1 | identity | prefix | 37 | 37 | 0 | True |  |
| 0.1 | identity | both | 30 | 29 | 1 | True |  |
| 0.1 | fresh_ids | edge | 41 | 38 | 3 | True |  |
| 0.1 | fresh_ids | prefix | 37 | 37 | 0 | True |  |
| 0.1 | fresh_ids | both | 30 | 29 | 1 | True |  |
| 0.25 | identity | edge | 33 | 33 | 0 | True |  |
| 0.25 | identity | prefix | 31 | 31 | 0 | True |  |
| 0.25 | identity | both | 29 | 29 | 0 | True |  |
| 0.25 | fresh_ids | edge | 33 | 33 | 0 | True |  |
| 0.25 | fresh_ids | prefix | 31 | 31 | 0 | True |  |
| 0.25 | fresh_ids | both | 29 | 29 | 0 | True |  |
| 0.5 | identity | edge | 33 | 33 | 0 | True |  |
| 0.5 | identity | prefix | 31 | 31 | 0 | True |  |
| 0.5 | identity | both | 29 | 29 | 0 | True |  |
| 0.5 | fresh_ids | edge | 33 | 33 | 0 | True |  |
| 0.5 | fresh_ids | prefix | 31 | 31 | 0 | True |  |
| 0.5 | fresh_ids | both | 29 | 29 | 0 | True |  |
| 0.75 | identity | edge | 33 | 33 | 0 | True |  |
| 0.75 | identity | prefix | 31 | 31 | 0 | True |  |
| 0.75 | identity | both | 29 | 29 | 0 | True |  |
| 0.75 | fresh_ids | edge | 33 | 33 | 0 | True |  |
| 0.75 | fresh_ids | prefix | 31 | 31 | 0 | True |  |
| 0.75 | fresh_ids | both | 29 | 29 | 0 | True |  |
| 0.92 | identity | edge | 33 | 33 | 0 | True |  |
| 0.92 | identity | prefix | 31 | 31 | 0 | True |  |
| 0.92 | identity | both | 29 | 29 | 0 | True |  |
| 0.92 | fresh_ids | edge | 33 | 33 | 0 | True |  |
| 0.92 | fresh_ids | prefix | 31 | 31 | 0 | True |  |
| 0.92 | fresh_ids | both | 29 | 29 | 0 | True |  |
| 1.0 | identity | edge | 33 | 33 | 0 | True |  |
| 1.0 | identity | prefix | 31 | 31 | 0 | True |  |
| 1.0 | identity | both | 29 | 29 | 0 | True |  |
| 1.0 | fresh_ids | edge | 33 | 33 | 0 | True |  |
| 1.0 | fresh_ids | prefix | 31 | 31 | 0 | True |  |
| 1.0 | fresh_ids | both | 29 | 29 | 0 | True |  |

## 사전 가설 전체 판정

| 조건 | 처리 | 가설 | 판정 |
|---|---|---|---|
| s00__identity | carry_edge | H_gate | supported |
| s00__identity | carry_prefix | H_gate | supported |
| s00__identity | carry_both | H_gate | supported |
| s00__identity | fixed_edge | H_gate | supported |
| s00__identity | fixed_prefix | H_gate | supported |
| s00__identity | fixed_both | H_gate | supported |
| s00__identity | edge | H_precision_at_cell | not_evaluable |
| s00__identity | edge | H_outcome_at_cell | supported |
| s00__identity | prefix | H_precision_at_cell | not_evaluable |
| s00__identity | prefix | H_outcome_at_cell | supported |
| s00__identity | both | H_precision_at_cell | not_evaluable |
| s00__identity | both | H_outcome_at_cell | supported |
| s00__fresh_ids | carry_edge | H_gate | supported |
| s00__fresh_ids | carry_prefix | H_gate | supported |
| s00__fresh_ids | carry_both | H_gate | supported |
| s00__fresh_ids | fixed_edge | H_gate | supported |
| s00__fresh_ids | fixed_prefix | H_gate | supported |
| s00__fresh_ids | fixed_both | H_gate | supported |
| s00__fresh_ids | edge | H_precision_at_cell | not_evaluable |
| s00__fresh_ids | edge | H_outcome_at_cell | supported |
| s00__fresh_ids | prefix | H_precision_at_cell | not_evaluable |
| s00__fresh_ids | prefix | H_outcome_at_cell | supported |
| s00__fresh_ids | both | H_precision_at_cell | not_evaluable |
| s00__fresh_ids | both | H_outcome_at_cell | supported |
| s01__identity | edge | H_precision_at_cell | falsified |
| s01__identity | edge | H_outcome_at_cell | supported |
| s01__identity | prefix | H_precision_at_cell | falsified |
| s01__identity | prefix | H_outcome_at_cell | supported |
| s01__identity | both | H_precision_at_cell | falsified |
| s01__identity | both | H_outcome_at_cell | supported |
| s01__fresh_ids | edge | H_precision_at_cell | falsified |
| s01__fresh_ids | edge | H_outcome_at_cell | supported |
| s01__fresh_ids | prefix | H_precision_at_cell | falsified |
| s01__fresh_ids | prefix | H_outcome_at_cell | supported |
| s01__fresh_ids | both | H_precision_at_cell | falsified |
| s01__fresh_ids | both | H_outcome_at_cell | supported |
| s02__identity | edge | H_precision_at_cell | falsified |
| s02__identity | edge | H_outcome_at_cell | supported |
| s02__identity | prefix | H_precision_at_cell | falsified |
| s02__identity | prefix | H_outcome_at_cell | supported |
| s02__identity | both | H_precision_at_cell | falsified |
| s02__identity | both | H_outcome_at_cell | supported |
| s02__fresh_ids | edge | H_precision_at_cell | falsified |
| s02__fresh_ids | edge | H_outcome_at_cell | supported |
| s02__fresh_ids | prefix | H_precision_at_cell | falsified |
| s02__fresh_ids | prefix | H_outcome_at_cell | supported |
| s02__fresh_ids | both | H_precision_at_cell | falsified |
| s02__fresh_ids | both | H_outcome_at_cell | supported |
| s03__identity | edge | H_precision_at_cell | falsified |
| s03__identity | edge | H_outcome_at_cell | supported |
| s03__identity | prefix | H_precision_at_cell | falsified |
| s03__identity | prefix | H_outcome_at_cell | supported |
| s03__identity | both | H_precision_at_cell | falsified |
| s03__identity | both | H_outcome_at_cell | supported |
| s03__fresh_ids | edge | H_precision_at_cell | falsified |
| s03__fresh_ids | edge | H_outcome_at_cell | supported |
| s03__fresh_ids | prefix | H_precision_at_cell | falsified |
| s03__fresh_ids | prefix | H_outcome_at_cell | supported |
| s03__fresh_ids | both | H_precision_at_cell | falsified |
| s03__fresh_ids | both | H_outcome_at_cell | supported |
| s04__identity | edge | H_precision_at_cell | falsified |
| s04__identity | edge | H_outcome_at_cell | supported |
| s04__identity | prefix | H_precision_at_cell | falsified |
| s04__identity | prefix | H_outcome_at_cell | supported |
| s04__identity | both | H_precision_at_cell | falsified |
| s04__identity | both | H_outcome_at_cell | supported |
| s04__fresh_ids | edge | H_precision_at_cell | falsified |
| s04__fresh_ids | edge | H_outcome_at_cell | supported |
| s04__fresh_ids | prefix | H_precision_at_cell | falsified |
| s04__fresh_ids | prefix | H_outcome_at_cell | supported |
| s04__fresh_ids | both | H_precision_at_cell | falsified |
| s04__fresh_ids | both | H_outcome_at_cell | supported |
| s05__identity | edge | H_precision_at_cell | falsified |
| s05__identity | edge | H_outcome_at_cell | supported |
| s05__identity | prefix | H_precision_at_cell | falsified |
| s05__identity | prefix | H_outcome_at_cell | supported |
| s05__identity | both | H_precision_at_cell | falsified |
| s05__identity | both | H_outcome_at_cell | supported |
| s05__fresh_ids | edge | H_precision_at_cell | falsified |
| s05__fresh_ids | edge | H_outcome_at_cell | supported |
| s05__fresh_ids | prefix | H_precision_at_cell | falsified |
| s05__fresh_ids | prefix | H_outcome_at_cell | supported |
| s05__fresh_ids | both | H_precision_at_cell | falsified |
| s05__fresh_ids | both | H_outcome_at_cell | supported |
| s06__identity | edge | H_precision_at_cell | falsified |
| s06__identity | edge | H_outcome_at_cell | supported |
| s06__identity | prefix | H_precision_at_cell | falsified |
| s06__identity | prefix | H_outcome_at_cell | supported |
| s06__identity | both | H_precision_at_cell | falsified |
| s06__identity | both | H_outcome_at_cell | supported |
| s06__fresh_ids | edge | H_precision_at_cell | falsified |
| s06__fresh_ids | edge | H_outcome_at_cell | supported |
| s06__fresh_ids | prefix | H_precision_at_cell | falsified |
| s06__fresh_ids | prefix | H_outcome_at_cell | supported |
| s06__fresh_ids | both | H_precision_at_cell | falsified |
| s06__fresh_ids | both | H_outcome_at_cell | supported |
| 0.02 | cold | H_ID_native | supported |
| 0.02 | carry_edge | H_ID_native | supported |
| 0.02 | carry_prefix | H_ID_native | supported |
| 0.02 | carry_both | H_ID_native | supported |
| 0.02 | fixed_edge | H_ID_native | supported |
| 0.02 | fixed_prefix | H_ID_native | supported |
| 0.02 | fixed_both | H_ID_native | supported |
| 0.1 | cold | H_ID_native | supported |
| 0.1 | carry_edge | H_ID_native | supported |
| 0.1 | carry_prefix | H_ID_native | supported |
| 0.1 | carry_both | H_ID_native | supported |
| 0.1 | fixed_edge | H_ID_native | supported |
| 0.1 | fixed_prefix | H_ID_native | supported |
| 0.1 | fixed_both | H_ID_native | supported |
| 0.25 | cold | H_ID_native | supported |
| 0.25 | carry_edge | H_ID_native | supported |
| 0.25 | carry_prefix | H_ID_native | supported |
| 0.25 | carry_both | H_ID_native | supported |
| 0.25 | fixed_edge | H_ID_native | supported |
| 0.25 | fixed_prefix | H_ID_native | supported |
| 0.25 | fixed_both | H_ID_native | supported |
| 0.5 | cold | H_ID_native | supported |
| 0.5 | carry_edge | H_ID_native | supported |
| 0.5 | carry_prefix | H_ID_native | supported |
| 0.5 | carry_both | H_ID_native | supported |
| 0.5 | fixed_edge | H_ID_native | supported |
| 0.5 | fixed_prefix | H_ID_native | supported |
| 0.5 | fixed_both | H_ID_native | supported |
| 0.75 | cold | H_ID_native | supported |
| 0.75 | carry_edge | H_ID_native | supported |
| 0.75 | carry_prefix | H_ID_native | supported |
| 0.75 | carry_both | H_ID_native | supported |
| 0.75 | fixed_edge | H_ID_native | supported |
| 0.75 | fixed_prefix | H_ID_native | supported |
| 0.75 | fixed_both | H_ID_native | supported |
| 0.92 | cold | H_ID_native | supported |
| 0.92 | carry_edge | H_ID_native | supported |
| 0.92 | carry_prefix | H_ID_native | supported |
| 0.92 | carry_both | H_ID_native | supported |
| 0.92 | fixed_edge | H_ID_native | supported |
| 0.92 | fixed_prefix | H_ID_native | supported |
| 0.92 | fixed_both | H_ID_native | supported |
| 1.0 | cold | H_ID_native | supported |
| 1.0 | carry_edge | H_ID_native | supported |
| 1.0 | carry_prefix | H_ID_native | supported |
| 1.0 | carry_both | H_ID_native | supported |
| 1.0 | fixed_edge | H_ID_native | supported |
| 1.0 | fixed_prefix | H_ID_native | supported |
| 1.0 | fixed_both | H_ID_native | supported |

## 해석과 대안 설명

음수 Δticks는 actual이 더 적은 native ticks를 썼다는 뜻입니다. 실제 A와 B가 올바르게 채택되고 gate가 적용된 경우에만 효율 비교를 해석합니다.
A가 양성 채택에 실패한 조건도 B 7군을 모두 실행했습니다. gate 거부 후 같아진 cold 궤적을 초기값 정밀도의 동등성 증거로 사용하지 않습니다.
0.92 조건은 이미 알려진 EXP-28 대조점입니다. 이전 6개 H_source_specificity 실패를 소급 수정하거나 새 독립 증거로 세지 않습니다.
서로 다른 궤적이 같은 ticks로 종료할 수 있습니다. checkpoints.csv는 실제 양쪽에 존재하는 시점만 비교하고, 조기 종료 후의 상태를 복제하거나 계산을 연장하지 않습니다.
관측 강도 변화가 만드는 동역학의 차이는 관찰 대상입니다. 임계 구간, attractor, 의미적 메커니즘에 관한 원인은 추가 판별 없이 확정하지 않습니다.

## 비용과 주장 범위

동일 block 안에서는 A/B의 공유 근거 score와 binding을 유지합니다. 추가 B edge는 0.92로 고정합니다. 모든 world edge는 별도로 True로 고정하고 runtime에 전달하지 않았습니다.
native ticks, group updates, signals, dependency/descriptor 검사, bytes, wall time을 분리합니다. native/bridge proof 수는 같은 생성 작업의 별칭이므로 더하지 않습니다.
모든 처리에서 전체 A packet을 사용하는 기존 구현입니다. partial-mask 저장량 최적화, 전송 최소화, source 계산 생략을 시험하지 않았습니다.
wall time에는 기록·fsync 비용이 포함됩니다. 에너지와 peak memory는 null이며 실행시간·전력 절감을 주장하지 않습니다.
고정 잠재 연결 공간, 가소성, 학습된 Circuit 경쟁, 자연어 문맥 이해, 전체 HCC lifecycle은 이번 실험 대상이 아닙니다.

## 다음 판별 실험

이번에 동결한 전 범위의 Δticks와 정확도·채택·가용성을 함께 본 뒤 다음 질문을 정합니다. 유리한 강도만 남기거나 fixed 값을 사후 조정하지 않습니다.
