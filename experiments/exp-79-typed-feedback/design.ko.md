# EXP-79: typed 대안 후보의 왕복 소비와 실패 경계

R19의 scalar feedback/R32의 단방향 역할 소비 이후 비중복 가설은 **후보별 역할 compatibility가 실제 native lower 선택을 바꾸고, 그 선택된 객체가 최초 C를 읽지 않는 별도 native T 판단을 바꾼다**이다. 고정 host 직렬 스케줄이며 반복 수렴·joint graph·학습·고유한 primitive 필요성 주장이 아니다. 방향 토론의 근거·조건은 direction.ko.md와 evidence의 검증된 DecisionRecord에 있다.

## 공개 과제와 원천

각 namespace에서 R(a,b0), R(a,b1)는 하나의 관계 슬롯에 결속할 **완결된 두 대안 가설**이다. 각 가설을 지지하는 실제 native 2-edge path의 역할/원천/positive proof를 가져오지만, 두 가설이 동시에 세계에서 참이거나 path confidence가 보정 확률이라는 뜻은 아니다. 상위 S(b0,z), S(b1,z)와 후속 T(b0,w), T(b1,w)도 실제 native path 원천이다. 총12개를 한 번 생성·공유하며 원천은 하드 제약 실험의 가정 아래 양성이다. 원천 재사용은 독립 표본이 아니다.

C는 one0, one1, either(두 S 중 하나 만족), both(두 S 모두 만족)의 공개 hard grammar다. 앞의 둘은 한 후보만 허용, either는 둘, both는 빈 집합이다. 별도의 soft local prior 차이 -0.25/0/+0.25는 후보별 noisy preference이며 hard truth가 아니다. hard C와 반대인 prior를 오도 증거 조건으로 다루고, C 자체가 잘못된 hidden world를 감지하라는 요구는 하지 않는다.

## 실제 경로와 정보 경계

각 numeric arm은 ①원래 local prior만으로 native lower selector ②두 후보 각각 native role compatibility ③원래 prior+후보별 compatibility 차이로 native lower selector 재실행 ④새 revision1 conditional slot packet ⑤별도 native T의 순서다. 실제 settle은 1+2+1+1=5회다. lower-frozen도 동일한5회를 수행하되 반환 drive만0으로 만드는 인과 개입 대조다. 충분한 경쟁 알고리즘은 같은 후보/C/T를 받는 일반 exact solver다.

Compatibility graph는 R.object와 S.subject를 각각 bipolar로 인코딩하고 native signed AND/OR로 equality를 계산한다. host는 역할 간 비교·후보 교집합·argmax를 하지 않는다. feedback에는 lower confidence/posterior를 넣지 않아 자기 근거 재가산을 피한다. 두 숫자를 후보/source ID로 라우팅하며 원래 drive에 replacement 신호로 한 번만 준다. activation을 독립 증거나 확률로 해석하지 않는다. selector는3group, 단일 equality/T는5group, either/both는10group이며 공통 원본 tick/settle을 사용한다.

최종 consume_t의 입력은 revised binding,T,vocabulary,cfg,Program,initial뿐이다. C/feedback/case/truth를 받지 않는다. binding의 선택은 native goal의 고정 status/margin decoder로 정하며 역할·source는 수정하지 않고 revision만1로 발급한다. 보류 binding이어도 같은 T graph를 실행하고 semantic value는None으로 보류한다. numeric reason은 abstain_dynamic/decided이며 hard ambiguity와 inconsistency를 자동으로 구분해 준다고 가정하지 않는다. 검사기가 이를 고치지 않는다.

## 동결 입력과 판정

맥락4×softprior3×T2×namespace2×후보순서2×initial0.2/0.5/0.8의288조건, full/frozen/exact 3군864평가다. 이름/초기상태 변형은 독립 표본·통계적 반복으로 세지 않는다. arm 순서는 case별 순환한다. source12 + 288×2×5 = 최대2892native settle, 각160tick으로462720tick 상한이다.

검사기만 hard feasible-set S를 계산한다. S가 유일하면 그 후보, 복수면 binding 보류, 빈 집합이면 inconsistent 보류다. T는 모든 가능한 binding에서 같은 참/거짓일 때만 해당 값을 내고, mixed이면 ambiguous 보류, S가 비면 inconsistent 보류다. query 값 일치, binding 일치, value/reason/binding 모두 맞는 strict를 분리한다. 일부 정상 양성/음성 성공, C만 바꾼 쌍의 lower 및 T 변화, 모호/모순 오확정을 모두 집계한다. scalar/controller/cost/source proof와 source/revision/message/T/value/count 표적 변조를 검산하며 입력·출력·threshold를 사후 수정하지 않는다.

## 비용·종료·주장 제한

AI Research SSH 한 worker, 전체1800초/단계90초/자동retry0/학습0/세계측정0. parent512MiB/child256MiB, file32MiB, raw128MiB 범위에서 모든 tick과 원자료를 남긴다. 원천 path·proof 생성, export/guard/그래프/인코딩/메시지/선택/후속논증/직렬화/파일쓰기와 process 비용을 기록한다. 각 arm에 동일한 실제 공유 source 비용을 한 번씩 배분하고 물리 실행량·batch 공통 overhead·검산/봉인을 별도로 표시한다. source-inclusive 비교는 native tick/group/link와 CPU·wall의 단위를 섞지 않는다. 짧은 한 실행의 시간으로 속도/통계 우월성이나 미래 회수지점을 주장하지 않는다.

모호·모순에서 잘못 확정하면 numeric selector의 적용 범위 실패이며 실패를 보존한 연구는 완료할 수 있다. production 채택은 하지 않는다. 성공하더라도 authored 두 후보의 직렬 왕복 소비 충분성만 지지한다. 구조적 의미학습·더 큰 객체/관계 일반화·효율·고유성·반복전파 우위는 별도 과제다.
