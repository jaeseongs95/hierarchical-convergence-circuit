# R52 / EXP-98 설계: 경로가 둘인 과제에서 수렴 지연과 입력 규칙을 다시 겨루기

작성 2026-11-20. 이 문서와 [frozen_spec.json](frozen_spec.json)은 본 실행 전에 작성했고 실행 뒤에는 수정하지 않는다. 번호 R52 / EXP-98은 잠정이다.

## 1. 출발점

[R51 / EXP-97](../exp-97-slowdown-signal/RESULTS.ko.md)은 수렴 지연(kernel tick)이 "회로를 끄면 판단이 달라지는 입력"을 잘 가려내지만, 2-edge chain에서는 "증거가 0 이하인 edge가 있으면 보류"라는 입력 규칙과 정확히 같은 셀을 고른다고 보고했다(`SLOWDOWN_REDUNDANT_HERE`). 그 결과 문서는 한계도 적었다: chain에서는 회로 OFF의 판단이 둘째 edge 증거의 부호 하나로 정해져서, tick이 입력 규칙을 이길 수 있는 조건이 시험 집합에 없었다.

이번에는 그 지름길이 깨지는 과제를 쓴다. diamond(출발 q0 → q1 → 도착 q3, 또는 q0 → q2 → q3)에서는 한 경로의 증거가 음수여도 다른 경로가 온전하면 회로를 끄든 켜든 True다. 단순 입력 규칙은 그런 입력까지 보류해 정상 재사용을 잃을 것이고, tick은 실제로 회로와 증거가 맞설 때만 커질 수 있다.

## 2. 설계 전에 확인한 엔진 동작 (빈 조건 1회 호출)

n=3 memory, 네 edge 모두 1.0인 diamond에서 ON·OFF 한 번씩 호출해 구조만 확인했다.

- pool에 두 경로(edge 0-1, edge 2-3)가 후보로 함께 올라오고 서로 억제한다. 동률이면 첫 경로가 선택된다.
- ON은 선택한 경로 하나로 True가 나오면 거기서 멈춘다(expansion 1). OFF는 primitive 전개 2회로 첫 경로에서 True를 얻고 멈춘다.
- pool 호출 1회, decision network 1회. tick은 pool 32 + decision 33.

이 호출의 판단값·tick은 증거로 쓰지 않는다.

## 3. 고정 조건

- 엔진: `AdaptiveEngine`, `AdaptiveConfig()` 기본값, `legacy`, `FROZEN_EVAL`. `src/hcr` 수정 0. `World.measure` 0, revision 요청 0.
- memory: R50·R51과 같은 chain 학습(진실한 양수 2-edge chain 20개)의 snapshot. 회로는 chain에서 배운 길이 2 pattern 하나이고, diamond의 두 경로에 각각 묶인다(다른 구조로의 재사용).
- 관측: diamond의 edge 순서는 (q0→q1, q1→q3, q0→q2, q2→q3). 첫 edge 둘은 1.0으로 고정하고, **둘째 edge 둘의 증거 a1(경로 A), b1(경로 B)** 을 각각 {−0.5, −0.4, …, 1.0} 16점으로 바꾼다. 16 × 16 = 256 입력.
- 보정 memory: n ∈ {3, 9}. 시험 memory: n ∈ {6, 8, 15, 20}. ON 평가 6 × 256 = 1,536, OFF 평가 256.

## 4. 정의 (R51과 동일)

- **적용 대상 셀**: ON 실행에서 회로가 한 번이라도 적용된 셀.
- **표적**: 적용 대상 셀 중 ON 채택값 ≠ OFF 채택값. 유형: 포획형(ON True, OFF True 아님), 미결정형(ON None), 기타.
- **보류**: 신호 ≥ 문턱이면 OFF 결과를 채택. 새 정보 없음.
- **재사용 보존율**: 비표적 적용 대상 셀 중 보류되지 않은 비율.

## 5. 신호

| 이름 | 정의 | 필요한 것 |
|---|---|---|
| `ticks_total` (주 신호) | pool + decision tick 합 | ON 실행 |
| `ticks_pool` | pool tick 합 | 회로 적용 전 |
| `ticks_decision` | decision tick 합 | ON 실행 |
| `simple_any` | −min(네 edge 증거). "어느 edge든 증거 ≤ 0이면 보류" | 입력만 |
| `selected_route` | −min(적용된 회로가 묶은 edge들의 증거). "쓴 경로에 증거 ≤ 0인 edge가 있으면 보류" | 입력 + 어느 회로를 썼는지 |
| `structure_aware` | −max over 경로 [min(그 경로 edge 증거)]. "모든 경로에 증거 ≤ 0인 edge가 있으면 보류" | 입력 + 전체 경로 구조 |
| `goal_margin` | −\|2·goal − 1\| | ON 실행 (음성 대조, R51에서 무용) |

`structure_aware`는 사실상 회로 없이 그래프를 손으로 푸는 규칙이라 가장 강한 경쟁자다. 일반 과제에서 이 규칙을 계산하려면 경로를 모두 전개해야 하므로 회로를 쓰는 이득(expansion 절감)과 양립하지 않는다는 점이 tick과의 차이다.

## 6. 문턱

두 가지를 모두 보고한다.

- **이월 문턱**: R51이 chain에서 정한 값 그대로. `ticks_total ≥ 70`, `ticks_pool ≥ 35`, `ticks_decision ≥ 35`, 입력 규칙 셋은 "min ≤ 0". `goal_margin`은 이월 문턱이 모든 셀을 보류시키는 값이었으므로 이월 평가에서 제외한다.
- **재보정 문턱**: 보정 memory(n = 3, 9)의 diamond 표적 셀에서 신호의 최솟값(R51과 같은 규칙).

## 7. 측정

시험 memory 4개의 적용 대상 셀에서 신호별로 (1) AUC(주 지표, 문턱 무관), (2) 두 문턱 각각의 재현율·재사용 보존율, (3) 재보정 문턱 기준 always-ON / always-OFF / gate의 tick 합·expansion 합.

## 8. 사전 예측

- **P1**: `simple_any`는 이월 문턱(min ≤ 0)에서 재현율 1.0이지만 재사용 보존율 < 0.7이다(다른 경로가 판단을 지탱하는 입력까지 보류).
- **P2**: `ticks_total`의 시험 AUC ≥ 0.80.
- **P3**: `ticks_total` AUC − `simple_any` AUC ≥ 0.05.
- **P4**: `structure_aware` AUC ≥ `ticks_total` AUC. 가장 강한 입력 규칙은 여전히 tick 이상이다.
- **P5**: 이월 문턱 70은 diamond에서 무너진다: `ticks_total`의 재현율 < 0.9 또는 재사용 보존율 < 0.5. pool에 후보가 둘이라 기본 tick 수가 chain과 다를 것이라는 예상이다. (R51에서 같은 종류의 예측 P3을 틀렸다. 이번에도 틀릴 수 있다.)
- **P6**: `selected_route`의 AUC는 `simple_any`보다 크고 `structure_aware`보다 작거나 같다.

작성자가 가장 자신 없는 것은 P4와 P5다.

## 9. 판정 규칙

시험 AUC 기준, 차이 0.05를 경계로 한다.

| 조건 | 해석 |
|---|---|
| P2 falsified | `NOT_A_SIGNAL_ON_DIAMOND` |
| `ticks_total`이 `simple_any`와 `selected_route` 둘 다보다 0.05 이상 크고, `structure_aware`보다 0.05 넘게 작지 않음 | `SLOWDOWN_MATCHES_STRUCTURE_AWARE`: 경로 구조를 몰라도 구조를 아는 규칙만큼 가려낸다. tick 신호의 고유 가치에 대한 첫 근거. |
| `ticks_total`이 두 단순 규칙보다 0.05 이상 크지만 `structure_aware`보다 0.05 넘게 작음 | `SLOWDOWN_BETWEEN`: 단순 규칙보다는 낫고 구조를 아는 규칙에는 못 미친다. |
| 그 밖 | `SLOWDOWN_REDUNDANT_AGAIN`: 경로가 둘이어도 값싼 입력 규칙이 tick만큼 한다. |

결과를 본 뒤 격자·memory 분할·주 신호·규칙을 바꾸지 않는다.

## 10. 예산과 경계

- 학습 20 episode(feedback 20), 평가 1,792. worker 1, retry 0, 본 실행 1회, 결정성 재실행 1회.
- diamond 하나, 첫 edge 둘은 1.0 고정, 회로 하나의 결정적 격자 비교다. 독립 표본이 아니고 AUC는 이 격자의 순위 통계다. 격자 간격 0.1.
- 경로 둘이 같은 pattern을 쓰는 대칭 구조다. 경로 길이가 다르거나 회로가 여럿인 경우는 보지 않는다.
- 보류는 여전히 새 정보 없이 OFF를 채택하는 것이라 R51에서 본 영합(닫힌 세계의 포획 오답 제거 = 열린 세계의 올바른 보완 상실)은 그대로다. 이번 실험은 "어떤 신호로 보류 대상을 고르는가"만 비교한다.
- 검산은 R50 v2 방침: 이산 결과와 tick은 필수 일치, 부동소수 마지막 자리는 진단.
- 인간의 직관, LLM 내부, 생물학에 대한 주장이 아니다. 설계·구현·실행·검산은 한 작성자(AI 연구 보조)의 한 세션 작업이며 blind 토론·별도 Judge는 없다.
