# EXP-28 / R047 — 상태 전달의 기여 분해

## 결론

모집단: `research`. A 2회 공유, B 42조건. 독립 무작위 반복 실험이 아닙니다.
전달 없음, edge만, prefix만, 둘 다를 비교하고 각 mask에 고정 초기값 0.99 대조를 둡니다.
가설의 지지/실패는 아래에 전부 표시하며, audit 통과 여부와 구분합니다.

## 관찰

| 상황 | ID | 처리 | B ticks | 신규 proof | 초기값 설정 group | 판정 |
|---|---|---|---:|---:|---:|---|
| extend | identity | cold | 36 | 6 | 0 | correct |
| extend | identity | carry_edge | 33 | 6 | 2 | correct |
| extend | identity | carry_prefix | 31 | 6 | 2 | correct |
| extend | identity | carry_both | 29 | 6 | 4 | correct |
| extend | identity | fixed_edge | 33 | 6 | 2 | correct |
| extend | identity | fixed_prefix | 31 | 6 | 2 | correct |
| extend | identity | fixed_both | 29 | 6 | 4 | correct |
| extend | fresh_ids | carry_edge | 33 | 6 | 2 | correct |
| extend | fresh_ids | carry_prefix | 31 | 6 | 2 | correct |
| extend | fresh_ids | carry_both | 29 | 6 | 4 | correct |
| extend | fresh_ids | fixed_edge | 33 | 6 | 2 | correct |
| extend | fresh_ids | fixed_prefix | 31 | 6 | 2 | correct |
| extend | fresh_ids | fixed_both | 29 | 6 | 4 | correct |
| extend | fresh_ids | cold | 36 | 6 | 0 | correct |
| different_subject | identity | carry_prefix | 36 | 6 | 0 | correct |
| different_subject | identity | carry_both | 36 | 6 | 0 | correct |
| different_subject | identity | fixed_edge | 36 | 6 | 0 | correct |
| different_subject | identity | fixed_prefix | 36 | 6 | 0 | correct |
| different_subject | identity | fixed_both | 36 | 6 | 0 | correct |
| different_subject | identity | cold | 36 | 6 | 0 | correct |
| different_subject | identity | carry_edge | 36 | 6 | 0 | correct |
| different_subject | fresh_ids | carry_both | 36 | 6 | 0 | correct |
| different_subject | fresh_ids | fixed_edge | 36 | 6 | 0 | correct |
| different_subject | fresh_ids | fixed_prefix | 36 | 6 | 0 | correct |
| different_subject | fresh_ids | fixed_both | 36 | 6 | 0 | correct |
| different_subject | fresh_ids | cold | 36 | 6 | 0 | correct |
| different_subject | fresh_ids | carry_edge | 36 | 6 | 0 | correct |
| different_subject | fresh_ids | carry_prefix | 36 | 6 | 0 | correct |
| premise_changed | identity | fixed_edge | 28 | 3 | 0 | correct |
| premise_changed | identity | fixed_prefix | 28 | 3 | 0 | correct |
| premise_changed | identity | fixed_both | 28 | 3 | 0 | correct |
| premise_changed | identity | cold | 28 | 3 | 0 | correct |
| premise_changed | identity | carry_edge | 28 | 3 | 0 | correct |
| premise_changed | identity | carry_prefix | 28 | 3 | 0 | correct |
| premise_changed | identity | carry_both | 28 | 3 | 0 | correct |
| premise_changed | fresh_ids | fixed_prefix | 28 | 3 | 0 | correct |
| premise_changed | fresh_ids | fixed_both | 28 | 3 | 0 | correct |
| premise_changed | fresh_ids | cold | 28 | 3 | 0 | correct |
| premise_changed | fresh_ids | carry_edge | 28 | 3 | 0 | correct |
| premise_changed | fresh_ids | carry_prefix | 28 | 3 | 0 | correct |
| premise_changed | fresh_ids | carry_both | 28 | 3 | 0 | correct |
| premise_changed | fresh_ids | fixed_edge | 28 | 3 | 0 | correct |

## 사전 가설 전체 판정

| 상황 | ID | 처리/대조 | 가설 | 판정 |
|---|---|---|---|---|
| extend | identity | carry_edge / cold | H_outcome | supported |
| extend | identity | carry_edge / cold | H_edge_ticks | supported |
| extend | identity | carry_prefix / cold | H_outcome | supported |
| extend | identity | carry_prefix / cold | H_prefix_ticks | supported |
| extend | identity | carry_both / cold | H_outcome | supported |
| extend | identity | carry_both / cold | H_carry_both_ticks | supported |
| extend | identity | fixed_edge / cold | H_outcome | supported |
| extend | identity | fixed_prefix / cold | H_outcome | supported |
| extend | identity | fixed_both / cold | H_outcome | supported |
| extend | identity | carry_edge / fixed_edge | H_source_specificity | falsified |
| extend | identity | carry_prefix / fixed_prefix | H_source_specificity | falsified |
| extend | identity | carry_both / fixed_both | H_source_specificity | falsified |
| extend | fresh_ids | carry_edge / cold | H_outcome | supported |
| extend | fresh_ids | carry_edge / cold | H_edge_ticks | supported |
| extend | fresh_ids | carry_prefix / cold | H_outcome | supported |
| extend | fresh_ids | carry_prefix / cold | H_prefix_ticks | supported |
| extend | fresh_ids | carry_both / cold | H_outcome | supported |
| extend | fresh_ids | carry_both / cold | H_carry_both_ticks | supported |
| extend | fresh_ids | fixed_edge / cold | H_outcome | supported |
| extend | fresh_ids | fixed_prefix / cold | H_outcome | supported |
| extend | fresh_ids | fixed_both / cold | H_outcome | supported |
| extend | fresh_ids | carry_edge / fixed_edge | H_source_specificity | falsified |
| extend | fresh_ids | carry_prefix / fixed_prefix | H_source_specificity | falsified |
| extend | fresh_ids | carry_both / fixed_both | H_source_specificity | falsified |
| different_subject | identity | carry_edge / cold | H_outcome | supported |
| different_subject | identity | carry_edge / cold | H_rejection | supported |
| different_subject | identity | carry_prefix / cold | H_outcome | supported |
| different_subject | identity | carry_prefix / cold | H_rejection | supported |
| different_subject | identity | carry_both / cold | H_outcome | supported |
| different_subject | identity | carry_both / cold | H_rejection | supported |
| different_subject | identity | fixed_edge / cold | H_outcome | supported |
| different_subject | identity | fixed_edge / cold | H_rejection | supported |
| different_subject | identity | fixed_prefix / cold | H_outcome | supported |
| different_subject | identity | fixed_prefix / cold | H_rejection | supported |
| different_subject | identity | fixed_both / cold | H_outcome | supported |
| different_subject | identity | fixed_both / cold | H_rejection | supported |
| different_subject | fresh_ids | carry_edge / cold | H_outcome | supported |
| different_subject | fresh_ids | carry_edge / cold | H_rejection | supported |
| different_subject | fresh_ids | carry_prefix / cold | H_outcome | supported |
| different_subject | fresh_ids | carry_prefix / cold | H_rejection | supported |
| different_subject | fresh_ids | carry_both / cold | H_outcome | supported |
| different_subject | fresh_ids | carry_both / cold | H_rejection | supported |
| different_subject | fresh_ids | fixed_edge / cold | H_outcome | supported |
| different_subject | fresh_ids | fixed_edge / cold | H_rejection | supported |
| different_subject | fresh_ids | fixed_prefix / cold | H_outcome | supported |
| different_subject | fresh_ids | fixed_prefix / cold | H_rejection | supported |
| different_subject | fresh_ids | fixed_both / cold | H_outcome | supported |
| different_subject | fresh_ids | fixed_both / cold | H_rejection | supported |
| premise_changed | identity | carry_edge / cold | H_outcome | supported |
| premise_changed | identity | carry_edge / cold | H_rejection | supported |
| premise_changed | identity | carry_prefix / cold | H_outcome | supported |
| premise_changed | identity | carry_prefix / cold | H_rejection | supported |
| premise_changed | identity | carry_both / cold | H_outcome | supported |
| premise_changed | identity | carry_both / cold | H_rejection | supported |
| premise_changed | identity | fixed_edge / cold | H_outcome | supported |
| premise_changed | identity | fixed_edge / cold | H_rejection | supported |
| premise_changed | identity | fixed_prefix / cold | H_outcome | supported |
| premise_changed | identity | fixed_prefix / cold | H_rejection | supported |
| premise_changed | identity | fixed_both / cold | H_outcome | supported |
| premise_changed | identity | fixed_both / cold | H_rejection | supported |
| premise_changed | fresh_ids | carry_edge / cold | H_outcome | supported |
| premise_changed | fresh_ids | carry_edge / cold | H_rejection | supported |
| premise_changed | fresh_ids | carry_prefix / cold | H_outcome | supported |
| premise_changed | fresh_ids | carry_prefix / cold | H_rejection | supported |
| premise_changed | fresh_ids | carry_both / cold | H_outcome | supported |
| premise_changed | fresh_ids | carry_both / cold | H_rejection | supported |
| premise_changed | fresh_ids | fixed_edge / cold | H_outcome | supported |
| premise_changed | fresh_ids | fixed_edge / cold | H_rejection | supported |
| premise_changed | fresh_ids | fixed_prefix / cold | H_outcome | supported |
| premise_changed | fresh_ids | fixed_prefix / cold | H_rejection | supported |
| premise_changed | fresh_ids | fixed_both / cold | H_outcome | supported |
| premise_changed | fresh_ids | fixed_both / cold | H_rejection | supported |
| extend | identity_vs_fresh | cold / identity | H_ID_native | supported |
| extend | identity_vs_fresh | carry_edge / identity | H_ID_native | supported |
| extend | identity_vs_fresh | carry_prefix / identity | H_ID_native | supported |
| extend | identity_vs_fresh | carry_both / identity | H_ID_native | supported |
| extend | identity_vs_fresh | fixed_edge / identity | H_ID_native | supported |
| extend | identity_vs_fresh | fixed_prefix / identity | H_ID_native | supported |
| extend | identity_vs_fresh | fixed_both / identity | H_ID_native | supported |
| different_subject | identity_vs_fresh | cold / identity | H_ID_native | supported |
| different_subject | identity_vs_fresh | carry_edge / identity | H_ID_native | supported |
| different_subject | identity_vs_fresh | carry_prefix / identity | H_ID_native | supported |
| different_subject | identity_vs_fresh | carry_both / identity | H_ID_native | supported |
| different_subject | identity_vs_fresh | fixed_edge / identity | H_ID_native | supported |
| different_subject | identity_vs_fresh | fixed_prefix / identity | H_ID_native | supported |
| different_subject | identity_vs_fresh | fixed_both / identity | H_ID_native | supported |
| premise_changed | identity_vs_fresh | cold / identity | H_ID_native | supported |
| premise_changed | identity_vs_fresh | carry_edge / identity | H_ID_native | supported |
| premise_changed | identity_vs_fresh | carry_prefix / identity | H_ID_native | supported |
| premise_changed | identity_vs_fresh | carry_both / identity | H_ID_native | supported |
| premise_changed | identity_vs_fresh | fixed_edge / identity | H_ID_native | supported |
| premise_changed | identity_vs_fresh | fixed_prefix / identity | H_ID_native | supported |
| premise_changed | identity_vs_fresh | fixed_both / identity | H_ID_native | supported |

## 상호작용과 ID 검사 비용

- identity: both − edge − prefix + cold = 1 ticks. 독립성 증명이 아니라 기술적 대조값입니다.
- fresh_ids: both − edge − prefix + cold = 1 ticks. 독립성 증명이 아니라 기술적 대조값입니다.
- premise_changed / carry_edge: dependency 검사는 identity 2회 / fresh 1회. 원래의 ID 정렬·조기 종료 효과를 숨기지 않았습니다.
- premise_changed / carry_prefix: dependency 검사는 identity 2회 / fresh 1회. 원래의 ID 정렬·조기 종료 효과를 숨기지 않았습니다.
- premise_changed / carry_both: dependency 검사는 identity 2회 / fresh 1회. 원래의 ID 정렬·조기 종료 효과를 숨기지 않았습니다.
- premise_changed / fixed_edge: dependency 검사는 identity 2회 / fresh 1회. 원래의 ID 정렬·조기 종료 효과를 숨기지 않았습니다.
- premise_changed / fixed_prefix: dependency 검사는 identity 2회 / fresh 1회. 원래의 ID 정렬·조기 종료 효과를 숨기지 않았습니다.
- premise_changed / fixed_both: dependency 검사는 identity 2회 / fresh 1회. 원래의 ID 정렬·조기 종료 효과를 숨기지 않았습니다.

## 해석과 대안 설명

actual carry와 fixed 대조의 ticks가 같으면, 이 단일 조건의 tick 절감만으로 A의 정밀한 수치 상태가 필수라고 주장하지 않습니다. 수치 궤적의 동일성과 tick 수의 동일성은 별개입니다.
고정값 대조도 같은 binding, 근거 검사, source packet, target mask를 사용합니다. 이것은 binding이 불필요하다는 실험이 아닙니다.
prefix는 기존 path-prefix signal group입니다. 자연어 의미·인간 사고 깊이·학습된 synaptic strength와 동일시하지 않습니다.
기존 source 전체를 packet으로 전달하므로 부분 mask의 최소 저장/통신비용을 측정한 것이 아닙니다.
D_DAG, ticks, group updates, signals, 검사 수, bytes, wall time은 서로 다른 단위입니다. native/bridge proof node 수는 동일 생성을 가리키는 중복 계수입니다.
wall time에는 Python 기록·fsync 비용이 포함됩니다. 실행시간·전력 효율 주장은 하지 않습니다.

## 현재 주장 가능한 범위

현재 toy/kernel, 한 A→B 경계에서 상태 성분과 초기값을 분해했습니다. Preallocated substrate, 가소성, 새 회로 학습, 자연어 문맥 경쟁은 미실험입니다.
EXP-27의 H_ID 실패는 별도 parent_review.ko.md에 그대로 유지합니다. 새 결과로 과거 가설을 소급 수정하지 않습니다.
