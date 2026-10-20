# EXP-81 / R35: 가변 후보와 논리 제약의 공통 생성 규칙

R34는 authored 두 후보 문법에서 full/exact576/576을 맞혔지만 후보 수와 제약 조합 일반화는 검증하지 않았다. R35는 역할값이나 정답을 보지 않는 하나의 syntax/count 생성기가 후보수1..4와6개 제약 AST를 native Program으로 만들고, eligibility packet으로 별도 T query를 처리하는지 검사한다. 구조적 확장성의 유한 공학 검사이며 학습된 zero-shot 일반화나 arbitrary CSP의 증명이 아니다. 일반 exact가 동일 typed 원천·AST·외부 complete flag를 받는다. 정보가 적은 약한 군은 추가하지 않는다.

## 원천·입력과 완전성의 뜻

2개 namespace에서 R/S/T 각각4개, 총24개의 실제 native path 원천을 새로 생성한다. 각 R(a,b)는 완결된 조건부 대안이고 S/T는 별도 외생 관계다. 원천 positive proof를 실제 세계의 두 가설 동시 참이나 확률 교정으로 해석하지 않는다. 원천·역할·revision·Config·proof digest를 보존한다.

864조건은 기준 후보 domain2/3/4 × C AST6 × T AST6 × namespace2 × 후보순서2 × complete2다. initial은0.5로 고정하며 새 그래프의 다른 초기상태 견고성을 주장하지 않는다. 각 기준 domain은 해당 과제가 허용하는 R 대안 범위를 외부에서 정한 계약이다. 전체 source pool의 다른 R 원천이 해당 과제 domain에 자동으로 포함되는 것은 아니다. incomplete 입력은 이 domain에서 가장 큰 endpoint 후보를 하나 뺀 뒤 순서를 정하고 complete=False를 명시한다. 실제 관측 후보 수는1..4다.

complete는 외부에서 제공한 신뢰된 연구 계약이다. 알려지지 않은 누락을 자동으로 발견하는 장치가 아니다. 이 표시가 거짓이면 의미 보장을 할 수 없다. 불완전하면 현재 보이는 후보가 우연히 같은 답을 주더라도 보수적으로 incomplete 보류한다. 이는 최적 정보 추론이 아니라 사전 고정한 안전 정책이다.

C의 세 leaf는 S0/S1/S2, T는 T1/T2/T0이다. AST6종은 leaf0, OR(0,1), AND(0,1), NOT(0), AND(OR(0,1),NOT(2)), OR(AND(0,1),NOT(2))다. 마지막 두 식은 조합과 부정을 포함한다. candidate가 없는 endpoint에 대한 match는 False가 되며 NOT은 현재 외부 domain의 후보에 대한 Boolean 부정이다. namespace는8기호의 공개 vocabulary를 제공한다. 동일3bit 필드 인코딩 뒤 equality는 native 그래프가 계산한다.

## 생성기와 소비 경계

동일 signed AND/OR 규칙으로3bit equality16group, AST4..6group, 후보 classifier9..18group, 후속 query13..25group의 Program을 생성한다. 실제 group 수는 동결 JSON과 준비 검사로 확정한다. 그래프 모양은 syntax와 관측 후보 수에만 의존하며 role 비교 결과·case ID·oracle을 보지 않는다. native route의 host는 기호별 인코딩·신호 전달·고정 stable one-hot decoder만 수행한다. role equality, feasible filtering, truth repair는 금지한다.

후보마다 C leaf match3회+AST1회, classifier1회로 eligibility와 none/unique/many/incomplete를 만든다. packet은 모든 eligibility와 native coverage activation, 출처·revision1·state digest를 보존한다. selected index는 unique label과 native eligibility one-hot 출력에서만 읽는다. 최종 consume_t는 이 packet과 T AST/원천·vocabulary·Config·Program·initial만 받고 최초 C를 받지 않는다. 각 후보의 T match3회+AST1회와 universal query1회로 전부 True/전부 False/빈해/혼합/불완전을 구분한다. 후보가 여러 개여도 T가 일치하면 확정할 수 있고, 빈해는 False가 아니라 inconsistent 보류다.

각 numeric 평가는 실제8n+2 settle이다. 총 native19008 + 원천24 =19032회/최대3045120tick이다. 각864조건에 native/exact 총1728평가를 수행한다. 프로그램 생성·검증·source export/guard·native 실행·packet/hash·기록을 비용에 포함한다. exact는 상위 native0회이며 같은 실제 원천을 소비한다. 기존 core·learner·과거 연구는 수정하지 않는다.

## 검증·저장·중단 조건

실행 전 AST 생성 문법과 모든 Boolean 입력, 행렬·경계·source pins를 검사한다. 이것은 scalar native 실행의 대체 증거가 아니다. 모든 native 호출을 실제 계산하며, 완전히 동일 kernel+Config digest와 객체 equality가 맞는 경우에만 trace 저장을 공유한다. 모든 physical call reference에 대해 비용을 합산한다. 이 저장 공유를 계산 캐시나 속도 이득으로 주장하지 않는다.

서버와 수신 후 로컬에서 전체 tick을 손실 없이 복원하고 scalar/controller/count를 재계산한다. 독립적인 집합 기반 AST oracle로 exact와 native 결과를 채점하고, source·역할·Program·drive·coverage·packet·T·revision·물리 호출 수를 대조한다. 표적 변조를 거부하는지도 확인한다. 작성자의 별도 수식/저장 데이터 검산이며 독립 감사자 검증은 아니다. 원자료를 수신하기 전에는 완료를 주장하지 않는다.

AI Research SSH 전체1800초/단계600초/worker1/retry0/parent512MiB/child256MiB/raw128MiB, 학습·World.measure0이다. source를 물리적으로 한 번 생성하고 arm별 원천 포함 비교에는 같은 원천 비용을 한 번씩 배분한다. core/저장/공통 프로세스/감사/봉인 비용과 배분 가정을 구분한다. 단일 실행 시간으로 속도 우위를 판정하지 않는다. source/input/generator/decoder/threshold를 봉인한 뒤 native 실패를 고치거나 다시 실행하지 않는다.

채택은 해당 유한 문법에서 상태·선택·값·사유가 exact 의미와 맞고 incomplete 오확정이 없을 때에만 허용한다. 실패는 개수·조건·최초 틀린 신호를 보존하고 다음 연구의 제약으로 쓴다. 성공하더라도 학습·자율 계층 형성·반복 추론 필요성·일반 CSP·운영 적용·총비용 우위를 주장하지 않는다.
