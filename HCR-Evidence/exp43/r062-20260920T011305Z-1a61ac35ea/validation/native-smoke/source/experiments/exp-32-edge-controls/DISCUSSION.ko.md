# EXP-31 결과 토론과 EXP-32 선택

## 1. Executive Verdict

EXP-31은 공개 score의 강도 변경이 일부 고정 조건에서 채택을 바꾸었다는 증거를 제공한다.
그러나 top-down ON이 회복을 막았다는 인과 해석은 식별되지 않는다.
TD OFF/ON과 조작한 slot0/slot1이 함께 달랐기 때문이다.

## 2. Consensus Proposal

상태: `conditional_consensus`.
후속 주 질문은 같은 구조 slot에서 TD를 비교하고, 같은 TD에서 slot을 비교하는 것이다.
4개 약한 ++ 기준선 × hold/revision-only/edge0/edge1의 16개 분기를 채택한다.
공용 revision-only의 조건은 native 측정·소비·선택 경로를 실행하지 않는 직접 score 개입이다.
이 조건은 소스와 호출 차단 테스트로 확인하며, 측정 프로토콜을 평가한다는 주장은 하지 않는다.

## 3. Strong Consensus

실제 재시작 비교는 c000–c003 네 조건이다. 나머지 20조건은 이미 채택돼 추가 실행이 없었다.
동일 입력과 revision-only의 4개 비교는 수치 상태·tick 궤적이 같았다.
강도 개입은 4조건 모두 상태를 바꿨지만 두 identity의 TD OFF만 채택으로 전환했다.
96개 branch는 독립 표본이 아니며 identity 두 쌍도 결정적 counterbalance다.
검산 통과는 provenance와 실행 계약의 검증이며, 혼재 요인의 제거 또는 이론의 입증은 아니다.

## 4. Material Disagreements

첫 쟁점은 '정답 채택'이라는 표현이다. runtime support는 외부 진실을 판정하지 않는다.
다만 audit은 사전 동결된 synthetic relation의 True와 채택값을 별도로 비교하므로,
'synthetic reference truth에 대한 정답 채택'이라는 제한된 표현은 타당하다.
현실의 정확성, 센서 정확도 개선, 학습 효과로 해석하지 않는다.

둘째는 대조군의 수다. 측정 요청·consume 경로까지 포함한다면 slot별 echo 2개를 두자는 의견과,
입력 변화만 비교한다면 공용 revision-only로 충분하다는 의견이 있었다.
최종 구현은 측정 경로를 배제한 직접 개입으로 좁혔다. target은 native 입력 객체로 전달되지 않고,
native가 받는 것은 observation·config·memory·switch와 고유 session ID뿐이다.
공용 대조군의 타당성은 이 구현 조건에 한정하며 일반적인 측정 시스템으로 확장하지 않는다.

셋째는 both와 강한 입력 대조군의 필요성이다. both는 총 강도와 변경 위치 수가 함께 바뀐다.
강한 ++는 EXP-31 c016–c019에서 모두 채택됐다. 이번에는 본실험 범위를 늘리지 않고
강한 입력을 구현 sanity test로만 사용한다.

## 5. Decision by Axis

| 축 | 관찰/판정 | 후속 조치 |
|---|---|---|
| 재계산 | 이번 결정적 조건에서 same-input/echo는 상태·궤적 동일 | 새 revision-only 대조 유지 |
| 내부 회복 | ON은 conflict 2→1이나 raw=False·support gap=1·채택 거부 | conflict와 채택을 분리 |
| top-down | 조작 slot·초기 실패 유형과 혼재 | 고정 slot × TD 완전 비교 |
| 위치/identity | OFF는 slot0, ON은 slot1; ID 반전에도 같은 패턴 | 구조 slot을 동결하고 ID 대칭 확인 |
| 비용 | echo 250 ticks, strength 326 ticks 추가 | 회복 수를 단일 효율 점수로 환산하지 않음 |
| 일반화 | 단일 chain·빈 memory·synthetic 조건 | 인지·AGI·학습·에너지 주장 제외 |

## 6. Evidence

근거 run: `r050-20260919T125611Z-1b3aab6370`.
`analysis/audit.json` SHA-256: `61ab8f4d21d0b9131620a180885eded4eb8c62817d21fb017c5865534cf01c74`.

| 사례 | TD | target | 초기 실패 | 강도 개입 후 |
|---|---|---|---|---|
| c000/c002 | OFF | slot0 | proof 구성 실패 | raw=True, proof valid, 채택=True |
| c001/c003 | ON | slot1 | support 충돌 | raw=False, proof valid, support gap=1, 채택=False |

OFF goal activation은 약 0.0173→0.7342, ON은 약 0.0117→0.0133이다.
ON에서는 강화하지 않은 e:0이 약 0.3859로 남았다. 이 관찰만으로 그 edge를
원인이라고 확정할 수 없으며, 반대 slot을 조작하는 개입이 필요하다.
근거 파일은 해당 run의 baselines/c000–c003, raw/c000–c003,
analysis/audit.json·trials.csv와 R050 worker.py·protocol.py다.

## 7. Required Actions

원자료, frozen spec, core 및 이전 release를 보존한다.
R051의 fixed-slot 개입, paired binding, revision·switch·memory, 비용 예약과
독립 상태/proof/support 재생을 검증하고 구현 검증과 본실험을 구분한다.
다음 소스 생성 요청에서는 validate-only를 실행하고 본실험은 미실행으로 남긴다.

## 8. Optional Optimizations

이번에는 없음. 추가 강도·관계·길이·both·학습·센서 경로는 별도 질문이 생겼을 때 설계한다.

## 9. Unresolved

반대 slot 개입의 결과, slot과 TD의 상호작용, 두 단일 강화 모두 실패하는 경우의 기제는 미확인이다.
고정 scope에서 얻은 결과는 그 밖의 문제·representation·memory·관측 정책으로 일반화하지 않는다.

## 10. Method / Run Summary

MEDIUM, degraded_ok로 causal/evidence와 design/contract 관점 2명을 새 컨텍스트에서 시작했다.
두 reviewer는 읽기 전용으로 원자료를 검토했고 구현은 coordinator가 담당했다.
토론 중 한 reviewer의 최초 응답 완료 전에 교차 쟁점을 전달했으므로 두 blind review가
완전히 분리됐다고 주장하지 않는다. 보증은 `partially_independent`이며 완전 독립 합의가 아니다.
C1(target/TD 혼재)을 design reviewer가, C2(최소 조건·both 제외)와 C3(정답 표현)를
causal reviewer가 교차 검토했다. material claim은 coordinator도 원자료와 코드로 확인했다.
MEDIUM에서 별도 Judge는 요구되지 않았으며 생성하지 않았다. specialist·재위임은 없었다.
reviewer 요청 설정은 각각 gpt-5.6-terra/xhigh, fork_turns=none이었다.
생성 응답은 작업 ID만 제공했으므로 모델·추론의 실제 적용은 unverified로 기록한다.
원시 reviewer 출력이나 내부 대화 대신 확인한 주장·반론·결정만 이 문서에 남긴다.
