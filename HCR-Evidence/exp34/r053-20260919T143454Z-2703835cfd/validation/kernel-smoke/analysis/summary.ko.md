# EXP-34 / R053 feedback factorial

실행 목적: implementation_validation

| condition | mask | goal | e:0 | e:1 | ticks | transmissions |
|---|---|---:|---:|---:|---:|---:|
| weakweak | off | 0.017257067519771244 | 0.5513780774684683 | 0.5513780774684683 | 37 | 148 |
| weakweak | edge_local_only | 0.02277586994105987 | 0.7063699554019931 | 0.3678061366955755 | 84 | 504 |
| weakweak | path_internal_only | 0.012074625190860104 | 0.5513780610700825 | 0.5513780610700825 | 34 | 204 |
| weakweak | full | 0.01167128084167289 | 0.3839648752718711 | 0.3342380505078899 | 88 | 704 |

R052 numerical bridge 2개가 모두 통과했다.
이 표는 counterfactual numerical kernel 결과이며 native proof, support, adoption은 측정하지 않았다.
결정론적 분기들은 독립 표본이 아니다.
