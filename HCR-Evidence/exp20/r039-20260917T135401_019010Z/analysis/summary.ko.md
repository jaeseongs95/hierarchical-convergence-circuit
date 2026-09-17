# EXP-20 / R0.3.9 — identity 고정 · 배열 순서 단독 조작

기준 topology 1 / 순열 6 / native 실행 36 / 실제 readout 69
S=지지 가지(e0,e1), M=관측 누락 가지(e2,e3), D=음의 관측 포함 가지(e4,e5,e6).
모든 node/edge/episode ID, 관계, score, world, memory, config를 고정하고 분기 블록 배열만 바꿨다.
observation digest와 내부 slot 번호는 순서에 따라 자연스럽게 달라진다. 이를 host가 고치지 않았다.

## 최종 결과

| prior / arm | 조건 수 | 정답 | 오답 | 보류 | native ticks |
|---|---:|---:|---:|---:|---:|
| legacy/native | 6 | 0 | 0 | 6 | 1020 |
| legacy/posthoc_support | 6 | 6 | 0 | 0 | 1020 |
| legacy/online_support | 6 | 6 | 0 | 0 | 816 |
| route_only/native | 6 | 6 | 0 | 0 | 1278 |
| route_only/posthoc_support | 6 | 6 | 0 | 0 | 1278 |
| route_only/online_support | 6 | 6 | 0 | 0 | 1278 |

정답은 모든 선언 world에서 정답이라는 뜻이다. Audit 통과 자체는 정답을 의미하지 않는다.

## 순열 내부 paired 비교

| 순서 / prior | 지지 경로 완성 순위(native) | 차등 기회 tick | native / 사후 / 온라인 ticks | 절감 ticks | 온라인 frontier | 판정 |
|---|---:|---:|---:|---:|---:|---|
| DMS/legacy | 3 | None | 170/170/170 | 0 | 0 | no_differential_opportunity_observed |
| DMS/route_only | 3 | None | 262/262/262 | 0 | 0 | no_differential_opportunity_observed |
| DSM/legacy | 3 | None | 170/170/170 | 0 | 0 | no_differential_opportunity_observed |
| DSM/route_only | 3 | None | 262/262/262 | 0 | 0 | no_differential_opportunity_observed |
| MDS/legacy | 3 | None | 170/170/170 | 0 | 0 | no_differential_opportunity_observed |
| MDS/route_only | 3 | None | 262/262/262 | 0 | 0 | no_differential_opportunity_observed |
| MSD/legacy | 2 | 102 | 170/170/102 | 68 | 1 | correct_output_preserving_tick_saving |
| MSD/route_only | 2 | None | 164/164/164 | 0 | 1 | no_differential_opportunity_observed |
| SDM/legacy | 2 | 102 | 170/170/102 | 68 | 1 | correct_output_preserving_tick_saving |
| SDM/route_only | 2 | None | 164/164/164 | 0 | 1 | no_differential_opportunity_observed |
| SMD/legacy | 2 | 102 | 170/170/102 | 68 | 1 | correct_output_preserving_tick_saving |
| SMD/route_only | 2 | None | 164/164/164 | 0 | 1 | no_differential_opportunity_observed |

차등 기회: raw True + activation 적격 완성 지지 경로 + 남은 frontier + native 보류.
절감 = 사후군 native ticks − 온라인군 native ticks. 같은 정답, prefix, 기준 trace 정합성을 함께 본다.
기회가 없으면 조기 종료를 판별하지 못한 결과이다. 효과 없음/오답/보류도 삭제하지 않는다.

## 배열 순서 효과

| prior / arm | ticks 최소~최대 | 전개 순서 종류 | 최종 결과 불변 | ticks 차이 관찰 |
|---|---:|---:|---|---|
| legacy/native | 170~170 | 2 | True | False |
| legacy/posthoc_support | 170~170 | 2 | True | False |
| legacy/online_support | 102~170 | 2 | True | True |
| route_only/native | 164~262 | 2 | True | True |
| route_only/posthoc_support | 164~262 | 2 | True | True |
| route_only/online_support | 164~262 | 2 | True | True |

ID가 고정된 조건에서 차이가 생기면 이번 범위의 배열 순서 효과다. ID가 무관하다거나 ID 효과의 크기를 측정했다는 뜻은 아니다.
모든 순열이 같아도 검증 실패가 아니다. 최종 결과 불변과 중간 경로/시점 불변은 분리한다.

## 비용·출처·주장 범위

전체 native ticks: 6690
원 native finish proof nodes: 276
온라인 selector: {'edge_checks': 63, 'gate_assumptions_checked': 120, 'path_checks': 30, 'proof_nodes_created': 48, 'proof_nodes_reused': 192, 'ranked_paths': 42}
사후 selector: {'edge_checks': 36, 'gate_assumptions_checked': 24, 'path_checks': 18, 'proof_nodes_created': 48, 'proof_nodes_reused': 0, 'ranked_paths': 33}
서로 다른 비용 단위를 더해 전체 속도/전력 절감으로 표현하지 않는다. 미계측 scan은 null이다.
최초/후속 readout의 누적 ticks를 중복 합산하지 않는다. 평가 재생 비용은 task 비용이 아니다.
추가 학습·관측 요청·raw 값 반전·prior 전환·새 controller 학습을 하지 않았다.
같은 1개 topology의 6개 배열과 2 prior × 3 arm을 독립 표본 36개로 세지 않는다.
D_DAG와 선택 경로를 기록하지만, 경로 길이나 D축을 조작한 실험이 아니다.
input_isolation은 입력 개입을, records의 order_diagnostics는 ID 대응된 경로/activation을 기록한다.
