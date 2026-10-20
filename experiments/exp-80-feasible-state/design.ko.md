# EXP-80 / R34: 해집합 상태 보존과 모든해 후속 query

R33은 typed 상위 제약이 하위 선택과 별도 T 판단으로 전달됨을 보였으나, 모호·모순144조건에서 strict0이었다. 두 compatibility를 차이 하나로 축약하면 두 후보 모두 허용과 둘 다 금지의 공통성분을 잃는다. 다음 비중복 과제는 **두 허용 신호를 유지해 native 유일0/유일1/복수/해없음 상태를 내고, 별도 T 판단이 가능한 모든 결속에 대해 같은 답일 때만 확정하는 충분성**이다. 후속 방향이 R33 근거에서 구체화돼 이번에는 그 계약을 바로 구현한다.

## 원천과 표현

R33과 같은 두 객체 grammar에서 R(a,b0), R(a,b1)는 완결된 대안 후보이고 S(b0,z),S(b1,z)는 hard context, T(b0,w),T(b1,w)는 별도 query다. namespace2에서 총12개의 실제 native path source를 새 R34 폴더에서 생성해 primitive proof/역할/원천/Config를 결속한다. positive path는 후보 지지의 조건부 근거이며 두 가설이 세계에서 동시에 참이거나 confidence가 보정 확률이라는 뜻이 아니다.

Context와 T는 각각 one0,one1,either,both의 공개 grammar다. C either는 복수해, C both는 해없음이다. T either는 두 후보에서 모두 True, T both는 둘 다 False, one0/one1은 후보에 따라 다르다. 따라서 복수해에서도 T either/both는 답할 수 있고, T one0/one1은 보류해야 한다. 빈 해집합은 False가 아니라 inconsistent 보류다.

576조건은 C4×T4×namespace2×후보순서2×초기상태0.2/0.5/0.8×softprior3의 교차다. softprior -0.25/0/+0.25는 선호 metadata이고 hard 허용집합에 적용하지 않는다. 이 변형은 독립 표본·통계적 반복이 아니다.

## 비교와 native 경계

full은 후보별 외생 compatibility 두 값을 그대로7group native classifier에 전달한다. delta는 차이 d만 보존해 [0.5-d/2,0.5+d/2]로 공통성분을 제거하고 **동일 classifier·후속 graph·decoder**에 전달한다. delta는 정보 손실 개입군이며 충분한 일반 알고리즘 대조는 같은 원천/C/T를 받는 exact solver다.

하위 graph는 허용 f0/f1로 none,u0,u1,many를 native signed AND/OR로 계산한다. host는 stable one-hot 출력의 고정 margin decoder만 읽고 원래 role을 고치거나 해집합을 계산하지 않는다. revised packet은 두 eligibility activation, classification,원천과revision1을 보존한다. 최종 consume_t는 이 packet과 T/mode/vocabulary/config/program/initial만 받고 처음 C나 oracle을 받지 않는다. 후보마다 native T-role match를 계산한 뒤15group graph가 가능한 후보의 positive/negative witness를 집계해 qtrue/qfalse/empty/mixed를 계산한다. 일부 후보만 True면 ambiguous, 모두 같으면 해당 답, 후보가 없으면 inconsistent다. 모든 numeric 출력·오답·보류는 고치지 않는다.

원천 외 각 numeric 평가의 실제 settle은 C-match2+하위class1+T-match2+모든해query1=6회다. full/delta 각576회, exact576회의 총1728평가이며 source12까지 실제 최대6924settle/1107840tick이다. 원본 common tick/settle은 수정하지 않는다. 상위 논증은 역할·native 상태의 별도 실험 계약이며 core primitive route-proof registry를 확장했다고 주장하지 않는다.

## 손실 없는 기록과 검증

모든 호출을 실제 수행한다. 완전히 같은 kernel record와 Config의 canonical digest가 같고 객체 전체 equality도 맞을 때 **기록 저장만** 공유한다. 단일 native record는 frozen Program key,drive,initial,각 tick의 residual/stable_steps/ordered state vector,final vector,convergence,cost/readout을 lossless JSON으로 저장한다. 모든 물리 호출은 이 기록 ID를 남기고, 실제 횟수·tick/group/link 비용을 각 reference마다 합산한다. 이를 계산 캐시나 속도 이득으로 세지 않는다.

별도 검사기는 프로그램·전체 tick dictionary를 복원해 원본 record+Config digest를 확인하고 scalar/controller/count를 재계산한다. 각 case의 역할 인코딩·순서·revision·메시지·최종 T 입력을 source에 대조하며 independent set oracle로 native 결과를 채점한다. 기존 R33 helper의 scalar/source-proof 검사를 재사용하고 이번 lossless codec과 신호·결속 변조를 검사한다. 실제 불합격도 보존하며 실행 후 threshold/decoder/입력/code를 고치거나 native 재실행하지 않는다.

## 비용과 제한

AI Research SSH worker1/retry0/전체1800초/단계600초, parent512MiB/child256MiB/parent file32MiB/child file16MiB/raw128MiB. 학습과 World.measure0이다. native 계산·source export/guard·인코딩·packet/논증 hash와 원자료 기록/직렬화, process overhead, 감사/봉인을 구분한다. source는 물리적으로 한 번 생성해 세 arm에 같은 실제 source 비용을 한 번씩 배분한다. artifact 저장 첫작성/공유 비용과 반복 물리 계산량을 섞지 않는다. 짧은 단일 실행에서 통계적 속도, 미래 회수, 학습/일반 CSP/고유성 우위를 주장하지 않는다.

채택은 동결 matrix에서 상태·결속·query 값·사유가 exact 의미와 함께 맞고 변형에 따른 오확정이 없을 때만 이 authored 두 후보 grammar에 한정한다. 다른 객체 수·불완전 후보·noisy hard context·새 grammar 일반화는 검증하지 않는다.
