# R069 이후: 약화 신호가 어디까지 전달됐는가

R069에서는 사용 회로 strength가 0.11에서 0.022로 바뀌었지만 새 세션의 stale 판단과 정수 비용은 같았다. 약화된 회로도 eligible=True로 다시 사용됐다. 다음에는 새 메커니즘을 추가하기 전에 이 경계를 확인한다.

1. 기존 raw packet의 M0/M1 pool network·drive·activation·mismatch·eligibility·선택을 독립 규칙으로 재계산한다. 관측·config·memory와 원본 hash를 유지한다. 재분석은 새 독립 표본이 아니다.
2. strength 변경이 pool 수치에 도달했는지, 수치는 바뀌었지만 같은 eligibility·선택을 유지했는지, route_only readout이 그 차이를 사용하지 않았는지 구별한다. 최종 state가 같다는 이유만으로 전체 계산 궤적이 같다고 판단하지 않는다.
3. 수치 변화가 확인되면 threshold 주변에서 선택이 달라지는 최소 조건을 실행 전에 별도 동결한다. 목표는 선택 경계의 민감도이며 순수 persistence나 자율 sensing으로 확장하지 않는다.
4. 현재 단일 후보 조건으로 선택 경쟁을 측정할 수 없으면 측정 불가로 기록한다. 원하는 행동을 만들기 위해 memory를 자동 복구하거나 core에 메커니즘을 덧붙이지 않는다.
