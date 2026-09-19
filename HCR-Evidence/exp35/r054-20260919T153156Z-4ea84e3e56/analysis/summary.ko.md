# EXP-35 / R054 single feedback links

실행 목적: research

| condition | mask | goal | convergence | ticks | transmissions |
|---|---|---:|---|---:|---:|
| startstrong | full | 0.02611721134724789 | stable_decision | 60 | 480 |
| startstrong | off | 0.7341643876681345 | stable_decision | 47 | 188 |
| startstrong | drop_E_start | 0.026112690432840695 | stable_decision | 60 | 420 |
| startstrong | drop_E_goal | 0.924067763373901 | stable_decision | 76 | 532 |
| startstrong | drop_P_prefix | 0.02867619581616716 | stable_decision | 62 | 434 |
| startstrong | drop_P_goal | 0.9670038466545456 | stable_decision | 116 | 812 |
| goalstrong | full | 0.013283387008994015 | stable_decision | 116 | 928 |
| goalstrong | off | 0.9342952583666644 | stable_decision | 44 | 176 |
| goalstrong | drop_E_start | 0.9849930534707447 | stable_decision | 61 | 427 |
| goalstrong | drop_E_goal | 0.013286369212838212 | stable_decision | 116 | 812 |
| goalstrong | drop_P_prefix | 0.9868078092823211 | stable_decision | 75 | 525 |
| goalstrong | drop_P_goal | 0.9865789235698565 | stable_decision | 61 | 427 |

| condition | removed link | delta goal | weak edge | delta weak | full | dropout | necessity |
|---|---|---:|---|---:|---|---|---|
| startstrong | E_start | -4.520914407196708e-06 | e:1 | -9.026596586247937e-06 | low | low | False |
| startstrong | E_goal | 0.8979505520266531 | e:1 | 0.1764703522810127 | low | high | True |
| startstrong | P_prefix | 0.0025589844689192683 | e:1 | 0.004891081107885775 | low | low | False |
| startstrong | P_goal | 0.9408866353072978 | e:1 | 0.32774204697881804 | low | high | True |
| goalstrong | E_start | 0.9717096664617507 | e:0 | 0.16545503264066325 | low | high | True |
| goalstrong | E_goal | 2.982203844197062e-06 | e:0 | 3.5532584325981276e-06 | low | low | False |
| goalstrong | P_prefix | 0.9735244222733271 | e:0 | 0.3204454772860033 | low | high | True |
| goalstrong | P_goal | 0.9732955365608625 | e:0 | 0.3442666293205195 | low | high | True |

R053 full/off numerical bridge 4개가 모두 통과했다.
비안정 종료도 연속값과 delta를 보고하지만 endpoint 판정은 inconclusive다.
이 결과는 고정 맥락의 수치 endpoint 술어이며 sufficiency, native proof/adoption, basin 증거가 아니다.
결정론적 분기들은 독립 표본이 아니다.
