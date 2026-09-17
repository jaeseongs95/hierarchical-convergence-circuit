# R0.3 — 제한된 M 전문화와 중간 경로 교환

## 1. 무엇을 이어받았는가

EXP-10은 같은 버전의 legacy/continuous/resumed에서 판단·proof·memory·기존 연산 의미를 보존했다.
main의 저장/복원 비용은 약 3.616초였고, 이 값은 디스크뿐 아니라 검산·직렬화·복원 비용을 포함했다.
따라서 처리기 교대 자체는 메모리 내 session 진행으로 구현하고 디스크 checkpoint를 강제하지 않는다.
이 분석은 이전 commit `189d3ffcf491b6068b64dfe788c3b973e3aba6b7`의 결과에 관한 것이며 R0.3 성능 결과가 아니다.
현재 소스 기준은 그 분석을 반영한 `309828118509340572b946dfa60e8cde1f16e452`다.

EXP-09의 prior 오수렴·부분회로 재선택·pool 비용은 이번에 고치지 않는다.
학습, prior, kernel을 그대로 둬서 무엇이 처리 순서·협력 때문에 변했는지 구분한다.

## 2. 처리기와 정책

| 처리기 | 정책 | 고정하는 것 |
|---|---|---|
| Sequential | primitive 1 edge, 가장 짧은 frontier 우선(breadth-first) | 같은 Observation, seed memory, primitive proof, kernel |
| Associative | 기존 learned macro 우선, 기존 깊이우선 frontier 순서 | 같은 memory와 기존 prior·활성 경쟁 |
| 고정 통합 | 가능한 처리기를 round-robin으로 진행 | 두 처리기의 합계 예산 |
| 적응 통합 | 미수신 경로 힌트 → 공개 mismatch → 오래 기다린 처리기 순 | 숨은 정답·case label 접근 없음 |

Sequential/Associative는 사람이 정한 두 profile이다. 두 정책의 여러 구성 차이를 각각 독립 M축 효과로 해석하지 않는다.
`fixed_no_messages`, `adaptive_no_messages` 대조를 별도로 두어 중간 교환의 효과는 고정된 두 profile에서 구분한다.
자체적인 새 알고리즘 발견, A/M의 일반 독립성 증명, OS 병렬 실행이 아니다.

## 3. 중간 상태가 실제로 어떻게 전달되는가

1. sender가 기존 `advance()`로 생성한 selected path를 읽는다.
2. `RouteHint`에 입력 digest/revision, memory digest, R0…Rn 역할-객체 대응, edge evidence refs, source event와 generation을 기록한다.
3. receiver는 이 메시지를 검증하고 자신의 **이미 존재하는 frontier 중 해당 경로의 prefix**를 우선한다.
4. receiver는 자기 정책으로 남은 edge를 실행한다. sender의 값·prior·activation·proof를 자기 사실로 복사하지 않는다.
5. 상태 교환은 `r03_message`, 소비는 `r03_scheduled`, 실제 순서 변경은 `r03_frontier_prioritized`로 연결된다.

메시지는 한 번 받은 뒤 작업 동안 경로 안내로 유지할 수 있다. 이를 새 증거로 재집계하거나 activation drive에 반복 가산하지 않는다.
각 worker의 node ID는 독립이다. 같은 문자열이라는 이유로 타 worker node를 자기 node로 사용하지 않고, 공통 공개 edge·role에 대한 명시적 대응을 사용한다.
기존 frontier의 순서만 바꾸며 생성/삭제/ID 자동 보정은 없다. 구조 학습·회로 간 영구 연결은 R0.4 범위로 남긴다.

## 4. 예산 계약

주 비교는 모든 arm에 같은 **총 상한 벡터**를 준다.

| 조건 | 전체 advance 상한 | 전체 kernel tick 상한 | 전체 메시지 상한 |
|---|---:|---:|---:|
| standard | 12 | 2048 | 64 |
| limited | 4 | 480 | 64 |

결합 조건의 두 worker 합계를 센다. 각 worker에 두 배로 배정한 뒤 winner 비용만 보고하지 않는다.
단위가 다른 expansion/tick/signal/binding을 임의 가중치로 한 수치에 합산하지 않는다.
모든 연산 카운터는 보고하되 hard limit은 위 세 항목이다. wall-time이나 RAM의 동일 상한을 보장한다고 주장하지 않는다.

기존 advance 내부를 임의 tick에서 중단하지 않기 위해 **실행 전에 worst-case tick을 예약**한다.
primitive는 최대 decision settle 1회, 회로 사용 시 pool 1회 + decision 1회다. 예약 후 실제 tick만 차감한다.
이미 계산하고 예산 초과분을 지워버리는 preview/rollback은 없다.
이 때문에 남은 예산이 실제 필요한 양보다 커도 보수적인 예약을 충족하지 못하면 시작하지 않는다.
`conservative_tick_admission`과 `unused_kernel_ticks`를 기록하며 이를 intrinsic 계산 실패나 최적 예산 배분으로 해석하지 않는다.

Session deepcopy·JSON hash·스케줄·메시지 검증 등의 관리 비용은 `total_wall_seconds`에 포함된다.
기존 `cost.wall_seconds`와 별개인 `management_seconds`도 기록한다. 디스크 교대 비용 0은 관리 비용 0을 의미하지 않는다.

## 5. 통합과 오류

한 방법만 있는 조건은 그 결과를 그대로 반환한다.
결합 조건에서는 모든 worker가 완료하고 비보류 값이 같으면 agreement다. 서로 다르면 `conflict_abstention`, 미완료/보류가 있으면 `incomplete_or_ambiguous`다.
같은 답 두 개를 새로운 외부 근거로 보지 않는다. 실제 정답은 실행 완료 후 독립 world evaluator가 판정한다.
첫 provisional result와 최종 통합 결과를 구분한다. 오답 provisional → 통합 보류는 정답 수정 성공이 아니다.
부정 결론은 원래 worker의 coverage 조건을 충족해야 한다. 임의의 합성 proof를 새로 만들지 않고 component proof들을 보존한다.
여러 회로가 이미 안정 오답에 도달한 후 학습·재시도시키는 새 기능은 추가하지 않았다.

## 6. 상태·스키마

기존 R0.2.1 `begin/advance/finish/feedback/request_revision` 동작은 보존한다.
`prioritize_frontier`가 없는 packet은 기존 `hcr-session-checkpoint-r021-v1`이다.
새 전이가 들어간 worker packet은 `hcr-session-checkpoint-r03-v1`으로 구분한다.
복원 시 스키마·소스·계보·frontier·counter를 검사하며 과거 hash를 현재 값으로 보정하지 않는다.
개별 worker의 snapshot은 가능하지만 **두 worker·mailbox·shared budget 전체 coordinator resume**는 이번 범위에 없다.

## 7. 생성기와 평가기

- `methods.py`: 총예산, worker 교대, 공개 상태에 따른 정책.
- `integration.py`: typed 경로 hint와 보수적 통합 계약.
- `runtime.py`, `sessions.py`: 기존 frontier 순서 변경의 원자적 API만 추가.
- `evaluation/session_audit.py`: 새 우선순위 전이를 기존 독립 상태 replay에 추가.
- `evaluation/method_audit.py`: 생성 함수를 import하지 않고 스케줄/메시지/예산/통합을 재계산.
- `evaluation/method_protocol.py`: seed·고정 fixture·외부 평가·원시 결과 보존.
- `method_cli.py`, `Run-HCR-R03.ps1`: 실행 연결.

감사기는 session 수치 replay를 재사용한다. 모든 모듈을 독립 개발했다고 주장하지 않는다.
벽시계 시간은 기록 범위만 검산하고 재현하지 않는다. aggregate source hashes는 수치 실행·감사 코드를 동결한다.

## 8. 실험 수용 기준

7개 authored 사례 × 6개 arm × 2개 예산 = 84개 method 비교다. 실제 worker attempt는 140개다.
먼저 6개 seed 학습 episode를 수행하며 그 memory를 모든 비교에서 동결한다.
fixture는 familiar, counterfactual, longer, fork, weak_conflict, unknown, diamond다.
각 cell은 wall-time 1회 기록이므로 속도 일반화는 하지 않는다. 순서가 다른 반복은 별도 run으로 수행한다.

완료는 실행·기록·검산 성공이다. 결합이 단독보다 우세하거나 adaptive가 fixed보다 우세해야만 통과하는 조건을 만들지 않는다.
message on/off에서 실제 경로 변화가 없거나 손해가 생겨도 그대로 데이터로 남긴다.

## 9. 다음 판별 질문

메시지가 실제로 바꾼 frontier, 절감/추가된 연산, conflict 보류, 사용하지 못한 예약 여유를 각각 분석한다.
개선이 없으면 M 설계를 수정하며, 이를 근거 없이 '검증 완료'로 처리하지 않는다.
prior의 routing/판단 역할 분리, 음의 예외 학습, pool 최적화는 각각 별도 개입으로 남긴다.
