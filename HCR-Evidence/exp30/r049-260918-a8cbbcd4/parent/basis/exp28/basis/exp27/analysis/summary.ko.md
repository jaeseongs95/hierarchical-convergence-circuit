# EXP-27 / R046 — A의 계산을 B의 추론에 전달하기

## 결론

원천 A 2회, 후속 B 24조건. 아래는 실제 관찰값이며 예측 지지는 audit 통과 조건이 아니다.
기존 HCR native 핵심 함수에 순차 carry 어댑터를 붙인 실험이다. AdaptiveSession 전체 또는 새 회로 학습의 효과와 동일시하지 않는다.

| 상황 | ID | 군 | B ticks | 새 proof node | A 참조 node | state 전달 | 판정 |
|---|---|---|---:|---:|---:|---:|---|
| extend | identity | cold | 36 | 6 | 0 | 0 | correct |
| extend | identity | state_carry | 29 | 6 | 0 | 4 | correct |
| extend | identity | proof_memo | 36 | 2 | 4 | 0 | correct |
| extend | identity | relation_carry | 36 | 2 | 4 | 0 | correct |
| extend | fresh_ids | state_carry | 29 | 6 | 0 | 4 | correct |
| extend | fresh_ids | proof_memo | 36 | 2 | 4 | 0 | correct |
| extend | fresh_ids | relation_carry | 36 | 2 | 4 | 0 | correct |
| extend | fresh_ids | cold | 36 | 6 | 0 | 0 | correct |
| different_subject | identity | proof_memo | 36 | 6 | 0 | 0 | correct |
| different_subject | identity | relation_carry | 36 | 6 | 0 | 0 | correct |
| different_subject | identity | cold | 36 | 6 | 0 | 0 | correct |
| different_subject | identity | state_carry | 36 | 6 | 0 | 0 | correct |
| different_subject | fresh_ids | relation_carry | 36 | 6 | 0 | 0 | correct |
| different_subject | fresh_ids | cold | 36 | 6 | 0 | 0 | correct |
| different_subject | fresh_ids | state_carry | 36 | 6 | 0 | 0 | correct |
| different_subject | fresh_ids | proof_memo | 36 | 6 | 0 | 0 | correct |
| premise_changed | identity | cold | 28 | 3 | 0 | 0 | correct |
| premise_changed | identity | state_carry | 28 | 3 | 0 | 0 | correct |
| premise_changed | identity | proof_memo | 28 | 3 | 0 | 0 | correct |
| premise_changed | identity | relation_carry | 28 | 3 | 0 | 0 | correct |
| premise_changed | fresh_ids | state_carry | 28 | 3 | 0 | 0 | correct |
| premise_changed | fresh_ids | proof_memo | 28 | 3 | 0 | 0 | correct |
| premise_changed | fresh_ids | relation_carry | 28 | 3 | 0 | 0 | correct |
| premise_changed | fresh_ids | cold | 28 | 3 | 0 | 0 | correct |

## 사전 예측의 pair별 판정

- extend / identity / state_carry: H_outcome=supported, H_state_ticks=supported
- extend / identity / proof_memo: H_outcome=supported
- extend / identity / relation_carry: H_outcome=supported, H_proof_reuse=supported
- extend / fresh_ids / state_carry: H_outcome=supported, H_state_ticks=supported
- extend / fresh_ids / proof_memo: H_outcome=supported
- extend / fresh_ids / relation_carry: H_outcome=supported, H_proof_reuse=supported
- different_subject / identity / state_carry: H_outcome=supported, H_binding=supported
- different_subject / identity / proof_memo: H_outcome=supported, H_binding=supported
- different_subject / identity / relation_carry: H_outcome=supported, H_binding=supported
- different_subject / fresh_ids / state_carry: H_outcome=supported, H_binding=supported
- different_subject / fresh_ids / proof_memo: H_outcome=supported, H_binding=supported
- different_subject / fresh_ids / relation_carry: H_outcome=supported, H_binding=supported
- premise_changed / identity / state_carry: H_outcome=supported, H_invalidation=supported
- premise_changed / identity / proof_memo: H_outcome=supported, H_invalidation=supported
- premise_changed / identity / relation_carry: H_outcome=supported, H_invalidation=supported
- premise_changed / fresh_ids / state_carry: H_outcome=supported, H_invalidation=supported
- premise_changed / fresh_ids / proof_memo: H_outcome=supported, H_invalidation=supported
- premise_changed / fresh_ids / relation_carry: H_outcome=supported, H_invalidation=supported

## 해석

수치 상태 전달과 proof 관계 전달은 서로 다른 개입이다. native 탐색·decision program은 모든 군에서 유지된다. proof node를 덜 만들었다고 decision 계산이 줄었다고 하지 않는다.
일반 dependency-aware proof memo와 relation-carry 결과는 memo_controls.csv에 따로 비교한다. 동치이면 관계 표기만의 독립적인 이득으로 세지 않는다.
old goal과 안정화 이력을 넘기지 않는다. state는 근거로 채택하는 것이 아니라 초기값 제안이며 B에서 다시 수렴·검증한다.

## 근거 변경과 Binding

gate_reason, proof_refs.csv, transfer_maps.csv에서 대상 불일치·근거 변경 후 A의 상태/노드가 사용됐는지 확인한다. rejection 후 cold 처리는 사전 등록된 정책이며 ID/proof 자동 수정이 아니다.

## 현재 주장 가능한 범위

정적 topology 2종, 순차 관측 3상황의 최소 계산 실험이다. 유효 관계의 구조적 재사용과 warm initialization을 분리하며, 새 학습·생물학·HCC 고유성을 입증하지 않는다.
D_DAG는 A의 외부 parent까지 펼친 proof에서 독립 계산한다. 신규 node 수·native ticks와 같지 않다.
A_plus_B ticks는 각 pair가 필요로 한 A 한 번과 B의 합이며, 공유된 A를 서로 다른 독립 실행으로 중복 집계하지 않는다.
carry byte·검사·native 비용·wall time은 별개다. ID 문자열 길이가 다르면 byte 수는 달라질 수 있다. energy/peak memory는 null이다.
