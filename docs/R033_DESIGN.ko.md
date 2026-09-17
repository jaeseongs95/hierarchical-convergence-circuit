# R0.3.3 — 근거 부족 뒤의 계산·관측·정책 재검토

## 출발점과 구현 범위

기준 저장소 main: `a51bedb2340f82abc44dc12c8cede0aa7361e6ef` (`R032 commit`).
EXP-13의 `HCR-Evidence/exp13/r032-first` 및 그 분석을 이 단계의 근거로 사용한다.
그 결과는 선택된 proof의 지지 부족을 진단할 수 있지만, 추가 작업은 실행하지 않았다.
이번에는 그 차이를 개입별로 시험한다. 기본 `AdaptiveEngine.infer()` 정책, 학습·pool·primitive proof 생성 규칙은 변경하지 않는다.

## 실행 구조

1. 기존 session으로 최초 readout-ready까지 실제 계산한다.
2. `fork_readout()`은 session 복사 branch에서 기존 `finish()`를 실행한다. 최초 decision, proof, trace를 저장한다.
3. 계속 실행할 branch의 frontier·node identity·binding·memory·누적 비용은 그대로 보존한다.
4. `continue_dependency()`는 명시적인 실험 개입이다. ready/value만 다시 열고, 다음 `advance()`가 기존 frontier를 실제 전개한다. 정답·feedback을 요구하거나 주입하지 않는다.
5. 새 readout은 다시 정상 finish branch로 계산하고, R0.3.2 diagnostic/dependency_gate를 적용한다. 새 proof를 임의로 고르거나 기존 값을 뒤집지 않는다.
6. 관측 또는 정책 변경이 필요하면 별도 session을 시작한다. 이는 기존 frontier의 resume가 아니라 **비용을 전부 지불하는 재계산**이다.

추론 자체의 engine-local decision ID는 같은 계속 계산에서 유지된다. 각 readout의 전역 `candidate_id`는 segment, generation, ready hash, finished hash를 결속한다. 같은 ID를 다른 내용으로 덮어쓰지 않는다.

## 독립 개입

| 정책 | 수행 |
|---|---|
| hold | 현재 dependency_gate의 보류/수용 그대로 종료 |
| expand_only | 기존 관측·prior를 유지하며 남은 frontier만 제한적으로 전개 |
| observe_first | 현재 선택 proof의 미관측/중립 gap을 먼저 요청하고, 새 관측으로 재계산 |
| expand_then_observe | 남은 frontier 전개 후에도 gap이 남으면 관측 요청 |
| route_review | 새 정보 없이 `route_only`로 처음부터 명시적 재계산 |

`route_review`는 후보 가정의 신뢰도를 자동 학습한 것이 아니다. 사용자가 동결한 명시적 조건이다. 초기 정책이 이미 route_only이면 같은 정책으로 재계산하는 비용 대조가 된다.

## 관측 인터페이스

`MeasurementRequest`에 candidate ID, observation digest, 기존/다음 revision, 요청 edge, 순번을 결속한다.
provider는 요청 edge의 score와 출처만 반환한다. 관측 revision은 실제 score 변화가 있을 때만 진행한다.
요청하지 않은 edge, topology, episode identity의 변경은 허용하지 않는다.
동일 정보 응답은 `measurement_no_new_information`, 관측 불가는 `measurement_unavailable`로 끝난다. 자동 retry가 없다.

선택 규칙은 **선택 proof 또는 이미 전개된 경로의 첫 gap**이다. 평가기의 possible worlds, hidden truth, influential-edge 판정은 실행기로 전달하지 않는다. 따라서 최적·최소 관측을 보장하지 않는다. sign conflict만 있는 경우는 관측 요청으로 무조건 처리하지 않고 route_review와 별도로 비교한다.

## 비용 계약

기준 추론은 각 입력·학습 memory·초기 prior 정책마다 한 번 생성하고 모든 대응 rollout이 공유한다.
비교용 경로 비용은 기준 비용 + 해당 rollout의 추가 비용이다. 전역 실행량에서는 공유 기준 비용을 한 번만 센다.

- `extra_advances`: 계속 실행 및 새 session 재계산에 사용된 advance의 합.
- `extra_kernel_ticks`: 모든 추가 segment의 실제 engine tick. 최초 비용은 별도.
- `measurements`: 요청한 feature 수. 현재 요청당 한 edge. 응답 실패/동일 정보도 비용으로 센다.
- proof readout 계산은 각 branch마다 실제로 수행되므로 `proof_readout_items`에 합산한다.
- 같은 segment의 누적 cost를 여러 readout마다 더하지 않는다.
- `candidate_capture_seconds`, `validation_seconds`, `review_wall_seconds`, `baseline_seconds`를 분리한다.

다음 advance의 최대 pool+decision tick을 보수적으로 예약한다. 잔여 tick이 있어도 예약량보다 작으면 작업을 시작하지 않는다. 이 상태를 수학적인 non-convergence로 분류하지 않는다.
시간에는 Python 복사·검산·직렬화 비용이 포함된다. checkpoint 검산의 recurrence replay는 검산 작업이지 신규 task inference가 아니다. CPU 최적화나 에너지 절감을 이 실험에서 주장하지 않는다.

## 가설에 맞지 않는 결과도 보존

EXP-13의 irrelevant_missing/legacy는 다른 지지 경로가 존재하지만 선택한 proof가 미관측 edge를 사용한다.
추가 전개만으로도 출력이 회복될 수 있다는 가설과, **기존 prior/proof 선택 정책이 계속 같은 약한 경로를 선택하여 전개만으로는 부족하다**는 대안 가설을 비교한다.
후자가 나타나도 소스 오류나 실험 실패로 취급하지 않는다. 상대 경로를 host가 강제로 proof로 교체해 성공시키지 않는다.

## 검산

`evaluation/review_audit.py`는 production review controller를 호출하지 않고 다음을 재구성한다.

- 각 session의 frontier·binding·수치 recurrence·누적 비용·전이 계보: 기존 session auditor 확장.
- candidate가 해당 ready generation에서 정상 finish한 branch인지: prefix·state·event hash 대조.
- 근거 진단과 gate: 기존 독립 grounding auditor 재사용.
- 작업 순서, 공유 예산, 요청 대상, 응답 변화, 재시작 입력: 별도 controller 규칙 재구현.
- frozen memory와 최초 decision 보존, 신규 값의 실제 candidate 출처.
- provider의 응답 충실도: 실험 종료 뒤 평가 층에서만 hidden world와 비교.

지지 계약 자체가 정답을 보증하지 않는다. misleading_direction의 오답은 유지될 수 있다.

## 포함하지 않는 것

장기 학습/부정 예외 학습, 공유 dependency 재배선, consolidation, 자동 confidence 학습, 전역 최적 관측, 전체 controller의 checkpoint/resume, kernel-tick 중간 선점은 후속 과제다.
개별 session의 새 continuation 경계 snapshot/restore는 지원한다. 서로 다른 source 버전의 snapshot hash를 덮어써 호환시키지 않는다.
