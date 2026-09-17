# EXP-13 / R0.3.2 — 근거 출처·결측 dependency·충돌 진단

원래 판단/가정/proof를 보존한 진단이다. 두 gate는 명시적인 사후 readout 개입이며 참·거짓을 뒤집지 않는다.
directional-support는 score 방향과의 일치 계약이지 참값·보정확률·정답의 보증이 아니다.
과제 추론 126회 / 학습 9회 / readout 평가 378건.
readout 평가와 hidden-world 채점 수를 과제 추론 수에 더하지 않는다.

| 학습 | 사례 | 엔진 | 원 판단 | 선택 proof 지지 | dependency gate | blanket gate | 지지 부족 edge |
|---:|---|---|---|---|---|---|---|
| 3 | strong_positive | legacy | True | True | True | True |  |
| 3 | strong_positive | route_only | True | True | True | True |  |
| 3 | strong_positive | graph_only | True | True | True | True |  |
| 3 | strong_negative | route_only | False | True | False | False |  |
| 3 | strong_negative | graph_only | False | True | False | False |  |
| 3 | strong_negative | legacy | False | True | False | False |  |
| 3 | weak_negative | graph_only | False | True | False | False |  |
| 3 | weak_negative | legacy | True | False | None | True | e0 |
| 3 | weak_negative | route_only | False | True | False | False |  |
| 3 | weak_positive | legacy | True | True | True | True |  |
| 3 | weak_positive | route_only | True | True | True | True |  |
| 3 | weak_positive | graph_only | True | True | True | True |  |
| 3 | critical_missing | route_only | False | False | None | None | e0 |
| 3 | critical_missing | graph_only | False | False | None | None | e0 |
| 3 | critical_missing | legacy | True | False | None | None | e0 |
| 3 | critical_zero | graph_only | False | False | None | None | e0 |
| 3 | critical_zero | legacy | True | False | None | None | e0 |
| 3 | critical_zero | route_only | False | False | None | None | e0 |
| 3 | all_missing | legacy | False | False | None | None | e2 |
| 3 | all_missing | route_only | None | None | None | None |  |
| 3 | all_missing | graph_only | None | None | None | None |  |
| 3 | all_zero | route_only | None | None | None | None |  |
| 3 | all_zero | graph_only | None | None | None | None |  |
| 3 | all_zero | legacy | False | False | None | None | e2 |
| 3 | irrelevant_missing | graph_only | True | True | True | None |  |
| 3 | irrelevant_missing | legacy | True | False | None | None | e2 |
| 3 | irrelevant_missing | route_only | True | True | True | None |  |
| 3 | known_cut_missing | legacy | False | True | False | None |  |
| 3 | known_cut_missing | route_only | False | True | False | None |  |
| 3 | known_cut_missing | graph_only | False | True | False | None |  |
| 3 | irrelevant_zero | route_only | True | True | True | None |  |
| 3 | irrelevant_zero | graph_only | True | True | True | None |  |
| 3 | irrelevant_zero | legacy | True | False | None | None | e2 |
| 3 | known_cut_zero | graph_only | False | True | False | None |  |
| 3 | known_cut_zero | legacy | False | True | False | None |  |
| 3 | known_cut_zero | route_only | False | True | False | None |  |
| 3 | two_branch_cut | legacy | False | True | False | None |  |
| 3 | two_branch_cut | route_only | False | True | False | None |  |
| 3 | two_branch_cut | graph_only | False | True | False | None |  |
| 3 | misleading_direction | route_only | True | True | True | True |  |
| 3 | misleading_direction | graph_only | True | True | True | True |  |
| 3 | misleading_direction | legacy | True | True | True | True |  |
| 6 | strong_positive | route_only | True | True | True | True |  |
| 6 | strong_positive | graph_only | True | True | True | True |  |
| 6 | strong_positive | legacy | True | True | True | True |  |
| 6 | strong_negative | graph_only | False | True | False | False |  |
| 6 | strong_negative | legacy | False | True | False | False |  |
| 6 | strong_negative | route_only | False | True | False | False |  |
| 6 | weak_negative | legacy | True | False | None | True | e0 |
| 6 | weak_negative | route_only | False | True | False | False |  |
| 6 | weak_negative | graph_only | False | True | False | False |  |
| 6 | weak_positive | route_only | True | True | True | True |  |
| 6 | weak_positive | graph_only | True | True | True | True |  |
| 6 | weak_positive | legacy | True | True | True | True |  |
| 6 | critical_missing | graph_only | False | False | None | None | e0 |
| 6 | critical_missing | legacy | True | False | None | None | e0 |
| 6 | critical_missing | route_only | False | False | None | None | e0 |
| 6 | critical_zero | legacy | True | False | None | None | e0 |
| 6 | critical_zero | route_only | False | False | None | None | e0 |
| 6 | critical_zero | graph_only | False | False | None | None | e0 |
| 6 | all_missing | route_only | None | None | None | None |  |
| 6 | all_missing | graph_only | None | None | None | None |  |
| 6 | all_missing | legacy | True | False | None | None | e0,e1,e2 |
| 6 | all_zero | graph_only | None | None | None | None |  |
| 6 | all_zero | legacy | True | False | None | None | e0,e1,e2 |
| 6 | all_zero | route_only | None | None | None | None |  |
| 6 | irrelevant_missing | legacy | True | False | None | None | e2 |
| 6 | irrelevant_missing | route_only | True | True | True | None |  |
| 6 | irrelevant_missing | graph_only | True | True | True | None |  |
| 6 | known_cut_missing | route_only | False | True | False | None |  |
| 6 | known_cut_missing | graph_only | False | True | False | None |  |
| 6 | known_cut_missing | legacy | False | True | False | None |  |
| 6 | irrelevant_zero | graph_only | True | True | True | None |  |
| 6 | irrelevant_zero | legacy | True | False | None | None | e2 |
| 6 | irrelevant_zero | route_only | True | True | True | None |  |
| 6 | known_cut_zero | legacy | False | True | False | None |  |
| 6 | known_cut_zero | route_only | False | True | False | None |  |
| 6 | known_cut_zero | graph_only | False | True | False | None |  |
| 6 | two_branch_cut | route_only | False | True | False | None |  |
| 6 | two_branch_cut | graph_only | False | True | False | None |  |
| 6 | two_branch_cut | legacy | False | True | False | None |  |
| 6 | misleading_direction | graph_only | True | True | True | True |  |
| 6 | misleading_direction | legacy | True | True | True | True |  |
| 6 | misleading_direction | route_only | True | True | True | True |  |
| 9 | strong_positive | graph_only | True | True | True | True |  |
| 9 | strong_positive | legacy | True | True | True | True |  |
| 9 | strong_positive | route_only | True | True | True | True |  |
| 9 | strong_negative | legacy | False | True | False | False |  |
| 9 | strong_negative | route_only | False | True | False | False |  |
| 9 | strong_negative | graph_only | False | True | False | False |  |
| 9 | weak_negative | route_only | False | True | False | False |  |
| 9 | weak_negative | graph_only | False | True | False | False |  |
| 9 | weak_negative | legacy | True | False | None | True | e0 |
| 9 | weak_positive | graph_only | True | True | True | True |  |
| 9 | weak_positive | legacy | True | True | True | True |  |
| 9 | weak_positive | route_only | True | True | True | True |  |
| 9 | critical_missing | legacy | True | False | None | None | e0 |
| 9 | critical_missing | route_only | False | False | None | None | e0 |
| 9 | critical_missing | graph_only | False | False | None | None | e0 |
| 9 | critical_zero | route_only | False | False | None | None | e0 |
| 9 | critical_zero | graph_only | False | False | None | None | e0 |
| 9 | critical_zero | legacy | True | False | None | None | e0 |
| 9 | all_missing | graph_only | None | None | None | None |  |
| 9 | all_missing | legacy | True | False | None | None | e0,e1,e2 |
| 9 | all_missing | route_only | None | None | None | None |  |
| 9 | all_zero | legacy | True | False | None | None | e0,e1,e2 |
| 9 | all_zero | route_only | None | None | None | None |  |
| 9 | all_zero | graph_only | None | None | None | None |  |
| 9 | irrelevant_missing | route_only | True | True | True | None |  |
| 9 | irrelevant_missing | graph_only | True | True | True | None |  |
| 9 | irrelevant_missing | legacy | True | False | None | None | e2 |
| 9 | known_cut_missing | graph_only | False | True | False | None |  |
| 9 | known_cut_missing | legacy | False | True | False | None |  |
| 9 | known_cut_missing | route_only | False | True | False | None |  |
| 9 | irrelevant_zero | legacy | True | False | None | None | e2 |
| 9 | irrelevant_zero | route_only | True | True | True | None |  |
| 9 | irrelevant_zero | graph_only | True | True | True | None |  |
| 9 | known_cut_zero | route_only | False | True | False | None |  |
| 9 | known_cut_zero | graph_only | False | True | False | None |  |
| 9 | known_cut_zero | legacy | False | True | False | None |  |
| 9 | two_branch_cut | graph_only | False | True | False | None |  |
| 9 | two_branch_cut | legacy | False | True | False | None |  |
| 9 | two_branch_cut | route_only | False | True | False | None |  |
| 9 | misleading_direction | legacy | True | True | True | True |  |
| 9 | misleading_direction | route_only | True | True | True | True |  |
| 9 | misleading_direction | graph_only | True | True | True | True |  |

## 정책별 집계

| 엔진/정책 | 출력 | 보류 | 근거 부족 확정 | 식별 불가 확정 | 식별 가능한 입력의 보류 |
|---|---:|---:|---:|---:|---:|
| graph_only/blanket_unknown_gate | 15 | 27 | 0 | 0 | 15 |
| graph_only/dependency_gate | 30 | 12 | 0 | 0 | 0 |
| graph_only/diagnostic_only | 36 | 6 | 6 | 6 | 0 |
| legacy/blanket_unknown_gate | 15 | 27 | 3 | 0 | 15 |
| legacy/dependency_gate | 21 | 21 | 0 | 0 | 9 |
| legacy/diagnostic_only | 42 | 0 | 21 | 12 | 0 |
| route_only/blanket_unknown_gate | 15 | 27 | 0 | 0 | 15 |
| route_only/dependency_gate | 30 | 12 | 0 | 0 | 0 |
| route_only/diagnostic_only | 36 | 6 | 6 | 6 | 0 |

## 해석 경계

- score가 잘못된 관측이면 지지 계약을 만족해도 오답이다. misleading_direction은 이 구분의 대조다.
- 기존 proof에 쓰이지 않은 결측과 실제 결론에 필요한 결측을 구분한다. 새 proof를 자동 생성하지 않는다.
- 진단은 선택된 proof 중심이다. 다른 지지 가능한 경로가 있어도 그 경로로 proof를 자동 교체하지 않는다.
- compatible_worlds는 평가기 전용이며 sign 계약의 식별 가능성을 판정한다. engine/gate에 공급하지 않는다.
- agreement_with_support_gap은 합의도 근거 부족을 해결하지 못한다는 뜻이다. 다수결 정답 판정이 아니다.
- suggestion은 제안 기록이다. 추가 관측·재시도·학습은 실행하지 않았다.
- engine 비용은 raw에 그대로 남으며 diagnostic/readout 처리 시간은 costs.csv에 별도 기록한다.
- 과거 EXP-12 결과를 갱신하지 않으며 새 run을 해당 연구 증거와 혼합하지 않는다.
