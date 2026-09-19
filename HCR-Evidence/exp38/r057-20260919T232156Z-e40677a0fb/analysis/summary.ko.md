# EXP-38 / R057 초기 상태 대조

실행 목적: research

| orientation | initial | mask | goal | e:0 | e:1 | convergence | ticks | transmissions |
|---|---:|---|---:|---:|---:|---|---:|---:|
| start | 0.1 | full | 0.02611724803206026 | 0.9998907056314146 | 0.3749078147372993 | stable_decision | 70 | 560 |
| start | 0.1 | drop_P_prefix | 0.02867625199843423 | 0.9998920310525439 | 0.37979892820775285 | stable_decision | 73 | 511 |
| start | 0.5 | full | 0.02611721134724789 | 0.9998907056302733 | 0.3749077314029905 | stable_decision | 60 | 480 |
| start | 0.5 | drop_P_prefix | 0.02867619581616716 | 0.9998920310525439 | 0.37979881251087627 | stable_decision | 62 | 434 |
| start | 0.9 | full | 0.9820171747580223 | 0.9998928466325187 | 0.7291590595749805 | stable_decision | 37 | 296 |
| start | 0.9 | drop_P_prefix | 0.9816043862990428 | 0.9998920310387363 | 0.7282017839653608 | stable_decision | 38 | 266 |
| goal | 0.1 | full | 0.013283164003762848 | 0.3859176640751283 | 0.9995789757377209 | stable_decision | 75 | 600 |
| goal | 0.1 | drop_P_prefix | 0.9868078099234494 | 0.7063685410172043 | 0.9998914649548893 | stable_decision | 99 | 693 |
| goal | 0.5 | full | 0.013283387008994015 | 0.3859230510431379 | 0.9995789769707959 | stable_decision | 116 | 928 |
| goal | 0.5 | drop_P_prefix | 0.9868078092823211 | 0.7063685283291412 | 0.9998914649539711 | stable_decision | 75 | 525 |
| goal | 0.9 | full | 0.9874829754861603 | 0.7304305513222462 | 0.9998924596286723 | stable_decision | 38 | 304 |
| goal | 0.9 | drop_P_prefix | 0.986807984016951 | 0.7063719866261875 | 0.9998914652042425 | stable_decision | 60 | 420 |

| condition | drop-minus-full goal | full | dropout | necessity |
|---|---:|---|---|---|
| start_i01 | 0.002559003966373971 | low | low | False |
| start_i05 | 0.0025589844689192683 | low | low | False |
| start_i09 | -0.0004127884589795183 | high | high | None |
| goal_i01 | 0.9735246459196866 | low | high | True |
| goal_i05 | 0.9735244222733271 | low | high | True |
| goal_i09 | -0.0006749914692092407 | high | high | None |

| orientation | mask | initial | goal minus .5 baseline | baseline regime | changed regime | different stable regimes |
|---|---|---:|---:|---|---|---|
| start | full | 0.1 | 3.668481236840382e-08 | low | low | False |
| start | full | 0.9 | 0.9558999634107744 | low | high | True |
| start | drop_P_prefix | 0.1 | 5.6182267071241965e-08 | low | low | False |
| start | drop_P_prefix | 0.9 | 0.9529281904828756 | low | high | True |
| goal | full | 0.1 | -2.230052311667785e-07 | low | low | False |
| goal | full | 0.9 | 0.9741995884771663 | low | high | True |
| goal | drop_P_prefix | 0.1 | 6.411282615914615e-10 | high | high | False |
| goal | drop_P_prefix | 0.9 | 1.74734629876383e-07 | high | high | False |

R056 전체 궤적 bridge 4개가 통과했다.
초기 상태 .1/.9와 .5의 비방향 기술 대조다. 비안정 종료의 범주 차이는 null이다.
같은 범주·작은 차이는 같은 수학적 고정점이나 전역 수렴의 증명이 아니다.
범주가 달라도 basin 경계·attractor·hysteresis·native outcome의 증거로 확장하지 않는다.
결정론적 분기는 독립 표본이 아니다.
