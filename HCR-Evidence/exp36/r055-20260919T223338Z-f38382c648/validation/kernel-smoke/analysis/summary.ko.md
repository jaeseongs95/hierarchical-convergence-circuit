# EXP-36 / R055 fixed-total drive allocation

실행 목적: implementation_validation

| condition | input pair | mask | goal | e:0 | e:1 | convergence | ticks | transmissions |
|---|---|---|---:|---:|---:|---|---:|---:|
| startstrong | [1.0, 0.02] | full | 0.02611721134724789 | 0.9998907056302733 | 0.3749077314029905 | stable_decision | 60 | 480 |
| startstrong | [1.0, 0.02] | drop_P_prefix | 0.02867619581616716 | 0.9998920310525439 | 0.37979881251087627 | stable_decision | 62 | 434 |
| goalstrong | [0.02, 1.0] | full | 0.013283387008994015 | 0.3859230510431379 | 0.9995789769707959 | stable_decision | 116 | 928 |
| goalstrong | [0.02, 1.0] | drop_P_prefix | 0.9868078092823211 | 0.7063685283291412 | 0.9998914649539711 | stable_decision | 75 | 525 |

| condition | delta goal | delta e:0 | delta e:1 | full | dropout | necessity |
|---|---:|---:|---:|---|---|---|
| startstrong | 0.0025589844689192683 | 1.3254222706038377e-06 | 0.004891081107885775 | low | low | False |
| goalstrong | 0.9735244222733271 | 0.3204454772860033 | 0.00031248798317518034 | low | high | True |

R054 양 끝 조건 전체 궤적 bridge 4개가 모두 통과했다.
비안정 종료도 연속값과 delta를 보고하지만 endpoint 판정은 inconclusive다.
mirrored contrast는 비방향 기술량이며 대칭성 검정이나 0 기대 주장이 아니다.
이 결과는 고정 맥락의 수치 endpoint이며 native outcome, sufficiency, basin, 일반성 증거가 아니다.
결정론적 분기들은 독립 표본이 아니다.
