# R072 이후: uncertainty prior와 evidence drive를 별도로 재계산한다

R072에서는 e1이 0.6→0.8→1.0으로 증가할 때 prior가 줄었고 activation도 내려갔다. 1.0에서 두 checkpoint의 수치 pool가 같아졌다. 이를 단순 단조 evidence 효과로 예상했던 방향 예측은 틀렸으므로 먼저 같은 자료의 설명을 분해한다.

1. R072의 봉인된 config·M0/M1·pool program·initial state·top_down과 원자료 hash를 입력으로 고정한다. native 관찰과 동일한 수식 재생을 먼저 확인한다. 재분석은 새 native 실행·독립 표본이 아니다.
2. score 0.8을 고정 기준으로 쓰고, 각 score에서 evidence drive만 바꾼 replay와 uncertainty prior만 바꾼 replay, 둘 다 바꾼 관찰 대응 replay를 사전에 제한해 동결한다. 계산은 evaluator의 수식 counterfactual이며 observation/memory를 runtime에 수정·재서명하거나 실제 학습 증거로 쓰지 않는다.
3. checkpoint 차이를 읽는 prior 항이 1.0에서 0이 되는 경로, 각 단독 변경의 activation 방향과 결합 효과를 따로 판정한다. 모든 궤적을 native 출력과 같은 것으로 강제하지 않는다. 안정성·예산·측정 불가를 그대로 보존한다.
4. 원자료의 실제 선택과 counterfactual eligibility 분류, raw 판단과 설명을 구분한다. counterfactual pool 재생에 native expansions·decision cost를 임의로 붙이지 않는다. 에너지·memory 효율도 주장하지 않는다.

조건·예측·분해 및 검증 규칙을 다음 실행 전에 별도로 동결한다. 필요성이 드러날 때만 새 native score 구간이나 다중 회로 경쟁으로 진행한다. 이번 문서는 후속 후보이며 실행 결과가 아니다.
