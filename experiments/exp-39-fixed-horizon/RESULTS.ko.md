# EXP-39 / R058 결과

## 결론

R057의 12조건을 최초 종료 상태에서 총 512 tick까지 이어 실행했을 때,
모든 조건에서 최초 종료 뒤의 low/high 범주가 유지됐다(`observed`).
initial=.1/.5와 .9 사이의 분리는 start/full, start/drop_P_prefix,
goal/full에서 유지됐고, goal/drop_P_prefix는 세 initial 모두 high였다.
따라서 해당 분리를 최초 종료 직전의 짧은 과도 현상만으로 설명하는 대안은
관측한 512 tick 범위에서 지지되지 않는다.

다만 최초 종료 뒤에도 전 좌표 중 최대 약 `4.11e-6`의 변화가 있었다.
최초 종료를 정확한 고정점 도달로 해석할 수 없다. 이번 결과는 유한시간 지속성의
관측이며 수학적 attractor, basin 경계, 무한시간 안정성의 증명은 아니다.

## 관찰

기준 commit은 `82e152ef290d477ebce90bef700073745749a5ed`다.
실행 전 [설계](design.ko.md)와 [조건](frozen_spec.json)을 동결했다.
실제 연구 실행은 한 번이며, run은
`HCR-Evidence/exp39/r058-20260919T233747Z-4393c4f8bc`다.

최초 종료까지의 12개 prefix packet은 R057 anchor와 abs/rel `1e-12` 기준으로
일치했다. 이후 같은 갱신식·상태·안정 counter를 유지하면서 중단만 해제했다.
재현 prefix와 새 continuation을 두 독립 표본으로 세지 않는다.

다음 값은 표시 자릿수에서 반올림했으며 원자료에는 전체 정밀도를 보존했다.
mask의 drop은 `drop_P_prefix`다.

| 방향 | initial | mask | 최초 종료 tick | 최초 goal | goal@160 | goal@512 | 범주 유지 |
|---|---:|---|---:|---:|---:|---:|---|
| start | .1 | full | 70 | .026117248 | .026118233 | .026118233 | low |
| start | .1 | drop | 73 | .028676252 | .028677490 | .028677490 | low |
| start | .5 | full | 60 | .026117211 | .026118233 | .026118233 | low |
| start | .5 | drop | 62 | .028676196 | .028677490 | .028677490 | low |
| start | .9 | full | 37 | .982017175 | .982016770 | .982016770 | high |
| start | .9 | drop | 38 | .981604386 | .981604023 | .981604023 | high |
| goal | .1 | full | 75 | .013283164 | .013283277 | .013283276 | low |
| goal | .1 | drop | 99 | .986807810 | .986807900 | .986807900 | high |
| goal | .5 | full | 116 | .013283387 | .013283277 | .013283276 | low |
| goal | .5 | drop | 75 | .986807809 | .986807900 | .986807900 | high |
| goal | .9 | full | 38 | .987482975 | .987482938 | .987482938 | high |
| goal | .9 | drop | 60 | .986807984 | .986807900 | .986807900 | high |

범주 유지는 checkpoint 두 곳뿐 아니라 최초 종료 직후부터 512까지 모든 tick에서
확인했다. 불일치 tick은 0개다. 160/512 checkpoint는 12조건 모두 사전 안정 기준을
충족했으며, 512의 residual은 부동소수점 계산에서 모두 0이었다.
이 값은 수학적 실수 연산의 정확한 고정점이나 반올림 오차 부재를 뜻하지 않는다.

512에서 initial=.9−.5의 goal 차이는 start/full `+.9558985362`,
start/drop `+.9529265329`, goal/full `+.9741996611`이다.
goal/drop은 약 `+1.11e-16`이며 두 조건 모두 high다.
initial=.1−.5의 goal 차이는 네 방향·mask 조합에서 계산상 0이다.

최초 종료 대비 전 좌표의 최대 절대 변화량은 goal/.1/full에서
`4.11269140704329e-6`이었다. 한 tick의 residual 종료 기준 `1e-6`을
이후 누적 상태 변화량의 상한으로 사용할 수 없다는 구체적 사례다.

| 비용 counter | 최초 종료까지 | 추가 continuation | 합계 |
|---|---:|---:|---:|
| kernel_ticks | 803 | 5,341 | 6,144 |
| group_updates | 4,015 | 26,705 | 30,720 |
| normalization_ops | 4,015 | 26,705 | 30,720 |
| signal_transmissions | 6,017 | 40,063 | 46,080 |

각 행은 같은 단위끼리만 합산했다. 출처 replay·smoke·검산 비용은 포함하지 않았다.
이 counter들을 실행시간·실제 에너지 또는 하나의 총 계산량으로 변환하지 않는다.

## 해석

R057에서 확인한 초기 상태별 분리는 이번 동결 recurrence 아래에서 512 tick까지
지속됐다. 유한시간 지속성은 `observed`, 서로 다른 안정 상태로 향하는 계산 구조라는
설명은 이 관측과 양립하지만 수학적 안정성·국소 복원력은 아직 별도 검증 대상이다.

R057의 맥락적 필요성 판정도 유지된다. goal 방향의 initial=.1/.5에서는
full low/drop high지만 initial=.9에서는 full/drop 모두 high다.
start 방향에서는 initial=.1/.5가 full/drop 모두 low, .9가 모두 high다.
이를 초기 상태와 무관한 경로 필요성이나 일반적 원인으로 확장하지 않는다.

## 대안 설명

512 이후에 변화하는 긴 과도 상태, 부동소수점 연산에서 멈춘 상태,
교란에 취약하지만 외부 교란 없이 유지되는 상태는 이번 결과와 양립한다.
또한 관측된 분리는 특정 synthetic program·drive·bias·갱신식의 성질일 수 있다.
초기 조건과 parameter를 더 넓게 조사하지 않았으므로 일반적 basin 구조를 추정하지 않는다.

## 판별 실험

다음 후보는 goal/full의 initial=.5와 .9에서 얻은 512 상태를 각각 출발점으로 삼는
국소 교란 실험이다. 동일 program에서 각 다섯 좌표에 하나씩 `±1e-4`를 적용하고
각 출발점의 무교란 대조를 포함하면 22개 branch가 된다. 상태 범위를 먼저 확인하고
clipping 없이 실행 가능한 조건, 128 추가 tick, 대조 궤적까지의 거리와 복원 판정 기준을
실행 전에 동결해야 한다. 교란 후 대조 상태로 가까워지는지 비교하면 단순 지속성과
유한시간 국소 복원력을 구별할 수 있다. 이는 결과를 본 뒤 정한 후속 제안이며,
이번 R058에서 실행하거나 성공을 예측한 실험이 아니다.

## 현재 주장 가능한 범위와 검증

주장 범위는 명시적 synthetic 계산 장치의 12조건에서 확인한 유한시간 상태 지속성이다.
native packet/proof/support/raw decision/adoption 및 실제 에너지는 `null`이다.
LLM 내부 계산, 인간 인지, 학습된 Circuit 형성·재사용, HCC 전체 가설의 직접 증거가 아니다.

오케스트레이션 적용 방식과 역할 범위는 [기록](ORCHESTRATION.ko.md)에 남겼다.
수치 검산은 별도 recurrence와 프로세스를 사용하지만 구현자는 같으며 독립 연구자 감사는 아니다.

- synthetic self-test 22개 통과. 별도 smoke 4행 및 prefix bridge 4개 통과.
- 최종 core regression 1회: 602개 중 599개 통과, 기존 Windows symlink skip 3개 유지.
- 연구 12행의 prefix bridge와 모든 continuation tick·상태·residual·counter 독립 수치 검산 통과.
- raw에서 checkpoint·범주·drift·대조 차이·비용 집계를 별도로 재확인했다.
- source 268파일, bundle hash 대상 629파일, ZIP 630파일의 목록·내용·무결성을 확인했다.
- 연구 재실행이나 결과 확인 후 조건 변경은 없었다. 기존 core·tests·historical evidence는 수정하지 않았다.

근거: run의 `analysis/audit.json`, `analysis/summary.ko.md`, raw 및 manifests,
`HCR-Evidence/r058-validation/delivery-verification.json`.
이 결과 문서는 실행 후 해석이며 사전 source manifest나 동결 bundle에 소급 편입하지 않는다.
