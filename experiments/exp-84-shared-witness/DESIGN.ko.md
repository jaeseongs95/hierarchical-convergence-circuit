# R38 공유 변수의 같은 증인과 전역 양립성

R37은 한 이항관계의 상관관계를 보존했다. R38은 R(X,Y), S(Y,Z), U(X,Z)가 같은 Z를 사용해야 할 때의 전역 양립성을 검증한다. 각 변수는 서로 겹치지 않는 두 값이고 초기상태는0.5다. 완전 domain과 관계목록의 완전성은 외부 계약이다. 목록 부재를 세계의 부정 증거로 해석하지 않으며 가상 assignment는 지지된 세계 사실이 아니다.

R은 대각9 또는 교차6, S/U는 각각 가능한16개 관계표 전체를 교차한512조건이다. 추가로 R2×S/U 각[0,6,9,15]의32조건에 이름/순서(0,1),(1,0),(1,1)의3변형을 붙여96조건을 더한다. 총608조건×native_shared/native_split/exact_joint=1824평가다. 순서는 세 관계목록 및 각 공개2×2 assignment의 역순을 함께 바꾼다. Z 증인 순서는 고정0,1이며 역할은 그대로다. 이름 변경은 문자열만 바꾸고3bit code 대응은 유지한다. 이는 전체16³관계표나 임의CSP 전수검증이 아니다.

24개 positive native path 원천은 이름2×관계3×쌍4다. 각 관계의4개 membership은 기존 R37 필드별3bit equality2→pairAND→행OR를 실제 실행해 얻는다. host는 공개domain·정수layout 열거/encoding/metadata 검사만 하고 사실 일치나 해집합을 풀지 않는다. numeric 결합자는 사실·도메인토큰·case/mask/oracle 없이 세 수치표와 공개order만 받는다.

native_shared는 각 XY에 대해 같은 정수 Z 위치의 S(Y,Z) AND U(X,Z)를 두 번 계산하고 OR한 뒤 R(X,Y)와 AND한다. 8개 triple witness,4개 existential join,4개 R결합이 모두 native다. native_split는 S와 U에서 Z를 각각 먼저 OR하여 지운 후 서로 AND하고 R과 결합한다. 이 명시적 정보손실 개입은 두 관계에 서로 다른 증인을 허용한다. 두 방식 모두 동일 원래 관계표를 입력받고 전체 계산을 실행한다. 최종4개 XY eligibility는 기존 feasible4를 통해 kind/선택위치/양립성으로 판독한다. 원래8개 triple은 승격 packet에 보존하지 않으므로 이후 Z 질의가 가능한 일반 상태 표현으로 주장하지 않는다.

정확 기준은 원래 세 관계를 동시에 만족하는8개 triple을 독립 set oracle로 열거한 후 XY로 투영한다. 독립 증인 개입은 별도 완화 oracle에 비교하고 full oracle 정보손실을 따로 센다. R=9,S=9,U=6은 각 관계가 비어 있지 않고 모든 변수가 주변집합에 남지만 공통 triple은 없으며, 독립 증인 완화는 XY 대각을 허용한다. 대조 R=9,S=9,U=9는 실제 공통 triple2개가 있다.

role/pair/membership/composition 각 층과 eligibility 및 최종 kind/선택/consistent의 일치를 별도 채점한다. 원자료의 Program/drive/초기값/출처/packet/controller/물리호출을 모두 검산한다. 의미 실패를 harness 오류로 덮거나 사후 정답 수리·threshold조정·native재실행하지 않는다. 계산 공유는 없고 동일 trace 저장만 공유한다. 학습/세계측정0, 통계적 속도·일반추론·운영채택 주장은 없다.
