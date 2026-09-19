# EXP-36 / R055 fixed-total drive allocation

실행 목적: research

| condition | input pair | mask | goal | e:0 | e:1 | convergence | ticks | transmissions |
|---|---|---|---:|---:|---:|---|---:|---:|
| startstrong | [1.0, 0.02] | full | 0.02611721134724789 | 0.9998907056302733 | 0.3749077314029905 | stable_decision | 60 | 480 |
| startstrong | [1.0, 0.02] | drop_P_prefix | 0.02867619581616716 | 0.9998920310525439 | 0.37979881251087627 | stable_decision | 62 | 434 |
| startlean | [0.755, 0.265] | full | 0.9875263810307797 | 0.9992397131862918 | 0.9617198104999893 | stable_decision | 34 | 272 |
| startlean | [0.755, 0.265] | drop_P_prefix | 0.987486189933344 | 0.9992334768921429 | 0.9616983365111096 | stable_decision | 34 | 238 |
| balanced | [0.51, 0.51] | full | 0.9877174230190755 | 0.9946034994751314 | 0.9946007891774205 | stable_decision | 33 | 264 |
| balanced | [0.51, 0.51] | drop_P_prefix | 0.9876857829414023 | 0.9945574254479416 | 0.9945983552743867 | stable_decision | 33 | 231 |
| goallean | [0.265, 0.755] | full | 0.9877314810218224 | 0.9617442231545643 | 0.9992392635708583 | stable_decision | 33 | 264 |
| goallean | [0.265, 0.755] | drop_P_prefix | 0.9876907543653767 | 0.9613185007458742 | 0.9992388215484844 | stable_decision | 33 | 231 |
| goalstrong | [0.02, 1.0] | full | 0.013283387008994015 | 0.3859230510431379 | 0.9995789769707959 | stable_decision | 116 | 928 |
| goalstrong | [0.02, 1.0] | drop_P_prefix | 0.9868078092823211 | 0.7063685283291412 | 0.9998914649539711 | stable_decision | 75 | 525 |

| condition | delta goal | delta e:0 | delta e:1 | full | dropout | necessity |
|---|---:|---:|---:|---|---|---|
| startstrong | 0.0025589844689192683 | 1.3254222706038377e-06 | 0.004891081107885775 | low | low | False |
| startlean | -4.019109743569338e-05 | -6.2362941488647294e-06 | -2.147398887974994e-05 | high | high | None |
| balanced | -3.164007767320065e-05 | -4.6074027189813016e-05 | -2.4339030337827694e-06 | high | high | None |
| goallean | -4.072665644572204e-05 | -0.00042572240869009903 | -4.4202237392543253e-07 | high | high | None |
| goalstrong | 0.9735244222733271 | 0.3204454772860033 | 0.00031248798317518034 | low | high | True |

| left | right | right-minus-left delta goal | status |
|---|---|---:|---|
| startstrong | goalstrong | 0.9709654378044079 | nondirectional |
| startlean | goallean | -5.355590100286634e-07 | nondirectional |

R054 양 끝 조건 전체 궤적 bridge 4개가 모두 통과했다.
비안정 종료도 연속값과 delta를 보고하지만 endpoint 판정은 inconclusive다.
mirrored contrast는 비방향 기술량이며 대칭성 검정이나 0 기대 주장이 아니다.
이 결과는 고정 맥락의 수치 endpoint이며 native outcome, sufficiency, basin, 일반성 증거가 아니다.
결정론적 분기들은 독립 표본이 아니다.
