# R077 이후 판별 후보

같은 길이·prior0 조건에서 score에 따라 두 완결 binding의 최초 선택과 proof가 바뀌었다. 동률에서는 두 activation이 같고 앞선 binding을 선택했다. 현재 미해결 사항은 topology/ID를 고정한 배열 순서 개입에서도 비동률 선택이 유지되는지다.

다음 최소 실험은 R077 봉인 memory·config·world·score를 그대로 쓰고 edge 배열 순서만 바꾼 paired native 평가다. 같은 의미 graph를 실제 edge ID로 대응하고 slot별 binding·pool 상태·후보 순서·최초 선택·proof/readout·비용을 함께 기록한다. 동률은 순서 민감도, 비동률은 evidence 우선 선택의 유지 여부를 구분한다.

이 문서는 후보 방향이다. 아직 구체적 배열·score 조합·성공/반증 기준을 동결하거나 새 native 실행을 하지 않았다. inhibition 필요성은 이 실험과도 별개다.
