# R075 이후: 수식 분해를 닫고 native 경쟁을 새로 묻는다

e0를 고정해도 e1 scale 감소가 score 반응을 크게 키웠고, e0 배경의 작은 기여와 상호작용도 확인했다. c:0는 계속 높은 활성 영역에 있다. 같은 단일 후보 수식의 scale·prior 조합을 더 반복하는 것으로 실제 선택·학습의 근거가 늘어나지 않는다. 이 분해는 여기서 마친다.

다음 native 후보의 질문은 **같은 목표에 두 회로가 유효하게 binding됐을 때, 한 경로의 공개 evidence score 변화가 실제 경쟁과 선택을 바꾸는가**다. 아직 동결·구현·실행하지 않았다.

1. 현재 native 계약으로 두 회로를 형성·검증할 최소 world와 memory recipe를 먼저 확인한다. 회로 존재, binding 성공, pool 진입을 원자료로 구분하고 정답에 맞춰 host가 ID·proof·memory signature를 수정하지 않는다.
2. 두 경로의 topology·identity·공개 observation 배열·memory·config·초기 상태·budget을 대응 조건에서 고정한다. 한쪽 evidence score만 동결한 값으로 조작한다. score와 함께 native uncertainty prior가 자연적으로 달라지면 joint 개입으로 기록한다. 이를 evidence-only 효과라고 부르지 않는다.
3. 최초 pool의 모든 candidate 상태, 경쟁/억제, eligibility, 선택 경로, proof/readout과 terminal adoption을 분리해 보존한다. 후보 선택 변화와 정답률·수렴·비용 변화도 따로 판정한다. 단일 후보 threshold 통과나 evaluator 궤적을 native 경쟁의 대체 근거로 쓰지 않는다.
4. 수용 기준은 장치·provenance·독립 검산에 두고 기대한 선택 전환을 통과 조건으로 요구하지 않는다. 전환이 없거나 budget이 부족하면 해당 조건의 음성·측정불가 결과를 보존한다. 결과를 얻기 위해 새 선택 정책이나 경쟁 메커니즘을 추가하지 않는다.

이는 새로운 native 질문이다. R075 원자료의 재분석과 구분하며, 별도 동결 설계가 완성되기 전에 실행 결과나 이론 지지로 기록하지 않는다.
