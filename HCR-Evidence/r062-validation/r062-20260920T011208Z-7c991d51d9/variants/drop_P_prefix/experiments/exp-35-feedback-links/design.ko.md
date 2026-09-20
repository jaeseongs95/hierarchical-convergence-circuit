# EXP-35 / R054 사전 동결 설계

## 질문

R053의 두 강화 입력에서 E-only/P-only는 goal을 높였지만 full은 낮췄다.
E 단독 억제 예측은 반박됐으며 집합 간 조건부 효과 반전이 확인됐다.
이번에는 full의 네 feedback 중 어느 하나를 제거했을 때 낮은 endpoint가 깨지는지 판별한다.
이는 수치 커널의 개별 링크 필요성 대조이며 native session·proof·support·adoption 연구가 아니다.

## 조건

startstrong=(1.0,0.02), goalstrong=(0.02,1.0)의 두 입력을 유지한다.
path order, R052에서 생성한 network, support links, group bias, default config,
초기 전 좌표 0.5와 기존 동기 갱신·종료 규칙·max_ticks=160을 고정한다.
각 branch는 fresh start이며 이전 branch의 최종 상태를 넘겨받지 않는다.

| 링크 ID | source→target | 구조 |
|---|---|---|
| E_start | p:0:0→e:0 | 첫 edge로 돌아가는 feedback |
| E_goal | p:0:1→e:1 | 둘째 edge로 돌아가는 feedback |
| P_prefix | p:0:1→p:0:0 | prefix 사이 feedback |
| P_goal | goal→p:0:1 | goal에서 prefix로 돌아가는 feedback |

mask는 full, off, drop_E_start, drop_E_goal, drop_P_prefix, drop_P_goal 순서다.
full은 그대로, off는 네 feedback 모두 제거, 각 drop은 해당 링크 하나만 제거한다.
남은 link의 순서·weight·kind를 비롯해 나머지 program은 변경하지 않는다.
2입력×6mask=12실행 중 새로운 단일 제거 대조는 8개, 재현 controls는 4개다.
이 기록들은 독립 표본이 아니다. 결과를 보고 mask를 추가·제외하지 않는다.

## 사전 예측과 판정

P1: 남은 약한 edge에 도착하는 E 링크를 제거하면 안정된 high goal이 된다.
startstrong에서는 drop_E_goal, goalstrong에서는 drop_E_start다.
P2: 강화한 edge에 도착하는 E 링크만 제거하면 안정된 low goal이 유지된다.
startstrong에서는 drop_E_start, goalstrong에서는 drop_E_goal이다.
P_prefix/P_goal의 네 대조는 방향을 정하지 않은 사전 지정 대조다.

1차 측정은 drop−full의 goal activation 차이이며, 약한 edge의 activation·차이도 보고한다.
전 좌표·매 tick·convergence와 단위별 counter는 raw에 보존한다.
종료 시점 비교를 동일 tick의 효과로 바꾸지 않는다.

안정 종료 상태는 stable_decision 또는 stable_ambiguous다.
안정 종료했고 goal<0.5−1e-6이면 low, goal>0.5+1e-6이면 high,
경계 구간 또는 비안정 종료는 inconclusive다. 이 폭은 공학적 판정보류 폭이며
고정점 오차 한계나 통계적 불확실성을 보장하지 않는다.

- full=low, drop=high: 이 고정 조건의 low predicate에 대한 개별 필요성 지지.
- full=low, drop=low: 같은 predicate에 대해서만 개별 비필요성.
- 그 외: 필요성 판정 null. 예산 종료·진동을 low/high의 성공·실패로 강제 분류하지 않는다.

비필요성을 궤적·다른 상태·다른 입력에서 무관하다는 뜻으로 쓰지 않는다.
어느 링크 하나의 충분성, 유일한 원인 고리, 복수 attractor나 basin은 이번 matrix로 판정하지 않는다.

## 출처와 독립 검산

R052 원본10파일과 R053 원본8파일의 정확한 경로·SHA-256을 spec에 동결했다.
R053 자료는 plan/source_manifest/raw_manifest/audit와 두 강화 입력의 full/off 4 raw다.
각 실행에 parents/와 anchors/로 원본 bytes를 복사하고 worker 직전에 다시 hash를 확인한다.
생산기는 R052 network의 program·drives만 읽고 부모의 최종 상태·proof·채택을 입력으로 쓰지 않는다.
R053 anchor의 outcome은 검산기의 재현 비교에서만 사용한다.

기존 R053 execute는 실제 hcr.dynamics.settle을 호출하므로 재사용한다.
검산기는 별도 independent_step을 쓰는 R053 verify_trajectory를 재사용하며
R054의 exact single-link mask·입력·schema·inventory·source·판정 규칙은 별도 확인한다.
검산기에 producer/dynamics/runtime/session import가 없어야 한다.
R052 여섯 native execution과 R053 네 anchor를 재검산하고 출처·plan/hash를 결속한다.
새 full/off 4개는 R053의 모든 tick/state/residual/stable·종료·counter와
절대·상대 1e-12로 일치해야 한다. 이 bridge는 실험 유효성 조건이지 P1/P2 지지 조건이 아니다.

## 실행·완료 계약

Run-HCR-R054.cmd: source·spec·부모 자료 동결 → synthetic self-test → 별도 목적의
startstrong 6조건 smoke와 2bridge → 최종 core 회귀 1회 → 연구 12조건 → 독립 audit → ZIP.
smoke는 연구 결과에 합산하지 않는다. --validate-only도 구현 검증용이다.
필수 완료 조건은 기록 완전성·출처·실제 삭제 조작·replay·종료/counter·bridge 통과다.
원하는 효과가 나오지 않으면 예측 반박 또는 판정불가로 그대로 보고한다.

기존 Python 3.12+만 사용하며 설치·다운로드·자동 retry·Git 조작은 원클릭에 없다.
최초 실패·부분 evidence와 로그를 보존한다. 구현 결함 수정·표적 재검증은 현재 작업에 포함되지만
연구 결과를 맞추기 위한 조건·기준·mask 변경이나 추가 실행은 하지 않는다.
이번 연구는 정상 완료 1회로 계획하며 검증 실패 시 연구를 자동 재시작하지 않는다.

변경은 R054 add-on·문서·신규 evidence·experiment index에 한정한다.
core/src/tests, 기존 release/manifest/evidence, 기본 dispatcher EXP-30을 보존한다.
검증 후 로컬 commit/main 병합까지 수행하고 현재 요청에서 원격 push는 하지 않는다.
