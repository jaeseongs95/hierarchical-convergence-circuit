# R069 독립 토론 기록

## Executive Verdict

두 blind reviewer와 별도 fresh Judge가 checkpoint·관측 내용·revision API 경로를 나누는 최소 비교를 승인했다. 구현 완료나 연구 가설 지지에 대한 판정은 아니다.

## Consensus Proposal

`consensus`: 회로 ON donor 1개, 피드백 전후 memory × stale/fresh 새 세션 4개, 동일 요청 packet의 정상 revision 2개를 실행한다. 조건과 예측은 실행 전에 동결한다.

## Strong Consensus

피드백은 memory 갱신과 revision 허가를 함께 바꾼다. revision은 회로 재사용을 끄므로 세션 비교를 순수 persistence로 부를 수 없다. 별도 authored truth로 피드백을 산출하고 실제 weaken 여부를 검사해야 한다.

## Material Disagreements

세션 지속이라는 최초 표현의 인과 범위가 너무 넓었다. 교차 검토 뒤 API 경로 차이로 제한했다. 새 세션과 revision의 configured gate는 ON이며 실제 circuit eligibility 차이를 공개한다. 남은 중대한 설계 이견은 없다.

## Decision by Axis

인과 해석은 checkpoint·score 내용·API 경로 비교로 한정한다. 계약과 최소 구현은 기존 실행·revision·독립 검산기를 재사용한다. 비용은 획득·전달·runtime request를 분리한다. no-candidate와 채택 판정 부재는 측정 불가로 남긴다.

## Evidence

직접 확인한 근거는 runtime.py의 feedback·request_revision·revision circuit gate, learning.py의 회로 약화와 metadata 갱신, R064의 native revision과 독립 prefix 검산, R068의 합성 단일 후보 원자료다. [구조화 기록](decision-record.json)에 주장별 locator를 연결했다. reviewer 출력 자체를 실험 증거로 세지 않는다.

## Required Actions

Judge가 발견한 no-candidate 변조검사 오류와 측정 불가를 반증으로 처리하던 경계를 실행 전에 수정했다. donor의 raw 오답과 True 채택 예측을 별도 판정한다. 실제 실행·원자료 보존·수식 검산·최종 회귀는 이후 수행한다.

## Optional Optimizations

추가 대조군, 다중 약한 edge 선택, 새로운 core 메커니즘은 이번 결정에 필요하지 않아 추가하지 않았다.

## Unresolved

피드백 정보만의 효과와 순수 persistence 효과는 현재 API에서 독립 조작하지 못한다. 이진 오답 피드백 자체가 정답 정보를 제공하므로 새 측정의 필요성이나 정보 최초 획득을 주장하지 않는다.

## Method / Run Summary

MEDIUM, blind reviewer 2명과 fresh Judge 1명, 재위임 없음, 주장 단위 교차 검토 1회. specialist와 추가 재숙고는 사용하지 않았다. 초기 reviewer는 사용자 모델 제한 추가 전 상속 설정으로 생성돼 실제 모델·추론 수준이 caller에 관측되지 않는다. 이후 fresh Judge는 gpt-6.1-sol/high로 생성했다. lifecycle은 기록상 독립이며 플랫폼 격리의 외부 증명은 아니다.

첫 DecisionRecord 검증은 필드 일관성과 lifecycle 표기로 실패했다. 원본을 별도 보존하고 fresh Judge를 포함한 최종 기록을 검증했다. 거버넌스 MCP bootstrap은 BINDING_REQUIRED로 시작되지 않아 설치된 스킬을 직접 실행했다. guarded MCP 완료를 주장하지 않는다.
