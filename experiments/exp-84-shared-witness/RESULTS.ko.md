# R38 / EXP-84: 같은 Z 증인의 결속이 거짓 양립성을 막았다

**공유 Z 증인 방식은 608/608조건과 2432/2,432개 XY eligibility를 맞혔다.** 독립 증인 방식은 원래 full triple 기준 476/608조건이며, 실제 공통 해가 없는데 가능하다고 판단한 경우는 76건이었다. 독립 증인 개입 자체는 선언한 완화 oracle 기준 608/608조건이었다. 공유 증인 전체 검사 `True`, 개입 정합성 검사 `True`다.

주어진 완전2×2×2 domain·폐쇄 관계표·초기상태0.5에서의 유한 결과다. 원래8개 triple 전체를 이후 상태에 보존한 것은 아니며, 최종 packet은 XY 투영이다. 학습·임의CSP·세계의 부정증거·확률교정·계산재사용·효율우위·운영채택의 근거로 확대하지 않는다. 동결 후 native 재실행·사후튜닝0회다.

## 비중복 질문과 구현

[R37](../exp-83-joint-tuple/RESULTS.ko.md)은 한 이항관계의 두 변수 상관관계를 보존했다. 이번에는 R(X,Y), S(Y,Z), U(X,Z)를 연결하고 S와 U에서 사용하는 Z가 같은 값이어야 함을 시험했다. R은 대각9/교차6 두 가지, S/U는 각16개 전체 관계표를 교차한512조건이다. R2×S/U각[0,6,9,15]의32핵심조건에는 이름/순서3변형을 추가해96조건을 더했다. 총608조건×3방식=1,824평가다. 이는 R까지16종인 전체16³표나 임의CSP 전수검증이 아니다.

24개 positive path 원천은 이름2×관계3×쌍4이며 실제 native 수렴과 조건부 primitive proof로 만든다. 각 변수의 두 값과 관계목록의 완전성은 외부 계약이다. 가상 assignment는 세계에서 지지된 사실이 아니고 목록 부재는 세계의 부정 증거가 아니다. 각 namespace의 문자열은 다르지만3bit 필드 code 대응은 같다. 순서 변형은 관계행과 각 공개 assignment layout을 함께 역전한다. Z 정수 증인 순서0,1은 고정이다.

기존 R37 membership과 R35 equality/pair AND/OR/feasible4, 공통 수렴기를 재사용했다. 관계마다 각 공개 쌍을 관계행의 두 필드와 native equality로 비교하고 pair AND 뒤 행 OR를 계산한다. host는 공개domain·정수layout열거·필드encoding·metadata검사만 수행한다. numeric 결합자는 **세 수치표와 공개order**만 받고 사실·domain토큰·case/mask·oracle를 받지 않는다.

native_shared는 각 XY에서 같은 Z 위치의 S(Y,Z) AND U(X,Z)를 두 번 계산한 뒤 OR하고 R(X,Y)와 AND한다. native_split는 S와 U에서 Z를 각각 먼저 OR해 지운 후 두 결과 및 R을 AND한다. 후자는 서로 다른 증인을 허용하는 명시적 정보손실 개입이다. 두 arm 모두 원래 세 관계를 실제로 계산한다. 상위4개 XY eligibility는 기존 feasible4에서 none/unique/many와 선택 위치·양립성을 판독한다. exact_joint는 동일 최초 정보의 명시적 symbolic 기준이다.

## 관측과 판별

별도 set oracle는 원래8개 triple을 동시에 검사한 뒤 XY로 투영한다. strict는 eligibility·kind·선택위치·consistent가 모두 맞아야 한다. 개입 기준은 split에는 독립 존재양화 완화 oracle, 나머지에는 full triple oracle다. full 기준 실패를 개입 구현 오류로 바꾸어 세지 않는다.

| 방식 | full strict | full eligibility | 개입 strict | 거짓 가능 | 거짓 불가능 |
|---|---:|---:|---:|---:|---:|
| exact_joint | 608/608 | 2432/2432 | 608/608 | 0 | 0 |
| native_shared | 608/608 | 2432/2432 | 608/608 | 0 | 0 |
| native_split | 476/608 | 2280/2432 | 608/608 | 76 | 0 |

실행 전 Boolean 기대는 split strict476/608, eligibility2280/2432, 거짓가능76건이었다. 이 수치는 준비 단계 기대이며 위 표가 실제 native 관측이다. 동적 보류를 False와 같다고 세지 않는다. 최종 consistent만 같아도 eligibility나 다른 층이 틀리면 공유증인 보존의 성공으로 채택하지 않도록 고정했다.

| native 방식 | 필드 equality | 필드 pair AND | 관계 membership | 증인 결합 AND/OR |
|---|---:|---:|---:|---:|
| native_shared | 29184/29184 | 14592/14592 | 7296/7296 | 9728/9728 |
| native_split | 29184/29184 | 14592/14592 | 7296/7296 | 7296/7296 |

R=9,S=9,U=6에서는 X=Y, Y=Z, X≠Z여야 하므로 공통 triple은 없다. 세 관계는 각각 비어 있지 않고 모든 변수의 주변집합이 전체다. 공유증인은 이 모순을 보존해야 하며, 독립증인은 S의 Z와 U의 Z를 다르게 골라 XY 대각을 잘못 허용한다. 대조 R=9,S=9,U=9에서는 실제 공통 triple2개가 있다. 두 반례의 이름·순서 모든 변형과 중간값을 analysis.json의 `cycle_counterexamples` 및 batch 원자료에 보존했다.

| 방식 | 이름·순서 정규화 불변성 |
|---|---:|
| exact_joint | 96/96 |
| native_shared | 96/96 |
| native_split | 96/96 |

변형은96쌍/arm이며 독립 통계표본으로 세지 않는다. 첫 실패층 집계와 분류별 건수도 analysis.json에 남겼다. exact의 native 중간 검사는0회다.

## 실제 계산과 전체비용

AI Research SSH의 새 전용폴더에서 작업자1·재시도0으로 실행했다. 준비/계산/감사3단계가 exit0이고 봉인까지 **229.941487초**였다. 원천24+numeric120,384=**120,408회 실제 settle, 3,596,996tick**이다. 학습·세계측정0회다. 관계 membership은12×(|R|+|S|+|U|)+12회, shared결합/분류17회, split결합/분류13회가 더해진다.

| 방식 | 상위 native 호출 | 원천 포함 tick | core CPU(s) | 저장 CPU(s) | 배분한 원천 포함 CPU(s) |
|---|---:|---:|---:|---:|---:|
| exact_joint | 0 | 792 | 2.324140 | 0.000899 | 2.444497 |
| native_shared | 61,408 | 1,830,396 | 69.575083 | 27.953386 | 97.647928 |
| native_split | 58,976 | 1,767,392 | 68.648347 | 27.205707 | 95.973512 |

source CPU0.042866초, 792tick·3,960group·6,336link다. core는 source export/guard, Program생성·검증, encoding·native연산·packet/hash를 포함한다. workCPU195.980205초 중 공통 잔여는0.229777초다. 마지막 열은 원천 한 번을 각 arm에 부과하고 공통1/3을 배분한 회계 가정이다. 열을 합산해 물리 총비용이라고 하지 않는다. 별도 준비/감사/봉인 비용은 raw/result와 completion에 있다. 원천과 kernel의 생성·제어 카운터 및 설정·codec 식별자를 보존했다.

모든120,384numeric 계산을 실행하고 fullkernel+Config canonical bytes가 같은 기록의 저장만 공유해 1110개 trace를 남겼다. 동일 digest도 전체bytes를 비교한다. 저장비용은 첫 작성 순서의 영향을 받고 arm순서는 고정 회전이다. 계산생략·가속·통계적 성능우위를 주장하지 않는다.

R37 실측의 호출/평가/원천 비례 휴리스틱은 work224.034497초/전체242.548693초이며 새 composition 비용을 보장하지 않는다. 선택안전계수3/60초올림으로 단계720초/전체780초를 고정했다. raw128MiB/cache192MiB/고유8192/건당128KiB/부모·자식AS각512MiB/파일130·8MiB/LRU18은 선택한 운영 중단선이다. 고유 trace수의 이론적 상한 증명이나 통계적/RSS 보장이 아니다. 서버 메모리점관측은 이후 가용량을 보장하지 않는다. 원시 `ru_maxrss_raw`에 단위 변환을 주장하지 않는다.

## 검증과 한계

로컬 준비1,959검사·metadata변조8개·codec roundtrip2개·저장/cache/용량변조9개·Python6파일AST/UTF8/LF를 확인했다. Boolean stub은 routing검사이며 수치정확성의 증거가 아니다. 로컬실제native0회다. 이후 JSON 1158개/13,219,729bytes를 수신하고 manifest 대상 1157개JSON의 크기·SHA를 전부 대조했다. source135개와 input pin102개도 변하지 않았다.

전체trace 1110개를 lossless 복원하고 모든120,384물리참조의 scalar/controller/cost/counter를 검산했다. 원천24개 primitive proof,1,824출력,독립triple/완화oracle,역할·Program·drive·initial·packet/revision·출처 및 저장기록의미변조12개를 확인했다. 최대scalar오차1.1102230246251565e-16는 고정1e-14이내다. 서버와 로컬 의미·비용집계가 일치한다. 작성자의 저장자료 검산이며 독립 감사가 아니다. CS bundle은 구조와 원시해시 결속을 확인하며 실행·신뢰·권한을 별도로 보증하지 않는다.

서버ZIP과 빈stdout/stderr6개는 수신하지 않았다. 모든native tick과 판단자료는 수신JSON에 포함된다. 수신 중 `UNAVAILABLE: Connection failed`1건은 성공한 페이지를 보존하고 같은 출력ID의 누락 페이지만 다시 읽어 복구했다. 명령·native실행 재시도는0회다. 동일채널해시는 외부host attestation이나 upstream완전성의 독립보장이 아니며, 기대한JSON이름·개수·크기·해시는 전부 대조했다. 공유변수domain이 겹치거나 domain이 크거나 표완전성이 불명확한 경우는 검증하지 않았다.

## 다음 판단

이번 유한 triangle에서 같은 Z 증인을 결속하는 연산의 적합성을 인정한다. 독립 증인 완화는 전역 양립성 판단에 채택하지 않는다. 다음 비중복 후보는 이번 XY투영에서 버린 Z를 후속 질의가 요구할 때의 정보 보존이다. 같은 XY상태를 만들지만 Z의 허용값이 다른 반례를 먼저 고정하고, triple 상태 또는 필요한 separator 상태를 보존하는 최소 표현과 동일정보 exact 기준을 별도 계약으로 비교해야 한다.

후속 방향은 현재 성취로 세지 않으며 일반CSP·학습·효율우위를 주장하지 않는다.

## 근거

- [설계](DESIGN.ko.md), [결과별 판단](OUTCOMES.ko.md), [동결입력](frozen_spec.json), [비용상한](BUDGET.ko.md)
- [관측·반례·비용](../../evidence/shared-witness-20261020-r38/analysis.json), [수신검산](../../evidence/shared-witness-20261020-r38/receipt-verification.json), [로컬검산](../../evidence/shared-witness-20261020-r38/local-verification.json)
- [서버단계결과](../../evidence/shared-witness-20261020-r38/raw/result.json), [원본manifest](../../evidence/shared-witness-20261020-r38/raw/manifest.json), [호출ledger](../../evidence/shared-witness-20261020-r38/raw/work-ledger.json)
- [실행경계](../../tools/r38_shared_witness/runtime.py), [독립oracle·검산](../../tools/r38_shared_witness/verify.py), [실험실행](../../tools/r38_shared_witness/probe.py)
- [작성자CS검토](../../evidence/shared-witness-20261020-r38/cs/review.json), [bundle검사](../../evidence/shared-witness-20261020-r38/cs/bundle-check.json)
