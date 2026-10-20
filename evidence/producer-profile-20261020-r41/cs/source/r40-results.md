# R40 / EXP-86: factor가 답을 보존했지만 총비용 채택선에는 못 미쳤다

**결합slice·factor·동일정보exact가 각각1,536/1,536질의와3,072/3,072 Z eligibility를 맞혔다.** factor는 적은 조건부질의에서 수렴호출을 줄였지만, 어느 부하에서도 사전에 고정한 **3회 반복 각각 총 배분CPU 5% 이상 절감** 조건을 충족하지 못했다. 정확성은 통과했고 비용 후보 채택은 모두 보류한다. 이는 연구·검산 실패가 아니라 동결한 비용 가설의 판정 결과다.

조건부1회에서 factor/joint 총CPU비의 중앙값은0.971726(관측2.83%절감),2회0.983633(1.64%절감),4회1.000864,8회1.036269(3.63%증가)였다. 전체Z1회는0.997035다. 5%는 실행 전에 선택한 실무 판별선이며 통계적 유의수준이나 신뢰구간이 아니다. 같은 최초정보의 exact가 이 유한 과제에서 훨씬 적은 CPU를 사용했으며 native 효율우위를 주장하지 않는다.

## 비중복 질문과 실행 계약

[R39](../exp-85-z-query/RESULTS.ko.md)는 XY/Z주변집합이 조건부Z를 잃는 반례와 결합slice의 유한 충분성을 확인했다. 이번에는 원래 세 관계의 수치factor를 보존하면 답을 유지하고 미리 계산하는 비용을 줄일 수 있는지 비교했다. R39에서 정한 후속 후보를 직접 측정하는 단계여서 새 방향성 패널은 반복하지 않았다. 구현은 기존 회로·저장기·검산기를 재사용했으며 core·설정·임계값·후보상한은 바꾸지 않았다.

8선택표(R,S,U)=(9,9,9),(9,6,6),(9,5,5),(9,10,10),(9,9,6),(1,1,1),(1,3,3),(6,9,6)에 이름2×행순서2를 적용한32맥락이다. 각 변수는 서로 겹치지 않는2값domain이고 표의 완전성은 외부 폐쇄계약이다. 가상assignment는 세계에서 지지된 사실이 아니며 목록 부재는 세계의 부정 증거가 아니다. 초기값0.5와 필드 code 대응·Z순서0/1을 고정했다.

5부하는 조건부slot0의1회(q1),slot0/1의2회(q2),slot0/1/2/3의4회(q4),같은4질의를 두 번 실행하는8회(q8),전체Z질의1회(u1)다. **각 부하마다 생산자를 새로 실행해 봉인 비용을 실제 지불했다.** 3고정반복과 `(caseindex+workloadindex+repetition)%3` arm순서 회전을 사용했다. 총32×5×3×3=1,440기록,32×16×3×3=4,608출력이다. 서로 다른4,608개 질의나 독립 통계표본으로 세지 않는다.

## 생산·소비 정보 경계

24fresh conditional native path원천을 생성하고, 기존 R37필드equality→pairAND→행OR로 R(X,Y),S(Y,Z),U(X,Z)의 membership을 계산한다. native_joint는 같은XYZ의 R·S·U를 기존3leafAND로8번 결합해 Z별XY4 slice, 총8수치를 봉인한다. native_factor는 R4/S4/U4, 총12수치를 봉인한다. factor는 joint보다 수치 개수가 크므로 압축·최소표현이라고 하지 않는다.

producer는query를 받지 않는다. 공개 행순서 역전은 정수순열로만 canonical XY00/01/10/11에 맞춘다. consumer는 선언한numericpayload·공개queryslot·representation·fixedcfg/docs/initial만 받으며 원래fact·case·mask·중간메시지·출처hash·등록부에 접근하지 않는다. 외부binding과 hash는 보관·변조검사용이다. 모든 질의 전후 producer봉인과 payload해시가 같음을 확인한다.

joint의 조건부질의는 두slice의 공개slot을 기존feasible2로 전달한다. factor는 공개slot을 정수x,y로 배선하고 z0/1별 Rxy,Syz,Uxz를 nativeAND 두 번 실행한 뒤 같은feasible2로 판독한다. 전체Z질의에서는 factor가8triple을 계산해 z별OR4를 수행하고, joint는 보존한slice를 OR4로 줄인다. 질의마다 회로 초기상태를 새로 설정한다. 반복질의도 매번 실제 계산하며 host가 답·argmax를 계산하거나 숫자를 수리하지 않는다.

exact_joint는 같은 최초정보의 관계표에서 명시적symbolic full triple을 구하는 대조다. 별도 setoracle가 원래8triple과 최종허용Z집합을 검사한다. exact의 직렬화 payload는 토큰triple목록으로 native수치배열과 codec가 달라 크기 우위로 비교하지 않는다.

## 실제 정확성과 계산

| 방식 | 기록 | strict 질의 | Z eligibility | 상위 실제 수렴 | 상위 tick |
|---|---:|---:|---:|---:|---:|
| exact_joint | 480 | 1536/1536 | 3072/3072 | 0 | 0 |
| native_factor | 480 | 1536/1536 | 3072/3072 | 42,816 | 1,292,388 |
| native_joint | 480 | 1536/1536 | 3072/3072 | 43,008 | 1,297,200 |

strict는 eligibility2개·none/unique/many·선택위치가 모두 맞아야 성공이다. 중간층도 각각 확인했다.

| 방식 | 필드 equality | pair AND | membership | triple AND | 질의 입력 |
|---|---:|---:|---:|---:|---:|
| native_factor | 21120/21120 | 10560/10560 | 5760/5760 | 3648/3648 | 3264/3264 |
| native_joint | 21120/21120 | 10560/10560 | 5760/5760 | 3840/3840 | 3264/3264 |

arm마다 이름/순서 정규화360기록쌍·1,152질의쌍이 전부 불변이었다. 반복0과 이후반복의320기록쌍/arm도 전부 일치했다. 대각/반대Z 및 비대각XY 양성 대조를 포함한다. fullfactor는 이번 유한 질의군에서 주변집합 개입과 달리 조건부 상관정보를 보존했다. 이를 임의CSP·큰domain·불완전표·학습·확률교정·임의후속질의로 확대하지 않는다.

L=세관계행수합, B=12L+12 membership호출이다. producer는 joint B+8/factor B, 조건부질의당 joint1/factor3, 전체Z질의당 joint3/factor11호출이다. 조건부 호출수의 교차점은4회다. **호출수 교차점이 CPU 교차점이나 효율우위의 증명은 아니다.**

| 부하 | joint 호출(3반복 합) | factor 호출(3반복 합) |
|---|---:|---:|
| 조건부1회 | 8,352 | 7,776 |
| 조건부2회 | 8,448 | 8,064 |
| 조건부4회 | 8,640 | 8,640 |
| 조건부8회 | 9,024 | 9,792 |
| 전체Z1회 | 8,544 | 8,544 |

원천24+상위85,824=**85,848회 실제settle·2,590,380tick**이다. 학습·세계측정·동결후native재실행·사후튜닝0회다. 모든 계산을 실행하고 fullkernel+Config canonical exactbytes가 같은 기록의 저장만 공유해82trace를 남겼다. 같은digest도 전체bytes를 비교했다. 최초작성 저장비용의 순서효과를 보존했으며 계산cache로 보고하지 않는다.

## 총비용과 사전 판정

아래 CPU는 각 부하·방식·반복의 같은32맥락을 합한 그룹 비용이다. 총45그룹이다. 각 CPU열은3그룹 값의 중앙값이고, 비율열은 같은 반복의factor/joint를 짝지은3비율의 중앙값이다. 서로 다른 중앙값을 나눠 비율을 재계산하면 동일하지 않을 수 있다.

| 부하 | joint 총CPU(s) | factor 총CPU(s) | exact 총CPU(s) | 짝비율 중앙값 | 짝비율 범위 | 사전5%선 |
|---|---:|---:|---:|---:|---:|---|
| 조건부1회 | 5.209122 | 5.061840 | 0.195800 | 0.971726 | 0.966613–0.977711 | 보류 |
| 조건부2회 | 5.317014 | 5.215771 | 0.195841 | 0.983633 | 0.976561–0.985776 | 보류 |
| 조건부4회 | 5.490141 | 5.495465 | 0.196175 | 1.000864 | 0.998081–1.003516 | 보류 |
| 조건부8회 | 5.742381 | 5.949817 | 0.196803 | 1.036269 | 1.036124–1.037725 | 보류 |
| 전체Z1회 | 5.370225 | 5.356215 | 0.195904 | 0.997035 | 0.995951–1.001912 | 보류 |

질의1회에서 관측된 절감 범위는2.23–3.34%로, 세 반복 모두5%선에 못 미쳤다. 2회 역시1.42–2.34%였다. 4회와전체Z1회는반복에따라비용증감방향이바뀌었고8회는세반복모두factor비용이증가했다. 평균을 사후 채택조건으로 바꾸거나 기준을 낮추지 않았다.

조건부1회 부하의 세부비용 중앙값은 다음과 같다. 각열의 중앙값 합이 총비용 중앙값과 반드시 같지는 않는다.

| 방식 | 생산prefix+외부exportguard CPU(s) | 질의 CPU(s) | 저장 CPU(s) | 기록 감사 CPU(s) |
|---|---:|---:|---:|---:|
| native_joint | 3.256966 | 0.044841 | 1.272717 | 0.543115 |
| native_factor | 3.129114 | 0.081386 | 1.224411 | 0.549693 |
| exact_joint | 0.111237 | 0.000423 | 0.000092 | 0.001850 |

prefix에는 원천export/guard·Program생성/검증·생산·봉인·기타core진입 비용이 포함된다. 이번 계측은 이 내부 원인들을 각각 분리하지 않았다. 전체numeric호출 중 두arm의membership경로는74,880/85,824회(87.25%)다. 이는 호출수 비중이며 CPU의87.25%가 membership 때문이라고 단정하지 않는다. 생산·저장·감사 비용을 포함하면 소수 결합연산을 늦추는 절감이 총비용의 큰 차이로 이어지지 않았다.

실제 원천CPU0.042348초·792tick·3,960group·6,336link를 별도로 기록했다. work잔여CPU0.222762초, audit잔여0.602402초, 준비CPU2.455620초, 부모봉인processCPU0.301595초, launcher영수증시점CPU0.073843초와 원천을 합친 공통CPU는3.698569초다. 그룹마다1/45=0.082190초를 동일 배분했다. 모든그룹총CPU의 합165.613284초가 관측한전체processCPU합165.613284초와 일치한다. 원천은 물리적으로한번생성했으며45번실행했다고부과하지않는다.

이것은 pooled실험의 명시적비용배분이다. standalone제품의 독립시작비용·네트워크전송·로컬문서작업시간을 측정한 값이 아니다. launcherCPU는영수증작성직전의관측이며정밀OS전체추적을대신하지않는다. source/보관검사도동일하게포함한exact비용은약0.196초/32맥락그룹으로 native두방식보다훨씬낮았다. 이번과제에서native의symbolic exact대비효율우위는없다.

## 서버 실행과 자원

AI Research SSH의 새전용폴더에서 단일작업자·재시도0으로 실행해 준비/계산/감사3단계 exit0, 봉인포함 **165.554352초**에완료했다.

| 단계 | wall(s) | process CPU(s) | exit | ru_maxrss_raw |
|---|---:|---:|---:|---:|
| preparation | 2.469944 | 2.455620 | 0 | 23724 |
| work | 143.562656 | 143.533318 | 0 | 30096 |
| audit | 19.300198 | 19.248909 | 0 | 47428 |

R39실측의수치호출·exact질의·기록비용을각각스케일하고기타단계잔여를유지한계획치는work139.532164초/전체142.231835초였다. 안전계수3·60초올림·단계420초/전체480초로동결했다. 실제계산wall143.562656초는실측이며계획치를보장으로해석하지않는다. raw128MiB/cache192MiB/건당128KiB/부모·자식AS각512MiB/파일130·8MiB/LRU18/고유trace≤85,824는운영중단선이다. byte상한이개수상한보다먼저작동할수있고,서버메모리점관측은이후가용량을보장하지않는다. RSS는platform-native원시값을보존했으며단위변환을주장하지않는다.

## 원자료 검산과 제한

로컬준비4,727Boolean검사·metadata변조8개·joint소비자격리10개·factor소비자격리12개·synthetic codec왕복2개·저장/cache/상한변조9개·LRU18·Python5파일AST/UTF8/LF가통과했다. 준비의85,824호출은Boolean stub모의배선검사이며수치정확성의증거가아니다. 실제로컬native0회다.

서버JSON123개/4,509,966bytes를수신했다. 원본manifest대상122개JSON중121개는수신bytes의크기·SHA가직접일치한다. 출처검사표1개는도구가공개문서경로 `experiments/exp-86-factor-query/OUTCOMES.ko.md`를 `[REDACTED:entropy:40].ko.md`로마스킹해최초원본해시assert가실패했다. 수신본을그대로보존하고동결150파일목록에이미있는이경로를넣은별도복원본의7,188bytes·SHA가원본manifest와정확히일치함을확인했다. 숫자나기대해시를교체하지않았으며원본metadata bytes를직접수신했다고세지않는다. manifest는자신의해시대상밖이고빈stdout/stderr6개와서버ZIP은받지않았다.

모든native tick과판단자료는수신JSON에포함된다. 82trace를lossless복원해85,824물리참조의scalar/controller/cost를검산했고,원천24개의primitive proof와1,440기록/4,608출력·모든Program/drive/initial/관계역할·payload/봉인/출처를확인했다. 최대scalar오차2.7755575615628914e-17는고정1e-14이내다. 저장기록의미변조12개를거부했고서버/로컬집계가일치한다. source150개/input118pin도변하지않았다. 전체계측행coverage/비음수/짝비교/실제phase CPU잔여·배분합도검산했다.

검산과CS검토는작성자의별도자료재계산이며독립감사가아니다. CS bundle44파일/필수3의무PASS는참조와원시해시결속을검사하며실행·정확성·권한·host attestation을독립보증하지않는다. SSH도구의upstream완전성은unknown이고동일채널해시도외부증명이아니다. 기대JSON이름·개수·원본/복원크기·해시대조의범위를밝힌다. 범위는선택32맥락·5부하·고정회로·3반복이며유의확률·제품성능·일반CSP·학습·최소표현·운영채택으로확대하지않는다.

## 연구 판단과 후속 후보

factor는이번조건부Z품질을보존했다. 짧은부하의관측절감은기록하지만사전5%기준에미달해비용개선표현으로채택하지않는다. 정확성기준으로결합slice를유지하고,질의수가많아질수록factor의재결합비용이누적되는경계를보고한다. 어느방식도이번동일정보exact보다빠르다고하지않는다.

후속후보는생산prefix의원천export/guard·Program생성/검증·membership settle비용을분해해,실제계산을줄일대상이있는지판별하는계측이다. 이번자료만으로그내부원인을확정하지않는다. 이전연구와중복을먼저확인하고,이미검증된입력·회로의동일성/무효화조건과동일정보exact기준을고정한새계약에서만후속최적화를검토한다. 이번R40을재실행하거나임계값을바꾸지않는다.

## 근거

- [설계](DESIGN.ko.md), [결과별판단](OUTCOMES.ko.md), [동결입력](frozen_spec.json), [비용상한](BUDGET.ko.md)
- [정확성·짝비교·전체비용](../../evidence/factor-query-20261020-r40/analysis.json), [수신검산](../../evidence/factor-query-20261020-r40/receipt-verification.json), [로컬검산](../../evidence/factor-query-20261020-r40/local-verification.json)
- [metadata복원검증](../../evidence/factor-query-20261020-r40/restoration-verification.json), [별도복원본](../../evidence/factor-query-20261020-r40/restored-source-postcheck.json)
- [서버단계결과](../../evidence/factor-query-20261020-r40/raw/result.json), [원본manifest](../../evidence/factor-query-20261020-r40/raw/manifest.json), [물리호출ledger](../../evidence/factor-query-20261020-r40/raw/work-ledger.json), [기록별감사CPU](../../evidence/factor-query-20261020-r40/raw/audit-metrics.json)
- [실행경계](../../tools/r40_factor_query/runtime.py), [독립oracle·검산](../../tools/r40_factor_query/verify.py), [실험실행](../../tools/r40_factor_query/probe.py)
- [작성자CS검토](../../evidence/factor-query-20261020-r40/cs/review.json), [bundle검사](../../evidence/factor-query-20261020-r40/cs/bundle-check.json)
