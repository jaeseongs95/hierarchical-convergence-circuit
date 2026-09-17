# EXP-18 / R0.3.7 — 온라인 proof 채택

선택 결과가 실제 후속 전개·종료를 제어한다. native kernel/원 finish 판단은 변경하지 않았다.
support_first의 별도 proof/adoption을 원래 native 출력과 구분해 보존한다.

기본 입력 8 / fresh native 실행 32 / readout 34
readout 전 예산/엔진 종료 0
native kernel ticks: 3286 + 68 = 3354

| 시점 / prior / policy | trial | readout 없음 | 확정 | 보류 | 모든 world 정답 | 하나 이상 오답 |
|---|---:|---:|---:|---:|---:|---:|
| first_readout/legacy/native_saved | 8 | 0 | 4 | 4 | 3 | 1 |
| first_readout/legacy/support_first | 8 | 0 | 4 | 4 | 3 | 1 |
| first_readout/route_only/native_saved | 8 | 0 | 6 | 2 | 5 | 1 |
| first_readout/route_only/support_first | 8 | 0 | 6 | 2 | 5 | 1 |
| last_available_readout/legacy/native_saved | 8 | 0 | 4 | 4 | 3 | 1 |
| last_available_readout/legacy/support_first | 8 | 0 | 5 | 3 | 4 | 1 |
| last_available_readout/route_only/native_saved | 8 | 0 | 6 | 2 | 5 | 1 |
| last_available_readout/route_only/support_first | 8 | 0 | 6 | 2 | 5 | 1 |
| terminal_adoption/legacy/native_saved | 8 | 0 | 4 | 4 | 3 | 1 |
| terminal_adoption/legacy/support_first | 8 | 0 | 5 | 3 | 4 | 1 |
| terminal_adoption/route_only/native_saved | 8 | 0 | 6 | 2 | 5 | 1 |
| terminal_adoption/route_only/support_first | 8 | 0 | 6 | 2 | 5 | 1 |

first/last readout과 terminal adoption은 같은 실행의 서로 다른 관찰이며 합산하지 않는다.
마지막 readout 뒤 pending 계산이 미완성인 경우도 terminal_pending_ready에 별도로 보존한다.

## Policy별 paired 비교

| 입력 / prior | 첫 view 동일 | 공통 readout prefix 동일 | native 채택 | support 채택 | ticks native/support | 정답 회복 |
|---|---|---|---|---|---:|---|
| critical_missing/legacy | True | True | False | False | 66/66 | False |
| critical_missing/route_only | True | True | False | False | 93/93 | False |
| critical_zero/legacy | True | True | False | False | 66/66 | False |
| critical_zero/route_only | True | True | False | False | 93/93 | False |
| irrelevant_missing/legacy | True | True | False | True | 102/102 | True |
| irrelevant_missing/route_only | True | True | True | True | 164/164 | False |
| known_cut_missing/legacy | True | True | True | True | 169/169 | False |
| known_cut_missing/route_only | True | True | True | True | 166/166 | False |
| misleading_direction/legacy | True | True | True | True | 69/69 | False |
| misleading_direction/route_only | True | True | True | True | 70/70 | False |
| strong_positive/legacy | True | True | True | True | 69/69 | False |
| strong_positive/route_only | True | True | True | True | 70/70 | False |
| two_branch_cut/legacy | True | True | True | True | 165/165 | False |
| two_branch_cut/route_only | True | True | True | True | 165/165 | False |
| weak_negative/legacy | True | True | False | False | 75/75 | False |
| weak_negative/route_only | True | True | True | True | 75/75 | False |

## 비용 및 주장 범위

native finish branch에서 생성한 proof node: 158
온라인 selector 계측: {'ranked_paths': 12, 'path_checks': 11, 'edge_checks': 29, 'proof_nodes_created': 32, 'proof_nodes_reused': 104, 'gate_assumptions_checked': 61}
Native ticks·경로/edge 검사·proof 생성/재사용은 서로 다른 비용 단위다. 단일 총비용으로 더하지 않는다.
원 native capture 내부의 미계측 scan은 null이며 0이 아니다. evaluator 재생 비용은 task 비용에서 제외한다.
8개 기본 입력의 prior/policy/world/readout 비교를 독립 문제 수로 세지 않는다. 통계적 일반화나 새 topology 검증은 하지 않았다.
부정 raw 값은 기존 proof를 통과시킨다. 이 실험은 raw 값 반전·관측 요청·prior 재검토·학습된 자율 repair를 포함하지 않는다.
보류가 정답 확정으로 회복됐는지, 지원된 오답인지, 계산/선택 예산 소진인지 분리해서 해석한다.
검증 통과는 원자료·계보·제어·proof·비용의 정합성이다. 정답/개선 자체를 통과 조건으로 삼지 않는다.
