# R053 설계 토론

## Executive Verdict

조건부 B: 기존 core를 바꾸지 않는 frozen-network 수치 개입을 다음 단계로 선택했다.
native 채택 원인까지 이번에 측정한다는 주장은 제외한다. 새 연구 결과를 보기 전에 결정했다.

## Consensus Proposal

세 입력 × 두 feedback 집합의 2×2 factorial을 실행한다. source와 부모 bytes를 동결하고
기존 production kernel과 별도 numerical replay를 사용한다. full/off 여섯 bridge가 필수다.

## Strong Consensus

초기 두 독립 검토자는 native session mask 확장(A)을 권고했다. proof/support/adoption을
직접 관측할 수 있다는 이유였다. B만으로 native 채택·보류 원인을 주장할 수 없다는 점에는
처음부터 이견이 없었다. 정확한 directed link 집합, fresh 초기 상태, 독립 stop/counter 검산,
결과 기반 마스크 선택 금지에도 동의했다.

## Material Disagreements

쟁점은 이번 단계에 native 결과까지 필요한가였다. Coordinator는 protected_files의
src/tests tree pin 때문에 A가 기존 R050~R052 실행기의 호환 계약까지 바꾼다는 근거를 제시했다.
두 검토자는 교차검토에서 질문을 수치 수렴으로 사전 한정하면 B도 유용한 구성요소 분리이며
A는 native proof/adoption을 측정할 후속 단계에 필요하다고 권고를 조건부로 수정했다.
만장일치의 원래 권고가 B였던 것처럼 기록하지 않는다.

## Decision by Axis

인과 축: 고정 커널 내부의 집합 제거 효과·상호작용만 판별한다.
계약 축: 과거 native source 계보와 release를 보존한다.
측정 축: 상태·궤적·종료·kernel counter와 proof/support/adoption을 분리한다.
명칭 축: 두 번째 집합은 A1→A1이므로 inter-level 대신 path-internal을 사용한다.

## Evidence

- src/hcr/workspace.py make_program: support의 역방향으로 네 top_down 링크 생성.
- src/hcr/model.py Group.level: e는 0, prefix와 goal은 1. 이 level은 proof D와 다름.
- src/hcr/dynamics.py: 동기 갱신, 전역 top_down 분기, fresh 0.5, stable/oscillation/budget 종료.
- src/hcr/evaluation/audit.py independent_step: 생산 커널을 import하지 않는 별도 계산식.
- tools/r050_review_boundary/pipeline.py protected_files와 R051/R052 pipeline: src/tests tree pin.
- R052의 봉인 audit와 여섯 원본 execution: 새 spec에 정확 hash로 결속.

Coordinator는 위 소스와 R052 원자료 network/trace 구조를 직접 확인했다.
검토자의 의견 자체를 새 실험 결과로 세지 않는다.

## Required Actions

12조건 사전등록, 원본10파일 결속·원본6execution 재검산, 전체 마스크·수치·종료·counter 검산,
full/off bridge 6개, 결과의 native 관련 필드 null과 counterfactual 표식을 구현한다.
생산기는 부모 network 입력 외 결과에 따라 실행을 선택하지 않는다.

## Optional Optimizations

일반화된 mask API나 새 의존성은 만들지 않는다. 기존 I/O·실행 커널·core regression을 재사용한다.
이는 Ponytail 스킬의 최소 구현 선택이다. 검증·provenance는 축소하지 않는다.

## Unresolved

수치 변화가 native proof/support/adoption에 어떻게 연결되는지는 미해결이다.
개별 feedback 링크의 원인 역할, 다른 강도·초기 상태·topology와 학습 memory도 미측정이다.

## Method / Run Summary

MEDIUM 패널. 독립 blind Round1 두 명: r053_causal(인과 과장 실패),
r053_contract(실행·검산 누락 실패). 모두 fork_turns=none으로 별도 briefing을 받았다.
각자 완료 후 상대 주장과 protected-core 제약을 한 번씩 교차검토했다(T1/T2, 각1항목).
새 Judge 없이 Coordinator가 원자료를 확인하여 통합했으므로 assurance=partially_independent다.
결과 기반 재토론이나 정량 연구 실행은 설계 결정 전에 하지 않았다.

두 reviewer 생성 인자는 model=gpt-5.6-terra, reasoning_effort=xhigh였다.
후속 evaluator 구현 r053_auditor는 model=gpt-5.6-sol, reasoning_effort=high,
fork_turns=none으로 audit.py와 test_audit.py만 소유한다. main은 producer/pipeline을 소유한다.
구현 책임을 나누면 생산 규칙을 복사할 위험과 병렬 작업 대기 시간을 줄일 수 있어 위임했다.
이 구현자는 최종 독립 감사자로 세지 않는다.
세 생성 응답은 task_name만 노출하여 actual 설정은 unverified다. 전달값을 적용 확인으로
표현하지 않는다. 전체 토큰·비용은 관측하지 않았고 절감 수치를 주장하지 않는다.
