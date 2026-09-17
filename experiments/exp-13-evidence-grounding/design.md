# EXP-13 — 결측 dependency와 판단 근거 진단

## 연구 질문

기존 판단을 바꾸지 않고 각 proof 가정의 관측 상태·drive·binding을 추적할 수 있는가?
같은 원시 판단에 대해, 선택 proof의 지지에 따른 명시적 보류 정책은 전역 결측 차단보다
불필요한 보류를 줄이면서 식별 불가 확정을 제한하는가?

## 사전 고정 조건

- 3/6/9회 학습 memory. 빈 memory에서 9회 연속 학습하고 세 시점의 상태를 사용한다.
- legacy/route_only/graph_only 세 엔진 조건. 기존 R0.3.1 정책을 그대로 사용한다.
- 14개 공개 입력: 양/음 강한 관측, 양/음 약한 관측, 핵심 edge None/0,
  전체 None/0, 다른 경로의 None/0, 알려진 차단 뒤의 None/0, 두 경로 차단+결측,
  관측 방향 자체가 잘못된 noisy 대조.
- 126회 task inference, 별도 학습 9회. 같은 task에서 세 readout을 평가하므로
  378건의 정책 평가이며 이를 378회의 추론 또는 독립 표본으로 세지 않는다.
- 조건명·world·정답은 evaluation 전용이다. runtime/diagnostic/gate에는 공개 Observation만 전달한다.
- 각 task는 동결 memory에서 1회 실행한다. 추가 feedback·관측·retry 없음.
- 진단은 하나의 source task를 공유한다. 두 정책이 서로 다른 추론을 했다고 보고하지 않는다.

## 대조

| 정책 | 동작 |
|---|---|
| diagnostic_only | 원래 출력 유지, 지지 부족도 그대로 기록 |
| dependency_gate | 선택된 proof의 실제 가정이 방향성 계약을 지지할 때만 원래 출력 유지 |
| blanket_unknown_gate | 입력에 None/0이 하나라도 있으면 보류 |

동일 관측이지만 숨은 세계가 다른 사례를 한 추론에 여러 번 채점한다.
14개 입력 중 9개에 두 world를 붙인다. 엔진별 원시 판단의 world 평가는 총 207건이다.
세 readout을 합친 외부 채점은 621건이지만 신규 추론 수는 여전히 126회다.

## 평가와 판정 기준

형식적 proof 유효성, score 방향성 지지, 외부 정확도, sign 계약 아래 식별 가능성,
정답 출력률/보류율, unsupported commitment, unidentified commitment를 나눈다.

`withheld_identifiable_cases`는 해당 계약에서 식별 가능한데 보류한 입력의 수다.
모두 '정답을 잃었다'고 해석하지 않는다. 원래 판단이 틀렸거나 잘못된 proof를 선택한
경우도 포함되므로 source decision과 함께 읽는다.

핵심 결측에서는 보류가 늘어도 정답 개선이라고 부르지 않는다. 알려진 완전 경로 또는
모든 경로의 알려진 차단이 있는 경우에 결측 때문에 불필요하게 막히는지 따로 본다.
misleading_direction은 'support=True이면 항상 correct=True'라는 과도한 해석을 반증하는 대조다.

합의와 지지 부족은 별개다. legacy/route_only, route_only/graph_only, 세 조건 전체를
각각 비교하지만 이를 새로운 협력 추론으로 세지 않는다.

## 무결성과 완료 조건

raw packet을 먼저 저장한 후 진단·정책 view를 생성한다. 실패하면 FAILED.json과 먼저 쓴
원시 packet을 보존한다. 기존 폴더를 덮지 않는다. run이 완료돼야 manifest가 생긴다.

감사기는 기존 session/primitive 감사와 진단 규칙의 별도 구현을 사용한다.
source/plan, 빈 seed와 9회 feedback, 126개 조건, 모든 policy view, 충돌,
summary/CSV를 재검산한다. hash만 다시 계산한 위변조도 의미 검산에서 거부한다.

정책의 성능 우월성을 도구 통과 조건으로 만들지 않는다. 예상과 다른 결과도 원시 evidence로 남긴다.

## 범위 밖

실제 추가 관측·제약 하의 재계산·counterfactual proof 교체, learned repair,
부정 예외 회로, 회로 재배선, pool 성능 최적화, 지속 동역학, 인간 습관의 실증.
