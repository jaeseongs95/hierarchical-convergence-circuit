# R071 이후: 선택 분리의 입력 범위를 확인한다

R071은 특정 threshold에서 선택을 분리했지만 오답은 유지했고 전체 kernel ticks도 같았다. 다음에는 새 core 메커니즘보다 기존 경계의 적용 범위를 확인한다.

1. 이번 native로 구성한 config별 M0/M1를 봉인된 입력으로 고정한다. threshold·memory signature를 변경하거나 재서명하지 않는다.
2. 입력 변화 후보는 e0=1.0을 고정하고 e1=0.6/0.8/1.0으로 사전에 제한한다. e1=0.8은 기존 조건의 반복이며 새 발견으로 세지 않는다. topology·identity·route_only·budget을 대응시킨다.
3. 각 score에서 threshold×checkpoint를 paired 비교한다. score는 uncertainty prior·evidence drive·decision 근거를 함께 바꾸므로 score 조건 간 차이를 순수 threshold 효과로 쓰지 않는다. 같은 score와 checkpoint의 두 threshold에서 pool 궤적 대응과 eligibility 분리를 판정한다.
4. 선택 분리가 사라지면 그 조건을 그대로 경계로 기록한다. 선택과 판단 교정·정수 비용을 별도 판정한다. 여러 회로의 경쟁과 선택 학습은 이후의 별도 질문이다.

다음 실험의 정확한 조건·예측·실패/측정 불가·원자료 hash는 실행 전에 별도 동결한다. 이번 문서는 후속 후보이며 새 실행 결과가 아니다.
