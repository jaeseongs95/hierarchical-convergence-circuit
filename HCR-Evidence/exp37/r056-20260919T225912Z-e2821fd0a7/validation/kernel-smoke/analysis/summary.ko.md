# EXP-37 / R056 국소 drive 2×2 대조

실행 목적: implementation_validation

| condition | input pair | mask | goal | e:0 | e:1 | convergence | ticks | transmissions |
|---|---|---|---:|---:|---:|---|---:|---:|
| startstrong | [1.0, 0.02] | full | 0.02611721134724789 | 0.9998907056302733 | 0.3749077314029905 | stable_decision | 60 | 480 |
| startstrong | [1.0, 0.02] | drop_P_prefix | 0.02867619581616716 | 0.9998920310525439 | 0.37979881251087627 | stable_decision | 62 | 434 |
| startlean | [0.755, 0.265] | full | 0.9875263810307797 | 0.9992397131862918 | 0.9617198104999893 | stable_decision | 34 | 272 |
| startlean | [0.755, 0.265] | drop_P_prefix | 0.987486189933344 | 0.9992334768921429 | 0.9616983365111096 | stable_decision | 34 | 238 |
| goallean | [0.265, 0.755] | full | 0.9877314810218224 | 0.9617442231545643 | 0.9992392635708583 | stable_decision | 33 | 264 |
| goallean | [0.265, 0.755] | drop_P_prefix | 0.9876907543653767 | 0.9613185007458742 | 0.9992388215484844 | stable_decision | 33 | 231 |
| goalstrong | [0.02, 1.0] | full | 0.013283387008994015 | 0.3859230510431379 | 0.9995789769707959 | stable_decision | 116 | 928 |
| goalstrong | [0.02, 1.0] | drop_P_prefix | 0.9868078092823211 | 0.7063685283291412 | 0.9998914649539711 | stable_decision | 75 | 525 |

| condition | delta goal | delta e:0 | delta e:1 | full | dropout | necessity |
|---|---:|---:|---:|---|---|---|
| startstrong | 0.0025589844689192683 | 1.3254222706038377e-06 | 0.004891081107885775 | low | low | False |
| startlean | -4.019109743569338e-05 | -6.2362941488647294e-06 | -2.147398887974994e-05 | high | high | None |
| goalstrong | 0.9735244222733271 | 0.3204454772860033 | 0.00031248798317518034 | low | high | True |
| goallean | -4.072665644572204e-05 | -0.00042572240869009903 | -4.4202237392543253e-07 | high | high | None |

R055 전체 궤적 bridge 8개가 모두 통과했다.
약한 drive 증가와 강한 drive 감소는 각각 다른 drive를 고정한 기술 대조다.
방향별 결과를 합치지 않는다. 총량이 함께 변하므로 별도의 총량 원인을 분리하지 않는다.
비안정 종료도 연속값을 보고하지만 endpoint는 inconclusive다.
고정 numerical kernel 결과이며 native outcome, sufficiency, basin, 일반성 증거가 아니다.
결정론적 분기들은 독립 표본이 아니다.
