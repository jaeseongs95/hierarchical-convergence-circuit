# EXP-65 / r19: 계산 대체 경계와 최소 cross-A 기술 확인

## 사전 결정

먼저 현재 공식 길이2 pattern program의 국소 전이를 회로 identity·현재 국소 state·동일 measurement만으로 대체하는 후보 하나를 검사한다. 이 후보는 외부/출력 경계 node의 현재 state를 키에서 제외한다. 동일한 내부 state와 측정에 경계 state .1/.9를 주고 기존 tick 한 번의 내부 출력이 달라지면 정확한 대체 후보를 기각한다. 이는 허용 state domain의 반례이며 실제 r18 궤적 도달성·모든 축약의 불가능성을 증명하지 않는다. 입력/출력만 같은 근사나 전체 state를 키로 한 cache와도 별개다. 후보를 억지로 보강하거나 같은 chain의 비용을 재측정하지 않는다.

기각 시 EXP05의 기술 전제로 이동한다. 하위 과제는 두 noisy feature와 수작업으로 명시된 A/B prototype의 분류, 상위 과제는 승격된 A confidence와 공개 context가 일치하는지의 XNOR 관계 판정이다. 두 과제는 서로 다른 함수이며 같은 hcr.dynamics.tick/settle과 동일한 kernel 설정을 쓴다. 별도 Program의 로컬 level0/1을 재사용하며 새 level2를 구현하지 않는다.

하위망은 feature 두 개→category goal, 상위망은 promoted/category와 context→match_A/match_B→relation goal이다. 모든 연결·bias는 공개 과제 문법으로 고정한다. adapter는 measurement에 evidence_gain을 곱하고 confidence를 [-1,1] drive로 선형 변환한다. 정답/hidden truth/case별 분기를 읽지 않는다. 상위 match_A−match_B를 gain1로 하위 goal drive에 한 번 보내고 하위와 상위를 재계산한다. 고정된 host orchestration이며 자율적인 계층 학습·스케줄러·새 회로 형성은 아니다.

## 입력·대조·측정

clear A/B, ambiguous A/B, misleading context, strong conflict의 6개 public input을 동결한다. ambiguous_B와 misleading_A는 같은 public input에 서로 다른 reference category를 둔다. 구별 정보가 없는 paired world이므로 둘을 모두 맞히는 예측을 하지 않는다. context의 유용성과 오류 전파를 함께 드러내는 정보 한계 대조다.

bottom_up은 하위→상위 두 settle, coupled는 동일한 첫 두 settle 뒤 고정 한 번 feedback·하위/상위 재계산, separate_algorithms는 공개 score 합+같은 gain의 context prior를 threshold로 분류하고 논리적 일치를 판정하는 수작업 수준별 기준선이다. 기준선은 학습/튜닝된 전용 kernel이 아니며 common kernel 우위를 입증하는 강한 baseline 비교가 아니다. native settle은 총36회, training0이다. cell마다 한 번이며 통계적 성능/일반화 실험이 아니다.

승격 packet은 전체 하위 결과 hash, public input hash, revision, 원 measurement IDs/scores, raw confidence·불확실성·adopted를 보존한다. stale revision/값 변조를 거부한다. 이는 provenance ledger이지 새 도메인의 논리적 truth proof가 아니다. 기존 경로용 primitive proof나 AdaptiveSession adoption을 구현했다고 주장하지 않는다. lower/upper는 수렴 상태와 margin에 따라 각각 보류할 수 있다.

정답은 별도 reference.json에서 audit만 읽는다. category와 relation 정답/보류, 처음과 feedback 뒤 판정, tick/group update/signal transmission, 단계 child CPU/wall, adapter 연산 수와 packet bytes를 보고한다. 상위 입력은 hard label로 바꾸지 않아 불확실성을 전달한다. 수작업 graph/adapter 기여를 숨기거나 adapter를 zero-cost로 취급하지 않는다. 학습0이므로 회로 학습 포함 효율·손익분기·장기 수정 유지 주장은 하지 않는다.

## 경계 오류와 검사

r18 source는 봉인 그대로 둔다. 새 r19 policy 사본만 마지막 도착 node의 재방문을 거부한다. 원 cycle 반례를 재현하고, 5개 vertex의 고유 비-self edge4 조합·유효 endpoint 범위에서 독립 판정식과 differential 검사한다. cross-A 실행은 이 gate를 사용하지 않는다.

서버 preparation→case18→별도 audit→봉인 전체600초, worker1, stage60초, child주소공간512MiB, raw128MiB 종료후 검사, retry0이다. audit는 별도 scalar 수식으로 모든 tick·종료·채택·cost와 public 입력/승격 연결을 재생하고 revision/value/state 변조 및 stale packet을 거부한다. 같은 kernel의 재실행을 독립 발견 표본으로 세지 않는다. 불리한 결과도 보존하며 결과를 보고 parameter·case를 바꾸지 않는다.
