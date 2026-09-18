# EXP-26 / R045 사전 설계 — 직접 지지 경로에서의 회로 재사용

## 1. 계보와 질문

기준 commit은 `3bfeb64af877a7512071798fd77d8eba839760a1`이다. EXP-25 입력·memory·config의 출처는 `HCR-Evidence/exp25/r044-20260918T015818_405389Z`이다. 그 raw manifest의 SHA-256을 `24b88d417b107b0d6a92c1187c52b2ef0b14a313beab90e6025d23c872129bcf`로 고정한다.

EXP-25의 관찰은 expansion 감소가 8/12쌍, native ticks 증가가 12/12쌍이었고, 최종 양성 지원 경로에는 직접 circuit use가 없었다는 것이다. 따라서 현재 회로가 지원 경로의 계산을 직접 대체할 수 있는 조건을 별도로 검사한다. 기존 EXP-25 원자료 재검산은 새로운 독립 실험 증거로 세지 않는다.

중심 질문은 다음과 같다.

> 여러 primitive expansion을 macro로 묶었을 때, 최종 지원 경로의 decision program·drive·수렴 state 계산도 달라지는가, 아니면 그 계산은 유지되면서 pool 비용만 추가되는가?

본 구현은 이 설명을 구별하기 위한 새 입력·관측·측정 장치다. pool 제거, 캐시, 새 scheduler, memory pruning, 회로 강도 변경, 정답 경로 강제 선택은 하지 않는다.

## 2. 조건과 조작

native 정책은 기존 `route_only / input_order / online_support`를 유지한다. 양군에 동일한 기존 학습 memory와 config를 전달하며 EXP-25의 budget과 selection_limits를 그대로 보존한다. 실제 변화는 기존 native 생성자의 `use_circuits`이다. 검색·binding·pool 경쟁·macro 적용의 **전체 분기 gate 효과**이지 macro 적용만의 효과가 아니다.

| 계열 | canonical edge | score | 수 |
|---|---|---|---:|
| supported_len2 | e0: v0→v1, e1: v1→v2 | +0.92, +0.92 | 4 |
| no_match_len1 | e0: v0→v2 | +0.92 | 4 |
| conflict_len2 | e0: v0→v1, e1: v1→v2 | +0.92, -0.92 | 4 |

공통 episode_id는 `exp26-fixed-path`, revision은 0이다. ID 대조는 e0→alias_Z9, e1→alias_A1로 일관되게 재명명하며 node, edge 배열, score, topology, 역할을 변경하지 않는다. 접미사의 역순 명칭은 실제 배열 순서를 바꾸지 않는다.

계열마다 두 ID 배치와 두 gate를 교차하며 쌍내 gate 순서와 계열별 variant 순서를 교차 배치한다. fresh session을 사용하되 memory 상태는 동일하다. 명시된 순서가 plan에 포함되며 결과를 보고 바꾸지 않는다.

설계 유효성 조건은 memory가 비어 있지 않고, 활성 길이 2 pattern이 존재하며, 활성 길이 1 pattern이 없고, mismatch threshold가 0.92 미만인 것이다. 이는 가능한 입력 노출에 대한 조건이며 실제 매칭 성공·macro 선택·정답 채택을 강제하는 조건이 아니다. 조건을 충족하지 못하면 seed를 수정하지 않고 중단한다.

선언 world는 평가기에만 공급한다. 양성 및 len1 edge는 True, conflict의 e1만 False이다. runtime은 observation/config/memory/budget/gate/event_sink만 받으며 world, 계열명, 정답, ID 역변환표는 받지 않는다.

## 3. 사전 예측과 판정 경계

주요 비교는 supported_len2 ON/OFF 2쌍이다.

| 예측 | 판정 대상 |
|---|---|
| H_direct | ON의 최종 양성 채택 route에 explicit circuit use가 존재하는가 |
| H_expansion | 직접 사용과 양군 비검열 조건에서 ON expansion < OFF인가 |
| H_kernel | 같은 평가 조건에서 ON native ticks < OFF인가 |
| H_decision_same | 같은 평가 조건에서 기록된 decision program·drive 및 전체 tick state열이 같은가 |
| H_outcome | 비검열 pair에서 최종 value·acceptance가 보존되는가 |

H_kernel과 H_decision_same은 다른 계산 설명을 구별하는 예측이다. 전개 감소·tick 감소·출력 보존을 하나의 성공 점수로 합치지 않는다. 직접 사용이 없으면 H_direct의 예측 실패를 보존하고 직접 노출 조건부 비용 예측은 `not_evaluable`로 분리한다. 원래 gate 총효과의 값은 노출이 없어도 기록한다.

추가 진단은 다음과 같다.

- len1: 실제 매칭 후보·pool·macro가 없는지, ON/OFF native ticks가 같은지 검사한다. binding/recall 검사까지 0 또는 전체 비용 동일이라고 예측하지 않는다.
- conflict: 구조적 매칭과 pool 평가가 실제 발생하고 mismatch 사유로 모든 평가 후보가 적격에서 제외되며 macro가 적용되지 않는지 검사한다. pool 미형성이나 activation 저하는 별도 기록한다. 어느 군도 True를 채택하지 않는지 보되 abstention을 정답으로 바꾸지 않는다.
- ID: 같은 계열·gate에서 역변환된 readout, decision 계산 서명과 관측 비용이 같은지 검사한다.

budget 종료와 engine 실패는 검열로 별도 처리한다. 부정 예측과 정답 여부는 audit 통과 조건이 아니다. `supported_in_pair / falsified_in_pair / not_evaluable`는 해당 사전 예측·조건에만 적용하며 전체 HCC 반증 판정이 아니다.

## 4. 관찰·측정

측정 단계는 `binding 검사 → 구조적 matched candidate → pool candidate 평가 → 적격 여부·거부 사유 → macro action → 최종 양성 route의 직접 사용`이다. circuit use가 없는 양성 route는 False, 양성 채택이나 식별된 route 자체가 없으면 null이다. 다른 route에 macro가 적용된 사실을 직접 사용으로 바꾸지 않는다.

R044의 이벤트 기반 비용 검산을 먼저 실행한다. native ticks는 모든 pool tick과 decision tick의 합과 대조한다. group updates, signal transmissions, binding scans, recall inspections, macro/primitive/retirement action은 각자 원자료·native 계수와 비교한다. 서로 다른 단위를 합한 총 계산 점수는 없다.

새 decision 서명은 event/network ID를 제외한 program, drives, top_down과 모든 tick state, residual, stable_steps, 종료 convergence를 사용한다. decision 계산 서명이 같더라도 전체 실행 궤적이나 비용이 같다고 주장하지 않는다. event ID는 네트워크 추적용으로 원자료와 CSV에 남긴다.

선택 proof의 D_DAG는 기존 독립 검산기에서 가져온다. 입력 edge 수를 D_DAG로 대체하지 않으며 최소 goal-support proof DAG의 동형성을 측정했다고 주장하지 않는다. wall time은 runtime 보고값으로 따로 기록하고 계수의 합에 포함하지 않는다. 실제 에너지·peak memory는 null이다.

## 5. 검증 장치와 독립성

입력 생성과 입력 검산은 별도 구현이다. 검산기는 producer의 case/trial 생성 함수를 사용하지 않는다. runtime은 기존 R044 worker를 그대로 호출하고, auditor는 기존 native state·proof·controller·scheduler replay를 이어 사용한다. 새 측정기는 runtime, matcher, pool, selector 함수를 호출하지 않는다. 단, 기존 schema/codec 및 source 무결성 도구는 재사용한다.

원클릭 실행기는 먼저 저장된 EXP-25 전체 24조건을 기존 verify로 재검증한다. 이어 t0000~t0003 4조건을 새 native session에서 다시 실행해 기존 event semantic·view·출력·scheduler/selector·비용 회귀를 비교한다. 추가 smoke 6조건은 identity에서 ±0.85 관측과 별도 episode_id를 사용한다. 올바름·macro 노출·효율을 self-test 통과 조건으로 두지 않는다.

이 10회 native self-test와 EXP-25 기존 raw 재검산은 EXP-26의 12개 연구 조건에 합산하지 않는다. EXP-26 evidence 자체는 그 seed training, 입력 격리, 12개 native raw, attempt stream, 부모 raw 4개를 독립 replay한다. 부모 전체 24조건 재검사는 launcher 단계이며 새 audit가 다시 전체 24개를 replay했다고 표시하지 않는다.

## 6. Evidence와 실패

plan, source hash, memory/config hash, parent capsule hash는 실행 전에 동결한다. raw마다 first attempt를 보존하고 각 action을 flush/fsync한다. 생성기는 raw_complete만 표시하며 independently verified나 예측 성공을 쓰지 않는다.

audit와 verify는 raw를 다시 읽고 독립 재계산한다. verify는 기존 analysis를 갱신하지 않는다. 실패 기록은 logical outcome, budget 종료, schema/contract, parsing, dependency, measurement, evaluator disagreement, runtime/I/O 범주로 구분한다. 오답·기권을 삭제하거나 정답으로 수정하지 않는다.

설치 파일은 신규 R045 경로만 허용한다. 다른 내용의 기존 파일과 충돌하면 덮어쓰기 없이 중단한다. 자동 retry, rollback, git commit/push, 모델·패키지 다운로드, 서버 시작, 회로/ID 보정은 없다. 중단된 raw와 최초 traceback은 남기고 실패 bundle은 `complete=false`로 표시한다.

## 7. 현재 가능한 주장과 다음 분기

직접 사용이 확인되고 decision 계산이 같으면서 expansion만 줄면, 현재 macro가 전개를 대체했으나 판단 수렴을 대체하지 못했다는 설명을 이 고정 native 조건에서 지지한다. 직접 사용 자체가 없으면 eligibility·실제 노출 경계를 먼저 조사한다. 충돌 조건의 macro 거부는 현재 관측에 대한 정적 거부 사례이며 동적 재확장이나 재학습 증거가 아니다.

단일 경로 입력은 경로 선택 우회라는 대안 원인을 제거하지만 전체 HCC의 학습·압축 효율, LLM 내부 계산, 인간 인지, 뇌 메커니즘 또는 에너지 절감을 입증하지 않는다. len1과 len2는 topology가 다르므로 그 차이를 순수 matching 비용이나 D_DAG 인과효과로 해석하지 않는다.

이번 결과가 어떤 방향이든 회로의 단순 존재가 아니라 **실제로 대체된 계산의 범위와 남아 있는 비용**을 기준으로 다음 변경을 정한다.
