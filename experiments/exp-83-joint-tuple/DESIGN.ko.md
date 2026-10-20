# R37 / EXP-83 joint tuple 상관관계

R36은 단일변수의 실제 겹침 논리를 검증했다. 다음 질문은 두 변수의 주변 후보집합이 같아도 허용 joint tuple이 다를 때 의미를 보존하는가이다. 두 변수 X/Y 각각2값과4개 공개 가상 assignment를 완전 domain 계약으로 제공한다. 가상 assignment는 세계에서 지지된 사실이 아니다.

C/T 각16개 관계표를 모두 교차하고 이름2·결합 순서2를 적용한1024조건을 고정한다. 순서1은 candidate와 관계목록을 함께 역순으로 바꾼다. 총3072평가(native_joint/native_marginal/exact_joint)다. 모든 초기상태는0.5다. 원천16개는 이름2 × C/T2 × 가능한쌍4개의 실제 native positive path다. 관계목록이 완전하다는 폐쇄표 전제에서의 membership을 계산하며, 목록에 없다는 것을 세계의 부정 증거로 주장하지 않는다.

기존 R35 Builder/equality/pair AND/feasible4/query4와 공통 kernel을 재사용한다. candidate마다 관계행의 X/Y 필드를 각3bit native equality에 넣고, native pair AND 뒤 관계행 OR를 계산한다. host는 공개domain Cartesian 열거·개별필드 인코딩·메타데이터 검사만 하고 C/T tuple 일치나 해집합을 풀지 않는다. 새 OR/주변투영 그래프는 관계행 수와 공개 assignment layout에만 의존한다.

native_joint는4개 eligibility를 그대로 승격한다. native_marginal은 같은 원래C입력을 실제로 계산한 후 native OR로 X/Y 주변집합을 구하고 native AND로 다시 곱한 상태만 승격하는 명시적 정보손실 개입이다. exact_joint는 같은 최초 전체 정보를 쓰는 명시적 symbolic 기준이다. 최종 T 소비자는 승격 packet과 별도T만 받고 처음C/case/mask/oracle/source registry를 받지 않는다. source refs는 결속 provenance이며 T의 의미 계산에 쓰지 않는다. 서로 다른 source hash를 이용해 C를 암기할 수 있다는 가능성까지 막은 추상적 packet 동일성 정리로 주장하지 않는다.

strict는 kind/selected index/value/reason의 완전 일치다. field/pair/OR/주변projection 중간값과 tuple eligibility도 별도 채점한다. marginal의 개입 정합성은 Cartesian closure oracle에 비교하고, 원래 full tuple oracle 대비 손실은 별도로 남긴다. 대각C=9와 교차C=6은 주변집합이 같지만 T=9 또는6의 universal query가 반대다. joint16개와 주변곱10개 의미 서명, 이름·순서 정규화 불변성을 채점한다. 선언한 table의 symbolic 기대는 marginal strict944/1024, eligibility3584/4096이며 이는 native 관측값이 아니다.

모든 native 계산은 실행하며 중복 trace의 저장만 공유한다. 학습/세계측정0이다. 원천·Program생성·검증·계산·저장·프로세스·감사·봉인을 나눠 기록한다. 사후 튜닝·native재실행은 하지 않는다. 결론은 이 완전2×2폐쇄표 문법에 한정하며 학습/임의CSP/알수없는누락/확률교정/효율우위/운영채택은 주장하지 않는다.
