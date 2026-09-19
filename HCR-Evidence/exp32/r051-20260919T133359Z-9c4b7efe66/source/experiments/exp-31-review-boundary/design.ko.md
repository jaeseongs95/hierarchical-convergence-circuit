# EXP-31 / R050 — 실제 session의 재검토 경계 판별

계약: `r050-review-boundary-v1`  
구현 기준: `7ba5f31fb68a92fa0eca8ed0bf5f302fe2d36b86`  
상태: 독립 실행 후보 계약. 연구 결과는 각 run의 원자료와 audit로 판정한다.

## 1. 무엇을 이어받는가

EXP-30의 분리된 kernel 실행에서 관찰한 약한 입력의 오판·proof 구성 실패·지지 거부를 실제 `AdaptiveSession` 경로에서 다시 측정한다. 이전 EXP-30의 state나 proof를 이식하지 않는다. 이번 기준선에서 동일 현상이 나타나지 않는 것도 결과다.

기존 `review.py`의 `capture_candidate`, `choose_action`, `measurement_request`, `consume_measurement`와 실제 `AdaptiveSession`을 재사용한다. `ReviewFlow.run()` 전체를 호출하거나 수정한 구현은 아니다. 기존 loop의 재시작은 constructor 기본 switch를 사용하므로, 이번 어댑터는 모든 재시작에 `use_circuits=True`, 해당 조건의 `top_down`, `allow_reexpansion=True`, `judgment_prior=legacy`를 명시한다.

기존 관측 선택기의 다음 action도 따로 기록한다. `grounding.py`는 missing/neutral 등의 edge를 관측 제안으로 내보내고, 알려진 약한 score의 sign conflict는 다른 진단 항목으로 내보낸다. 따라서 기존 관측 선택기가 이번 실패에 관측 대상을 제시하지 않는 경계를 확인할 수 있다. 이를 자동으로 수리하지 않는다.

## 2. 동결 조건

단일 길이 2 chain. 관측 강도 0.02/0.10/1.0 × 공개 부호 ++/+- × identity 배치 2종 × top-down OFF/ON = 24개 기준선이다. 같은 기준선에서 네 개 개입 기록을 만든다. 96개 기록을 96개의 독립 과제로 세지 않는다.

config는 기존 `AdaptiveConfig()`/`Config()` 그대로다. memory는 비어 있으며 frozen_eval이다. 학습, prior_state import, 높은 activation seed, 실제 circuit reuse는 없다. 기존 core를 수정하지 않는다.

각 session은 최대 8 advances, 최대 1,280 kernel ticks이다. 한 arm은 최대 한 번 restart와 한 번 probe만 한다. native advance의 최대 tick 예약을 먼저 검사한다. 계산 부족은 budget termination으로 남기며 추가 예산을 제공하지 않는다.

## 3. 네 대조군

| arm | 조작 | 목적 |
|---|---|---|
| hold | 최초 판단과 gate를 그대로 유지 | 추가 작업 없는 기준선 |
| same_input_restart | 관측·revision·config·memory·switch를 유지하고 새 session | 정보 없는 재계산 효과 |
| echo_revision_restart | 선택한 score를 그대로 반환하고 revision만 +1, 새 session | probe/metadata/revision 대조 |
| strength_revision_restart | 같은 대상 score 한 개의 부호는 유지하고 크기만 1, revision +1, 새 session | echo 대비 강도 변화의 효과 |

최초 gate가 이미 채택한 경우 모든 arm은 추가 작업 없이 정지한다. native failure가 있거나 probe 대상이 없으면 정지 사유를 기록한다. 최초 후보가 예산 안에 생성되지 않으면 해당 기준선의 budget 종료를 보존한다.

`consume_measurement`는 echo에 `measurement_no_new_information`을 반환한다. echo arm의 revision +1과 재시작은 이를 숨긴 자동 retry가 아니라 **별도 명시한 실험자 개입**이다. echo와 strength arm은 같은 revision과 대상을 쓰므로 강도 차이를 더 좁혀 비교할 수 있다.

## 4. 실험용 관측 대상 정책

새 정책임을 명시한다. 기존 native selector와 동일하다고 주장하지 않는다.

먼저 `sign_conflict_edges` 중 `0 < abs(score) < 1`인 edge를 고른다. 없으면 이미 전개된 path에 속한, 알려진 약한 edge를 고른다. 같은 우선순위에서는 score 절대값, 그다음 observation slot 순서로 선택한다. ID 문자열의 사전순으로 고르지 않는다. 새 path를 탐색하거나 proof를 바꾸지 않는다. unknown/zero score를 임의로 채우지 않는다.

strength arm은 이미 공개된 score의 부호만 이용한다. 숨은 정답이나 외부 세계를 worker에 전달하지 않는다. **이 조작은 독립 센서의 새 정보 수집이 아니라 공개 관측 강도에 대한 통제 개입**이다. 전역 최적 query 선택이나 최적 관측 횟수를 검증하지 않는다.

## 5. 예측과 판정

P1: 동일 입력의 재시작은 같은 수치 해에 도달할 것으로 예상한다. 다르면 identity/metadata 경로를 조사하며 결과를 지우지 않는다.

P2: echo/revision-only 개입은 동일 입력 재시작과 수치 상태가 같을 것으로 예상한다. 차이가 나면 이를 별도 효과로 기록한다.

P3: 하나의 강도 변경이 echo 대비 수치 상태 또는 채택을 바꿀 수 있다. 개선되지 않아도 실험 실패 코드로 처리하지 않으며, 두 번째 edge 조작을 덧붙이지 않는다.

P4: 기존 observe_first selector가 약한 known-score 거부에서 관측 대상을 찾지 못하는지 기록한다. 기존 정책의 다음 action만 평가한 것이며 native ReviewFlow 전체 rollout 결과가 아니다.

수치 상태 비교는 abs_tol=1e-12, rel_tol=1e-12를 사용한다. 원자료의 JSON/packet/hash 일치는 별도의 byte/identity 계약으로 검사한다.

## 6. 원자료와 독립 검산

`baselines/`: 실제 최초 session packet, 최초 finish branch의 candidate, native 다음 action, 실험 target.  
`raw/`: 각 arm의 최초 판단 참조, 명시적 개입, 실제 새 session packet/candidate, terminal adoption.  
`progress/`: 각 성공한 init/begin/advance의 append-only snapshot과 candidate 원본.  
`measurements/`: 응답 검증 전 보존한 request/response.  
`interventions/`: 실제 실행 전 동결한 restart 입력과 사유.  
`source/`, `source_manifest.json`, `plan.json`: 실행한 원본 core, 신규 도구, tests, 조건, provenance.  
`analysis/`: 독립 audit, trials.csv, summary.json, summary.ko.md.  
`validation/`: self-test, 실제 core smoke/audit, 최종 core regression의 원문 및 receipt.

독립 auditor는 worker/protocol/review/runtime/dynamics를 실행하지 않는다. 기존 `hcr.evaluation`의 session 수치·event 재생과 proof/support verifier를 이용하고, 신규 target·관측 조작·조건 행렬·비용·adoption·paired binding은 별도 규칙으로 재계산한다. 최초 baseline은 한 번만 검산·집계하며 복제된 rollout을 독립 관측으로 더하지 않는다.

최초 logical failure, proof failure, support rejection, native abstention, budget termination, runtime/schema/audit failure를 구분한다. 채택 거부는 정답 채택이 아니다. 종료 숫자 측면, pre-proof pending value, raw decision, proof, gate, terminal adoption을 따로 보존한다.

## 7. 비용

kernel ticks, signal transmissions, graph expansion/native counters, 새 proof 노드, target slot 검사, 요청 수, 재시작 수, 실제 측정 wall time을 구분한다. 자기보고 alias counter를 중복 합산하지 않는다. baseline 비용은 전체 실험에서 한 번만 세고 arm의 추가 비용을 분리한다. 측정하지 않은 process memory와 에너지는 null이다.

## 8. 유지보수 계약

기존 `src/hcr`, `tests`, R048/R049 manifest 및 release 파일, dispatcher는 변경하지 않는다. `experiments/INDEX.json`에는 `standalone_candidate_contract` 행만 추가한다. `default_experiment=EXP-30`과 기존 CURRENT mapping은 유지한다. 실행은 `Run-HCR-R050.cmd`이며 공통 dispatcher의 기본값을 새 실험으로 바꾸지 않는다.

패치 전 보호 파일 hash와 index를 검사하고 계획과 원본 bytes를 보존한다. 충돌하는 기존 파일은 덮어쓰지 않는다. 변경 후 직접 검산, 조건 동결, 신규 self-test, 최종 core regression 1회, 실제 실행, 독립 audit, 집계를 수행한다. 실패 시 이 설치가 만든 변경만 hash를 확인하여 되돌린다. 외부 변경은 unresolved로 남기고 강제로 덮어쓰지 않는다. 실패·부분 evidence는 제거하지 않는다.

## 9. 주장 범위

이 실험은 추상 HCC session의 재시작/관측 강도 개입 연구다. 학습된 직관, 상태 보존형 보정, 남은 frontier의 재확장, 실제 circuit 재사용, LLM 성능, 인간 인지, 생물학적 회로, hardware/전력 효율의 검증이 아니다. 이 항목들을 후속으로 확장하려면 별도 설계와 조건 동결이 필요하다.
