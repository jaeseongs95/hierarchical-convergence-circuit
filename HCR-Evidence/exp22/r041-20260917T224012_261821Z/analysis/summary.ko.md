# EXP-22 / R0.4.1 — 순열 불변성과 계산 효율의 분리

동일 topology 1 / 입력 순열 6 / scheduler 3 / native 실행 108 / readout 207
input_order: 기존 head, edge_id_min: ID 경로 최소값, edge_id_max: ID 경로 최대값.
입력·ID·관측·world·memory를 바꾸지 않고, 이미 생성된 frontier head만 공개 API로 이동한다.
S/M/D와 score·raw·정답을 scheduler에 주지 않는다. 첫 후보 pool은 변경하지 않는다.

## 최종 채택

| scheduler / prior / arm | 조건 | 정답 | 오답 | 보류 | native ticks |
|---|---:|---:|---:|---:|---:|
| input_order/legacy/native | 6 | 0 | 0 | 6 | 1020 |
| input_order/legacy/posthoc_support | 6 | 6 | 0 | 0 | 1020 |
| input_order/legacy/online_support | 6 | 6 | 0 | 0 | 816 |
| input_order/route_only/native | 6 | 6 | 0 | 0 | 1278 |
| input_order/route_only/posthoc_support | 6 | 6 | 0 | 0 | 1278 |
| input_order/route_only/online_support | 6 | 6 | 0 | 0 | 1278 |
| edge_id_min/legacy/native | 6 | 0 | 0 | 6 | 1020 |
| edge_id_min/legacy/posthoc_support | 6 | 6 | 0 | 0 | 1020 |
| edge_id_min/legacy/online_support | 6 | 6 | 0 | 0 | 612 |
| edge_id_min/route_only/native | 6 | 6 | 0 | 0 | 984 |
| edge_id_min/route_only/posthoc_support | 6 | 6 | 0 | 0 | 984 |
| edge_id_min/route_only/online_support | 6 | 6 | 0 | 0 | 984 |
| edge_id_max/legacy/native | 6 | 0 | 0 | 6 | 1020 |
| edge_id_max/legacy/posthoc_support | 6 | 6 | 0 | 0 | 1020 |
| edge_id_max/legacy/online_support | 6 | 6 | 0 | 0 | 1020 |
| edge_id_max/route_only/native | 6 | 6 | 0 | 0 | 1572 |
| edge_id_max/route_only/posthoc_support | 6 | 6 | 0 | 0 | 1572 |
| edge_id_max/route_only/online_support | 6 | 6 | 0 | 0 | 1572 |

## 불변성과 효율

| prior / arm | min/max ticks 범위 폭 | 두 고정 정책의 결과 일치 | min/max 평균 ticks | max−min 합계 | 관찰 |
|---|---|---|---|---:|---|
| legacy/native | 0/0 | True | 170.00/170.00 | 0 | invariant_same_outcome_equal_native_cost |
| legacy/posthoc_support | 0/0 | True | 170.00/170.00 | 0 | invariant_same_outcome_equal_native_cost |
| legacy/online_support | 0/0 | True | 102.00/170.00 | 408 | invariant_same_outcome_different_native_cost |
| route_only/native | 0/0 | True | 164.00/262.00 | 588 | invariant_same_outcome_different_native_cost |
| route_only/posthoc_support | 0/0 | True | 164.00/262.00 | 588 | invariant_same_outcome_different_native_cost |
| route_only/online_support | 0/0 | True | 164.00/262.00 | 588 | invariant_same_outcome_different_native_cost |

범위 폭 0은 이 여섯 순열의 비용 불변성이다. 적은 평균 비용·정확도·수렴 안정성과 동일하지 않다.
max−min은 같은 조건의 native ticks 차이이며 양수는 max 쪽이 더 많이 계산했다는 뜻이다.

## 기존 배열 의존 격차와 고정 scheduler

| prior / arm / 고정 정책 | 기존/고정 ticks 범위 폭 | 기존/고정 경로순서 종류 | 결과 유지 | 관찰 |
|---|---|---|---|---|
| legacy/native/edge_id_min | 0/0 | 2/1 | True | no_input_order_tick_gap |
| legacy/native/edge_id_max | 0/0 | 2/1 | True | no_input_order_tick_gap |
| legacy/posthoc_support/edge_id_min | 0/0 | 2/1 | True | no_input_order_tick_gap |
| legacy/posthoc_support/edge_id_max | 0/0 | 2/1 | True | no_input_order_tick_gap |
| legacy/online_support/edge_id_min | 68/0 | 2/1 | True | tick_gap_removed |
| legacy/online_support/edge_id_max | 68/0 | 2/1 | True | tick_gap_removed |
| route_only/native/edge_id_min | 98/0 | 2/1 | True | tick_gap_removed |
| route_only/native/edge_id_max | 98/0 | 2/1 | True | tick_gap_removed |
| route_only/posthoc_support/edge_id_min | 98/0 | 2/1 | True | tick_gap_removed |
| route_only/posthoc_support/edge_id_max | 98/0 | 2/1 | True | tick_gap_removed |
| route_only/online_support/edge_id_min | 98/0 | 2/1 | True | tick_gap_removed |
| route_only/online_support/edge_id_max | 98/0 | 2/1 | True | tick_gap_removed |

## 온라인 선택 시점

| scheduler / 순서 / prior | native / 사후 / 온라인 ticks | 차등 기회 | 사후−온라인 | 판정 |
|---|---:|---|---:|---|
| input_order/DMS/legacy | 170/170/170 | False | 0 | no_differential_opportunity_observed |
| input_order/DMS/route_only | 262/262/262 | False | 0 | no_differential_opportunity_observed |
| input_order/DSM/legacy | 170/170/170 | False | 0 | no_differential_opportunity_observed |
| input_order/DSM/route_only | 262/262/262 | False | 0 | no_differential_opportunity_observed |
| input_order/MDS/legacy | 170/170/170 | False | 0 | no_differential_opportunity_observed |
| input_order/MDS/route_only | 262/262/262 | False | 0 | no_differential_opportunity_observed |
| input_order/MSD/legacy | 170/170/102 | True | 68 | correct_output_preserving_tick_saving |
| input_order/MSD/route_only | 164/164/164 | False | 0 | no_differential_opportunity_observed |
| input_order/SDM/legacy | 170/170/102 | True | 68 | correct_output_preserving_tick_saving |
| input_order/SDM/route_only | 164/164/164 | False | 0 | no_differential_opportunity_observed |
| input_order/SMD/legacy | 170/170/102 | True | 68 | correct_output_preserving_tick_saving |
| input_order/SMD/route_only | 164/164/164 | False | 0 | no_differential_opportunity_observed |
| edge_id_min/DMS/legacy | 170/170/102 | True | 68 | correct_output_preserving_tick_saving |
| edge_id_min/DMS/route_only | 164/164/164 | False | 0 | no_differential_opportunity_observed |
| edge_id_min/DSM/legacy | 170/170/102 | True | 68 | correct_output_preserving_tick_saving |
| edge_id_min/DSM/route_only | 164/164/164 | False | 0 | no_differential_opportunity_observed |
| edge_id_min/MDS/legacy | 170/170/102 | True | 68 | correct_output_preserving_tick_saving |
| edge_id_min/MDS/route_only | 164/164/164 | False | 0 | no_differential_opportunity_observed |
| edge_id_min/MSD/legacy | 170/170/102 | True | 68 | correct_output_preserving_tick_saving |
| edge_id_min/MSD/route_only | 164/164/164 | False | 0 | no_differential_opportunity_observed |
| edge_id_min/SDM/legacy | 170/170/102 | True | 68 | correct_output_preserving_tick_saving |
| edge_id_min/SDM/route_only | 164/164/164 | False | 0 | no_differential_opportunity_observed |
| edge_id_min/SMD/legacy | 170/170/102 | True | 68 | correct_output_preserving_tick_saving |
| edge_id_min/SMD/route_only | 164/164/164 | False | 0 | no_differential_opportunity_observed |
| edge_id_max/DMS/legacy | 170/170/170 | False | 0 | no_differential_opportunity_observed |
| edge_id_max/DMS/route_only | 262/262/262 | False | 0 | no_differential_opportunity_observed |
| edge_id_max/DSM/legacy | 170/170/170 | False | 0 | no_differential_opportunity_observed |
| edge_id_max/DSM/route_only | 262/262/262 | False | 0 | no_differential_opportunity_observed |
| edge_id_max/MDS/legacy | 170/170/170 | False | 0 | no_differential_opportunity_observed |
| edge_id_max/MDS/route_only | 262/262/262 | False | 0 | no_differential_opportunity_observed |
| edge_id_max/MSD/legacy | 170/170/170 | False | 0 | no_differential_opportunity_observed |
| edge_id_max/MSD/route_only | 262/262/262 | False | 0 | no_differential_opportunity_observed |
| edge_id_max/SDM/legacy | 170/170/170 | False | 0 | no_differential_opportunity_observed |
| edge_id_max/SDM/route_only | 262/262/262 | False | 0 | no_differential_opportunity_observed |
| edge_id_max/SMD/legacy | 170/170/170 | False | 0 | no_differential_opportunity_observed |
| edge_id_max/SMD/route_only | 262/262/262 | False | 0 | no_differential_opportunity_observed |

## 비용·원자료·주장 범위

EXP21 원 raw와 일치한 기존 input_order/edge_id_min 대조: 72개.
전체 native ticks: 20070
Native finish proof nodes: 828
Scheduler inventory: {'decision_calls': 288, 'frontier_items_examined': 360, 'edge_id_reads': 252, 'key_comparisons': 72, 'priority_transitions': 36, 'priority_match_scans': 72}
온라인 selector: {'edge_checks': 189, 'gate_assumptions_checked': 360, 'path_checks': 90, 'proof_nodes_created': 144, 'proof_nodes_reused': 576, 'ranked_paths': 126}
사후 selector: {'edge_checks': 108, 'gate_assumptions_checked': 72, 'path_checks': 54, 'proof_nodes_created': 144, 'proof_nodes_reused': 0, 'ranked_paths': 99}
여기서 원인 분리는 고정 ID의 최소/최대 우선순위와 계산 결과의 관계에 한정한다.
두 ID 방향 모두 최적/학습된 정책이 아니다. 불변하지만 더 느린 결과도 유효한 실험 결과다.
min/max의 의미적 유불리를 미리 판정해 경로나 결과를 수정하지 않는다.
순서 효과·성능·예측에 맞는 방향은 audit 통과 조건이 아니다. 오답/보류/비용 증가도 보존한다.
Native ticks, 스케줄러 검사, selector/proof 생성 비용은 서로 다른 단위다. 합산하지 않는다.
미계측 native capture scan은 null이다. priority_match_scans는 모든 CPU 연산/시간을 뜻하지 않는다.
순열·prior·arm·scheduler·world·readout을 108개 독립 문제로 세지 않는다.
원 native 판단과 terminal adoption을 구분하고, raw 값 반전·관측 추가·학습·자동 retry를 하지 않는다.
D_DAG는 기록하지만 이 실험은 D축 조작이 아니다. 인간/LLM 내부 회로의 실증이 아니다.
계산 궤적 비교에서는 priority bookkeeping event_seq만 제외한다. 원문 event와 참조는 그대로 보존한다.
