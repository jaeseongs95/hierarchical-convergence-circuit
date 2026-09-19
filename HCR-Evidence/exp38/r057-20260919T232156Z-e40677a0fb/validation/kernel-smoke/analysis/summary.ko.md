# EXP-38 / R057 초기 상태 대조

실행 목적: implementation_validation

| orientation | initial | mask | goal | e:0 | e:1 | convergence | ticks | transmissions |
|---|---:|---|---:|---:|---:|---|---:|---:|
| start | 0.5 | full | 0.02611721134724789 | 0.9998907056302733 | 0.3749077314029905 | stable_decision | 60 | 480 |
| start | 0.5 | drop_P_prefix | 0.02867619581616716 | 0.9998920310525439 | 0.37979881251087627 | stable_decision | 62 | 434 |
| goal | 0.5 | full | 0.013283387008994015 | 0.3859230510431379 | 0.9995789769707959 | stable_decision | 116 | 928 |
| goal | 0.5 | drop_P_prefix | 0.9868078092823211 | 0.7063685283291412 | 0.9998914649539711 | stable_decision | 75 | 525 |

| condition | drop-minus-full goal | full | dropout | necessity |
|---|---:|---|---|---|
| start_i05 | 0.0025589844689192683 | low | low | False |
| goal_i05 | 0.9735244222733271 | low | high | True |

R056 전체 궤적 bridge 4개가 통과했다.
초기 상태 .1/.9와 .5의 비방향 기술 대조다. 비안정 종료의 범주 차이는 null이다.
같은 범주·작은 차이는 같은 수학적 고정점이나 전역 수렴의 증명이 아니다.
범주가 달라도 basin 경계·attractor·hysteresis·native outcome의 증거로 확장하지 않는다.
결정론적 분기는 독립 표본이 아니다.
