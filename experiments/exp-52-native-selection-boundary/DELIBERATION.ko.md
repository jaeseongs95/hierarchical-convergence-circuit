# R071 독립 설계 토론

## Executive Verdict

계약 검토자와 인과 검토자의 blind review 및 교차 검토로 threshold별 새 native memory를 구성하는 최소 설계에 조건부 합의했다. 연구 실행 성공이나 최종 감사의 판정은 아니다.

## Consensus Proposal

conditional_consensus: threshold 0.55/0.9940565651611166 각각의 empty memory에서 동일 positive training 세 개와 두 donor의 bound feedback을 실행한다. M0/M1를 새 세션 네 개로 평가하고 대응 checkpoint와 실제 reuse를 검사한다.

## Strong Consensus

threshold는 config signature에 포함된다. 기존 memory를 재서명하지 않는다. midpoint는 R070에서 도출한 post hoc 설계값이며 선택 분리와 판단 교정을 별도 측정한다.

## Material Disagreements

처음 검토한 R064 correction 이력 재생은 최소 목적에 필수적이지 않다. correction의 correct False feedback은 목표 circuit의 strength/balance를 추가 학습하지 않는다. 최소 recipe는 기존 R069 전체 memory의 재현이 아니라고 명시한다. 중대한 설계 이견은 남지 않았다.

## Decision by Axis

계약: config별 native lineage와 historical evidence를 보존한다. 인과: 같은 단계의 pool 관련 projection과 수치 궤적이 대응할 때 threshold eligibility 효과를 판정한다. M0/M1는 순수 strength 개입이 아닌 checkpoint bundle이다.

## Evidence

[구조화 기록](decision-record.json)은 실제 config signature, memory load, pool eligibility, feedback ID와 약화 조건에 근거를 연결한다. reviewer 출력 자체는 실험 증거로 세지 않는다.

## Required Actions

교차 검토에서 동일 donor episode ID가 feedback 중복 거부를 만든다는 조건을 확인했다. 서로 다른 donor ID를 사전에 동결한다. 실제 reuse·외부 오답·weaken·대응 checkpoint가 없으면 선택 가설을 판정 불가로 둔다.

## Optional Optimizations

관측 score sweep, 다중 회로 경쟁과 새 core 메커니즘은 이번 설계에 추가하지 않았다.

## Unresolved

특정 경계의 선택 민감도가 다른 입력에도 유지되는지는 측정하지 않았다. native 결과와 검산은 [결과](RESULTS.ko.md)에 별도로 기록한다.

## Method / Run Summary

MEDIUM, fork_turns:none의 blind reviewer 두 명, 각 한 번의 교차 검토, 재위임 없음. fresh Judge는 요구되지 않았고 추가 specialist·재숙고는 없었다. caller가 실제 모델·추론 수준을 관측하지 못해 NOT_OBSERVABLE로 기록했다. 보증은 partially_independent이며 플랫폼 격리의 외부 인증이 아니다. 초기 기록의 completed/reused 필드 충돌과 CLI 인코딩 실패를 validation에 보존하고 최종 record 검증을 통과했다.
