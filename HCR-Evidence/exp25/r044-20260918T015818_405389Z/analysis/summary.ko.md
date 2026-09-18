# EXP-25 / R044 — 학습 memory를 유지한 회로 재사용 기여 분리

## 결론

본 실험 24조건 / 12쌍, 실제 macro 적용과 무중단 조건을 만족한 예측 평가 대상 12쌍.
회로 재사용의 이득을 미리 성공으로 판정하지 않는다. 다음은 동결된 예측을 실제 결과에 적용한 판정이다.

| 예측 | pair 지지 | pair 예측 실패 | 평가 조건 미충족 |
|---|---:|---:|---:|
| H_expansion | 8 | 4 | 0 |
| H_kernel | 0 | 12 | 0 |
| H_outcome | 12 | 0 | 0 |

H_expansion: 재사용 허용 시 expansion 감소. H_kernel: native ticks 감소. H_outcome: 값·채택 보존.
각 예측은 별도이며, 하나의 실패를 다른 성공으로 상쇄하지 않는다. 비용 비교는 결과가 다른 pair에서도 원값을 보존하되 효율 향상이라 부르지 않는다.

## 관찰

| 배열 | ID 배치 | ON ticks | OFF ticks | ON expansion | OFF expansion | 관찰 분류 |
|---|---|---:|---:|---:|---:|---|
| SMD | identity | 164 | 33 | 2 | 2 | no_expansion_reduction |
| SMD | swap_SD | 164 | 33 | 2 | 2 | no_expansion_reduction |
| SDM | identity | 164 | 33 | 2 | 2 | no_expansion_reduction |
| SDM | swap_SD | 164 | 33 | 2 | 2 | no_expansion_reduction |
| MSD | identity | 164 | 130 | 2 | 3 | fewer_expansions_but_more_native_ticks |
| MSD | swap_SD | 164 | 130 | 2 | 3 | fewer_expansions_but_more_native_ticks |
| MDS | identity | 262 | 194 | 3 | 5 | fewer_expansions_but_more_native_ticks |
| MDS | swap_SD | 262 | 194 | 3 | 5 | fewer_expansions_but_more_native_ticks |
| DSM | identity | 262 | 60 | 3 | 4 | fewer_expansions_but_more_native_ticks |
| DSM | swap_SD | 262 | 60 | 3 | 4 | fewer_expansions_but_more_native_ticks |
| DMS | identity | 262 | 161 | 3 | 5 | fewer_expansions_but_more_native_ticks |
| DMS | swap_SD | 262 | 161 | 3 | 5 | fewer_expansions_but_more_native_ticks |

## 해석

`route_only`와 `input_order`, 동일 학습 memory·관측·config·selector·예산을 두고 native 생성자 use_circuits만 조작했다.
이 스위치는 회로 검색·binding·pool 경쟁·macro 적용 전체 경로를 허용/차단한다. macro 적용만의 순수 효과와 동일하지 않다.
pool/decision network ticks는 raw tick event에서 분리한다. expansion·binding·selector·wall time은 다른 단위로 보존한다.
macro의 span_edges는 실제 적용 span 길이이며 그 숫자를 곧바로 생략된 실행 단계 수로 바꾸지 않는다.
native가 자연스럽게 만든 경로·readout 수·실행 순서를 강제로 맞추지 않는다. 표의 차이는 강제 동기화 결과가 아니다.

## 대안 설명

회로 재사용 분기의 총 효과에는 후보 검색과 경쟁 비용, 적용 길이, 달라진 경로 및 채택 시점이 모두 포함된다.
route_only는 learned judgment drive만 차단한다. 회로 활성화 pool의 학습 routing prior까지 0으로 만들지는 않는다.
공통 예산 상한은 유지하지만 기존 보수적 tick 예약량은 회로 스위치에 의존한다. 예산 종료가 낀 pair는 별도 표시한다.
새 학습이나 회로 형성 전후를 비교한 실험이 아니다. 기존에 학습된 회로의 사용 기여를 시험한 단계다.

## 판별 실험

expansion 감소와 native ticks 증가가 함께 나타나면 network_costs.csv의 pool/decision 분해 및 binding 비용부터 확인한다.
값·채택·지원 signature가 바뀌면 비용 절감 주장을 멈추고 raw의 최초 경로 분기와 proof 선택을 검토한다.
회로 사용 자체가 없으면 새로운 회로를 자동 추가하지 않는다. 노출 실패와 gate overhead를 먼저 기록한다.

## 현재 주장 가능한 범위

동일 입력의 enabled/identity 부모 회귀 6/6. 부모 raw 재검산과 self-test는 신규 독립 연구 결과에 합산하지 않는다.
고정 toy topology 하나와 기존 seed 하나의 24조건이다. LLM·인간 인지·하드웨어 효율 결과가 아니다.
D_DAG는 proof 의존 깊이이다. 에너지·peak memory·최소 goal proof DAG 동형성은 null이다.
완전한 Graph→Circuit 학습·오류 후 장기 재학습·계층 수렴을 확인한 것으로 확장하지 않는다.
