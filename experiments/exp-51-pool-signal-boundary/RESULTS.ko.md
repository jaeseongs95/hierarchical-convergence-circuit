# R070 결과: 약화 신호는 pool에 전달됐지만 선택 경계를 넘지 않았다

## 결론

R069의 stale 관측에서 M0/M1의 strength 차이는 pool prior, drive와 activation 궤적에 전달됐다. 두 후보는 기존 activation threshold 0.55를 모두 넘어 같은 회로가 선택됐다. route_only의 decision program·drive·수치 궤적은 같았다. 따라서 최종 판단과 정수 비용이 같다는 사실을 전체 계산이 같다는 뜻으로 해석할 수 없다.

이번 결과는 R069 원자료의 재분석이다. 새 native 연구 실행과 새 독립 표본은 모두 0이다.

## 관찰

[재계산 집계](../../HCR-Evidence/exp51/r070-20260930T124334Z-a1eb37c575/summary.json)와 [별도 검산](../../HCR-Evidence/exp51/r070-20260930T124334Z-a1eb37c575/verification.json)은 동일 관측의 새 세션 네 packet을 사용했다. pool network를 별도 evaluator 식으로 구성하고 초기값 0.5부터 모든 tick을 재생했다. 생산 runtime과 kernel 실행 함수는 호출하지 않았다.

| 관측 | checkpoint | strength | pool prior | pool activation | eligible | 최초 선택 | pool / decision ticks |
| --- | --- | --- | --- | --- | --- | --- | --- |
| stale | M0 | 0.11 | 0.033 | 0.9942212668099926 | True | circuit | 35 / 33 |
| stale | M1 | 0.022 | 0.0066 | 0.9938918635122408 | True | circuit | 35 / 33 |
| fresh | M0 | 0.11 | 0 | 0.006129602484598997 | False | primitive | 29 / 28 |
| fresh | M1 | 0.022 | 0 | 0.006129602484598997 | False | primitive | 29 / 28 |

stale 쌍에서 prior 차이는 -0.0264, 최종 pool activation 차이는 약 -0.0003294였다. 같은 tick과 group을 대응시킨 전체 pool 궤적의 최대 차이는 0.048030327381431204였다. pool program은 같았고 drive는 달랐다. eligibility, 선택 edge, 최종 판단·채택과 정수 비용 카운터는 같았다. decision program, drive와 전체 숫자 궤적도 같았다.

fresh 쌍의 pool prior는 모두 0이었다. 고정된 식에서 관측의 절댓값이 모두 1이므로 prior의 불확실성 항이 0이 된다. 두 pool 궤적은 같았다. activation은 threshold보다 낮았고 mismatch 1도 허용 상한 0.8을 넘었다. 두 조건이 함께 회로 후보를 제외했으며 primitive 경로가 선택됐다.

별도 프로세스에서 네 packet을 감사하고 원자료와 집계를 대조했다. drive, prior, tick, activation, eligibility, 선택, decision drive와 memory strength의 여덟 변조를 거부했다. 원본 bundle 전체의 파일 목록·바이트 hash, 복사 입력과 봉인된 source를 확인했다. 전체 회귀와 최종 전달 검증은 [수용 근거](../../HCR-Evidence/r070-validation/delivery-verification.json)에 기록한다.

## 해석

이번 stale 조건에서 “약화 신호가 pool에 전달되지 않았다”는 설명은 원자료와 맞지 않는다. pool 수치는 달라졌으나 eligibility 경계를 넘지 않아 선택이 유지됐다는 설명이 직접 관찰과 맞는다. route_only는 회로 prior를 decision drive에 더하지 않으며, 선택 경로가 같았던 이번 쌍의 decision 계산도 같았다.

이는 학습 약화가 계산에 아무 영향도 없었다는 해석을 수정한다. 다만 행동 교정과 비용 변화가 없었다는 R069의 관찰은 유지한다. 실제 memory checkpoint에는 strength 외에도 version과 feedback 이력 등이 달라지므로 순수 strength 개입의 행동 효과로 일반화하지 않는다.

## 대안 설명

강한 stale score, 단일 회로 후보와 낮은 activation threshold가 선택 유지와 양립한다. 이번 자료는 여러 회로 사이의 경쟁이나 다른 관측·threshold에서의 행동 민감도를 측정하지 않는다. fresh 조건은 낮은 activation과 큰 mismatch가 함께 나타나므로 어느 조건만으로 선택이 달라졌다고 분리해 주장하지 않는다.

## 판별 실험

두 stale activation의 수학적 분리 구간은 `(0.9938918635122408, 0.9942212668099926]`이고 중간값은 0.9940565651611166이다. 이 구간의 threshold로 기존 pool readout을 재분류하면 M0는 허용되고 M1은 제외된다. 이는 기록된 수치에서 도출한 예측이며 실제 native 선택·readout 결과가 아니다.

[후속 작업](NEXT.ko.md)에서는 조건 변경에 따른 memory/config 계약을 먼저 확인하고, 선택 경계를 구별할 최소 paired 실행을 별도로 동결한다. 이번 결과를 본 뒤 정한 경계를 사전 예측의 독립 성공으로 세지 않는다.

## 현재 주장 가능한 범위

- observed: R069 stale 쌍에서 회로 약화 신호가 pool prior·drive·activation과 중간 궤적에 전달됐다.
- observed: 기존 threshold에서 eligibility와 최초 선택은 유지됐으며 route_only decision 궤적과 최종 판단도 같았다.
- derived-prediction: 기록된 두 activation 사이 threshold는 기존 pool readout을 다르게 분류한다.
- not measurable: 회로 간 선택 경쟁. 현재 후보는 하나다.
- unsupported: 실제 threshold 변경 후 native 행동 효과, 자율 sensing, 일반적 학습 우위, 에너지 효율과 HCC 고유 우위.

검산은 생산 코드와 분리된 로직·프로세스로 수행했다. 독립 연구자가 새 실험을 재현한 것은 아니다. 에너지와 peak memory는 측정하지 않았다.
