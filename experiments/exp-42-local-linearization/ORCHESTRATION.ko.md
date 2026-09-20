# R061 실행 조정 기록

main/origin/main `5fcdbb3f44cfe14628a65971b3fe916b0169536d`와 R060 원자료·해석을 확인했다.
상위 AGENTS.md와 사용자 제공 지침을 적용하며 대상 하위 override는 없다.
레지스트리에서 task-contract(priority 50, 비정형 요청), change-scope-guardian
(priority 50, 기존 미추적 자료와 변경 범위), ponytail(priority 50, 코드 구현),
acceptance-evidence-validator(priority 50, 완료 근거 대조)를 선정했다.
선행 조건은 원 요청·적용 지침, 유효 계약, 변경 전 Git 기준선, 고정 최종 대상과 증거다.
MCP workflow run 대신 설치 스킬의 직접 스크립트와 development-orchestration의
순차 실행 절차를 사용한다. 별도 에이전트와 모델 변경은 없다.

계약 → 기준선 → 최소 구현 → synthetic 검사 → smoke → 최종 회귀 1회 →
단일 연구·별도 검산 → 해석 → 범위·수용 근거 확인 → Git 전달 순서다.
기준선 digest는 `a72c3329d3418c6f997bbc1b9e0acdd78f4df1d111cfc574954297d42545f3df`다.
기존 kernel loop·출처 replay·동결/회귀 harness를 재사용하고 새 의존성은 없다.
보안·권한·결제·데이터 손실·배포·전역 설정이나 공유 core 계약 변경은 없다.
일반 push는 사용자가 제공한 한 턴 진행 범위에 포함된다.
계약 검증 CLI의 최초 인수 형식 오류는 보존하고 --input으로 수정한 검증을 별도 기록했다.
