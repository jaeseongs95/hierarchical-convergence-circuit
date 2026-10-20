# EXP-78 / R32: 역할 정보가 상위 관계 결합에 실제 쓰이는가

R31은 learned path2의 확장 이득을 일반 macro로 설명할 수 있고 activation pool의 추가 비용 이득은 없음을 관측했다. 이번에는 pool/gate 조정을 이어가지 않고 객체·역할 의미 소비 계약을 작은 native 실험으로 진행한다. 계약·범위·CS 조건을 동결했으며 core와 과거 연구는 보존한다.

질문은 하위 `R(a,b)`와 `S(c,d)`가 같은 confidence를 가질 때 상위 `R(x,y) ∧ S(y,z)` 판단이 실제 역할 결속에 따라 달라지는가다. x=R.subject, R.object=S.subject, S.object=z 세 일치와 두 양성 전제가 필요하다. 인코더는 각 역할 이름을 독립적인 -gain/+gain으로 옮기며 역할 간 비교·join·정답 계산을 하지 않는다. 상위 공통 kernel의 signed AND/OR graph가 세 동등성과 전제를 계산한다.

각 질문의 완결된 사실 집합은 전달한 두 packet이다. R/S는 두 원천 경로에 붙인 고정 relation 태그이며 자동으로 학습한 술어가 아니다. 상위 query는 x=z를 허용하는 주어진 두 사실의 결합 질문이다. Program metadata의 slot0/1은 두 관계 전제의 자리이며 native route proof의 raw edge를 뜻하지 않는다. 의미 soundness는 별도 논증 검사로 확인한다.

R19 upper는 confidence/context scalar만 소비했다. EXP-27은 typed reachable/proof memo를 전달했지만 B 전체 원관측을 다시 탐색·수렴했고 역할 정보는 주로 후보 proof 구성에 쓰였다. 이번에는 상위에 원래 두 lower path의 edge를 주지 않고 서로 다른 relation predicate를 실제 결합한다. 정상이며 출처가 맞는 role 반례가 실제 상위 readout을 바꿔야 한다. packet 필드 추가·손상 차단만으로 성공을 세지 않는다.

구현은 수작업으로 고정한 표현과18group Program이다. 기존 Group.level은0/1만 사용한다. 별도 A2 runtime·자동 의미 compiler·새 학습 알고리즘·지속 교정·전체 H02 입증을 주장하지 않는다. 같은 dynamics.tick/settle을 lower path와 upper의 다른 논리 작업에 쓰는 작은 충분성 검사다. 필요성·유일성·학습 일반화·생물학/LLM/하드웨어 주장은 없다.

## 고정 원천·질문·대조군

두 이름 집합 `[alpha,beta]`, `[iris,jun]`에 R/S의 정방향/역방향 lower path를 만들어 총8source를 사용한다. 각 lower는 source→전용midpoint→target의 양성 edge2개다. make_program·settle·primitive proof를 실제 실행하고 source별1회 결과를 읽기 전용으로 공유한다.8source 모두 수치 Program/drive가 같으며 실제 binary64 confidence가 같은지 검사한다. 서로 다른 packet hash를 독립적 세계 측정·평가 복제로 세지 않는다.

각 이름 집합의6질문은 정방향 양성, 반대방향 양성, join 역할 불일치, subject만 불일치, object만 불일치, subject/object 모두 불일치다. 총12질문은 양성4/음성8이다. 재명명은 구조적 대응 검사이며 독립 표본 증가나 학습된 어휘 일반화가 아니다. training/calibration·사전 native pilot은 없다. 모든 입력·Program·Config·판정·순서는 결과 전에 고정한다.

| 군 | 정보와 계산 |
|---|---|
| typed | 실제 lower packet 두 개의 confidence·predicate·subject/object와 query를 공통 native kernel로 결합 |
| scalar_erased | 같은 Program·query·confidence·출처 검증에서 fact-role drive4개만0으로 소거. query 역할은 보존. 정보 손실 대조이며 정보동일 알고리즘 대조가 아님 |
| ordinary_join | typed와 동일 packet/query 정보로 일반 equality3개와 premise2개를 직접 검사. upper native settle0회의 충분한 전통적 알고리즘 대조 |

각 이름 집합의 두 항목은 -4/+4 categorical code다. 임의 객체 embedding·연속 의미 거리의 학습/추론이 아니다. equality는 양수/양수 AND와 음수/음수 AND의 OR, goal은 equality3개와 confidence 전제2개의 AND다. 원본 sigmoid·damping·residual/history/stable·종료 규칙을 사용하며 threshold 보정은 없다. uncertainty는 이번 범위에 없다.

consumer 함수에는 query/compact packet/Config/고정 Program만 전달한다. 그 전 export/출처 검증 경계는 full lower record를 읽어 실제 confidence·관측·proof·config digest와 predicate/역할/revision을 확인한다. 이 경계는 raw graph로 upper 정답을 계산하지 않는다. lower raw edge를 upper에서 다시 추론하는 우회 경로가 없다. packet 역할과 confidence는 원래 값을 그대로 전달한다.

## 판정과 실패

typed의 예측은12질문의 실제 정답과 의미 논증 보존이다. 틀리거나 abstain하면 그대로 보존한다. scalar 소거는 같은 query/confidence/Program인데 다른 정답의 역할 조합이 충돌하는지 실제 bit 동일 trace로 확인한다. 이는 충분한 의미 정보의 조건을 보이는 대조이며 공통 kernel의 알고리즘 우월성을 뜻하지 않는다. ordinary_join도 성공하면 일반 relational join으로 같은 기능이 가능하다고 결론낸다.

수치 readout은 수정하지 않는다. producer는 readout 뒤 source proof refs와 role term의 주장만 복사하며 typed 경로에서 상위 정답을 별도로 계산하지 않는다. 별도 evaluator가 source primitive proof/진실성과 upper 의미 논증(positive는 모든 equality, negative는 하나 이상의 불일치)을 확인한다. upper 의미 논증은 기존 native primitive route proof가 아니며 해당 flag=false다. 잘못된 readout을 proof로 덮거나 채택을 강제하지 않는다.

정상 role counterexample와 packet 변조는 구별한다. 출처·revision·역할·confidence·proof 손상이나 drive/tick/readout/cost 조작은 감사 실패다. 정상 역할 불일치의 False는 논리적 음성 결과다. lower 양성 proof가 성립하지 않으면 원천 불충족으로 중단하며 이론 반증으로 세지 않는다. 사후 입력·반복·threshold 변경과 추가 확인 batch는 없다.

## 비용·상한·검증

lower8+typed12+scalar12=최대32settles/5120ticks, 일반join12를 포함한 upper 평가36개다. 준비1+source8+case36+audit1=46stage, 전체600초/단계60초/worker1/retry0/학습0/World.measure0이다. AS512MiB·parentfile32MiB/child16MiB·raw128MiB 단계 종료 soft 합계 검사를 적용한다. 로컬은 구조 검사와 수신 raw 재생만 하고 native 추론을 실행하지 않는다.

부모가 관측한 process CPU/wall에는 import·source 검사·입력/source 파일 읽기·export/guard·encoding/일반join·Program 실체화·수렴/논증·JSON/디스크 쓰기가 포함된다. 각 군의 실제 query prefix K1..12에서 사용한 lower source의 계산·proof·직렬화 stage를 source당1회 부과한다. 세 군이 같은 실제 원천을 공유한 회계이며 독립 end-to-end 반복이 아니다. 준비·audit·봉인·호스트 orchestration은 별도다. 미래 수명·상각·손익분기점·통계적 속도를 외삽하지 않는다.

query당 export2회와 guard의 export 재구성2회로 origin SHA4회·packet 내부 digest 합16회·validation2회가 수행된다. source 직렬화 bytes·packet bytes·typed symbol lookup6개/scalar lookup2개+role erasure4개·confidence 산술6개·일반 equality3개+premise2개를 별도 ledger로 남긴다. 이는 interpreter 명령 전수 계수가 아니며 native counter와 다른 단위를 합치지 않는다. producer 논증 복사 비용도 process 경계에 포함된다.

별도 audit는 signed AND/OR 문법·모든64개 symbol 조합의 Boolean 구조·필드 인코딩·실제 lower primitive proof·다른 scalar/controller 재생·source/upper 비용·의미 reference를 확인한다. 실제 연구32settle과 구조 검사를 혼합하지 않는다. role/confidence/origin/revision/drive/tick/readout/proof/cost 변조9종을 검증한다. 내부 일관성/재현 검사이며 독립 호스트 인증이나 생물학적 이론 검증이 아니다.
