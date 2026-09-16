# HCR R0.2 개발 실행 결과

실제 실행이 만든 결과다. 가설 입증 여부와 구분하며, 이 문서의 수치는 소스 배포 때 미리 작성하지 않는다.

## 조건별 판단
| 조건 | 실행 | 정답 | 오답 | 보류 | 근거 포함 정답 | 안정 오답 | 회로 사용 |
|---|---:|---:|---:|---:|---:|---:|---:|
| familiarity/cold | 3 | 3 | 0 | 0 | 3 | 0 | 0 |
| familiarity/warm | 3 | 3 | 0 | 0 | 3 | 0 | 3 |
| misconvergence/full | 2 | 1 | 1 | 0 | 1 | 1 | 1 |
| misconvergence/no_reexpansion | 1 | 0 | 1 | 0 | 0 | 1 | 1 |
| novelty/full | 2 | 2 | 0 | 0 | 2 | 0 | 2 |
| novelty/graph_only | 2 | 2 | 0 | 0 | 2 | 0 | 0 |
| retention/reload | 1 | 0 | 1 | 0 | 0 | 1 | 1 |
| tradeoff/training_3 | 2 | 1 | 1 | 0 | 1 | 1 | 1 |
| tradeoff/training_9 | 2 | 1 | 1 | 0 | 1 | 1 | 1 |
| tradeoff_training/training_3 | 3 | 3 | 0 | 0 | 3 | 0 | 0 |
| tradeoff_training/training_9 | 9 | 9 | 0 | 0 | 9 | 0 | 6 |
| training/full | 6 | 6 | 0 | 0 | 6 | 0 | 3 |

## Familiarity: warm − cold
음수는 해당 계측량 감소다. 서로 단위가 다른 비용을 더하지 않는다.

| 사례 | dependency node | 확장 | binding | 신호 | tick | primitive D (cold / warm) |
|---|---:|---:|---:|---:|---:|---|
| same_structure | -1 | -1 | 18 | 872 | 33 | 3 / 3 |
| counterfactual | -1 | -1 | 27 | 1210 | 68 | 2 / 2 |
| renamed_reordered | -1 | -1 | 18 | 872 | 33 | 3 / 3 |

## 해석 범위
- 개발용 deterministic symbolic toy-world 실험이다. 독립 일반화 표본이나 생물학 검증이 아니다.
- 부분 컴파일 범위는 연속 directed path motifs다. arbitrary graph mining이나 A/M 자동화가 아니다.
- 동적 dependency node 감소와 총 연산/시간 감소는 별개다. matching/pool/proof 비용도 포함한다.
- signal_events=signal_transmissions, convergence_ticks=kernel_ticks 등 별칭은 중복 합산하지 않는다.
- 오수렴 또는 trade-off의 발생은 측정 결과다. 실험 성공 조건을 맞추려고 최초 판단을 강제하지 않는다.
- 오류 수정은 외부 feedback와 요청된 추가 측정을 쓴다. feedback bit만으로 정답을 뒤집지 않는다.
- primitive proof D는 macro 호출 횟수로 대체하지 않는다. 실제 계측 wall time은 단일 실행의 관측값이다.
