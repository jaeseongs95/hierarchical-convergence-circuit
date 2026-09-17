# EXP-11 — R0.3 방법·메시지·예산 비교

[계약·설계](../../architecture/r03-methods.ko.md)와 [실행](../../docs/R03_USAGE.ko.md)을 따른다.

연구 질문: 같은 공개 입력/seed/primitive/kernel 아래에서 처리 정책·경로 힌트·계산 배분만 바꿀 때 실행 경로, 정답/보류, 비용이 어떻게 달라지는가?

주 비교: sequential, associative, fixed, adaptive. 판별 대조: fixed_no_messages, adaptive_no_messages.
각 조건은 standard 및 limited 총 상한 벡터를 사용한다. 세부 값은 설계와 plan.json에 함께 남긴다.

원자료: 각 worker packet의 events/transitions/engine, controller event chain. 파생물: summary 및 외부 assessment/audit.
최초 provisional 결과와 최종 보류를 합쳐 정답으로 처리하지 않는다.

fixed/no_messages 및 adaptive/no_messages는 메시지의 효과, fixed/adaptive는 스케줄 효과를 구별한다.
profile 자체는 primitive/macro와 BFS/DFS를 묶은 조작이다. 그 하위 변수까지 독립적으로 입증한 실험은 아니다.

사전 완료 gate는 데이터 보존·검산·자원 상한 준수이며, 효과의 방향은 완료 gate가 아니다.
