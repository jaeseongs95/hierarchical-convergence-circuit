# EXP-57 / R076: native 다중 회로 경쟁과 공개 score 개입

R075의 단일 후보 수식 분해를 마치고 새 native 계산을 실행한다. 질문은 같은 목표에 두 저장 회로가 연결될 때 한 경로의 공개 score가 후보 상태와 실제 선택을 바꾸는가다. 기존 core·선택 정책·경쟁 메커니즘은 수정하지 않는다.

## 동결 조건

기존 default config, route_only, top_down=True, 회로 형성 최소 3 episode, 초기 pool 상태 0.5를 사용한다. 서로 다른 이름의 길이3 positive chain 세 개를 train하고, 독립 world evaluator가 정확히 완료된 proof를 판정한 feedback만 native session에 전달한다. 길이2와 길이3 pattern이 형성됐는지를 별도로 검사한다. memory signature·ID·strength·proof를 host가 편집하지 않는다.

평가 world는 S→A→G와 S→B→C→G의 두 경로다. 모든 edge의 실제 passability는 True로 고정한다. 공개 입력의 e4(C→G) score만 -1, 0, 0.6, 1로 바꾸며 나머지 score는 1이다. 각 score를 동일 memory의 회로 ON/OFF 새 session에서 평가한다. topology·identity·edge 배열·episode/revision·config·memory·budget은 고정한다. 이는 noisy sensor 모델이 없는 authored input 개입이다.

두 pattern은 최초 pool에 세 후보를 만든다. 길이2 pattern의 완결 경로 [0,1], 길이2 prefix [2,3], 길이3 완결 경로 [2,3,4]다. prefix를 제거해 두 후보처럼 표현하지 않는다. 이후 pool·binding·frontier 변화도 그대로 보존한다.

각 session은 최대 16 advance와 5120 kernel tick이며 매 advance 전에 기존 실행기의 worst-case reservation을 적용한다. budget 종료·형성 실패·binding 실패는 별도 상태다. 같은 실행을 자동 retry하지 않는다.

## 예측과 수용 기준

두 저장 pattern과 두 goal-binding 후보가 실제 형성·진입할 것으로 예측한다. 공개 score 네 점에서 최초 선택 source/edge path가 달라질 것으로 예측하되 전환이 없으면 이 조건의 예측을 falsified로 남긴다. 형성·pool 계산·선택이 측정되지 않으면 not_evaluable다. 기대한 전환을 장치 수용 기준으로 요구하지 않는다.

모든 pool candidate의 prior·mismatch·state·eligibility, pairwise inhibition link와 최종 signed input, proposals·실제 expansion, proof/readout·terminal adoption, D_DAG와 각 정수 비용·pool/decision tick을 분리한다. wall time은 별도 관측이고 energy·peak memory는 null이다. 독립 검산 오차는 2e-12다.

score 변화는 evidence drive와 uncertainty prior를 함께 바꾸고 음수 조건에서는 mismatch도 바꾼다. 따라서 joint 개입이다. ON/OFF는 binding·pool·회로 reuse를 함께 바꾸므로 inhibition의 독립 인과 효과나 evidence-only 효과를 판정하지 않는다. 짧은 prefix와 길이가 다른 pattern의 구조 차이도 대안 설명이다.

## 실행과 주장 범위

`Run-HCR-R076.cmd`: source·plan/hash 동결 → 별도 합성 grammar self-test → native formation 3회와 독립 feedback → paired native evaluation 8회 → 원자료 저장 → 독립 journal·feedback·pool recurrence 재생 → 집계 검산·변조 거부 → 최종 core 회귀 1회 → bundle/ZIP.

조건별 새 native 실행은 11회다. deterministic authored world의 조건 대조이며 통계적으로 독립된 발견 표본은 0이다. synthetic self-test는 native 연구 실행에 합산하지 않는다. 전환·정답률·수렴·계산 비용은 서로 다른 결론이고 일반 HCC 우위·학습 효율·생물학적 메커니즘으로 확장하지 않는다.
