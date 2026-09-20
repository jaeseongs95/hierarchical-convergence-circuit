# R054 오케스트레이션·설계 토론

## 역할과 범위

사용자가 개발 오케스트레이션 스킬을 명시했다. main은 R053 후속의 조건·파일 경계를 정하고
producer/pipeline, 통합 실행, 결과 기록을 소유한다. r054_design은 읽기 전용 설계 검토,
r054_auditor는 audit.py와 tests/test_audit.py 구현만 소유한다. 공유 파일의 동시 쓰기는 없다.
생산기와 별도 numerical evaluator를 병렬 구현하면 독립 계산 경계를 유지하며 대기를 줄일 수 있어
분리했다. evaluator 구현자는 최종 독립 감사자나 fresh Judge로 세지 않는다.

core 변경·배포·권한·삭제·migration이 없는 append-only 연구 add-on이다.
고위험 release audit 대신 source pin, exact intervention·tamper tests,
독립 수치 재계산과 native provenance replay, 최종 core regression을 완료 기준으로 삼았다.

## 설계 토론과 결정

R053의 집합 상호작용을 개별 링크로 좁히는 2입력×6mask를 채택했다.
검토자는 두 입력 모두 유지하고 weak-edge 좌표를 startstrong=e:1, goalstrong=e:0으로
고정할 것을 권고했다. 개별 링크 제거 후 변화는 그 링크의 현재 조건 내 필요성만 판별하며
충분성·일반적 무관성·유일한 고리로 확대하지 않는다는 제한을 반영했다.

primary는 연속값 delta_goal, 보조는 delta_weak_edge다.
stable 종료와 0.5±1e-6 경계 규칙을 결과 전에 동결해 nonstable·경계 상태를 null로 남긴다.
검토자는 이 폭이 수치 오차 보증이 아님을 명시하도록 요청했다.
P1 약한 edge feedback 삭제→high, P2 강한 edge feedback 삭제→low의 예측을 유지하고,
P 내부 링크의 대조는 비방향 사전 대조로 기록했다. 결과에 맞춰 방향을 바꾸지 않는다.

## 재사용과 검증 분리

Ponytail 스킬에 따라 기존 R053 execute/read_network, verify_trajectory와
R052 native provenance 검산을 재사용한다. 과거 소스는 수정하지 않는다.
새 코드의 책임은 정확한 개별 링크 삭제, R053 anchor 결속, 조건부 endpoint 판정이다.
R053의 전체 실행을 다시 연구 표본으로 만들지 않으며 원자료 재검산은 새 독립 표본이 아니다.
원클릭 freeze/selftest/smoke/단1회 core regression/research/audit/bundle 순서는 유지한다.

## 모델·관측 기록

r054_design: requested model=gpt-5.6-terra, reasoning_effort=high,
fork_turns=none. 익숙한 후속 설계의 범위·해석 검토에 배정했다.
r054_auditor: requested model=gpt-5.6-sol, reasoning_effort=high,
fork_turns=none. 부모 자료 계보·새 mask·재계산·판정 계약의 통합 구현에 배정했다.
두 생성 호출에 두 인자를 모두 전달했지만 응답은 task_name만 노출했다.
actual=unverified이며 실제 설정 적용을 확인했다고 주장하지 않는다.
토큰·실제 비용 또는 절감률은 관측하지 않았다.

이는 독립 blind 2인 패널이 아니라 읽기 전용 설계 검토와 책임 분리 구현이다.
검토 의견은 source·spec과 대조하며 모델 이름을 채택 근거로 쓰지 않는다.
테스트·실제 실행 결과와 사후 토론은 RESULTS.ko.md와 봉인된 run receipt에 남긴다.

## 동결 전 구현 검토

읽기 전용 검토자는 삭제 이외 program 보존, 각 branch의 fresh initial=.5,
미측정 native 필드, 부모·anchor 변경 차단, 실행 순서와 retry 부재를 확인했고
필수 수정 사항을 보고하지 않았다. main도 별도 검산기 소스와 테스트를 확인했다.
신규 12개와 재사용 수치 검산 6개를 bootstrap 경로에서 실행해 18개 모두 통과했다.
선행 수동 `python -m unittest` 호출은 루트 hcr.py의 package shadowing으로 import가
실패했다. 원클릭이 사용하는 bootstrap의 source 경로 설정으로 해소했으며,
실험 재실행이나 연구 조건 변경은 없었다. 실제 frozen bundle 검증은 이후 smoke가 담당한다.
