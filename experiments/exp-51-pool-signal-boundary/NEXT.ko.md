# R070 이후: 선택 경계의 민감도를 실제로 구별한다

R070은 약화 신호가 pool 수치까지 전달됐으나 기존 eligibility와 선택을 유지했음을 확인했다. 다음에는 core에 새 메커니즘을 추가하기 전에 선택 경계가 native 실행에서 달라질 최소 조건을 확인한다.

1. 먼저 activation threshold와 observation score가 memory의 config signature, kernel dynamics, mismatch와 최종 readout에 어떻게 연결되는지 확인한다. threshold만 바꾸기 위해 기존 memory의 signature를 host가 자동 수정하지 않는다.
2. 기존 관측의 두 activation 사이 구간은 후속 설계 입력이다. 동일한 kernel trajectory가 유지된다는 조건에서만 threshold 분리 예측으로 사용한다. 실제 조건·checkpoint·선택/판단 예측·성공/실패/판정불가 기준과 비용 단위를 실행 전에 별도 동결한다.
3. 기존 config 계약을 보존할 수 있는 observation score 비교도 대안으로 검토한다. observation을 바꾸면 activation 외에도 mismatch와 decision 근거가 함께 달라진다. 이를 순수 threshold 효과로 해석하지 않는다.
4. 최소 paired 조건으로 선택을 분리할 수 없으면 측정 불가로 남긴다. 여러 회로의 경쟁, 순수 persistence와 자율 sensing은 별도 연구 과제다. R070의 재분석을 새 독립 표본으로 합산하지 않는다.
