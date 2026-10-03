# EXP-58 / R077: 같은 길이의 두 완결 binding과 prior 없는 score 개입

EXP-57에서는 두 저장 pattern과 추가 prefix가 함께 경쟁해 최초 선택이 prefix와 긴 완결 경로 사이에서 바뀌었다. 두 완결 경로 사이의 전환은 관찰되지 않았다. 이번에는 길이 차이·prefix·uncertainty prior를 통제한 별도 native 실험으로 그 한계를 좁힌다. 기존 core와 선택 정책은 변경하지 않는다.

## 동결 조건

`pattern_lengths=[2]`, `prior_gain=0`을 형성 전부터 고정한다. 다른 config는 R076과 같다. 이름이 다른 positive 길이2 chain 세 개에서 native train과 독립 world feedback을 실행한다. host는 memory·ID·strength·binding·proof를 편집하지 않는다. 예상 산출물은 길이2 저장 pattern 하나다.

평가 graph는 S→A→G와 S→B→G다. 두 경로는 각각 edge slot [0,1], [2,3]이며 모두 길이2 완결 경로다. 실제 passability는 모든 edge에서 True다. e0·e2 score는 1, e1은 0.6으로 고정하고 e3만 0, 0.6, 1로 바꾼다. 각 score에서 같은 memory의 ON/OFF 새 session을 실행한다. topology·identity·배열·episode/revision·config·budget은 고정한다. 비음수 score로 mismatch=0을 유지하고 native pool의 prior=0을 독립 재계산한다.

회로 하나의 두 binding 후보를 서로 다른 저장 회로 두 개로 해석하지 않는다. prefix가 들어오거나 예상한 binding이 측정되지 않으면 construct 불충족으로 기록하며 후보를 제거하거나 memory를 고치지 않는다. ON/OFF는 pool·binding·reuse 전체의 개입이다.

## 예측과 측정

e3=0에서는 [0,1], e3=1에서는 [2,3]이 최초 circuit 선택일 것으로 예측한다. e3=0.6은 같은 score의 동률 대조이며 구체적 선택은 예측하지 않는다. score에 따른 최초 선택 전환이 없으면 해당 예측을 falsified, pool 형성·안정 상태·선택을 측정하지 못하면 not_evaluable로 둔다. 예측 성공을 장치 수용 조건으로 요구하지 않는다.

모든 pool 후보·binding·prior·mismatch·state·eligibility·두 방향 inhibition link, proposals와 실제 expansion, 최초 선택·최종 proof/readout·terminal adoption을 보존한다. `D_DAG`는 외부 proof DAG 깊이다. 정수 비용·pool/decision tick·wall time은 분리하며 energy·peak memory는 null이다. 독립 recurrence 허용 오차는 2e-12다.

## 실행과 검증

`Run-HCR-R077.cmd`: source·조건/hash 동결 → 별도 synthetic grammar self-test → native 형성 3회와 feedback → paired 평가 6회 → 원자료 저장 → 독립 journal·feedback·pool recurrence 재생 → 집계 재계산과 변조 거부 → 최종 core 회귀 1회 → 봉인 bundle/ZIP.

session별 상한은 16 advance, 5120 kernel tick이다. 기존 worst-case reservation을 적용하며 최초 실패·부분 로그를 보존하고 자동 retry를 하지 않는다. 새 native 연구 실행은 9회, feedback은 최대 3회, 독립 발견 표본은 0이다. 합성 self-test는 별도 검증 자료다.

## 해석 경계

이번 조건에서 선택 전환이 생기면 길이 차이·prefix·비영 prior 없이도 score가 실제 선택을 바꿀 수 있다는 제한된 근거다. R076과는 topology·학습/config도 달라 그 결과의 원인을 단독으로 확정하지 않는다. 후보 간 inhibition의 인과적 필요성·최적 scheduler·일반 HCC 우위·학습 효율·인간/생물학적 메커니즘은 판정하지 않는다. 결과가 없으면 해당 동결 예측을 수정하고 원자료를 보존한다.
