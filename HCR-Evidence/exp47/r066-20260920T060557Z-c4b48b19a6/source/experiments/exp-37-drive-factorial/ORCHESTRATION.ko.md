# R056 작업 구성

기준 commit: `94745b23c03b7cc25cfa1311ecec33c487b09f2f`.
사용자 요청은 지정 작업을 참고한 한 턴 진행이며 현행 프로젝트 지침에 따라 push까지 포함한다.
R055 결과의 다음 판별 실험을 R056의 별도 계약으로 구현한다.

development-orchestration으로 상태 조사 → 조건 동결 → 구현 → 수치 검산 → 결과 해석 →
검증·통합을 구분했다. 기존 생성·검산 장치의 재사용이 중심이므로 이번 작업은 main이
직접 수행하고 서브에이전트는 생성하지 않는다. 모델 override도 없다.
검산의 독립성은 생산기와 분리된 수식 구현·별도 프로세스에 한정한다.
독립 연구자 검토, blind panel, 최종 Judge 감사라고 표현하지 않는다.

Ponytail 원칙에 따라 기존 numerical execute, 링크 mask, recurrence verifier, 출처 검증을
재사용한다. 과거 manifest를 변경하지 않도록 버전별 얇은 worker와 동결 pipeline을 둔다.
새 구현 범위는 R056 도구·진입점·EXP-37 설계/index·신규 evidence다.
기존 사용자 미추적 파일과 raw evidence는 보존한다.

수용 기준은 예상 가설의 성공이 아니라 동결 16행, R055 bridge 8개, 전 궤적 재계산,
단순차·상호작용의 방향 검증, 최초 실패 보존, 전체 회귀 1회와 manifest/bundle 무결성이다.
실험 전 새 연구 조건을 실행하지 않고 synthetic fixture로 변조·분기·대조 수식을 검사한다.
실행 결과의 상태·근거와 사후 토론은 별도 RESULTS.ko.md에 기록한다.
