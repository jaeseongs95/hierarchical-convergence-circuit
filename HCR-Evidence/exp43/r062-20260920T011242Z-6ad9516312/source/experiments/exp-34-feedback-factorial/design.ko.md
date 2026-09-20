# EXP-34 / R053 동결 설계

## 질문과 범위

R052는 2-edge ++ chain의 배열 교환 후에도 구조 역할별 궤적이 같음을 확인했다.
다음 질문은 동결된 numerical network에서 두 feedback 집합의 개별 효과와 상호작용이다.
이번 단계는 native session 확장이 아니다. 증명·support·raw decision·terminal adoption은
모두 미측정(null)이며 수치 상태에서 이 값을 추정하지 않는다.

## 조건과 예측

path order, 빈 memory에서 생성된 R052 network, config, support link, group bias,
초기 activation 0.5와 기존 동기 갱신·종료 규칙을 고정한다.
입력은 weakweak(0.02,0.02), startstrong(1.0,0.02), goalstrong(0.02,1.0)이다.
각 입력은 off, edge_local_only, path_internal_only, full의 네 마스크를 모두 실행한다.

- edge-local E: p:0:0→e:0, p:0:1→e:1. A1→A0의 두 링크.
- path-internal P: p:0:1→p:0:0, goal→p:0:1. A1→A1의 두 링크.

두 집합은 서로소이고 전체 feedback의 합집합이어야 한다. 링크를 삭제하되 남은 링크의
순서·종류·가중치와 비feedback 구조는 그대로 둔다. 삭제 링크는 transmission에 세지 않는다.
R052 문서의 inter-level 후보 명칭은 실제 Group.level과 달라 새 실험에서는 쓰지 않는다.
원본 문서와 evidence는 수정하지 않는다.

사전 대안은 E 우세, P 우세, 두 집합 상호작용 또는 두 집합 모두 유의미한 변화가 없는 경우다.
P1은 두 강화 입력 각각에서 남은 약한 edge가 E-only/full에서는 0.5 미만이고,
off/P-only에서는 0.5 이상이라는 수치 예측이다. proof 가정이나 채택 예측이 아니다.
P2는 각 입력에서 goal의 2×2 상호작용 대비가 동결 허용오차 내 0인지 판정한다.
특정 방향을 성공 조건으로 삼지 않는다. 각 입력의 goal, e:0, e:1에 대해
E|P=0, E|P=1, P|E=0, P|E=1 및 Y11−Y10−Y01+Y00를 수치로 보고한다.
이는 고정된 결정론적 대비이며 통계적 유의성·확률적 일반화를 주장하지 않는다.
전체 상태·매 tick 궤적·종료 상태·residual·stable steps와 별도 kernel counter를 보존한다.
ticks는 각 실행의 자체 종료 시점까지 센 값이지 동일 시각에서의 상태 효과가 아니다.

## 원자료와 bridge

frozen_spec.json에 R052의 plan, source/raw manifest, audit와 여섯 실행 기록의 정확한
경로·SHA-256을 동결했다. 별도 parents/에 원본 bytes를 복사하며 부모 실행은 새 표본으로 세지 않는다.
생산기는 c001의 network program·drives만 입력으로 추출하고 부모의 candidate나 최종 상태로
초기 상태·마스크·종료·실행 여부를 선택하지 않는다. 전 조건은 fresh initial state에서 시작한다.

검산기는 여섯 원본 execution을 기존 NativeVerifier로 다시 검증한다. 새 full/off는 c001/c000의
각 입력에 대응하여 모든 tick/state/residual/stable, 최종 convergence와 kernel counter를 비교한다.
절대·상대 허용오차는 각각 1e-12다. 이 여섯 bridge는 수치 실험의 유효성 조건이지
새 실행의 native proof/adoption 동등성 검증이 아니다.

## 실행·검증 계약

`Run-HCR-R053.cmd`는 기존 Python 3.12+만 사용한다. 자동 설치·retry·Git 변경은 하지 않는다.
소스·조건·부모 자료를 먼저 동결하고 synthetic self-test, 별도 목적의 weakweak 4조건 smoke와
독립 audit, 최종 core regression 1회, 본 연구 12조건과 독립 audit, evidence ZIP 순으로 수행한다.
`--validate-only`는 구현 검증 목적이며 연구 결과와 합산하지 않는다.
생산기는 기존 hcr.dynamics.settle, 검산기는 별도 hcr.evaluation.audit.independent_step을 사용한다.
검산 과정에서 producer/runtime/dynamics 모듈을 import하지 않는다.

실행 완성 기준은 12기록의 완전성, 입력·마스크·소스·원자료 결속, 수치 replay, 종료·counter,
여섯 bridge 통과다. 부분 마스크의 효과 방향이나 차이 유무는 실패 조건이 아니다.
실패하면 최초 로그·부분 evidence를 보존한다. 구현 결함의 수정·표적 재검증은 허용하지만
결과를 맞추기 위한 조건·마스크·평가기 기준 변경이나 자동 재실행은 허용하지 않는다.

## 해석 한계

한 topology, 한 config, 세 drive의 12개 counterfactual 분기다. 독립 표본 12개가 아니다.
고정 커널의 링크 제거 효과는 판별할 수 있으나 native 보류 원인, learned circuit,
Graph→Circuit 학습, 인간 인지, 물리 에너지 효율의 증거로 확대하지 않는다.
개별 링크 하나의 기여나 강도 dose-response는 이번 집합 마스크로 분리하지 못한다.
native proof·support·adoption까지 연결하려면 versioned core 계보와 새 native 검산 계약이 필요하다.

변경 범위는 R053 add-on·문서·신규 evidence와 experiment index다.
core/src/tests, R048~R052 소스·manifest와 기존 evidence, 기본 dispatcher EXP-30은 유지한다.
현재 요청은 로컬 구현·검증·커밋·main 병합까지 수행하며 원격 push는 하지 않는다.
