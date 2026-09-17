# 진행 갱신 — R0.2.1 (2026-09-17)

7절의 dependency 경계 상태 계약을 코드로 추가했다. 상세 구현·한계는 [R0.2.1 설계](../architecture/r021-session.ko.md),
실행 상태는 [검증 기록](R021_ACCEPTANCE.ko.md), 실험은 [EXP-10](../experiments/exp-10-session-continuity/design.md)을 따른다.
지속 latent dynamics·ReadoutGate·M 전문화·A 이동은 이 구현으로 완료된 것이 아니다.
아래는 원래 설계 내용이며 이미 관찰된 EXP-09 결과의 현재 해석은 [기준선](R02_EXP09_OBSERVED_BASELINE.ko.md)을 우선한다.

---

# HCR 통합 개발·연구 로드맵
## R0.2에서 공통 primitive·전문화·계층·회로 학습·물리 substrate까지

- 작성일: 2026-09-16 KST
- 대상 프로젝트: `jaeseongs95/hierarchical-convergence-circuit`
- 현재 기준선: R0.2 Adaptive Graph/Circuit Engine
- 문서 상태: **기존 로드맵 + 여섯 원문 + 소스 재대조 반영. 원격 HEAD는 미확인**
- 이번 개정: 개념 추적·오류/설명 관찰·substrate gate 보강. 엔진 후속 기능 구현은 아님. 기존 658행 로드맵 원본은 `docs/reference/R02_PLUS_ROADMAP_20260916.ko.md`에 보존한다.

---

## 0. 결론

**R0.2를 폐기하거나 별도 엔진으로 다시 만들지 않는다. 검증된 공통 커널·동적 의존 그래프·부분회로·binding·proof·trace를 보존하면서, 계산 상태의 시간적 지속성, 서로 다른 처리 방법, 회로 간 구조 학습, 새로운 후보 형성, 표현 수준의 적응을 단계적으로 추가한다.**

장기적으로 구현하려는 구조는 다음과 같다.

> 공개 입력과 현재 문맥이 내부 후보를 활성화하고, 서로 다른 계산 방법을 사용하는 회로들이 상호작용하며, 상태가 계승·분기·결합·비활성화를 거친다. 그 결과 형성된 후보 중 일부가 출력 조건을 통과하고, 외부 검증을 받은 구조는 다음 실행에 영향을 주는 회로와 연결로 남는다.

이 로드맵에서 `직관`, `발상`, `세대 전이`, `전문화 회로`는 첨부 문서의 가설을 계산 과정과 실험 조건으로 옮기는 연구 대상이다. 현재 기능과 앞으로 시험할 설명을 구분한다.

기준선 패키지 적용·16개 도구시험·capture 생성은 사용자 로그에서 완료됐다. 상세 원시 분석·EXP-09는 별도다. 가장 가까운 기능 구현 목표는 **R0.2.1 — 시간·상태 계약 도입**이다. 다음 큰 기능 목표는 **R0.3 — 전문화된 처리 방법과 통합, 즉 제한된 M adaptation**이다.

---

## 1. 이 로드맵의 근거와 범위

### 1.1 실제로 사용한 자료

| 구분 | 자료 | 이 문서에서의 용도 |
|---|---|---|
| 기존 연구·구현 인계 | `HCR_세션인계_2026-09-16(1).md` | A/D/M 정의, R0.1 상태, R0.2 목표, 연구 원칙 |
| 실제 소스 | R0.1 소스 ZIP + R0.2 업데이트 ZIP의 `payload/` | 현재 클래스·함수·데이터 계약과 확장 지점 확인 |
| 사용자 실행 결과 | `붙여넣은 텍스트 (1)(20260916-130428).txt` | 적용·136개 테스트·demo·독립 audit의 실제 출력 |
| 새 관점 1 | `갑자기_떠오르는_생각_수렴모델_관점_2026-09-16(1).md` | 지속적인 내부 활성, 직관과 새로운 결합, 출력 임계치 |
| 새 관점 2 | `세상의_변화_사건그래프_세대전이_관점_2026-09-16(1).md` | 계승·분기·수렴·소멸이라는 상태 전이 언어 |
| 새 관점 3 | `시냅스_연결_좌뇌우뇌_관점_대화기록_2026-09-16(1).md` | 유효 연결 경로, 처리 특성의 전문화, 회로 간 연결 |
| 앞선 대화 분석 | 세 문서의 R0.2 적용 가능성 분석 | 확장 방향의 초안. 코드 대조가 필요한 설명은 아래에서 보완 |

자료 식별자와 코드 위치는 부록에 정리한다. 본문의 `[S…]`는 제공 자료, `[C…]`는 실제 소스 위치를 가리킨다.

### 1.2 확인 범위

분석용 디렉터리에 R0.1 소스를 풀고 R0.2 `payload/`를 겹쳐 현재 배포본을 복원했다. 복원본의 `RELEASE_MANIFEST.json`에 등록된 **114개 파일 항목의 해시가 모두 일치**했다. 이는 분석 대상 소스의 구성 확인이며, 프로젝트 테스트를 새로 실행한 것은 아니다.

실행 성과는 사용자가 제공한 로그를 근거로 한다. `runs/r02_first`의 원시 `events.jsonl`, `episodes.jsonl`, `summary.json`, memory checkpoint 전체를 이번에 직접 받아 재검산한 것은 아니다. GitHub 최신 HEAD 역시 이번 문서 작성에서 새로 조회하지 않았다.

세 번째 첨부파일은 사용자 발상과 당시 AI의 해석·제안이 함께 들어 있는 대화 기록이다. 이 문서는 **사용자가 제안한 연결·전문화 관점**, **그 대화에서 제안된 설계**, **이번 로드맵의 추가 제안**을 구분한다. 기록에 포함된 외부 신경과학·물리학 설명은 여기서 별도로 검증하지 않았으며, 구현 완료의 근거로 사용하지 않는다.

---

## 2. 출발점: 현재 R0.2에서 확보한 것

### 2.1 사용자 실행으로 확인된 기준선

| 항목 | 확인된 결과 | 근거 |
|---|---|---|
| 업데이트 적용 | 기준 파일 38개 확인 후 `state=applied`, 원본 백업 생성 | [S2] 적용 출력 |
| 회귀·신규 테스트 | `136/136 passed`, failures/errors/skipped 모두 0 | [S2] 286–290행 |
| 실행 환경 | Windows 11, Python 3.12.10 | [S2] 290행 |
| R0.2 통합 실행 | `complete=true` | [S2] 291–292행 |
| 독립 audit | `verified=true`, `differences=[]`, `source_checked=true` | [S2] 293–294행 |
| audit 처리 규모 | 판단 36개, 이벤트 2,646개, scalar tick 2,006개, graph step 84개, binding scan 355개, memory update 25개, checkpoint 4개 | [S2] 294행 |

따라서 **R0.2는 소스 작성만 끝난 단계가 아니라, 사용자의 환경에서 테스트와 통합 실행·검산이 완료된 기준선**이다. 배포 당시 문서에 남은 “실행 전” 표기는 이후 실행 결과와 시점을 구분해 정리해야 한다.

### 2.2 현재 코드가 실제로 수행하는 일

| 기능 | 실제 구현 | 현재 경계 |
|---|---|---|
| 공개 입력 | `Observation(start, goal, edges)` | 목표가 이미 정해진 작은 symbolic 관계 그래프 |
| 공통 수렴 | `dynamics.tick`, `settle`, `settle_recorded` | 두 고정 A 수준, 동기 갱신, 안정/모호/진동/예산 소진 구분 |
| D 확장 | `AdaptiveWorkspace` + `DeterministicExpansionPolicy` | 이미 공개된 topology에서 dependency를 선택·전개 |
| 부분회로 학습 | `SubgraphCompiler`, `CircuitPattern`, `AdaptiveMemory` | 기본 길이 2·3의 연속 directed path, `open_edge` 관계 문법 |
| 회로 경쟁 | `CircuitActivationPool` | 저장된 path program을 현재 역할에 바인딩해 같은 커널에서 경쟁 |
| binding | `NodeIdentity`, `SemanticIdentity`, `RoleIdentity`, `RoleBinding` | 관측 digest·revision·역할 순서·현재 edge 관계 확인 |
| 오류 수정 | feedback → 회로 약화 → 추가 관측 요청 → 새 revision의 primitive 재계산 | 임의 topology 변경은 허용하지 않음 |
| 기억 지속 | memory 직렬화·복원, version·증거 이력 검사 | 장기 회로 memory의 보존. 활성화 상태의 장기 지속과는 다름 |
| 평가 | 외부 proof/reference + adaptive audit | 정답·정당화·실행 기록·비용을 분리해 검사 |

근거: [C1]–[C10].

현재 kernel 계약은 **A 수준 0·1, edge 최대 8개, 경로 최대 4개, primitive 경로 길이 최대 4, group 최대 32**라는 작은 범위를 강제한다. 이는 단순 기본값만이 아니라 검증 코드에 포함된 한도다. 규모 확대는 숫자만 늘리는 작업이 아니라 계약·검산·실험 예산을 함께 확장하는 변경으로 취급한다. [C1]

### 2.3 현재 결과에서 다음 단계로 넘겨야 할 질문

**회로 재사용과 총비용 절감은 별개다.** 로그에서는 familiarity의 cold/warm 모두 3개 사례가 정답이고, 회로를 사용한 판단 수가 0에서 3으로 바뀐다. 그러나 콘솔 출력에는 전체 비용표가 없으므로 전체 연산량·지연 감소 수치를 확정할 수 없다. 소스에서도 macro 이후 최종 판단용 primitive signal graph를 다시 구성한다. 압축 효과는 우선 dependency 탐색 비용에서 확인해야 한다. [S2, C3, C8]

**한 episode의 오류 수정과 다음 episode의 오류 방지는 별개다.** `misconvergence/full`은 최초 안정 오답에서 추가 관측과 재계산 뒤 정답으로 바뀌었다. `no_reexpansion`은 오답을 유지했다. 한편 `retention/reload`는 새 episode에서 다시 안정 오답으로 기록됐다. [S2]

이 retention 항목은 소스에서 학습 후 memory를 저장·복원한 다음 같은 약한 측정 profile의 새 입력을 주도록 구성되어 있다. 따라서 현재 말할 수 있는 것은 **memory 복원과 행동 재실행은 이루어졌고, 그 조건에서 오류의 재발까지 막지는 못했다**는 것이다. 이를 근거 없이 “의도된 오답이므로 문제없다”거나 “직렬화 버그다”라고 분류하지 않는다. 후속 실험에서 저장 전후 동등성과 수정 효과의 일반화를 따로 판정한다. [C8]

또한 training 3회·9회 조건은 모두 수정까지 2번의 attempt가 기록됐다. 이것만으로 학습 강도와 수정 비용의 trade-off가 확인됐다고 말하지 않는다. 실제 비용과 prior·사용 회로의 변화를 비교해야 한다. [S2]

---

## 3. 세 문서를 하나의 계산 구조로 연결하기

### 3.1 각 문서가 확장하는 대상

| 첨부 관점 | 보존할 핵심 | HCR에서의 구현 대상 | 주요 단계 |
|---|---|---|---|
| 갑자기 떠오르는 생각 | 내부 변화는 이어지고, 출력으로 보이는 순간은 뒤에 올 수 있음 | persistent working state, 지속 갱신, readout gate, 후보 재결합 | R0.5a·R0.5b |
| 사건 그래프의 세대 전이 | 이전 상태가 계승·분기·결합·소멸을 거쳐 다음 상태를 만듦 | transition 계약, lineage, 제한된 구조 변경 | R0.2.1·R0.4 |
| 연결과 전문화 회로 | 강한 유효 경로, 다른 처리 특성, 회로 간 연결 | method profile, 처리기 간 메시지, 연결 학습 | R0.3·R0.4 |
| 기존 A/D/M | 표현·의존 전개·방법을 구분 | 각 축의 단독 조작과 조합 실험 | R0.3·R0.6·R0.7 |
| 공통 감각·착시·직관 가설 | 같은 primitive, cross-A recurrence, stable wrong | EXP-03·05, 고정 A 비교와 표현 승격 | R0.5a·R0.6 및 선행 단독 실험 |
| 판단과 설명 | value 생성과 근거 재구성의 구별 | 기존 trace 관찰, 별도 이벤트·시간 | EXP-06 / R0.2.1부터 |
| Physical/I/F | 고정 자원과 가변 연결, local 실행 | B0 계약 / B1 backend / B2 소자 | 조건부 별도 gate |

근거: [S1, S3, S4, S5].

이 표는 문서가 이미 제시한 세부 API가 아니라, **첨부 가설과 현재 구현을 연결한 설계 제안**이다.

### 3.2 같은 단어로 서로 다른 연산을 부르지 않기

**동역학적 수렴과 구조적 결합을 분리한다.** 현재 `settle()`의 수렴은 activation 변화가 안정되는 현상이다. 사건 그래프에서 `A, B → C`는 여러 부모가 새 구조를 만드는 결합이다. 둘은 연결될 수 있지만 같은 연산이 아니다. 코드에서는 전자를 `SETTLE`, 후자를 `JOIN`으로 구분하는 것을 제안한다.

**억제·작업 종료·소멸·가지치기도 분리한다.** 낮은 activation, dead-end frontier의 종료, 세션 후보의 비활성화, 장기 memory 연결의 폐기는 수명과 의미가 다르다. 기존 `retire()`를 이름만 `EXTINCT`로 바꾸어 전체 소멸 연산을 구현했다고 계산하지 않는다.

**공개 세계의 변화와 내부 가설의 변화를 분리한다.** R0.2의 확장은 공개 topology를 더 탐색하는 것이다. 새로운 내부 연결을 제안한다고 해서 실제 세계에 그 관계가 존재하는 것으로 바꾸지는 않는다. 입력 사실을 바꾸는 것은 새 관측이고, 내부 후보 연결을 바꾸는 것은 가설·계산 구조의 전이다.

**전문화는 A축의 대체물이 아니다.** A는 표현 수준, D는 의존 구조·분해 깊이, M은 처리 방법이다. `Sequential`과 `Associative`는 우선 M을 조작하기 위한 처리 profile이며 A0/A1의 새 이름이 아니다. 어떤 M을 택하느냐에 따라 실제 전개 D가 달라지는 효과는 별도 계측한다.

### 3.3 코드 대조로 보완한 앞선 분석

| 앞선 설명의 축약 | 코드에서 확인한 점 | 로드맵에 반영할 기준 |
|---|---|---|
| `settle()`은 항상 0.5에서 시작한다 | 함수 자체는 이미 `initial`을 받는다. R0.2 기록 어댑터는 이를 전달하지 않는다 | 커널을 새로 만들기보다 상태 전달·생명주기·검산 계약을 먼저 추가 |
| 같은 kernel을 쓰므로 계산 방법도 모두 같다 | 현재 차이는 제한된 path 후보에 머물지만, 공통 수치 커널을 써도 스케줄·탐색 정책은 달라질 수 있다 | 커널 공유는 유지하고 M의 실제 조작 변수를 명시 |
| 세대 전이의 네 연산을 바로 기존 동작에 대응시킬 수 있다 | 현재는 탐색 확장·dead-end 종료·신호 수렴이 중심이다 | 없는 구조적 JOIN·소멸을 억지 매핑하지 않고 별도 단계에서 구현 |
| 목표 없는 입력은 `Observation`만 바꾸면 된다 | `Program.validate()`도 `goal`과 경로를 요구하고, `settle()`·proof도 goal에 결합돼 있다 | goal-free 확장은 입력·program·readout·평가 계약을 함께 분리 |
| 후속 버전에서 구조·발상만 확장한다 | 기존 인계의 A adaptation 계획이 그 순서에서 빠질 수 있다 | A축을 R0.6의 명시적 독립 단계로 유지 |

근거: [C1, C2, C3, C4], [S1].

---

## 4. 최종 구조의 역할 분리

아래 구획은 **논리적 책임**이다. 모두 별도 데이터베이스나 별도 엔진으로 만들라는 뜻은 아니다.

| 구획 | 보유하는 것 | 다른 구획과 섞지 않을 것 |
|---|---|---|
| 공개 관측·과제 | 현재 허용된 입력 사실, 관계, 문맥 | hidden truth, 평가용 novelty label |
| 작업 상태 그래프 | 현재 가설·후보·활성 상태와 그 생명주기 | 검증된 장기 지식이라는 주장 |
| 의존 전개 workspace | 어떤 근거·경로를 실제로 조사했는지 | 아직 조사하지 않은 관계를 조사 완료로 표시 |
| 회로·연결 memory | 역할화된 재사용 계산, 적용 조건, 검증 이력 | 이전 정답 문자열, 무근거 후보의 자동 지식화 |
| signal program/state | 활성·경쟁·억제·재귀 신호 | proof의 논리적 부모 관계 |
| proof/검증 기록 | primitive 근거와 유효한 도출, 혹은 아직 미검증이라는 상태 | 자기 강화된 activation을 새로운 외부 증거로 취급 |
| event trace | 시간순 실제 실행과 상태 변경 | 사후 설명을 당시 실행으로 대체 |

제안하는 전체 순환은 다음과 같다.

```text
공개 입력 / 문맥
    ↓
표현 A + 현재 작업 상태 G[g]
    ↓
방법별 처리기 M_sequential / M_associative
    ↔ 타입·근거를 가진 회로 간 신호
    ↓
공통 activation / competition kernel
    ↓
다음 상태 G[g+1]
    ├─ 계승·분기·결합·비활성화
    ├─ 아직 출력되지 않은 상태 유지
    └─ ReadoutGate → 결과 또는 새 가설 후보
                         ↓
                   외부 평가 / 검증
                         ↓
             검증된 회로·연결만 장기 memory 갱신
```

출력은 자동으로 정답이나 학습 자료가 되지 않는다. 오류를 발견하면 최초 출력은 보존하고 새 계산·새 관측으로 수정한다.

---

## 5. 전체 단계와 버전 제안

일정은 날짜·주차가 아니라 **기능 계약과 실험 완료 gate**로 관리한다. 아래 버전명은 후속 개발을 위한 제안이며, 아직 구현된 버전이 아니다.

| 단계 | 목적 | 주로 바꾸는 것 | 그대로 고정하는 것 |
|---|---|---|---|
| R0.2 기준선 정리 | 현재 성과·미해결 질문을 고정 | 문서·증거 목록·후속 평가 설계 | 현재 엔진 동작 |
| R0.2.1 | 세대·상태·실행 단위 계약 | 시간 ID, snapshot, step/resume 기반 | R0.2의 판단·학습 의미 |
| R0.3 | 전문화 처리와 통합 | 제한된 M profile, 스케줄, 메시지 | 표현 문법, 공개 topology, 학습된 memory snapshot |
| R0.4 | 구조적 가소성 | 작은 fork/join motif, 회로 간 연결의 학습·약화 | A 수준, 검증 primitive, 선택한 M 설정 |
| R0.5a | 지속 활성과 지연 readout | 상태 유지·감쇠·갱신·출력 gate | 후보 문법·회로 topology·M 설정 |
| R0.5b | 제한된 새로운 발상 | 기존 구조의 새로운 조합, 비지정 출력 후보 | 유한한 관계 문법, 계산 예산, 평가 규칙 |
| R0.6 | A adaptation | 표현 변환, 추상화 수준 이동, 근거 복원 | 비교 과제의 의미와 정답 |
| R0.7 | A/D/M 조합·일반화 | 축 조합, held-out 구조, 확장된 과제 | 사전 고정된 평가·자원 예산 |
| 횡단 EXP-03/04/05/06 | 원 개념의 검증 누락 방지 | 오류·binding·계층·설명 비교 | 현재 과제의 의미·근거 기준 |
| B0 | 고정 자원 풀·I/F·시간축 계약 | 지역 상태·연결·권한·자원 정의 | 기존 reference 의미 |
| B1 | sparse/local/event-driven backend | 갱신 스케줄·통신·비용 | 사전 정한 수치/판단 허용 기준 |
| B2 | physical/neuromorphic prototype | 실제 장치·routing·가소성 | 명시한 과제·측정 경계 |
| 이후 조건부 입력 확장 | 외부 입력 | LLM adapter, 감각 encoder | 제공 정보와 HCR 자체 계산의 분리 |

### 버전 순서에 관한 결정

기존 인계의 큰 순서는 `D → M → A`였다. 앞선 대화의 확장안은 `M → 구조 학습 → 지속·발상`을 추가했지만 A의 후속 위치가 빠져 있었다.

이번 제안은 **M 이후 새 세 문서의 핵심을 먼저 작은 고정 표현에서 검증하고, A adaptation은 R0.6으로 명시적으로 이동**한다. A를 삭제하거나 구조 학습과 같은 것으로 간주하지 않는다. A 실험 명세는 앞서 준비할 수 있지만, 초기 비교에서 M·topology·A를 동시에 변경하지 않는다.

각 단계에는 두 종류의 완료 판정이 있다. **구현 gate**는 계약·회귀·검산 통과이고, **연구 gate**는 사전 질문에 대한 결과를 얻고 해석하는 것이다. 기대한 효율 개선이나 특정 현상이 관측되지 않아도 유효한 연구 결과다. 이를 얻기 위해 기대 결과를 강제로 만들지 않는다.

### 권장 순서와 실제 선행 조건

버전 순서는 연구 변수를 분리하기 위한 권장 순서이지, 모든 기능이 앞 버전 전체를 기술적으로 필요로 한다는 뜻은 아니다.

| 작업 | 실제로 필요한 선행 기반 |
|---|---|
| 전문화 M의 중간 상태 교환 | R0.2.1의 진행·상태 계약 |
| 고정 graph에서 지속 activation만 비교 | R0.2.1과 상태-aware 기록 어댑터. 구조 학습 완료는 필수가 아님 |
| 회로 간 연결의 학습 | typed port·binding·근거 전파와 작은 구조 문법 |
| 지속 상태에서 새로운 구조 조합 | 구조 합성 계약 + 지속 상태·readout 계약 |
| A 단독 실험 | 표현 대응·primitive 근거 복원. 새로운 발상 기능의 완료는 필수가 아님 |

따라서 지속성 또는 A의 독립 실험이 더 직접적인 질문이 되면 앞당길 수 있다. 그때도 같은 비교에서 여러 축을 동시에 바꾸지 않고, 실제 사용한 기반과 버전을 명시한다.

---

## 6. R0.2 기준선 정리 — 새 기능 전에 남길 기록

### 6.1 목적

현재 정상 실행된 기준선을 보존하고, 이후 기능을 추가하면서 과거 결과의 의미가 바뀌지 않도록 한다.

### 6.2 작업

`ROADMAP.md`와 현재 상태 문서에는 사용자 실행 완료 사실을 추가한다. 배포 당시의 정적 검사 기록은 당시 사실이므로 지우거나 “그때 실행했다”로 바꾸지 않는다. 별도의 실행 수용 기록으로 구분하는 편이 적절하다.

`runs/r02_first`는 덮어쓰지 않고 당시 source snapshot·config·plan·memory·trace·summary와 연결한다. 현재 소스로 과거 run의 source hash를 다시 맞추려 하지 않는다. 저장소에는 필요한 명세·요약·hash를 관리하고, 큰 원시 증거의 보관 방식은 코드 변경과 분리한다.

### 6.3 가장 먼저 추가할 분석

| 질문 | 비교 조건 | 판정 |
|---|---|---|
| 저장·복원이 행동을 보존하는가? | adaptation 후 memory의 직접 실행 vs 동일 memory를 save/load한 실행 | ID·시간값을 제외한 의미·결과·비용의 동등성 |
| 수정 효과가 새 episode에도 남는가? | adaptation 전 memory vs 후 memory, 같은 약한 측정 profile | 오답 재발·보류·회로 사용·prior·비용 변화 |
| 새 관측에 의존한 성공인가? | 약한 입력 vs 요청 후 강한 측정 vs 새 입력 | 추가 정보의 기여와 memory 변화의 기여를 분리 |
| 압축이 실제로 어디서 발생하는가? | 같은 입력의 cold/warm 쌍 | dependency·binding·signal·proof·초기화·학습 비용을 각각 비교 |
| 학습 강도가 수정 비용에 영향을 주는가? | training 3/9 및 사전 고정한 추가 조건 | attempt뿐 아니라 tick·관측 요청·약화·경로 재계산 비교 |

`retention/reload`의 재오답 원인은 이 비교를 하기 전 확정하지 않는다. 코드에 보이는 회로 약화와 실제 새 입력의 회로 선택·활성 상태를 trace로 연결해서 판단한다.

**완료 기준:** R0.2 실행 완료 사실, 연구적으로 확인한 효과, 아직 분석하지 않은 효과가 구별된 기준선 문서와 평가 명세가 남는다. 이미 통과한 적용·실행을 다시 미완료로 되돌리는 단계는 아니다.

---

## 7. R0.2.1 — 시간·상태 계약과 세대 전이의 기반

### 7.1 이번 단계의 핵심

**현재 계산을 중단·재개하고 시간순 상태 변화를 기록할 수 있는 기반을 만든다. 아직 새로운 회로 학습이나 자율적인 발상은 넣지 않는다.**

세대 전이는 인간 세대가 아니라 다음 계산 상태로의 전이라는 첨부 문서의 정의를 따른다. 다만 모든 시간을 하나의 숫자로 합치지 않는다. [S4]

| 시간·버전 | 의미 |
|---|---|
| kernel tick | 하나의 고정 signal program에서 수행한 동기 수치 갱신 |
| generation | 전이 적용이 완료된 작업 상태의 다음 snapshot |
| episode / attempt | 과제 또는 관측 시도, 오류 수정 시도 |
| observation revision | 새로 허용된 측정의 버전 |
| memory version | 검증된 학습 변경의 버전 |

### 7.2 제안 계약

`GenerationState`에는 최소한 session ID, generation ID, 이전 상태 digest, observation digest/revision, 사용 memory version, program digest, activation state, frontier·후보 참조가 필요하다. 전이에는 부모 상태·생성/변경/비활성 대상·원인 이벤트·실제 비용을 남긴다.

`TransitionEvent`의 상위 의미는 계승·분기·결합·소멸을 표현할 수 있게 하되, R0.2.1 어댑터는 **실제로 수행된 것만** 기록한다. 현재 없는 구조적 JOIN을 신호 수렴으로 대신 채우지 않는다. 모르는 전이를 범용 `CONVERGE` 하나로 뭉개지 않는다.

`step/resume`은 기존 한 번의 `infer()`가 끝까지 수행하던 작업을 일시 중단할 수 있게 만드는 실행 계약이다. 처음에는 dependency step 단위로 끊고, 수치 tick의 세션 간 지속은 R0.5a에서 확장한다.

### 7.3 소스 적용 지점

| 기존 위치 | 변경 방향 |
|---|---|
| `runtime.py:AdaptiveEngine.infer` | 전체 호출을 보존하면서 작은 진행 단위와 실행 상태를 추출 |
| `workspace.py:AdaptiveWorkspace` | frontier·완료 경로·사용 회로의 snapshot/복원 |
| `identity.py` | session/generation 참조 추가. 기존 Node/Semantic/Role 분리 유지 |
| `trace.py`, `codec.py` | 새 상태 packet과 전이의 직렬화·무결성 검사 |
| 신규 제안 `state.py`, `transitions.py` | 시간·상태·전이 계약만 담당 |

기존 `NodeRef.revision`에 generation을 덮어 넣지 않는다. 관측 revision과 내부 시간이 다른 역할이기 때문이다. [C10]

### 7.4 필수 테스트와 완료 기준

한 번에 끝낸 실행과 `step → 저장 → 복원 → resume`한 실행을 비교한다. 관측·판단·primitive proof·학습 결과·기존 의미의 비용은 같아야 한다. 추가 기록 때문에 생긴 이벤트 ID나 trace-count 기반 decision ID 차이는 비교용 정규화로 구분하되 **원본 trace는 고치지 않는다**. 새 snapshot 직렬화·복원 비용은 기존 알고리즘 비용과 별도 계측한다.

다른 observation/memory/program으로 잘못 resume하면 거부해야 한다. snapshot을 변조하거나 계보를 끊은 경우 audit가 탐지해야 한다. 완료된 옛 이벤트를 소급 수정해서 새 상태를 만드는 방식은 허용하지 않는다.

**범위 밖:** 일반적인 graph rewrite, background activation, 새 motif 문법, A/M 자동화. R0.2.1의 목표는 행동을 바꾸지 않는 실행 기반이다.

---

## 8. R0.3 — Specialized Method Circuits / 제한된 M adaptation

### 8.1 연구 질문

> 같은 표현·공개 입력·회로 memory에서 서로 다른 처리 정책을 운용하면, 경로 탐색·출력 시점·충돌 해결 양상이 어떻게 달라지는가?

사용자의 “역할이 다른 회로를 나누자”는 제안을 계산 방법의 전문화로 옮긴다. 생물학적 좌뇌·우뇌 이름을 붙이거나 각 처리기의 정확성·직관성을 미리 보장하지 않는다. [S5]

### 8.2 최소 구현

| 처리 profile | 실제 조작 변수 | 공통으로 사용하는 것 |
|---|---|---|
| Sequential | primitive 우선 전개, 제한된 활성 frontier, 중간 의존 상태 유지 | 입력 계약, 근거 규칙, 공통 수치 kernel |
| Associative | learned macro 우선 조회, 복수 후보 활성화, 짧은 경로 완성 우선 | 동일 memory snapshot, 동일 근거 규칙, 동일 kernel |
| Integration | 공통 후보의 결합·충돌 기록, 추가 계산의 배정 | typed message, evidence provenance, 총예산 |

여기서 profile 차이는 **M을 위한 제한된 조작 정의**다. 같은 primitive를 쓰더라도 실행 정책은 달라질 수 있다. 반대로 기존 `use_circuits` 스위치만 이름을 바꾸고 새로운 전문화가 구현됐다고 하지는 않는다.

처음에는 단일 CPU의 결정적 interleaving scheduler로 논리적 동시 처리를 구현한다. 운영체제 thread 병렬화는 별도 성능 변경으로 남긴다. 한 처리기의 중간 상태를 다른 처리기가 실제로 소비하도록 메시지 흐름을 기록해야 한다.

### 8.3 통합 계약

메시지에는 candidate ID, 표현 타입, 역할 binding, observation revision, 원래 evidence refs, 보류/지지/충돌 상태를 포함한다. 같은 근거가 A→B→A로 돌아왔다고 독립 지지 두 개로 세지 않는다.

두 처리기가 같은 답을 내도 그것만으로 correctness가 증가한 것으로 처리하지 않는다. 서로 다른 답을 내면 어느 경로의 근거가 부족한지와 어떤 추가 계산을 배정했는지 남긴다. 전체 미탐색 경로가 남은 부정 판단은 통합 계층에서도 확정하지 않는다.

고정 분할·적응 배분을 비교하되, 적응 스케줄은 공개된 mismatch·잔여 예산·진행 상태만 읽는다. 정답 label이나 실험군 이름은 읽지 않는다.

### 8.4 구현 위치와 실험

`expansion.py`의 정책 계약, `activation.py`의 후보 활성화, `runtime.py`의 진행 단위를 재사용한다. 신규 `methods.py`는 profile·scheduler, `integration.py`는 메시지와 통합만 담당하도록 제안한다. `CircuitActivationPool`의 기존 역할은 학습된 path 후보 경쟁으로 유지한다.

실험군은 Sequential 단독, Associative 단독, 고정 배분 결합, 적응 배분 결합이다. 이때 **결합 조건에만 두 배의 계산 예산을 주지 않는다.** 동일 총예산 비교를 주평가로 하고, 병렬 하드웨어·추가 예산의 효과는 별도 실험으로 분리한다.

**완료 기준:** trace에서 다른 처리 순서·메시지 교환·충돌 후 행동 변경이 실제로 확인되고, 근거 중복·부정 coverage·총예산 검사가 통과한다. 결합 방식이 더 느리거나 우세하지 않은 결과도 그대로 기록한다.

---

## 9. R0.4 — Structural Graph/Circuit Plasticity

### 9.1 연구 질문

> 반복 검증된 부분구조와 회로 간 연결을 학습하면, 새로운 조합에서 실제 계산 경로가 바뀌고 오류 뒤에는 그 연결을 수정할 수 있는가?

현재 R0.2는 회로를 새로 등록하므로 단순한 weight-only 시스템은 아니다. 다만 기본 motif가 길이 2·3의 단일 관계 path에 한정되고, 회로들 사이의 학습된 연결망은 없다. 이 제한을 작은 문법부터 확장한다. [C5, C6, C7]

### 9.2 구현 순서

먼저 기존 path와 구별되는 `ForkPattern` 및 `JoinPattern`의 뜻과 primitive 검증 규칙을 정의한다. 그다음 구조 certificate, binding, compiler, runtime, external validator, audit를 순서대로 연결한다. 마지막에 회로 간 연결을 학습 대상으로 올린다.

| 구조 | 필요한 계약 |
|---|---|
| Path | 기존 연속 관계의 연결과 역할화 |
| Fork | 하나의 부모에서 여러 후속 후보가 생기며, 선택하지 않은 가지의 생명주기가 명시됨 |
| Join | 여러 부모가 함께 필요한 결합인지, 대안 중 하나만 필요한 결합인지 명시 |
| Deactivate | 현재 작업 후보를 비활성화하되 이유와 계보는 보존 |
| Prune | 장기 연결을 제거/사용 중지하며 memory version과 증거 이력을 갱신 |

`A→C`, `B→C` 두 edge만으로 `A AND B가 있어야 C`라는 뜻을 보장할 수 없다. 최소 구현에서는 부모 집합과 `all_of / any_of` 같은 결합 조건을 명시한 transition 또는 relation node를 사용한다. 현재 경로 도달성 proof를 새 결합 문법의 verifier로 그대로 재사용하지 않는다.

### 9.3 회로 간 연결

`CircuitLink`에는 source/target circuit과 port, 역할 대응, 표현 타입, 적용 조건, strength, 검증 근거, version, 무효화 조건을 둔다. 호출 대상의 과거 답을 저장하지 않고 **현재 인스턴스의 중간 상태와 역할을 전달**한다.

학습 연산은 연결 제안, 검증 대기, 생성, 강화, 약화, 사용 중지로 나눈다. 공동 활성화만으로 곧바로 검증된 연결이 되지는 않는다. 오류가 난 출력에 관여한 연결과 단지 동시에 존재한 연결을 구별할 provenance를 남긴다.

초기에는 작은 허용 문법과 제한된 후보 수를 사용한다. 임의 subgraph mining이나 모든 회로 쌍의 무제한 연결은 넣지 않는다.

### 9.4 실험·완료 기준

고정 topology와 학습 가능한 topology를 같은 데이터·총예산에서 비교한다. 새 객체 이름에서의 재사용, 미학습 fork/join 조합, 한 부모가 빠진 join, 잘못된 결합 이후 약화, 가지치기 뒤 대안 경로 복구를 포함한다.

구조 변화는 `graph edit distance` 같은 단일 숫자만이 아니라 생성·삭제된 연결 ID와 실제 다음 실행의 선택 경로로 확인한다. 판단에 쓰이지 않은 새 edge의 개수를 성능으로 세지 않는다.

**완료 기준:** 제한된 구조 변경이 실제 입력 처리에 영향을 주고, primitive 정당화와 외부 검산이 가능하며, stale binding과 무근거 결합을 거부한다. 이전 branch를 몰래 지워 성공률을 높이지 않는다.

---

## 10. R0.5a — Persistent Dynamics와 ReadoutGate

### 10.1 연구 질문

> 명시적 출력이 없는 동안에도 내부 상태가 계속 변화하고, 그 상태의 누적으로 나중에 출력 조건을 넘는가?

이는 첫 번째 첨부 문서의 “내부 변화와 외부에 드러나는 순간을 분리한다”는 관점을 시험하는 단계다. 새로운 개념 조합은 다음 단계로 나누고, 여기서는 **동일한 후보 공간에서 지속성의 효과**부터 확인한다. [S3]

### 10.2 기존 커널을 활용하는 방법

`settle()`에는 `initial`이 이미 있다. 따라서 수치 갱신식을 새로 만들기보다 세션 상태를 연결하고, 필요한 구간만 `tick()`으로 진행하며, 출력 여부를 별도 계층에서 결정하는 방식이 적절하다. [C2]

기존 R0.2 호출은 계속 fresh-state 경로로 보존한다. 새 경로에서 activation을 가져올 때에는 program digest·역할·관측 revision을 검사한다. `e:0`처럼 위치에 기반한 키가 같다는 이유만으로 의미가 다른 이전 활성값을 복사하지 않는다.

**감쇠의 기준도 계약으로 둔다.** 현재 `tick()`의 상태값은 양/음 후보 경쟁을 나타내며 0.5가 중립이다. 이를 그대로 쓴다면 “망각”을 무조건 0으로 보내는 것은 음의 판단으로 편향시키는 변경이 될 수 있다. 중립 복귀는 예를 들어 `0.5 + ρ(a − 0.5)`로 제안할 수 있다. 새 activation 의미를 도입한다면 baseline을 명시적으로 다시 정의해야 한다. [C2]

### 10.3 장기 memory와 작업 상태의 분리

장기 `AdaptiveMemory`에는 검증된 회로가 남고, `SessionState`에는 미완료 계산과 activation이 남는다. session checkpoint에 목표·문맥·현재 program·memory version·미처리 메시지·출력 이력을 기록한다.

`FROZEN_EVAL`에서 시간에 따라 작업 activation이 변하는 것과 장기 memory를 학습으로 바꾸는 것을 구별한다. 추론 중의 내부 진행은 허용하되 검증 없는 장기 학습은 금지한다.

### 10.4 readout 규칙

회로를 macro로 선택하는 기존 `activation_threshold`와 결과를 외부에 내보내는 gate는 다르다. `ReadoutGate`에는 활성/대안과의 margin, 필요한 지속 기간, 중복 출력 억제, 근거 상태, 현재 문맥 적합성 등을 별도 계약으로 둔다.

최소 구현은 임계치·지속 기간·근거 상태를 포함한다. `generation == 5`처럼 특정 시점에 정답을 출력하도록 조건을 박아 넣지 않는다. 출력이 없는 generation도 그대로 기록한다. 최초 출력 시점과 최종 안정 시점을 별도로 측정한다.

### 10.5 실험과 완료 기준

동일 입력 순서에서 state reset, state carry, carry+decay, carry 상태를 유지하되 tick을 중단한 대조군을 비교한다. 문맥을 바꾸어 예전 후보가 잘못 재등장하는지, 무관한 입력에서 오출력이 생기는지도 검사한다.

소스가 실행되는 동안 명시적 `advance()` 호출로 idle generation을 진행한다. 초기 연구를 위해 실제 OS background process나 자동 실행 예약을 도입할 필요는 없다.

**완료 기준:** 출력 전의 연속적인 내부 변화와 gate 통과가 trace로 연결되고, 중단·복원 뒤에도 동일한 전이가 재현된다. 지연 출력이 없거나 잔류 활성의 부작용만 확인돼도 그 결과를 남긴다.

---

## 11. R0.5b — 제한된 새로운 발상과 비지정 출력 후보

### 11.1 연구 질문

> 저장된 답이나 전체 회로를 조회하는 대신, 기존 부분구조가 현재 문맥에서 새롭게 결합해 이전에 저장되지 않은 후보를 만드는가?

기존 R0.2에는 `start`, `goal`, 경로 기반 `Program`, goal readout, 도달성 proof가 서로 연결되어 있다. 따라서 `goal=None`만 허용해서 끝나는 변경이 아니다. [C1, C2, C3, C9]

### 11.2 최소 범위

범용 자연어 창의성 대신 **고정된 symbolic 관계 문법 안의 새로운 조합**을 다룬다. `OpenConvergenceObservation`과 `CandidateReadout`을 기존 goal-directed 입력·결정과 분리하고, 여러 typed 후보의 생성·유지·검증 상태를 지원한다.

목표 candidate ID나 기대하는 최종 X를 입력에 넣지 않는다. 다만 무제약 계산 대신 허용된 관계 타입·조합 연산·문맥과 총예산은 사전에 공개한다. 특정 관계가 결합 가능하다는 규칙을 설계자가 준 경우 그것은 제공된 문법으로 기록하며, 엔진이 그 규칙 자체를 발견했다고 세지 않는다.

후보의 상태는 적어도 `proposed → evaluated → accepted/rejected/unresolved`로 구분한다. 기존 사실에서 도출 가능한 합성인지, 외부 검사가 필요한 새 관계 가설인지도 분리한다. 제안된 edge를 입력 사실에 몰래 추가해 자기 proof를 만드는 것은 금지한다.

### 11.3 source 변경 지점

기존 `Program`을 무조건 느슨하게 만들지 않고 path task 계약과 일반 signal network 계약의 분리를 먼저 검토한다. `tick()`의 동기 갱신 primitive는 공유하되 `goal`을 직접 읽는 종료·출력 로직을 어댑터로 옮긴다.

신규 제안 `candidates.py`는 typed candidate·합성·근거 상태, `readout.py`는 출력 gate를 담당한다. `tasks/`와 `evaluation/`에는 새 문법의 독립 evaluator가 필요하다. 기존 reachability 평가기는 기존 task 전용으로 남긴다.

### 11.4 실험과 완료 기준

학습에서는 부분 motif만 제공하고, 전체 조합은 평가 시 처음 등장하게 한다. 단순 이름 바꾸기, 기존 전체 회로 조회, 부분구조의 미학습 조합, 문법 밖 관계 제안은 별도 범주로 집계한다.

대조군은 전체 조합 캐시, 부분 motif만 있고 재결합 금지, 재결합 허용, 지속 activation 없이 매회 재시작이다. 먼저 한 조작씩 비교하고, 지속성과 재결합의 결합 효과는 추가 조건으로 둔다.

**완료 기준:** 전체 출력이 미리 저장되거나 입력으로 주어지지 않았으며, 어떤 부분구조가 어떤 전이로 결합했는지 확인된다. 유효한 후보의 비율·무효 후보·보류·계산량을 함께 보고한다. 후보 개수 증가만으로 발상 품질을 판정하지 않는다.

---

## 12. R0.6 — A adaptation을 독립적으로 검증

### 12.0 공통 primitive 반복과 A adaptation은 다른 질문

원래 EXP-05는 low/mid/high 과제의 공통 계산 primitive를 묻는다. R0.2의 고정 두 수준·top-down 시험이 기반이지만 일반 계층 구축 완료는 아니다. A_n의 수렴 출력을 A_(n+1)의 후보 node로 승격할 때 evidence·uncertainty·revision·양방향 mapping을 유지한다. top-down 신호가 하위 후보를 바꾸고 그 mismatch가 다시 상위를 제약하게 하되, 재순환 근거를 중복 지지로 세지 않는다.

먼저 고정 두 수준과 symbolic low/mid/high adapter로 EXP-05를 수행할 수 있다. 그 뒤에 표현 수준을 선택/이동하는 아래 A adaptation을 독립 조작한다. 실제 시각·후각 encoder가 생길 때까지 공통 primitive 실험을 미루지 않는다.


### 12.1 연구 질문

> 같은 문제를 서로 다른 표현 수준으로 옮겨 계산할 때, 의미와 primitive 근거를 유지하면서 계산 비용·해결 가능성이 달라지는가?

R0.2의 두 A 수준은 이미 존재하지만 고정되어 있다. 이것은 표현 수준의 존재이지, 상황에 따른 A 선택·이동의 구현 완료가 아니다. [S1, C1]

### 12.2 최소 구현

`RepresentationAdapter`에 입력/출력 표현 타입, 역할 대응, 정보 손실 여부, 적용 조건, 원래 근거로의 복원 규칙을 둔다. 첫 비교에서는 명시적으로 대응을 검증할 수 있는 두 표현만 사용한다.

예를 들어 primitive 관계 표현과 역할화된 복합 관계 표현을 같은 과제에 적용할 수 있다. 단, 복합 표현으로 바꿨다는 이유만으로 primitive proof D를 줄여 기록하지 않는다. 표현 변환과 macro 실행은 관련되지만 별개의 조작으로 측정한다.

고정 A0, 고정 A1, 명시적 A 전환을 먼저 비교한다. 자동 선택은 이 둘의 의미 대응이 검증된 뒤에 추가한다. M 정책과 topology 학습은 평가 동안 고정한다.

### 12.3 근거·예산·완료 기준

최종 판단은 원래 primitive fact/rule까지 복원할 수 있어야 한다. 손실 표현을 허용하는 후속 실험에서는 어떤 정보가 빠졌고 언제 보류/추가 관측이 필요한지 명시한다. 상위 표현에 정답을 미리 넣어주는 지원 효과를 엔진의 이득으로 계산하지 않는다.

표현 변환 비용·추가 metadata·binding 비용·proof 복원 비용을 포함한다. 추상화 전환이 의미 오류를 줄였는지 또는 새 오류를 만들었는지도 비교한다.

**완료 기준:** 같은 의미 과제의 표현 대응이 검증되고, A 전환의 실제 경로·비용·오류가 다른 축의 변경과 분리돼 기록된다.

---

## 13. R0.7 — A/D/M 조합과 일반화

### 13.1 조합 순서

먼저 각 축의 단독 결과를 정리하고, `D+M`, `D+A`, `A+M`의 두 축 조합을 비교한다. 그다음 `A+D+M`을 시험한다. 세 축 전체가 유리하지 않더라도 유효한 두 축 조합을 별도 결과로 남긴다. [S1]

전체 조합 조건에서는 같은 입력과 같은 총예산을 사용하고 축별 off 대조를 둔다. 실패가 발생하면 최초 실패를 representation, binding, dependency coverage, method integration, readout, learning credit 중 어느 단계에서 확인했는지 분류한다. 뒤따른 오류는 최초 실패와 별도로 기록한다.

### 13.2 일반화의 수준

| 수준 | 질문 |
|---|---|
| 객체 재명명 | 같은 구조에서 새 identity·역할 binding을 유지하는가? |
| edge 순서 변경 | 저장·입력 순서가 결과를 임의로 바꾸지 않는가? |
| 새 조합 | 학습된 부분구조를 다른 조합에 쓸 수 있는가? |
| 새 topology | 학습에 없던 fork/join 배치에서도 동작하는가? |
| 문맥·측정 변화 | 같은 구조의 불확실한 관측에서 보류·수정이 작동하는가? |
| 표현 이동 | 의미를 보존한 다른 A 수준에서도 유효한가? |
| 새 task family | 기존 관계 과제 밖에서도 공통 primitive를 재사용하는가? |

held-out 구조와 평가 설정은 실행 전에 고정하고, 학습·개발 fixture와 구분한다. deterministic 실행의 반복은 재현성·시간 분산 자료이지 새로운 일반화 표본이 아니다.

**완료 기준:** 적어도 무엇이 일반화되고 무엇이 실패하는지, 추가된 계산과 지원 정보가 무엇인지가 구분된 결과가 남는다. 범용성이라는 한 문장으로 모든 수준을 합치지 않는다.

---

## 14. 단계별 실험 등록안

기존 `exp-00`과 `exp-08`은 구현 통합 실험, `exp-01~07`은 별도 연구 명세를 포함한다. R0.2 demo에 비슷한 이름의 조건이 있다고 해서 기존 연구 실험 전체가 완료됐다고 처리하지 않는다. 기존 폴더와 claim ID는 보존한다. [C11]

아래 ID는 신규 제안이다.

| ID | 실험 | 주요 대조 | 핵심 관측 |
|---|---|---|---|
| EXP-09 | R0.2 retention·압축 상세 평가 | pre/post adaptation, direct/reload, cold/warm | 오류 재발, memory 동등성, 비용 분해 |
| EXP-10 | 상태·세대 호환성 | 일괄 실행 vs step/resume | 판단·proof·학습의 의미 동등성 |
| EXP-11 | 전문화와 통합 | 각 M 단독 vs 고정/적응 결합 | 처리 순서, 메시지, 충돌, 총예산 |
| EXP-12 | 구조·연결 학습 | 고정 graph vs 학습 가능 graph | 새 연결의 실제 사용, fork/join 검증 |
| EXP-13 | 지속 활성·readout | reset/carry/decay/일시정지 | 최초 출력 tick, 잔류 활성, 오출력 |
| EXP-14 | 새로운 후보 재결합 | cache-only/재결합 off/on | 조합 신규성, 근거, 무효 후보 |
| EXP-15 | A adaptation | 고정 표현 vs 전환 | 의미 대응, 변환 비용, 근거 복원 |
| EXP-16 | A/D/M 조합·일반화 | 단일 축·두 축·세 축 | 상호작용, 새 구조, 최초 실패 |

각 명세는 다음 질문에 답해야 한다. 어떤 조작을 하는가, 무엇을 고정하는가, 엔진이 볼 수 있는 정보는 무엇인가, 총예산은 얼마인가, 정답/유효성은 누가 판단하는가, 어떤 결과이면 기대 효과가 없다고 판정하는가.

정확도·효율의 목표 수치는 현재 근거 없이 만들지 않는다. 개발 calibration과 평가를 분리한 뒤 설정을 고정한다. 외부 평가 결과가 예상과 달라도 테스트 fixture를 바꿔 그 결과를 없애지 않는다.

---

## 15. 비용·품질·신규성 계측 규칙

### 15.1 기존 비용을 버리지 않기

| 계층 | 기존 또는 추가할 관측 |
|---|---|
| dependency 탐색 | nodes/edges created, expansions, frontier retirements, topology edge checks |
| 회로 회상·binding | recall checks, binding operations, candidate circuits, pool calls |
| 수치 계산 | kernel ticks, group updates, signal transmissions, normalization operations |
| proof·외부 검증 | 복원한 primitive proof nodes, verification checks, coverage |
| 학습·저장 | compilation items, learning updates, memory write items, 직렬화 bytes |
| 전체 성능 | 초기화, infer, 학습, checkpoint I/O의 시간과 peak memory를 분리 |
| 시간 지속성 | idle/active ticks, generation 수, 상태 유지량, 최초 출력 시점 |
| 구조 학습 | 연결 생성·강화·약화·비활성화, 실제 사용 여부, provenance |

`signal_events=signal_transmissions`, `convergence_ticks=kernel_ticks`, `proof_reconstruction_cost=proof_nodes_reconstructed`, `storage_cost=storage_bytes`는 현재 별칭이다. 원래 값과 더하지 않는다. 서로 단위가 다른 카운터를 근거 없이 하나의 “총비용”으로 더하지 않는다. [C1, C11]

현재 저장 byte 계측은 학습 과정의 직렬화량 성격이 있다. 후속 단계에서는 누적 쓰기량과 특정 시점의 memory/session 크기, peak resident memory를 별도 지표로 둔다.

### 15.2 품질과 상태를 나누기

정답률 외에 보류율, 안정 오답, primitive proof 유효성, 가정의 실제 적합성, 최초 실패, 수정 후 성공, 다음 episode에서의 재발을 따로 보고한다. 최초 오답과 수정 성공을 하나의 최종 정답으로 합쳐 실패를 숨기지 않는다.

후보 생성 단계에서는 학습된 전체 구조와 동일한 출력, 새 객체에 대한 같은 구조, 기존 부분구조의 새 조합을 나눈다. “새 후보”라는 이름 자체는 신규성 증거가 아니다.

### 15.3 강한 연결과 빠른 출력의 검사

첨부 관점의 유효 경로 강도는 weight 하나로 고정하지 않는다. 회로 strength, 경로 전개량, gate 조건, 경쟁 구조를 독립적으로 조작하고 최초 출력 tick·오수렴·수정 비용을 함께 측정한다. 더 강한 prior가 항상 더 빠르고 더 정확하다는 전제를 두지 않는다. [S5]

---

## 16. 소스 구조의 확장 원칙

### 16.1 유지할 골격

연구 자산은 기존 `theory / formalism / evidence / architecture / experiments / papers` 구획에 두고 실제 구현은 `src/hcr`에만 둔다. 실험마다 엔진을 복제하거나 `frozen-r02 → frozen-r01` import 체인을 만들지 않는다. [S1, C11]

기존 `Engine`/`AdaptiveEngine`의 공개 경로는 호환성을 유지한다. 공통 primitive를 함께 쓰는 task/실행 어댑터를 추가하며, 새 이름의 거대한 엔진 복사본을 만들지 않는다.

### 16.2 단계별 파일 배치 제안

| 단계 | 기존 주요 변경 대상 | 필요할 때 추가할 모듈 |
|---|---|---|
| R0.2.1 | `runtime.py`, `workspace.py`, `identity.py`, `trace.py`, `codec.py` | `state.py`, `transitions.py` |
| R0.3 | `expansion.py`, `activation.py`, `runtime.py` | `methods.py`, `integration.py` |
| R0.4 | `patterns.py`, `compiler.py`, `circuits.py`, `learning.py`, `proof.py` | `connectivity.py`, 필요 시 `plasticity.py` |
| R0.5a | `dynamics.py`의 상태 전달 어댑터, `runtime.py`, `codec.py` | `readout.py` |
| R0.5b | 공개 입력·program 계약, `tasks/`, `evaluation/` | `candidates.py` |
| R0.6 | `model.py`, `identity.py`, `proof.py`, task adapter | `representations.py` |
| 전 단계 | `tests/`, `evaluation/`, `configs/`, `architecture/` | 해당 단계의 protocol·독립 audit·계약 테스트 |

이 표는 미리 빈 파일·추상 클래스 수십 개를 만드는 지시가 아니다. 각 단계에서 실제 호출되는 최소 책임만 추가한다. 상위 인터페이스를 일반화할 때는 최소 두 실제 사용 사례로 필요한 추상화를 확인한다.

### 16.3 호환성과 원자성

새 memory/session schema에는 버전과 migration 정책을 둔다. 기존 R0.1/R0.2 memory를 조용히 덮어쓰거나 자동으로 의미를 바꾸지 않는다. 지원하지 않는 조합은 오류로 거부하고, 변환이 필요하면 원본을 보존한 명시적 변환으로 수행한다.

전이·graph 변경은 먼저 전체 유효성을 검사한 뒤 원자적으로 반영한다. 예산 부족·binding 실패 후 절반만 바뀐 상태가 남지 않게 한다. 상태 비활성화·연결 제거 뒤에도 실행 당시 proof와 trace는 계속 해석 가능해야 한다.

기존 회로·신호에는 재귀를 허용할 수 있지만 proof의 논리적 근거 cycle은 허용하지 않는다. 세대 계보의 DAG는 시간순 전이를 설명하며, 그 자체를 정답 proof로 대신하지 않는다.

---

## 17. 다음 구현 작업의 우선순위

### 첫 번째 작업 묶음: R0.2의 사실과 미해결 질문 고정

실행 완료 기록을 추가하고, 현재 소스·설정·증거 연결을 보존한다. EXP-09 명세에 retention의 direct/reload 대조와 pre/post adaptation 대조를 넣는다. 이때 이미 성공한 R0.2를 다시 작성하지 않는다.

### 두 번째 작업 묶음: R0.2.1의 최소 수직 경로

```text
기존 공개 Observation
    → 기존 R0.2 진행
    → dependency step 직후 snapshot
    → 파일 저장 / 복원
    → resume
    → 동일한 판단·primitive proof·memory 결과
    → 독립 replay로 상태 전이 확인
```

이 한 경로가 다음 단계의 기반이다. 여기에 새 graph rewrite, 전문화 회로, background cognition, goal-free 후보를 한꺼번에 넣지 않는다.

### 세 번째 작업 묶음: R0.3 명세 확정

두 M profile이 **무엇을 실제로 다르게 실행하는지**와 통합 계층의 총예산·근거 중복 방지·충돌 처리를 먼저 확정한다. R0.2.1 상태 계약을 사용해 작은 전문화 비교를 구현한다.

### 다음 세션에 전달할 구현 요청문

> 현재 R0.2 소스와 사용자 실행 증거를 기준선으로 보존한 상태에서 R0.2.1을 구현한다. 기존 136개 회귀 테스트를 유지하고, episode/revision과 별개인 generation/session 상태 계약을 추가한다. 먼저 기존 AdaptiveEngine의 dependency 진행을 snapshot·restore·resume할 수 있게 하되, 기존 판단·primitive proof·학습 결과의 의미를 바꾸지 않는다. 동역학적 settle과 구조적 JOIN, frontier retire와 장기 memory pruning을 구분한다. 새 상태 및 전이의 변조·stale binding·부분 적용을 검사하는 독립 audit를 추가한다. 이번 범위에 전문화 M, 일반 graph rewrite, 지속적인 latent activation, goal-free candidate generation은 포함하지 않는다. 구현·정적 검사·실제 실행 결과를 나눠 보고하고, 커밋·push는 수행하지 않는다.

이 요청문은 후속 작업을 위한 계획이며, 이번 문서 작성에서 실행한 명령이 아니다.

---

## 18. 최종 목표와 확장 조건

HCR의 다음 목표는 “직관 기능”과 “논리 기능”을 이름으로 나누는 것이 아니라, **같은 계산 원리와 검증 체계 안에서 익숙한 경로의 재사용, 다른 처리 방법의 협력, 구조의 재조합, 출력되지 않은 상태의 지속, 표현 수준의 이동이 어떻게 행동 차이를 만드는지** 보여주는 것이다.

CPU symbolic 참조 엔진에서 이 차이가 계측된 뒤 외부 입력·성능 확장을 검토한다. LLM은 candidate generator나 representation adapter로 붙일 수 있으나, LLM 제공 정보와 HCR 자체 계산의 기여를 분리하는 대조가 먼저 필요하다. GPU/분산 backend는 실제 병목과 같은 의미·수치 계약의 재현성을 확인한 뒤 검토한다. 감각 입력과 물리 하드웨어는 독립된 과제·근거가 필요한 후속 단계로 남긴다.

**현재 출발점은 R0.2의 정상 실행이다. 가장 가까운 다음 성과는 그 계산을 의미 손실 없이 시간과 상태로 다룰 수 있게 만드는 것이고, 그 기반 위에서 전문화·연결 학습·지속 수렴·발상·A/D/M 조합을 하나씩 실험한다.**

---

## 부록 A. 자료와 코드 근거

### A.1 제공 자료

- **[S1]** `HCR_세션인계_2026-09-16(1).md`: §2 A/D/M·세 그래프 구분, §11 R0.2 계획, §12 D→M→A 순서, §16 연구 원칙.
- **[S2]** `붙여넣은 텍스트 (1)(20260916-130428).txt`: 1–145행 적용, 148–290행 테스트, 291–292행 demo, 293–294행 verify.
- **[S3]** `갑자기_떠오르는_생각_수렴모델_관점_2026-09-16(1).md`: §2 연속 내부 변화, §3–5 직관·발상, §6 세대 전이, §8 지연된 생각, §10 핵심 가설.
- **[S4]** `세상의_변화_사건그래프_세대전이_관점_2026-09-16(1).md`: §2 계승·분기·수렴·소멸, §3 세대 정의, §6 그래프 전이, §8–9 기존 모델 연결.
- **[S5]** `시냅스_연결_좌뇌우뇌_관점_대화기록_2026-09-16(1).md`: 사용자 제안 5–13행, 이후 대화의 유효 경로 21–87행, 전문화 93–183행, 회로 간 연결·학습 235–299행. 사용자 제안과 AI 해석이 혼재된 기록임.
- **[S6]** `R02_적용_실행안내.md`, `R02_정적검사_결과.json`: 배포 당시의 적용·검사 범위. 이후 사용자 실행 사실은 [S2]를 우선한다.

### A.2 실제 소스 위치

아래 행 번호는 이번에 복원한 R0.2 배포 snapshot 기준이다.

| ID | 위치 | 확인한 내용 |
|---|---|---|
| [C1] | `src/hcr/model.py:42–120, 127–188, 265–357` | 작은 Config 한도, goal 필수 관측/Program, 두 A 수준, AdaptiveConfig·Cost·Mismatch 계약 |
| [C2] | `src/hcr/dynamics.py:7–65` | 동기 tick, 중립 초기값, 선택적 initial, goal 기반 settle, 기록 어댑터 |
| [C3] | `src/hcr/workspace.py:71–223` | RoutePrefix·AdaptiveWorkspace, 실제 확장, 측면 분기 보존, 최종 network 재구성 |
| [C4] | `src/hcr/expansion.py:10–41`; `src/hcr/activation.py:12–135` | deterministic policy, bounded matching, prior·mismatch·eligibility·후보 경쟁 |
| [C5] | `src/hcr/compiler.py:23–79`; `src/hcr/patterns.py:7–61` | 실제 양의 proof에서 길이별 연속 path motif 추출, `open_edge`, certificate |
| [C6] | `src/hcr/circuits.py:124–252` | R0.1/R0.2 memory 구분, PatternCircuit/Pending, 구조·증거 이력 |
| [C7] | `src/hcr/learning.py:73–145` | feedback 이후 약화·검증 증거·등록, 원자적 memory 교체 |
| [C8] | `src/hcr/evaluation/adaptive_protocol.py:20–81, 156–214` | 집계와 비용, checkpoint 동등성, adaptation 및 새 weak-profile retention |
| [C9] | `src/hcr/runtime.py:132–306` | AdaptiveEngine의 추론·새 revision·feedback 권한, frozen memory |
| [C10] | `src/hcr/identity.py:7–66` | Node/Semantic/Role 분리, observation digest/revision-bound binding |
| [C11] | `architecture/r02-engine.ko.md`; `ROADMAP.md`; `docs/R02_ACCEPTANCE.ko.md`; `experiments/` | 구현 경계·이전 후속 계획·연구 gate·기존 실험 구획 |

### A.3 배포 소스 식별

| 파일 | SHA-256 |
|---|---|
| `hierarchical-convergence-circuit-r01-source.zip` | `c69ba87af591fa508f9d9cfd9b42e5515aef5206034e78b89e801f56e43d50b0` |
| `hcr-r02-update.zip` | `1ef93af88705bb16c134eafb6ee6e98673d59065d9d9b8d6259c8c61c916fc66` |

기준 snapshot은 위 R0.1 ZIP에 R0.2 `payload/`를 적용한 구성이다. GitHub commit SHA를 대신 만들어 기입하지 않았다.

### A.4 이번 문서 작성에서 수행한 작업

첨부 가설·인계·실행 로그를 읽고, 배포 ZIP을 분석용 경로에 복원했으며, 현재 인터페이스와 동작·계약을 대조했다. 복원본의 release manifest 해시를 확인하고 로드맵을 작성했다. 프로젝트 모듈 import, check/demo/verify 재실행, 사용자 저장소 수정, 커밋·push는 하지 않았다.


## 20. 이번 원문 재대조로 유지·보완할 횡단 계획

첨부 원문 S01~S06의 파일명/hash와 24개 개념 연결은 `evidence/concept_coverage.json`, 독립 설명은 `docs/CONCEPT_COVERAGE.ko.md`에 있다. 이 catalog의 구현 상태는 소스 검토 상태이며 `evidence/claims.yaml`의 가설 증거 등급을 대체하지 않는다.

기존 repo에는 EXP-04(binding), EXP-05(cross-A), EXP-06(decision/explanation), 공통 primitive 가설·claim이 이미 있다. 따라서 '누락'은 상당 부분 후속 로드맵의 연결 부족이었다. 동일 개념을 새 엔진·새 실험 ID로 중복 생성하지 않는다.

| 과제 | 지금 가능한 것 | 이후 필요한 것 |
|---|---|---|
| EXP-04 | 계약·revision·재명명 불변성 | 의미를 실제 사용하는 matcher의 통제 실험. 결정적 ID 이름 변경으로 효과 강제 금지 |
| EXP-05 | 같은 kernel의 A0/A1·top-down 기반 | 다른 표현·과제의 재사용, 수렴결과 승격·근거 복원·cross-A recurrence |
| EXP-06 | R0.1 독립 이벤트, R0.2 proof/trace 관찰 | R0.2 새 trace schema의 readout/설명 시간; 탐색 graph와 proof의 타입 차이를 반영한 비교 |
| EXP-03 | 안정 오답·다른 초기값의 두 attractor 시험 | 동일 trajectory의 switching·dwell time, low/high-A analogue |
| X-FAIL | Status·외부 assessment에 의한 관측 taxonomy | stage별 원인 증거·first failure/전파 분리 |

이 항목을 R0.8 이후의 별도 '고도화'로 미루지 않는다. 다음 기능 변경과 함께 사용할 검증 기준이다. stable wrong가 있었다고 원인이 over-compression인 것은 아니고, 서로 다른 초기값의 안정점 두 개가 있었다고 자발적 시간 전환을 구현한 것은 아니다.

## 21. substrate와 Plasticity/I/F 장기 gate

B0/B1/B2의 계약은 `architecture/substrate-contract.ko.md`를 따른다. 물리 자원 풀의 크기와 논리적 연결·의미 identity를 구별한다. connect/disconnect/strengthen/weaken/reroute/threshold/delay를 학습 제어의 후보 연산으로 보존하되, 현재 CPU 자료구조를 physical network로 부르지 않는다.

Configuration은 상대적으로 느리게, 반복 실행은 local하게 두는 원칙을 설계 목표로 유지한다. 상위 control의 권한·통신 비용을 계측해야 실제 충족 여부를 알 수 있다. event trace와 event-driven scheduler, Python 병렬 루프와 물리적 병렬성도 구별한다.

B1은 기존 동기 kernel을 참조하며 queue·sparsity·지역 통신·read/write·runtime·오차를 비교한다. B2는 장치/소자 상태가 실제 계산을 수행하는 정도와 재구성·학습·전력 비용을 측정한다. 연산수 감소를 자동으로 에너지 효율 우위로 바꾸지 않는다. 문헌 신규성은 별도 외부 조사로 남긴다.

## 22. 즉시 적용 범위와 다음 행동

이번 코드 변경은 개념 anchor 검사와 기존 capture의 관측·설명 포함 관계 분석 도구다. `src/hcr` 및 당시 plan에 들어가는 실행 소스/설정 집합은 동일하다. R0.2.1 snapshot/resume, M·A 자동화, 지속 readout, learned semantic binder, event-driven backend는 아직 구현 대상이다.

기준선 capture를 새 reviewer로 읽고 원시 비용/회로 변화를 분석한 뒤 EXP-09가 필요한 원인 질문을 구분한다. 이것을 위해 처음부터 R0.2 demo를 다시 돌릴 필요는 없다. 다음 기능 구현은 기존 순서대로 R0.2.1이다.
