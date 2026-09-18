# EXP-30 / R049 — 역방향 신호 × 초기조건

## 결론

모집단: `research`. 48개 조건 중 기존 탐색 대조 16개, 새 조건 32개입니다.
ID 변형과 재실행은 독립 무작위 반복으로 세지 않습니다. 가설 지지와 장치 검증 통과는 별개입니다.
0.99 초기화는 모든 world에 같은 방식으로 주어진 실험 조건이며 실제 A 재사용·학습이 아닙니다.

## 관찰

| 강도 | 관계 | ID | 처리 | ticks | raw | 채택 | 분류 | D_DAG |
|---:|---|---|---|---:|---|---|---|---:|
| 0.02 | positive | identity | on_neutral | 88 | False | False | unsupported | 2 |
| 0.02 | positive | identity | off_neutral | 37 | False | False | unsupported | None |
| 0.02 | positive | identity | on_high | 64 | True | True | correct | 2 |
| 0.02 | positive | identity | off_high | 42 | False | False | unsupported | None |
| 0.02 | positive | fresh_ids | off_neutral | 37 | False | False | unsupported | None |
| 0.02 | positive | fresh_ids | on_high | 64 | True | True | correct | 2 |
| 0.02 | positive | fresh_ids | off_high | 42 | False | False | unsupported | None |
| 0.02 | positive | fresh_ids | on_neutral | 88 | False | False | unsupported | 2 |
| 0.02 | mixed_negative | identity | on_high | 146 | False | True | correct | 2 |
| 0.02 | mixed_negative | identity | off_high | 41 | False | True | correct | 2 |
| 0.02 | mixed_negative | identity | on_neutral | 88 | False | True | correct | 2 |
| 0.02 | mixed_negative | identity | off_neutral | 36 | False | True | correct | 2 |
| 0.02 | mixed_negative | fresh_ids | off_high | 41 | False | True | correct | 2 |
| 0.02 | mixed_negative | fresh_ids | on_neutral | 88 | False | True | correct | 2 |
| 0.02 | mixed_negative | fresh_ids | off_neutral | 36 | False | True | correct | 2 |
| 0.02 | mixed_negative | fresh_ids | on_high | 146 | False | True | correct | 2 |
| 0.1 | positive | identity | on_neutral | 54 | True | True | correct | 2 |
| 0.1 | positive | identity | off_neutral | 43 | True | True | correct | 2 |
| 0.1 | positive | identity | on_high | 30 | True | True | correct | 2 |
| 0.1 | positive | identity | off_high | 42 | True | True | correct | 2 |
| 0.1 | positive | fresh_ids | off_neutral | 43 | True | True | correct | 2 |
| 0.1 | positive | fresh_ids | on_high | 30 | True | True | correct | 2 |
| 0.1 | positive | fresh_ids | off_high | 42 | True | True | correct | 2 |
| 0.1 | positive | fresh_ids | on_neutral | 54 | True | True | correct | 2 |
| 0.1 | mixed_negative | identity | on_high | 49 | False | True | correct | 2 |
| 0.1 | mixed_negative | identity | off_high | 36 | False | True | correct | 2 |
| 0.1 | mixed_negative | identity | on_neutral | 47 | False | True | correct | 2 |
| 0.1 | mixed_negative | identity | off_neutral | 35 | False | True | correct | 2 |
| 0.1 | mixed_negative | fresh_ids | off_high | 36 | False | True | correct | 2 |
| 0.1 | mixed_negative | fresh_ids | on_neutral | 47 | False | True | correct | 2 |
| 0.1 | mixed_negative | fresh_ids | off_neutral | 35 | False | True | correct | 2 |
| 0.1 | mixed_negative | fresh_ids | on_high | 49 | False | True | correct | 2 |
| 0.92 | positive | identity | on_neutral | 33 | True | True | correct | 2 |
| 0.92 | positive | identity | off_neutral | 32 | True | True | correct | 2 |
| 0.92 | positive | identity | on_high | 26 | True | True | correct | 2 |
| 0.92 | positive | identity | off_high | 25 | True | True | correct | 2 |
| 0.92 | positive | fresh_ids | off_neutral | 32 | True | True | correct | 2 |
| 0.92 | positive | fresh_ids | on_high | 26 | True | True | correct | 2 |
| 0.92 | positive | fresh_ids | off_high | 25 | True | True | correct | 2 |
| 0.92 | positive | fresh_ids | on_neutral | 33 | True | True | correct | 2 |
| 0.92 | mixed_negative | identity | on_high | 32 | False | True | correct | 2 |
| 0.92 | mixed_negative | identity | off_high | 32 | False | True | correct | 2 |
| 0.92 | mixed_negative | identity | on_neutral | 28 | False | True | correct | 2 |
| 0.92 | mixed_negative | identity | off_neutral | 28 | False | True | correct | 2 |
| 0.92 | mixed_negative | fresh_ids | off_high | 32 | False | True | correct | 2 |
| 0.92 | mixed_negative | fresh_ids | on_neutral | 28 | False | True | correct | 2 |
| 0.92 | mixed_negative | fresh_ids | off_neutral | 28 | False | True | correct | 2 |
| 0.92 | mixed_negative | fresh_ids | on_high | 32 | False | True | correct | 2 |

## 실패 경계 — 동시에 여러 항목이 참일 수 있음

| 조건 | raw 오판 | edge/관측 충돌 | proof 구성 실패 | proof 지지 충돌 | 채택 거부 | 예산 종료 |
|---|---|---|---|---|---|---|
| t0000 | True | True | False | True | True | False |
| t0001 | True | False | True | False | True | False |
| t0002 | False | False | False | False | False | False |
| t0003 | True | False | True | False | True | False |
| t0004 | True | False | True | False | True | False |
| t0005 | False | False | False | False | False | False |
| t0006 | True | False | True | False | True | False |
| t0007 | True | True | False | True | True | False |
| t0008 | False | True | False | False | False | False |
| t0009 | False | False | False | False | False | False |
| t0010 | False | True | False | False | False | False |
| t0011 | False | False | False | False | False | False |
| t0012 | False | False | False | False | False | False |
| t0013 | False | True | False | False | False | False |
| t0014 | False | False | False | False | False | False |
| t0015 | False | True | False | False | False | False |
| t0016 | False | False | False | False | False | False |
| t0017 | False | False | False | False | False | False |
| t0018 | False | False | False | False | False | False |
| t0019 | False | False | False | False | False | False |
| t0020 | False | False | False | False | False | False |
| t0021 | False | False | False | False | False | False |
| t0022 | False | False | False | False | False | False |
| t0023 | False | False | False | False | False | False |
| t0024 | False | False | False | False | False | False |
| t0025 | False | False | False | False | False | False |
| t0026 | False | False | False | False | False | False |
| t0027 | False | False | False | False | False | False |
| t0028 | False | False | False | False | False | False |
| t0029 | False | False | False | False | False | False |
| t0030 | False | False | False | False | False | False |
| t0031 | False | False | False | False | False | False |
| t0032 | False | False | False | False | False | False |
| t0033 | False | False | False | False | False | False |
| t0034 | False | False | False | False | False | False |
| t0035 | False | False | False | False | False | False |
| t0036 | False | False | False | False | False | False |
| t0037 | False | False | False | False | False | False |
| t0038 | False | False | False | False | False | False |
| t0039 | False | False | False | False | False | False |
| t0040 | False | False | False | False | False | False |
| t0041 | False | False | False | False | False | False |
| t0042 | False | False | False | False | False | False |
| t0043 | False | False | False | False | False | False |
| t0044 | False | False | False | False | False | False |
| t0045 | False | False | False | False | False | False |
| t0046 | False | False | False | False | False | False |
| t0047 | False | False | False | False | False | False |

## 사전 가설 전체 판정

| 강도/관계 | ID | 처리 | 가설 | 상태 |
|---|---|---|---|---|
| 0.02/positive | identity | on_neutral | H_adoption_safety | supported |
| 0.02/positive | identity | off_neutral | H_off_edge_alignment | supported |
| 0.02/positive | identity | off_neutral | H_adoption_safety | supported |
| 0.02/positive | identity | on_high | H_adoption_safety | supported |
| 0.02/positive | identity | off_high | H_off_edge_alignment | supported |
| 0.02/positive | identity | off_high | H_adoption_safety | supported |
| 0.02/positive | fresh_ids | off_neutral | H_off_edge_alignment | supported |
| 0.02/positive | fresh_ids | off_neutral | H_adoption_safety | supported |
| 0.02/positive | fresh_ids | on_high | H_adoption_safety | supported |
| 0.02/positive | fresh_ids | off_high | H_off_edge_alignment | supported |
| 0.02/positive | fresh_ids | off_high | H_adoption_safety | supported |
| 0.02/positive | fresh_ids | on_neutral | H_adoption_safety | supported |
| 0.02/mixed_negative | identity | on_high | H_negative_high_raw | supported |
| 0.02/mixed_negative | identity | on_high | H_adoption_safety | supported |
| 0.02/mixed_negative | identity | off_high | H_off_edge_alignment | supported |
| 0.02/mixed_negative | identity | off_high | H_negative_high_raw | supported |
| 0.02/mixed_negative | identity | off_high | H_adoption_safety | supported |
| 0.02/mixed_negative | identity | on_neutral | H_adoption_safety | supported |
| 0.02/mixed_negative | identity | off_neutral | H_off_edge_alignment | supported |
| 0.02/mixed_negative | identity | off_neutral | H_adoption_safety | supported |
| 0.02/mixed_negative | fresh_ids | off_high | H_off_edge_alignment | supported |
| 0.02/mixed_negative | fresh_ids | off_high | H_negative_high_raw | supported |
| 0.02/mixed_negative | fresh_ids | off_high | H_adoption_safety | supported |
| 0.02/mixed_negative | fresh_ids | on_neutral | H_adoption_safety | supported |
| 0.02/mixed_negative | fresh_ids | off_neutral | H_off_edge_alignment | supported |
| 0.02/mixed_negative | fresh_ids | off_neutral | H_adoption_safety | supported |
| 0.02/mixed_negative | fresh_ids | on_high | H_negative_high_raw | supported |
| 0.02/mixed_negative | fresh_ids | on_high | H_adoption_safety | supported |
| 0.1/positive | identity | on_neutral | H_adoption_safety | supported |
| 0.1/positive | identity | off_neutral | H_off_edge_alignment | supported |
| 0.1/positive | identity | off_neutral | H_adoption_safety | supported |
| 0.1/positive | identity | on_high | H_adoption_safety | supported |
| 0.1/positive | identity | off_high | H_off_edge_alignment | supported |
| 0.1/positive | identity | off_high | H_adoption_safety | supported |
| 0.1/positive | fresh_ids | off_neutral | H_off_edge_alignment | supported |
| 0.1/positive | fresh_ids | off_neutral | H_adoption_safety | supported |
| 0.1/positive | fresh_ids | on_high | H_adoption_safety | supported |
| 0.1/positive | fresh_ids | off_high | H_off_edge_alignment | supported |
| 0.1/positive | fresh_ids | off_high | H_adoption_safety | supported |
| 0.1/positive | fresh_ids | on_neutral | H_adoption_safety | supported |
| 0.1/mixed_negative | identity | on_high | H_negative_high_raw | supported |
| 0.1/mixed_negative | identity | on_high | H_adoption_safety | supported |
| 0.1/mixed_negative | identity | off_high | H_off_edge_alignment | supported |
| 0.1/mixed_negative | identity | off_high | H_negative_high_raw | supported |
| 0.1/mixed_negative | identity | off_high | H_adoption_safety | supported |
| 0.1/mixed_negative | identity | on_neutral | H_adoption_safety | supported |
| 0.1/mixed_negative | identity | off_neutral | H_off_edge_alignment | supported |
| 0.1/mixed_negative | identity | off_neutral | H_adoption_safety | supported |
| 0.1/mixed_negative | fresh_ids | off_high | H_off_edge_alignment | supported |
| 0.1/mixed_negative | fresh_ids | off_high | H_negative_high_raw | supported |
| 0.1/mixed_negative | fresh_ids | off_high | H_adoption_safety | supported |
| 0.1/mixed_negative | fresh_ids | on_neutral | H_adoption_safety | supported |
| 0.1/mixed_negative | fresh_ids | off_neutral | H_off_edge_alignment | supported |
| 0.1/mixed_negative | fresh_ids | off_neutral | H_adoption_safety | supported |
| 0.1/mixed_negative | fresh_ids | on_high | H_negative_high_raw | supported |
| 0.1/mixed_negative | fresh_ids | on_high | H_adoption_safety | supported |
| 0.92/positive | identity | on_neutral | H_adoption_safety | supported |
| 0.92/positive | identity | off_neutral | H_off_edge_alignment | supported |
| 0.92/positive | identity | off_neutral | H_adoption_safety | supported |
| 0.92/positive | identity | on_high | H_adoption_safety | supported |
| 0.92/positive | identity | off_high | H_off_edge_alignment | supported |
| 0.92/positive | identity | off_high | H_adoption_safety | supported |
| 0.92/positive | fresh_ids | off_neutral | H_off_edge_alignment | supported |
| 0.92/positive | fresh_ids | off_neutral | H_adoption_safety | supported |
| 0.92/positive | fresh_ids | on_high | H_adoption_safety | supported |
| 0.92/positive | fresh_ids | off_high | H_off_edge_alignment | supported |
| 0.92/positive | fresh_ids | off_high | H_adoption_safety | supported |
| 0.92/positive | fresh_ids | on_neutral | H_adoption_safety | supported |
| 0.92/mixed_negative | identity | on_high | H_negative_high_raw | supported |
| 0.92/mixed_negative | identity | on_high | H_adoption_safety | supported |
| 0.92/mixed_negative | identity | off_high | H_off_edge_alignment | supported |
| 0.92/mixed_negative | identity | off_high | H_negative_high_raw | supported |
| 0.92/mixed_negative | identity | off_high | H_adoption_safety | supported |
| 0.92/mixed_negative | identity | on_neutral | H_adoption_safety | supported |
| 0.92/mixed_negative | identity | off_neutral | H_off_edge_alignment | supported |
| 0.92/mixed_negative | identity | off_neutral | H_adoption_safety | supported |
| 0.92/mixed_negative | fresh_ids | off_high | H_off_edge_alignment | supported |
| 0.92/mixed_negative | fresh_ids | off_high | H_negative_high_raw | supported |
| 0.92/mixed_negative | fresh_ids | off_high | H_adoption_safety | supported |
| 0.92/mixed_negative | fresh_ids | on_neutral | H_adoption_safety | supported |
| 0.92/mixed_negative | fresh_ids | off_neutral | H_off_edge_alignment | supported |
| 0.92/mixed_negative | fresh_ids | off_neutral | H_adoption_safety | supported |
| 0.92/mixed_negative | fresh_ids | on_high | H_negative_high_raw | supported |
| 0.92/mixed_negative | fresh_ids | on_high | H_adoption_safety | supported |
| 0.02/positive | identity_vs_fresh | on_neutral | H_ID_native | supported |
| 0.02/positive | identity_vs_fresh | off_neutral | H_ID_native | supported |
| 0.02/positive | identity_vs_fresh | on_high | H_ID_native | supported |
| 0.02/positive | identity_vs_fresh | off_high | H_ID_native | supported |
| 0.02/mixed_negative | identity_vs_fresh | on_neutral | H_ID_native | supported |
| 0.02/mixed_negative | identity_vs_fresh | off_neutral | H_ID_native | supported |
| 0.02/mixed_negative | identity_vs_fresh | on_high | H_ID_native | supported |
| 0.02/mixed_negative | identity_vs_fresh | off_high | H_ID_native | supported |
| 0.1/positive | identity_vs_fresh | on_neutral | H_ID_native | supported |
| 0.1/positive | identity_vs_fresh | off_neutral | H_ID_native | supported |
| 0.1/positive | identity_vs_fresh | on_high | H_ID_native | supported |
| 0.1/positive | identity_vs_fresh | off_high | H_ID_native | supported |
| 0.1/mixed_negative | identity_vs_fresh | on_neutral | H_ID_native | supported |
| 0.1/mixed_negative | identity_vs_fresh | off_neutral | H_ID_native | supported |
| 0.1/mixed_negative | identity_vs_fresh | on_high | H_ID_native | supported |
| 0.1/mixed_negative | identity_vs_fresh | off_high | H_ID_native | supported |
| 0.92/positive | identity_vs_fresh | on_neutral | H_ID_native | supported |
| 0.92/positive | identity_vs_fresh | off_neutral | H_ID_native | supported |
| 0.92/positive | identity_vs_fresh | on_high | H_ID_native | supported |
| 0.92/positive | identity_vs_fresh | off_high | H_ID_native | supported |
| 0.92/mixed_negative | identity_vs_fresh | on_neutral | H_ID_native | supported |
| 0.92/mixed_negative | identity_vs_fresh | off_neutral | H_ID_native | supported |
| 0.92/mixed_negative | identity_vs_fresh | on_high | H_ID_native | supported |
| 0.92/mixed_negative | identity_vs_fresh | off_high | H_ID_native | supported |

## 해석·대안 설명

top-down OFF에서 메시지 수가 줄어드는 것은 실행 함수가 바뀐 직접 효과입니다. 같은 계산을 더 효율적으로 했다는 주장으로 합치지 않습니다.
중립 activation 0.5라도 AND형 prefix bias는 음수입니다. edge 부호 유지, goal 방향, proof 구성, 근거 지지, 채택을 각각 판단해야 합니다.
수렴은 정답이 아니며 채택 거부는 정답 수정이 아닙니다. 높은 초기값에서 양성 답이 나와도 음성 대조와 함께 해석합니다.
signal_ledger.csv는 모든 tick/group의 읽기 전용 분해입니다. masked_top_down_term은 실제 전송이 아니라 같은 기록 상태에서 계산한 비활성 연결 항입니다.
target_implied_by_native_update는 원자료 전후 값에서 역산한 목표값입니다. 별도 tanh 감사가 수치 정합성을 확인하며, ledger 생성은 실행기에 되먹임하지 않습니다.
self_competition_logit에는 자가흥분과 억제의 합이 들어갑니다. 현재 두 계수를 독립 기제로 분리했다고 주장하지 않습니다.

## 기존 탐색과 회귀

기존 탐색의 exact SHA256 비교: {False: 2, True: 14}
수치·이산 판단 회귀 비교: {True: 16}
prior_regressions.csv에 원래 SHA256 일치 여부를 그대로 보존하고, 전 tick 수치의 절대오차 2e-12 이내 및 tick·정지·부호·raw·채택의 정확 일치를 별도로 검사합니다. 해시가 다르다는 사실을 성공으로 바꾸지 않으며 raw/source 파일 무결성 해시는 완전 일치를 유지합니다. 기존 탐색값을 신규 독립 증거로 세지 않습니다.

## 다음 판별 질문과 현재 주장 범위

어떤 항이 edge·goal·proof 경계를 갈라놓는지 이 대조에서 확인하고, 이후 기존 재검토/session 구조와 연결합니다.
bias나 초기값을 결과에 맞춰 조정하지 않습니다. 이 단계는 자동 구조 수정, 학습, Graph 재확장, 고정 잠재 공간의 구현이 아닙니다.
D_DAG·ticks·검사 수·messages·wall time은 별개입니다. wall time에는 raw 기록 비용이 포함되며 전력·peak memory는 null입니다.
