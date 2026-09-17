# EXP-15 / R0.3.4 — 전개·재시작·prior·proof 선택 분리

모의 toy-engine 실행이다. LLM/인간 뇌/현실 센서 결과가 아니다.
main은 최초 판단을 공유한다. running 대조는 최초 판단 이전이며 별도 그룹이다.
support-first는 원 판단과 activation을 바꾸지 않는 명시적 증명 선택 개입이다.
kernel ticks와 선택 검사/증명 노드 수는 서로 다른 비용 단위다. 합쳐 CPU 비용이라 부르지 않는다.

기준 계산 18 (readout-ready 16, running 2) / rollout 194
task kernel ticks: 1643 + 3059 = 4702

| 그룹 / 초기 정책 / 개입 | 정답 | 오답 | 보류 | 출력 회복 | 추가 ticks | 관측 | 경로 검사 | 새 proof 노드 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| main/legacy/expand_only | 5 | 1 | 7 | 0 | 68 | 0 | 0 | 0 |
| main/legacy/expand_then_select | 7 | 1 | 5 | 2 | 68 | 0 | 11 | 8 |
| main/legacy/hold | 5 | 1 | 7 | 0 | 0 | 0 | 0 | 0 |
| main/legacy/observe_first | 11 | 1 | 1 | 6 | 457 | 6 | 0 | 0 |
| main/legacy/restart_route_only | 8 | 1 | 4 | 3 | 775 | 0 | 0 | 0 |
| main/legacy/restart_same | 5 | 1 | 7 | 0 | 475 | 0 | 0 | 0 |
| main/legacy/select_only | 5 | 1 | 7 | 0 | 0 | 0 | 7 | 0 |
| main/route_only/expand_only | 8 | 1 | 4 | 0 | 0 | 0 | 0 | 0 |
| main/route_only/expand_then_select | 8 | 1 | 4 | 0 | 0 | 0 | 0 | 0 |
| main/route_only/hold | 8 | 1 | 4 | 0 | 0 | 0 | 0 | 0 |
| main/route_only/observe_first | 12 | 1 | 0 | 4 | 330 | 4 | 0 | 0 |
| main/route_only/restart_route_only | 8 | 1 | 4 | 0 | 372 | 0 | 0 | 0 |
| main/route_only/restart_same | 8 | 1 | 4 | 0 | 372 | 0 | 0 | 0 |
| main/route_only/select_only | 8 | 1 | 4 | 0 | 0 | 0 | 0 | 0 |
| running_budget_0/route_only/continue | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 |
| running_budget_1/route_only/continue | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 |
| running_budget_8/route_only/continue | 2 | 0 | 0 | 0 | 74 | 0 | 0 | 0 |
| running_hold/route_only/hold | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 |
| selection_no_edges/legacy/expand_then_select | 0 | 0 | 1 | 0 | 34 | 0 | 0 | 0 |
| selection_no_extra_compute/legacy/expand_then_select | 0 | 0 | 1 | 0 | 0 | 0 | 1 | 0 |
| selection_no_proof/legacy/expand_then_select | 0 | 0 | 1 | 0 | 34 | 0 | 3 | 0 |
| selection_no_scan/legacy/select_only | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 |

## 개별 조건

| ID | 입력 | 그룹 | 초기 | 개입 | world | 출력 | 외부 정확성 | 출처 | 종료 | 추가 ticks |
|---|---|---|---|---|---|---|---|---|---|---:|
| s0000 | strong_positive | main | legacy | hold | declared | True | True | native | stop_supported_native | 0 |
| s0001 | strong_positive | main | legacy | expand_only | declared | True | True | native | stop_supported_native | 0 |
| s0002 | strong_positive | main | legacy | restart_same | declared | True | True | native | stop_supported_native | 0 |
| s0003 | strong_positive | main | legacy | restart_route_only | declared | True | True | native | stop_supported_native | 0 |
| s0004 | strong_positive | main | legacy | select_only | declared | True | True | native | stop_supported_native | 0 |
| s0005 | strong_positive | main | legacy | expand_then_select | declared | True | True | native | stop_supported_native | 0 |
| s0006 | strong_positive | main | legacy | observe_first | declared | True | True | native | stop_supported | 0 |
| s0007 | strong_positive | main | route_only | hold | declared | True | True | native | stop_supported_native | 0 |
| s0008 | strong_positive | main | route_only | expand_only | declared | True | True | native | stop_supported_native | 0 |
| s0009 | strong_positive | main | route_only | restart_same | declared | True | True | native | stop_supported_native | 0 |
| s0010 | strong_positive | main | route_only | restart_route_only | declared | True | True | native | stop_supported_native | 0 |
| s0011 | strong_positive | main | route_only | select_only | declared | True | True | native | stop_supported_native | 0 |
| s0012 | strong_positive | main | route_only | expand_then_select | declared | True | True | native | stop_supported_native | 0 |
| s0013 | strong_positive | main | route_only | observe_first | declared | True | True | native | stop_supported | 0 |
| s0014 | weak_negative | main | legacy | hold | declared | None | None | none | stop_hold | 0 |
| s0015 | weak_negative | main | legacy | expand_only | declared | None | None | none | stop_frontier_exhausted | 0 |
| s0016 | weak_negative | main | legacy | restart_same | declared | None | None | none | stop_restart_finished | 75 |
| s0017 | weak_negative | main | legacy | restart_route_only | declared | False | True | native | stop_supported_native | 75 |
| s0018 | weak_negative | main | legacy | select_only | declared | None | None | none | stop_no_supported_selection | 0 |
| s0019 | weak_negative | main | legacy | expand_then_select | declared | None | None | none | stop_frontier_exhausted | 0 |
| s0020 | weak_negative | main | legacy | observe_first | declared | None | None | none | stop_no_measurement_target | 0 |
| s0021 | weak_negative | main | route_only | hold | declared | False | True | native | stop_supported_native | 0 |
| s0022 | weak_negative | main | route_only | expand_only | declared | False | True | native | stop_supported_native | 0 |
| s0023 | weak_negative | main | route_only | restart_same | declared | False | True | native | stop_supported_native | 0 |
| s0024 | weak_negative | main | route_only | restart_route_only | declared | False | True | native | stop_supported_native | 0 |
| s0025 | weak_negative | main | route_only | select_only | declared | False | True | native | stop_supported_native | 0 |
| s0026 | weak_negative | main | route_only | expand_then_select | declared | False | True | native | stop_supported_native | 0 |
| s0027 | weak_negative | main | route_only | observe_first | declared | False | True | native | stop_supported | 0 |
| s0028 | critical_missing | main | legacy | hold | first_closed | None | None | none | stop_hold | 0 |
| s0029 | critical_missing | main | legacy | expand_only | first_closed | None | None | none | stop_frontier_exhausted | 0 |
| s0030 | critical_missing | main | legacy | restart_same | first_closed | None | None | none | stop_restart_finished | 66 |
| s0031 | critical_missing | main | legacy | restart_route_only | first_closed | None | None | none | stop_restart_finished | 93 |
| s0032 | critical_missing | main | legacy | select_only | first_closed | None | None | none | stop_no_supported_selection | 0 |
| s0033 | critical_missing | main | legacy | expand_then_select | first_closed | None | None | none | stop_frontier_exhausted | 0 |
| s0034 | critical_missing | main | legacy | observe_first | first_closed | False | True | native | stop_supported | 96 |
| s0035 | critical_missing | main | legacy | hold | first_open | None | None | none | stop_hold | 0 |
| s0036 | critical_missing | main | legacy | expand_only | first_open | None | None | none | stop_frontier_exhausted | 0 |
| s0037 | critical_missing | main | legacy | restart_same | first_open | None | None | none | stop_restart_finished | 66 |
| s0038 | critical_missing | main | legacy | restart_route_only | first_open | None | None | none | stop_restart_finished | 93 |
| s0039 | critical_missing | main | legacy | select_only | first_open | None | None | none | stop_no_supported_selection | 0 |
| s0040 | critical_missing | main | legacy | expand_then_select | first_open | None | None | none | stop_frontier_exhausted | 0 |
| s0041 | critical_missing | main | legacy | observe_first | first_open | True | True | native | stop_supported | 69 |
| s0042 | critical_missing | main | route_only | hold | first_closed | None | None | none | stop_hold | 0 |
| s0043 | critical_missing | main | route_only | expand_only | first_closed | None | None | none | stop_frontier_exhausted | 0 |
| s0044 | critical_missing | main | route_only | restart_same | first_closed | None | None | none | stop_restart_finished | 93 |
| s0045 | critical_missing | main | route_only | restart_route_only | first_closed | None | None | none | stop_restart_finished | 93 |
| s0046 | critical_missing | main | route_only | select_only | first_closed | None | None | none | stop_no_supported_selection | 0 |
| s0047 | critical_missing | main | route_only | expand_then_select | first_closed | None | None | none | stop_frontier_exhausted | 0 |
| s0048 | critical_missing | main | route_only | observe_first | first_closed | False | True | native | stop_supported | 95 |
| s0049 | critical_missing | main | route_only | hold | first_open | None | None | none | stop_hold | 0 |
| s0050 | critical_missing | main | route_only | expand_only | first_open | None | None | none | stop_frontier_exhausted | 0 |
| s0051 | critical_missing | main | route_only | restart_same | first_open | None | None | none | stop_restart_finished | 93 |
| s0052 | critical_missing | main | route_only | restart_route_only | first_open | None | None | none | stop_restart_finished | 93 |
| s0053 | critical_missing | main | route_only | select_only | first_open | None | None | none | stop_no_supported_selection | 0 |
| s0054 | critical_missing | main | route_only | expand_then_select | first_open | None | None | none | stop_frontier_exhausted | 0 |
| s0055 | critical_missing | main | route_only | observe_first | first_open | True | True | native | stop_supported | 70 |
| s0056 | critical_zero | main | legacy | hold | first_closed | None | None | none | stop_hold | 0 |
| s0057 | critical_zero | main | legacy | expand_only | first_closed | None | None | none | stop_frontier_exhausted | 0 |
| s0058 | critical_zero | main | legacy | restart_same | first_closed | None | None | none | stop_restart_finished | 66 |
| s0059 | critical_zero | main | legacy | restart_route_only | first_closed | None | None | none | stop_restart_finished | 93 |
| s0060 | critical_zero | main | legacy | select_only | first_closed | None | None | none | stop_no_supported_selection | 0 |
| s0061 | critical_zero | main | legacy | expand_then_select | first_closed | None | None | none | stop_frontier_exhausted | 0 |
| s0062 | critical_zero | main | legacy | observe_first | first_closed | False | True | native | stop_supported | 96 |
| s0063 | critical_zero | main | legacy | hold | first_open | None | None | none | stop_hold | 0 |
| s0064 | critical_zero | main | legacy | expand_only | first_open | None | None | none | stop_frontier_exhausted | 0 |
| s0065 | critical_zero | main | legacy | restart_same | first_open | None | None | none | stop_restart_finished | 66 |
| s0066 | critical_zero | main | legacy | restart_route_only | first_open | None | None | none | stop_restart_finished | 93 |
| s0067 | critical_zero | main | legacy | select_only | first_open | None | None | none | stop_no_supported_selection | 0 |
| s0068 | critical_zero | main | legacy | expand_then_select | first_open | None | None | none | stop_frontier_exhausted | 0 |
| s0069 | critical_zero | main | legacy | observe_first | first_open | True | True | native | stop_supported | 69 |
| s0070 | critical_zero | main | route_only | hold | first_closed | None | None | none | stop_hold | 0 |
| s0071 | critical_zero | main | route_only | expand_only | first_closed | None | None | none | stop_frontier_exhausted | 0 |
| s0072 | critical_zero | main | route_only | restart_same | first_closed | None | None | none | stop_restart_finished | 93 |
| s0073 | critical_zero | main | route_only | restart_route_only | first_closed | None | None | none | stop_restart_finished | 93 |
| s0074 | critical_zero | main | route_only | select_only | first_closed | None | None | none | stop_no_supported_selection | 0 |
| s0075 | critical_zero | main | route_only | expand_then_select | first_closed | None | None | none | stop_frontier_exhausted | 0 |
| s0076 | critical_zero | main | route_only | observe_first | first_closed | False | True | native | stop_supported | 95 |
| s0077 | critical_zero | main | route_only | hold | first_open | None | None | none | stop_hold | 0 |
| s0078 | critical_zero | main | route_only | expand_only | first_open | None | None | none | stop_frontier_exhausted | 0 |
| s0079 | critical_zero | main | route_only | restart_same | first_open | None | None | none | stop_restart_finished | 93 |
| s0080 | critical_zero | main | route_only | restart_route_only | first_open | None | None | none | stop_restart_finished | 93 |
| s0081 | critical_zero | main | route_only | select_only | first_open | None | None | none | stop_no_supported_selection | 0 |
| s0082 | critical_zero | main | route_only | expand_then_select | first_open | None | None | none | stop_frontier_exhausted | 0 |
| s0083 | critical_zero | main | route_only | observe_first | first_open | True | True | native | stop_supported | 70 |
| s0084 | irrelevant_missing | main | legacy | hold | other_closed | None | None | none | stop_hold | 0 |
| s0085 | irrelevant_missing | main | legacy | expand_only | other_closed | None | None | none | stop_frontier_exhausted | 34 |
| s0086 | irrelevant_missing | main | legacy | restart_same | other_closed | None | None | none | stop_restart_finished | 68 |
| s0087 | irrelevant_missing | main | legacy | restart_route_only | other_closed | True | True | native | stop_supported_native | 164 |
| s0088 | irrelevant_missing | main | legacy | select_only | other_closed | None | None | none | stop_no_supported_selection | 0 |
| s0089 | irrelevant_missing | main | legacy | expand_then_select | other_closed | True | True | selection | stop_supported_selection | 34 |
| s0090 | irrelevant_missing | main | legacy | observe_first | other_closed | True | True | native | stop_supported | 64 |
| s0091 | irrelevant_missing | main | legacy | hold | other_open | None | None | none | stop_hold | 0 |
| s0092 | irrelevant_missing | main | legacy | expand_only | other_open | None | None | none | stop_frontier_exhausted | 34 |
| s0093 | irrelevant_missing | main | legacy | restart_same | other_open | None | None | none | stop_restart_finished | 68 |
| s0094 | irrelevant_missing | main | legacy | restart_route_only | other_open | True | True | native | stop_supported_native | 164 |
| s0095 | irrelevant_missing | main | legacy | select_only | other_open | None | None | none | stop_no_supported_selection | 0 |
| s0096 | irrelevant_missing | main | legacy | expand_then_select | other_open | True | True | selection | stop_supported_selection | 34 |
| s0097 | irrelevant_missing | main | legacy | observe_first | other_open | True | True | native | stop_supported | 63 |
| s0098 | irrelevant_missing | main | route_only | hold | other_closed | True | True | native | stop_supported_native | 0 |
| s0099 | irrelevant_missing | main | route_only | expand_only | other_closed | True | True | native | stop_supported_native | 0 |
| s0100 | irrelevant_missing | main | route_only | restart_same | other_closed | True | True | native | stop_supported_native | 0 |
| s0101 | irrelevant_missing | main | route_only | restart_route_only | other_closed | True | True | native | stop_supported_native | 0 |
| s0102 | irrelevant_missing | main | route_only | select_only | other_closed | True | True | native | stop_supported_native | 0 |
| s0103 | irrelevant_missing | main | route_only | expand_then_select | other_closed | True | True | native | stop_supported_native | 0 |
| s0104 | irrelevant_missing | main | route_only | observe_first | other_closed | True | True | native | stop_supported | 0 |
| s0105 | irrelevant_missing | main | route_only | hold | other_open | True | True | native | stop_supported_native | 0 |
| s0106 | irrelevant_missing | main | route_only | expand_only | other_open | True | True | native | stop_supported_native | 0 |
| s0107 | irrelevant_missing | main | route_only | restart_same | other_open | True | True | native | stop_supported_native | 0 |
| s0108 | irrelevant_missing | main | route_only | restart_route_only | other_open | True | True | native | stop_supported_native | 0 |
| s0109 | irrelevant_missing | main | route_only | select_only | other_open | True | True | native | stop_supported_native | 0 |
| s0110 | irrelevant_missing | main | route_only | expand_then_select | other_open | True | True | native | stop_supported_native | 0 |
| s0111 | irrelevant_missing | main | route_only | observe_first | other_open | True | True | native | stop_supported | 0 |
| s0112 | known_cut_missing | main | legacy | hold | rest_closed | False | True | native | stop_supported_native | 0 |
| s0113 | known_cut_missing | main | legacy | expand_only | rest_closed | False | True | native | stop_supported_native | 0 |
| s0114 | known_cut_missing | main | legacy | restart_same | rest_closed | False | True | native | stop_supported_native | 0 |
| s0115 | known_cut_missing | main | legacy | restart_route_only | rest_closed | False | True | native | stop_supported_native | 0 |
| s0116 | known_cut_missing | main | legacy | select_only | rest_closed | False | True | native | stop_supported_native | 0 |
| s0117 | known_cut_missing | main | legacy | expand_then_select | rest_closed | False | True | native | stop_supported_native | 0 |
| s0118 | known_cut_missing | main | legacy | observe_first | rest_closed | False | True | native | stop_supported | 0 |
| s0119 | known_cut_missing | main | legacy | hold | rest_open | False | True | native | stop_supported_native | 0 |
| s0120 | known_cut_missing | main | legacy | expand_only | rest_open | False | True | native | stop_supported_native | 0 |
| s0121 | known_cut_missing | main | legacy | restart_same | rest_open | False | True | native | stop_supported_native | 0 |
| s0122 | known_cut_missing | main | legacy | restart_route_only | rest_open | False | True | native | stop_supported_native | 0 |
| s0123 | known_cut_missing | main | legacy | select_only | rest_open | False | True | native | stop_supported_native | 0 |
| s0124 | known_cut_missing | main | legacy | expand_then_select | rest_open | False | True | native | stop_supported_native | 0 |
| s0125 | known_cut_missing | main | legacy | observe_first | rest_open | False | True | native | stop_supported | 0 |
| s0126 | known_cut_missing | main | route_only | hold | rest_closed | False | True | native | stop_supported_native | 0 |
| s0127 | known_cut_missing | main | route_only | expand_only | rest_closed | False | True | native | stop_supported_native | 0 |
| s0128 | known_cut_missing | main | route_only | restart_same | rest_closed | False | True | native | stop_supported_native | 0 |
| s0129 | known_cut_missing | main | route_only | restart_route_only | rest_closed | False | True | native | stop_supported_native | 0 |
| s0130 | known_cut_missing | main | route_only | select_only | rest_closed | False | True | native | stop_supported_native | 0 |
| s0131 | known_cut_missing | main | route_only | expand_then_select | rest_closed | False | True | native | stop_supported_native | 0 |
| s0132 | known_cut_missing | main | route_only | observe_first | rest_closed | False | True | native | stop_supported | 0 |
| s0133 | known_cut_missing | main | route_only | hold | rest_open | False | True | native | stop_supported_native | 0 |
| s0134 | known_cut_missing | main | route_only | expand_only | rest_open | False | True | native | stop_supported_native | 0 |
| s0135 | known_cut_missing | main | route_only | restart_same | rest_open | False | True | native | stop_supported_native | 0 |
| s0136 | known_cut_missing | main | route_only | restart_route_only | rest_open | False | True | native | stop_supported_native | 0 |
| s0137 | known_cut_missing | main | route_only | select_only | rest_open | False | True | native | stop_supported_native | 0 |
| s0138 | known_cut_missing | main | route_only | expand_then_select | rest_open | False | True | native | stop_supported_native | 0 |
| s0139 | known_cut_missing | main | route_only | observe_first | rest_open | False | True | native | stop_supported | 0 |
| s0140 | two_branch_cut | main | legacy | hold | rest_closed | False | True | native | stop_supported_native | 0 |
| s0141 | two_branch_cut | main | legacy | expand_only | rest_closed | False | True | native | stop_supported_native | 0 |
| s0142 | two_branch_cut | main | legacy | restart_same | rest_closed | False | True | native | stop_supported_native | 0 |
| s0143 | two_branch_cut | main | legacy | restart_route_only | rest_closed | False | True | native | stop_supported_native | 0 |
| s0144 | two_branch_cut | main | legacy | select_only | rest_closed | False | True | native | stop_supported_native | 0 |
| s0145 | two_branch_cut | main | legacy | expand_then_select | rest_closed | False | True | native | stop_supported_native | 0 |
| s0146 | two_branch_cut | main | legacy | observe_first | rest_closed | False | True | native | stop_supported | 0 |
| s0147 | two_branch_cut | main | legacy | hold | rest_open | False | True | native | stop_supported_native | 0 |
| s0148 | two_branch_cut | main | legacy | expand_only | rest_open | False | True | native | stop_supported_native | 0 |
| s0149 | two_branch_cut | main | legacy | restart_same | rest_open | False | True | native | stop_supported_native | 0 |
| s0150 | two_branch_cut | main | legacy | restart_route_only | rest_open | False | True | native | stop_supported_native | 0 |
| s0151 | two_branch_cut | main | legacy | select_only | rest_open | False | True | native | stop_supported_native | 0 |
| s0152 | two_branch_cut | main | legacy | expand_then_select | rest_open | False | True | native | stop_supported_native | 0 |
| s0153 | two_branch_cut | main | legacy | observe_first | rest_open | False | True | native | stop_supported | 0 |
| s0154 | two_branch_cut | main | route_only | hold | rest_closed | False | True | native | stop_supported_native | 0 |
| s0155 | two_branch_cut | main | route_only | expand_only | rest_closed | False | True | native | stop_supported_native | 0 |
| s0156 | two_branch_cut | main | route_only | restart_same | rest_closed | False | True | native | stop_supported_native | 0 |
| s0157 | two_branch_cut | main | route_only | restart_route_only | rest_closed | False | True | native | stop_supported_native | 0 |
| s0158 | two_branch_cut | main | route_only | select_only | rest_closed | False | True | native | stop_supported_native | 0 |
| s0159 | two_branch_cut | main | route_only | expand_then_select | rest_closed | False | True | native | stop_supported_native | 0 |
| s0160 | two_branch_cut | main | route_only | observe_first | rest_closed | False | True | native | stop_supported | 0 |
| s0161 | two_branch_cut | main | route_only | hold | rest_open | False | True | native | stop_supported_native | 0 |
| s0162 | two_branch_cut | main | route_only | expand_only | rest_open | False | True | native | stop_supported_native | 0 |
| s0163 | two_branch_cut | main | route_only | restart_same | rest_open | False | True | native | stop_supported_native | 0 |
| s0164 | two_branch_cut | main | route_only | restart_route_only | rest_open | False | True | native | stop_supported_native | 0 |
| s0165 | two_branch_cut | main | route_only | select_only | rest_open | False | True | native | stop_supported_native | 0 |
| s0166 | two_branch_cut | main | route_only | expand_then_select | rest_open | False | True | native | stop_supported_native | 0 |
| s0167 | two_branch_cut | main | route_only | observe_first | rest_open | False | True | native | stop_supported | 0 |
| s0168 | misleading_direction | main | legacy | hold | declared | True | False | native | stop_supported_native | 0 |
| s0169 | misleading_direction | main | legacy | expand_only | declared | True | False | native | stop_supported_native | 0 |
| s0170 | misleading_direction | main | legacy | restart_same | declared | True | False | native | stop_supported_native | 0 |
| s0171 | misleading_direction | main | legacy | restart_route_only | declared | True | False | native | stop_supported_native | 0 |
| s0172 | misleading_direction | main | legacy | select_only | declared | True | False | native | stop_supported_native | 0 |
| s0173 | misleading_direction | main | legacy | expand_then_select | declared | True | False | native | stop_supported_native | 0 |
| s0174 | misleading_direction | main | legacy | observe_first | declared | True | False | native | stop_supported | 0 |
| s0175 | misleading_direction | main | route_only | hold | declared | True | False | native | stop_supported_native | 0 |
| s0176 | misleading_direction | main | route_only | expand_only | declared | True | False | native | stop_supported_native | 0 |
| s0177 | misleading_direction | main | route_only | restart_same | declared | True | False | native | stop_supported_native | 0 |
| s0178 | misleading_direction | main | route_only | restart_route_only | declared | True | False | native | stop_supported_native | 0 |
| s0179 | misleading_direction | main | route_only | select_only | declared | True | False | native | stop_supported_native | 0 |
| s0180 | misleading_direction | main | route_only | expand_then_select | declared | True | False | native | stop_supported_native | 0 |
| s0181 | misleading_direction | main | route_only | observe_first | declared | True | False | native | stop_supported | 0 |
| s0182 | computation_chain3 | running_hold | route_only | hold | declared | None | None | none | stop_hold | 0 |
| s0183 | computation_chain3 | running_budget_0 | route_only | continue | declared | None | None | none | stop_compute_budget | 0 |
| s0184 | computation_chain3 | running_budget_1 | route_only | continue | declared | None | None | none | stop_compute_budget | 0 |
| s0185 | computation_chain3 | running_budget_8 | route_only | continue | declared | True | True | native | stop_supported_native | 36 |
| s0186 | computation_chain4 | running_hold | route_only | hold | declared | None | None | none | stop_hold | 0 |
| s0187 | computation_chain4 | running_budget_0 | route_only | continue | declared | None | None | none | stop_compute_budget | 0 |
| s0188 | computation_chain4 | running_budget_1 | route_only | continue | declared | None | None | none | stop_compute_budget | 0 |
| s0189 | computation_chain4 | running_budget_8 | route_only | continue | declared | True | True | native | stop_supported_native | 38 |
| s0190 | irrelevant_missing | selection_no_scan | legacy | select_only | other_closed | None | None | none | stop_no_supported_selection | 0 |
| s0191 | irrelevant_missing | selection_no_extra_compute | legacy | expand_then_select | other_closed | None | None | none | stop_compute_budget | 0 |
| s0192 | irrelevant_missing | selection_no_edges | legacy | expand_then_select | other_closed | None | None | none | stop_frontier_exhausted | 34 |
| s0193 | irrelevant_missing | selection_no_proof | legacy | expand_then_select | other_closed | None | None | none | stop_frontier_exhausted | 34 |

## 해석 경계

실험 조건의 이름은 결과를 보장하지 않는다. 오류·보류를 정답으로 보정하지 않는다.
재시작은 동일 정책과 route_only 정책을 구분한다. 선택 개입은 기존 생성 경로만 검사한다.
support-first가 실패한 경우도 유지한다. 관측 자체가 틀린 방향이면 여전히 오답을 확정할 수 있다.
학습량은 6회 하나이며 장기 수정/rigidity 실험이 아니다.
