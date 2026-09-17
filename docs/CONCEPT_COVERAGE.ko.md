# R0.3.2 연결 보강

근거 진단은 K18 오류 taxonomy와 K23 외부 정확도/내부 정합성 구분에 연결한다.
proof 유효성·관측 지지·외부 정확도를 분리하며, 근거 부족을 모든 오류의 원인으로 단정하지 않는다.
기존 구현 상태 등급은 올리지 않는다. [상세](R032_DESIGN.ko.md)

---

# R0.3.1 반영

K09/K24에 prior 적용 범위 비교 구현을 연결했다. 기존 지위는 유지하며 습관/rigidity/consolidation을 입증된 개념으로 승격하지 않는다.
기본 runtime·session anchor는 대응 정의를 재검토하고 현재 hash로 갱신했다. 관련 설계는 [R0.3.1](R031_DESIGN.ko.md)이다.

---

# R0.3 반영

HCR-K13은 **implemented_scoped**로 갱신한다. 범위는 두 수작업 M profile, 메모리 내 교대,
typed 경로 hint, 총상한, 충돌 보류다. 범용 M 학습·영구 circuit link를 완료 처리하지 않는다.
변경한 코드 anchor hash는 현재 구현과 대조했다. 아래 표의 과거 상태는 이력이며 최신 기계 판독 상태는 `evidence/concept_coverage.json`이다.

---

# R0.2.1 반영

기존 24개 개념과 상태 분류는 유지했다. HCR-K11에 `AdaptiveEngine.finish`의 구현 경계,
HCR-K14에 `AdaptiveSession`의 dependency 경계 저장·복원 근거를 추가했다.
두 개념 모두 **partial**이다. 지속 활성/새 readout gate/자연어 설명의 인과 동일성을 구현한 것이 아니다.
변경한 runtime 근거 hash는 실제 R0.2.1 소스 대조 후 갱신했다. 검사 자체는 의미 검증이나 연구 증명이 아니다.

---

# 여섯 원문과 현재 HCR의 개념 추적

기준: R0.1 실제 배포 → R0.2 적용 패키지 → 기준선 패키지. 사용자는 이 적용과 실행을 완료했다고 로그를 제공했다. 이번 원격 조회는 404여서 최신 remote commit을 인증하지 못했다.

이 표는 가설의 참/거짓이 아니라 **소스/시험 정의/설계에 어디까지 반영됐는지**다. `implemented_scoped`는 명시된 toy 범위만, `partial`은 구현 또는 명세 일부, `planned`는 계획이다. 시험 정의 존재 자체를 통과·가설 입증으로 세지 않는다.

| ID | 개념 | 상태 | 현재 범위 | 남은 작업 | 단계 |
|---|---|---|---|---|---|
| HCR-K01 | Dynamic Graph ↔ Compiled Circuit | implemented_scoped | 길이 2·3 path motif의 역할화·재사용과 오류 뒤 primitive 재확장. | 임의 graph 압축과 모든 상황의 비용 감소를 뜻하지 않음. | R0.2, R0.4 |
| HCR-K02 | Binding Continuity와 Node/Semantic/Role Identity | implemented_scoped | 관측 digest·revision·role의 결합 검사. B는 네 번째 A/D/M 축이 아님. | 학습된 의미 표현이 binding 성능을 높이는 인과 비교는 별도. | R0.2, EXP-04 |
| HCR-K03 | semantic vs opaque binding 실험 | partial | EXP-04 초안과 재명명/순서·stale-binding 검사가 존재. | 이름을 이해하지 않는 결정적 HCR에 의미 ID 효과를 억지로 만들지 않음. learned binder는 독립 조건. | EXP-04, R0.7 |
| HCR-K04 | primitive proof D와 runtime 비용의 분리 | implemented_scoped | proof depth와 expansion/tick/binding/proof 복원 카운터 분리. | 요구 D를 선택하는 LLM 실험과 D-expansion 정책은 같은 검증이 아님. | R0.2, EXP-09, R0.7 |
| HCR-K05 | 같은 kernel을 두 A 수준에 사용 | implemented_scoped | A0 feature/A1 relation에 같은 수치 갱신식을 적용하는 toy engine. | 다른 감각·인지 과제의 일반 재사용까지 검증된 것은 아님. | R0.2, EXP-05 |
| HCR-K06 | 낮은 A의 수렴 결과 → 높은 A의 node | partial | theory와 EXP-05에는 명시됨. 고정 feature/relation 구성이 실행 기반. | 수렴 결과 승격·근거 대응·되돌림을 가진 일반 cross-A contract 필요. | EXP-05, R0.6 |
| HCR-K07 | bottom-up / top-down recurrence | implemented_scoped | support/top_down links와 하위 activation 변화 시험. | 자동 cross-A 계층 생성이나 감각 왜곡 전부의 모델은 아님. | R0.2, EXP-05 |
| HCR-K08 | Candidate Competition / Inhibition | implemented_scoped | 같은 커널 안에서 복수 path 회로 후보가 경쟁. | 서로 다른 전문화된 M 처리기 또는 물리적 병렬 실행과 구별. | R0.2, R0.3 |
| HCR-K09 | Misconvergence와 수정 가능성 | implemented_scoped | 정상 학습 prior의 안정 오답, feedback 뒤 새 관측·재계산을 개발 fixture로 구현. | retention 재오답 원인은 미확정. 새 episode 일반화는 EXP-09에서 분리. | R0.2, EXP-03, EXP-09 |
| HCR-K10 | 다중안정과 시간 내 자발적 전환 | partial | 다른 초기 상태에서 두 attractor가 생기는 단위시험이 이미 존재. | 한 지속 trajectory에서 동일 입력의 전환·체류시간은 아직 별도 실험. | EXP-03, R0.5a |
| HCR-K11 | Decision Generation ≠ Explanation Reconstruction | partial | R0.1 독립 이벤트·시험 및 R0.2 값 계산 뒤 proof 재구성. EXP-06 초안 존재. | R0.2 별도 readout/explanation 시점·latency 기록 없음. 신규 reviewer는 기존 포함 관계만 분석. | EXP-06, R0.2.1 |
| HCR-K12 | 학습 = 구조 형성·강화·가지치기·재구성 | partial | path pattern 신규 등록·강화·약화·현재 routing 변경은 구현. | 일반 Fork/Join 및 회로 간 연결의 학습·pruning은 R0.4. | R0.2, R0.4 |
| HCR-K13 | 전문화 방법 회로 / M adaptation | planned | 현재 path 후보를 서로 다른 전문 처리기로 과장하지 않음. | 같은 총예산에서 policy·메시지·통합의 행동 차이 구현. | R0.3 |
| HCR-K14 | 지속 활성·readout·여러 시간 규모 | partial | settle(initial=...) 제공. 장기 memory와 기록은 존재. | 상태 전달 어댑터, session 생명주기, idle ticks/readout 및 학습 시간축 분리. | R0.2.1, R0.5a, B1 |
| HCR-K15 | 비지정 후보·기존 구조의 새 조합 | planned | 현재는 start/goal 도달성 계약. | goal=None만 허용하지 않고 program/readout/평가를 함께 분리. | R0.5b |
| HCR-K16 | A adaptation과 A/D/M 조합 | planned | 고정 A 수준의 존재와 적응 선택은 다름. | A 단독·두 축·세 축을 지원 정보/예산 통제하에 비교. | R0.6, R0.7 |
| HCR-K17 | 감각·개념·직관의 공통 계산 비교 | partial | 원 theory, EXP-05, 고정 두 수준 커널에 포함. | symbolic low/mid/high task adapter를 먼저 비교. 생물학적 시각/후각과 동일시하지 않음. | EXP-05, R0.6 |
| HCR-K18 | 오류 taxonomy | partial | Status·외부 평가에 관측 상태 일부가 있음. 신규 offline reviewer에서 현상만 표준화. | activation/binding/competition/over-compression/expansion 원인은 필요한 증거가 있을 때만 확정. | X-FAIL, R0.2.1 |
| HCR-K19 | 고정 자원 풀 + 가변 연결 | planned | 현재 CPU 자료구조를 물리 fabric 구현으로 세지 않음. | 자원 슬롯·지역 연결·재할당·용량 부족·ID 수명 계약부터 모델링. | B0, B2 |
| HCR-K20 | Physical system IS the network | planned | 가설의 최종 물리 구현 지향을 별도 backend gate로 보존. | 전압/전류/소자 dynamics 등 실제 소자 구현·학습성을 평가하는 후속 단계. | B2 |
| HCR-K21 | Plasticity/I/F 및 control/execution 분리 | partial | 소프트웨어 compiler/feedback/kernel의 역할 분리는 존재. | configuration과 local execution의 권한·통신·재구성 비용 계약이 필요. | R0.4, B0, B1, B2 |
| HCR-K22 | Sparse / local / event-driven / asynchronous | planned | append-only event trace는 이벤트 구동 계산이 아님. 현재 tick은 동기 전체 갱신. | 변경된 활성만 처리하는 backend 및 다른 스케줄의 오차·비용을 독립 대조. | B1 |
| HCR-K23 | External correctness와 내부 정합성 | implemented_scoped | reference 평가와 엔진 분리. stable/valid proof와 실제 가정 정확성을 별도 측정. | 가설 전체 입증과 기록 검산을 혼동하지 않음. | R0.2, 전 단계 |
| HCR-K24 | 회로 학습의 효율·간섭·유연성 대조 | partial | Familiarity/Novelty/Training3·9 fixture 및 비용·baseline 도구 존재. | 전역 가속·에너지·간섭·망각은 미측정. 임의 카운터 합산 금지. | EXP-01, EXP-07, EXP-09, R0.7, B1 |

## 원문 증거와 해석

원문에는 사용자의 발상, 이전 AI의 해석, 선행연구 요약이 함께 있다. 이 표는 해당 문서의 계산 개념을 보존하며 선행연구·뇌 메커니즘·사용자 역량 평가를 새 사실로 채택하지 않는다. 각 source의 절 제목은 원문에서 추적할 수 있고 상세 code/test anchor는 JSON에 기록된다.

- S01: `intuition_to_physical_neural_circuit_architecture-1(1).md` — SHA-256 `945220763f29848a9fc5e89382b1ea0397b600fb6f559cf2d88f455f37b53738`
- S02: `human_intuition_llm_neuromorphic_hypothesis_20260916(1)(1).md` — SHA-256 `e4bf787f4eb9d693c10bf3121eaa4134b9aec61a10fa365d79dc9097a1330c7a`
- S03: `AI_논문_핵심_및_실험결과_요약_2026-09-16(2)(1).md` — SHA-256 `046492e3c45c127d1c1b5588bf40a1d04b9b11e0cc478886b18efb6365898e7e`
- S04: `ADM_Circuit_통합가설_진짜혼합본_2026-09-16(1).md` — SHA-256 `c749bae59eb4bf761ebfde9587da548ca64ae91e62c18c6c2a384e46fc2ad5f4`
- S05: `직관_감각_착시_공통계산가설_2026-09-16(2).md` — SHA-256 `6c9b7a446d605527976b6713fcc7698abd6d02b598ad79b2699f715a14c3c2a5`
- S06: `계층적_수렴_회로_통합가설_감각_착시_ADM_2026-09-16(2).md` — SHA-256 `fa8aaa32675d1f6ee427b5072e8372d71c86ab635b6afd84fdbec0b89d9fefd5`

## 이번에 바로잡은 판단

EXP-04/05/06 및 공통 primitive·cross-A 가설은 처음부터 저장소의 theory/claims/experiments에 있었다. R0.1 Decision/Explanation 이벤트와 초기값별 두 안정점 단위시험도 존재한다. 이를 통째로 누락으로 세지 않는다. 미구현은 일반 계층 승격·지속 switching·R0.2 독립 설명 시간계측 등 구체적인 나머지다.

R0.2의 D adaptation은 dependency search 전개 정책이다. 기존 LLM 실험의 요구 proof D 선택 능력을 이것만으로 재입증하지 않는다. 같은 커널을 사용하는 것과 동일한 M 정책은 같은 뜻이 아니다.
