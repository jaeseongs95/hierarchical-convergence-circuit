# ADR-001 — 첨부 연구 저장소와 HCR R0.1 실행 구조의 통합 결정

결정일: 2026-09-16. 상태: R0.1 코드에 반영. 이 문서는 두 자료를 비교해 내린 새 설계 결정이지 어느 원문에 이미 명시된 정답은 아니다.

## 1. 실제로 비교한 자료

1. 사용자 제공 `hierarchical-convergence-circuit(1).zip`: 44개 파일. 이론 원문, 주장 목록, 7개 실험의 draft 설계, architecture/자료구획, 저장소 초기화와 파일 존재 검사 스크립트가 있다. HCR 실행 엔진은 들어 있지 않다.
2. 앞서 작성한 `HCR_R01_최소구현_재설계계획.md`: 두 A 수준·공통 kernel·동적 graph·학습된 circuit·오류 뒤 재확장까지 하나의 실행계에 넣는 설계다. 파일별 역할을 제안하지만 이것만으로 연구 자료의 상위 구획을 대체하지는 않는다.

첨부 ZIP의 SHA-256: `3cc62b31b0a5887d37ce5612cd226bde9fd9875ded617b3d837012623f7a6ccf`.
원래 제안의 파일 hash는 `evidence/implementation/input_provenance.json`, 변경한 운영 문서의 원문은 `docs/reference/`, 이전 최소계획은 `architecture/HCR_R01_original_plan.ko.md`에 보존한다.

## 2. 결론

**저장소 상위 구조는 첨부안을 채택하고, 실행 엔진 내부는 R0.1 계획의 작은 단일 패키지를 채택한다.** 두 설계는 같은 수준의 대안이 아니다. 하나는 연구 자료와 주장의 관리 구조이고, 다른 하나는 실행 책임과 평가 경계다.

실험 폴더별로 엔진을 복제하지 않는다. 모든 실제 알고리즘은 `src/hcr`에 한 번만 구현한다. `experiments/`는 명세·입력 조건·실행 계획을, `evidence/`는 주장과 검증 기록의 위치를 담당한다. 원래 `simulations/`·`related-work/`·`papers/`는 계획 영역으로 남기되, R0.1 실행을 위해 빈 backend나 plugin 추상계층을 만들지는 않는다.

## 3. 선택표

| 쟁점 | 첨부 프로젝트 | 이전 최소계획 | 최종 선택과 이유 |
|---|---|---|---|
| 상위 자료 관리 | theory/formalism/evidence/experiments/architecture 등 분리 | 엔진·tests·작은 docs 중심 | 첨부의 상위 구획 채택. 이론과 실행 성과 혼동 방지 |
| 핵심 소스 배치 | 인터페이스 안정화 후 src, 그 전 실험별 구현 가능 | 처음부터 src/hcr 단일 엔진 | 지금부터 src/hcr에 두되 상태를 experimental로 명시. 구현 중복 방지 |
| 초깃값/환경 | 실험별 연구 질문은 있고 구현 알고리즘은 미정 | 작은 관계 세계·CPU·두 A 수준 | 한 toy world, 두 수준, 한 kernel로 제한 |
| 계층 검증 시점 | 넓은 cross-abstraction 검증은 로드맵 R3 | 두 수준 상·하향 recurrence가 R0.1 필수 | 두 수준 기능은 지금. 여러 도메인의 일반성 검증은 여전히 후속 |
| 회로 compiler/cache | 개념적 모듈과 적용 범위 검사가 제안됨 | 답 캐시 대신 역할화된 실행 구조 | 현재 입력을 다시 계산하는 Program+Binding 저장. 답만 반환하지 않음 |
| 학습/현실 feedback | 개념으로 분리 | TRAIN/FROZEN_EVAL/ADAPT 및 공개시점 구체화 | 이전 최소계획의 권한·시점 경계 채택 |
| 주장 관리 | HCC-C/H Claim ID와 상태 분리 | 기능·연구효과 구분 | claims.yaml 원형 보존. 구현 점검은 별도 IMP 레코드 |
| 실행 기록 | 문서·재현성 원칙 | append-only event, memory 전후, 코드 hash | 고정 source 참조와 JSONL hash chain, 원형 source 반복포함 없음 |
| 초기 의존성 | 언어/수치 backend 미정 | NumPy 제안 | 이 크기에서는 표준 라이브러리 math만 사용. 외부 설치 없이 CPU reference |
| 기존 v0xx LLM 실험 | 별도 저장소 | 런타임 import로 끌어오지 않음 | 둘 다 유지. 옛 evidence/LLM/Ollama를 요구하지 않음 |

## 4. 디렉터리가 아니라 실제 경계로 합친 부분

`runtime`는 숨은 정답, World, reference evaluator를 import하지 않는다. 낮은 A와 높은 A 모두 `dynamics.tick`을 사용한다. top_down 링크는 상태를 바꾸지만 논리적 premise가 되지 않는다. 학습된 template와 임시 workspace는 같은 Program 형식을 사용하고 같은 settle 함수로 실행한다.

평가기는 판단 event가 기록된 뒤에만 숨은 환경을 읽는다. FROZEN_EVAL은 feedback을 받아 학습할 수 없다. ADAPT는 외부 오류 신호 후 허용된 edge의 추가 측정만 요청한다. 정답이나 정답 경로를 infer에 전달하지 않는다. 오류 판단을 과거 기록에서 고치지 않는다.

## 5. 채택하지 않거나 축소한 것

- 모든 EXP-01~07을 한 번에 완성하지 않았다. 지금 실제 실행하는 것은 `EXP-00`의 개발 통합 시나리오다. 나머지는 첨부의 draft 상태를 보존한다.
- 실제 카메라·언어모델·GPU·뉴로모픽·분산 실행을 만들지 않았다.
- 일반 학습된 encoder, 새 A 수준 자동 발견, 임의 primitive 학습을 만들지 않았다. 표현과 AND/OR 연결 문법은 설계자가 제공한다.
- 일반 부분그래프 mining, 필요 premise를 제거하는 추론 압축, native code JIT는 아니다. 이미 형성한 작은 관계 topology/연산을 역할화해 재사용한다.
- 회로 재사용으로 primitive proof D가 줄었다고 쓰지 않는다. 동적 구성과 탐색을 줄이는 기능이며 나머지 계산은 실제 계측한다.
- 원본문서의 HCC-H 상태를 구현 시험 통과만으로 observed로 올리지 않는다.

## 6. 최소 순환의 구현상 의미

cold 입력에서 공개 topology의 후보 경로를 열거하고, 낮은 feature group과 높은 관계 group을 실제로 만든다. 동일한 역할 구조가 서로 다른 세 episode에서 외부 근거까지 검증되면 회로 Program을 저장한다. 새 이름의 입력에는 binding을 새로 수행하고 활성값을 초기화해 실행한다.

편향된 positive 경험에서 학습된 prior가 약한 반대 관측보다 우세하면, 내부적으로 안정되고 가정 아래 proof도 성립하지만 현실에서는 틀릴 수 있다. 오류 feedback 이후에는 recall strength를 낮추고 새 관측을 요청한다. 다음 attempt는 회로를 그대로 믿지 않고 graph를 다시 전개한다. 최초 판단은 남고 새로운 판단과 memory version이 추가된다.

이러한 동작은 이 제한된 프로그램에서 확인할 수 있는 구현 사실이다. 인간의 직관·착시·신경회로를 실제로 재현했다거나, 가설이 검증됐다는 뜻은 아니다.
