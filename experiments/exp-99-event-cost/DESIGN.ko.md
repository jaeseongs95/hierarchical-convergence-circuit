# R53 / EXP-99 설계: 회로 재사용의 비용 증가는 세는 방식 탓인가, 구조 탓인가

작성 2026-11-20. 이 문서와 [frozen_spec.json](frozen_spec.json)은 본 실행 전에 작성했고 실행 뒤에는 수정하지 않는다. 번호 R53 / EXP-99는 잠정이다.

## 1. 출발점

EXP-09, 25, 26, 44, r16~r18(EXP-62~64), R31(EXP-77)은 같은 결과를 반복해서 보고했다: 회로를 재사용하면 expansion은 줄지만 kernel tick은 늘어난다. R29 ROADMAP은 원인을 구조로 적었다(회로를 적용한 뒤에도 판단 network를 다시 계산한다).

그런데 지금까지의 비용은 전부 동기식·밀집 갱신의 계수다. `src/hcr/dynamics.py`의 `tick`은 매 tick 모든 group을 갱신하고 모든 link에 `signal_transmissions += 1`을 한다. 이미 포화해 움직이지 않는 group도 계속 센다. 이 연구의 동기 문서가 처음 제안한 검증은 "같은 문제를 반복해 풀 때 event 수가 줄어드는가"였고, `docs/CONCEPT_COVERAGE.ko.md` K22(sparse/local/event-driven)는 planned로 남아 있다. 사건 기반으로 센 실험은 저장소에 없다.

따라서 두 설명이 분리된 적이 없다.

- **계수 설명**: 변화가 있을 때만 세면 회로 ON이 더 싸다. 지금까지의 음성 결과는 밀집 계수의 산물이다.
- **구조 설명**: 어떻게 세든 회로 ON이 더 비싸다. pool을 추가로 돌리고 판단을 다시 계산하기 때문이다.

이번 실험은 같은 실행을 사건 기반으로 다시 세어 둘을 가른다.

## 2. 설계 전에 확인한 것 (연구 입력 아님)

EXP-44 `frozen_spec.json`의 `smoke` 입력(연구 입력과 별개인 길이 2 chain)으로 계측기만 점검했다. θ = 0 사건 실행기가 native trace의 5개 network(pool 1, decision 4)에서 tick별 state를 비트 단위로 재현했다. 이때 사건 수는 출력하지 않았고 보지 않았다. ON/OFF 비교도 하지 않았다.

## 3. 고정 조건

- 엔진: `AdaptiveEngine`, `AdaptiveConfig()` 기본값, `src/hcr` 수정 0. `World.measure` 0, revision 요청 0.
- native 실행은 그대로 한다. trace의 `r02_network`(program, drives, top_down)를 꺼내 사건 실행기([tools/r53_event_cost/core.py](../../tools/r53_event_cost/core.py))로 network마다 다시 돌린다.

### 사건 실행기

갱신식은 native와 같다. 매개변수 θ 하나로 밀집 갱신을 send-on-delta로 바꾼다.

- group은 자기 state가 마지막으로 내보낸 값과 θ보다 크게 다를 때만 나가는 link 전부에 전송한다(첫 tick은 전부 전송). 전송 1건 = **link 사건** 1.
- group은 이번 tick에 전송을 받았거나 직전 자기 갱신이 θ보다 크게 움직였을 때만 다시 계산한다. 계산 1건 = **group 갱신** 1.
- 받는 쪽은 보내는 쪽의 현재 값이 아니라 마지막 전송값을 쓴다.
- 종료 규칙은 native 그대로다.

θ = 0이면 정확히 no-op인 계산만 건너뛰므로 궤적이 native와 비트 단위로 같다. θ > 0은 근사이고, 결과가 native와 같은지를 따로 검사한다.

θ 격자: 0, 1e-6, 1e-4, 1e-3, 1e-2.

### 결과 보존 검사

- decision network: (status, goal ≥ 0.5)가 native와 같다.
- pool network: 적격 후보의 정렬된 목록(`activation.py`의 적격 규칙, `expansion.py`의 정렬)이 native와 같다.

한 추론의 모든 network가 보존되면 그 추론은 그 θ에서 "보존"이다. 엔진의 경로 선택은 이 결과에만 의존하므로, 보존된 추론에서는 network별 재실행의 합이 사건 기반 엔진의 비용과 같다. 보존되지 않은 추론은 그 θ의 비교에서 제외하고 수를 보고한다.

**주 θ**: Part A·B의 모든 추론이 보존되는 가장 큰 격자값. 0보다 큰 값이 없으면 0.

### Part A: EXP-44 재현

EXP-44 `frozen_spec.json`의 학습 3개(길이 2·3·4, 증거 1.0)와 평가 3개(길이 2 재명명, 길이 4 + 막다른 분기, 같은 분기 + 마지막 edge 닫힘)를 그대로 쓴다. `route_only`, memory 0/3 × 회로 OFF/ON = 12 평가.

기준점 검사(실패하면 실행 중단): 학습 뒤 회로 1개·strength 0.55, 형성 뒤 native tick이 EXP-44 기록(OFF/ON 33/68, 38/105, 34/95)과 같다.

### Part B: 같은 문제의 반복

동기 문서의 첫 제안에 해당한다. 같은 구조의 문제를 매번 새 ID로 12번 풀고 매번 올바른 feedback을 준다.

- 구조 2종: 길이 2 chain, 길이 4 chain. 증거는 모두 0.92.
- 정책 2종: `route_only`, `legacy`.
- 학습자 2종: 회로 사용 ON, 회로 사용 OFF(같은 학습을 하되 재사용하지 않음).

8계열 × 12 episode = 96 추론. 회로는 3번째 episode의 feedback 뒤에 생기므로 episode 1~3이 "형성 전", 4~12가 "형성 후"다.

## 4. 측정

추론마다 θ별로 link 사건 합과 group 갱신 합(pool/decision 구분), 밀집 계수(native `signal_transmissions`, `group_updates`), tick. link 사건을 주 지표로 하고 group 갱신은 따로 보고한다. 둘을 더하지 않는다. binding 검사, 학습 쓰기, 시간은 사건 단위가 아니라서 이번 비교에 넣지 않는다.

**pool 단독 사건**: ON 추론에서 pool network들의 사건만 합한 값. "회로가 답을 직접 내고 판단 재계산을 생략한다"는 가상의 설계가 치러야 할 최소 비용의 하한으로 쓴다(그 설계의 정확성은 이번에 보지 않는다).

**저장된 회로의 크기**: 형성된 길이 2 pattern의 program(group 수, link 수)과, 길이 2 경로 하나의 primitive 판단 program을 비교한다.

## 5. 사전 예측

- **P1 (계측기)**: θ = 0 재실행이 모든 network의 모든 tick state와 tick 수를 비트 단위로 재현한다.
- **P2**: θ = 0에서는 절감이 거의 없다. 모든 network에서 link 사건 / 밀집 link 계수 ≥ 0.9. (부동소수 state는 종료 허용오차 1e-6에 닿을 때까지 매 tick 바뀔 것이다.)
- **P3**: θ ≤ 1e-3에서는 Part A·B의 모든 추론이 보존되고, θ = 1e-2에서는 보존되지 않는 추론이 있다.
- **P4 (주 예측)**: 주 θ에서 Part A 형성 뒤 3쌍 모두 link 사건이 ON > OFF다.
- **P5**: 주 θ에서 pool 단독 link 사건 ≥ OFF 전체 link 사건인 쌍이 3쌍 중 2쌍 이상이다.
- **P6**: 주 θ에서 Part B의 ON 학습자 4계열 모두, 형성 후(episode 4~12) 평균 link 사건이 형성 전(1~3) 평균 이상이고, 같은 episode의 OFF 학습자보다 크다.
- **P7**: 저장된 길이 2 pattern program의 group 수와 link 수는 길이 2 경로의 primitive 판단 program과 같다(회로 자체에 압축이 없다).

작성자의 예상은 구조 설명이다(P4~P6). 가장 자신 없는 것은 P3의 경계값과 P5다.

## 6. 판정 규칙

주 θ, Part A 형성 뒤 3쌍의 link 사건으로 정한다.

| 조건 | 해석 |
|---|---|
| ON < OFF인 쌍이 2쌍 이상 | `ACCOUNTING_ARTIFACT`: 사건으로 세면 회로 재사용이 싸다. 지금까지의 음성 결과는 밀집 계수의 산물이다. |
| ON ≥ OFF가 2쌍 이상이고, pool 단독 < OFF가 2쌍 이상 | `RECOMPUTATION`: 비싼 이유는 판단 재계산이다. 재계산을 생략하는 설계는 사건 기준으로 이길 여지가 있다. |
| ON ≥ OFF가 2쌍 이상이고, pool 단독 ≥ OFF가 2쌍 이상 | `SELECTION_COST`: 회로를 고르는 계산만으로 이미 답을 처음부터 계산하는 것 이상이다. 재계산을 없애도 이기지 못한다. |
| 그 밖 | `MIXED` |

보존되는 다른 θ 값들에서 같은 규칙을 적용한 해석을 함께 보고하고, 주 θ와 다르면 그렇게 적는다. 결과를 본 뒤 θ 격자·주 θ 규칙·입력·판정 규칙을 바꾸지 않는다.

## 7. 예산과 경계

- native 추론: Part A 학습 3 + 평가 12, Part B 96. worker 1, retry 0, 본 실행 1회, 결정성 재실행 1회.
- 사건 실행기는 계수 모형이다. 실제 사건 기반 하드웨어나 비동기 실행이 아니고, 시간·에너지를 재지 않는다. queue 관리·비교 연산 같은 사건 기반 실행의 부대 비용은 세지 않는다(사건 쪽에 유리한 누락이다).
- θ > 0의 재실행은 network를 따로 돌린 것이다. 결과 보존이 확인된 추론에서만 엔진 전체의 비용으로 읽는다.
- 입력은 EXP-44의 authored toy 3개와 chain 2종이다. 독립 표본이 아니다. 경로 길이 4, edge 8 이하의 작은 문제이고, 큰 문제에서 관계가 뒤집히는지는 보지 않는다.
- pool 단독 하한은 실행하지 않은 가상 설계에 대한 산술이다.
- 검산은 R50 v2 방침: native 이산 결과·tick·판정은 필수 일치. θ > 0 사건 수는 부동소수 비교에 의존하므로 호스트 간 차이를 진단으로 보고하고, 판정이 달라질 때만 실패로 한다.
- 인간의 직관, LLM 내부, 생물학에 대한 주장이 아니다. 설계·구현·실행·검산은 한 작성자(AI 연구 보조)의 한 세션 작업이며 blind 토론·별도 Judge는 없다.
