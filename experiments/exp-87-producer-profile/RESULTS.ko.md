# R41 / EXP-87: 계측이 수치 이력을 보존했지만 native 교란 허용선을 넘었다

**288짝의 전체 반환기록·native kernel bytes가 정확히 같았고, 2,304개 질의 출력과 모든 중간층을 맞혔다.** 다만 계측형의 core CPU는 비계측형보다 joint 중앙값14.138%, factor13.928% 늘어 사전에 고정한10%허용선을 넘었다. 따라서 **비계측 native의 병목 순위와 후속 최적화 우선 후보는 판정 보류**한다. 기준을 바꾸거나 계측을 줄여 이번run을 재실행하지 않았다.

같은 최초정보 exact의 부담은 중앙값0.951%로 허용선 안이었다. 이 유한 symbolic 대조에서는 `source_export_guard`가 세 반복 모두 최대이고 총계측core의96.763–96.820%여서 해당경로의 후속 조사 후보 조건만 충족했다. 이를 native병목·제품성능·효율개선으로 전용하지 않는다. R40의5%총비용 채택 음성 결과는 그대로 유지한다.

## 비중복 질문과 범위

[R25](../exp-71-fixedpoint-elision/RESULTS.ko.md)는 고정점 이후 산술 생략을, [R30](../exp-76-spatial-sharing/RESULTS.ko.md)는 공간 공유와 cold 생성비용을, [R40](../exp-86-factor-query/RESULTS.ko.md)는 표현별 생산·질의·검산 총비용을 다뤘다. 이번에는 원본R40 q4의 계산을 바꾸지 않고 회로 생성·검증·수렴·결과구성/해시 비용을 관측하고, 관측 자체의 부담을 먼저 검증했다. 기존 후속 진단을 수행하는 단계라 새 방향성 패널은 반복하지 않았다.

R40의8선택표×이름2×행순서2=32맥락, canonical XY00/01/10/11 조건부질의4개를 고정했다. 비대각XY 양성 대조도 포함한다. 세 방식(native_joint/native_factor/same-information exact_joint)×plain/profiled두mode×3고정반복으로576기록·2,304출력이다. 각실행은새producer/초기0.5이고 답cache는 없다. namespace문자열은다르지만필드code대응은같다. 표의완전성은외부폐쇄계약이며가상assignment/목록부재를세계의지지사실/부정증거로바꾸지않는다. 독립통계표본이나일반CSP/큰domain/학습/최소표현검증이아니다.

arm순서는(caseindex+rep)%3, mode짝순서는(caseindex+rep+arm순번)%2로회전했다. 원천24개는fresh conditional native path로한번생성했다. 모든수치계산을실행했고 fullkernel+Config canonical exactbytes가같은trace의저장만공유했다. 학습·세계측정·동결후native재실행·사후튜닝0회다.

## 관측 방법과 정수 CPU 원장

plain은원본R40execute를호출했다. profiled는기존R33kernel의data-producing행을그대로둔외피에서Program구축·settle·결과구성주변에timer를놓고기존함수호출을관측했다. 원래수식·tick·검사·Program.digest·codec.plain·trace관찰·cost카운터는항상실행했다. 엔진소스/설정/임계값은바꾸지않았다. 연구singleworker process안의12binding을정상·예외모두finally로정확히복원했고중첩observer를거부했다. 서버서비스나사용자전역설정을변경하지않았다.

process_time_ns중첩stack에서inclusive−측정자식시간을exclusive로계산한다. 각기록에서exclusive합=core inclusive가정수ns로정확히맞는다. observer설치/복원·snapshot은전체core와root차이인profile_support에남긴다. childtimer종료뒤집계·wrapper bookkeeping은부모잔여에남는다. 최종timer필드구성/파일저장/원천생성/감사/준비/봉인/launcher는별도phase비용에남긴다. clock관측은analysis/rawsummary에보존했으며분해능을정확도나무교란보장으로해석하지않는다.

사전해석조건은각arm의32맥락core CPU합profiled/plain<=1.10이3반복모두맞고,모든품질/trace동치/계측검사가맞아야한다. 그때동일한최대exclusive범주가3반복모두총계측core의30%이상이면후속조사우선후보로만남긴다. 10%와30%는선택한기술판별선이며유의확률·신뢰구간·운영채택선이아니다. 이번native는첫조건이미달하므로최대범주가안정적이어도우선후보를부여하지않는다.

## 계측 교란과 정확성

CPU열은각32맥락그룹의3반복중앙값이다. 비율은같은반복의짝비율중앙값이므로각열의중앙값을나눈값과같지않을수있다. 이표는R41의coreCPU이며R40의공통비용배분을포함한총CPU와측정경계가다르다.

| 방식 | plain core CPU(s) | profiled core CPU(s) | 부담 중앙값 | 부담 범위 | 사전10%선 |
|---|---:|---:|---:|---:|---|
| native_joint | 3.467113 | 3.956932 | +14.138% | 14.101–14.346% | 미달 |
| native_factor | 3.463911 | 3.959739 | +13.928% | 13.891–14.549% | 미달 |
| exact_joint | 0.111415 | 0.112550 | +0.951% | 0.796–1.116% | 통과 |

| mode | 방식 | strict질의 | Z eligibility | 상위 실제수렴 |
|---|---|---:|---:|---:|
| plain | exact_joint | 384/384 | 768/768 | 0 |
| plain | native_factor | 384/384 | 768/768 | 8,640 |
| plain | native_joint | 384/384 | 768/768 | 8,640 |
| profiled | exact_joint | 384/384 | 768/768 | 0 |
| profiled | native_factor | 384/384 | 768/768 | 8,640 |
| profiled | native_joint | 384/384 | 768/768 | 8,640 |

모든role/pair/membership/triple/queryinput층이정확했다. arm-mode마다이름/순서정규화72기록쌍·288질의쌍,반복0대비이후64기록쌍도모두불변이었다. fulltriple set oracle는numeric실행과별도로계산했다. exact는상위native0회이며동일최초정보를받는명시적symbolic대조다.

288짝은mode와R40의두CPU필드(`prefix_core_cpu_seconds`,`query_core_cpu_seconds`)만제외한전체반환기록이동일했다. underlying kernel+Config의전체Program/drives/initial/tickstate/residual/stable_steps/convergence/cost를canonicalbytes로비교하고,같은digest도전체bytes를검사했다. scalar tolerance로이짝비교기준을완화하지않았다. timer자료는별도metric에두어답경로로흘러가지않는다.

## 계측된 q4 core의 기술적 관측

다음표는**profiled환경의관측값**이다. native열은10%부담검사에미달했으므로plain의병목비중/순위나최적화효과로채택하지않는다. 각칸은3그룹의개별비중중앙값이어서중앙값들의합이정확히100%일필요는없다. 정수원장의합검사는각그룹/기록에서따로통과했다.

| exclusive범주 | joint | factor | exact |
|---|---:|---:|---:|
| 원천 export/guard | 2.769% | 2.779% | 96.769% |
| 회로 문서 생성 | 0.262% | 0.262% | 0.000% |
| Program 객체 생성 | 2.801% | 2.726% | 0.000% |
| Program 검증 | 1.150% | 1.141% | 0.000% |
| 원래 tick 본문 | 52.219% | 52.197% | 0.000% |
| 수렴 제어·관찰·잔여 | 16.348% | 16.323% | 0.000% |
| 결과 plain 변환·구성 잔여 | 12.870% | 12.996% | 0.000% |
| Program digest | 8.995% | 9.050% | 0.000% |
| membership 외피 잔여 | 0.392% | 0.392% | 0.000% |
| 필드 encoding | 0.254% | 0.254% | 0.000% |
| producer 외피 잔여 | 0.133% | 0.093% | 0.000% |
| consumer 외피 잔여 | 0.067% | 0.120% | 0.000% |
| 입력 계약 검사 | 0.048% | 0.048% | 1.000% |
| kernel 외피 잔여 | 1.108% | 1.111% | 0.000% |
| core 잔여 | 0.392% | 0.426% | 1.290% |
| observer 설치·복원·snapshot | 0.030% | 0.031% | 0.936% |

native의계측환경에서는tick범주가약52%로최대였지만,허용선미달로`followup_priority=null`을유지했다. tick은incoming구성·전체원래tick본문과counter를포함하며순수신경산술만의시간이아니다. settleexclusive는validate/tick이외의controller·trace복사·잔여·hook부담을포함한다. result_materialize는Program/Convergence plain변환·cost/result구성의잔여이고Program.digest는별도계측했다. 프로파일러의전체교란을각범주에서공짜로빼거나plain시간을복원했다고하지않는다.

생산/소비함수의inclusive구간은별도로관측했다. 이값들은위exclusive분해와겹치므로서로더하지않는다.

| profiled방식 | producer inclusive/core | consumer inclusive/core |
|---|---:|---:|
| native_joint | 91.854% | 4.778% |
| native_factor | 87.272% | 9.338% |

깊은세부범주는q4 core전체에서합산했으며producer만의원인기여도로동일시하지않는다. exact는native producer/consumer를쓰지않으므로두anchor가0이며,원천export/guard후symbolic계산경로를직접실행한다. exact에서허용된source_export_guard우선후보도이지정경로/입력에서의관측에한정하며검사삭제나출처계약완화를정당화하지않는다.

## 실제 자원·비용과 근거 검산

AI Research SSH의새전용폴더에서원천24+수치34,560=**34,584회settle·1,044,216tick**을실행했다. 준비/계산/감사3단계exit0,봉인포함 **70.469707초**였다. 65고유trace를lossless저장했으며계산은생략하지않았다.

| 단계 | wall(s) | process CPU(s) | exit | ru_maxrss_raw |
|---|---:|---:|---:|---:|
| preparation | 0.316221 | 0.314190 | 0 | 23712 |
| work | 61.473234 | 61.437513 | 0 | 29540 |
| audit | 8.481538 | 8.448023 | 0 | 35984 |

관측coreCPU합45.204479초,저장16.009480초,원천0.041531초,work잔여0.182023초의합이work processCPU와맞는다. audit잔여0.599252초를포함한감사phase·준비·부모봉인CPU0.215078초·launcher영수증시점CPU0.075713초를별도보존했다. 전체관측processCPU합은70.490516초다. 네트워크전송/로컬문서작업이나OS전체추적·standalone제품비용측정은아니다. 비용비교를위해부담을제외하거나미래수명에임의상각하지않았다.

R40q4실측에서plain1회+profiled계획부담1.25를선택해계획work65.161155초/전체87.182189초를만들었다. 안전계수3·60초올림으로단계240초/전체300초를고정했다. 자원계획1.25는해석허용선1.10과별개다. raw128MiB/cache192MiB/건당128KiB/부모·자식AS각512MiB/파일130·8MiB/LRU18/고유trace<=34,560은운영중단선이며완료·CPU/RSS·통계성능을보장하지않는다. RSS와메모리점관측은원시값으로보존했으며단위변환·미래가용량보장은주장하지않는다.

준비503Boolean검사·9synthetic외피대조·정상/예외복원·중첩차단·metadata변조8개·joint소비자격리10개·factor격리12개·synthetic codec왕복2개·저장/cache/상한변조9개·LRU18·Python5파일AST/UTF8/LF를확인했다. 합성대조의settle/tick은fake이며실제수치정확성의증거가아니다. 실제로컬native0회다.

서버JSON88개/2,562,646bytes를수신했고manifest대상87개JSON의원본크기·SHA가모두직접일치했다. 이번에는adapter마스킹이나복원예외가없었다. manifest는자기해시대상밖이며서버ZIP·빈stdout/stderr6개는수신하지않았다. 모든native tick/판단/계측자료는수신JSON에있다. source161개/input128pin도변하지않았다.

로컬에서65trace전체와34,560물리참조의scalar/controller/cost,원천24개의primitive proof,576기록/2304출력/288짝의전체bytes·288계측원장의배타합·호출/tick/복원수를검산했다. 최대별도scalar오차1.7347234759768071e-18는고정1e-14이내다. semantic변조12개·계측변조5개·실제짝비교의kernelref변조1개를거부했고서버/로컬집계가일치했다.

검산과CS검토는작성자의별도자료재계산이며독립감사가아니다. CS bundle34파일/필수3의무PASS는참조·원시해시결속을확인하며native계측교란허용선통과나실행/정확성/권한/외부host attestation을자동증명하지않는다. 도구의upstream완전성은unknown이고동일채널해시도독립호스트증명이아니다.

## 판단과 다음 후보

현재계측외피는이유한조건의전체수치이력을보존했다. 그러나native계측부담13.9–14.5%때문에사전10%조건을충족하지못해native병목판정은보류한다. exact의source_export_guard만별도경로의유한조사후보로남긴다. 기준을낮추거나tick최대비중을근거로지금native최적화를채택하지않는다. R40의비용음성결과를구제하는재평가가아니다.

후속후보는매tick등의미세probe를줄인더거친측정경계가전체trace동치를유지하면서10%부담선안에드는지확인하는별도계약이다. 원래settle전체와Program구축/결과구성등큰구간을먼저분리하는방법을검토할수있다. 이는계측방법의후속후보이며아직구현·실행하지않았다. 새로운계약/중복확인없이이번R41을재실행하거나원래검사·출처·수식·임계값을변경하지않는다.

## 근거

- [설계](DESIGN.ko.md), [결과별판단](OUTCOMES.ko.md), [동결입력](frozen_spec.json), [비용상한](BUDGET.ko.md)
- [계측부담·전체원장·판정](../../evidence/producer-profile-20261020-r41/analysis.json), [수신검산](../../evidence/producer-profile-20261020-r41/receipt-verification.json), [로컬검산](../../evidence/producer-profile-20261020-r41/local-verification.json)
- [서버결과](../../evidence/producer-profile-20261020-r41/raw/result.json), [원본manifest](../../evidence/producer-profile-20261020-r41/raw/manifest.json), [물리호출ledger](../../evidence/producer-profile-20261020-r41/raw/work-ledger.json), [실행·짝비교요약](../../evidence/producer-profile-20261020-r41/raw/summary.json)
- [계측·복원외피](../../tools/r41_producer_profile/runtime.py), [oracle·짝·원장검산](../../tools/r41_producer_profile/verify.py), [실험실행](../../tools/r41_producer_profile/probe.py)
- [작성자CS검토](../../evidence/producer-profile-20261020-r41/cs/review.json), [bundle검사](../../evidence/producer-profile-20261020-r41/cs/bundle-check.json), [비중복근거](../../evidence/producer-profile-20261020-r41/nonduplication.json)
