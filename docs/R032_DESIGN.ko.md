# R0.3.2 — 판단 근거·결측 dependency·충돌 진단

## 기준과 범위

코드 기준은 `14c1b0f42a9babc6b82d879e5f57be2421030c18` (`exp12 실행`)이다.
직전 EXP-12 분석의 다음 세 결과를 설계 입력으로 사용한다.

1. 회로 선택과 경로를 유지해도 판단용 prior의 적용에 따라 약한 반례의 답이 달라졌다.
2. route_only도 부분 결측/0점에서 근거가 부족한 False를 확정한다.
3. 전체 결측의 None은 별도 guard 결과이며, 신호 수렴 자체의 불확실성 표현과 다르다.

이 버전은 **진단 계층과 명시적 readout 개입**만 추가한다. 기존 엔진의 수치 계산,
학습, pool, frontier, proof 재구성, session 저장/복원, R0.3 통합은 변경하지 않는다.
실제 관측 요청·추가 전개·후보 교체·정답 수정·오류 뒤 재학습을 구현한 버전이 아니다.

## 코드 배치

| 파일 | 책임 |
|---|---|
| `src/hcr/grounding.py` | SupportContract, 가정의 출처/지지 진단, 명시적 gate, 진단 간 충돌 |
| `src/hcr/grounding_cli.py` | `hcr grounding plan/demo/verify` 입출력 |
| `src/hcr/evaluation/grounding_spec.py` | EXP-13 입력·학습 시점·정책 고정 |
| `src/hcr/evaluation/grounding_audit.py` | 진단 규칙 별도 구현, 기존 proof/session 검산, 평가 전용 세계 완성 |
| `src/hcr/evaluation/grounding_protocol.py` | 생성/기록/집계/파일 무결성 검증 |
| `tests/test_r032_grounding.py` | 원본 보존, source binding, 결측 역할, 위변조, 완전 실행 시험 |
| `Run-HCR-R032.py` | Python 기반 전체 적용 후 검증·실험 실행 |

EXP-13의 개별 과제 실행은 기존 `prior_protocol.run_task`를 재사용한다. 그 안의
`hcr-exp12-task-r031-v1` packet 형식도 유지한다. 이는 이전 결과를 복사한 것이 아니라
**현재 새로 실행한 과제를 기존 검산 가능한 포맷에 저장**한다는 의미다.
바깥 plan/record/manifest는 EXP-13 스키마를 사용한다.

## 세 층위의 분리

- `raw/...`의 원래 decision: 신호 수렴과 기존 readout, 기존 proof, 기존 비용.
- `records/...`의 diagnostic: 이미 만들어진 proof의 가정이 어떤 관측에 연결되는지.
- 같은 record의 readouts: 명시한 세 정책의 결과. 원래 값 유지 또는 None만 가능.

`diagnostic_only`는 원래 값을 그대로 내보낸다.
`dependency_gate`는 **현재 선택된 proof의 가정**이 선언된 지지 계약을 충족할 때만 원래 값을 유지한다.
`blanket_unknown_gate`는 입력에 None/0이 하나라도 있으면 보류하는 비교 대조다.
어느 gate도 True를 False로, False를 True로 바꾸지 않는다. proof·memory·원래 trace도 고치지 않는다.
따라서 보류 개입의 효과를 모델 내부의 자발적 수정이나 host가 고친 정답으로 보고하지 않는다.

## 방향성 지지 계약

기본 `hcr-directional-support-v1`의 `min_abs_score=0.0`은 다음을 의미한다.

| 관측 | 가정 지지 분류 |
|---|---|
| None | missing |
| 0 또는 -0.0 | neutral |
| 절댓값이 명시 threshold 이하인 비영점 | below_threshold |
| 방향이 가정과 반대 | sign_conflict |
| 방향이 가정과 일치 | directional_support |

score는 검증된 참값이나 보정 확률이 아니다. 매우 약한 점수도 기본 계약에서는 방향성만
지지할 수 있으며, threshold 변경은 별도 계약/실험으로 취급한다. 잘못된 센서 방향을 준
`misleading_direction`에서는 지지 계약을 통과해도 외부 오답이 될 수 있도록 대조한다.

각 가정에 원래 score, missing/neutral/directional 구분, 입력 digest+edge ID,
관측 drive, 최종 activation, 관련 relation의 learned drive, goal drive,
해당 edge에 바인딩된 회로와 routing prior를 남긴다. **drive가 함께 있었다는 이유로
해당 가정의 유일한 원인이라고 판정하지 않는다.**

## dependency 범위

원래 proof에 쓰이지 않은 결측은 전역적인 '근거 없음'으로 처리하지 않는다.
양의 결론에서는 선택 proof의 실제 경로 가정만 검사한다. 음의 결론은 선택 proof의
차단 가정과 `graph_complete`를 함께 요구한다. 독립 감사는 기존 primitive reference를
통해 실제 모든 경로에 대한 부정 증명 coverage도 재검사한다.

진단기는 새로운 path를 열거하지 않는다. 추가 경로 관련 항목은 engine이 이미 기록한
`expanded_paths`에만 한정한다. 평가기는 별도로 최대 8개 edge의 None/0을 모두 완성해
sign 계약 아래 결론이 식별 가능한지 계산한다. 이 결과는 engine/gate에 공급하지 않는다.

이 설계에는 의도적으로 한계가 있다. **실제로 지지되는 다른 경로가 있어도 현재 선택한
proof가 근거 부족이면 dependency_gate는 보류한다.** 그 경로로 proof를 자동 교체하는
기능은 다음 판별 실험 대상이다. '선택 proof의 지지'와 '가능한 모든 proof의 존재'를
같은 개념으로 보고하지 않는다.

## 충돌 진단

같은 관측·memory·지지 계약의 진단끼리만 비교한다. 서로 다른 값이면 decision_conflict,
같은 값이지만 지지가 부족하면 agreement_with_support_gap으로 남긴다.
같은 edge에 서로 다른 가정을 한 경우만 assumption_conflicts에 넣는다. 한 proof에만
등장하는 edge는 그 이유만으로 충돌이라 하지 않는다. 같은 관측이 여러 판단에 쓰여도
지지 횟수나 confidence를 배수로 올리지 않는다. 승자를 선택하는 기능은 없다.

## 다음 행동과 비용

suggestion은 요청할 edge 또는 재검토할 prior/방법을 제안할 뿐 `executed=false`다.
실제 observation request, revision, retry, feedback 비용을 발생했다고 기록하지 않는다.
원래 engine 비용을 그대로 보존하고 diagnostic/readout의 처리 시간을 별도로 측정한다.
이 시간에는 source chain 검사·가정 순회·직렬화/해시 등의 관리 계산이 포함된다.
이를 공짜 연산이나 전체 실행시간과 같다고 주장하지 않는다.
진단 packet의 참조 개수는 inventory 지표이며 전체 CPU 연산 횟수가 아니다.
원시 task 시간 밖의 packet 직렬화 시간도 CSV의 packet_seconds로 따로 남긴다.

## 연구 단계에서의 위치

습관·고정관념 통합 가설 중 '익숙한 해석의 근거와 수정 필요를 어떻게 구분하는가'의
기반이다. Strength/Rigidity/Entanglement/Consolidation을 새로 측정한 것으로 세지 않는다.
현재는 진단·보류 개입을 분리했고, 다음에는 제안된 관측/대안 전개를 실제로 실행하면서
추가 비용과 첫 실패를 유지하는 프로토콜을 별도 단계로 검증한다.
