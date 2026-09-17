# R0.3.6 / EXP-17 — 입력 재표현과 native Graph 형성

## 결론과 이번 구현 범위

기준 커밋은 `28b1dea8a309df62bd89ac36e340cd904726a45a`이다. EXP-16은 EXP-15의 계산 상태를 고정한 채 native proof 보존·재구성·관측 지지 기반 선택을 비교했다. `irrelevant_missing/legacy/expanded_1`에서만 선택에 의한 회복이 나타났고 그 차이는 16개 사후 재표현에서 유지됐다. 입력부터 실제 Graph를 다시 생성한 결과는 아니었다.

이번 실험은 재표현의 적용 위치만 입력 단계로 옮긴다. 핵심 질문은 ‘동일한 의미를 가진 입력의 이름과 edge 배열 순서가 달라질 때, native 엔진이 어떤 경로를 제안·완성하고 어떤 proof를 채택하는가’다. 결과를 미리 회복/불변으로 정하지 않는다.

## 조건

EXP-15 동결 계획의 기본 입력 8개를 빠짐없이 사용한다. 두 판단 prior는 `legacy`와 `route_only`다. node alias, edge ID alias, edge 배열 역순을 각각 두 수준으로 조합한다. 총 `8 × 2 × 8 = 128`개의 새로운 native trial이다.

edge 배열 역순은 directed edge의 방향을 뒤집는 것이 아니다. 입력 serialization 순서만 바꾸고 endpoints와 score를 유지한다. episode ID와 revision도 유지한다. 완성 경로 순서와 activation은 입력에 존재하지 않으므로 사후 변환하거나 강제하지 않는다. 이들은 새 native 계산의 관찰 대상이다.

새 topology를 추가하지 않는다. 이번 8개 입력은 기존 과제의 paired 입력 재표현이며 128개 독립 과제가 아니다. 두 prior 조건도 통계적으로 독립된 128개 표본이라는 의미가 아니다.

## 실제 실행

1. EXP-15 `seed/6.json`의 memory를 같은 config로 읽어 복사한다. 새 학습은 하지 않는다.
2. 공개 observation만 재표현한다. 실행 adapter에는 world, 외부 정답, case 분류나 판별 가능성 지표를 주지 않는다.
3. 각 입력·prior 조합에서 `AdaptiveSession`을 새로 만들고 `begin/advance`를 실제 실행한다. 첫 readout 이전의 최대 advance는 64회다.
4. 첫 native 판단은 정상 `fork_readout`의 candidate로 보존한다. 준비된 계산 branch는 남겨 둔다.
5. 기존 R034 `SelectionFlow(arm='expand_only')`로 실제 추가 전개를 수행한다. 추가 advance 8회, kernel ticks 2,048, 관측 0회가 상한이다. 이 controller는 native 지지 출력이 나오면 종료하므로 모든 Graph를 끝까지 완성하는 실험은 아니다.
6. 첫 판단 및 실제로 발생한 후속 native readout 각각에 R035의 `native_saved`, `native_rebuild`, `support_first`를 적용한다. 세 정책은 동일한 해당 상태를 사용한다. 선택 결과는 앞 단계의 전개/종료 결정에 되먹임하지 않는다.

초기 예산이 끝나도 아직 running이면 `initial_budget_exhausted`를 기록하고 first candidate는 만들지 않는다. 이를 보류 답변을 수정한 사례로 세지 않는다. readout 수와 따라서 선택 비교 수는 실제 경로 실행에 따라 달라진다. candidate를 결과에 따라 골라 버리지 않는다.

## 검산과 측정

생성기와 검산기는 별도 프로세스다. seed의 과거 학습 계보, 새 native 초기 session, 추가 전개와 native candidate는 기존 독립 native auditor로 재생한다. 새 입력 재표현은 별도 구현으로 대응표·위상·score·순서를 확인한다. 각 readout 투영은 생산 projector 대신 R034의 독립 `source_view`로 재계산한다. proof DAG와 세 선택 정책은 R035 독립 auditor로 검사한다.

동일 상태의 `native_rebuild`가 원 proof와 다르면 evaluator disagreement로 중단한다. 반면 다른 입력 재표현에서 native 값이나 경로가 달라지는 것은 관찰 결과이며 실패로 숨기지 않는다.

다음 관찰을 구별한다.

- 전체 공개 정보에서 지지되는 양성 경로가 있는가, 답이 유일하게 결정되는가.
- 후보 pool에서 완성 경로가 **제안**되었는가.
- workspace의 `completed_paths`에 그 경로가 **완성**되었는가.
- 완성된 지지 경로가 activation 조건도 만족하는가.
- native proof가 그 경로를 채택했는가, support-first에서 같은 값의 출력이 회복되는가.

`gap label`은 위 관찰의 운영상 분류다. 특정 뉴런/학습 편향/해시 등 원인을 확정한 진단이 아니다. 원인 귀속에는 별도의 개입 실험이 필요하다. 특히 pool에 이미 제안됐지만 workspace에 완성되지 않은 경로를 ‘시스템 어디에도 존재하지 않았다’고 해석하지 않는다.

숨은 world 정확성과 공개 정보의 판별 가능성은 evaluator에서만 계산한다. `native_supported`라도 실제 world에서는 틀릴 수 있다. 정답과 검산 통과를 구별한다.

## 비용과 paired 비교

각 trial의 마지막 실제 native segment 누적 비용을 한 번만 집계한다. 첫·후속 readout에 들어 있는 누적 ticks를 모두 더하지 않으며, 세 proof 정책 또는 여러 world 수만큼 kernel 비용을 곱하지 않는다. 선행 6회 학습 비용을 새 실험에서 다시 실행했다고 기록하지 않는다.

native kernel ticks, 실제 advance 횟수, native proof 복원 노드, 선택기의 경로/edge 검사 및 새 proof 노드는 별도 단위다. native 재구성 내부 scan 미계측 값은 `null`로 유지한다.

첫 readout과 마지막으로 확보한 readout 각각에서 입력 표현별 raw 값, native/support 출력, 의미상 경로 집합/순서, 선택 proof, `D_DAG`, edge activation 차이를 비교한다. 분석용 역매핑은 원 native 기록이나 선택기 입력에 되돌려 넣지 않는다. 마지막으로 확보한 readout과 예산 종료 시점의 미완성 pending 상태를 혼동하지 않도록 종료 이유와 pending-ready 여부도 기록한다.

## 보존 및 실패

기존 `src/hcr` 62개 파일, 기존 R035 모듈, README, 기존 릴리스 manifest와 원 evidence는 변경하지 않는다. 버전 R0.3.6은 새 실험 도구의 버전이며 기존 native 패키지의 버전 문자열도 보존한다.

실행 전/후 소스 해시, 원 seed 및 입력 계획 해시, 각 trial raw, 정상 finish branch, 관측·memory digest, action stream을 남긴다. 새 run/plan/analysis 파일은 추가 전용이다. 실패 시 마지막 commit된 session과 최초 candidate, continuation의 partial evidence 및 오류 종류를 기록한다. 자동 retry, ID/parent 보정, 관측 추가, Git 변경은 없다.

## 이번에 구현하지 않은 것

상태에 따라 expand/observe/review/select를 자율 선택하는 통합 controller, 관측 신뢰도 학습, 새 topology 일반화, 장기 rigidity/재학습, 다계층 HCC 확장은 이번 실험에 넣지 않는다. 이 선택은 EXP-16의 동일 상태 결과와 입력 단계의 Graph 형성 효과를 먼저 분리하기 위한 것이다.
