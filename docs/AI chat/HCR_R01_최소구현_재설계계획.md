# HCR R0.1 — 계층적 수렴·회로 학습 엔진 최소 구현 계획

상태: 설계 제안. 이번 산출물은 계획서이며 구현·성능 검증 결과가 아니다. 기존 실험 소스와 evidence는 변경하지 않는다.

근거 문서: `계층적_수렴_회로_통합가설_감각_착시_ADM_2026-09-16.md` 및 직전 `구현가능성_검토.md`.

## 0. 이번 결정

기존 LLM 실험기의 다음 버전을 만드는 대신, 독립적인 단일 Python 프로젝트 `hcr-engine`을 처음부터 구성한다. 첫 산출물 이름은 `HCR R0.1`로 한다. 과거 `v0xx` 파일이나 중첩 `frozen...` 실행 의존성을 새 엔진에 넣지 않는다.

최소화할 것은 환경·규모·가소성 규칙·표현 종류다. 두 A 수준에서의 공통 계산, 상·하향 재귀, 실제 graph↔circuit 변환, 외부 feedback에 의한 재확장은 제외하지 않는다.

첫 목표:

> 같은 수렴 커널이 두 표현 수준에서 작동하고, 낯선 입력에는 임시 그래프를 만들며, 반복적으로 검증된 관계 구조가 재사용 회로로 남고, 새 입력에서 이를 재활성화하고, 오류 시에는 그 회로를 약화하고 그래프를 다시 확장하는 하나의 실행계를 만든다.

여기서 ‘가설을 만족하는 최소 구현’은 핵심 메커니즘을 실제 상태·연산·학습 변경으로 연결한다는 의미다. 정확도·비용 개선까지 달성했는지는 구현 후 별도로 판정한다. 기능적 소프트웨어 회로를 생물학적 회로나 물리 뉴로모픽 구현과 동일시하지 않는다.

## 1. 문서 개념 → 최소 구현 계약

| 문서의 핵심 | R0.1에서 실제로 구현할 것 | 단순 대체로 인정하지 않을 것 |
|---|---|---|
| 공통 계산 primitive, §7·40 | 두 A 수준에 같은 activation/competition/inhibition/recurrence 함수 적용 | 수준별로 별도 정답 알고리즘 실행 |
| 계층 간 상·하향 상호작용, §28~30 | 하위 상태가 상위 후보가 되고 상위 메시지가 하위 활성에 돌아감 | A0→A1 단방향 파이프라인 |
| Binding Continuity, §5·23 | identity·의미·역할·근거 버전을 분리하고 회로 재호출 시 역할을 새 입력에 결합 | ID 문자열 같음만으로 의미 결합 성공 판정 |
| 동적 Thought-Graph, §1·11~13 | 필요한 후보/관계/규칙 인스턴스를 예산 안에서 실제 추가 | 처음부터 정답 graph를 제공 |
| 학습·회로 압축, §14~16 | 검증된 부분 그래프를 역할 변수화하고 고정 희소 연결·실행 계획으로 저장 | 입력 문자열→정답 캐시 |
| 회로 재사용, §11·15 | 새 입력에 역할을 결합해 저장된 연산 구조를 같은 커널로 활성화 | 이전 출력과 이전 episode 상태 반환 |
| 오류 후 재확장, §20~21 | 외부 오류 신호 또는 내부 불일치로 회로 의존을 낮추고 새 후보/관계를 탐색 | 실패 결과를 지우고 최초 성공처럼 기록 |
| 내부 안정≠현실 정확, §8·31 | 수렴 판정과 외부 채점을 완전히 분리 | margin을 정답 확률로 간주 |
| 관측 D와 실행량 구분, §3·16~17 | primitive proof D, 커널 갱신, 신호 전달, 탐색, 검증·설명 비용 별도 기록 | macro 1회 호출을 proof D=1로 바꿈 |

문서의 표기·구분은 유지한다. 아래의 자료구조, 정책, 범위와 기본값은 R0.1을 위해 제안하는 구현 선택이며, 문서에 이미 정해진 알고리즘이라고 주장하지 않는다.

## 2. 구현 범위: 하나의 작은 세계에서 전체 순환 연결

### 2.1 환경 제안

첫 도메인은 `toy_relational_world` 하나다. 소수의 대상, 잡음·부분 관측이 있는 특징, 작은 공개 규칙 집합으로 관계 판단을 수행한다.

예시: 두 연결이 통과 가능한지에 대한 불확실한 관측으로, A→B→C 경로의 통과 가능성을 판단한다. 이름과 표면 관측은 바뀌어도 같은 관계 패턴이 재사용될 수 있다. 추가 관측이나 다른 경로 후보가 있는 예외도 포함한다.

- 낮은 A: 관측 특징의 해석 후보. 예: 각 연결이 통과 가능/불가능한지.
- 높은 A: 관계·경로 해석 후보. 예: 어떤 관계 구조가 전체 판단을 지지하는지.
- 두 수준 모두 후보 활성·경쟁·억제·재귀 업데이트에 같은 커널을 사용한다.
- 연결이 실제 통과 가능한지와 최종 정답은 환경의 숨은 상태다. 엔진에 직접 전달하지 않는다.
- 임계값 기반 특징 adapter, 공개 규칙, 후보를 만드는 기본 연산은 설계자가 제공한다. 이 단계에서 감각 encoder나 원시 논리 자체를 학습했다고 하지 않는다.

이 환경은 감각/직관의 실제 데이터 재현이 아니라, 낮은 수준의 불확실한 해석과 높은 수준의 관계 판단을 하나의 실행계에 연결하는 최소 작업이다.

### 2.2 첫 구현 규모 상한안

| 항목 | 초기 범위 |
|---|---|
| 표현 수준 | 낮은 A / 높은 A의 2수준 |
| 커널 | 단일 bounded recurrent update |
| 기본 M | CIRCUIT_REUSE / GRAPH_EXPANSION 두 실행 방식 |
| 대상/관측 범위 | 소수의 대상과 유한 특징 슬롯, 실제 영상·음성 없음 |
| primitive 의존 깊이 | 개발 시나리오에서 1~4 범위 |
| 후보 수 | 전체 64개 이하, 경쟁 집합별 소수 후보 |
| 장기 회로 메모리 | 최대 16개 템플릿부터 시작 |
| 실행 예산 | tick·후보·확장·관측 요청 각각 상한 |
| 학습 | 성공한 경로의 구조 추출 + 재활성 연결 강화/약화 |
| 런타임 | CPU, 단일 프로세스, 단일 순차 scheduler |
| 입력/출력 | CLI + JSON/JSONL |

수치는 개발 상한 제안이다. 성능이 좋아 보이는 조건을 골라 사후 바꾸지 않는다. 개발용 사례에서 수치 안정성을 점검한 뒤 평가에 쓸 설정을 동결한다. R0.1에서 깊이 1~4는 성능 주장이 아니라 작은 graph로 기전을 검증하기 위한 범위다.

### 2.3 이번에 만들지 않을 것

실제 카메라/후각/음성 adapter, 대규모 언어 모델 연동, CUDA/스파이킹/뉴로모픽 backend, 대규모 분산 실행, 자유로운 A 단계 생성, 범용 메타학습, 자연어 설명기, GUI, 서비스 API, 플러그인 체계는 제외한다.

LLM을 제외하는 이유는 편의를 위해 가설을 바꾸려는 것이 아니라, 이번 결과가 외부 모델의 추론인지 새 엔진의 계산인지 섞이지 않게 하려는 것이다. 구현 후 adapter로 추가할 수 있지만 빈 adapter 계층을 미리 만들지는 않는다.

## 3. 최소 실행 사례

동일 코드·동일 상태 전이 정책에서 다음 순환을 연결한다.

### 3.1 미학습

정답 회로를 사전에 넣지 않는다. 공개 primitive와 후보 구성 규칙만 있다. 입력을 받고 낮은 A의 특징 후보를 활성화한 뒤 높은 A의 관계 후보를 형성한다. 기존 회로가 없거나 불일치가 크면 규칙 라이브러리에서 후보 의존관계를 확장한다. 후보 선택은 공통 커널이 수행한다.

### 3.2 학습

환경 feedback이 실제 성공을 확인하면, 그 결정에 사용된 부분 그래프의 구조와 근거를 검사한다. 같은 역할 구조가 서로 다른 관측 인스턴스에서 반복 검증되면 역할 변수화한 회로 후보로 편입한다. 정확한 원문 입력이나 정답 label을 키로 저장하지 않는다.

### 3.3 숙련

새 이름·새 관측의 같은 관계 유형에서 회로의 guard를 검사하고 현재 대상들을 역할에 바인딩한다. 현재 episode의 활성 상태는 새로 초기화하고, 학습된 연결과 prior만 재사용한다. 고정 topology를 재활성화하여 동적 탐색·관계 재구성 비용을 줄일 수 있는지 측정한다. 회로 역시 두 수준의 같은 dynamics 안에서 후보로 경쟁한다.

### 3.4 모호함과 오수렴

학습 분포에서는 유효했던 회로가 불완전한 관측·편향된 경험에서 강한 prior가 될 수 있다. 같은 코드가 안정되지만 외부 환경과 다른 결과를 낼 수 있도록 관찰한다. 정답을 알아낸 뒤 반대 값을 강제로 출력하는 가짜 오수렴 시나리오는 만들지 않는다.

오수렴 단위시험에는 명시적으로 주입한 prior를 사용할 수 있다. 그러나 통합 학습 실험에서는 feedback으로 형성된 prior와 그 provenance를 사용하며, 손으로 초기화한 동역학 시험을 학습 결과와 구분한다.

### 3.5 재확장과 재학습

오류 feedback이 공개된 시점 이후, 사용된 회로의 재활성 prior를 낮추고 원래 증명·연결 구조를 workspace로 다시 펼친다. 기존 graph를 표시만 하는 데 그치지 않고, 다른 후보/의존관계 또는 허용된 추가 관측을 실제로 시도한다. 충분한 정보가 있으면 새 판단을 만들고, 정보가 부족하면 판단보류로 끝낸다.

이후 검증된 대체 경로를 학습하고, 다시 같은 종류의 입력이 왔을 때 행동이 달라졌는지 확인한다. 한 episode에서 답이 바뀌었다는 사실만으로 지속적인 회로 학습이라고 하지 않는다.

## 4. 핵심 아키텍처

```text
Public Observation
        │
        ▼
Runtime / Workspace  ←→  Circuit Recall + Binding
        │                         │
        └─────────────┬───────────┘
                      ▼
              Shared Dynamics Kernel
             lower A ↔ higher A
                      │
                      ▼
             Convergence Observation
               │                 │
       tentative decision    mismatch/ambiguity
               │                 │
               │                 ▼
               │          Graph Expansion
               │                 │
               └───────◀─────────┘
                      │
              decision event fixed
                      │
         permitted external feedback only
                      │
                      ▼
       Validation → Learning / Compilation
                      │
                      ▼
             Versioned Circuit Memory
                      │
                  next attempt
```

runtime는 전역 정답 계산기가 아니다. 예산 관리, 상태 전이, 기록과 호출을 조정한다. ‘올바른 후보를 선택’하거나 ‘오답 부모를 정답으로 교체’하는 권한은 없다.

### 4.1 빠른 실행과 느린 변경

- 한 tick 안에서는 topology와 memory version을 고정한다. 같은 snapshot을 읽어 모든 상태를 동기 갱신한다.
- 임시 graph 확장은 tick 사이의 명시적인 경계에서만 반영한다.
- 지속되는 weight/회로 변경은 허용된 feedback 뒤 안전 경계에서 새 memory version으로 반영한다.
- 새 연결은 episode 임시 연결인지 장기 회로 연결인지 명시한다.

‘Configuration은 느리게, Execution은 Local하게’의 기능적 경계를 먼저 만든다. CPU scheduler가 있다는 이유로 완전 분산 물리 회로를 구현했다고 표현하지 않는다.

## 5. 소스 구조

```text
hcr-engine/
├── pyproject.toml
├── README.md
├── configs/
│   └── mvp.toml
├── docs/
│   ├── hypothesis_contract.md
│   ├── architecture.md
│   └── acceptance.md
├── src/hcr/
│   ├── __init__.py
│   ├── model.py
│   ├── binding.py
│   ├── dynamics.py
│   ├── workspace.py
│   ├── circuits.py
│   ├── compiler.py
│   ├── learning.py
│   ├── runtime.py
│   ├── trace.py
│   ├── cli.py
│   ├── tasks/
│   │   └── toy_world.py
│   └── evaluation/
│       ├── reference.py
│       └── protocol.py
├── tests/
│   ├── test_model_binding.py
│   ├── test_dynamics.py
│   ├── test_graph_circuit_cycle.py
│   ├── test_adaptation.py
│   ├── test_no_oracle_leakage.py
│   └── test_trace_replay.py
└── runs/                  # Git 추적 제외
```

파일명에 버전 번호를 붙이지 않는다. 버전은 배포·config·manifest·schema에서 관리한다. `frozen091/...`를 새 엔진의 런타임 import 경로로 넣지 않는다.

### 5.1 모듈별 책임

| 모듈 | 책임 | 금지할 책임 |
|---|---|---|
| model.py | NodeId, semantic key, role, candidate, typed edge, derivation, observation, feedback 계약 | 정답 판정·학습 정책 |
| binding.py | 현재 입력의 대상/관계를 회로 역할에 결합, 버전/범위/유일성 검사 | 평가 label로 역할 채우기 |
| dynamics.py | 공통 tick과 안정성·margin·진동 관측 | feedback 정답 읽기·장기 memory 갱신 |
| workspace.py | 현재 후보·신호 연결·명시적 의존관계, 예산 내 동적 확장 | 답을 얻은 것처럼 과거 노드 수정 |
| circuits.py | 회로 템플릿·instance·조건부 recall·메모리 직렬화 | 입력 해시로 정답 조회 |
| compiler.py | 검증된 subgraph의 역할 변수화·희소 topology/실행 계획 생성·certificate | 직접 전제 누락·숨은 비용 제거 |
| learning.py | feedback 기반 활성 연결 강화/약화, 회로 등록·격리·은퇴 | 자기 확신을 외부 성공으로 사용 |
| runtime.py | 한 실행 loop, 정책 전이, 예산과 관측 요청 | 정답 solver·episode 종류별 답 분기 |
| trace.py | append-only event·snapshot·증명/설명 연결·비용 기록 | 과거 결과 수정 |
| tasks/toy_world.py | 공용 입력과 primitive adapter, 허용된 추가 관측 | inference 함수에 hidden truth 전달 |
| evaluation/reference.py | 숨은 환경 기준 외부 채점·독립 proof 검사 | runtime에 미공개 label/정답 경로 반환 |
| evaluation/protocol.py | train/frozen-eval/adapt 실행, snapshot·대조군 관리 | 실패에 맞춰 사후 설정 변경 |
| cli.py | 설정 읽기와 명령 진입점 | 계산 로직 복제 |

처음에는 각 모듈을 한 파일로 유지한다. 실제 필요가 생기기 전에는 interface 계층·Factory·plugin registry·복수 backend를 추가하지 않는다.

### 5.2 의존성 방향

```text
model → binding/dynamics/workspace/circuits
model + workspace/circuits → compiler/learning
위 구성요소 + trace → runtime
runtime + toy task + external reference → evaluation protocol / CLI
```

runtime·dynamics·workspace·binding·circuits·compiler는 evaluation/reference를 import하지 않는다. 학습에는 제한된 `Feedback`과 검증 근거가 전달될 뿐 숨은 정답 객체를 공유하지 않는다. 관측을 요청할 때 runtime는 `ObservationRequest`를 내보내고 외부 실행기가 공개 가능한 관측만 반환한다.

## 6. 세 표현과 데이터 계약

### 6.1 회로/후보 연결과 proof를 분리

1. 신호 연결: SUPPORT / INHIBITION / TOP_DOWN 등을 가진 recurrent graph. cycle 허용.
2. 실행 이력: tick·결정·feedback·확장·학습 event. append-only.
3. 정당화: primitive rule과 premise로 구성한 proof DAG. cycle 불허.

상위 hypothesis가 하위 feature 후보를 강화했다는 이유로 상위 hypothesis를 자기 자신의 논리 전제로 쓰지 않는다. 신호 인과와 논리적 정당화는 다른 자료구조다.

잡음 관측에서 채택한 특징은 `assumed_feature`로 기록한다. 확인된 세계 사실로 조용히 바꾸지 않는다. 내부 proof가 가정 아래 유효하면서 현실에서는 틀릴 수 있어야 오수렴을 올바르게 분리할 수 있다.

### 6.2 주요 record 제안

- `Observation`: 외부에 공개된 측정값, 대상 범위, 시각, 신뢰/잡음 설정의 공개 부분. gold label 없음.
- `Candidate`: NodeId, semantic_key, A_level, role_bindings, activation, evidence_refs, state_version.
- `Derivation`: rule_id, premise refs, conclusion ref, assumption refs. 논리적 직접 전제만 기록.
- `CircuitTemplate`: 역할 변수, 적용 guard, 고정 topology와 연산, 학습된 활성 연결, 조건부 certificate, 유효 범위, version.
- `CircuitInstance`: template/version, 현재 역할 binding, 현재 episode 활성 상태. 이전 episode의 임시 상태 재사용 금지.
- `ConvergenceObservation`: stable, margin, residual, persistence, oscillation/budget 상태. 정답 여부 없음.
- `Decision`: 선택 후보, 내부 진단, memory version, trace 위치, feedback 이전 시점.
- `Feedback`: 출처·공개 시점·허용된 correct/incorrect 또는 추가 관측. 전체 정답 graph는 주지 않음.
- `MemoryPatch`: 변경 연결, 원인 feedback/trace, 이전/새 version, 검증 결과.

같은 semantic_key가 여러 NodeId에 나타날 수 있다. 동일 NodeId의 뜻을 다른 값으로 덮어쓰지 않는다. 관계/role 참조에는 생성된 시점과 version을 붙여 오래된 binding을 검출한다.

## 7. 단일 수렴 커널의 초기 명세

두 수준에 공통으로 사용하는 한 가지 bounded recurrence부터 시작한다.

```text
input_i = observed_drive_i + learned_prior_i
          + Σ(local_support_ji × activation_j)
          + Σ(cross_level_feedback_ki × activation_k)
          - Σ(inhibition_li × activation_l)

next_activation[group] =
    (1-damping) × current_activation[group]
    + damping × normalize(input[group])
```

`normalize`는 경쟁 집합별 softmax 같은 유한 범위 연산 하나로 정한다. 높은 A만 별도 solver를 호출하는 분기는 넣지 않는다. topology/표현 adapter는 달라도 커널과 기본 안정성 판정은 공유한다.

초기에는 수치 감쇠·온도·연결 범위를 config로 고정한다. 이 형태가 모든 설정에서 수렴한다는 보장은 전제하지 않는다. 임의 입력에 대해 보편적인 attractor 수렴을 증명한 것으로 표현하지 않는다.

### 7.1 수렴 상태와 정답 상태

내부 상태는 최소 다음처럼 구분한다.

- 안정되고 후보 차이가 충분함: `STABLE_DECISION` — 아직 정답이라는 의미 없음.
- 안정됐으나 후보 차이가 작음: `STABLE_AMBIGUOUS`.
- 주기적 변화 관측: `OSCILLATING`.
- 예산 끝까지 안정 조건 미충족: `BUDGET_EXHAUSTED`.
- 필요한 후보 자체 없음: `NO_CANDIDATE`.

외부 평가가 이후 별도로 `correct / incorrect / unresolved`를 부여한다. `wrong_stable`는 내부 안정과 외부 incorrect가 함께 관측된 결과다. 높은 margin은 calibration을 거치기 전에는 확률적 신뢰도라고 부르지 않는다.

## 8. Graph ↔ Circuit의 구체적인 최소 형태

### 8.1 Graph formation / expansion

공개 primitive 라이브러리에서 현재 부족한 관계에 적용 가능한 규칙 인스턴스를 유한하게 생성한다. 새 노드·관계가 실제로 추가됐는지 event로 기록한다. expansion은 선택된 후보를 확정하는 답 함수가 아니라 후보를 늘리는 연산이다.

이미 안정된 회로가 없거나, guard 실패·관계 불일치·작은 margin·예산 내 반복 불안정이 있으면 expansion을 허용한다. scenario 이름이 `novel`이라는 이유로 분기하지 않는다. 확장은 대안 관계를 추가할 수도 있으므로 실제 proof D가 반드시 증가한다고 가정하지 않는다.

### 8.2 Compilation

반복 검증된 부분 그래프에서 사용한 역할·primitive·직접 전제·상하위 routing을 추출한다. episode별 NodeId와 관측 문자열은 역할 변수로 바꾸고, 같은 구조에 현재 입력을 바인딩할 수 있도록 한다.

컴파일 산출물은 답이 아니라 실행 가능한 연결/연산 구조다. 새 입력에서도 실제 입력값과 관계를 읽고 계산해야 한다. 같은 관계 형태라도 전제 관측을 바꾸면 결과가 달라지는 양·음 대조를 포함해 상수 답 캐시를 배제한다. guard가 무효이면 결과를 반환하지 않고 graph 경로로 넘어간다.

guard는 현재 이용 가능한 관측과 바인딩만 검사하며 숨은 정답을 조회하지 않는다. 관측이 모호한 경우 회로는 잠정 후보를 만들 수 있으나, 그 가정과 불확실성을 지우지 않는다.

첫 버전에서는 정답을 보장하려고 필요한 직접 전제를 삭제하는 일반화, 신경 가중치 전체를 미분 학습하는 최적화, 전역 subgraph mining은 하지 않는다. 단순한 구조 패턴의 정규화/반복 카운터로 회로를 생성한다.

논리적 계약은 보존하지만 수렴 궤적이 동일하다고 가정하지 않는다. topology·prior가 바뀌면 dynamics와 비용도 바뀔 수 있으므로 실제 대조로 측정한다.

### 8.3 실제 비용 감소 기준

탐색 후보 생성, 관계 matching, 동적 노드 생성, 커널 갱신, 신호 전달, 회로 guard/binding, 검증과 설명 복원 비용을 각각 센다. 저장된 회로가 하나의 외부 호출로 보이더라도 내부 연산은 계속 계산한다.

처음에는 주로 탐색·관계 재구성 비용 감소를 목표로 한다. 계산량이 줄지 않았다면 그 부분의 가설 효과는 미확인으로 남긴다. 단지 코드가 짧아지거나 macro 호출 하나로 표시됐다는 이유로 압축 성과라고 하지 않는다.

### 8.4 Circuit → Graph

회로 certificate의 구조를 현재 workspace에 명시적으로 재인스턴스화하고, 아직 없던 규칙 후보나 observation을 추가한다. 새로운 의존관계를 사용했다는 trace가 있어야 expansion이다. 저장된 설명을 표시하는 것만으로 계산 확장이라고 하지 않는다.

## 9. 최소 학습과 가소성

### 9.1 시작 상태

내장되는 것은 primitive, 후보 구성 문법, common kernel, 작은 초기 prior다. 정답 회로와 성공 경로를 사전 설치하지 않는다. 표현 encoder·규칙은 수작업이고 회로 topology/재사용 정도는 경험에 따라 바뀐다는 경계를 기록한다.

### 9.2 성공 후

검증된 선택 경로에 대해서만 반복 사용 통계를 누적한다. 구조적으로 같은 패턴이 서로 다른 인스턴스에서 일정 횟수 검증되면 compiler에 넘긴다. 임계값은 설정값으로 동결하며 시작안으로 3개 독립 episode를 둘 수 있다. 같은 episode를 반복 검산한 것을 3개 학습 경험으로 세지 않는다.

새 회로를 등록하고 cue→회로의 재활성 연결을 강화한다. 즉 학습은 단순히 로그에 점수를 쌓는 것이 아니라, 다음 infer에서 읽는 연결/가중치 또는 routing을 실제 변경한다.

### 9.3 실패 후

실패에 참여한 회로의 recall prior를 보수적으로 낮추고, 해당 적용을 보류하거나 graph expansion을 우선한다. 피드백 하나를 받았다는 이유로 유효한 primitive 규칙이나 모든 과거 증명을 삭제하지 않는다. 관측 가정의 오류와 구조적 binding/계약 오류를 가능한 범위에서 구분한다.

첫 버전의 credit assignment는 근거가 남은 활성 경로를 대상으로 한 명시적 정책이다. 정교한 자율 학습 알고리즘이라고 부르지 않는다. 장기간 사용되지 않거나 계속 거부된 회로는 활성 메모리에서 은퇴시킬 수 있지만 원본 trace와 template version은 보존한다.

### 9.4 시간 경계

지속되는 학습 변화는 feedback 뒤 event 경계에서만 적용한다. 적용 중인 회로 객체를 다른 함수가 몰래 바꾸지 않는다. 중간에 memory version이 달라지면 새 attempt로 시작하며 기존 판단은 그대로 남긴다.

## 10. 실행 상태 전이

```text
OBSERVE
  → RECALL_AND_BIND
  → SETTLE
      ├─ mismatch / ambiguity / missing candidates
      │    → EXPAND_GRAPH → SETTLE
      ├─ budget exhausted / no supported conclusion
      │    → ABSTAIN → RECORD
      └─ stable candidate
           → EMIT_DECISION (정답 여부 미상)
           → RECORD
           → permitted FEEDBACK
                ├─ success → LEARN / COMPILE → COMMIT_MEMORY
                └─ error   → WEAKEN / REOPEN
                             → optional new observation
                             → EXPAND_GRAPH → SETTLE
```

최초 판단과 수정 판단을 같은 record에 덮어쓰지 않는다. `AttemptId`, `DecisionId`, `FeedbackId`, `MemoryVersion`으로 연결한다. 학습 feedback이 없는 평가에서는 decision 뒤 채점만 외부에서 수행하고 학습·재확장으로 돌아가지 않는다.

추가 관측·다른 후보가 없어도 무조건 정답으로 바뀌는 설계를 요구하지 않는다. 정보가 충분하지 않으면 보류가 맞다. feedback은 정답 경로를 직접 제공하지 않고 공개 범위와 사용 시점을 trace에 남긴다.

## 11. 엔진과 환경·평가의 분리

### 세 실행 모드

| 모드 | 최초 판단 전 gold 접근 | 판단 후 feedback | 장기 memory 변경 |
|---|---|---|---|
| TRAIN | 금지 | 허용 | 허용 |
| FROZEN_EVAL | 금지 | 엔진에 주지 않음; 평가기만 채점 | 금지 |
| ADAPT | 금지 | 사전 허용 범위만 공개 | 공개 이후 허용 |

모드 차이는 학습/feedback 권한이다. runtime가 샘플의 정답, 익숙함/예외 라벨, 시나리오 분류를 보고 답을 고르게 하지 않는다.

후속 시나리오의 초기 memory는 학습 종료 snapshot으로 고정한다. 여러 ADAPT 평가를 순차적으로 학습시키면 뒤 episode가 앞 평가에서 학습했다는 사실을 별도로 표시한다. frozen holdout처럼 합산하지 않는다.

### 독립 평가

reference는 환경의 실제 상태와 공개 primitive를 기준으로 내부 proof의 구조적 유효성, 관측/가정의 근거, 결과 정확성을 구분한다. runtime가 반환한 `is_correct`를 신뢰해 점수를 주지 않는다. 평가 함수에 접근하면 즉시 실패하는 sentinel을 둔 시험으로 inference 중 gold 호출이 없는지 확인한다.

## 12. 측정할 것과 측정하지 않을 것

필수 측정:

- 최초 판단 정확도, feedback 뒤 최종 정확도, 판단보류율.
- 수렴 residual, 후보 margin, 안정 지속 길이, 비수렴/진동/오수렴 수.
- primitive proof의 D, 사용한 가정, 실제 실행 trace와 설명의 연결.
- 활성 노드/간선, 커널 tick, edge 전달, 후보 생성, graph 확장, circuit recall/hit, binding/guard 검사.
- 학습·컴파일·검증·설명 비용, wall-clock 시간과 memory 크기.
- error→새 판단까지의 비용, 이전 회로 약화·대체·재학습, 익숙한 정상 입력 성능 유지.

성능 주장은 비교를 통과한 항목만 한다. proof D가 같아도 검색·재구성 비용이 줄 수 있다. macro 호출 수만 줄고 내부 연산이 같다면 비용 개선으로 보고하지 않는다. 가설의 ‘effective D’에 임의 수치를 붙이기보다 이번 엔진에서 직접 관측한 지표 이름을 사용한다.

train+compile 비용을 빼고 숙련 실행만 비교한 결과와 전체 누적 비용은 나눠 보고한다. 외부 검증이나 설명 생성 비용을 circuit 방식에서만 누락하지 않는다. 경로/표시 반복을 독립 구조 수로 세지 않는다.

## 13. 최소 인수 시나리오와 대조군

### 인수 시나리오

| 시나리오 | 확인할 실행 사실 |
|---|---|
| COLD | 빈 회로 메모리에서 후보/관계가 실제 추가되고 동일 kernel로 판단 |
| FAMILIAR | 반복 검증에서 생성된 circuit이 존재하고 다음 실행에서 호출됨 |
| TRANSFER | 학습 때 없던 이름/instance에서 역할 binding으로 같은 관계 구조 재사용 |
| AMBIGUOUS | 안정돼도 후보 차이가 부족하면 보류; 자동 정답 처리 금지 |
| NOVELTY | guard 실패·불일치에서 실제 후보/간선/경로가 추가됨 |
| MISCONVERGENCE | 내부는 안정되지만 외부에서 틀린 사례를 보존 |
| CORRECTION | 허용된 feedback 뒤 회로 prior 약화·graph 재확장·새 판단 발생 |
| RELEARNING | memory 저장/재시작 후에도 바뀐 회로 선택과 결과가 유지 |

시나리오 이름은 실험기 metadata이며 엔진의 정답 분기에 전달하지 않는다. 명시적인 동역학 failure injection 시험과 학습에서 자연스럽게 관측된 실패는 다른 결과로 기록한다.

### 최소 비교

| 조건 | 목적 |
|---|---|
| 동적 graph만, 회로 컴파일/호출 비활성 | 저장 회로의 추가 효과 기준선 |
| 전체 엔진, training snapshot 고정 평가 | 재사용에 의한 정확도/비용 변화 |
| 전체 엔진, top-down 연결 비활성 | 양방향 상호작용의 기여 확인 |
| 전체 엔진, 오류 뒤 재확장 비활성 | revisability의 기여 확인 |

모든 비교는 같은 원시 입력·초기 memory 출처·예산 정의·정확도 채점으로 한다. 비활성화가 무엇을 바꾸는지 manifest에 기록하고 나머지 정책은 유지한다. 더 많은 연산을 허용해 성공한 결과는 동일 비용 개선으로 쓰지 않는다.

### 구현 완료와 연구 효과 분리

공학적 완료는 자료구조/경계/trace/학습 저장/전이/검산이 동작하는지다. 연구 효과는 같은 정확도에서 전체 실행 비용이 감소하는지, 새로운 입력에 구조를 재사용하는지, feedback 뒤 적절히 수정되는지다.

효과가 나타나지 않아도 계측과 상태 전이가 올바르면 구현 실패와 구분할 수 있다. 반대로 답을 맞혀도 hard-coded 분기나 정답 누수가 있으면 구현 목표를 만족하지 않는다.

## 14. 개발 순서와 각 단계의 종료 기준

### P0 — 계약과 작은 환경

`hypothesis_contract.md`, `model.py`, `toy_world.py`, `reference.py`를 먼저 만든다. 공개 정보/숨은 정보, 두 A 수준, primitive, 목표, 학습·평가 모드를 정의한다. 정답 경로를 입력에 포함하지 않음을 시험한다.

종료: 사람이 확인 가능한 작은 사례와 반례에서 reference가 올바르게 동작하고 runtime에 gold가 전달되지 않는 인터페이스가 정해짐.

### P1 — 두 수준 공통 수렴

`binding.py`, `dynamics.py`, 기본 `runtime.py`, `trace.py`를 만든다. 하위 후보와 상위 후보가 실제로 상·하향 메시지를 교환한다. 모호한 안정·오수렴·비수렴은 별도 상태로 보존한다.

종료: 같은 kernel 호출이 두 수준에서 확인되고, 상위 피드백을 끄는 대조가 lower trajectory에 영향을 주는 fixture가 존재함. 생물학적 실증 결과로 해석하지 않음.

### P2 — 그래프 형성과 재확장

`workspace.py`에 제한된 후보 확장 연산을 넣는다. 낮은 margin/guard 실패 등 실제 상태에서 정책이 전환하며, 추가된 노드·간선·의존관계가 trace에 남는다.

종료: circuit이 없는 cold 입력을 처리하고, 정보 부족 시 보류하며, expansion이 단순 retry·설명 출력과 구분됨.

### P3 — 학습과 회로 재사용

`compiler.py`, `circuits.py`, `learning.py`를 연결한다. 성공한 구조의 변수화·등록·cue 연결 강화·현재 입력 binding·저장/재시작을 구현한다. warm/cold, 정확도/비용을 함께 측정한다.

종료: 프로그램을 재시작해도 학습 회로가 남고 새로운 instance에서 실제 실행됨. exact-input 캐시가 아님을 대조로 확인함. 구조 재사용이 비용을 줄이는지는 측정 결과로 남김.

### P4 — 오수렴 이후 약화·재학습

external feedback 이벤트, conservative weakening, circuit reopening, 새 graph 후보, 새 version commit을 구현한다. 실패 원문을 보존하고 최초/수정 성과를 구분한다.

종료: 새 정보가 있는 경우에 수정 시도가 실제 graph 변경을 거쳐 수행되고, 정보가 부족하면 정답 강제 대신 보류함. 재학습이 후속 episode에 남음.

### P5 — 최소 통합 gate

독립 reference·memory snapshot·모드 대조·전체 비용 계측을 연결해 단일 CLI 실험을 실행한다. P1~P4를 서로 다른 샘플 코드로 보여주는 것이 아니라 하나의 엔진에서 이어서 수행한다.

종료: 입력→수렴→확장→검증→회로화→재사용→오류→재확장의 동일 실행계 증거와 보고서를 출력함.

R0.1은 P5까지 포함한다. 수렴만 되는 P1, 회로를 저장만 하는 P3 일부는 통합 가설의 최소 구현 완료로 표시하지 않는다. 단계마다 필요한 테스트만 추가하며 과거 전체 evidence를 매번 다시 검산하지 않는다.

## 15. 테스트·기록·배포 운영

### 꼭 필요한 불변식

- NodeId는 episode/identity 범위에서 유일하고 semantic_key와 독립적이다.
- 직접 premise는 증명에서 생략되지 않는다. signal feedback은 논리 premise로 자동 전환되지 않는다.
- 커널은 입력 snapshot을 제자리 수정하지 않는다. 생성 순서가 예기치 않은 in-place 효과를 만들지 않는다.
- feedback 없는 frozen evaluation에서 memory checksum이 바뀌지 않는다.
- `learned` circuit에는 source derivation과 허용 feedback의 provenance가 존재한다.
- 검증되지 않은 회로가 stable했다는 이유만으로 강화되지 않는다.
- trace는 과거 decision과 failure를 덮어쓰지 않는다.
- compiler certificate는 현재 binding에 맞춰 펼쳐지며 미실행 primitive를 ‘실제로 실행했다’고 기록하지 않는다.
- 잘못된 guard/binding/오래된 version이면 조용한 정답 보정 대신 명시적으로 reject 또는 expand한다.
- 모든 비용 대조는 내부 macro 연산·검증·확장·재시도를 포함한다.

### 기록 제안

각 run에 `manifest.json`, `events.jsonl`, `memory_before.json`, `memory_after.json`, `summary.json`을 둔다. 코드는 commit 또는 release hash로 식별하고 config·task split·memory version·random seed를 고정한다. 예측 오차와 소프트웨어 예외는 분리한다.

초기 회로 메모리는 작으므로 JSON을 사용하고, 쓰기는 임시 파일 후 교체 방식으로 끝난 snapshot만 commit한다. 중단된 실행을 최종 완료로 표시하지 않는다. 단일 프로세스에서 명시적으로만 이어서 실행하며 예외 뒤 몰래 새로운 run으로 재시작하지 않는다.

기존의 매 run마다 과거 source/evidence를 재귀로 포함하는 구조는 새 엔진에 가져오지 않는다. 코드 snapshot은 release 단위로 한 번 보존하고 run은 그 hash를 참조한다. 외부 배포 시 필요한 release와 run을 함께 전달하면 된다.

### 기술 선택

기준 언어는 사용자 환경에 맞춘 Python 3.12로 제안한다. 커널 수치 연산은 NumPy 하나를 중심으로 두고, JSON·CLI·설정·파일 처리는 표준 라이브러리를 사용한다. 테스트는 pytest 또는 표준 unittest 중 하나로 통일한다. 구체 패키지 버전은 실제 첫 구현을 검증한 뒤 lock한다. 이 계획은 최신 라이브러리 권장 버전을 조사한 문서가 아니다.

CPU reference를 먼저 만들고 GPU/하드웨어는 별도 성능 단계로 미룬다. 계산과 상태 저장을 분리하는 계약은 유지하되 R0.1에서 존재하지 않는 여러 backend를 위한 추상 계층은 만들지 않는다.

## 16. 기존 연구 자산의 처리

기존 저장소·실행기·proof 검증·evidence는 원형 보존한다. 새 엔진의 학습 메모리나 코드 import 트리에 끼워 넣지 않는다.

재사용할 것은 무보정·미관측 분리·단계별 성공·독립 검산 원칙, 알려진 binding 반례, 작은 primitive 규칙과 DAG 검사의 기준이다. R0.1의 graph와 기존 형식은 의미가 다를 수 있으므로 과거 verifier를 그대로 가져다 통과시킨다고 동등한 검증이라고 하지 않는다.

후속 adapter에서 새 엔진의 primitive 정당화 그래프를 기존 포맷으로 내보내 교차 검사할 수 있다. LLM 비교·기존 대규모 배치·물리 구현은 R0.1 통합 순환이 완성된 이후 과제다.

## 17. 설계 고정 원칙

구현 전 문서의 개념을 좁힌 이 계약을 먼저 고정한다. 이후 변경은 ‘구현 버그 수정’과 ‘커널/학습/feedback/평가 조건 변경’을 구분해 기록한다. 어떤 파라미터·어떤 primitive를 손으로 제공했는지와 어떤 연결이 경험에서 학습됐는지를 명시한다.

최소판을 통과시키기 위해 결과를 미리 정해두거나, 복잡한 표상 기능을 생략하고 저장소·클래스 이름만 가설 용어로 꾸미지 않는다. 같은 실행계에서 핵심 순환이 실제 상태 변화로 일어나야 한다.

## 18. 근거 위치

본 계획이 보존한 원문 중심축은 다음과 같다.

- §3·5·23: A/D 구분과 Binding의 기반 역할.
- §7·28~30·40: 공통 primitive와 두 방향 계층 피드백.
- §14~16·21: 반복 성공 graph의 회로화와 양방향 graph↔circuit.
- §8·20·31·33: 안정성/정답 분리, revisability, 외부 검증과 오류 분류.
- §36~42: 익숙함에 따른 비용 변화, novelty-triggered expansion, 오수렴, 실행/설명 분리.
- §44~45: 느린 configuration과 빠른 local execution의 시간 경계.

범위 상한·도메인·모듈명·정규화 함수·학습 임계값·개발 단계는 본 계획의 제안이다. 원문이 이미 이 알고리즘을 확정하거나 계획의 성능을 입증했다고 하지 않는다.

## 한 문장 결론

**범용 뇌형 시스템을 한 번에 만들지 않고, 두 표현 수준·한 도메인·한 수렴 커널에서 실제 학습으로 그래프가 회로가 되고 오류로 다시 그래프가 되는 최소 엔진을 새 프로젝트로 만든다.**
