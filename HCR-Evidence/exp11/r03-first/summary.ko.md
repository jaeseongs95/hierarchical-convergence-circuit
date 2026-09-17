# EXP-11 / R0.3 — 전문화 방법·메시지·총예산 비교

개발 fixture 결과다. agreement는 외부 정답 판정이 아니며 conflict는 보류다.
동일한 총 advance/tick/message 상한을 부여한다. 동일 연산량·동일 wall time을 강제하지 않는다.
tick은 실행 전 최악 상한을 예약하므로, 아직 남은 tick이 있어도 시작하지 못할 수 있다.

| 예산 | 사례 | 방법 | 출력 | 정답 | 상태 | 전개 | tick | 메시지 수신 | 우선순위 변경 |
|---|---|---|---|---|---|---:|---:|---:|---:|
| standard | familiar | sequential | True | True | single_method | 3 | 36 | 0 | 0 |
| standard | familiar | associative | True | True | single_method | 2 | 69 | 0 | 0 |
| standard | familiar | fixed | True | True | agreement | 5 | 105 | 3 | 0 |
| standard | familiar | adaptive | True | True | agreement | 5 | 105 | 3 | 0 |
| standard | familiar | fixed_no_messages | True | True | agreement | 5 | 105 | 0 | 0 |
| standard | familiar | adaptive_no_messages | True | True | agreement | 5 | 105 | 0 | 0 |
| standard | counterfactual | sequential | False | True | single_method | 3 | 28 | 0 | 0 |
| standard | counterfactual | associative | False | True | single_method | 2 | 96 | 0 | 0 |
| standard | counterfactual | fixed | False | True | agreement | 5 | 124 | 3 | 0 |
| standard | counterfactual | adaptive | False | True | agreement | 5 | 124 | 3 | 0 |
| standard | counterfactual | fixed_no_messages | False | True | agreement | 5 | 124 | 0 | 0 |
| standard | counterfactual | adaptive_no_messages | False | True | agreement | 5 | 124 | 0 | 0 |
| standard | longer | sequential | True | True | single_method | 4 | 38 | 0 | 0 |
| standard | longer | associative | True | True | single_method | 2 | 105 | 0 | 0 |
| standard | longer | fixed | True | True | agreement | 6 | 143 | 3 | 0 |
| standard | longer | adaptive | True | True | agreement | 6 | 143 | 3 | 0 |
| standard | longer | fixed_no_messages | True | True | agreement | 6 | 143 | 0 | 0 |
| standard | longer | adaptive_no_messages | True | True | agreement | 6 | 143 | 0 | 0 |
| standard | fork | sequential | True | True | single_method | 4 | 36 | 0 | 0 |
| standard | fork | associative | True | True | single_method | 2 | 69 | 0 | 0 |
| standard | fork | fixed | True | True | agreement | 5 | 105 | 3 | 1 |
| standard | fork | adaptive | True | True | agreement | 5 | 105 | 3 | 1 |
| standard | fork | fixed_no_messages | True | True | agreement | 6 | 105 | 0 | 0 |
| standard | fork | adaptive_no_messages | True | True | agreement | 6 | 105 | 0 | 0 |
| standard | weak_conflict | sequential | False | True | single_method | 3 | 39 | 0 | 0 |
| standard | weak_conflict | associative | True | False | single_method | 1 | 75 | 0 | 0 |
| standard | weak_conflict | fixed | None | None | conflict_abstention | 4 | 114 | 1 | 0 |
| standard | weak_conflict | adaptive | None | None | conflict_abstention | 4 | 114 | 1 | 0 |
| standard | weak_conflict | fixed_no_messages | None | None | conflict_abstention | 4 | 114 | 0 | 0 |
| standard | weak_conflict | adaptive_no_messages | None | None | conflict_abstention | 4 | 114 | 0 | 0 |
| standard | unknown | sequential | None | None | incomplete_or_ambiguous | 3 | 59 | 0 | 0 |
| standard | unknown | associative | True | True | single_method | 2 | 179 | 0 | 0 |
| standard | unknown | fixed | None | None | incomplete_or_ambiguous | 5 | 238 | 3 | 0 |
| standard | unknown | adaptive | None | None | incomplete_or_ambiguous | 5 | 238 | 3 | 0 |
| standard | unknown | fixed_no_messages | None | None | incomplete_or_ambiguous | 5 | 238 | 0 | 0 |
| standard | unknown | adaptive_no_messages | None | None | incomplete_or_ambiguous | 5 | 238 | 0 | 0 |
| standard | diamond | sequential | True | True | single_method | 3 | 60 | 0 | 0 |
| standard | diamond | associative | True | True | single_method | 1 | 64 | 0 | 0 |
| standard | diamond | fixed | True | True | agreement | 3 | 97 | 1 | 1 |
| standard | diamond | adaptive | True | True | agreement | 3 | 97 | 1 | 1 |
| standard | diamond | fixed_no_messages | True | True | agreement | 4 | 124 | 0 | 0 |
| standard | diamond | adaptive_no_messages | True | True | agreement | 4 | 124 | 0 | 0 |
| limited | familiar | sequential | True | True | single_method | 3 | 36 | 0 | 0 |
| limited | familiar | associative | True | True | single_method | 2 | 69 | 0 | 0 |
| limited | familiar | fixed | None | None | incomplete_or_ambiguous | 4 | 69 | 3 | 0 |
| limited | familiar | adaptive | None | None | incomplete_or_ambiguous | 4 | 69 | 3 | 0 |
| limited | familiar | fixed_no_messages | None | None | incomplete_or_ambiguous | 4 | 69 | 0 | 0 |
| limited | familiar | adaptive_no_messages | None | None | incomplete_or_ambiguous | 4 | 69 | 0 | 0 |
| limited | counterfactual | sequential | False | True | single_method | 3 | 28 | 0 | 0 |
| limited | counterfactual | associative | False | True | single_method | 2 | 96 | 0 | 0 |
| limited | counterfactual | fixed | None | None | incomplete_or_ambiguous | 4 | 96 | 3 | 0 |
| limited | counterfactual | adaptive | None | None | incomplete_or_ambiguous | 4 | 96 | 3 | 0 |
| limited | counterfactual | fixed_no_messages | None | None | incomplete_or_ambiguous | 4 | 96 | 0 | 0 |
| limited | counterfactual | adaptive_no_messages | None | None | incomplete_or_ambiguous | 4 | 96 | 0 | 0 |
| limited | longer | sequential | True | True | single_method | 4 | 38 | 0 | 0 |
| limited | longer | associative | True | True | single_method | 2 | 105 | 0 | 0 |
| limited | longer | fixed | None | None | incomplete_or_ambiguous | 4 | 105 | 3 | 0 |
| limited | longer | adaptive | None | None | incomplete_or_ambiguous | 4 | 105 | 3 | 0 |
| limited | longer | fixed_no_messages | None | None | incomplete_or_ambiguous | 4 | 105 | 0 | 0 |
| limited | longer | adaptive_no_messages | None | None | incomplete_or_ambiguous | 4 | 105 | 0 | 0 |
| limited | fork | sequential | True | True | single_method | 4 | 36 | 0 | 0 |
| limited | fork | associative | True | True | single_method | 2 | 69 | 0 | 0 |
| limited | fork | fixed | None | None | incomplete_or_ambiguous | 4 | 69 | 3 | 0 |
| limited | fork | adaptive | None | None | incomplete_or_ambiguous | 4 | 69 | 3 | 0 |
| limited | fork | fixed_no_messages | None | None | incomplete_or_ambiguous | 4 | 69 | 0 | 0 |
| limited | fork | adaptive_no_messages | None | None | incomplete_or_ambiguous | 4 | 69 | 0 | 0 |
| limited | weak_conflict | sequential | False | True | single_method | 3 | 39 | 0 | 0 |
| limited | weak_conflict | associative | True | False | single_method | 1 | 75 | 0 | 0 |
| limited | weak_conflict | fixed | None | None | conflict_abstention | 4 | 114 | 1 | 0 |
| limited | weak_conflict | adaptive | None | None | conflict_abstention | 4 | 114 | 1 | 0 |
| limited | weak_conflict | fixed_no_messages | None | None | conflict_abstention | 4 | 114 | 0 | 0 |
| limited | weak_conflict | adaptive_no_messages | None | None | conflict_abstention | 4 | 114 | 0 | 0 |
| limited | unknown | sequential | None | None | incomplete_or_ambiguous | 3 | 59 | 0 | 0 |
| limited | unknown | associative | True | True | single_method | 2 | 179 | 0 | 0 |
| limited | unknown | fixed | None | None | incomplete_or_ambiguous | 4 | 179 | 3 | 0 |
| limited | unknown | adaptive | None | None | incomplete_or_ambiguous | 4 | 179 | 3 | 0 |
| limited | unknown | fixed_no_messages | None | None | incomplete_or_ambiguous | 4 | 179 | 0 | 0 |
| limited | unknown | adaptive_no_messages | None | None | incomplete_or_ambiguous | 4 | 179 | 0 | 0 |
| limited | diamond | sequential | True | True | single_method | 3 | 60 | 0 | 0 |
| limited | diamond | associative | True | True | single_method | 1 | 64 | 0 | 0 |
| limited | diamond | fixed | True | True | agreement | 3 | 97 | 1 | 1 |
| limited | diamond | adaptive | True | True | agreement | 3 | 97 | 1 | 1 |
| limited | diamond | fixed_no_messages | True | True | agreement | 4 | 124 | 0 | 0 |
| limited | diamond | adaptive_no_messages | True | True | agreement | 4 | 124 | 0 | 0 |

## 해석 경계

Sequential은 breadth-first primitive 전개이고 Associative는 기존 macro 우선·depth-first 전개다.
따라서 단독 두 방법의 차이는 두 정책을 묶은 제한된 M profile 차이이지, 각 구성요소의 독립 효과는 아니다.
메시지의 효과는 fixed/no_messages 및 adaptive/no_messages 대응쌍으로 읽는다.
같은 evidence가 두 처리기를 통과해도 지지도가 두 배가 되지 않는다. primitive proof는 처리기별로 보존한다.
추론 중 장기 memory 갱신, prior 정책 수정, 음의 예외 학습, OS thread 병렬화는 없다.
controller 관리·session 복사 시간을 total_wall_seconds에 포함하고 engine active time과 분리했다.
이 run은 처리기 교대 중 디스크 checkpoint를 사용하지 않는다. 개별 worker의 R0.2.1 snapshot 검산은 결과 저장 후 수행한다.
표본 반복이 없는 진단이므로 wall-time 가속을 주장하지 않는다. 실패·오답·보류를 분리한다.
