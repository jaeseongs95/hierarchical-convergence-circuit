# EXP-78 / R32 결과: 역할 의미를 상위 kernel이 소비했다

**같은 신뢰도를 가진 하위 결과도 역할을 보존해 전달하면 상위 공통 수치 kernel이 주어진 관계를 정확히 결합했다. 역할 drive를 소거하면 정답이 다른 질문이 같은 수치 입력/trace로 충돌했다.** typed와 정보동일 일반 join은 각각12/12 정답과 출처에 결속된 의미 논증을 보존했다. 일반 join도 성공했으므로 이번 결과는 공통 kernel의 고유성·효율·학습 우위를 지지하지 않는다.

## 무엇을 새로 시험했는가

R31은 같은 learned path motif의 실행 이득을 일반 macro로 설명할 수 있었고 학습 포함 비용 회수도 없었다. 그 결과와 앞선 전체 방향 토론의 설계 gate를 반영해 이번에는 객체·역할 의미의 **실제 상위 소비**를 시험했다. [사전 계약](design.ko.md)과 frozen_spec.json에 표현·소비·대조·반례·실패·예산을 고정했다.

R19 upper는 scalar confidence/context만 읽었다. EXP-27은 typed relation/proof를 전달했지만 B 판단을 위해 원래 전체 관측을 다시 탐색·수렴했다. R32의 상위 함수는 raw lower edge나 원래 관측을 받지 않고 두 compact relation packet과 query만 받아 native graph로 join을 계산한다. 출처 검증 경계가 full source를 읽는 비용은 포함하지만 그 경계가 upper 정답을 계산하거나 raw graph로 답을 우회하지 않는다. 정상 role 불일치가 실제 native readout을 바꿨으므로 packet field 추가·변조 차단만의 검사는 아니다.

하위는 실제 native path2 추론·primitive proof이고, 상위는 같은 원본 tick/settle로 구동하는 수작업18group/46link signed AND/OR graph다. 인코더는 역할6개를 각각 두 객체 이름의 -4/+4 값으로 바꾼다. 역할 간 equality 세 개는 수치 graph 내부에서 계산한다. producer는 readout 후 source refs와 role term 주장만 복사하며 별도 symbolic 정답으로 수치 출력을 고치지 않는다.

질문은 제공된 두 관계 인스턴스 `R(a,b)`, `S(c,d)`로 query `R(x,y) ∧ S(y,z)`를 구성할 수 있는가다. 각 질문의 완결된 사실 집합은 그 두 packet이다. 다른 원천 파일은 다른 입력 변형을 만드는 자료다. R/S는 수작업으로 붙인 관계 태그이고 upper의 x=z 질문도 허용한다. native Program metadata의 slot0/1은 관계 전제 두 개이며 upper의 의미 논증은 기존 native primitive route-proof registry 밖에 있다. 해당 지원 flag를 false로 보존했다.

## 실제 관찰

두 이름 집합 `[alpha,beta]`, `[iris,jun]`에서 R/S 방향별8개 실제 lower source를1회씩 실행했다.8개 모두 유효하고 진실한 positive primitive proof였고 confidence는 binary64까지 동일한 **0.9877449513800958**이었다. 원래 role·revision·관측/proof/config/source digest를 packet에 그대로 결속했다. 이름 재명명은 구조 대응 검사이며 독립 표본 증가나 학습된 어휘 일반화가 아니다.

각 이름 집합의6질문, 총12질문은 양성4개/음성8개다. 입력·반복·threshold·순서를 사후 조정하지 않았다. 모든 arm의 abstention은0회였다.

| 방식 | strict 정답 | 오답 | upper ticks | upper group/normalization | upper link | 원천8개 포함 K12 CPU / wall(초) |
|---|---:|---:|---:|---:|---:|---:|
| ordinary_join | 12/12 | 0 | 0 | 0 | 0 | 2.757809 / 3.333116 |
| scalar_erased | 8/12 | 4 | 552 | 9936 | 25392 | 2.824801 / 3.333467 |
| typed | 12/12 | 0 | 398 | 7164 | 18308 | 2.806802 / 3.333215 |

strict 정답은 원래 수치값/일반 join 값이 고정 의미 정답과 같고, 원천 primitive proof와 상위 의미 논증이 유효한 경우다. typed는 양성4개를 True, join/subject/object/both 불일치8개를 False로 판정했다. 일반 join도 같은12개 판단을 냈다. scalar_erased는12개 모두 stable False였으므로 네 양성 질문에서 오답이며 해당 negative 논증도 유효하지 않았다.8/12라는 집계는 양성4/음성8 구성에 의존하므로 일반 정확도 추정으로 쓰지 않는다.

typed의 입력별 ticks는 각 이름 집합에서 positive_forward36, positive_reverse36, bad_join32, bad_subject32, bad_object32, bad_both31이었다. scalar_erased는 모든 질문46ticks다.8lower source는 각각33ticks, 총264ticks다. 실제 전체 실행은 lower8+typed12+erased12=32settles·1214ticks이며 일반join12개의 추가 upper native settle은0회다.

역할 소거는 packet·출처 검증·후단 논증 자료를 유지하면서 **상위 kernel의 fact-role drive4개만0**으로 만든 개입이다. query 역할과 lower confidence는 보존했다. 따라서 전체 시스템에서 모든 role 정보가 제거된 정보동일 알고리즘 대조라고 부르지 않는다.

특히 두 이름 집합의 positive_reverse와 bad_both 네 질문은 scalar 소거 뒤 같은 Program/drive와 **전체 native kernel trace**를 만들었으나 고정 정답은 True/False로 달랐다. scalar readout은 모두 False였다. 실제 packet의 정상 역할 정보가 달랐고 손상/출처 차단으로 만든 반례가 아니다. 이 충돌은 해당 kernel 입력에서 scalar confidence만으로 이 질문들을 구별할 수 없다는 제한된 정보 조건을 보인다. typed는 이 네 질문을 구별했다.

## 비용과 경쟁 설명

typed와 ordinary_join은 같은 packet/query 정보를 받았다. ordinary_join은 equality3개와 premise2개를 직접 검사하는 충분한 알고리즘이며 약한 cache를 기준선으로 쓰지 않았다.12질문에서 일반 equality 검사는36개·premise 읽기/검사는24개였다. typed는 symbol lookup72개·confidence 산술72개 및 upper 수치398ticks·7164group/normalization·18308link를 수행했다. scalar 소거는552ticks·9936group·25392link였지만 품질이 달라 같은 품질의 효율 대조로 해석하지 않는다. 이 단위들을 하나의 연산 수로 합하지 않는다.

주 표의 process CPU/wall에는 import·source SHA 검사·source 두 파일 읽기·export/guard·encoding 또는 일반join·Program 실체화·추론·논증 복사·JSON/디스크 쓰기를 포함했다. 세 군에 실제8lower source 생성/primitive proof/직렬화 stage CPU 합 **1.157694초**를 각각 한 번 부과했다. source-inclusive native ticks는 typed662, erased816, ordinary264이며 group은8484/11256/1320, link는20420/27504/2112다. actual physical source는 한 번만 공유했으므로 이 군별 비용을 합쳐 물리 실행 총량이라고 부르지 않는다.

actual query prefix K1..12의 의존성별 source 비용 귀속과 모든8source를 부과한 eager 비용을 [분석](../../evidence/semantic-join-20261020-r32/analysis.json)에 함께 보존했다. 실제 실행은8source를 먼저 모두 생성했다. prefix 귀속값은 실제 관측한 구성요소의 회계이며 각 K의 독립 end-to-end 실행/복제가 아니다. K12에서는 두 회계가 같고 미래 수명·상각·손익분기점을 외삽하지 않는다.

각 query는 export2회와 guard의 export 재구성2회를 수행해 origin SHA4회·packet 내부 digest16회·validation2회를 계수했다. source/packet compact 직렬화 bytes와 추가 encoding/join ledger도 보존했다. 이는 interpreter 비용의 전수 계수가 아니며 전부 process 경계 안에서 실제 비용을 치렀다. source 검증이 무료이거나 semantic code가 저절로 학습됐다고 가정하지 않는다.

ordinary_join도 같은 정답을 더 적은 native 작업으로 수행했다. process CPU의 작은 단회 차이를 통계 속도 우위로 채택하지 않는다. 수치 primitive의 정보동일 알고리즘 대비 비용 이득은 이번에 확인하지 못했다. 학습은0회이며 learned efficiency 결론을 내리지 않는다.

## 실행·근거 검증과 제한

AI Research SSH 요청d57c03e6… 하나가 owner-reviewed command_set 정책으로 자동 허용됐다. 소유자 승인 대기나 대체 요청은 없었다. Linux Python3.12.3,46stage 모두 exit0, 봉인 포함 **8.028516초**(상한600초), 최대 stage wall 0.317813초(상한60초)였다. worker1/retry0·학습0·World.measure0, AS512MiB·parentfile32MiB/child16MiB와 raw stage peak 863534bytes를 확인했다. 준비 CPU 0.132534초·audit CPU 0.288943초, 전체46stage 자식 CPU 합은 6.495501초다. 호스트 orchestration 비용은 계측하지 않았고 봉인 wall은 completion에 포함했다.

구조 검사192개는64개 Boolean role 조합의 논리 구조·개별 인코딩·소거를 검증했다. 로컬 native 추론/학습은0회였다. 수신8lower+36upper 기록의 source primitive proof·의미 reference·역할 인코딩·원본과 다른 scalar/controller 재생·비용 및 실제 source/query 결속을 별도로 확인했다.9종 변조(role/confidence/origin/revision/drive/tick/readout/proof/cost)는 모두 거부됐다. 이는 saved-record 검산의 결함 탐지 근거이며 모든 production 경로의 보안 인증은 아니다.

server 재생 최대오차0, local 최대오차 **1.6940658945086007e-21 ≤ 1e-14**였다. 초기 호스트 요약의 완전일치 검사는 six typed 음성 기록의 `numeric_replay_max_absolute_error` 통계만 달라 `AssertionError`가 났다. 원래 고정한 scalar tolerance로 그 파생 오차 통계를 확인하도록 호스트 집계만 수정했다. source·정답·proof·비용 계수는 정확히 같았고 frozen candidate/서버 raw/threshold를 바꾸거나 native 실험을 재실행하지 않았다. 이 경과를 local-verification.json에 보존했다. 호스트별 재생의 수치 차이가 왜 발생했는지 별도의 수학 라이브러리 원인 분리는 하지 않았다.

source99개의 로컬 bytes와 서버 postcheck가 불변이었고, 수신 결과 JSON48개 모두 same-channel manifest의 SHA-256과 정확히 일치했다. 전송 마스킹은 관측되지 않았다. 서버 보고 evidence ZIP244204bytes 자체와92개 stdout/stderr는 수신하지 않았다. redacted-adapter-outcome의 upstream SSH 완전성은 unknown이며 독립 host attestation은 없다. [수신 검사](../../evidence/semantic-join-20261020-r32/receipt-verification.json)와 [로컬 검산](../../evidence/semantic-join-20261020-r32/local-verification.json)을 구분해 보존했다.

작성자 CS3의무 검토와 bundle check(65개 raw 결속)는 PASS다. 이는 독립 구현 감사나 테스트 실행의 자동 증명이 아니다. 기존 core·과거 연구·user 변경은 보존했다.

## 전체 방향에 반영

이번 범위의 양성 결과는 **원천 native 결과의 객체·역할 정보를 보존해 다른 상위 논리 작업의 native 입력으로 실제 소비할 수 있다**는 작은 수작업 충분성이다. scalar의 안정적 수렴만으로 의미 결속의 완전성을 알 수 없었다. 같은 confidence에서도 다른 역할을 구별해야 하는 계약을 이후에도 유지한다.

일반 join도 성공했으므로 동일 기능이 HCC에 고유하거나 회로가 더 효율적이라는 설명은 채택하지 않는다. binary symbol encoding·관계 태그·18group 논리·두 객체 이름 집합은 모두 고정 수작업이고 불확실 역할·세 개 이상 객체·자동 의미 형성·상위에서 하위로의 피드백은 시험하지 않았다. upper의 실제 의미 소비를 확인한 것을 학습 일반화나 전체 H02 검증으로 확대하지 않는다.

후속을 진행하려면 모호한 역할 후보를 표현하고 상위 맥락이 하위 native 후보 선택을 실제로 바꾸는 양방향 경로를 별도 계약으로 정해야 한다. 일반 constraint propagation도 정보동일 대조로 유지해야 한다. 이번 결과만으로 자동 학습기나 새 gate/캐시를 추가하지 않으며 이 연구용 표현을 production/core에 채택하지 않는다.
