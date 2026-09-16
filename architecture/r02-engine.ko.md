# HCR R0.2 — Adaptive Graph/Circuit Engine

상태: **소스 작성 완료, 이 배포 세션에서 런타임·시험 미실행**. R0.1의 실행 결과를 R0.2 결과로 전용하지 않는다.

## 1. 기준 소스와 변경 경계

사용자가 지정한 `jaeseongs95/hierarchical-convergence-circuit` 원격 조회는 이 세션의 GitHub 연결에서 404였다. 대신 이전 세션에서 실제 생성된 `hierarchical-convergence-circuit-r01-source.zip`을 Library에서 회수했다. SHA-256은 `c69ba87af591fa508f9d9cfd9b42e5515aef5206034e78b89e801f56e43d50b0`이다. 최신 원격 HEAD와의 동일성은 확인하지 못했다.

이전 ZIP의 실제 소스·설정·시험을 읽고 그 위에 추가했다. 인계 문서만으로 인터페이스를 추정하거나 새로운 폴더 skeleton으로 대체하지 않았다. 안전 적용기는 로컬 기준 파일의 해시가 다르면 변경을 시작하지 않는다. CRLF/LF 차이는 본문 변경과 구별한다.

상위 `theory / formalism / evidence / architecture / experiments / papers` 구획은 유지한다. 구현은 `src/hcr`에만 있다. 실험별 엔진 복제, frozen 버전 import chain, 원격 변경, 모델 설치가 없다. 기존 `Engine`/`Memory`/`Config`와 R0.1 기본 CLI는 유지한다. `AdaptiveEngine`은 같은 모듈 안의 추가 실행 controller이며, 관측·proof·trace와 특히 `dynamics.tick/settle`을 공유한다.

## 2. 구현 범위

고정된 두 A 수준과 기존 계산 primitive에서 **D/dependency 확장만** 적응시킨다. 입력은 작은 directed symbolic graph의 공개 topology, edge score, start/goal이다. 기본 한도는 8 edges, 경로당 4 primitive, 최대 4 goal routes다. 감각 encoding이나 자연어 후보 생성은 하지 않는다.

부분 컴파일 범위는 **검증된 양의 primitive proof에서 추출한 길이 2·3의 연속 directed path motif**다. 범용 arbitrary-subgraph mining은 아니다. 현재 grammar에서 관계 종류는 `open_edge` 하나다. 따라서 같은 길이 motif는 위치나 객체 이름이 달라도 같은 역할 구조다. 출현 횟수와 독립 episode 검증 횟수를 구분한다.

새 task family, A/M 자동 탐색, 뉴로모픽/GPU 성능 우월성, 인간 감각·직관의 사실성은 이번 구현 범위가 아니다.

## 3. 실제 실행 흐름

```text
공개 Observation
  → start의 RoutePrefix 하나로 Workspace 시작
  → 현재 frontier의 primitive outgoing 후보 조사
  → 학습된 부분회로의 역할 매칭 (독립 예산)
  → 저장된 회로 program을 현재 역할에 실체화
  → 동일 dynamics kernel에서 복수 회로 후보 경쟁/억제
  → 활성화·mismatch 조건을 충족한 macro 또는 primitive 1-step 제안
  → 선택 경로 확장 + macro 내부의 다른 분기 보존
  → goal에 도달한 경로들로 판단 signal graph 구성/수렴
  → 양의 판단이면 해당 경로로 종료 가능
  → 음의 판단이면 미탐색 dependency를 계속 확장
  → 모든 경로가 검사됐을 때만 음의 판단 확정
  → primitive proof 복원 → 외부 평가
  → 외부 검증 성공의 부분경로를 역할화/누적/등록
  → 오류 feedback이면 사용 회로의 prior 약화
  → ADAPT에서 허용된 추가 관측 요청
  → 다음 revision에서 primitive graph 재계산
  → memory 저장/reload → 다음 episode의 후보/routing/prior에 반영
```

`MismatchSignal`은 새 입력, 미해결, 음의 판단의 coverage 부족, feedback 재확장을 기록한다. 현재 정책은 결정적 경로 확장과 circuit/primitive 선택이다. mismatch의 연속값으로 최적 탐색을 학습하는 정책은 아니다. `novelty`나 `holdout` label을 받아 분기하지 않는다.

## 4. 모듈 책임

| 위치 | 책임 |
|---|---|
| `model.py` | 기존 계약 보존 + AdaptiveConfig/Cost/Decision, ExpansionBudget, MismatchSignal |
| `identity.py` | NodeIdentity, SemanticIdentity, RoleIdentity, revision-bound RoleBinding |
| `patterns.py` | 역할·관계·entry 조건·output 역할·컴파일된 program의 구조 certificate |
| `workspace.py` | AdaptiveWorkspace, RoutePrefix, 실제 frontier/goal route 확장 및 측면 분기 보존 |
| `expansion.py` | ExpansionPolicy와 bounded deterministic D policy |
| `activation.py` | CircuitActivationPool, 저장 program 실체화, 공통 커널의 복수 후보 경쟁 |
| `dynamics.py` | 기존 tick/settle + 기록 어댑터 settle_recorded; 수치 갱신식 복제 없음 |
| `compiler.py` | SubgraphCompiler: 실제 최종 primitive proof의 연속 motif만 추출 |
| `circuits.py` | 독립 R0.2 schema의 PatternCircuit/Pending/AdaptiveMemory |
| `learning.py` | 검증 증거 축적·등록·강화·오류 약화·원자적 memory 교체 |
| `runtime.py` | AdaptiveEngine의 추론·feedback·revision 권한 및 실행 순환 |
| `evaluation/adaptive_protocol.py` | truth/실험 분류를 격리한 개발 실험 |
| `evaluation/adaptive_audit*.py` | 생산 알고리즘을 호출하지 않는 경로·수치·학습·집계 재구성 |

## 5. Graph / Circuit / Proof / Trace

공개 topology는 입력으로 주어진 관계다. 동적 dependency graph는 해당 관계를 어느 순서로 얼마나 펼쳤는지를 나타낸다. signal graph는 후보 활성화·경쟁·재귀 상호작용이며 A0/A1을 공유한다. 저장 circuit은 역할화된 signal program과 적용 조건이다. primitive proof DAG는 최종 결론의 직접 근거이며, trace는 시간순 실행 기록이다.

macro 하나로 3개 edge를 진행해도 primitive proof D를 1로 기록하지 않는다. 긍정 proof는 `assumed_open → start_edge → extend_path`를 현재 인스턴스에서 복원한다. 부정 proof는 모든 공개 start-goal 경로의 차단 근거가 필요하다. 외부 reference가 coverage를 다시 확인한다.

NodeIdentity는 특정 후보 문맥의 실행 참조, SemanticIdentity는 현재 관측의 vertex, RoleIdentity는 저장 패턴의 `R0…Rn`이다. 같은 semantic은 다른 후보의 node에 나타날 수 있다. 기존 node의 semantic을 몰래 바꾸거나 이전 observation digest/revision의 binding을 재사용하지 않는다.

## 6. 부분회로와 활성화

회로에는 이전 객체 이름이나 goal 정답을 저장하지 않는다. 저장 항목은 역할, 연속 관계, 적용 조건, output role, compiled primitive program, kernel signature, 검증 episode/feedback/proof 해시, strength/version이다. 양의 motif만 학습하는 것은 이번 task grammar의 명시적 범위다.

매칭은 관측 topology와 역할 제약만 읽는다. 순서는 결정적이며 hidden truth를 읽지 않는다. score는 매칭 이후 공통 수렴 pool의 evidence drive 및 mismatch에 쓰인다. prior는 다음처럼 관측 불확실성이 클수록 영향을 준다.

```text
prior = prior_gain × strength × n/(n+1) × max(1 − |score|)
mismatch = max(max(0, −score))
```

후보의 c:i gate는 같은 커널에서 상호 억제한다. 안정화, activation threshold, mismatch threshold를 통과한 후보만 macro가 된다. 충분한 활성화가 없거나 매칭 예산/후보 용량이 초과되면 부분 후보 목록을 임의 승자로 삼지 않고 primitive 경로로 복귀한다.

현재 최종 판단 graph에는 primitive 신호 노드를 다시 구성한다. **연구적으로 주장할 압축은 우선 dependency 탐색과 경로 확장 단계의 압축**이다. 최종 수렴 전체를 단일 operation으로 바꿨다는 주장은 하지 않는다. 저장 회로 program은 경쟁 pool에서 실제 사용된다.

## 7. 예산과 보류

별도 한도: 확장 횟수, frontier 폭, 매칭 edge 검사 횟수, 회로 후보 수, primitive 경로 깊이, goal route 수, common signal group 수, convergence tick 수.

매칭/풀 한도 초과는 primitive fallback이다. 전체 dependency 계산 한도 초과는 `value=null`, `budget_exhausted`다. 검사하지 않은 경로를 제거해 부정 결과를 확정하지 않는다. 판단 근거가 전혀 없는 score 0/None 입력은 구조 bias만으로 답을 만들지 않는다. 수렴 실패와 경로 예산 실패는 trace에서 구분한다.

## 8. 학습·재확장·지속성

독립 episode가 `min_valid_episodes`에 도달해야 circuit을 등록한다. 같은 episode의 반복 호출/수정/동일 motif 중복 출현은 새 독립 증거로 세지 않는다. frozen inference는 memory를 바꾸지 않는다. feedback은 held decision/observation/memory version에 묶이고, 재전달은 거부한다.

오류 뒤 사용 circuit의 strength는 weakening 비율로 낮춘다. 실제 오류가 확인된 ADAPT에서만 추가 관측을 요청한다. 요청한 edge score 외의 topology·identity·다른 score를 수정한 revision은 거부한다. 수정 attempt는 circuit을 우회한 primitive 재계산이며 최초 기록을 덮어쓰지 않는다. 추가 측정에 의존한 오류 수정이지, feedback bit를 정답으로 복사하는 처리가 아니다.

R0.2 memory는 `hcr-memory-r02`다. 기존 R0.1 memory를 덮어쓰거나 자동 변환하지 않는다. 다른 설정 signature의 memory도 거부한다.

## 9. 비용 해석

`graph_nodes_created/graph_edges_created`는 dynamic dependency 상태와 arc다. `dynamic_groups_created/dynamic_links_created`는 signal 후보 graph다. `circuit_groups_instantiated`는 저장 program에서 실체화한 group이다. 이 세 개념을 혼합하지 않는다.

추가 카운터는 expansions, frontier_retirements, topology_edge_checks, candidate_circuits, binding_operations, pool_calls, circuit_reuses, primitive_candidates, learning_updates, storage_bytes다. kernel_ticks, group_updates, signal_transmissions, normalization_ops, proof_nodes_reconstructed, compilation_items, memory_write_items, wall_seconds도 유지한다.

`signal_events = signal_transmissions`, `convergence_ticks = kernel_ticks`, `proof_reconstruction_cost = proof_nodes_reconstructed`, `storage_cost = storage_bytes`는 **별칭**이다. 이들을 원래 값과 더하면 중복 집계다. 저장비용은 학습 후 memory 문서의 직렬화 byte 추정량, 실제 checkpoint bytes는 별도 이벤트로 남긴다. wall time은 계측값이며 재검산으로 재현하지 않는다.

Warm이 graph node를 줄이면서도 binding/pool/signal 비용은 증가할 수 있다. 결과에서 각각 비교하고 총 속도 우월성을 미리 정하지 않는다.

## 10. 독립 검산 범위

`verify`는 파일 집합·해시·append-only chain, 각 tick의 별도 수식, 전체 매칭 scan 순서/예산, 공통 커널 program 구성, 후보 순위, macro 측면 분기 보존, 판단 및 부정 coverage, proof, 학습 전이, memory checkpoint, 비용 및 summary를 검산한다.

수치/확장/학습/집계 재계산에서는 production runtime/dynamics/expansion/activation/learning을 호출하지 않는다. JSON 계약, memory 구조 certificate loader, 기존 외부 proof/reference validator는 공유한다. 따라서 구현과 완전히 독립된 제삼자 인증이나 실제 실행의 암호학적 증명은 아니다. 기록 및 선언된 설정의 내부 일관성 검산이다.

## 11. 실행 전 상태

이 배포의 사실은 소스 생성, Python 3.12 AST 구문 검사, 기준 파일 보존 검사, 패키지 해시 검사까지다. 테스트·demo·runtime·PowerShell·git 작업은 수행하지 않았다. `evidence/implementation/r02_static_review.json`의 실제 수행 항목과 `docs/R02_ACCEPTANCE.ko.md`의 사용자 실행 기준을 구분한다.

### 비용 계측의 세부 범위

현재 `binding_operations`는 역할 매칭 중 검사한 관측 arc 수이며 `binding_checks`와 같은 값이다. 자료구조 hash/직렬화/계약 검사의 모든 저수준 instruction을 포괄하는 FLOP 계수가 아니다. 추론 wall time은 `infer` 내부 계산부터 proof 복원까지이며 엔진 생성 시 memory certificate 검사는 별도 초기화 비용이다. 학습 wall time과 checkpoint byte 수는 따로 남긴다. 일반적인 end-to-end 성능 benchmark가 필요하면 초기화·저장 I/O와 반복 통계도 추가해야 한다.
