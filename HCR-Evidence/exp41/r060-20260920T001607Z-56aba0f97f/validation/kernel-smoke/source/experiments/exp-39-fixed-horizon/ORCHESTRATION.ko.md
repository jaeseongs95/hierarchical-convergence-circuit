# R058 오케스트레이션 기록

기준 commit: `82e152ef290d477ebce90bef700073745749a5ed`.
사용자의 “다음턴 진행해줘. 진행할땐 오케스트레이션 쓰고” 요청에 따라
development-orchestration의 작업 계약·현재 상태·수행 방식·통합 검증 절차를 적용했다.
R057의 다음 판별 실험을 R058의 새로운 continuation 계약으로 구체화한다.

## 역할과 의존성

main이 조건 확정·생산기 구현·검산기 구현·통합·결과 해석을 순서대로 수행한다.
서브에이전트는 사용하지 않는다. 기존 동결 인터페이스를 따라 순차 재사용하는 범위이며
사용자가 요청한 오케스트레이션을 다중 에이전트 위임과 동일시하지 않는다.
모델 override도 없다. 검산의 독립성은 다른 갱신 수식과 별도 프로세스에 한정하며
독립 연구자·blind panel·최종 Judge 감사라고 표현하지 않는다.

1. 조건: 12조건·512 horizon·marker 보존·대조 방향과 판정 기준을 실행 전에 고정한다.
2. 생산기: 기존 settle 결과를 보존하고 원래 tick 함수로 suffix를 실행한다.
3. 검산기: 기존 R057 검산기로 prefix를 재계산하고 독립 recurrence로 suffix를 확인한다.
4. 통합: synthetic 변조 검사와 smoke bridge 후 전체 회귀를 한 번 수행한다.
5. 연구·해석: 동결 12조건을 한 번 실행하고 raw에서 주장 범위와 다음 판별 실험을 정한다.
6. 전달: source/bundle/ZIP 무결성과 변경 범위를 확인한 뒤 커밋·병합·push·원격 확인한다.

Ponytail 원칙에 따라 수치 갱신식과 core를 수정하지 않고 기존 settle/tick·mask·검산기를 재사용한다.
새 기능은 종료 marker 뒤 continuation과 해당 궤적·비용 검증에 한정한다.
실행 성공은 persistence 여부가 아니라 동결 계약과 원자료·검산의 일치로 판정한다.
최초 실패·budget·oscillation은 후속 안정 상태로 숨기지 않는다.
필수 검증을 통과하면 추가 horizon 탐색이나 architecture 확장을 수행하지 않는다.
