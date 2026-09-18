# R0.3.5 / EXP-16 설계

## 결론: 이번에 분리할 계산

EXP-15의 `irrelevant_missing / legacy`에서 전개만으로는 보류가 해소되지 않았고, 전개 후 support-first가 별도 proof를 만들었을 때 출력이 회복됐다. 다음 비교는 **이미 같은 경로와 activation을 가진 상태**에서 재구성만으로 바뀌는지, 선택 기준이 달라져야 바뀌는지를 분리하는 것이다.

이번 구현은 이 첫 판별 실험에 집중한다. 자율 후속 작업 controller, 새 입력부터의 native Graph 변형, 학습 강도/rigidity, sensor reliability를 동시에 추가하지 않는다.

## 증거 기준선

- 저장소: `jaeseongs95/hierarchical-convergence-circuit`
- 커밋: `a9c643954696cbe309f29691bf63e5d4fe463f91`
- 원 실행: `HCR-Evidence/exp15/r034-first`
- 원 판단 함수: `src/hcr/proof.py:reconstruct`
- 기존 선택 기준: `src/hcr/selection.py:select_supported`
- 기존 근거 계약: `src/hcr/grounding.py:diagnose`, `dependency_gate`
- 원 실행 독립 검산: `src/hcr/evaluation/selection_protocol.py:verify_raw`

이 단계는 이미 관찰된 EXP-15 자료를 재사용하는 **후향적 고정 상태 개입**이다. 새 입력을 사전에 보지 않은 독립 일반화 실험으로 부르지 않는다. EXP-16의 정책·행렬·예산·소스는 실행 전에 다시 동결한다.

## 공유 상태와 세 정책

각 원 candidate에서 공개 관측, raw 값, activation, 이미 완성된 경로, graph_complete, 원 proof와 관측 지지 threshold만 추출한다. 별도의 source candidate ID·해시·파일 경로·case 분류·숨은 world는 외부 provenance 또는 evaluator에만 두고 선택기 인자로 전달하지 않는다. 관측의 `episode_id`는 원 binding 보존용 identity로 유지되지만, 정책 분기나 순위 계산에는 사용하지 않는다.

| 정책 | 수행 | 판별 목적 |
|---|---|---|
| `native_saved` | 기존 native proof를 그대로 유지하고 공통 gate 적용 | 원래 판단의 보존 대조 |
| `native_rebuild` | 기존 `hcr.proof.reconstruct`를 같은 입력으로 실제 호출 | 재구성만의 효과 |
| `support_first` | 활성도 순서는 유지하되 관측도 지지하는 첫 생성 경로로 별도 proof 작성 | 지지 기준을 반영한 선택 효과 |

`native_rebuild`는 기존 함수를 다른 이름으로 흉내 내는 실행 조건이 아니다. 실제 함수를 import해 사용한다. 기존 함수가 읽는 paths/binding/state의 최소 투영만 제공하며 network를 다시 실행하지 않는다. identity 조건의 재구성 결과가 보존 proof와 다르면 독립 검산에서 **evaluator disagreement**로 중단한다. 이를 개선 성과로 처리하지 않는다.

공통 gate는 원 R032와 같은 부호 계약을 적용한다. raw 값이 있고, 보고된 proof가 유효하며, 가정이 하나 이상 존재하고, 각 가정이 현 관측의 부호/threshold로 지지돼야 한다. 음성 결론에는 `graph_complete`도 요구한다. proof의 실제 유효성은 별도 evaluator가 DAG를 따라 재검산한다. identity의 `native_saved` gate 결과가 원 native readout과 같은지도 확인한다.

`support_first`의 새 선택은 raw `True`에만 적용한다. `False`와 `None`은 기존 native proof를 유지하는 범위 밖 대조이며 `applicable=false`로 기록한다. 반대 결론 생성, raw 값 뒤집기, 학습, 새 관측, 새 경로 생성은 없다.

## 선정 규칙: 성공 사례만 고르지 않는다

EXP-15 `main/expand_only`의 모든 case×scope를 대상으로, 같은 공개 입력을 공유하는 world 중 사전 정의된 사전식 첫 이름의 raw를 하나 고른다. 그 raw에 들어 있는 **모든 native candidate**를 보존한다. 최초 응답을 포함하고, 추가 전개 경계가 있으면 별도 phase로 포함한다.

선정에 정답·보류·회복 여부나 analysis summary는 사용하지 않는다. 원 world가 둘이어도 같은 native 상태를 독립 표본 둘로 세지 않는다. 외부 정확성은 모든 선언 world에 대해 evaluator가 별도로 계산하고 한 조건의 `world_results`에 넣는다.

`running` 대조는 최초 proof가 없는 단계이므로 이번 선택 경계 모집단에는 포함하지 않는다. EXP-15의 계산 부족 결과를 새 결과처럼 중복 누적하지 않는다.

## 16개 재표현 조합

다음 네 요인을 2×2×2×2로 조합한다.

| 요인 | 수준 0 | 수준 1 |
|---|---|---|
| node 이름 | 원 이름 | opaque 일대일 alias |
| edge ID | 원 ID | opaque 일대일 alias |
| edge slot 순서 | 원 순서 | 역순 |
| 경로 순서 | 원 순서 | 역순 |

slot을 바꾸면 해당 edge activation과 경로 slot을 같은 일대일 사상으로 이동한다. 경로 순서를 바꾸면 관계 activation의 path index도 함께 이동한다. 원 proof는 edge 의미와 path index만 동일 사상으로 옮긴다. proof node ID/parent ID는 opaque identity로 유지한다. node ID 문자열 안 숫자를 읽어 host가 임의 보정하지 않는다.

변환 결과는 `hcr-frozen-transform-r035-v1` wrapper에 별도로 저장하고 원 snapshot 해시와 모든 사상을 기록한다. 원 candidate/packet/trace를 수정하거나 변형된 입력이 원 native packet에서 직접 나온 것처럼 위장하지 않는다. 독립 evaluator는 생성 변환 함수를 호출하지 않고 사상과 실제 수송 결과를 다시 확인한다.

**이 변형은 native readout 이후의 선택 경계에만 적용된다.** 이 실험으로 입력 이름이 실제 Graph 생성, circuit binding 경쟁 또는 수렴 과정에 주는 효과를 주장하지 않는다. 같은 계산 관계를 보존하는 재표현에 대한 선택기의 경계 검증이다.

경로 말단 activation이 동률이면 기존 규칙의 index tie-break 때문에 순서 변경 효과가 생길 수 있다. 이를 오류로 숨기거나 불변성을 강제로 통과시키지 않는다. 원 상태별 outcome 변화로 보고한다.

## 조건 수와 예산

원 snapshot 하나마다 주 비교 `16개 재표현 × 3개 정책 = 48개`와 identity에서 support-first 예산을 각각 0으로 만드는 대조 4개를 수행한다. 따라서 조건 수는 `원 snapshot 수 × 52`다. 원 snapshot 수는 원자료에서 구하고 계획에 고정한다.

정상 선택 예산은 ranked paths 64, path checks 64, edge checks 256, 새 proof nodes 128이다. 이번 원 엔진의 최대 경로/edge 범위에서는 정상 조건의 충분한 예산 대조로 사용한다. 0 예산 대조는 ranking / path scan / edge scan / proof 작성 자원의 부족을 구별한다. 자원이 모자라면 보류를 기록하고 자동 retry하지 않는다.

## 비용

EXP-16 실행 조건의 새 native kernel ticks는 0이다. 기존 EXP-15 kernel 비용은 provenance에만 보존하고 새 비용으로 다시 합산하지 않는다. 독립 auditor의 수치 재계산은 검산 작업이며 새 실험 episode가 아니다.

별도로 새 proof 노드, 재사용 proof 노드, gate에서 검사한 가정 수, 선택기의 경로/edge 검사 inventory와 선택 wall time을 기록한다. 기존 native reconstruct 내부의 scan 카운터는 이 추가 패키지에서 계측하지 않으므로 **null**로 기록한다. 미계측을 0으로 취급하지 않는다. 재구성 API가 제공하는 실제 생성 proof 노드 수는 기록한다.

kernel ticks, path 검사, proof 노드, wall time을 하나의 CPU/에너지 척도로 합치지 않는다. 변환·파일 I/O·auditor 작업도 선택기 wall time 밖의 작업이다.

## 독립 검산

생성기는 raw만 작성한다. `audit`은 별도 프로세스에서 다음을 수행한다.

1. 기존 62개 native source와 EXP-16 도구 source, frozen plan 및 raw manifest를 검사한다.
2. 원 EXP-15 전체 raw를 기존 독립 `verify_raw`로 다시 검산한다. 저장된 summary의 verified 표시만 믿지 않는다.
3. 원 plan의 cell 행렬에서 원 snapshot 모집단을 다시 도출하고, 생성 projector 대신 기존 evaluator의 독립 source_view로 공개 입력을 재구성한다.
4. 모든 변형과 세 정책의 순서/예산/근거 gate를 별도로 계산한다.
5. proof를 DAG로 해석해 feature binding, start/extend/cut/all-path 규칙, 부모 참조, 사용된 모든 노드, 최종 결론과 inferential depth를 확인한다.
6. 최초 시도 로그와 각 raw 결과의 해시를 대조한 뒤에만 analysis를 작성한다.

feature node 깊이는 0이고 추론 node는 부모 최대 깊이+1이다. 이 `D_DAG`는 저장된 proof의 의존 깊이이지 인간 사고 깊이나 hidden-state depth가 아니다.

`verify`는 모든 계산을 다시 수행해 이미 발표한 analysis와 비교한다. 기존 analysis는 덮어쓰지 않는다. 논리적 보류/외부 오답이 있어도 계약과 기록이 맞으면 audit은 통과할 수 있다. 잘못된 proof/ID/부모 참조를 host가 보정하는 경로는 없다.

## 실패 분리와 출력

생성 중 parsing / schema-contract / runtime-I/O / 기타 runtime 실패는 `failure.json`에 보존한다. policy 호출 전 `attempt_started`를 flush/fsync하며, 실패 시 마지막 시도도 남는다. 완료 manifest가 없는 실행은 완료로 보지 않는다.

검산 불일치는 `audit_failures/`에 별도로 남긴다. 잘못된 결과를 정답이나 보류로 고쳐 저장하지 않는다. 모든 파일은 추가 전용이며 이미 존재하는 plan/raw/analysis를 덮어쓰지 않는다.

핵심 paired 지표는 다음이다.

- native 보존과 native 재구성이 모두 보류하는데 support-first가 확정하는가?
- 원 상태의 재표현별 확정/보류와 선택된 원 의미 경로가 달라지는가?
- 반례가 있다면 재구성 차이, tie-break, 지지 없음, 활성도 불충족, 예산 부족 중 무엇인가?

보고서에서 여러 재표현을 독립 문제 수로 해석하거나 이항 검정의 독립 표본으로 사용하지 않는다.

## 다음 단계와 연결

이번 결과가 나온 뒤에는 새 입력부터 원 엔진을 재실행하는 topology/ID/order 변형과, 공개 진단만으로 expand/select/observe/prior-review를 선택하는 controller 실험을 별도로 설계한다. 이번 패키지에 성공을 보장하는 case-name 분기나 자동 controller는 넣지 않는다.
