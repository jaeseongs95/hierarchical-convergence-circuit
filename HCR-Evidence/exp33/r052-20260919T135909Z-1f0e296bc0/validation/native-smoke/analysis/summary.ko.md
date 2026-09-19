# EXP-33 / R052

실행 목적: implementation_validation

독립 원자료 검산을 통과했다. 검산 통과는 배열 불변성 가설 지지를 뜻하지 않는다.

| 배열 순서 | top-down | 개입 | 채택 | 정답 채택 | 오답 채택 | 보류 | 추가 ticks |
|---|---|---|---:|---:|---:|---:|---:|
| path | False | hold | 0 | 0 | 0 | 1 | 0 |
| path | False | revision_only | 0 | 0 | 0 | 1 | 37 |
| path | False | start_edge | 1 | 1 | 0 | 0 | 47 |
| path | False | goal_edge | 1 | 1 | 0 | 0 | 44 |
| swapped | False | hold | 0 | 0 | 0 | 1 | 0 |
| swapped | False | revision_only | 0 | 0 | 0 | 1 | 37 |
| swapped | False | start_edge | 1 | 1 | 0 | 0 | 47 |
| swapped | False | goal_edge | 1 | 1 | 0 | 0 | 44 |

동일 기준선의 분기와 배열 순서 대조는 독립 확률 표본이 아니다.
role-aligned 비교는 원 packet을 수정하지 않고 구조 역할로만 투영한다.
수치·궤적·proof/support/readout 차이는 연구 결과이며 audit 실패로 바꾸지 않는다.
구현 검증 실행은 연구 결과로 합산하지 않는다.
