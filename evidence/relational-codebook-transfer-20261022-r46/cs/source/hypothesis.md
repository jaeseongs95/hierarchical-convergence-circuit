# 전체 연구 방향 재검토 — 2026-10-20 / R29

## 1. Executive Verdict

연구는 계속하되 **현재 학습 회로 구현의 효율 우위를 기본 전제로 삼는 경로는 보류**한다. 다음 중심 질문은 검증된 중간 구조가 실제 원계산을 대체하고, 그 효과가 학습·생성·검증·binding·실행의 총비용까지 이어지는가다. 최근 gate·상태 재사용 실험의 성공을 이 연결의 성공으로 세지 않는다.

HIGH 판정은 `conditional_consensus`이며 첫 과제는 **A-0: 구조적 공간 공유 기회32조건의 정적 판별**까지다. 실제 runtime 대체·속도·학습 효율은 이번 A-0의 결과가 아니다.

## 2. Consensus Proposal

현재 이론 문서와 과거 raw는 보존하고, 주장 상태를 다음처럼 구별한다.

| 큰 질문 | 누적 증거와 현재 경계 | 방향 |
|---|---|---|
| H01 공통 primitive | 같은 함수의 고정 수준별 실행은 구현 사실. 맞춘 전용 알고리즘 대비 필요성·우월성은 미검증 | recurrence·capacity·adapter 계약 후 재검토 |
| H02 cross-A 승격 | R19~23의 수작업 연결·문맥·근거/측정 경계를 관측. 자율 계층 형성·일반 의미 보존 아님 | 승격 packet의 유일 정보경로와 인과 대조부터 |
| H03 Graph→Circuit | 미리 정한 path motif의 형성·구조 재사용·expansion 감소는 관측. 최종 수치 판단은 남고 tick·총비용은 증가하는 조건이 반복 | 실제 원계산 대체 가능성부터 확인, 학습 효율 주장은 보류 |
| H04 재확장·수정 | fresh 정보 효과와 약화·재탐색은 구별됨. 같은 misleading 정보에서 수정 유지가 보장되지는 않음 | 새 정보·구조 학습·기억 효과를 분리한 계약이 있을 때 진행 |
| H05 직관/명시적 사고 | 작은 장치의 회로/graph 실행 양식. 인간·LLM 내부 기제 증거 아님 | 계산 가설로 유지 |
| H06 오수렴 | toy의 안정된 잘못된 답과 조기 종료·평형 거리를 구별할 근거 있음 | 생물학·착시의 동일 기제로 확대하지 않음 |
| H07 강도–수정성 | 과거 learned strength/version/failures 묶음과 kernel 자기이득은 다른 조작 | g0/hysteresis·선행 상태 생성비용·차별 예측 후 별도 검사 |
| H08 판단/설명 | proof·readout·경로 기록을 구별할 필요는 있으나 사후 설명 생성의 직접 증거는 부족 | 가설 유지, 현 결과로 확정하지 않음 |

가설 원문은 `theory/core-hypothesis.md`, `evidence/claims.yaml`이다. 이 표는 원문 상태를 덮어쓰는 registry 갱신이 아니라 후속 판단이다.

## 3. Strong Consensus

학습 회로의 구조 재사용, 같은 tick의 계산 공유, 이전 state 사용, exact-input cache, 종료 인증을 서로 다른 개입으로 관리한다. expansion 감소·tick 감소·CPU/wall·외부 정답·proof는 별도 축이다. 준비·학습·실패 복귀를 무료로 두거나 실제 없는 사용 수명을 가정해 이득을 만들지 않는다. 작은 개발 입력 반복을 독립 일반화 표본으로 세지 않는다.

R15의 장시간 합성 workload에서는 C1 전체시간 약7.99% 단축이 기술적으로 관측됐다. 이를 지우지 않되, 조건별2회이며 작은 symbolic 회로의 효율 증거로 이전하지 않는다. 모든 효율 연구가 실패했다는 결론도 근거가 없다.

## 4. Material Disagreements

네 후보가 검토됐다. A는 공간적 동일 row의 정확 공유, B는 learned pool/통상적 실행계획/primitive 비교, C는 kernel 자기 상태 이득의 좁은 H07 검사, D는 matched-task 공통 primitive 비교다. B는 기존 EXP25/26의 ON/OFF보다 새 대조가 될 수 있지만 동일 경험·후보 순서·fallback 계약이 먼저 필요하다. C는 작은 인과검사가 가능하나 자명한 hysteresis와 학습된 attractor를 혼동할 위험이 있다. D는 R19의 재실행과 구별할 recurrence·capacity·정보 우회 계약이 부족하다.

별도 판정자는 A의 **정적 기회 판별만 먼저** 선택했다. A/B/C의 실제 성능 우열과 최종 실행 순서에는 현재 합의가 없다. 다른 후보를 비용상 실패했다고 미리 판정하지 않는다.

## 5. Decision by Axis

| 축 | 실행 순서와 gate |
|---|---|
| A-0 기회 | 기존 생성기의4Program×고정8drive/initial에서 보존 충분조건을 두 방법으로 확인. 0기회면 그 경로 종료 |
| A-1 실제 대체 | A-0 양성 뒤 별도 계약. 최대64settles에서 fullstate·residual·controller·readout bit 대조와 실제 제거 연산 검증 |
| 총비용 | 생성·검증·복원·lookup·실행을 포함해 고정32query 비용 측정. 단회 시간값은 기술 관측, 불확실성 규칙 없으면 속도 판정 보류 |
| 학습 연결 | 대체 구조가 learner 산출물에 존재하고 실제 수명에서 학습 비용을 회수하는지 별도 확인. 연결 없으면 독립 compiler 연구로 한정 |
| 일반화 | 새 topology·revision·과제 family로 나갈 때 선택 정책/정보/capacity/adapter를 다시 맞춤 |
| 중단 | 국소 gate 튜닝·중복 비용분해·사후 조건 조정으로 음성 결과 구제, 합성 fault 추가를 실제 신뢰성 지식으로 확대하는 방식은 중단 |

## 6. Evidence

EXP25/26과 기존 EXP09 분석은 이미 pool/decision 비용과 최종 판단 재계산을 구별했다. EXP62~64의 실제 학습 회로는 구조 안전성과 expansion 감소에도 tick 증가·학습비용 미회수를 보였다. `SubgraphCompiler.extract`는 양성 proof의 연속 경로를 길이별 고정 motif로 만들며, `adaptive_network`는 macro 뒤에도 primitive 판단 Program을 만든다.

R24의 원래 수명 cross-settle exact hit0은 motif 재사용 기회가 없다는 뜻이 아니다. R25는 고정점 뒤 산술 생략, R26은 초기 state 선별, R27은 사후 인증, R28은 eligible Boolean 변환이다. 이 무학습 실험들을 H03 학습 가설의 다섯 번 연속 직접 검증으로 세지 않는다. R28의96대응은24개 개발 입력4반복이고 cold6 CPU는 reset7.235배/legacy4.997배였다.

claim별 원문 경로·SHA와 축 연결은 `decision-record.json`에 있다. 별도 Judge는 정제 dossier로 판정했으며, 원문을 직접 재검증한 것으로 표현하지 않는다.

## 7. Required Actions

첫 실행은 A-0만 수행한다. 네 Program은 chain2, shared_bypass, R19 lower/upper의 기존 생성기에서 만들고 전체 JSON·source SHA를 고정했다. 입력은 동일 양/음·중립·약한 동일 drive, 한 input의 비대칭·부호 반전·1ULP 차이·초기 state 차이의8조건이다. hidden truth·정답·이전 종료 state는 읽지 않는다.

source binding, level/goal 역할, bias/drive/initial bit, 원래 incoming 순서·중복 link·feedback을 포함한 충분조건으로 partition을 만든다. 다른 pair-elimination 검산기가 같은 규칙 내 closure와 maximality를 확인한다. 이 규칙 밖의 모든 의미적 동치를 찾았다는 주장은 하지 않는다.

전체600초·단계60초·worker1·retry0·native/학습/측정/benchmark0을 적용한다. A-0 양성은 A-1의 계약 심사 조건일 뿐이며 자동으로 native 실행이나 성능 채택을 시작하지 않는다. 상세 조건은 `design.ko.md`와 `proof.ko.md`에 있다.

## 8. Optional Optimizations

이번에는 threshold 사전 저장·cache 수명 확대·새 scheduler·새 학습 규칙·서버 증설을 추가하지 않는다.

## 9. Unresolved

실제 응용 workload와 수명, A-0의 공유 기회, runtime 동치와 실제 순이득, learner와의 연결, 공정한 과제 간 비교는 미검증이다. A-0 음성은 네 Program과 고정 입력·보수적 규칙의 범위를 넘어서 일반 H03/H01/H07을 반증하지 않는다. 문헌 신규성·일반 AI·인간·생물학·물리 에너지 주장은 하지 않는다.

## 10. Method / Run Summary

HIGH blind 검토4관점(구조·타당성·자원·전략), 비원저자 교차검토4건, 별도 fresh Judge1명이 완료했다. specialist/reserve·adaptive 추가는0이다. 요청 모델은 노출된 gpt-6.1-sol/xhigh이며 Terra 선호는 가용하지 않았다. 실제 provider 내부와 토큰 사용은 NOT_OBSERVABLE이다. `independent`는 관찰한 방향 토론 절차이며 구현 독립 감사나 provider 격리의 외부 증명이 아니다. 이후 구현·원자료 검토는 Coordinator가 수행한다.
