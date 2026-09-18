# EXP-24 / R043 실험 설계

## 결론과 출발점

이번 산출물은 EXP23 후속 실험 장치이며 EXP24 실행 결과를 미리 제시하지 않는다.
EXP23의 ID-key scheduler 비용 역전을 출발점으로, ID ranking을 하지 않는 기존 input_order에서도
ID 재명명 효과가 남는지를 분리한다. 새 정책 학습·새 topology·회로 알고리즘은 추가하지 않는다.

## 고정 및 조작

기준선은 `eedb04f90f02cf3c55693d493d33db18f96a23b5`다. R042의 12개 입력 case와 evaluation world를
그대로 재구성하여 EXP23 frozen plan과 byte-semantic JSON 동치로 확인한다.

scope=`legacy`, arm=`online_support`, scheduler=`input_order`를 고정한다.
각 순열 내에서 edge-ID bijection만 조작한다. identity와 swap_SD의 vocabulary를 유지하며,
`e0↔e4`, `e1↔e5`, 나머지 `e2/e3/e6`는 고정한다. edge array slots, node ID, relation, score,
episode, revision, config, trained seed memory, 예산은 동일하다.
world의 key만 같은 bijection으로 옮기며 world·variant·inverse map은 실행기에 전달하지 않는다.
원래 parent_case 및 case family/cohort 명칭도 EXP23과의 정확한 입력 동치를 위해 유지한다.
새 실험 여부는 plan/raw/summary schema와 protocol ID로 구분한다.

순열은 SMD, SDM, MSD, MDS, DSM, DMS다. 각 순열에서 두 ID 배치를 모두 실행하며
배치 실행 순서는 순열 인덱스에 따라 번갈아 바꾼다. 총 12조건이고 반복 성공에 따른 조건 선별은 없다.
명시적 plan을 prepare에서 저장하고 소스·입력·이전 evidence checksum이 달라지면 execute를 중단한다.

## 가설과 사전 판정

H1(주 예측): 같은 배열 순열에서 ID 배치를 바꿔도 native ticks와 측정된 readout 궤적이 같다.
H2(대안): ID ranking 이외의 경로에 ID 의존성이 남아 있어 차이가 나타난다.
측정 범위 밖의 hidden state 동치나 전체 ID 독립성까지 주장하지 않는다.

pair의 tick이 다르거나 비교 가능한 readout 궤적이 다르면 `falsified_in_pair`다.
tick이 같고 readout 궤적도 같으면 `supported_in_pair`다. readout이 부족하고 측정된 반례가 없으면
`not_evaluable`다. 이 판정은 가설 결과이지 audit의 acceptance criterion이 아니다.
오답·abstention·정상 budget 종료도 원문 및 classification을 유지한다.

같은 tick/궤적이라도 outcome, 지원 signature, 완성 경로 inventory, scheduler slot 궤적,
scheduler/selector/기타 native count가 다르면 보조 차이를 따로 보고한다.
다른 배열 순열 사이의 spread는 기술통계이며 불변성을 요구하지 않는다.
이 6쌍을 독립 문제 12개 또는 모집단 일반화의 반복 표본으로 간주하지 않는다.

## 실행기와 검산 경계

기존 `r041_scheduler_direction.runtime.ScheduledTimingTrial`을 그대로 사용한다.
input_order는 frontier 첫 slot을 선택한다. 선택된 경로의 ID 로그와 inventory 검사는 유지된다.
새 독립 `policy_audit.py`는 생산 choose 함수를 호출하지 않고 선두 slot, raw ID 기록,
priority 호출 부재, 작업량을 재계산한다. ID 읽기 0을 기대하지 않는다.

기존 R041 native auditor가 state/proof/controller/scheduler를 독립 재생한다.
그 이후 R042의 evaluator-only inverse-ID 투영을 사용한다. 실행 raw/state/proof를 수정하지 않는다.
원문 hash가 투영 전후 같은지도 검사한다.

EXP22 input_order/legacy/online_support의 원문 6조건을 capsule에 포함하고 다시 독립 audit한다.
이와 EXP24 identity 6조건의 동일 입력 회귀를 검사한다. 새 ID 효과에 대한 기대값은 회귀 조건이 아니다.
EXP23은 원클릭 선행 단계에서 전체 verify하며, EXP24의 portable capsule에는 원래 manifest,
plan, audit 및 analysis manifest anchor만 넣는다. EXP24 audit가 EXP23 전체를 다시 재생했다고 표시하지 않는다.
EXP22 전체108 및 EXP23 전체24의 preflight verify와 EXP24 auditor의 EXP22 6조건 replay를 구분한다.

## 측정

D_DAG는 기존 독립 proof auditor가 계산한 inferential dependency depth다. ticks로 대체하지 않는다.
native ticks, native cost 필드, scheduler 작업, selector 작업, 실제 wall time을 별도 저장한다.
단위가 다른 count를 더한 효율 점수는 만들지 않는다. 에너지와 프로세스 peak memory는 null이다.
기존 native cost의 wall_seconds placeholder는 그대로 raw에 보존하되 실제 측정 시간으로 쓰지 않는다.

최종 support signature는 value, D_DAG, assumed_edges의 투영이다. 완성 경로 목록과 별도다.
이 signature 동치를 전체 proof DAG 또는 최소 goal-support DAG의 동치라고 부르지 않는다.
최소 proof DAG isomorphism은 이번 조작에 필수인 측정이 아니므로 구현을 확장하지 않고 null로 표시한다.

## 실패와 evidence

append-only raw/action stream, exclusive-create files, source/parent hashes, frozen plan을 보존한다.
logical outcome과 schema/graph-reference/binding/runtime/evaluator 오류를 구분하며
기존 auditor가 제공하는 세부 메시지와 traceback을 삭제하지 않는다.
실행기 자동 retry, ID 교정, prior 교체, proof 재선택, host terminal correction을 추가하지 않는다.
원클릭이 일부 실패해도 그 상태를 성공으로 처리하거나 후속 실험을 진행하지 않는다.

## 결과에 따른 다음 판단

모든 pair가 주 예측에 부합하고 보조 차이도 없다면, 이 조건에서 EXP23 효과가 ID-key scheduling과
연관된다는 설명을 강화한다. 차이가 남으면 최초 divergence를 기준으로 ID의 다른 접근 경로,
reference handling, 측정 투영을 조사한다. 두 경우 모두 결과를 보고 새 메커니즘을 자동 추가하지 않는다.
