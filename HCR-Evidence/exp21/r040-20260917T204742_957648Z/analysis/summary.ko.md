# EXP-21 / R0.4.0 — frontier scheduling 개입

동일 topology 1 / 입력 순열 6 / scheduler 2 / native 실행 72 / readout 135
input_order는 기존 삽입 순서, edge_id_min은 이미 등록된 frontier 중 edge-ID 경로 tuple 최소값을 선택한다.
입력 자체를 정렬하지 않고 공개 prioritize_frontier API만 호출한다. score/world/raw를 scheduler에 주지 않는다.
전체 frontier를 미리 정렬하거나 첫 후보 pool 정책을 변경한 실험이 아니다.

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

## 순열 사이의 격차

| prior / arm | 기존 ticks 범위 폭 | ID-min ticks 범위 폭 | 기존/ID-min 경로순서 종류 | 최종 결과 유지 | 관찰 |
|---|---:|---:|---|---|---|
| legacy/native | 0 | 0 | 2/1 | True | no_input_order_tick_gap |
| legacy/posthoc_support | 0 | 0 | 2/1 | True | no_input_order_tick_gap |
| legacy/online_support | 68 | 0 | 2/1 | True | tick_gap_removed |
| route_only/native | 98 | 0 | 2/1 | True | tick_gap_removed |
| route_only/posthoc_support | 98 | 0 | 2/1 | True | tick_gap_removed |
| route_only/online_support | 98 | 0 | 2/1 | True | tick_gap_removed |

## 같은 scheduler 안의 온라인/사후 선택 비교

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

## 비용·정합성·주장 범위

EXP20 원 raw와 일치한 input_order 대조: 36개.
전체 native ticks: 12294
Native finish proof nodes: 540
Scheduler inventory: {'decision_calls': 180, 'frontier_items_examined': 216, 'edge_id_reads': 144, 'key_comparisons': 36, 'priority_transitions': 18, 'priority_match_scans': 36}
온라인 selector: {'edge_checks': 111, 'gate_assumptions_checked': 240, 'path_checks': 54, 'proof_nodes_created': 96, 'proof_nodes_reused': 384, 'ranked_paths': 72}
사후 selector: {'edge_checks': 72, 'gate_assumptions_checked': 48, 'path_checks': 36, 'proof_nodes_created': 96, 'proof_nodes_reused': 0, 'ranked_paths': 63}
Scheduler 검사/비교/native priority scan은 별도 inventory 단위이다. native ticks에 더하지 않는다.
priority_match_scans는 기존 API의 경로 일치 검사 횟수이며 딥카피·직렬화·모든 CPU 연산을 포괄하지 않는다.
ID 정렬이 이 고정 문제에서 지지 경로를 앞세워도 최적/학습된 탐색 정책으로 해석하지 않는다.
격차 감소/소실은 이 개입 범위의 원인 분리를 지지한다. 남은 pool/slot/수치 효과까지 제거했다고 단정하지 않는다.
배열 순서 효과 없음, 보류, 오답, 개선 없음도 보존한다. audit 통과 조건은 계약/원자료/독립 재생의 일치이다.
입력 identity와 관측을 고정하며 새 학습·관측 요청·raw 값 반전·자동 retry는 하지 않는다.
미계측 비용은 null이다. 전력/전체 실행시간 절감, D축 검증, 인간/LLM 내부 회로 검증을 주장하지 않는다.
order_effects의 계산 궤적은 priority로 달라진 event_seq를 제외하지만 경로/expansion/activation/ticks를 보존한다.
개별 priority 원자료와 generation 참조는 records 및 scheduler_decisions.csv에 보존한다.
