# R075 거버넌스와 전달 기록

현재 사용자의 계속 진행 요청과 직접 제공한 AGENTS 제8절을 작업·일반 Git 전달 권한으로 삼았다. 기준 main은 `dba07e5b855e74de52f5a654ba02cf94bbd6a7f2`이며 작업 브랜치는 `research/r075-drive-factorization`이다. 다른 세션의 현황판에는 R074 완료·실행 없음이 기록돼 있었으며 해당 기록을 새 권한으로 사용하지 않았다.

설치된 `orchestrator`가 registry의 priority50 provider를 선택하고 직접 로컬 스킬 흐름을 연결했다. MCP guarded workflow나 독립 에이전트 감사의 완료 근거로 표현하지 않는다.

1. `task-contract`: R074 NEXT를 현재 요청의 EXP56 목표·범위·수용 기준 네 개로 구체화했고 구조·권한 출처·기준별 evidence 계획을 검증했다.
2. `change-scope-guardian`: 첫 변경 전 baseline을 캡처했다. 동결 digest는 `10578b073696a6aa06a1574caab2f4a3d6f9a1ea71c547899cbd89f307863765`다. 기존 untracked evidence·launcher는 보존하며 이번 파일만 포함한다.
3. `ponytail`: 기존 evaluator와 별도 recurrence, 입력·source chain 검사, 원클릭·회귀·bundle 구조를 재사용했다. 새 core 메커니즘·dependency·native 실행을 추가하지 않았다.
4. 수식 생산 뒤 별도 입력·매 tick·수렴·집계 재계산, 여섯 R074 대응, raw9개·summary5개 변조 거부와 budget/ambiguity 경계를 검증했다. self-test·연구 replay·검산을 구분하고 자동 retry를 하지 않았다.
5. `change-scope-guardian`와 `acceptance-evidence-validator`: 현재 파일 집합·실제 근거를 고정해 범위와 수용 기준을 검사한다. Git 전달까지 포함한 마지막 기준은 실제 원격 반영을 확인한 뒤에만 최종 충족으로 기록한다.
6. `mutation-risk-preflight`: 일반 `git push origin main` 직전에 정확한 ref·현재 fingerprint·사용자 권한·복구 조건을 연결하고 receipt를 다시 확인한다. 원클릭에는 Git 동작이 없다.

하위 에이전트 요청이 없고 병렬 병목 감소·순이익이 확인되지 않아 직접 수행했다. core·보안·권한·데이터 손실·배포 변경이 없어 고위험 독립 감사는 선택하지 않았다. 독립 수식 검산은 구현자와 분리된 에이전트 감사 또는 외부 재현을 뜻하지 않는다. 연구 결과의 작성이며 별도 한국어 산문 편집 요청은 아니다.

최종 core 회귀와 byte 검증은 성공 run의 `validation/core_regression.json`, `HCR-Evidence/r075-validation/delivery-verification.json`을 따른다. 범위·수용의 기계적 판정과 요청 digest 결속은 해당 validation 디렉터리에 보존한다. 서명 commit·local main 병합·완료한 local 작업 브랜치 삭제·일반 push·원격 확인 결과는 Git 전달 evidence에서 확인한다. 강제 push·설치·배포·태그·원격 브랜치 삭제는 수행 범위가 아니다.

전달 검사의 첫 source 동일성 assertion은 실행 후 EXP-56을 추가한 색인과 봉인 당시 색인의 차이 때문에 실패했다. `blocker-diagnostician`에서 계산 소스 변경 없이 INDEX.json만 신규 항목을 추가했음을 직접 대조해 `CAUSE_CONFIRMED`로 판정하고 요청 digest 결속을 검증했다. 봉인 source/manifest를 다시 쓰지 않고 현재 색인의 추가 항목을 별도로 검증했다. 연구 실행이나 core 회귀를 반복하지 않았다.

후속 사용자 요청에 따라 저장소 밖 프로젝트 `D:/codex/AI논문/AGENTS.md`에 독립 환경 검증 시 Codex 클라우드 세션을 추가 확인 없이 생성할 수 있다는 권한을 두 문장으로 추가했다. 해당 파일은 Git 저장소에 속하지 않는다. 기존 문구·인코딩·줄바꿈 보존과 변경 전후 hash를 `project-instruction-update.json`에 기록했다. 이번 R075에서는 클라우드 세션을 생성하거나 외부 환경 검증을 수행하지 않았다.
