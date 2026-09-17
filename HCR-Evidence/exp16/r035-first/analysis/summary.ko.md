# EXP-16 / R0.3.5 — 동일 상태의 proof 재구성·선택 비교

EXP-15 원 상태를 재사용한 선택 단계 개입 결과다. 새 native Graph 실행 결과가 아니다.
node/edge ID·slot·경로 순서 변형은 readout 이후에만 적용한다. 입력부터의 Graph 형성 효과와 구별한다.
같은 원 상태의 변형과 여러 world 평가는 독립 문제/독립 반복이 아니다.

원 native snapshot: 17 / 주 비교: 816 / 예산 대조: 68
EXP-16 새 native kernel ticks: 0. proof 생성·선택·검산은 별도 작업이다.

| 그룹 / 정책 | 조건 | 확정 | 보류 | 새 proof 노드 | 재사용 proof 노드 |
|---|---:|---:|---:|---:|---:|
| ablation_max_edge_checks/support_first | 17 | 5 | 12 | 0 | 25 |
| ablation_max_path_checks/support_first | 17 | 5 | 12 | 0 | 25 |
| ablation_max_proof_nodes/support_first | 17 | 5 | 12 | 0 | 25 |
| ablation_max_ranked_paths/support_first | 17 | 5 | 12 | 0 | 25 |
| main/native_rebuild | 272 | 160 | 112 | 1264 | 0 |
| main/native_saved | 272 | 160 | 112 | 0 | 1264 |
| main/support_first | 272 | 176 | 96 | 512 | 400 |

## 원 상태별 paired 결과

회복은 native 보존과 native 재구성이 모두 보류하고 support-first만 확정한 조건이다.
확정이 곧 외부 정답이라는 뜻은 아니다. world별 정확성은 records/rows에 분리했다.

| 상태 | 입력 | prior | 단계 | 선택만으로 회복한 재표현 조건 | 출력 불변성 saved/rebuild/support |
|---|---|---|---|---:|---|
| n0000 | critical_missing | legacy | first | 0/16 | True/True/True |
| n0001 | critical_missing | route_only | first | 0/16 | True/True/True |
| n0002 | critical_zero | legacy | first | 0/16 | True/True/True |
| n0003 | critical_zero | route_only | first | 0/16 | True/True/True |
| n0004 | irrelevant_missing | legacy | first | 0/16 | True/True/True |
| n0005 | irrelevant_missing | legacy | expanded_1 | 16/16 | True/True/True |
| n0006 | irrelevant_missing | route_only | first | 0/16 | True/True/True |
| n0007 | known_cut_missing | legacy | first | 0/16 | True/True/True |
| n0008 | known_cut_missing | route_only | first | 0/16 | True/True/True |
| n0009 | misleading_direction | legacy | first | 0/16 | True/True/True |
| n0010 | misleading_direction | route_only | first | 0/16 | True/True/True |
| n0011 | strong_positive | legacy | first | 0/16 | True/True/True |
| n0012 | strong_positive | route_only | first | 0/16 | True/True/True |
| n0013 | two_branch_cut | legacy | first | 0/16 | True/True/True |
| n0014 | two_branch_cut | route_only | first | 0/16 | True/True/True |
| n0015 | weak_negative | legacy | first | 0/16 | True/True/True |
| n0016 | weak_negative | route_only | first | 0/16 | True/True/True |

## 판정 방법

identity 조건에서 native 재구성이 보존 proof와 다르면 단순 선택 개선으로 해석하지 않고 evaluator disagreement로 중단한다.
순서 변형에서 활성도 동률의 tie-break가 달라지는 것은 실제 관찰로 남긴다. 불변성을 성공 조건으로 강제하지 않는다.
support-first의 False/None 입력은 새로운 음성 proof를 찾지 않고 기존 native proof를 유지하는 범위 밖 대조다.
native 재구성 내부 scan 카운터는 미계측(null)이다. 0 비용으로 해석하거나 서로 다른 단위를 합산하지 않는다.
이 결과 이후의 새 입력 native Graph 변형 실험과 자율 controller 실험은 별도 단계다.
