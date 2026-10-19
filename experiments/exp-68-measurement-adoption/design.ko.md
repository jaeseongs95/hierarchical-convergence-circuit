# EXP-68 / r22: 새 측정의 채택 조건과 상호 지지의 한계

## r21 이후의 비중복 질문

r21은 새 측정의 요청 조건을 비교했다. 초기 primary 불확실성 조건은 aux가 만든 오답을 고쳤지만 반전 응답을 새 오답으로 채택했다. 이번에는 요청 조건을 그대로 고정하고 **받은 측정을 어떤 공개 근거가 있을 때 채택할지**를 비교한다. 회로·학습·요청 범위 확장이 아니라 measurement adoption wrapper의 기술 확인이다.

세 정책 모두 r20 gated 초기 추론 비용을 전부 지불한다. 첫 primary 수렴 상태가 `stable_ambiguous`일 때만 추가 측정을 요청한다. 안정된 primary 오답은 여전히 놓친다는 control을 남긴다. goal/category 정답·provider fault·hidden feature는 정책에 입력하지 않는다.

## 고정한 세 정책

| 정책 | 요청 조건 충족·예산 충분 시 행동 |
|---|---|
| no_query | 추가 요청 없이 초기 결과 유지 |
| single_contract | primary_sensor1회, r21 응답 계약을 통과하면 첫 측정으로 재추론 |
| corroborated | primary_sensor와 witness_sensor 각각1회, 아래 조건을 모두 통과할 때만 첫 측정으로 재추론 |

두 번째 정책은 r21의 단일 응답 채택에 해당한다. 세 번째 정책의 채택 조건은 (1) 두 응답 모두 허용 source·request hash·episode·다음 revision·f0/f1 topology/score 계약 일치, (2) acquisition_id가 다르고 공개된 root_measurement_ids 집합이 비중복, (3) 모든 feature score 절대값이0.8 이상, (4) 대응하는 feature별 부호가 일치하는 것이다. 0.8은 기존 r20 aux 강도 상수를 가져온 고정 규칙이며 새 데이터로 calibration하거나 최적화하지 않는다.

두 응답은 같은 episode의 revision1과 같은 f0/f1을 대상으로 한다. witness는 측정 채택의 근거로만 쓰며 score를 평균·합산하거나 inference evidence로 중복 주입하지 않는다. 채택 후 primary 두 score와 revision만 바꾼 새 입력으로 기존 r20 gated를 한 번 실행한다. context와 aux를 보존하고 aux revision을 새것으로 고치지 않는다.

corroborated는 예산을 예약한 후 두 응답을 모두 받는다. 첫 응답의 내용에 따라 witness 요청을 선별하지 않으므로 단일/이중 측정 비용 차이를 그대로 기록한다. 오류·부족한 근거·불일치 응답은 재추론 없이 분류와 관계를 보류한다. 요청 자체가 불필요하거나 예산 때문에 거부되면 초기 결과를 유지한다. acquisition/source/root 정보는 제공자의 **선언**이며 실물 인증이나 통계적 독립성의 증명이 아니다.

## 사전 고정한13개 입력

| key | 초기 상태/응답 조건 | 확인할 경계 |
|---|---|---|
| clear_A | 안정된 A, 두 제공자는 A | 모든 정책 요청 없음 |
| repair_aux_A | primary0/0, aux가 B 채택, 두 측정 A | 초기 불확실성 요청으로 aux 오답 교정 |
| missing_aux_A | primary0/0·aux 없음, 두 측정 A | 정상 측정 채택 |
| primary_flipped_A | 첫 측정 B, witness A, reference A | 상호 불일치로 잘못된 첫 측정 보류 |
| witness_flipped_A | 첫 측정 A, witness B, reference A | 올바른 첫 측정도 보류할 수 있는 손실 |
| both_wrong_A | 두 측정 B, reference A, root 선언은 서로 다름 | 함께 틀리면 상호 지지가 truth를 보장하지 못함 |
| declared_overlap_A | 두 측정 B, root 선언 겹침, reference A | 알려진 공통 근거를 재확인으로 세지 않음 |
| stale_witness_A | 첫 측정 A, witness의 이전 revision | witness 계약 실패 |
| no_information_A | 첫 측정은 새 revision에도0/0, witness A | 새 revision과 실제 정보 증가 구별 |
| weak_witness_A | 첫 측정 A, witness score +0.2/+0.2 | 약한 일치를 강한 근거로 채택하지 않음 |
| request_budget_A | 요청 예산1·feature2, 두 측정 A | 이중 요청은 제공자 접근 전에 거부 |
| feature_budget_A | 요청 예산2·feature3, 두 측정 A | 이중 feature 비용 예약 실패 |
| strong_primary_wrong_B | 안정된 A 입력, reference B, 요청하면 B 측정 | 이번 채택 과제로 요청 범위의 한계를 숨기지 않음 |

clear_A/strong_primary_wrong_B만 강한 입력1/.8·+context다. 나머지는0/0·−context이며 repair_aux_A에만 fresh aux−1이 있다. 명시하지 않은 예산은 요청2·feature4·추가 settle4다. relation reference는 category와 context의 일치 여부다. label은 감사 전용 reference.json에 둔다.

모두 합성 feature 제공자다. 각 실제 요청은 기존 World.measure를 한 번 호출하고 feature별 ±0.98 score를 얻는다. 이후 고정된 stale/no-information/flip/weak 변환을 적용한다. ±0.98은 실제 정확도98%가 아니다. 두 제공자 모두 같은 hidden feature 세계를 기준으로 하며 실제 센서 독립성·잡음 분포를 검증하지 않는다. both_wrong_A는 공개 선언의 분리가 동시 오류나 밝히지 않은 의존성을 배제할 수 없다는 반례다. 실제 의존 구조를 식별했다는 주장도 하지 않는다.

## 예산과 검산

13×3=39개 cell, 준비1·case39·audit1의41단계다. native settle 최대260회, World.measure 최대39회, 학습0·threshold 탐색0·자동 재시도0이다. 이 상한은 cell당 최대 초기4+재추론4회와 정책별 요청0/1/2의 보수적 합계다. 실제 호출 수와 사용한 추가 계산을 기록하며 상한을 사용량으로 보고하지 않는다.

single_contract는 요청1·feature2·재추론4회, corroborated는 요청2·feature4·재추론4회를 응답 접근 전에 예약해야 한다. 요청한 두 feature는 잘못되거나 정보가 없어도 요청당2단위를 부과한다. 실제 사용한 재추론 settle만 비용으로 세고 나머지 예약을 해제한다. 초기 비용·재추론 비용·전체 비용, 요청 수·합성 feature 단위·provider wall·전체 child CPU/wall·출력 bytes를 분리한다. 서로 다른 단위를 임의 환율로 합치지 않는다.

기존 별도 scalar 수식으로 초기와 재추론의 모든 tick·종료·판정·비용을 재생한다. 서버 절대오차0, 별도 호스트 보조 재생 절대오차1e-15·상대오차0을 PRE 고정한다. source 전후 hash·provider 응답의 별도 고정식·request/adoption binding·ledger·집계도 확인한다.

변조10종은 request gate·request revision·charge·response score·adoption action·request cap·unit cap·revision reservation·상위 tick·상위 program이다. 각 지정한 거부 사유까지 정확히 일치해야 한다. 상위 tick/program을 변조해 앞선 하위 trace hash가 가리는 문제를 피한다. request/unit/revision cap은 해당 full-record 검사보다 앞에서 실제로 거부되도록 순서를 고정한다.

추가로 pure preparation에서 전역 요청39/settle260 경계를 넘는 카운터를 각각 global_caps 함수에 직접 넣어 거부 사유를 확인한다. 이는 전역 감사의 모든 행을 변조한 통합 시험이 아니다. stage_violations는 nonzero rc일 때도 raw 크기 초과를 함께 반환하는 사례를 시험한다. 준비의 stub cell과 저장 r20 trace 재생은 새 실험 관측이 아니며, 실제 새 World.measure/수렴은 서버 case 단계에만 있다.

## r21 감사 반영과 남는 제약

원격 전용 `/home/mcpops/hcc-measurement-adoption-20261019-r22`에서 순차1·전체600초·stage60초, 부모 주소공간512MiB·개별 파일32MiB, 자식 주소공간512MiB·개별 파일16MiB를 적용한다. bootstrap이 timeout/run 부모에 제한을 걸고, 각 stage worker에 더 작은 파일 제한을 건다. 서버 준비와 result에 실제 적용된 resource limit을 기록한다. AS는 resident RAM 사용량의 측정치가 아니다.

stage는 정상/nonzero/강제 종료 모두 raw 합계 크기를 관측한다. nonzero rc와 raw128MiB 초과는 함께 기록/판정하며, 한쪽 실패 때문에 다른 크기 검사를 생략하지 않는다. raw128MiB는 stage 종료 후 검사이지 디스크 hard quota가 아니다. 부모도 제한되므로 큰 봉인/메타데이터 쓰기는 실패할 수 있다. SIGTERM 정리·실패 자료·봉인은 best effort이며 SIGKILL·저장장치 정지까지 보장하지 않는다.

bootstrap의 중요 조건은 assert 대신 명시적 예외를 쓰며 child PYTHONOPTIMIZE=0을 고정한다. private generator는 입력 작성 도구이고 재실행 금지다. 별도 prepared/ 코드 사본은 만들지 않는다. 패키지는 저장소의 정식 파일에서 한 번 만들고 source manifest·ZIP hash로 동결한다. 이후 수정이 필요하면 같은 run의 결과를 맞추지 않고 실패/새 계약으로 분리한다.

원자료와 source 전후 검사·봉인 ZIP SHA·실제 수신 범위를 보존한다. ZIP 서버 준비와 agent/기기의 실제 수신을 구별하며 마스킹된 자료를 원문으로 복구하지 않는다. 기존 src·r19/r20/r21 하네스와 과거 봉인은 변경하지 않는다. 새로운 유료 자원·서비스·권한은 만들지 않는다.

공개 근거의 조건부 채택이 어떤 오류를 보류하고 어떤 올바른 답을 잃는지 비교하는 실험이다. 품질 보존·금전 절감·신뢰도 calibration·학습 포함 효율·기억 유지·실제 센서 인증/독립성·일반화·자율 계층 학습을 주장하지 않는다.
