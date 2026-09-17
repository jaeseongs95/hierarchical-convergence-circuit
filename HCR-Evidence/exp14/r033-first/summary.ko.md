# EXP-14 / R0.3.3 — 근거 기반 재검토·추가 전개·선택적 관측

관측은 모의 환경의 요청별 score 응답이다. 실제 센서·LLM 실험이 아니다.
최초 판단을 공유하고 분기하므로 rollout 수를 독립 과제 수/추론 수로 합산하지 않는다.
expand_only는 기존 prior/proof 선택을 그대로 둔다. 추가 경로를 만들고도 실패할 수 있다.
route_review는 명시적 route_only 전체 재계산이며 그 비용을 전부 합산한다.
supported는 방향성 지지 계약이며 외부 정답을 보증하지 않는다.

기준 추론 16 / 추가 session 시작 33 / 학습 6 / rollout 142
실제 task tick: 기준 1643 + 추가 2957 = 4600

| 그룹 / 초기 정책 / 개입 | 정답 | 오답 | 보류 | 출력 회복 | 추가 advance | 추가 tick | 관측 |
|---|---:|---:|---:|---:|---:|---:|---:|
| main/legacy/expand_only | 5 | 1 | 7 | 0 | 2 | 68 | 0 |
| main/legacy/expand_then_observe | 11 | 1 | 1 | 6 | 12 | 525 | 6 |
| main/legacy/hold | 5 | 1 | 7 | 0 | 0 | 0 | 0 |
| main/legacy/observe_first | 11 | 1 | 1 | 6 | 10 | 457 | 6 |
| main/legacy/route_review | 8 | 1 | 4 | 3 | 9 | 775 | 0 |
| main/route_only/expand_only | 8 | 1 | 4 | 0 | 0 | 0 | 0 |
| main/route_only/expand_then_observe | 12 | 1 | 0 | 4 | 8 | 330 | 4 |
| main/route_only/hold | 8 | 1 | 4 | 0 | 0 | 0 | 0 |
| main/route_only/observe_first | 12 | 1 | 0 | 4 | 8 | 330 | 4 |
| main/route_only/route_review | 8 | 1 | 4 | 0 | 4 | 372 | 0 |
| one_extra_step/legacy/expand_then_observe | 0 | 0 | 2 | 0 | 2 | 67 | 1 |
| one_extra_step/route_only/expand_then_observe | 1 | 0 | 1 | 0 | 1 | 33 | 1 |
| unavailable_sensor/legacy/expand_then_observe | 0 | 0 | 1 | 0 | 0 | 0 | 1 |
| unavailable_sensor/route_only/expand_then_observe | 0 | 0 | 1 | 0 | 0 | 0 | 1 |
| unchanged_sensor/legacy/expand_then_observe | 0 | 0 | 1 | 0 | 0 | 0 | 1 |
| unchanged_sensor/route_only/expand_then_observe | 0 | 0 | 1 | 0 | 0 | 0 | 1 |
| zero_extra_work/legacy/expand_then_observe | 0 | 0 | 2 | 0 | 0 | 0 | 0 |
| zero_extra_work/route_only/expand_then_observe | 1 | 0 | 1 | 0 | 0 | 0 | 0 |

## 개별 조건

| ID | 학습 | 사례 | 초기 | 개입 | 환경/world | 출력 | 정답 | 종료 이유 | 추가 advance/tick | 관측 |
|---|---:|---|---|---|---|---|---|---|---|---:|
| r0000 | 6 | strong_positive | legacy | hold | main / declared | True | True | stop_supported | 0/0 | 0 |
| r0001 | 6 | strong_positive | legacy | expand_only | main / declared | True | True | stop_supported | 0/0 | 0 |
| r0002 | 6 | strong_positive | legacy | observe_first | main / declared | True | True | stop_supported | 0/0 | 0 |
| r0003 | 6 | strong_positive | legacy | expand_then_observe | main / declared | True | True | stop_supported | 0/0 | 0 |
| r0004 | 6 | strong_positive | legacy | route_review | main / declared | True | True | stop_supported | 0/0 | 0 |
| r0005 | 6 | strong_positive | route_only | hold | main / declared | True | True | stop_supported | 0/0 | 0 |
| r0006 | 6 | strong_positive | route_only | expand_only | main / declared | True | True | stop_supported | 0/0 | 0 |
| r0007 | 6 | strong_positive | route_only | observe_first | main / declared | True | True | stop_supported | 0/0 | 0 |
| r0008 | 6 | strong_positive | route_only | expand_then_observe | main / declared | True | True | stop_supported | 0/0 | 0 |
| r0009 | 6 | strong_positive | route_only | route_review | main / declared | True | True | stop_supported | 0/0 | 0 |
| r0010 | 6 | weak_negative | legacy | hold | main / declared | None | None | stop_gate | 0/0 | 0 |
| r0011 | 6 | weak_negative | legacy | expand_only | main / declared | None | None | stop_frontier_exhausted | 0/0 | 0 |
| r0012 | 6 | weak_negative | legacy | observe_first | main / declared | None | None | stop_no_measurement_target | 0/0 | 0 |
| r0013 | 6 | weak_negative | legacy | expand_then_observe | main / declared | None | None | stop_no_measurement_target | 0/0 | 0 |
| r0014 | 6 | weak_negative | legacy | route_review | main / declared | False | True | stop_supported | 1/75 | 0 |
| r0015 | 6 | weak_negative | route_only | hold | main / declared | False | True | stop_supported | 0/0 | 0 |
| r0016 | 6 | weak_negative | route_only | expand_only | main / declared | False | True | stop_supported | 0/0 | 0 |
| r0017 | 6 | weak_negative | route_only | observe_first | main / declared | False | True | stop_supported | 0/0 | 0 |
| r0018 | 6 | weak_negative | route_only | expand_then_observe | main / declared | False | True | stop_supported | 0/0 | 0 |
| r0019 | 6 | weak_negative | route_only | route_review | main / declared | False | True | stop_supported | 0/0 | 0 |
| r0020 | 6 | critical_missing | legacy | hold | main / first_closed | None | None | stop_gate | 0/0 | 0 |
| r0021 | 6 | critical_missing | legacy | expand_only | main / first_closed | None | None | stop_frontier_exhausted | 0/0 | 0 |
| r0022 | 6 | critical_missing | legacy | observe_first | main / first_closed | False | True | stop_supported | 2/96 | 1 |
| r0023 | 6 | critical_missing | legacy | expand_then_observe | main / first_closed | False | True | stop_supported | 2/96 | 1 |
| r0024 | 6 | critical_missing | legacy | route_review | main / first_closed | None | None | stop_review_finished | 1/93 | 0 |
| r0025 | 6 | critical_missing | legacy | hold | main / first_open | None | None | stop_gate | 0/0 | 0 |
| r0026 | 6 | critical_missing | legacy | expand_only | main / first_open | None | None | stop_frontier_exhausted | 0/0 | 0 |
| r0027 | 6 | critical_missing | legacy | observe_first | main / first_open | True | True | stop_supported | 2/69 | 1 |
| r0028 | 6 | critical_missing | legacy | expand_then_observe | main / first_open | True | True | stop_supported | 2/69 | 1 |
| r0029 | 6 | critical_missing | legacy | route_review | main / first_open | None | None | stop_review_finished | 1/93 | 0 |
| r0030 | 6 | critical_missing | legacy | expand_then_observe | zero_extra_work / first_closed | None | None | stop_compute_budget | 0/0 | 0 |
| r0031 | 6 | critical_missing | legacy | expand_then_observe | one_extra_step / first_closed | None | None | stop_compute_budget | 1/33 | 1 |
| r0032 | 6 | critical_missing | legacy | expand_then_observe | unchanged_sensor / first_closed | None | None | measurement_no_new_information | 0/0 | 1 |
| r0033 | 6 | critical_missing | legacy | expand_then_observe | unavailable_sensor / first_closed | None | None | measurement_unavailable | 0/0 | 1 |
| r0034 | 6 | critical_missing | route_only | hold | main / first_closed | None | None | stop_gate | 0/0 | 0 |
| r0035 | 6 | critical_missing | route_only | expand_only | main / first_closed | None | None | stop_frontier_exhausted | 0/0 | 0 |
| r0036 | 6 | critical_missing | route_only | observe_first | main / first_closed | False | True | stop_supported | 2/95 | 1 |
| r0037 | 6 | critical_missing | route_only | expand_then_observe | main / first_closed | False | True | stop_supported | 2/95 | 1 |
| r0038 | 6 | critical_missing | route_only | route_review | main / first_closed | None | None | stop_review_finished | 1/93 | 0 |
| r0039 | 6 | critical_missing | route_only | hold | main / first_open | None | None | stop_gate | 0/0 | 0 |
| r0040 | 6 | critical_missing | route_only | expand_only | main / first_open | None | None | stop_frontier_exhausted | 0/0 | 0 |
| r0041 | 6 | critical_missing | route_only | observe_first | main / first_open | True | True | stop_supported | 2/70 | 1 |
| r0042 | 6 | critical_missing | route_only | expand_then_observe | main / first_open | True | True | stop_supported | 2/70 | 1 |
| r0043 | 6 | critical_missing | route_only | route_review | main / first_open | None | None | stop_review_finished | 1/93 | 0 |
| r0044 | 6 | critical_missing | route_only | expand_then_observe | zero_extra_work / first_closed | None | None | stop_compute_budget | 0/0 | 0 |
| r0045 | 6 | critical_missing | route_only | expand_then_observe | one_extra_step / first_closed | None | None | stop_compute_budget | 1/33 | 1 |
| r0046 | 6 | critical_missing | route_only | expand_then_observe | unchanged_sensor / first_closed | None | None | measurement_no_new_information | 0/0 | 1 |
| r0047 | 6 | critical_missing | route_only | expand_then_observe | unavailable_sensor / first_closed | None | None | measurement_unavailable | 0/0 | 1 |
| r0048 | 6 | critical_zero | legacy | hold | main / first_closed | None | None | stop_gate | 0/0 | 0 |
| r0049 | 6 | critical_zero | legacy | expand_only | main / first_closed | None | None | stop_frontier_exhausted | 0/0 | 0 |
| r0050 | 6 | critical_zero | legacy | observe_first | main / first_closed | False | True | stop_supported | 2/96 | 1 |
| r0051 | 6 | critical_zero | legacy | expand_then_observe | main / first_closed | False | True | stop_supported | 2/96 | 1 |
| r0052 | 6 | critical_zero | legacy | route_review | main / first_closed | None | None | stop_review_finished | 1/93 | 0 |
| r0053 | 6 | critical_zero | legacy | hold | main / first_open | None | None | stop_gate | 0/0 | 0 |
| r0054 | 6 | critical_zero | legacy | expand_only | main / first_open | None | None | stop_frontier_exhausted | 0/0 | 0 |
| r0055 | 6 | critical_zero | legacy | observe_first | main / first_open | True | True | stop_supported | 2/69 | 1 |
| r0056 | 6 | critical_zero | legacy | expand_then_observe | main / first_open | True | True | stop_supported | 2/69 | 1 |
| r0057 | 6 | critical_zero | legacy | route_review | main / first_open | None | None | stop_review_finished | 1/93 | 0 |
| r0058 | 6 | critical_zero | route_only | hold | main / first_closed | None | None | stop_gate | 0/0 | 0 |
| r0059 | 6 | critical_zero | route_only | expand_only | main / first_closed | None | None | stop_frontier_exhausted | 0/0 | 0 |
| r0060 | 6 | critical_zero | route_only | observe_first | main / first_closed | False | True | stop_supported | 2/95 | 1 |
| r0061 | 6 | critical_zero | route_only | expand_then_observe | main / first_closed | False | True | stop_supported | 2/95 | 1 |
| r0062 | 6 | critical_zero | route_only | route_review | main / first_closed | None | None | stop_review_finished | 1/93 | 0 |
| r0063 | 6 | critical_zero | route_only | hold | main / first_open | None | None | stop_gate | 0/0 | 0 |
| r0064 | 6 | critical_zero | route_only | expand_only | main / first_open | None | None | stop_frontier_exhausted | 0/0 | 0 |
| r0065 | 6 | critical_zero | route_only | observe_first | main / first_open | True | True | stop_supported | 2/70 | 1 |
| r0066 | 6 | critical_zero | route_only | expand_then_observe | main / first_open | True | True | stop_supported | 2/70 | 1 |
| r0067 | 6 | critical_zero | route_only | route_review | main / first_open | None | None | stop_review_finished | 1/93 | 0 |
| r0068 | 6 | irrelevant_missing | legacy | hold | main / other_closed | None | None | stop_gate | 0/0 | 0 |
| r0069 | 6 | irrelevant_missing | legacy | expand_only | main / other_closed | None | None | stop_frontier_exhausted | 1/34 | 0 |
| r0070 | 6 | irrelevant_missing | legacy | observe_first | main / other_closed | True | True | stop_supported | 1/64 | 1 |
| r0071 | 6 | irrelevant_missing | legacy | expand_then_observe | main / other_closed | True | True | stop_supported | 2/98 | 1 |
| r0072 | 6 | irrelevant_missing | legacy | route_review | main / other_closed | True | True | stop_supported | 2/164 | 0 |
| r0073 | 6 | irrelevant_missing | legacy | hold | main / other_open | None | None | stop_gate | 0/0 | 0 |
| r0074 | 6 | irrelevant_missing | legacy | expand_only | main / other_open | None | None | stop_frontier_exhausted | 1/34 | 0 |
| r0075 | 6 | irrelevant_missing | legacy | observe_first | main / other_open | True | True | stop_supported | 1/63 | 1 |
| r0076 | 6 | irrelevant_missing | legacy | expand_then_observe | main / other_open | True | True | stop_supported | 2/97 | 1 |
| r0077 | 6 | irrelevant_missing | legacy | route_review | main / other_open | True | True | stop_supported | 2/164 | 0 |
| r0078 | 6 | irrelevant_missing | legacy | expand_then_observe | zero_extra_work / other_closed | None | None | stop_compute_budget | 0/0 | 0 |
| r0079 | 6 | irrelevant_missing | legacy | expand_then_observe | one_extra_step / other_closed | None | None | stop_compute_budget | 1/34 | 0 |
| r0080 | 6 | irrelevant_missing | route_only | hold | main / other_closed | True | True | stop_supported | 0/0 | 0 |
| r0081 | 6 | irrelevant_missing | route_only | expand_only | main / other_closed | True | True | stop_supported | 0/0 | 0 |
| r0082 | 6 | irrelevant_missing | route_only | observe_first | main / other_closed | True | True | stop_supported | 0/0 | 0 |
| r0083 | 6 | irrelevant_missing | route_only | expand_then_observe | main / other_closed | True | True | stop_supported | 0/0 | 0 |
| r0084 | 6 | irrelevant_missing | route_only | route_review | main / other_closed | True | True | stop_supported | 0/0 | 0 |
| r0085 | 6 | irrelevant_missing | route_only | hold | main / other_open | True | True | stop_supported | 0/0 | 0 |
| r0086 | 6 | irrelevant_missing | route_only | expand_only | main / other_open | True | True | stop_supported | 0/0 | 0 |
| r0087 | 6 | irrelevant_missing | route_only | observe_first | main / other_open | True | True | stop_supported | 0/0 | 0 |
| r0088 | 6 | irrelevant_missing | route_only | expand_then_observe | main / other_open | True | True | stop_supported | 0/0 | 0 |
| r0089 | 6 | irrelevant_missing | route_only | route_review | main / other_open | True | True | stop_supported | 0/0 | 0 |
| r0090 | 6 | irrelevant_missing | route_only | expand_then_observe | zero_extra_work / other_closed | True | True | stop_supported | 0/0 | 0 |
| r0091 | 6 | irrelevant_missing | route_only | expand_then_observe | one_extra_step / other_closed | True | True | stop_supported | 0/0 | 0 |
| r0092 | 6 | known_cut_missing | legacy | hold | main / rest_closed | False | True | stop_supported | 0/0 | 0 |
| r0093 | 6 | known_cut_missing | legacy | expand_only | main / rest_closed | False | True | stop_supported | 0/0 | 0 |
| r0094 | 6 | known_cut_missing | legacy | observe_first | main / rest_closed | False | True | stop_supported | 0/0 | 0 |
| r0095 | 6 | known_cut_missing | legacy | expand_then_observe | main / rest_closed | False | True | stop_supported | 0/0 | 0 |
| r0096 | 6 | known_cut_missing | legacy | route_review | main / rest_closed | False | True | stop_supported | 0/0 | 0 |
| r0097 | 6 | known_cut_missing | legacy | hold | main / rest_open | False | True | stop_supported | 0/0 | 0 |
| r0098 | 6 | known_cut_missing | legacy | expand_only | main / rest_open | False | True | stop_supported | 0/0 | 0 |
| r0099 | 6 | known_cut_missing | legacy | observe_first | main / rest_open | False | True | stop_supported | 0/0 | 0 |
| r0100 | 6 | known_cut_missing | legacy | expand_then_observe | main / rest_open | False | True | stop_supported | 0/0 | 0 |
| r0101 | 6 | known_cut_missing | legacy | route_review | main / rest_open | False | True | stop_supported | 0/0 | 0 |
| r0102 | 6 | known_cut_missing | route_only | hold | main / rest_closed | False | True | stop_supported | 0/0 | 0 |
| r0103 | 6 | known_cut_missing | route_only | expand_only | main / rest_closed | False | True | stop_supported | 0/0 | 0 |
| r0104 | 6 | known_cut_missing | route_only | observe_first | main / rest_closed | False | True | stop_supported | 0/0 | 0 |
| r0105 | 6 | known_cut_missing | route_only | expand_then_observe | main / rest_closed | False | True | stop_supported | 0/0 | 0 |
| r0106 | 6 | known_cut_missing | route_only | route_review | main / rest_closed | False | True | stop_supported | 0/0 | 0 |
| r0107 | 6 | known_cut_missing | route_only | hold | main / rest_open | False | True | stop_supported | 0/0 | 0 |
| r0108 | 6 | known_cut_missing | route_only | expand_only | main / rest_open | False | True | stop_supported | 0/0 | 0 |
| r0109 | 6 | known_cut_missing | route_only | observe_first | main / rest_open | False | True | stop_supported | 0/0 | 0 |
| r0110 | 6 | known_cut_missing | route_only | expand_then_observe | main / rest_open | False | True | stop_supported | 0/0 | 0 |
| r0111 | 6 | known_cut_missing | route_only | route_review | main / rest_open | False | True | stop_supported | 0/0 | 0 |
| r0112 | 6 | two_branch_cut | legacy | hold | main / rest_closed | False | True | stop_supported | 0/0 | 0 |
| r0113 | 6 | two_branch_cut | legacy | expand_only | main / rest_closed | False | True | stop_supported | 0/0 | 0 |
| r0114 | 6 | two_branch_cut | legacy | observe_first | main / rest_closed | False | True | stop_supported | 0/0 | 0 |
| r0115 | 6 | two_branch_cut | legacy | expand_then_observe | main / rest_closed | False | True | stop_supported | 0/0 | 0 |
| r0116 | 6 | two_branch_cut | legacy | route_review | main / rest_closed | False | True | stop_supported | 0/0 | 0 |
| r0117 | 6 | two_branch_cut | legacy | hold | main / rest_open | False | True | stop_supported | 0/0 | 0 |
| r0118 | 6 | two_branch_cut | legacy | expand_only | main / rest_open | False | True | stop_supported | 0/0 | 0 |
| r0119 | 6 | two_branch_cut | legacy | observe_first | main / rest_open | False | True | stop_supported | 0/0 | 0 |
| r0120 | 6 | two_branch_cut | legacy | expand_then_observe | main / rest_open | False | True | stop_supported | 0/0 | 0 |
| r0121 | 6 | two_branch_cut | legacy | route_review | main / rest_open | False | True | stop_supported | 0/0 | 0 |
| r0122 | 6 | two_branch_cut | route_only | hold | main / rest_closed | False | True | stop_supported | 0/0 | 0 |
| r0123 | 6 | two_branch_cut | route_only | expand_only | main / rest_closed | False | True | stop_supported | 0/0 | 0 |
| r0124 | 6 | two_branch_cut | route_only | observe_first | main / rest_closed | False | True | stop_supported | 0/0 | 0 |
| r0125 | 6 | two_branch_cut | route_only | expand_then_observe | main / rest_closed | False | True | stop_supported | 0/0 | 0 |
| r0126 | 6 | two_branch_cut | route_only | route_review | main / rest_closed | False | True | stop_supported | 0/0 | 0 |
| r0127 | 6 | two_branch_cut | route_only | hold | main / rest_open | False | True | stop_supported | 0/0 | 0 |
| r0128 | 6 | two_branch_cut | route_only | expand_only | main / rest_open | False | True | stop_supported | 0/0 | 0 |
| r0129 | 6 | two_branch_cut | route_only | observe_first | main / rest_open | False | True | stop_supported | 0/0 | 0 |
| r0130 | 6 | two_branch_cut | route_only | expand_then_observe | main / rest_open | False | True | stop_supported | 0/0 | 0 |
| r0131 | 6 | two_branch_cut | route_only | route_review | main / rest_open | False | True | stop_supported | 0/0 | 0 |
| r0132 | 6 | misleading_direction | legacy | hold | main / declared | True | False | stop_supported | 0/0 | 0 |
| r0133 | 6 | misleading_direction | legacy | expand_only | main / declared | True | False | stop_supported | 0/0 | 0 |
| r0134 | 6 | misleading_direction | legacy | observe_first | main / declared | True | False | stop_supported | 0/0 | 0 |
| r0135 | 6 | misleading_direction | legacy | expand_then_observe | main / declared | True | False | stop_supported | 0/0 | 0 |
| r0136 | 6 | misleading_direction | legacy | route_review | main / declared | True | False | stop_supported | 0/0 | 0 |
| r0137 | 6 | misleading_direction | route_only | hold | main / declared | True | False | stop_supported | 0/0 | 0 |
| r0138 | 6 | misleading_direction | route_only | expand_only | main / declared | True | False | stop_supported | 0/0 | 0 |
| r0139 | 6 | misleading_direction | route_only | observe_first | main / declared | True | False | stop_supported | 0/0 | 0 |
| r0140 | 6 | misleading_direction | route_only | expand_then_observe | main / declared | True | False | stop_supported | 0/0 | 0 |
| r0141 | 6 | misleading_direction | route_only | route_review | main / declared | True | False | stop_supported | 0/0 | 0 |

## 판정 경계

후속 판단은 실제 finish branch와 새 candidate ID로 연결된다. engine-local ID는 같은 계속 계산 안에서 유지된다.
추가 전개는 ready 상태의 기존 frontier를 이어간다. 관측/정책 변경은 새 session이며 기존 비용은 유지한다.
예산·정보 미변경·관측 불가 때문에 보류하면 그 상태를 그대로 보존한다. 자동 retry는 없다.
전역 최적 관측 선택, 지지되는 다른 proof의 자동 교체, 장기 학습/entanglement/consolidation은 이 실험의 범위가 아니다.
