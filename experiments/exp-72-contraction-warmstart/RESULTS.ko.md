# EXP-72 / r26 결과: 수축률 선별은 이번 품질을 보존했지만 총비용은 늘었다

**현재 구현은 채택하지 않는다.** AI Research SSH에서 입력별 exact-rational 수축 상계로 이전 수렴 state의 초기값 재사용을 선별했다. `guarded`는 고정 24조건에서 reset과 종료 상태·답을 보존하고 terminal state 차이도 실행 전 기준 1e-4 이하였다. native tick은 488→448로 40회(8.20%) 줄었지만, gate와 상태 관리를 포함한 component CPU는 6.523→11.110ms로 70.31% 늘었다. 반면 무조건 `carry`는 중립 입력 8조건에서 답을 바꾸고 tick도 늘었다. 계산량 감소와 실제 비용 감소를 구별해야 한다.

## 개입과 실행

R25의 정확 고정점 산술 생략을 개선하거나 반복하지 않았다. EXP27의 A→B 상태 전달 및 EXP38의 초기값 의존성에 더해, **현재 drive만으로 계산하는 전역 수축 상계**를 재사용 전 조건으로 추가한 것이 이번 개입이다. 상세 수식·입력·판정은 실행 전 고정한 [design.ko.md](design.ko.md), [frozen_spec.json](frozen_spec.json)을 따른다.

원 R19 lower template와 config, `src/hcr/dynamics.py`, native settle controller/history/patience는 그대로다. 상태 재사용은 결과 cache가 아니라 초기값 변경이다. 모든 tick을 원 native 함수가 실제 계산했다. strong/weak × positive-first/negative-first의 4stream에 각각 같은 부호 두 입력→중립→반대 부호 두 입력→중립을 배치하고, reset/carry/guarded를 고정 순환 순서로 한 번씩 실행했다. stream·arm별 state는 분리했다. 학습과 World.measure는 0회다.

AI Research SSH `aws-local`에서 기존 요청 `52338b35ef20112d00f30e87bf77123f935675e61f968665`가 소유자 승인(`owner`)으로 완료됐다. 인증 오류 동안에는 실행 여부를 알 수 없었으며, 연결 복구 뒤 이 요청의 결과를 조회했다. 재전송·재실행하지 않았다. Linux/Python 3.12.3, worker 1, retry 0이었다.

준비→4stream→검산의 6단계가 모두 exit 0이었다. 총 72 native settle / 1,652 tick으로 상한 72회 / 11,520 tick 안에 있다. 서버 completion의 봉인 포함 시간은 1.214초, 6단계 child CPU 합은 0.889651초, stage 종료 시 raw 누적 최댓값은 452,010bytes였다. 600초 전체·60초 stage 상한을 지켰다. 부모와 준비 child의 AS 512MiB 및 개별파일 32/16MiB 한도를 기록했다. 이는 peak RSS, hard disk quota 또는 모든 OS 실패의 봉인 보증이 아니다.

## 품질과 계산량

품질 기준은 reset과 같은 종료 status/adopted 값 및 terminal state 최대 절대차 1e-4 이하다. 외부 정답이나 학습 성능을 검사한 기준은 아니다.

| 방식 | native settle | warm 시작 | gate | tick | group/normalization | signal | 품질 불일치 / 답 변경 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| reset | 24 | 0 | 0 | 488 | 1,464 / 1,464 | 1,952 | 0 / 0 |
| carry | 24 | 20 | 0 | 716 | 2,148 / 2,148 | 2,864 | 8 / 8 |
| guarded | 24 | 6 | 20 | 448 | 1,344 / 1,344 | 1,792 | 0 / 0 |

guarded는 강한 입력에서만 6번 warm 시작했다. 이때 유리수 q 상계는 약 0.87625로 고정 threshold 19/20 이하다. 중립·약한 입력에서는 약 1.91125여서 재사용을 거부했다. 큰 상계는 비수축의 증명이 아니라 이번 충분조건이 성립하지 않았다는 뜻이다. 4개의 첫 입력은 과거 state가 없어 gate 없이 reset했다.

강한 각 stream에서 reset의 112 tick을 guarded가 92 tick으로 줄였다. 같은 부호의 두 번째 입력(step1/4)은 각각 26→16 tick이었고, 부호를 바꾸는 step3은 26→26으로 줄지 않았다. 약한 각 stream에서는 모두 reset하여 132→132 tick이었다. guarded의 terminal state 최대 차이는 약 2.581e-7, 약한 stream은 0이었다. reset을 고른 18조건은 전체 kernel record가 reset arm과 타입·float bit까지 동일했다.

carry의 품질 불일치 8개는 네 stream의 중립 step2/5였다. reset은 4 tick 뒤 `stable_ambiguous`/`None`이지만, carry는 40~41 tick 뒤 이전 부호를 따른 `stable_decision`/True 또는 False였다. strong_positive_first의 step2에서는 terminal 최대 차이가 약 0.47363이었다. 따라서 무조건 state를 전달하는 정책은 이 reset 기준의 답 보존 조건을 만족하지 않는다. 이 차이를 실제 세계의 오답으로 단정하지 않는다.

## gate를 포함한 비용

| 방식 | component CPU (ms) | component wall (ms) | 그중 gate CPU (ms) | reset 대비 CPU |
| --- | ---: | ---: | ---: | ---: |
| reset | 6.523254 | 6.491059 | 0 | 1.0000배 |
| carry | 8.393033 | 8.362286 | 0 | 1.2866배 |
| guarded | 11.109569 | 11.078949 | 4.722266 | 1.7031배 |

gate 시간은 component 전체에 이미 포함되므로 다시 더하지 않는다. guarded wall 비율은 1.7068배다. component 경계는 drive 생성·gate·source 검사·initial 선택·native settle/trace 복사·결과 구성·private cache 갱신을 포함한다. 공통 program/config 준비, import, raw JSON 저장, 최종 audit/봉인은 밖이며 위 실행 단계 비용에 별도로 남겼다. 서버 전체 처리와 component 시간을 같은 값으로 표현하지 않는다. 학습 비용은 이번에 0이므로 학습이 있는 방법의 총비용 결론으로 확대하지 않는다.

| stream | reset tick → guarded tick | reset CPU → guarded CPU (ms) |
| --- | ---: | ---: |
| strong_positive_first | 112 → 92 | 1.658393 → 2.633307 |
| strong_negative_first | 112 → 92 | 1.428460 → 2.631289 |
| weak_positive_first | 132 → 132 | 1.651180 → 3.038927 |
| weak_negative_first | 132 → 132 | 1.785221 → 2.806046 |

4stream의 실제 prefix K=1..6도 원자료에 모두 보존했다. gate가 누적되는 K=2..6의 20개 prefix 중 guarded의 CPU가 reset보다 작은 경우는 없었다. K=1은 둘 다 cold여서 gate 효율의 근거가 아니다. cell별 한 번의 작은 고정 부하에서 나온 관측이므로 통계적 지연·속도 차이나 일반화는 확립하지 않았다. 유리한 cell만 골라 순이득을 선언하지 않는다.

carry의 state read/write는 60/72개, guarded는 18/72개였다. 둘 다 stream·arm당 state 값의 logical payload peak는 24bytes다. Python 객체·Fraction·metadata·allocator 및 실제 메모리 사용량은 이 숫자에 포함되지 않는다. 차원이 다른 tick·signal·bytes·시간을 하나의 비용으로 합치지 않았다.

## 검증과 출처

서버 준비의 순수 경계·수식 검사 35개가 통과했다. 별도로 기록된 initial에서 모든 궤적을 scalar 수식과 원 종료 규칙으로 재생하고, 독립 전개의 유리수 bound·source provenance·Cost·입력 순서를 검산했다. gate/initial/state/cost/source/order/timing 변조 7종을 각각 의도한 사유로 거부했다.

수신한 4stream, preparation, result, summary의 **7개 JSON 전체 bytes**가 서버 raw manifest의 SHA-256과 일치한다. 로컬 [저장 결과 검산](../../evidence/contraction-warmstart-20261019-r26/local-replay.json)도 이 7개 hash, 실행 전 동결 source 96개와 입력·결과 결속, 모든 scalar 궤적, 집계/prefix 및 7종 변조를 확인했다. 새 native 호출·시간 측정은 없었다. Linux 서버 scalar 최대 오차는 0, Windows 로컬 재생은 약 1.388e-17로 고정 허용치 1e-15 이하였다. 로컬 helper `replay_saved.py`는 서버 실행 이후 추가했으며 서버 ZIP에 들어 있지 않았다.

CS 불변조건 3개와 같은 동결 후보 6파일의 구현자 검토 및 `check-bundle`이 PASS다. CLI는 원시 파일 digest와 계약·근거의 일관성을 확인한다. 독립 감사, 정책 권한 인증 또는 수학/실행 내용의 진실성 증명으로 취급하지 않는다. 해당 묶음과 검증 receipt는 [evidence](../../evidence/contraction-warmstart-20261019-r26/)에 있다.

송신 source ZIP은 285,199bytes, SHA-256 `6fa7f7efcbf9d131afc7f59efbad8a3b86a5ec58f438e8f5e32508df39cbd265`다. 실행 전 manifest hash는 `4d3f59c50a161e0b00d49c28cf90964aecb09ba073898c273b2949df2fdca5f1`이고 송신 사본을 `source_manifest.pre-frozen.json`으로 구별했다. 서버 result도 이 hash와 source_unchanged=true를 보고했다. 원격 source manifest/postcheck의 전체 내용을 다시 수신해 비교한 것은 아니다.

수송 adapter는 redacted 결과와 upstream completeness unknown을 표시한다. 7개 핵심 JSON은 개별 hash로 완전성을 대조했지만, manifest 자체는 같은 채널의 출처이며 독립 서명이 아니다. 전체 원격 evidence ZIP, stdout/stderr 12개 및 source-postcheck의 원문은 수신하지 않았다. completion이 보고한 ZIP은 73,329bytes / SHA-256 `e46280bd88fa573956831055dae90f097a2d19a49061a8727e86577cc74ce2c7`이며, 이를 로컬에서 내려받아 검증했다고 주장하지 않는다. 인증 실패의 원인은 확정하지 않았다.

## 후속 판단

재사용 전에 현재 입력을 검사하는 개입은 이번 유한 조건에서 무조건 carry의 이력 의존 차이를 피하고 실제 tick 일부를 줄였다. 그러나 **전역 실수 map의 contraction은 native 반올림·유한 종료·답 보존의 certificate가 아니다.** 품질 보존은 여기서 관측한 24조건의 결과이며 임의 프로그램·입력·수명에 대한 보장이 아니다.

다음 질문은 gate를 더 정교하게 만드는 것보다 **품질 허용 오차·margin·남은 종료 예산을 함께 고려한 유한 실행 오차 경계가 가능하며, 그 판별 비용을 줄일 만큼 재사용할 계산이 실제로 충분한가**다. 작은 kernel에서는 충분조건 계산만으로 이득이 사라졌으므로 규모 확대나 반복 실행을 바로 정당화하지 않는다. 별도 사전 설계에서 품질 경계와 손익분기 계산을 먼저 고정하고, 이를 만족할 근거가 생길 때만 다음 제한 실험을 선택한다. 이번 결과로 자동 편입·대규모 실행·일반 품질 보장을 승인하지 않는다.
