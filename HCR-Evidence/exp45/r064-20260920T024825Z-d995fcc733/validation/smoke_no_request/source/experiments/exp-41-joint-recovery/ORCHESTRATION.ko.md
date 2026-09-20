# R060 오케스트레이션 기록

현재 main과 origin/main `b3fc168a4650851b5930964ac79fdaa8eb96cc27`,
R059 원자료·결과·후속 제안을 읽고 EXP-41을 선택했다.
상위 AGENTS.md와 사용자 제공 지침이 적용되며 대상 하위 override는 없다.

Agent Governance Suite orchestrator의 registry에서 관련 provider를 확인했다.
task-contract는 비정형 다음 턴 요청의 범위·수용 기준을 동결하기 위해,
change-scope-guardian은 기존 미추적 파일의 보존과 범위 확인을 위해 선택했다.
ponytail은 코드 구현, acceptance-evidence-validator는 완료 근거 대조를 담당한다.
각 provider priority는 50이며 task contract, Git 기준선, 고정 최종 대상과 evidence라는
선행 조건을 해당 단계 전에 확보한다. MCP workflow run 대신 설치된 스킬의 직접
스크립트와 development-orchestration의 순차 실행 절차를 사용한다.

계약 → 변경 전 기준선 → 최소 구현 → synthetic 검사 → smoke → 최종 회귀 1회 →
단일 연구 실행/별도 검산 → 해석 → 범위/수용 근거 확인 → Git 전달 순서다.
기준선 digest는 `2070eaacbbf1dd5744d95b0e14c434c6a7e89881c18ffb4b5e19880419efafe0`이다.
검증 artifact는 `HCR-Evidence/r060-validation/`에 보존한다.

동결 조건과 출처에 의존하는 순차 연구 add-on이므로 서브에이전트나 모델 변경은 없다.
독립성은 다른 수식과 별도 프로세스에 한정하며 독립 연구자 감사로 표현하지 않는다.
보안·권한·결제·데이터 손실·배포·전역 설정·공유 core 계약 변경은 없다.
kernel loop, 출처 replay, source freeze 및 회귀 harness를 재사용하고 새 의존성을 추가하지 않는다.
조건·성공 기준은 결과 방향과 무관하며 연구 실행 예산은 1회, 자동 retry는 없다.
사용자의 한 턴 요청에 포함된 일반 push 권한으로 원격 main 반영까지 수행한다.
