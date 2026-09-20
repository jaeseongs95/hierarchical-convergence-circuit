# R066 결과: 기록한 사실은 조회할 때 판단을 바꾸며, 낡은 조회는 오류를 만들 수 있다

## 결론

이 toy 과제에서는 교정 사실을 **저장만 하면** fresh 판단이 달라지지 않았다. 같은 사실을 조회해 입력에 반영하면 고정 세계의 오답 True가 정답 False로 바뀌었다. 반대로 세계 변화를 알리지 않고 예전 사실을 조회하면 원래 맞던 True가 틀린 False로 바뀌었다.

교정은 회로 ON/OFF 양쪽에서 발생했다. 이는 명시적 사실 조회·입력 개입의 효과이며 native HCC의 사실 학습이나 독자적 우위의 증거가 아니다.

## 관찰

실행: [r066-20260920T060557Z-c4b48b19a6](../../HCR-Evidence/exp47/r066-20260920T060557Z-c4b48b19a6/summary.json). 부모는 R064의 요청 교정 관측과 memory다. 2개 정보 channel × 3개 처리군 × 2개 gate × 5개 case = 새 frozen 평가 60개이며, 새 학습은 0회다. 모두 readout을 채택했으며 독립 표본 60개라는 뜻은 아니다.

아래는 edge_correction channel의 결과이며 ON/OFF에서 채택값이 같았다.

| 조건 | current / record_only | lookup | 참조 정답 |
|---|---|---|---|
| 고정 세계 재노출 | True, 오답 | False, 정답 | False |
| 다른 context | True, 정답 | 미조회 상태로 True, 정답 | True |
| 새 epoch | True, 정답 | 미조회 상태로 True, 정답 | True |
| 미통지 세계 변화 | True, 정답 | False, 오답 | True |
| 정확한 원래 관측 | False, 정답 | False, 정답 | False |

record_only와 current의 native 측정값·비용은 20개 대응 조건에서 모두 같았다. binary_feedback channel에는 edge 사실을 만들지 않았으므로 세 군의 native 결과가 같았다. 정확한 원래 관측을 주면 binary/current에서도 False를 올바르게 채택했다.

교정 사실표는 출처 metadata를 포함해 670 bytes, Boolean edge 값 2개였다. 빈 표의 JSON은 2 bytes다. lookup은 입력마다 query 2개와 record 비교 4회를 수행했다. 다른 context/epoch의 일치 사실은 0개였고, same/silent_change/truthful에서는 2개였다. truthful은 조회해도 원래 입력과 같았고, 실제 score가 달라진 조건은 same/silent_change × ON/OFF의 4개였다. 새 외부 관측 호출은 없었다. 같은 R064 관측 재사용을 60번 새로 측정한 정보로 세지 않는다.

native memory의 canonical JSON 크기는 binary channel 5,569 bytes(version 4), 교정 channel 5,828 bytes(version 5)였다. 이는 프로세스 메모리 사용량이 아니다. channel 사이에는 feedback 이력 차이가 있으므로 순수한 정보 bit 수의 효과로 비교하지 않는다. 정보 entropy·정보 이득과 실제 에너지는 측정하지 않았다.

교정 channel의 고정 세계 재노출 비용:

| 군 / gate | expansion | circuit reuse | kernel ticks | binding checks |
|---|---:|---:|---:|---:|
| current·record_only / OFF | 2 | 0 | 33 | 0 |
| current·record_only / ON | 1 | 1 | 68 | 4 |
| lookup / OFF | 2 | 0 | 28 | 0 |
| lookup / ON | 2 | 0 | 57 | 6 |

회로 ON은 잘못된 원래 관측에서 expansion을 줄였지만 tick은 증가했다. 교정 입력에서는 저장된 양성 회로의 실제 reuse가 0이었다. 표 조회 비용과 native tick을 합쳐 총 계산량이라고 부르지 않는다.

## 해석

R065의 정보 흐름 분석을 입력 개입으로 확장해, 과거 사실의 보존과 다음 판단에서의 사용을 분리했다. 기록의 존재만으로는 충분하지 않았고, 조회가 실제 입력에 연결될 때 이 조건의 판단이 달라졌다. 정확한 관측 통제군도 성공했으므로 회로 학습을 추가하지 않아도 해당 정보를 입력으로 제공하는 경로가 충분했다.

context/epoch 확인은 명시적으로 제공된 범위 밖 사실의 적용을 막았다. 그러나 같은 scope 안의 미통지 변화는 식별하지 못했다. 조회 성공(hit)은 key 일치를 뜻하며 현재 세계에서 사실이 참이라는 보증이 아니다.

## 대안 설명

효과의 직접적인 경로는 native 입력 score를 ±1로 바꾼 것이다. 기억 기반 추론, confidence 강화, 선택적 edge 정보의 기여를 이 실험만으로 각각 분리하지 못한다. e0도 +0.8에서 +1로 바뀌었으므로 e1 하나만의 효과라고 단정하지 않는다.

동일한 상황 metadata는 host가 제공했다. native 시스템이 context나 freshness를 스스로 알아낸 결과가 아니다. same과 silent_change는 노출 입력이 같고 참조 세계만 다른 두 조건이며 실제 시간 변화의 추적 실험이 아니다. 현재/기록군과 조회군의 차이는 과거 정보의 접근 허용 차이이며, native에 동일 정보가 들어간 상태에서 HCC 구조의 고유 이점을 검증한 비교가 아니다.

## 판별 실험

다음은 과거 사실과 현재 관측이 충돌할 때, 동일한 추가 관측 예산 아래 신뢰할 수 있는 새 관측이 두 세계를 구별하는지 확인하는 것이다. [NEXT.ko.md](NEXT.ko.md)에 관측 획득과 판단 경로의 분리 조건을 남긴다.

## 현재 주장 가능한 범위

- `observed`: 고정된 toy 조건에서 사실 기록만으로는 native 판단이 바뀌지 않았고, 명시적 조회·입력 개입은 교정과 미통지 변화 오류를 모두 만들었다.
- `partially-supported`: R065에서 제기한 “교정 유지에는 사용할 수 있는 사실 정보 경로가 필요하다”는 설명을 이 두-edge baseline이 지지한다. 모든 memory 구조의 일반적 필요조건을 증명한 것은 아니다.
- `unsupported`: native HCC의 사실 학습, 자동 freshness 판별, 일반화, 정보량을 맞춘 HCC의 독자적 우위 또는 총 효율 향상.

별도 로직·프로세스에서 60개 native 수식 replay와 입력 join을 검산하고, 합성 경계 검사 10개 및 변조 13개 거부를 확인했다. 이는 독립 연구자 감사가 아니다. 최종 회귀와 전달 무결성은 [delivery-verification.json](../../HCR-Evidence/r066-validation/delivery-verification.json)에 기록한다.
