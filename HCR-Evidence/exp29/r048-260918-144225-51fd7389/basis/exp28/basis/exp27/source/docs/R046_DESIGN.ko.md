# EXP-27 / R046 — A의 결과를 B의 추론에 전달하기

## 동결 질문
EXP-26에서 직접 circuit 적용은 expansion을 2→1로 줄였지만 decision은 33 ticks를 다시 수행했다. 원형 drive 서명 불일치와 수치 궤적 동일성도 분리됐다. 이번에는 pool warm-start를 그대로 구현하지 않고, 직후 논의한 **앞선 추론 A의 수치 상태 / 관계·대상 binding·근거를 새 질문 B에 전달하는 기능**을 최소 구현한다.

## 구현 수준
기존 hcr의 `discover_paths`, `make_program`, `settle`, `reconstruct`를 그대로 호출하는 **새 순차 추론 어댑터**다. 기존 AdaptiveSession, 학습회로 선택기, selector/adoption pipeline의 성능을 그대로 측정하는 후속 버전이라고 표시하지 않는다. 기존 native 파일과 이전 evidence는 수정하지 않는다. EXP-26의 native 전체 verify를 선행하고 동일 핵심 함수의 cold 회귀를 검사한다.

학습 memory는 원자료로 보존하지만 이 어댑터에서는 검색·pool·학습을 실행하지 않는다. 학습회로의 효과와 중간 산출물 유지의 효과를 동시에 바꾸지 않는다. 숫자 전달은 **A decision→B decision**이고, EXP-26 pool→decision 전달과 다르다.

## 질문·조건
A는 같은 episode의 revision 0에서 u→v→w를 판단한다. B는 revision 1에서 (1) u→v→w→z, (2) p→q→r→s, (3) u→v→w→z에서 v→w 관측만 반전한 입력이다. ID 두 배치에서 A를 각각 한 번 생성하고, 동일 A record를 네 처리군에 읽기 전용으로 제공한다. B 3상황×2 ID×4군=24조건, A 원천 2개. A를 24개 독립 근거로 중복 집계하지 않는다.

- cold: native 경로 탐색·수렴·proof 재구성.
- state_carry: 원천 근거가 현재 입력과 일치하고 query start가 맞을 때, edge/prefix binding으로 대응한 A 활성값만 B initial에 전달한다. 새 goal은 0.5이며 안정화 이력은 넘기지 않는다. 이후 B kernel은 전부 재실행한다.
- proof_memo: 일반적인 의존성 검증형 proof memo. relation군과 똑같이 B 수렴 전에 후보를 구성할 수 있다. 올바른 대상·근거를 확인하고 기존 proof node의 참조를 재사용한다. 일부러 정답만 저장하는 취약한 캐시를 기준선으로 삼지 않는다.
- relation_carry: `reachable(start,end)`, episode, origin revision, 관측 의존성, proof ref를 갖는 typed relation node. 같은 기준으로 검증한 뒤 **B의 native 수렴 전에** A proof와 새 edge로 B 관계 후보를 구성한다. 이를 native kernel로 별도 확인하며, 실제 B proof의 parent는 A node의 참조다.

memo와 relation은 같은 논리 기능을 수행할 수 있다. 차이가 없어도 정상 결과이며, 관계 저장을 HCC만의 고유 성과로 주장하지 않는다. 숫자·proof 전달의 결합군은 이번에 넣지 않는다.

## 통제와 비용
모든 군은 같은 B 원관측을 받고 native 전체 경로 탐색 및 동일 decision graph를 만든다. **관계 저장만으로 decision을 생략하거나, 이전 True를 새 관측 score로 주입하지 않는다.** 이번 proof carry는 proof 재구성의 부분 재사용이며 그래프 탐색 절감은 주장하지 않는다.

A 원천 계산, carry 생성/읽기 byte와 field 검사, B kernel ticks/group updates/link transmissions, native 탐색 edge 검사, proof 생성/참조/검증, wall time은 개별 기록한다. 서로 다른 단위를 합치지 않는다. 전체 proof를 펼쳐 독립 계산한 D_DAG와 새로 생성한 inference node 수를 구분한다.

정상 입력의 대상 불일치·근거 변경은 명시적 gate rejection과 사전 등록된 cold 경로로 진행한다. schema 파손·참조 손상은 failure이며 고쳐서 진행하지 않는다. 이전 node는 삭제/갱신하지 않는다. B가 invalidated A node를 부모로 사용하지 않는지 검사한다. 이는 새로운 학습이나 feedback 수정이 아닌 **관측 revision에 대한 재사용 차단·재계산**이다.

## 측정과 검산
원형 program/drives, 누락 drive를 0으로 해석한 유효 drive, initial state, 모든 tick, final convergence, 실제 proof node identities, export/import 경계와 비용을 raw에 보존한다. 원형 서명 불일치를 수치 변화와 혼동하지 않는다. 실행 코드와 별도 evaluator는 BFS로 topology를 열거하고 native 코드를 import하지 않는 scalar 갱신과 논리 규칙으로 raw를 재계산한다. evaluator는 정답을 실행기에 제공하지 않는다.

실험 결과는 `supported / falsified / not_evaluable`로 따로 판정한다. 틀린 정답·절감 없음·동치 없음은 audit 실패가 아니다. schema/graph/reference/measurement 오류와 예산 종료는 구분한다. 성공할 때까지 재실행하지 않는다. 회귀·smoke·오류 주입 검사는 연구 모집단에 넣지 않는다.

## 개발 중 construct 점검
초기 어댑터 초안은 B 수렴 후에만 A proof를 이어붙였다. 이 경우 새 관계 생성과 사후 proof 압축이 구별되지 않으므로, release 전 후보 생성 경계를 native B network 생성보다 앞으로 옮겼다. native decision은 여전히 재실행하며 이 비용은 숨기지 않는다. 0.85 관측의 smoke는 구현 점검이지 연구 결과가 아니다.

## 측정 비용의 겹침과 미측정
`carry.proof_nodes_created`는 해당 B record가 새로 소유한 proof node의 전체 수다. cold에서는 native 재구성 node와 겹치므로 `native.proof_nodes_reconstructed`와 더하지 않는다. 참조·field 검사 및 packet byte는 명시한 연산의 inventory이지 Python의 모든 CPU 연산 수가 아니다. provenance hash와 raw 직렬화의 모든 CPU 비용, process peak memory, energy는 측정하지 않는다. query wall time도 전체 launcher wall time과 다르다.

## 재귀 경계
이번 구현은 하나의 source proof A를 하나의 후속 질문 B에 전달하는 경계만 지원한다. B를 다시 C에 무제한 전달하는 중첩 foreign-proof 저장소, 자동 abstraction 생성, 새 circuit compilation을 구현한 것으로 표시하지 않는다. 이미 foreign parent를 가진 source를 다시 export하려 하면 scope 계약 실패로 중단한다.
