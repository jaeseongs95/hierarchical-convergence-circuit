# R074 이후: gain bundle의 원인 분리가 필요할 때만 진행한다

R074에서 gain 4→1은 e:1과 c:0의 score 반응을 모두 키웠다. 기존 조건의 작은 evidence-only 효과와 포화 관련 설명의 연결은 제한적으로 지지됐지만, e0 drive도 같이 바뀌었다. c:0는 prior 0에서도 약 0.9934 이상의 높은 활성 영역을 유지했다. 같은 짧은 경로의 민감도를 반복 계산하는 것만으로 실제 학습·선택의 증거가 늘어나지 않는다.

이 confound를 분리할 가치가 있을 때만 다음 후보를 별도 동결한다.

1. prior 0, 한 checkpoint, 기존 program·initial·top_down·나머지 config를 고정한다. memory나 observation을 재서명하거나 core를 바꾸지 않는다.
2. e0 drive scale 4/1과 e1 drive scale 4/1을 2×2로 분리하고, 각 조건에서 e1 score 0.6/0.8/1.0을 비교한다. 12 evaluator 조건 중 동시 scale4/4와1/1은 R074의 기존 조건 반복이고, 혼합 두 조건만 새 개입이다.
3. e:0·e:1·p:0:0·p:0:1·c:0 상태와 baseline 차이를 따로 읽는다. e0 배경을 고정해도 e1 scale 감소가 score 반응을 키우는지, e0 배경 변화가 c0 효과 크기에 기여하는지를 예측으로 분리한다. top_down 역할이나 전역 안정성까지 검증했다고 해석하지 않는다.
4. 이는 native config 변경이 아니라 drive-level counterfactual이다. 실제 선택·learning·경쟁을 질문하려면 이 수식 연구와 별개의 native 계약이 필요하다. counterfactual 반복을 새 독립 표본으로 세지 않는다.

위 내용은 후속 후보이며 아직 실행하지 않았다. 이 toy program에서 더 세밀한 분해가 연구 판단을 바꾸지 않는다면 수식 분해를 여기서 닫고 다음 native 질문을 새로 정의한다.
