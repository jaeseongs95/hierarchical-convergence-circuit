# EXP-25 / R044 — 고정 학습 memory에서 회로 재사용의 실제 기여

## 결론: 이번 소스가 묻는 질문

동일한 학습 memory를 보존하고 native `use_circuits`만 허용/차단했을 때, 실제 계산 구조와 작업량은 어떻게 달라지는가? 재사용으로 expansion이 줄어도 pool 경쟁과 binding 때문에 native ticks가 늘 수 있다는 대안 설명을 분리한다. 새로운 scheduler, 학습 규칙, 예외회로, 보정 정책은 추가하지 않는다.

기준선은 `6b8ff8ab4c4858a3ab8f1a24e82b9033372133fc` (main, R043)다. EXP-22의 동결 seed와 EXP-24의 12개 입력을 그대로 사용한다. 앞선 결과를 새 독립 실험처럼 합산하지 않는다.

## 앞선 관찰과 이번 개입의 연결

EXP-22~24는 배열 순서·ID 재명명·frontier scheduling·proof 선택·채택 시점의 관계를 분리했다. 이 결과는 반복 학습에 의한 회로 압축의 효과가 아니었다. 이번에는 이 제어·검산 기반을 유지해, 이미 학습된 회로의 사용 기여를 시험한다. 초기 EXP-09에서 제기된 'expansion 감소와 native ticks 감소는 다를 수 있다'는 질문을 다시 다룬다.

자료 기준: `HCR-Evidence/exp22/r041-20260917T224012_261821Z`, `HCR-Evidence/exp24/r043-20260918T002524_574380Z` 및 해당 source capsule. R043의 summary를 생성기의 정답표로 사용하지 않는다.

## 조건 동결

| 항목 | 값 |
|---|---|
| Native reuse gate | `use_circuits=True` / `False` |
| 학습 memory | 동일한 기존 seed, circuits 삭제·active flag 수정 없음 |
| Judgment prior | 양군 모두 `route_only` |
| Selector/adoption | 양군 모두 기존 `online_support` / `support_first` |
| Scheduler | 양군 모두 기존 `input_order` |
| ID 배치 | `identity`, `swap_SD` |
| 배열 순열 | `SMD`, `SDM`, `MSD`, `MDS`, `DSM`, `DMS` |
| 입력·config·world·예산 | 같은 pair 안에서 동일, EXP-22 예산 유지 |
| 신규 native 본 실험 | 2 × 2 × 6 = 24조건 / 12개 paired contrast |
| Topology와 학습 seed | 각각 하나 |
| Native integration self-test | 4조건, 본 실험과 분리 |
| 부모 회귀 | ON/identity 6조건을 EXP-22 동조건 raw와 비교 |

같은 입력의 gate ON/OFF는 기존 session naming을 유지한다. gate 때문에 달라진 state hash, reference, 경로, readout 수, 종료시점은 자연스러운 결과로 보존한다. 동일한 hash나 경로를 만들려고 host가 수정하지 않는다.

`input_order`는 현재 frontier의 선두를 선택하는 정책이다. 양군의 frontier가 달라지더라도 같은 정책을 적용한다. 원본 배열의 모든 경로를 처음부터 같은 순서로 실행하도록 강제하는 정책이 아니다.

## 단일 조작의 정확한 범위

`src/hcr/sessions.py`의 기존 `AdaptiveSession(..., use_circuits=...)` 생성자만 사용한다. `src/hcr`를 패치하거나 runtime 전역 함수를 monkeypatch하지 않는다. 새 backend는 생성자 연결만 바꾸고 capture/project/select/reservation은 기존 backend를 상속한다.

이 스위치는 `DeterministicExpansionPolicy.propose` 안의 회로 후보 검색·binding·pool 경쟁·macro 적용 경로 전체를 허용/차단한다. 그러므로 이 실험은 **회로 지원 분기의 총 효과**이며, pool을 동일하게 실행한 뒤 macro 적용만 막는 실험이 아니다.

`route_only`는 완성 경로의 판단 network에 학습 prior가 직접 들어가는 것을 막는다. ON군의 pool 내부에는 기존 학습 routing prior가 남는다. 회로의 경로 선택 기여와 판단 bias를 혼동하지 않기 위한 고정 배경 조건이다. 따라서 legacy와 route_only를 동시에 바꾸는 pair가 아니다.

동일 budget 상한을 사용하지만 기존 보수적 tick reservation은 gate에 의존한다. 이를 억지로 같게 하지 않고 실제 예약량을 보존한다. 예산 종료가 포함된 pair는 자원 여유 조건의 효율 예측에서 별도 분류한다.

## 사전 예측과 실패 기준

실제 macro 적용이 존재하고 양군 모두 budget/engine-failure에 의해 중단되지 않은 pair를 주 예측 평가대상으로 둔다. 적용이 없거나 조건에 맞지 않아도 trial은 유효한 관찰로 보존한다.

- `H_expansion`: ON의 expansion 수가 OFF보다 엄격히 작다.
- `H_kernel`: ON의 native kernel ticks가 OFF보다 엄격히 작다.
- `H_outcome`: ON/OFF의 최종 value와 acceptance가 같다.

각 예측은 pair별 `supported_in_pair`, `falsified_in_pair`, `not_evaluable_for_registered_prediction`으로 기록한다. 같은 수는 엄격한 감소 예측을 지지하지 않는다. 한 예측의 실패를 전체 HCC 이론의 반증으로 표시하지 않는다.

H_outcome은 출력 보존이지 정답성의 증명이 아니다. 외부 world 정답성, 관측 지원 signature, `D_DAG`를 따로 기록한다. 값·채택이 다른 pair의 비용 차이는 동일 품질의 효율 향상이라고 부르지 않는다. final support signature도 최소 goal-support proof DAG의 동형성으로 대체하지 않는다.

부 예측은 같은 gate·배열 순서에서 ID 재명명 전후의 native ticks와 역할 기준 readout 궤적이 보존되는지다. 서로 다른 여섯 배열 순서의 비용이 같아야 한다는 예측은 없다.

## Raw와 독립 검산

`attempts.jsonl`은 trial 시작부터 이벤트를 기록하고 flush/fsync한다. `raw/tNNNN.json`은 완료한 최초 실행만 저장한다. 부분 실패는 failure.json과 trace에 남고 retry하지 않는다.

검산은 production worker를 호출하지 않는다. 기존 native session state replay, original proof/candidate 검산, selector 검산, R041 controller/scheduler 검산을 이어 쓴다. R041 native audit의 고정 `use_circuits=True` 검사만 새로운 별도 switch/input 검사로 대체한다. 나머지 replay·proof·control 계약을 끄지 않는다.

모든 state generation에서 원 memory/config, route_only policy, 고정 top_down/allow_reexpansion, frozen mode, observation, 학습·외부 관측 미개입을 검사한다. 역 ID 변환은 평가 전용이며 실행 state를 바꾸지 않는다. gate 차이 이후 궤적 일치를 audit 성공 조건으로 요구하지 않는다.

원자료 event에서 다음을 별도로 재계산한다: pool/decision network ticks, group updates, signal transmissions, binding scan, circuit inspection, macro/primitive/retirement action. native 계수와 대조한다. network tick 합은 동일 단위 내의 native ticks 분해이며, 이를 binding/selector 검사 수와 더하지 않는다.

macro `span_edges`는 적용된 경로 길이다. 그 값 또는 `span_edges-1`을 자동으로 '절약된 실제 step'이라고 해석하지 않는다. 대조군의 실제 expansion과 비교해야 한다. 채택된 경로와 그 경로에 실제 붙은 circuit uses도 별도로 보존한다.

실제 wall time은 기록하되 count 동치나 감소로부터 시간·전력 이득을 추론하지 않는다. energy, peak memory, 최소 goal proof DAG 동형성은 null이다.

## 계보와 회귀

EXP-24 전체 verify를 실행 전 필수 단계로 둔다. 이번 audit의 EXP-24 anchor 검사는 그 full verify와 별개이며, raw 전체 replay를 했다고 표시하지 않는다. EXP-22 중 route_only/input_order/online_support 6개의 부모 raw는 이번 독립 audit에서 다시 검산하고 새 ON/identity 실행과 비교한다.

회귀는 동일 입력의 native event 의미, candidate view, 최종 결과, native/selector 작업량, scheduler 결정 등을 확인한다. wall-clock 동일성은 요구하지 않는다. 이전 raw를 수정하거나 hash를 현재 source로 다시 봉인하지 않는다.

## 대안 설명과 다음 판단

확장 수는 감소했지만 ticks가 늘면 binding과 pool 경쟁 부담을 우선 확인한다. 출력이 달라지면 좋은 경로를 일찍 선택한 것인지, 완성 경로와 native readout이 달라진 것인지 검토한다. 적용된 macro가 없으면 회로를 자동 추가하지 않고 applicability·binding·pool 노출을 먼저 분석한다.

어느 결과든 다음 기능을 자동으로 붙이지 않는다. 이 실험에서 확인하지 않은 새 학습 효과, 회로 형성의 압축률, 오류 수정 유지, 계층적 수렴은 이후 별도의 판별 실험으로 둔다.

## 현재 주장 가능한 범위

이미 학습된 seed를 사용한 toy native engine의 24조건이다. 실제 LLM 실험, 인간 인지 실험, 에너지 측정, 장기 재학습 실험이 아니다. 양군 모두 memory가 고정이므로 이번 결과를 새로운 학습으로 회로가 개선된 증거로 표현하지 않는다.
