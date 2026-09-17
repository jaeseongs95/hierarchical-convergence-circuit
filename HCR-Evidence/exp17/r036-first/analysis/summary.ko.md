# EXP-17 / R0.3.6 — 입력 재표현과 native Graph 형성

각 재표현 입력에서 native 엔진을 새로 실행했다. 동결된 memory만 EXP-15에서 재사용했다.
선택기는 실제 native readout 후에만 적용했고, 후속 전개량이나 종료를 제어하지 않았다.
같은 입력의 재표현·두 prior 조건·여러 world 평가는 독립 문제 수로 합산하지 않는다.

native 실행 128 / 실제 native readout 136 / 선택 비교 408
최초 판단 이전 예산 종료 0
새 task kernel ticks 13144 + 272 = 13416

| 단계 / prior / 선택 | 상태 | 확정 | 보류 | 모든 선언 world 정답 | 하나 이상 오답 |
|---|---:|---:|---:|---:|---:|
| first_readout/legacy/native_rebuild | 64 | 32 | 32 | 24 | 8 |
| first_readout/legacy/native_saved | 64 | 32 | 32 | 24 | 8 |
| first_readout/legacy/support_first | 64 | 32 | 32 | 24 | 8 |
| first_readout/route_only/native_rebuild | 64 | 48 | 16 | 40 | 8 |
| first_readout/route_only/native_saved | 64 | 48 | 16 | 40 | 8 |
| first_readout/route_only/support_first | 64 | 48 | 16 | 40 | 8 |
| last_available_readout/legacy/native_rebuild | 64 | 32 | 32 | 24 | 8 |
| last_available_readout/legacy/native_saved | 64 | 32 | 32 | 24 | 8 |
| last_available_readout/legacy/support_first | 64 | 40 | 24 | 32 | 8 |
| last_available_readout/route_only/native_rebuild | 64 | 48 | 16 | 40 | 8 |
| last_available_readout/route_only/native_saved | 64 | 48 | 16 | 40 | 8 |
| last_available_readout/route_only/support_first | 64 | 48 | 16 | 40 | 8 |

첫/마지막 readout 표는 같은 실행을 서로 다른 시점에서 본 것이다. 두 표의 비용·표본을 다시 합산하지 않는다.
`last_available_readout`은 가장 나중에 얻은 판단이며, 예산 종료 시점의 미완성 상태와 구별한다.

## 입력 재표현별 paired 비교

| 입력 / prior / 단계 | readout 변형 | 경로 집합 불변 | raw 값 불변 | native 출력 불변 | support 출력 불변 | 선택 회복 |
|---|---:|---|---|---|---|---:|
| critical_missing/legacy/first_readout | 8/8 | True | True | True | True | 0 |
| critical_missing/route_only/first_readout | 8/8 | True | True | True | True | 0 |
| critical_zero/legacy/first_readout | 8/8 | True | True | True | True | 0 |
| critical_zero/route_only/first_readout | 8/8 | True | True | True | True | 0 |
| irrelevant_missing/legacy/first_readout | 8/8 | True | True | True | True | 0 |
| irrelevant_missing/route_only/first_readout | 8/8 | True | True | True | True | 0 |
| known_cut_missing/legacy/first_readout | 8/8 | True | True | True | True | 0 |
| known_cut_missing/route_only/first_readout | 8/8 | True | True | True | True | 0 |
| misleading_direction/legacy/first_readout | 8/8 | True | True | True | True | 0 |
| misleading_direction/route_only/first_readout | 8/8 | True | True | True | True | 0 |
| strong_positive/legacy/first_readout | 8/8 | True | True | True | True | 0 |
| strong_positive/route_only/first_readout | 8/8 | True | True | True | True | 0 |
| two_branch_cut/legacy/first_readout | 8/8 | True | True | True | True | 0 |
| two_branch_cut/route_only/first_readout | 8/8 | True | True | True | True | 0 |
| weak_negative/legacy/first_readout | 8/8 | True | True | True | True | 0 |
| weak_negative/route_only/first_readout | 8/8 | True | True | True | True | 0 |
| critical_missing/legacy/last_available_readout | 8/8 | True | True | True | True | 0 |
| critical_missing/route_only/last_available_readout | 8/8 | True | True | True | True | 0 |
| critical_zero/legacy/last_available_readout | 8/8 | True | True | True | True | 0 |
| critical_zero/route_only/last_available_readout | 8/8 | True | True | True | True | 0 |
| irrelevant_missing/legacy/last_available_readout | 8/8 | True | True | True | True | 8 |
| irrelevant_missing/route_only/last_available_readout | 8/8 | True | True | True | True | 0 |
| known_cut_missing/legacy/last_available_readout | 8/8 | True | True | True | True | 0 |
| known_cut_missing/route_only/last_available_readout | 8/8 | True | True | True | True | 0 |
| misleading_direction/legacy/last_available_readout | 8/8 | True | True | True | True | 0 |
| misleading_direction/route_only/last_available_readout | 8/8 | True | True | True | True | 0 |
| strong_positive/legacy/last_available_readout | 8/8 | True | True | True | True | 0 |
| strong_positive/route_only/last_available_readout | 8/8 | True | True | True | True | 0 |
| two_branch_cut/legacy/last_available_readout | 8/8 | True | True | True | True | 0 |
| two_branch_cut/route_only/last_available_readout | 8/8 | True | True | True | True | 0 |
| weak_negative/legacy/last_available_readout | 8/8 | True | True | True | True | 0 |
| weak_negative/route_only/last_available_readout | 8/8 | True | True | True | True | 0 |

## 해석할 때 유지할 구분

후보 pool에서 제안한 경로, workspace의 완성 경로, activation 적격 경로, 최종 proof는 별도 필드다.
gap label은 관찰 위치의 분류이며 학습 편향 등 원인을 확정한 진단이 아니다.
입력의 전체 판별 가능성과 숨은 world 정답은 independent evaluator만 계산한다.
동일 상태 native 재구성 불일치는 evaluator disagreement로 중단한다. 재표현 결과 불변성은 성공 조건으로 강제하지 않는다.
경로·edge 검사, proof 생성, native kernel ticks는 다른 비용 단위다. 미계측 scan은 null이며 0이 아니다.
추가 전개는 기존 expand_only 정책이다. native 지지 출력이 나오면 종료하므로 모든 trial의 Graph 완성을 보장하지 않는다.
새로운 topology 또는 자율적인 expand/observe/review/select 선택 능력은 이 실험의 검증 범위가 아니다.
