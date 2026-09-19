# EXP-32 결과 토론과 다음 판별 질문

## 1. Executive Verdict

R051 본 연구의 원자료와 독립 audit는 유효하다. 같은 edge 위치에서 비교해도
TD OFF는 단일-edge 강화 후 채택하고 ON은 보류하므로, EXP-31의 위치 혼재만으로
차이를 설명할 수 없다. 이는 고정 toy kernel의 개입 대비이며 일반적 인지 결론이 아니다.

## 2. Consensus Proposal

`conditional_consensus`: 결과를 보고하고 proof/support/adoption의 분리를 유지하는 데 합의했다.
다음 질문은 representation/index/binding과 feedback 기제를 분리하는 것이다.
검사 순서에는 이견이 있어 전원 합의로 표시하지 않는다.
Coordinator는 기존 core·audit 계약을 유지할 수 있는 배열/binding 불변성 대조를 먼저 권고하고,
그 뒤 동일한 사전등록 feedback mask를 각 edge 강화에 교차하는 기제 실험을 권고한다.
후속 소스와 실행은 이 문서에서 완료했다고 주장하지 않는다.

## 3. Strong Consensus

- hold/revision-only 수치 상태·궤적 동일: revision이나 fresh restart만의 효과는 이 조건에서 관찰되지 않았다.
- OFF의 두 강화는 모두 채택, ON의 두 강화는 모두 보류: 이진 채택에서는 위치 차이가 없다.
- 수치 상태·ticks에는 위치 차이가 있다. goal의 edge1−edge0 대비는 OFF +0.200130870699,
  ON −0.012833824338이다. 통계적 모집단 효과 크기로 읽지 않는다.
- ON의 충돌 2→1 감소는 support gap 해소가 아니다. valid proof와 관측 근거 충족은 별개다.
- identity 반전은 독립 표본을 늘리지 않는다. learning, circuit reuse, 센서 측정은 실행하지 않았다.

## 4. Material Disagreements

인과 검토자는 교차 반박 후 배열 순서 대조를 우선했다. 현재 불확실성을 기존 입력 계약 안에서
낮은 구현 비용으로 줄일 수 있다는 이유다. 기제 검토자는 feedback mask 실험을 우선했다.
배열 대조가 통과해도 TD 효과의 내부 원인을 설명하지 못한다는 이유다.

Coordinator 판단은 전자의 순서를 채택하되 후자의 한계를 유지한다. 먼저 불변성 검사를 하고,
이를 feedback 원인 규명의 대체물이나 새 scheduling 실험으로 포장하지 않는다.
후속 우선순위의 이견은 해소되지 않았으나 현재 연구 결과의 유효성에 관한 이견은 아니다.

## 5. Decision by Axis

| 축 | 판정 | 근거 |
|---|---|---|
| 실행 계약 | 충족 | 고정 4기준선·16기록, 직접 score 개입, retry/measurement 없음 |
| 원자료 검증 | 충족 | 상태 replay, proof/support/readout 검산, raw/source/bundle hash |
| TD 설정 효과 | 현재 조건에서 관찰 | 같은 slot·identity에서 OFF/ON 비교 |
| 위치에 따른 채택 차이 | 관찰되지 않음 | 각 TD 안에서 두 강화의 채택 결과 동일 |
| 위치에 따른 수치·비용 차이 | 관찰 | goal과 ticks가 다름 |
| 특정 feedback link 원인 | 미확인 | 전역 스위치가 4개 link를 함께 토글 |
| 배열/index 불변성 | 미확인 | R051 identity 대조는 path-order 배열을 유지 |
| 일반화·학습·HCC 전체 | 범위 밖 | 단일 구조·고정 강도·빈 memory |

## 6. Evidence

원자료 위치는 `HCR-Evidence/exp32/r051-20260919T133359Z-9c4b7efe66`이다.
`study/raw/r051-c000`과 `r051-c001`의 edge0/edge1,
`candidate.diagnostic.assumptions`, `candidate.readout`,
`packet.document.engine.pending.state`를 확인했다. c002/c003과의 identity 대비는
`analysis/audit.json.cross_case_comparisons`에서 검산됐다.

`src/hcr/dynamics.py:tick`은 동기 갱신이며 top_down=False일 때 해당 종류의 link를 건너뛴다.
`src/hcr/workspace.py:make_program`과 raw `r02_network`에는 다음 4개 역방향 link가 있다:
`p:0:0→e:0`, `p:0:1→e:1`, `p:0:1→p:0:0`, `goal→p:0:1`.
각 frontier에는 다음 edge 하나만 있으므로 배열 교환은 경쟁 후보의 scheduling 조작이 아니다.

교차 검토 ledger:

- C1, mechanism 제안 → causal 검토: 배열 대조의 저비용 장점에 동의, scheduling 해석은 제외.
- C2, Coordinator 질문 → causal 검토: 독립 seed 반복 권고 철회. seed 없는 결정론적 재실행은
  독립 증거가 아니며 초기 상태 변경은 별도 개입이다.
- C3, causal 제안 → mechanism 검토: feedback mask를 우선하되 두 강화에 같은 mask를 적용해야 함.
- C4, Coordinator 질문 → mechanism 검토: 배열 대조는 index/binding 불변성 검사로 한정.

Coordinator는 수치 대비를 audit 원자료에서 재계산했다. 검토자의 identity 설명 중 배열도
뒤집혔다는 표현은 frozen spec과 맞지 않아 채택하지 않았다. R051은 이름을 반전하되
start→goal 경로의 배열 순서를 유지한다.

## 7. Required Actions

이번 페이즈: 본 연구 실행·독립 검산·결과 토론·증거 보존 및 로컬 커밋으로 마무리한다.
다음 페이즈 제안은 별도 동결된 배열/binding 대조다:

- topology, edge ID, score, config, memory는 고정하고 observation.edges만 path/swapped 순서로 교차한다.
- identity 1종 × 배열 2종 × TD 2종의 4기준선에 hold/revision-only/start-adjacent 강화/goal-adjacent 강화를 둔다.
- 강화 대상은 raw array index가 아니라 구조 역할로 정한다. 총 16기록은 독립 표본이 아니다.
- 원 packet을 바꾸지 않고 독립 evaluator의 비교 투영에서만 edge ID/구조 역할을 대응시킨다.
  e:0/e:1 키를 그대로 비교해서 생기는 가짜 차이를 실제 동역학 변화로 세지 않는다.
- 경로/binding/proof/raw decision/채택과 수치 궤적을 함께 확인한다.
- role-aligned 결과가 같으면 이 입력에서 index 의존 설명이 약화된다. 다르면 먼저 binding/표현
  구현을 진단한다. 어느 경우도 단독으로 특정 feedback 원인을 확정하지 않는다.

다음 단계의 feedback 분리는 새 kernel/config 및 독립 replay 계약을 먼저 동결해야 한다.
결과를 보고 성공할 link만 끄지 않으며, 두 강화에 동일 mask를 교차한다.
국소 feedback과 계층 feedback 그룹 분리는 후보 설계이지 이번에 실행한 실험이 아니다.

## 8. Optional Optimizations

이번 페이즈에는 추가하지 않았다. both-score 강화, 강도 sweep, learned memory, 관계·길이 확대는
현재 질문을 더 넓히므로 별도 설계가 필요하다.

## 9. Unresolved

TD link별 매개 기제, 배열/binding 불변성, 다른 강도·구조·memory에서의 일반화는 미확인이다.
후속 검사 순서에는 관점 차이가 남아 있다. 원자료 동일 재분석이나 ID 반전을 독립 반복으로
계상하지 않는다. 에너지 효율은 미측정이다.

## 10. Method / Run Summary

independent-deliberation-panel을 사용했다. MEDIUM, degraded_ok, adaptive_review=bounded,
worker cap 기본 8 중 새 reviewer 2명만 실행했다. 인과/표본 해석과 기제/측정 적합성이라는
서로 다른 실패 관점을 배정했다. `/root/r051_causal`, `/root/r051_mechanism`을
fork_turns=none으로 시작했고, 두 첫 답변이 모두 끝난 뒤 각각 한 번 교차 반박했다.
재위임·파일 변경·새 연구 실행은 reviewer 역할에서 제외했다.

요청 모델은 두 reviewer 모두 gpt-5.6-terra, xhigh였다. 도구 반환이 실제 적용 모델을
별도로 확인해 주지 않아 적용 여부는 미확인이다. 독립성은 관찰 가능한 격리 요청과
순서에 관한 기록이지 provider 내부 격리의 증명이 아니다.
fresh Judge는 MEDIUM에서 필수가 아니고 별도 요청도 없어 사용하지 않았다.
Coordinator 통합이므로 assurance는 보수적으로 `partially_independent`로 기록한다.
specialist와 adaptive 재숙고는 실행하지 않았다. 토론은 연구 해석이며 실행기의 독립 audit를 대신하지 않는다.
