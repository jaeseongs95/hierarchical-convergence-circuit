# EXP-21 / R0.4.0 — Frontier 스케줄링 개입

## 결론과 연구 질문

코드 기준선은 `ef074f7991733ba0a73d870780d4873718caf1ca`이다. EXP-20의 동결 원자료는
`HCR-Evidence/exp20/r039-20260917T135401_019010Z`이며 raw manifest SHA-256은
`3dd7fcef33f6f9b00af158892d35294ad34311bb4ea9ff7db7d31567cbe05e26`이다.

이전 EXP-20에서는 입력 identity·관측·topology를 고정한 여섯 배열 중 S가 D보다 먼저 놓인
세 조건의 legacy/online이 102 ticks, 나머지는 170 ticks를 사용했다. 기존 native/사후 선택은
모두 170 ticks였다. 이 수치는 이전 실험의 설계 근거이지 EXP-21의 결과가 아니다.
원 출처: 위 기준 커밋의 EXP-20 `analysis/paired.csv`, `analysis/readouts.csv`, `analysis/trials.csv`.

새 질문은 **배열 순서가 frontier의 생성/처리 순서를 통해 경로 완성 시점에 전달되는가?**이다.
더 빠른 solver를 만들어 순위를 매기기보다, 효과의 전달 경로를 분리하는 최소 개입이다.

## 조작과 고정

EXP-20의 동일한 6개 관측을 재사용한다. Node/edge/episode ID·revision·관계·score·world·memory·config·
계산/선택 예산은 그대로다. 입력 순열별 observation digest와 slot은 자연스럽게 달라지며 host가 고치지 않는다.

| 차원 | 조건 |
|---|---|
| 입력 분기 블록 순서 | SMD, SDM, MSD, MDS, DSM, DMS |
| prior | legacy, route_only |
| 채택 방식 | native, posthoc_support, online_support |
| scheduler | input_order, edge_id_min |

본 실험은 6 × 2 × 3 × 2 = **72개 fresh native session**이다. 같은 한 topology의 paired 비교이며
72개 독립 문제나 통계적 표본으로 세지 않는다. 실행 순서는 여섯 scheduler/arm cell을 입력/prior마다
순환 배치하여 사전 동결한다. 반복 timing benchmark나 무작위 표집 실험은 아니다.

## 스케줄러의 정확한 의미

`input_order`는 현재 frontier[0]을 그대로 처리한다. native priority API를 호출하지 않는다.
`edge_id_min`은 **이미 생성된 frontier 경로의 edge-ID tuple 중 사전식 최소값**을 다음 처리 대상으로 고른다.
선택된 항목이 현재 선두가 아니면 기존 공개 API `AdaptiveSession.prioritize_frontier(path)`를 호출한다.
이미 선두면 불필요한 전이를 만들지 않는다. 전체 queue를 한 번에 정렬하지 않고, 매 advance 직전에
다음 head 하나를 선택한다. 선택 대상을 미래의 미생성 경로에서 찾지 않는다.

```text
기존 R037 loop의 실패·계산 예산 검사
→ running 상태의 공개 edge_ids + 등록 frontier_paths 투영
→ 선언된 scheduler로 다음 head 결정
→ 필요할 때만 prioritize_frontier (native event/generation으로 보존)
→ 기존 advance 1회
→ 실제 readout 발생 시 원 판단 보존
→ 기존 native_saved 또는 support_first 적용
→ 채택/보류/계속/종료
```

스케줄러는 score, raw 판단, 세계 정답, S/M/D 라벨, case 이름, 지원 경로 진단을 받지 않는다.
실험 운반 계층에는 world가 있지만 `ScheduledTimingTrial`에는 전달되지 않는다.
ID tuple 정렬이 이 fixture에서 S를 앞세워도, 이것은 **ID에 의한 고정 대조 정책**이지
학습된 탐색이나 의미를 이해하는 최적 스케줄러가 아니다.

첫 루트 frontier는 한 항목뿐이므로 이 개입은 최초 candidate pool의 정책을 바꾸지 않는다.
후보 pool 구성·입력 slot·native 수치 연산·첫 경로 선택은 기존 구현 그대로다. 따라서 격차가 남으면
그 잔여 경로를 조사할 수 있다. 스케줄러를 넣었다는 이유만으로 모든 배열 의존성을 제거했다고 주장하지 않는다.

## Native 보존 및 새로운 audit 경계

`src/hcr`, R035/R037/R038/R039 파일과 과거 raw/analysis를 교체하지 않는다. R040은 R037 `OnlineTrial`
제어 loop와 R038 `TimingTrial` 사후 채택 경계를 재사용한다. 내부 base raw는 scheduler 필드를 가진
`hcr-scheduled-online-r040-v1`로 분리하며, 기존 R038 wrapper 형식은 유지한다.

새 control audit는 생산 scheduler의 함수를 부르지 않고 별도 정렬 명세로 각 결정을 재계산한다.
실제 `prioritize_frontier` 전이는 기존 native session auditor로 재생하고, 추가로 전후 engine document를
비교해 **frontier의 해당 항목을 선두로 옮긴 것 외에 어떤 필드도 바뀌지 않았는지** 확인한다.
Node/parent/binding 수정, dependency 삭제, activation·관측·memory·kernel tick 변경은 거부한다.

기존 proof DAG 의미·가정·D_DAG·selector 예산 검산은 유지한다. R035 가정 수 보고 오류는 R038부터의
검사/지지/비지지 분리를 계속 사용한다. Scheduler나 selector가 실패해도 최초 native candidate는 보존한다.

EXP-20의 36개 원 raw를 별도 capsule로 보존하며, 새 `input_order` 36개가 과거 native 사건 의미·
선택기 view·최종 값·native/selector 계수와 일치하는지 원자료 기준으로 비교한다.
시간과 그로부터 파생된 candidate/trace 봉인 hash의 동일성은 요구하지 않는다.
새 scheduler가 좋아지는 것과 **아무 native 개입도 하지 않은 기준선이 바뀌는 회귀**를 구분한다.

## 평가와 예측

관찰 단위는 경로 완성 순서, 지지 경로 완성 순위·readout 시점, frontier head 선택 열,
최초 지지/차등 기회 시점, 채택/보류/오답, native ticks·advance·expansion, selector inventory,
scheduler inventory이다. 선택이 없거나 기회가 없으면 None/해당 없음으로 유지한다.

H_frontier: 동일 ID 기준으로 다음 frontier를 고르면 순열 간 경로 전개와 ticks 격차가 줄거나 사라질 것이다.
대안: 같은 head 선택에서도 pool/slot/activation 경로 때문에 일부 차이가 남을 수 있다.

이를 `mediation.csv`에 기존/ID-min ticks 범위 폭과 경로 종류를 나란히 기록한다. 파일 이름은 전달 경로
분석을 뜻하며 완전한 인과 매개 분석이나 생물학적 메커니즘의 증명을 뜻하지 않는다.
격차가 원래 0인 조건, 감소하지 않은 조건, 결과가 달라진 조건도 숨기지 않는다.

같은 scheduler 안에서는 native↔사후↔온라인을 비교해 선택 효과와 조기 종료 효과를 유지한다.
다른 scheduler 사이에서는 같은 입력/prior/arm의 차이를 비교한다.
교차 순열의 계산 signature에서는 priority 기록 때문에 달라진 event_seq만 제외하고,
경로·expansion·activation·readout ticks는 유지한다. 원본 event/generation은 모두 별도로 보존한다.

## 비용

Native kernel ticks는 각 session의 최종 누적값을 한 번만 센다. Readout 누적 ticks를 합하지 않는다.
Scheduler의 decision_calls, frontier_items_examined, edge_id_reads, key_comparisons,
priority_transitions, priority_match_scans를 별도 계측한다. priority_match_scans는 native API의
기존 frontier 경로 일치 검사 수다. key_comparisons는 tuple 비교 호출 수이며 문자열·tuple 내부의
모든 원시 CPU 연산 수가 아니다. Projection·딥카피·직렬화·파일 보존의 전체 연산을 포괄하지 않는다.

서로 다른 비용 단위를 더해 총비용/전력 절감이라고 부르지 않는다. 전체 wall time을 순수 kernel 속도로
해석하지 않는다. 독립 auditor의 replay 비용은 task 비용에서 제외한다. 미계측 native capture scan은 null이다.

## 실패 및 실행 원칙

Append-only attempts.jsonl을 flush/fsync하고 각 원 native readout을 selector 호출 전 보존한다.
계약·parsing·dependency·runtime·evaluator 오류는 논리적 보류와 별개로 기록한다.
실패한 폴더나 plan을 재사용하지 않고, 자동 retry·관측 요청·prior 변경·추가 학습·자동 Git 작업을 하지 않는다.

Native self-test는 기존 대조 두 개와 별도 contract probe로 32개 session을 수행하며 본 72회와 분리한다.
32개에는 30개 treatment, 기존 wrapper 대조 1개, 공개 priority API probe 1개가 포함된다.
새 EXP-21 6개 순열을 사전 실행해서 유리한 조건을 고르지 않는다.

Audit 통과는 입력·실행·제어·계수의 정합성을 뜻한다. 순서 효과·기회 발생·정답·격차 감소는 통과 조건이 아니다.
현재 검증 범위는 작은 native toy engine의 선언된 scheduling 개입이며, 새 회로 학습·LLM hidden state·
인간 사고 회로의 검증을 포함하지 않는다.
