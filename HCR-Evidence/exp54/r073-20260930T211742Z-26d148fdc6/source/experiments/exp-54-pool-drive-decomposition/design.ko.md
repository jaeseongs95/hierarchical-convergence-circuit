# R073 / EXP-54: evidence drive와 uncertainty prior의 수식 분해

## 문제와 이전 근거

R072에서 e1=0.6→0.8→1.0으로 증가할 때 pool activation이 내려갔다. 완전 양의 입력에서는 M0/M1 prior가 모두 0이고 pool 궤적도 같았다. 단순 evidence 방향 예측은 틀렸으며, [후속 지정](../exp-53-selection-input-range/NEXT.ko.md)에 따라 동일 원자료의 설명을 먼저 분해한다.

## 동결 조건

R072 봉인 bundle·source·raw manifest 및 필요한 원자료 hash를 고정한다. 기존 native 12개 관찰을 별도 재검산한다. 동일 pool program, fresh initial state(모든 group 0.5), top_down=True, config, M0/M1 checkpoint를 유지한다. score 0.8을 기준으로 e1의 evidence drive만 바꾸는 `evidence_only`, uncertainty prior만 바꾸는 `prior_only`, 둘을 함께 바꾸는 `joint`를 0.6/0.8/1.0 × 두 checkpoint에서 계산한다. 총 18개 수식 replay이며 0.8의 여섯 셀에는 중복 기준 계산이 포함된다. joint 여섯 replay는 기존 두 threshold arm의 12개 native pool 관찰과 대응한다.

prior는 `prior_gain × strength × balance × (1−|e1|)`다. e0=1.0, balance=3/4인 이 경로에서만 이 축약을 쓴다. evidence drive는 `evidence_gain × e1`이다. prior는 c:0, p:0:0, p:0:1에만 주며 goal drive는 기존처럼 없다. observation·memory·binding을 runtime에 수정하거나 재서명하지 않는다. 계산은 evaluator 수식의 counterfactual이다.

## 사전 예측과 측정

기준 대비 evidence-only의 activation 차이는 0.6에서 음, 1.0에서 양이다. prior-only는 반대 방향을 예측한다. joint는 기존 관찰의 재현으로 0.6 양, 1.0 음을 예측하며 새 발견으로 세지 않는다. 0.8에서는 세 조작의 차이가 0이다. prior-only와 joint의 1.0에서는 prior=0으로 M0/M1의 수치 입력과 궤적이 같아질 것으로 예측한다. 예측 실패는 수용 실패와 구분한다.

각 replay는 기존 residual/patience/margin/oscillation/max_ticks 규칙으로 자연 종료한다. stable_decision과 stable_ambiguous를 구분해 보존하며 둘 다 기존 pool 적격 판정의 stable 조건에 포함한다. oscillating 또는 budget_exhausted는 효과 방향·eligibility를 not_evaluable/null로 둔다. native 관찰과 맞추려고 tick이나 궤적을 강제하지 않는다. terminal activation의 결합 비가산 항은 `J−E−P+B`로 정의한다. 이는 종료 규칙까지 포함한 수식 효과이며 통계적 인과 추정치가 아니다. 수치 tolerance와 방향 tolerance는 실행 전에 명세로 동결한다.

## 검증과 비용 경계

조건 동결 → native anchor 검산·self-test → 수식 replay → 독립 수식/집계 검산·변조 거부 → 기존 core 회귀 1회 → hash/bundle/ZIP 검증 순서다. 두 번째 검산기는 별도 합산 순서와 positive/negative 수식으로 매 tick과 자연 종료를 다시 계산한다. 생산 runtime/dynamics/learning을 import하지 않는다. 한 tick 예산과 stable_ambiguous self-test는 장치 검증이며 연구 표본이 아니다.

counterfactual eligibility는 고정된 두 threshold의 수식 분류다. 실제 native selection, expansions, decision cost를 생성하거나 붙이지 않는다. formula replay ticks는 evaluator 반복 횟수이며 native kernel ticks 또는 효율 증거가 아니다. 새 native 실행·학습·feedback·독립 표본은 모두 0, 에너지·peak memory는 null이다. 단일 후보·짧은 toy 경로의 코드 수식 설명까지만 판정한다.

## 실행

`Run-HCR-R073.cmd`가 기존 Python 3.12+로 전체 흐름을 실행한다. 기존 evidence를 덮어쓰지 않고 `HCR-Evidence/exp54/r073-*`에 최초 실패·부분 자료·traceback과 로그를 보존한다. 자동 retry·설치·모델 변경·Git 조작은 없다. 기본 dispatcher는 유지한다.
