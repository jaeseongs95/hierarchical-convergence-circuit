# R073 이후: evidence 효과가 작은 이유를 필요할 때만 구분한다

R072의 감소는 현재 pool 수식에서 prior 감소가 evidence 증가보다 크게 작용한 결과로 설명됐다. 같은 원자료의 재분석을 계속 늘려 새로운 독립 증거로 세지 않는다. native 학습·경쟁·판단 개선을 이번 결과의 후속 성과로 가정하지 않는다.

남은 제한된 질문은 evidence-only 변화가 작은 이유가 양의 evidence drive 포화 때문인지, prior 항과 이 경로의 배치 때문인지다. 이를 구분할 가치가 있을 때만 다음 수식 실험을 진행한다.

1. 이번 봉인 program·initial·top_down·checkpoint를 고정하고 evidence_gain=4(기존 조건)와 1(명시적 counterfactual)을 사전에 비교한다. 새 config가 실제 native memory signature와 호환된다고 간주하지 않고 evaluator 계산에만 사용한다.
2. 각 gain 안에서 e1=0.6/0.8/1.0의 evidence-only 차이를 baseline score 0.8과 비교하고, prior를 기존 값 또는 0으로 고정한 조건을 분리한다. e0/e1의 drive가 gain과 함께 바뀌는 config bundle임을 명시한다.
3. e:1과 c:0의 상태·수렴·방향을 따로 읽는다. 작은 activation 차이가 안정적으로 사라지는 것과 budget/oscillation으로 측정하지 못한 것을 구분한다. eligibility·native 선택·비용을 혼동하지 않는다.
4. gain 변화로 evidence-only 차이가 커지면 포화 설명을 제한적으로 지지한다. 그대로 작다면 경로·top_down·prior 배치 같은 대안을 남긴다. core 메커니즘을 결과에 맞춰 덧붙이지 않는다.

이 문서는 후속 후보다. 다음 실행 전에 범위·예측·실패 기준을 별도로 동결한다. 실제 행동이나 다중 후보 경쟁을 연구하려면 이 수식 분해와 별개의 native 실험 계약이 필요하다.
