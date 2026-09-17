# EXP-19 / R0.3.8 — proof 선택과 조기 종료의 분리

기본 입력 14 / fresh native 실행 84 / readout 125
기존 대조 8개 + 사전 정의한 신규 topology 6개. 2개 prior × 3개 실험군은 paired 조건이다.

## 최종 채택

| 입력군 / prior / 실험군 | trial | 정답 | 오답 | 보류 | readout 없음 | 미완성 종료 | native ticks |
|---|---:|---:|---:|---:|---:|---:|---:|
| all/legacy/native | 14 | 3 | 1 | 10 | 0 | 0 | 1733 |
| all/legacy/posthoc_support | 14 | 10 | 1 | 3 | 0 | 0 | 1733 |
| all/legacy/online_support | 14 | 10 | 1 | 3 | 0 | 0 | 1563 |
| all/route_only/native | 14 | 11 | 1 | 2 | 0 | 0 | 2140 |
| all/route_only/posthoc_support | 14 | 11 | 1 | 2 | 0 | 0 | 2140 |
| all/route_only/online_support | 14 | 11 | 1 | 2 | 0 | 0 | 2140 |
| baseline_control/legacy/native | 8 | 3 | 1 | 4 | 0 | 0 | 781 |
| baseline_control/legacy/posthoc_support | 8 | 4 | 1 | 3 | 0 | 0 | 781 |
| baseline_control/legacy/online_support | 8 | 4 | 1 | 3 | 0 | 0 | 781 |
| baseline_control/route_only/native | 8 | 5 | 1 | 2 | 0 | 0 | 896 |
| baseline_control/route_only/posthoc_support | 8 | 5 | 1 | 2 | 0 | 0 | 896 |
| baseline_control/route_only/online_support | 8 | 5 | 1 | 2 | 0 | 0 | 896 |
| new_topology/legacy/native | 6 | 0 | 0 | 6 | 0 | 0 | 952 |
| new_topology/legacy/posthoc_support | 6 | 6 | 0 | 0 | 0 | 0 | 952 |
| new_topology/legacy/online_support | 6 | 6 | 0 | 0 | 0 | 0 | 782 |
| new_topology/route_only/native | 6 | 6 | 0 | 0 | 0 | 0 | 1244 |
| new_topology/route_only/posthoc_support | 6 | 6 | 0 | 0 | 0 | 0 | 1244 |
| new_topology/route_only/online_support | 6 | 6 | 0 | 0 | 0 | 0 | 1244 |

보류/미관측/미완성 종료 열은 서로 배타적인 총합 항목이 아니다. 정답/오답/보류만 trial 수로 합산한다.
정답은 모든 선언 world에서 정답이라는 뜻이며 관측 지지와 별도로 평가했다.

## 선택 시점 paired 비교

| 입력 / prior | 차등 기회 발생 | 첫 view/전체 기준 trace/온라인 prefix 일치 | native/posthoc/online ticks | 절감 ticks | 온라인 종료 frontier | 판정 |
|---|---|---|---:|---:|---:|---|
| critical_missing/legacy | False | True/True/True | 66/66/66 | 0 | 0 | no_differential_opportunity_observed |
| critical_missing/route_only | False | True/True/True | 93/93/93 | 0 | 0 | no_differential_opportunity_observed |
| critical_zero/legacy | False | True/True/True | 66/66/66 | 0 | 0 | no_differential_opportunity_observed |
| critical_zero/route_only | False | True/True/True | 93/93/93 | 0 | 0 | no_differential_opportunity_observed |
| irrelevant_missing/legacy | False | True/True/True | 102/102/102 | 0 | 0 | no_differential_opportunity_observed |
| irrelevant_missing/route_only | False | True/True/True | 164/164/164 | 0 | 0 | no_differential_opportunity_observed |
| known_cut_missing/legacy | False | True/True/True | 169/169/169 | 0 | 0 | no_differential_opportunity_observed |
| known_cut_missing/route_only | False | True/True/True | 166/166/166 | 0 | 0 | no_differential_opportunity_observed |
| misleading_direction/legacy | False | True/True/True | 69/69/69 | 0 | 0 | no_differential_opportunity_observed |
| misleading_direction/route_only | False | True/True/True | 70/70/70 | 0 | 0 | no_differential_opportunity_observed |
| strong_positive/legacy | False | True/True/True | 69/69/69 | 0 | 0 | no_differential_opportunity_observed |
| strong_positive/route_only | False | True/True/True | 70/70/70 | 0 | 0 | no_differential_opportunity_observed |
| three_branch_l2_early/legacy | True | True/True/True | 136/136/102 | 34 | 1 | correct_output_preserving_tick_saving |
| three_branch_l2_early/route_only | False | True/True/True | 164/164/164 | 0 | 1 | no_differential_opportunity_observed |
| three_branch_l2_late/legacy | False | True/True/True | 136/136/136 | 0 | 0 | no_differential_opportunity_observed |
| three_branch_l2_late/route_only | False | True/True/True | 228/228/228 | 0 | 0 | no_differential_opportunity_observed |
| three_branch_l3_early/legacy | True | True/True/True | 170/170/102 | 68 | 1 | correct_output_preserving_tick_saving |
| three_branch_l3_early/route_only | False | True/True/True | 164/164/164 | 0 | 1 | no_differential_opportunity_observed |
| three_branch_l3_late/legacy | False | True/True/True | 170/170/170 | 0 | 0 | no_differential_opportunity_observed |
| three_branch_l3_late/route_only | False | True/True/True | 262/262/262 | 0 | 0 | no_differential_opportunity_observed |
| three_branch_l4_early/legacy | True | True/True/True | 170/170/102 | 68 | 1 | correct_output_preserving_tick_saving |
| three_branch_l4_early/route_only | False | True/True/True | 164/164/164 | 0 | 1 | no_differential_opportunity_observed |
| three_branch_l4_late/legacy | False | True/True/True | 170/170/170 | 0 | 0 | no_differential_opportunity_observed |
| three_branch_l4_late/route_only | False | True/True/True | 262/262/262 | 0 | 0 | no_differential_opportunity_observed |
| two_branch_cut/legacy | False | True/True/True | 165/165/165 | 0 | 0 | no_differential_opportunity_observed |
| two_branch_cut/route_only | False | True/True/True | 165/165/165 | 0 | 0 | no_differential_opportunity_observed |
| weak_negative/legacy | False | True/True/True | 75/75/75 | 0 | 0 | no_differential_opportunity_observed |
| weak_negative/route_only | False | True/True/True | 75/75/75 | 0 | 0 | no_differential_opportunity_observed |

차등 기회 = raw True + 완성된 관측 지지/activation 적격 경로 + 남은 frontier + native 보류.
기회가 발생하지 않은 경우에는 조기 종료 가설의 반증으로 처리하지 않는다.
절감 ticks = posthoc − online. 양수라도 출력/정답/prefix가 보존됐는지 함께 본다.

## 비용과 해석 범위

최종 누적 native ticks 합계: 11449
원 native finish가 만든 proof node: 533
온라인 selector 계측: {'edge_checks': 94, 'gate_assumptions_checked': 225, 'path_checks': 42, 'proof_nodes_created': 80, 'proof_nodes_reused': 391, 'ranked_paths': 55}
사후 selector 계측: {'edge_checks': 63, 'gate_assumptions_checked': 49, 'path_checks': 28, 'proof_nodes_created': 80, 'proof_nodes_reused': 25, 'ranked_paths': 44}
Native ticks, 경로/edge 검사, proof 생성/재사용은 다른 비용 단위다. 합산 총비용/전력 절감으로 해석하지 않는다.
Native capture 내부 미계측 scan은 null이다. 반복 readout 누적 ticks를 더하지 않는다.
Wall time에는 Python·직렬화·보존 비용이 포함된다. 반복 timing 실험이 아니므로 순수 속도 우위로 일반화하지 않는다.
검증 통과는 원자료·seed·상태·제어·proof·계수 정합성이다. 기회 발생/정답/개선을 통과 조건으로 삼지 않는다.
기존 R035 auditor의 supported_assumptions 명명 오류는 신규 보고에서 검사/지원/비지원 수로 분리했다. 기존 raw/analysis는 수정하지 않았다.
학습된 자율 repair, native kernel 교체, raw 값 반전, 외부 관측 요청, LLM/인간 뇌 검증은 포함하지 않는다.
