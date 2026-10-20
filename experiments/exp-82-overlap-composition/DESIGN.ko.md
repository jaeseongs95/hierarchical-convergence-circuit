# EXP-82 / R36: 겹치는 typed 원천과 실제 Boolean 조합

R35는864조건을 모두 맞혔으나 실제 leaf가 서로 배타적이어서 여섯 AST가 일부 같은 의미로 축약됐다. R36은 R35의 생성기·수식·decoder를 바꾸지 않고 **서로 다른 predicate와 목표의 원천 subject가 겹칠 수 있게 해 실제8개 Boolean 조합을 모두 실현**한다. 더 큰 후보 수나 새 학습기가 아니라 기존 조합 규칙의 실제 의미 보존을 판별하는 과제다.

## 원천과 의미

namespace2에서 R 후보2개와 P0/P1/P2 및 Q0/Q1/Q2 각각 subject2개를 만들어 총28개의 실제 native path 원천을 생성한다. Pj/Qj는 서로 다른 predicate이고 목표도 서로 다르다. 동일 subject에 여러 leaf가 맞더라도 같은 명제를 중복 기입한 것으로 취급하지 않는다. source/proof/config/revision/역할은 그대로 결속한다. 이 조건부 path 지지는 세계의 임의 관계 truth나 확률 교정의 증명이 아니다.

후보 endpoint는 b0/b1의 완전한 두 대안이다. C mask와 T mask의 각 bit가1이면 해당 leaf 원천 subject를 b0,0이면 b1로 정한다. candidate b0는 해당3bit 패턴을, b1는 그 여집합을 실제 역할 일치 입력으로 받는다. mask 자체는 native 소비 함수의 인자가 아니다. leaf False는 주어진 grounded 원천과 후보의 join 불일치이며, 세계에서 해당 관계가 거짓이라는 관측이 아니다. 부정은 이 유한 compatibility 값의 Boolean 부정이다.

메타데이터 guard는 후보 predicate/고정 subject와 C/T 각 slot의 선언된 predicate/목표가 맞는지 검사한다. candidate.object와 leaf.subject의 역할 비교는 unchanged native3bit matcher가 수행한다. native adapter에 해집합 계산·정답 수리는 넣지 않는다. exact가 같은 typed 원천·slot·AST·완전 domain을 받는다. source 조건을 guard한 뒤 R35 execute를 그대로 호출하고, 최종 T 소비 함수는 처음 C나 oracle을 받지 않는다.

## 행렬과 판별

canonical2304조건은 C8패턴×T8패턴×C AST6×T AST6의 완전 교차다. AST는 R35의 leaf0,OR01,AND01,NOT0,AND(OR01,NOT2),OR(AND01,NOT2) 그대로다. 전체8패턴에서 여섯 함수의 truth vector는 모두 달라야 한다. canonical은 namespace0/순서0이고,64패턴쌍마다 ci=Cmask mod6,ti=Tmask mod6을 선택해 순서반전·이름변경·둘다의3변형192개를 더한다. 총2496입력×native/exact=4992평가다. 변형은 독립 통계 표본이 아니다.

최종 kind/selected/value/reason의 strict 채점 외에 각 numeric 평가의 역할12개·AST4개 중간 출력도 별도 채점한다. C/T 각각 여섯 AST의 실제 native8bit truth vector가 정답과 맞고 서로 구별되는지 확인한다. sentinel에서는 선택 인덱스를 endpoint code로 정규화해 같은 의미가 유지되는지 비교한다. 결과별 결정은 OUTCOMES.ko.md에 먼저 고정한다. 오답·보류·중간 실패를 보존하고 사후 재조정이나 native 재실행은 하지 않는다.

## 계산·기록·검증

각 numeric 평가의 실제 kernel 호출은 후보별 C3match+AST1,후보상태1,후보별 T3match+AST1,최종query1의18회다. 원천28+numeric44928=44956회/최대7192960tick이다. initial0.5,학습·World.measure0이다. 단일변수·완전한 두 후보 domain·여섯 authored AST의 유한 검사이며 arbitrary CSP·학습·다변수 joint binding·효율 우위를 주장하지 않는다.

모든 호출을 실제 수행한다. R34 lossless writer를 재사용하되 동일성 확인용 보관은 전체 kernel+Config canonical bytes로 해 Python trace 객체의 무제한 보관을 피한다. 최대2692고유 기록/기록당128KiB에서 중단하고 digest가 같아도 bytes 전체가 맞아야 저장을 공유한다. 저장 공유는 계산 캐시가 아니다. 중간 결과를 양자화하거나 버리지 않는다.

원자료는128평가씩39개 batch와 별도 metrics로 나눈다. work payload는 raw96MiB 중2MiB를 metadata용으로 남긴 경계에서 새 파일을 쓰기 전에 검사한다. 부모는 모든 단계와 봉인 뒤 원자료 크기를 확인한다. 저장 데이터 검산은 전체 고유 기록을 하나씩 scalar/controller/count 재계산하고, 한 평가에 필요한18개 reference만 LRU로 보관한다. source proof·typed slot·Program·drive·순서·packet·T·수식·Boolean/집합 정답·변조를 별도 대조한다. 작성자의 별도 수식 검산이며 독립 감사자를 통한 검증은 아니다.

시간·메모리·파일 상한과 산출 근거는 BUDGET.ko.md/budget.json에 있다. 실제 CPU·wall·cache bytes·ru_maxrss 원시 값과 원천/생성/검증/저장/공통 overhead/감사/봉인 비용을 구분한다. resource/provenance 실패에서는 기록 완전성을 먼저 판정하며 이론상 음성 결론을 내리지 않는다. 기존 core/learner/과거 연구는 보존하고 신규 세 경로만 커밋한다.
