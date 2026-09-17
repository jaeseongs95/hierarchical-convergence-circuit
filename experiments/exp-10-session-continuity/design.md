# EXP-10 — R0.2.1 Session Continuity

protocol: `exp10-r021-session-continuity-v1`. 성능 개선이 아니라 실행 방식의 의미 보존을 시험한다.
원시 근거 출발점: EXP-09 복구 후 기준 `docs/R02_EXP09_OBSERVED_BASELINE.ko.md`.

## 조건

| 축 | 고정 또는 비교 |
|---|---|
| 알고리즘 | 동일 R0.2 dependency·prior·학습·부정 coverage |
| 입력/정답 | paired arm마다 같은 공개 관측과 평가기 world |
| 초기 memory | main/no_reexpansion은 동일한 6회 positive 학습 문서; 나머지는 empty |
| legacy | 현재 AdaptiveEngine.infer 일괄 호출 |
| continuous | begin/advance/finish, 저장 없이 session 수행 |
| resumed | 각 begin/advance/finish/feedback/request_revision 후 실제 JSON save/load |
| 별도 프로세스 | CLI 계약시험에서 start 프로세스 종료 후 resume 프로세스 시작 |

main은 익숙한 구조, strong counterfactual, 긴 구조, 분기, weak conflict, same-score forced revision,
다음 약한 입력의 retention까지 7개 판단이다. unknown·budget(max_expansions=1)·no_reexpansion은 각각 1개 판단이다.
비교는 `(7+1+1+1)×3=30`회이며 seed 학습 6회는 별도다.

## 주평가

판단 ID·value·primitive proof·expanded paths·모든 정수 비용·설정·관측·memory 문서·engine event payload가 같아야 한다.
오직 `cost.wall_seconds`와 이 시간값에서 파생된 event hash chain만 팔 간 equality에서 제외한다.
각 개별 event hash chain 자체는 따로 검증한다. 다른 provenance 필드를 광범위하게 지우지 않는다.

기존 소스와 리팩터된 infer의 비교는 배포 작성 환경의 별도 baseline differential 검사로 수행한다.
EXP-10의 legacy는 이전 버전 파일을 import한 엔진이 아니라 현재 리팩터된 단일 infer 경로다.
이는 원래 알고리즘을 실험 폴더별로 복제하지 않기 위한 선택이다.

## 원시 검산

모든 session snapshot에서 독립 state/event replay를 실행한다. completed memory만 로드해 같은 답이 나오는 시험에 그치지 않는다.
복원한 frontier·binding·program·누적 비용·revision 권한까지 대조한다.
resume checkpoint의 journal과 event prefix가 해당 final state의 prefix인지 검사해 다른 세션으로 교체한 기록을 거부한다.
외부 world의 assessment/proof는 reference evaluator로 재계산한다. 결과의 source와 전체 inventory/hash를 검증한다.

## 관찰되어야 하는 기준 동작

- weak circuits 오답과 retention의 다른 부분회로 재선택을 그대로 보존.
- same-score forced revision의 graph-only 정답과 39 ticks 보존.
- 이미 계산한 pool/판단 tick을 resume 후 다시 세지 않음.
- unknown 입력의 보류, budget 소진, request disabled 조건을 보존.
- 최초 실패와 수정 판단은 모두 별도 행 유지.

## 거부 시험

반쪽 graph 변경, stale observation/revision/memory/program, 잘못된 expected_ref,
checksum을 재작성한 snapshot/counter/program 변조, event/transition 절단, 중복 feedback,
원본/기존 결과 덮어쓰기, symlink/junction, 완료 bundle 내 파일 추가를 거부한다.

## 해석

equivalent는 행동 보존을 뜻하며 correct·hypothesis_proved와 다르다.
보관한 전 상태와 전체 trace를 포함하므로 snapshot 비용이 작다고 가정하지 않는다.
IO/검산 비용은 checkpoint_io.jsonl로 분리되며 transactional deepcopy는 항목별 미계측이다.
실측 시간은 동일성을 요구하지 않고 유한성·음수 금지·파일 bytes 대응만 검사한다.
