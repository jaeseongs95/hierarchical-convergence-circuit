# EXP-36 / R055 사전 동결 설계

## 질문과 근거

R054에서 P_prefix(p:0:1→p:0:0) 삭제는 startstrong에서는 low goal을 유지했지만
goalstrong에서는 high로 전환시켰다. 이번에는 고정 총량을 두 edge drive에 배분하면서
이 삭제 효과의 입력 의존성을 5개 사전 지정 점에서 측정한다.
전체 subset·충분성·native 채택 실험으로 범위를 넓히지 않는다.

## 조건

| id | 입력 표기 (e:0,e:1) | 실제 kernel drives (e:0,e:1) |
|---|---|---|
| startstrong | (1,.02) | (4,.08) |
| startlean | (.755,.265) | (3.02,1.06) |
| balanced | (.51,.51) | (2.04,2.04) |
| goallean | (.265,.755) | (1.06,3.02) |
| goalstrong | (.02,1) | (.08,4) |

입력 총량 1.02, scale=4, edge drive 총량 4.08, goal drive=0이다.
이 표는 새로운 native observation/session을 생성한다는 뜻이 아니다.
R052 c001/start_edge 원본 network의 program을 공통으로 쓰고 drives만 표대로 덮어쓴다.
원본 drives와 입력 표기·적용 drives를 raw에서 구분한다.
부모 두 강화 입력의 program이 같은지도 검산한다.

각 점에서 full과 drop_P_prefix 두 mask를 실행한다. 해당 top-down link의 삭제 외
program의 group/bias/support/link 순서·weight는 불변이다.
모든 branch는 전 좌표 0.5에서 새로 시작하며 default config·동기 갱신·종료 규칙·160 tick 예산을 유지한다.
10조건 중 양 끝 4개는 R054 재현 control, 내부 6개가 새 대조다. 독립 표본이 아니다.

## 사전 측정과 판정

primary는 각 입력의 delta_goal=drop_P_prefix−full 벡터다.
e:0/e:1 두 고정 좌표의 값과 delta, 전 좌표·모든 tick·종료 상태·단위별 cost를 보존한다.
중간 입력이나 동률 조건에서 weak edge를 사후 선택하지 않는다.

stable_decision/stable_ambiguous 종료이면서 goal<0.5−1e-6이면 low,
goal>0.5+1e-6이면 high, 그 외는 inconclusive다.
full=low와 drop=high이면 이 맥락의 low 술어에 대한 개별 필요성 true,
둘 다 low이면 false, 나머지는 null이다. nonstable에서도 연속값은 보고한다.
1e-6은 공학적 판정보류 폭이지 고정점 오차 한계·통계적 불확실성 보증이 아니다.

기술 대조량은 delta(goalstrong)−delta(startstrong),
delta(goallean)−delta(startlean)이며 부호를 결과 전에 고정한다.
비방향 사전 대조다. 대칭, 단조성, 중앙점의 전환, 전환점 존재를 성공 조건으로 두지 않는다.
topology/path 길이와 p:0:1 bias가 비대칭이므로 반사쌍의 동일성이 기대값이 아니다.
5점 사이를 보간해 연속 구간의 결론을 만들거나 결과에 따라 입력을 추가하지 않는다.

## 출처·검산·실행 계약

spec에 R052 부모 원본 10파일과 R054 anchor 원본 8파일의 경로·SHA-256을 동결했다.
anchor는 plan/source_manifest/raw_manifest/audit 및 두 끝점 full/drop_P_prefix raw 4개다.
worker는 공통 R052 program만 사용한다. anchor outcome은 독립 auditor의 비교용이다.
R052 native provenance replay와 R054 anchor trajectory 재검산은 새 연구 표본이 아니다.
bridge는 drives·전체 tick/state/residual/stable·최종 상태·종료·counter를 비교한다(수치 허용차 절대/상대 1e-12).

생산기는 기존 R053 execute와 R054 masked_program을 재사용한다.
검산기는 생산기·dynamics/runtime/session을 import하지 않고 기존 independent_step 기반
verify_trajectory로 모든 tick과 첫 종료·cost를 재계산한다.
native session/proof/support/raw decision/adoption/실제 에너지는 null로 남긴다.

Run-HCR-R055.cmd 순서: source/spec/parents/anchors 동결 → synthetic self-test →
별도 implementation smoke 양 끝 4조건·4bridge → 최종 core regression 1회 → 연구 10조건 →
독립 audit → summary·bundle·ZIP. smoke 결과는 연구와 합산하지 않는다.
정상 본 실험은 1회이며 자동 retry·덮어쓰기·조건 사후 변경은 없다.
실패는 최초 logs·traceback·부분 evidence를 보존한다. 구현 결함의 수정·표적 검증은 허용하지만
연구를 재시작하거나 조건/기준을 바꿔야 하면 원인을 보고하고 재계약한다.

범위는 R055 add-on·문서·index·신규 evidence뿐이다. 기존 core/tests/manifests/evidence와
기본 dispatcher EXP-30은 유지한다. 검증 완료 후 로컬 commit/main 병합하며 push는 하지 않는다.

## 주장 범위

고정된 topology·bias·initial·종료 규칙 안에서 배분에 따른 수치 반응을 측정한다.
topology, bias, 경로 길이, link 방향의 원인 분리나 충분성, basin/attractor,
인간 인지·LLM 내부·native proof/adoption의 증거가 아니다.
