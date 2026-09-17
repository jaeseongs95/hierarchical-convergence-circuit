# HCR EXP-11 분석과 습관·고정관념 가설의 통합 후속 설계

- 기준 저장소: `jaeseongs95/hierarchical-convergence-circuit`
- 검토한 main: `7803ec250efc950e848298ba79c141946d89c2df` — `exp11 실행결과 commit`
- 결과: `HCR-Evidence/exp11/r03-first/`
- 첨부: `HCC_습관_고정관념_세션정리_2026-09-17(1).md` 전체
- 성격: 결과 분석 및 다음 구현·실험의 설계안. 이 문서의 신규 모듈·실험 번호는 제안이며 아직 구현하거나 실행하지 않았다.
- 표기: 프로젝트의 가설명 HCC와 저장소 코드의 HCR 명칭을 각각 유지한다.

## 1. 결론

다음 연구의 중심은 **회로를 더 강하게 만드는 것** 자체가 아니라, **회로의 구조적 재사용 가치와 현재 입력에 대한 판단 신뢰를 분리하고, 반례 뒤 변경 범위를 얼마나 적절하게 조절하는가**로 잡는다.

EXP-11은 다음 기반을 제공했다.

1. 서로 다른 처리 방법을 같은 입력·학습 memory·총예산 상한에서 실행한다.
2. 실제 생성된 경로 메시지가 상대 처리기의 기존 frontier 순서를 바꿀 수 있다.
3. 서로 다른 결론을 합의로 위장하지 않고 충돌·보류로 기록한다.

그러나 현재 결합 처리는 **충돌을 발견하는 장치**이지, **충돌의 원인을 판단하고 장기적으로 수정하는 장치**까지는 아니다. 이번 결과에서 더 많은 처리기를 사용했다고 전반적으로 더 좋은 성능을 얻은 것도 아니다. [S2–S5]

첨부 문서는 이 경계에서 필요한 연구 질문을 구체화한다. 사용자가 제시한 핵심은 강한 회로의 변경 비용, 연결된 다른 기능의 손상 가능성, 반복에 따른 해석 구조의 고착이다. Strength·Rigidity·Entanglement·Attractor Width 등은 그 직관을 연구 언어로 확장한 후보이며, 모두 사용자 자신의 원래 표현이나 이미 확인된 실험 사실로 취급하지 않는다. [A1 §9, §11–18]

권장 흐름은 다음과 같다.

> **R0.3 기준선 수용 → prior 역할 분리 → 반례 후 수정과 다음 episode 유지 → 공유 dependency의 수정 범위 → 구조적 consolidation → 기존 persistent/hierarchical 연구와 결합**

A/D/M을 새 이름으로 바꾸거나 습관·고정관념을 네 번째 구조축에 넣지 않는다. 기존 표현·의존·방법의 축에 **학습 이력·가소성·수정 비용을 관찰하는 시간적 연구축**을 연결한다.

## 2. 이번 검토에서 실제로 수행한 범위

### 2.1 직접 확인

- 원격 main의 커밋을 고정했다.
- 원격 EXP-11 요약표 84행, 감사 결과, 계획, 결과 디렉터리 목록을 열람했다.
- `raw/limited/familiar/fixed.json`의 예산·초기 관측·controller 진행 부분을 열람했다. 전체 84개 raw를 내려받아 검사한 것은 아니다.
- 현재 `methods.py`, `integration.py`, `method_protocol.py`, `activation.py`, `workspace.py`, `learning.py`의 관련 정의를 대조했다.
- 이전 배포에 포함된 `src/hcr` 38개 파일의 로컬 복사본에 대해 Git tree를 재계산했다. 원격 현재 `src/hcr`의 tree `99fac92cd2f3af777dba1a82b0b83cefdc731c1a`와 정확히 일치했다. 따라서 전체 소스 독해에는 이 바이트 일치 복사본도 사용했다. 이전 개발 실행 결과를 사용자 실행 원자료로 대체하지 않았다.
- 원격에서 읽은 요약 Markdown과 Git blob `1ed2442da3e91acf31e61d463096b36e11324934`가 같은 로컬 복사본을 확보하고 표를 별도 Python 코드로 재집계했다.
- 첨부한 습관·고정관념 문서를 전체 읽었다.

### 2.2 수행하지 않은 것

전체 EXP-11 감사 재실행, 84개 raw 전체의 해시·수치 재검산, 신규 HCR 추론, 사용자 저장소 수정, 커밋·push는 수행하지 않았다. 아래 전역 `verified`와 수치 재연산 수는 **원격에 저장된 감사 결과**다. 이번에 직접 계산한 것은 요약표의 조건별 집계·대조와 소스 동일성이다.

## 3. EXP-11 결과: 기능 성공과 성능 우월성을 구분

### 3.1 저장된 완료·감사 상태

원격 audit는 `verified=true`, 비교 실행 84개, 처리기 시도 140개, seed 학습 6개를 보고한다. 316개 advance, 120개 메시지, 8,634개 수치 tick을 검사했고, 메시지 소비 68개와 우선순위 변경 6개를 기록했다. 요약표에서 재집계 가능한 advance·tick·메시지 소비·우선순위 변경 합계는 각각 316·8,634·68·6으로 일치한다. [S3]

84개는 7개 수작업 사례 × 6개 방법 조건 × 2개 예산 조건이다. 84개의 독립 문제나 일반 성능 표본으로 세지 않는다. 140개 처리기 시도에는 완료하지 못한 처리기도 있다.

### 3.2 조건별 판단

| 예산 | 방법 | 정답 | 오답 | 보류 | 판단 수 |
|---|---|---:|---:|---:|---:|
| standard | sequential | 6 | 0 | 1 | 7 |
| standard | associative | 6 | 1 | 0 | 7 |
| standard | fixed | 5 | 0 | 2 | 7 |
| standard | adaptive | 5 | 0 | 2 | 7 |
| standard | fixed_no_messages | 5 | 0 | 2 | 7 |
| standard | adaptive_no_messages | 5 | 0 | 2 | 7 |
| limited | sequential | 6 | 0 | 1 | 7 |
| limited | associative | 6 | 1 | 0 | 7 |
| limited | fixed | 1 | 0 | 6 | 7 |
| limited | adaptive | 1 | 0 | 6 | 7 |
| limited | fixed_no_messages | 1 | 0 | 6 | 7 |
| limited | adaptive_no_messages | 1 | 0 | 6 | 7 |

이는 요약표 84행을 다시 세어 얻은 결과다. [S2]

결합 조건은 weak_conflict에서 associative의 오답을 외부 최종 답으로 확정하지 않는다. 대신 conflict_abstention으로 보류한다. 그러나 unknown에서도 sequential이 답을 내지 못하므로 결합 결과가 보류된다. **오답 방지와 답변 가능 범위의 축소가 동시에 존재한다.**

향후 평가는 정답/오답/보류를 항상 함께 보고한다. 필요하면 응답률과 응답한 항목에 한정한 정확도를 병기하되, 보류가 많은 방법을 정확도 하나로 우월하다고 평가하지 않는다. 판단을 유보하는 비용은 응용 목적을 정한 경우에만 별도 손실로 설정한다.

### 3.3 메시지는 실제로 효과가 있었는가

다음 대응쌍에서는 효과가 관찰됐다.

| 사례·예산 | 조건 | 메시지 없음 | 메시지 있음 | 해석 |
|---|---|---:|---:|---|
| fork·standard | fixed 및 adaptive | 6 advances / 105 ticks | 5 / 105 | 경로 전개 감소, 수치 tick 변화 없음 |
| diamond·standard | fixed 및 adaptive | 4 / 124 | 3 / 97 | 경로 전개와 수치 tick 모두 감소 |
| diamond·limited | fixed 및 adaptive | 4 / 124 | 3 / 97 | 제한 예산에서도 같은 차이 |

6개의 priority change는 위 대응조건에서 발생한다. 이는 독립된 여섯 문제에서의 발견이 아니라, 두 사례를 방법·예산 조건으로 반복한 관찰이다.

다만 diamond의 단독 sequential은 60 ticks, associative는 64 ticks다. 결합의 97 ticks는 **메시지 없는 결합 124 ticks보다 낮지만 단독 방법보다 낮지는 않다.** 메시지의 기여와 결합 시스템의 최종 효율을 구분한다. [S2]

### 3.4 adaptive가 fixed보다 나았는가

이번 14개 사례·예산 조합에서 fixed와 adaptive의 표에 기록된 출력·정답 여부·통합 상태·advance·tick·메시지 소비·우선순위 변경은 같다. 메시지 없는 두 조건도 이 지표에서 동일하다.

이 결과로 전체 controller 이력까지 같다고 주장하지 않는다. **현재 과제와 보고 지표가 적응 스케줄러의 추가 이득을 구분하지 못했다**는 결론이다. 향후에는 동일 공개 상태에서 두 정책이 서로 다른 선택을 하는 시점이 실제 존재하는지 먼저 확인하고, 그 선택 차이가 성능을 바꾸는 과제를 설계한다.

### 3.5 limited의 보류 원인

standard는 `max_advances=12, max_kernel_ticks=2048`, limited는 `4,480`이다. 두 상한이 함께 바뀌므로 결과만으로 한 상한의 효과라고 부르지 않는다. [S4]

직접 읽은 limited/familiar/fixed 원시 기록에는 사용 advance=4, 사용 tick=69, 미사용 tick=411이 있다. associative는 이미 정답을 냈지만 sequential은 경로 전개가 남아 있다. 현재 통합 함수는 모든 기대 처리기가 완료되고 비보류 결론이 같아야 값을 낸다. [S5–S6]

따라서 이 사례의 보류는 단순히 “수치 tick이 부족했다”가 아니라 **공동 advance 상한에 도달했고 두 결과 완료를 요구하는 통합 계약이 작동한 것**이다. 이 현상을 고정관념이나 rigidity로 분류해서는 안 된다.

다음 예산 대조는 advance만 변화시키고 tick은 충분히 고정하는 시험과, tick만 변화시키는 시험을 분리한다. 시작 처리기도 양쪽을 균형 배치한다. 기존 기록은 first_method=associative다.

### 3.6 unknown의 정답을 어떻게 읽어야 하나

unknown은 모든 edge score가 None이고, 외부 참값은 모두 True인 수작업 사례다. associative가 True를 내 정답으로 평가받고 sequential은 보류했다. [S2, S7]

현재 prior는 관측 불확실성이 클수록 강해지는 계산을 포함한다. 따라서 여기서의 성공은 **해당 참값과 학습 prior가 일치한 조건에서의 성공**이다. 이를 무관측 상태에서 참값을 식별한 능력으로 확대하지 않는다.

다음 시험에는 공개 관측과 memory가 완전히 같은데 숨은 참값만 다른 대응 환경을 둔다. 이 경우 추가 관측 전에는 구분할 정보가 없다. 동일 출력을 두 외부 세계에 평가하는 것은 식별 불가능성을 확인하는 대조이며, 두 개의 독립 추론 성과로 세지 않는다. 강한 prior가 유용한 범위와 근거 없는 확정을 구분하는 데 필요하다.

## 4. 첨부 가설을 현재 구현과 연결

### 4.1 사용자 아이디어와 후속 정식화를 구분

사용자가 직접 제시한 핵심은 다음이다. [A1 §9]

- 습관: 강하게 형성된 회로를 바꾸기 어렵고, 변경에 비용이 들며, 다른 연결도 손상될 수 있다.
- 고정관념: 반복으로 해석 구조가 고착·consolidation된 상태일 수 있다.

첨부 문서가 이에 붙인 연구 변수들은 해석의 정식화다. 현재 코드에 같은 이름을 추가하는 것만으로 변수를 구현하거나 가설을 입증한 것이 되지 않는다.

### 4.2 반영 수준

| 개념 | 현재 상태 | 다음에 필요한 것 |
|---|---|---|
| Circuit Strength | `PatternCircuit.strength`와 외부 검증 후 강화·오류 후 약화가 이미 있다. | 회로 강도, 검증 횟수, 단순 사용 횟수, 나이를 분리 |
| Reuse Bias | 활성도·mismatch·prior가 macro 선택에 영향을 준다. | 입력별 재사용 확률/빈도와 유효 사용 범위 측정 |
| Interpretation bias | 회로 prior가 최종 판단의 relation·goal drive에도 들어간다. | routing 효과와 belief/판단 효과의 분리 개입 |
| Alternative Candidate Suppression | 후보 매칭·경쟁·예산 제한은 존재한다. | 미생성·매칭 실패·억제·미실행·선택 탈락을 단계별 구분 |
| Circuit Rigidity | 강도와 오류 이력은 있으나 독립적으로 측정한 수정 저항은 아니다. | 회로를 유지한 반례 수정, bypass, 다음 episode 유지 비교 |
| Escape Threshold | 코드의 threshold·revision 권한 규칙은 있다. | 코드 상수와 실제로 관찰된 재확장 경계를 구분 |
| Attractor Width | 이번 소수 사례만으로 폭을 측정하지 않았다. | 선언된 입력 공간에서 적용·오적용 영역 측정 |
| Dependency Entanglement | 동일 motif의 memory 상태를 여러 과제에 재사용할 수 있다. | 공유 parameter 영향과 실제 회로 간 공용 subgraph 참조를 구분 |
| Collateral Disruption | 여러 과제에서 수정 전후의 비표적 기능을 대조하지 않았다. | 정답이 변하지 않은 과제의 성능·비용 회귀 |
| Structural Consolidation | 길이 2·3 path motif의 생성·강화는 있다. | branch/join/recurrent topology 등 실제 구조 변화와 그 효과 |

현재 길이 3 회로가 길이 2 회로를 공용 하위 모듈로 참조하는 구조는 아니다. 길이 2·3이 같은 입력 edge에 겹쳐 적용된다는 사실만으로 회로 간 구조적 얽힘이 입증되지는 않는다. 다만 같은 PatternCircuit strength가 여러 입력에서 재사용되는 **parameter 수준 공유**는 최소 실험의 출발점이 될 수 있다. [S8–S10]

### 4.3 Strength와 Rigidity는 구분한다

현재 성공 강화식은 `s <- s + learning_rate * (1-s)`이고 오류 약화식은 `s <- weakening * s`다. 검증된 서로 다른 episode가 강화 조건이며, frozen evaluation에서 많이 호출하는 것만으로는 memory가 강화되지 않는다. [S9]

기본 learning_rate=0.25, 최초 등록 s=0.55 조건에서 같은 motif가 연속 성공하고 동일 전이 조건이 유지된다면 n≥3에서 다음 식을 도출할 수 있다.

`strength(n) = 1 - 0.45 * 0.75^(n-3)`

이는 **현재 코드로부터 도출되는 강화 곡선**이지 새 발견이 아니다. 50회와 100회를 비교했을 때 strength가 거의 포화되어도 구조적 consolidation이 발생했다고 읽지 않는다. 증거 수에 따른 balance도 따로 변한다.

Rigidity는 “s가 큼”의 다른 이름으로 저장하지 않는다. **정해진 반례·수정 정책 아래에서 이전 경로를 유지하는 정도와 올바른 전환을 지속하는 데 든 비용**으로 측정한다. 회로를 즉시 꺼서 얻은 correction 비용은 회로 영향을 유지한 escape 비용과 별개다.

### 4.4 Attractor Width의 두 의미

첨부 문서는 주로 여러 입력이 같은 해석에 흡수되는 범위를 이야기한다. 우선 다음을 따로 측정한다.

- **입력 적용 범위**: 미리 정한 입력 분포 Q에서 같은 motif가 선택되는 비율과 오적용 영역.
- **상태공간 basin**: 같은 입력·memory에서 초기 activation을 달리했을 때 같은 안정 상태로 수렴하는 영역.

두 실험은 같은 것이 아니다. 최초 구현은 입력 적용 범위부터 시작한다. 입력의 “near/far” 역시 문자열 길이나 이름이 아니라 topology 변화, 관측 불확실성, 맥락 변화, 반례 강도를 각각 정의한다. 임의로 하나의 distance로 합치지 않는다.

### 4.5 첨부 문서의 D 표현과 현재 계측 계약

첨부 §2.2·§8·§19는 외부 explicit reasoning 또는 `D_DAG` 감소 가능성을 언급한다. 현재 엔진의 실험에서는 **같은 정당화를 primitive proof DAG로 복원하면 D는 유지되고, macro hop이나 탐색량이 줄 수 있다**는 계약을 사용한다.

따라서 원문은 보존하되 후속 설계에서 다음 지표를 분리한다.

`D_DAG(primitive justification) / macro route hops / frontier expansions / kernel ticks / wall time`

표시된 macro가 짧아졌다는 이유로 primitive D가 감소했다고 기록하지 않는다. 긍정 경로 proof에서 부정 차단 proof로 바뀌면서 D가 달라지는 경우는 다른 proof가 선택된 것이지 같은 proof를 압축한 효과가 아니다.

## 5. 통합 아키텍처: 기존 엔진은 유지하고 제어·학습 경계를 명시

```text
Public Observation — 변경하지 않는 입력·revision
    │
    ├─ Circuit/Pattern Memory — 구조, 강도, 검증 이력
    │       ├─ Routing prior — 어느 경로를 우선 탐색할 것인가
    │       └─ Judgment prior — 어떤 상태를 더 그럴듯하게 볼 것인가
    │
    └─ MethodController
            ├─ Sequential worker
            ├─ Associative worker
            ├─ RouteHint — 실제 생성된 경로의 출처 포함
            └─ Integration — 합의/충돌/관측부족/예산부족
                    │
                    ├─ 충분한 근거 → Decision + primitive proof
                    ├─ 불일치 → ConflictReport → RevisionPolicy
                    │               ├─ 현 상태 추가 전개
                    │               ├─ 다른 처리 방법에 예산 배분
                    │               ├─ 공개 추가 관측 요청
                    │               ├─ 명시된 bypass 조건
                    │               └─ 보류
                    └─ 외부 결과/허용된 feedback
                            → PlasticityPolicy
                            → 수정 범위 기록
                            → 다음 episode에서 유지/부작용 평가
```

이는 제안 구조다. 현재 코드에는 RouteHint·worker·통합이 있고, ConflictReport와 장기 수정 정책은 추가 설계 대상이다.

### 책임 경계

**판단과 검증:** controller는 `correct`, hidden truth, 사례 정답을 입력으로 받지 않는다. 공개 관측·trace·의존관계·예산과 허용된 feedback만 사용한다. 두 처리기가 같은 evidence를 읽어 같은 답을 냈다고 지지도를 두 배로 세지 않는다.

**충돌의 위치:** ConflictReport는 최종 value 차이뿐 아니라 공통 observation에 대한 `assumed_edges`의 True/False 불일치, 미완료 경로, evidence 누락을 출처와 연결한다. 보고서는 정답 판정기가 아니다. 서로 다른 근거가 합쳐져 새로운 proof가 필요하면 별도 검증된 결합 절차가 있어야 한다.

**세 종류의 상태:** `pattern`의 불변 구조, learned memory의 versioned 상태, 현재 worker의 activation/frontier를 나눈다. 세션 저장은 이 상태를 보존하는 기능이며 consolidation 그 자체가 아니다.

**학습과 실행:** inference 중 memory를 몰래 수정하지 않는다. feedback 후 중앙 학습 단계에서 변경하며, 다른 worker의 구 memory를 재사용할 때는 version 불일치를 탐지한다. 현재 worker들은 동결 memory에서 출발하므로 R0.3 결과만으로 온라인 다중 worker 학습 안전성이 검증된 것은 아니다.

**예산:** 회로를 끄거나 방법을 바꾸어도 이미 쓴 비용을 0으로 초기화하지 않는다. 최초 판단·충돌 진단·추가 계산·관측·학습·checkpoint를 따로 기록하고 합산 범위를 명시한다.

## 6. 우선 구현: R0.3.1 / EXP-12(안) — prior 역할 분리

### 연구 질문

> 회로의 익숙함이 경로 탐색에는 도움이 되지만, 현재 관측의 참값 판단에 같은 prior를 넣으면 약한 반례를 잘못 흡수하는가?

이 실험을 우선하는 이유는 현재 코드에서 조작 지점이 분명하고, EXP-09의 오수렴과 EXP-11의 충돌을 하나의 원인 비교로 연결하기 때문이다. 광범위한 R0.4 구조 재설계보다 작은 변경으로 구분력이 높다.

### 최소 조건

| 조건 | 회로 선택·pool prior | 최종 판단의 learned prior | 용도 |
|---|---|---|---|
| legacy | 현재 그대로 | 현재 그대로 | 기존 기준선 |
| route_only | 현재 그대로 | 추가하지 않음 | prior의 최종 판단 기여 분리 |
| graph_only | 회로 사용 없음 | 없음 | 공개 관측 기반 대조 |

`route_only`에서는 pool의 prior·매칭·macro 선택을 동시에 바꾸지 않는다. 조건 이름은 명시적 policy로 기록하고 legacy를 기본값으로 보존한다. 모두 같은 관측·memory로 시작한다.

### 최소 과제

처음에는 길이 3 체인의 첫 edge를 대상으로 강한 반례·약한 반례·0점·약한 지지·강한 지지·None을 분리해 sweep한다. 나머지 edge, topology, 이름, 시작/목표는 고정한다. 정상 입력과 반사실 입력, 구조가 다른 소수의 보존 과제를 별도로 둔다. 이어서 training 3/6/9를 비교하되 실제 strength와 balance를 모두 기록한다.

None과 숫자 0을 같은 관측 상태로 합치지 않는다. 현재 drive 계산에서 둘이 같은 0으로 들어가더라도 관측의 결측 여부를 별도 지표로 남긴다.

### 두 수준의 대조

1. **전체 실행:** route_only 조작이 최종 판단·후속 expansion·비용을 어떻게 바꾸는가.
2. **고정 network 진단:** 동일 program·초기 상태·관측 drive에 learned drive만 다르게 넣어 수치 수렴 차이를 본다.

전체 실행에서는 prior 변화가 convergence 뒤 추가 탐색에도 영향을 줄 수 있다. 첫 전이 이후 경로가 달라졌다면 이를 숨기지 않는다. 고정 network 진단과 end-to-end 결과를 분리해야 route 효과와 judgment 효과의 위치를 더 정확히 구분할 수 있다.

### 관측 지표

- 출력, 외부 정답, 안정 오답, 보류 이유.
- pool에 적용한 prior와 최종 network에 적용한 prior를 각각 저장.
- assumed_edges, first-passage ticks, 최종 상태 margin/residual.
- motif 선택·binding span·frontier 변경, primitive proof D.
- 후보 funnel: 가능→생성→매칭→적격→실행→선택. 불가 이유를 별도 기록.
- expansions, binding, pool/decision ticks와 signals, controller 관리 시간.

정답·후보 universe는 evaluator에서만 계산한다. 엔진에 정답 경로나 누락 후보를 주입하지 않는다.

### 판정

- route_only가 동일한 초기 macro 활용을 유지하면서 weak conflict 오답을 줄이면, **최종 판단 prior의 오적용** 설명을 지지한다.
- 후보 생성 전에 대안이 사라지는 현상이 별도로 확인되면 **candidate suppression** 설명을 추가 검토한다.
- 최종 drive 조작만으로 차이가 없으면 매칭·후보 전개·integration 등 다른 지점을 검토한다.
- prior를 끄자 모든 입력을 보류한다면 그것을 정확도 개선으로 발표하지 않는다.

### 코드 변경 지점

| 위치 | 변경 방향 |
|---|---|
| `model.py` 또는 신규 `prior_policy.py` | legacy/route_only를 명시하는 작은 불변 정책 타입. 설정 서명과 버전 규칙 명시 |
| `activation.py` | 기존 pool 계산 유지, routing prior 관측값 명시 |
| `workspace.py::adaptive_network` | 최종 learned drive 적용 여부를 정책으로 분리 |
| `runtime.py`, `state.py`, `sessions.py` | 새 정책의 관측·snapshot·복원 일관성. 구 schema를 강제 변환하지 않음 |
| `evaluation/session_audit.py`, `method_audit.py` | 같은 정책에 맞춘 별도 drive 재계산과 구 기록 호환 |
| 신규 `evaluation/prior_protocol.py` | 입력 sweep·대응 memory·외부 평가·부정 결과 보존 |
| `experiments/exp-12-prior-scope/` | 조건 동결·관측 항목·판정 기준 |
| `tests/` | legacy 회귀, route_only 통제, policy 변조·누락 거부, label 누출 거부 |

이번 구현에서 새 예외 학습, 구조 pruning, pool 최적화, adaptive scheduler 교체는 함께 하지 않는다.

## 7. 다음 R0.3.2 / EXP-13(안) — 반례 뒤의 전환과 수정 저항

### 기존 EXP-11에서 보완할 관찰

`incomplete_or_ambiguous`에는 작업 미완료와 완료 후 모호함이 함께 들어간다. 향후 summary에는 최소한 다음을 구분한다.

`conflict / finished_ambiguous / unfinished_advance_budget / unfinished_tick_admission / no_candidate`

기존 raw의 값을 소급 수정하지 말고 새 보고서에서 가능한 범위만 파생 분류하거나 다음 schema에 추가한다.

`fixed`와 `adaptive`의 성능을 다시 비교할 때는 양쪽 정책이 공개 상태를 보고 서로 다른 배분 결정을 내리는 최소 fixture를 먼저 만든다. 메시지 수신 여부와 mismatch가 서로 반대 방향을 권하는 조건, 메시지는 있으나 frontier가 변하지 않는 조건, 시작 방법 반전 등을 별도 대조한다.

### Rule Shift의 실험 계약

규칙 A→B는 hidden truth만 바꿔 놓고 엔진이 알아내기를 요구하는 실험이 아니다. 변화에 해당하는 공개 맥락·관측 또는 허용된 결과 feedback을 제공해야 한다. 최초 오류 이전에 구별할 정보가 없다면 그 오류는 탐지 불가능 구간으로 분리한다.

현재 reachability 엔진은 행동 정책을 학습하는 엔진이 아니다. 여기서 먼저 수행하는 것은 **해석 경로의 반례 적응 analogue**다. state→action 습관 자체를 직접 시험할 때는 소규모 action/outcome 과제와 외부 평가기를 따로 만든다.

### 분리할 개입

| 개입 | 질문 |
|---|---|
| 기존 즉시 bypass | 회로 영향을 없앤 재계산 비용은 얼마인가 |
| 회로 유지 + 같은 입력 | 기존 prior를 유지하면 수정 가능한가 |
| 회로 유지 + 외부 반례 feedback | 명시적 약화·경쟁으로 올바른 상태로 전환하는가 |
| 추가 관측만 제공 | 새 정보의 기여는 얼마인가 |
| scope가 있는 예외 학습 | 특정 조건의 오류를 이후 episode에도 막는가 |

이를 한 번의 거대한 factorial로 구현하지 않는다. 우선 bypass와 회로 유지의 두 조건부터 만들고, 이후 추가 정보·학습 조건을 하나씩 분리한다. 현재 revision 경로가 자동으로 회로를 끄므로, 회로 유지 조건은 별도 실험 policy로 구현하고 audit에 기록해야 한다.

### Rigidity 측정

미리 정한 자원 예산과 입력 집합 아래에서 다음을 측정한다.

- 오류 신호 후 이전 경로가 계속 선택되는 횟수.
- 올바른 새 경로를 처음 선택하기까지의 비용.
- 다음 새로운 episode들에서 수정 효과가 유지되는 비율.
- 이미 정상인 입력에서 생긴 성능·비용 손실.
- 선택은 바뀌었지만 정답은 아닌 경우, 정답은 맞았지만 이후 재발한 경우의 분리.

EscapeThreshold는 코드의 고정 threshold 값과 구분한다. 관측 반례 강도 또는 누적 허용 feedback을 변화시킨 반응 곡선에서 추정한다. 비단조 결과는 임계점 하나로 덮지 않는다.

처음부터 `rigidity=0.9`를 추가하고 rigidity 효과를 측정하지 않는다. 강도·이력·연결 구조의 개입에서 수정 저항이 실제로 나타나는지 본다.

## 8. R0.4a/b / EXP-14(안) — 공유 dependency와 부수 손상

### 8.1 최소 단계: 공통 motif 상태의 공유

현 구조에서도 여러 과제가 같은 motif를 사용한다. 한 task의 오류로 해당 motif strength를 낮추면 다른 정상 task에서 recall·탐색 비용이 달라질 수 있다. 이 수준은 현재 엔진에 가까운 최소 대조다.

공유 memory 조건과 과제별 격리 memory 조건을 비교한다. 동일 초기 기능·동일 학습 정보에서 시작하고 저장량 차이는 비용으로 보고한다. 비표적 task들의 외부 정답은 바뀌지 않도록 고정한다. target 성능이 회복되지 않았는데 다른 task 성능이 유지됐다는 이유만으로 좋은 수정이라고 평가하지 않는다.

### 8.2 구조적 공유 단계

상위 Circuit A·B·C가 실제로 동일한 `SubcircuitRef(component_id, version)`를 참조하게 한다. 초기에는 작은 DAG와 고정 port contract만 허용한다. 이 단계가 되어야 하위 구조 편집이 상위 회로들에 어떻게 전파되는지 직접 시험할 수 있다.

단순히 두 프로그램에 같은 모양의 코드가 있다는 것은 공유 참조가 아니다. 다음을 구분한다.

- 같은 입력 edge에 겹쳐 binding.
- 같은 pattern ID·strength를 여러 과제에서 사용.
- 실제로 같은 mutable subcircuit/state를 여러 상위 회로가 참조.

### 수정 방식 대조

| 방식 | 예상 장점/비용 — 실험으로 판단 |
|---|---|
| shared in-place 변경 | 적은 저장량, 넓은 영향 범위 가능 |
| 공개 맥락에 한정된 guarded 수정 | 비표적 기능 보존 가능, guard 계산·표현 비용 |
| clone 후 해당 route만 재연결 | 국소 수정 가능, memory·관리 비용 증가 |
| bypass 또는 별도 alternative route | 원본 회로 보존, 반복 계산 비용 가능 |

전체 규칙이 실제로 바뀐 경우에는 공유 모듈의 일괄 수정이 맞을 수 있다. 특정 맥락만 달라진 경우와 구분한다. 무조건 모든 변경을 국소화하는 정책도 가설로 고정하지 않는다.

### 측정

- target의 correct recovery와 retention.
- **정답이 유지되는 비표적 과제**의 정확도 감소와 계산비용 증가.
- 변경 node/edge/parameter 수, 재binding 수, 재compile 수, 신규 memory bytes.
- dependency 영향 범위, rollback/recovery 비용.
- 독립 memory와 shared memory의 초기 자원 차이.

이것이 첨부 문서의 “하나를 바꾸면 다른 연결도 영향을 받는다”를 시험하는 직접적인 대응이다. “수정 에너지”는 우선 계산·저장·탐색 비용 벡터로 다룬다. 실제 에너지 계측 없이 Joule이나 인간의 두려움으로 환산하지 않는다.

## 9. R0.4c / EXP-15(안) — 구조적 consolidation

강도만 포화되는 시스템에서는 첨부 문서의 “굳은살처럼 뭉쳐짐” 중 구조적 부분을 평가할 수 없다.

동일 입출력 함수·초기 성능을 가능한 한 유지하면서 다음을 분리한다.

1. topology 고정, scalar strength만 갱신.
2. 같은 초기 기능에서 작은 circuit-to-circuit 연결 또는 복합 motif를 추가·재배치.
3. shared dependency를 사용하거나 독립 복제하는 조건.

fork/join, connection 강화·약화·비활성화는 compiler와 evaluator가 구조 certificate를 검증할 수 있는 작은 vocabulary부터 도입한다. 임의 graph mining이나 실제 신경회로를 바로 목표로 삼지 않는다.

가설은 “연결 수를 늘리면 반드시 수정 비용이 커진다”가 아니다. 추가 연결이 대체 경로를 제공해 수정이 쉬워지는 반대 결과도 가능하다. 동일 target 회복 수준에서 재배선 비용·부수 손상·재발률이 어떻게 달라지는지가 판단 기준이다.

나이, 반복 횟수, strength, evidence_count, topology 변화량을 분리 기록한다. consolidation이 단지 추가된 cost 때문에 비싸게 보이지 않도록 동일 기능의 대조와 자원 계측을 포함한다.

## 10. 기존 장기 로드맵의 연결

| 기존 단계 | 이번 가설의 연결 | 유지할 경계 |
|---|---|---|
| R0.3 M specialization | 해석 충돌 발견, 정보 교환, 수정 방법 선택 | 합의는 외부 증거가 아님 |
| R0.4 structural plasticity | shared dependency·scope-aware 수정·consolidation | 가중치 변화와 구조 변화 구분 |
| R0.5 persistent/readout | 복귀·재발·시간에 따른 활성 유지/감쇠 | 디스크 snapshot과 지속 activation 구분 |
| R0.6 A adaptation 및 계층 반복 | 하위 evidence와 상위 해석의 제약 상호작용 | 같은 primitive의 cross-A 재사용은 별도 검증 |
| R0.7 A/D/M 결합 | 표현·의존·방법에 따라 rigidity가 어떻게 달라지는가 | 세 축 독립성을 미리 확정하지 않음 |
| 감각·착시 analogue | 낮은 수준 misconvergence와 높은 수준 고착 비교 | 실제 인간 기전으로 일반화하지 않음 |
| event-driven·local/physical | 재사용·수정의 실제 자원 비용 비교 | Python wall time을 하드웨어 효율로 환산하지 않음 |

습관·고정관념을 위해 기존 아키텍처를 폐기할 이유는 없다. **Graph↔Circuit 형성 이후의 적응·수정·재발을 측정하는 연구 축을 기존 단계에 연결**한다.

## 11. 데이터·저장소 운영

현재 사용자가 채택한 프로젝트 내부 누적 구조를 유지한다.

```text
hierarchical-convergence-circuit/
├─ src/hcr/                 # 공통 엔진·정책·평가기
├─ tests/                   # 단위·회귀·변조·경계 시험
├─ experiments/
│  ├─ exp-11-method-interleaving/  # 기존 계획 보존
│  └─ exp-12-prior-scope/         # 다음 설계 제안
├─ docs/                    # 결과 해석과 설계 변경 기록
├─ theory/source/           # 첨부 원문의 불변 보존 위치 제안
├─ evidence/                # 정제한 주장·구현·증거 연결
└─ HCR-Evidence/
   ├─ exp09/                # 기존 실패·복구 결과 보존
   ├─ exp10/                # 상태 동등성 결과 보존
   ├─ exp11/r03-first/      # 이번 run 원본 그대로
   └─ exp12/<새-run-id>/    # 새 조건만 새 폴더에 기록
```

이 트리는 배치 제안이며 이번에 저장소에 적용하지 않았다. 오래된 raw·manifest·계획을 현재 설명에 맞게 다시 쓰지 않는다. 새 해석은 별도 문서/분석 폴더로 연결한다.

실행기는 기존 output 존재 시 중단하고 오류 직후 다음 단계로 진행하지 않는다. 단일 시험도 현재 프로젝트의 `unittest discover -s tests` 진입 환경과 일치시킨다. PowerShell 실행 정책 우회는 기존처럼 해당 실행 프로세스 범위로 한정한다. 실험 실패와 스크립트·경로 오류를 구분하며, 최초 실패 기록을 재실행으로 덮지 않는다.

검증 수용은 세 층으로 나눈다.

1. 구현 수용: schema, snapshot, legacy 회귀, provenance, budget, no host correction.
2. 실험 수용: 계획된 대응조건이 실제 실행됐고 독립 evaluator가 일치함.
3. 가설 판정: 개선/악화/동일/판정불가 중 실제 결과에 맞게 기록함.

사용자가 결과를 제공할 때는 각 run 폴더 전체를 보존·전달한다. 분석 보고서를 생성하는 도구는 원본 폴더 내부에 새 파일을 끼워 넣지 않고 별도 분석 run에 기록한다.

## 12. 다음 구현 작업의 확정 범위 제안

**다음 한 번의 구현은 R0.3.1 — prior 역할 분리와 적용 범위 계측으로 제한한다.**

포함:
- legacy 기본 동작 보존.
- route_only vs legacy vs graph_only의 명시적 조건.
- 동일 memory·관측을 사용하는 최소 score sweep.
- pool/판단 prior 및 후보 funnel 기록.
- fixed network 진단과 end-to-end 대조의 구분.
- 외부 truth 비노출과 legacy snapshot/audit 호환 시험.
- 현재 HCR-Evidence 내부에 새 결과 축적.

제외:
- rigidity 수치를 수동으로 올리는 구조.
- 오류 회로와 모든 유사 회로의 일괄 약화.
- 과거 실패 label·hash 수정.
- 정답을 아는 controller.
- 부정 예외 학습·공용 subcircuit·pool 최적화를 동시에 변경.

그 결과에 따라 R0.3.2에서 correction 정책을 정하고 R0.4에서 수정 범위를 실제 공유 구조로 확장한다. **더 큰 모델을 한 번에 만드는 것보다, 지금 왜 틀리고 왜 수정이 유지되지 않는지 구별하는 것이 다음 단계의 우선 목표다.**

## 근거 위치

모든 GitHub 경로는 다음 고정 커밋 아래의 파일이다.
`https://github.com/jaeseongs95/hierarchical-convergence-circuit/tree/7803ec250efc950e848298ba79c141946d89c2df`

- **A1**: 사용자 첨부 `HCC_습관_고정관념_세션정리_2026-09-17(1).md`. 원문 전체를 읽었으며 특히 §9 사용자 추가 가설, §11 공유 dependency, §12 consolidation, §14 A/D/M 구분, §15–19 변수·실험 후보를 사용했다.
- **S1**: main 커밋·root tree·`src/hcr` Git tree 조회.
- **S2**: `HCR-Evidence/exp11/r03-first/summary.ko.md` — 84행 전체.
- **S3**: `HCR-Evidence/exp11/r03-first/audit.json`.
- **S4**: `HCR-Evidence/exp11/r03-first/plan.json`.
- **S5**: `src/hcr/methods.py` — MethodEngine, choose_worker, tick_reservation.
- **S6**: `src/hcr/integration.py` 및 `raw/limited/familiar/fixed.json`의 controller·budget 부분.
- **S7**: `src/hcr/evaluation/method_protocol.py` — cases, external_assessment, summarize.
- **S8**: `src/hcr/activation.py::instantiate_pool`, `workspace.py::adaptive_network`.
- **S9**: `src/hcr/learning.py::update_adaptive`, `circuits.py::PatternCircuit.balance`.
- **S10**: `src/hcr/patterns.py::CircuitPattern`, `compiler.py::SubgraphCompiler`, `state.py`, `sessions.py`.

첨부 산출물 `EXP11_요약표_독립재집계.json`과 `검토범위_출처.json`에 수행 범위와 해시를 별도로 남겼다.
