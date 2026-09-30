# R074 거버넌스와 전달 기록

사용자의 연구 계속 진행 요청과 직접 제공한 AGENTS 제8절을 권한 근거로 삼았다. 재부팅 PEER 공지와 ACK는 작업 승인으로 사용하지 않았다. 기준은 main `b11aaa04e896be9ef5a8452754ac18b51c672b35`이며, 기존 untracked 자료를 첫 변경 전 baseline으로 동결했다. local branch는 `research/r074-evidence-gain-sensitivity`다.

## 선택과 실행

`orchestrator`가 설치 registry에서 다음 provider를 priority 50으로 선정했다. 직접 로컬 스킬 흐름으로 연결하며 MCP guarded workflow 완료나 독립 에이전트 감사로 표현하지 않는다.

1. `task-contract`: R073 NEXT와 현재 사용자 지시를 EXP55 목표·범위·수용 기준 네 개로 연결했다. 계약의 구조·권한 출처·기준별 근거 계획 검증이 PASS다.
2. `change-scope-guardian`: 첫 저장소 변경 전에 baseline을 캡처했다. digest는 `4f9c35644a5e7e18e7dc62067e2f51a0346787d8f037613791685bec04d313f1`다. 구현 뒤 범위 판정은 `HCR-Evidence/r074-validation/scope-report.json`에서 확인한다.
3. `ponytail`: 기존 R073 evaluator recurrence, 별도 recurrence와 source chain, 부모 자료 검증, final regression·원클릭 구조를 재사용했다. core·historical evidence·기본 dispatcher·의존성을 바꾸지 않았다.
4. `blocker-diagnostician`: 최초 grid 순서 오류와 후속 goal 직접 drive 입력 오류를 각각 원자료로 확정하고 request digest·report 검증을 통과했다. 실험 조건을 바꾸지 않고 검증기 두 지점만 고쳤다. 실패한 입력 점검 뒤 이어간 두 번째 launcher는 source drift gate에서 막혔다. 실패 두 run과 부분 자료를 보존했다.
5. 수식 생산 → 독립 입력·recurrence·summary 검산 → 최종 core 회귀 1회: 성공 run의 24 궤적·R073 대응 6개·raw 변조 9개·summary 변조 5개를 확인했다. 602 회귀 중 599 pass와 기존 환경 skip 3개를 구분했다. source/input/bundle/ZIP 바이트 검증은 `delivery-verification.json`에 있다.
6. `acceptance-evidence-validator`: 실제 산출물의 파일 집합을 target digest로 고정하고 네 수용 기준에 직접 근거를 연결한다. 판정과 요청 artifact 결속은 `acceptance-report.json` 및 `acceptance-validation.json`에 저장한다.
7. `mutation-risk-preflight`: ordinary `git push origin main`의 정확한 원격 ref·현재 fingerprint·사용자 권한·검증된 변경 범위와 새 commit으로 되돌릴 복구 절차를 실행 직전에 연결한다. receipt가 READY여도 새 권한으로 해석하지 않는다.

하위 에이전트 요청이 없고 병렬 실행의 순이익을 확인하지 못해 직접 수행했다. core/보안/권한/데이터 손실/배포 변경이 없어 고위험 독립 감사는 선택하지 않았다. 현재 모델·추론 수준 관측값을 추정하지 않았다. 연구 보고서는 실험 결과의 해석이며 별도 한국어 산문 편집 요청은 아니다.

## 수용과 Git 전달의 경계

원클릭에는 Git 동작이 없다. 범위·수용·사전점검 통과 후 커밋, local main 병합, 완료한 local 작업 브랜치 삭제, 일반 origin/main push와 원격 반영 확인을 수행한다. 강제 push·태그·설치·배포·원격 브랜치 삭제는 실행 범위에 없다.

source/doc/index의 현재 변경은 staged whitespace 검사로 확인하고, 봉인된 evidence의 기존 CRLF와 Markdown hardbreak는 그대로 보존한다. 전체 evidence에 같은 whitespace 정책을 적용해 기록을 고치거나 검증 통과라고 주장하지 않는다. 되돌림은 primary patch의 reverse 적용 가능성을 읽기 전용으로 확인하고 raw evidence를 보존한다. 실제 restore를 실행한 것으로 표현하지 않는다.

수식 예측이 지지되는 것과 native 능력·학습이 개선되는 것을 구분한다. 성공 상태는 이번 장치와 증거 검증의 통과이며 이론 전체의 증명이 아니다.
