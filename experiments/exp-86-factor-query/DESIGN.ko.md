# R40 / EXP-86: factor를 보존한 후속 질의와 전체비용

R39에서 결합Z slice는160/160, XY/Z주변집합은136/160질의를 맞혔다. 이번 비중복 질문은 R4/S4/U4 factor를 남긴 상태도 같은 조건부Z 답을 보존하며, 질의가 적을 때 생산·봉인·질의·저장·검산을 합한 비용을 줄이는가다. R39에서 정한 후속 후보의 직접 측정이므로 새 방향성 패널은 반복하지 않는다. 기존 유한32맥락/회로/초기값/원천을 유지하고, 정보경계와 측정계약을 먼저 고정한다.

선택한8관계표×이름2×행순서2=32맥락이다. 완전 폐쇄2×2×2domain/initial0.5는 외부계약이며 가상assignment는 세계에서 지지된 사실이 아니고 목록부재는 세계 부정증거가 아니다. 24fresh conditional path원천은 실제native로 생성한다. R37fieldmembership/R39삼항AND·OR4·feasible2/기존수렴기를 그대로 쓴다.

native_joint는 세 membership표를 계산한 뒤 같은XYZ의8개nativeAND값을 Z별XY4 slice로 봉인한다. native_factor는 세 membership표12개 수치를 바로 봉인하고 질의 시 필요한 sameXYZ AND를 계산한다. factor12수치는joint8수치보다 크므로 압축·최소표현이라고 하지 않는다. exact_joint는 같은최초정보의 명시적symbolic fulltriple기준이다.

두native producer는query를 받지 않는다. 행순서역전은 공개정수순열로 수치배열을canonical XY00/01/10/11순서로 바꿔 보존한다. 소비자는 numericpayload·공개queryslot·representation·fixedcfg/docs/initial만 받고 원래fact/domain문자열/case/mask/message/출처hash/registry는 받지 않는다. 바깥bindinghash는 보관·불변성검사이며 답분기에 쓰지 않는다. factor조건부는공개slot에서x,y를정수배선하고z0/1의Rxy,Syz,Uxz를nativeAND한뒤기존feasible2로판독한다. unary는8triple을계산하고z별OR4뒤같은분류기를쓴다. host가관계정답/argmax를계산하거나숫자를수리하지않는다.

부하는q1=조건부slot0, q2=slot0/1, q4=slot0/1/2/3, q8=slot0/1/2/3두번, u1=전체Z1회다. **각부하마다생산자를새로실행**하고같은봉인상태로부하안의질의만소비한다. q8의반복질의도매번native실행하며답cache는없다. 3고정반복을실행하고(caseindex+workloadindex+repeat)%3으로arm순서를회전한다. 32×5×3×3=1440기록, 32×16×3×3=4608출력이다. 이는4608서로다른질의나독립통계표본이아니다.

L=세관계행수합, B=12L+12 membership호출이다. joint는B+8생산호출과조건부당1/unary당3호출, factor는B생산호출과조건부당3/unary당11호출이다. 조건부호출수는Q=4에서같고Q<4에서factor가적으며Q>4에서많다. u1은동수다. 이론적호출수교차점을실제CPU교차점으로바꾸어말하지않는다. 총85824numeric+24source=85848수렴호출을실행한다. fullkernel+Config exactbytes가같은trace의저장만공유한다.

독립setoracle는원래8triple을동시에확인한다. 모든role/pair/membership/triple/queryinput/최종Zeligibility·none/unique/many/selected를검산한다. namespace/order변형과3반복의의미불변성을따로검사한다. source/Program/drive/initial/봉인/원천역할/물리참조/trace복원·scalar/controller/proof/cost및metadata/consumer격리/저장가드를검사한다. 실제오류는보존하며동결후native재실행·retune하지않는다.

coreCPU에는원천exportguard·Program생성/검증·생산/봉인·모든질의가포함된다. prefix/queryCPU를추가분리하고저장CPU·기록별감사CPU를계측한다. 공통원천·준비·work잔여·감사잔여·부모봉인·launcher의관측CPU는5부하×3arms×3반복=45개그룹에동일1/45로배분한다. 각그룹은같은32맥락이며이배분합은물리CPU합과맞춰검산한다. 비용은pool된실험의명시적회계가정이며standalone제품/통신/로컬문서작업비용측정이아니다. rawRSS와전체wall도별도보고한다. 분류성공/호출감소만으로효율을채택하지않는다.

사전채택조건: 모든품질·출처·검산·상한검사가맞고, 부하별32맥락을합한factor/joint총배분CPU가3쌍반복각각0.95이하일때만해당유한부하의후속후보로남긴다. 5%는선택한실무판별선이며통계적유의수준/신뢰구간이아니다. 전체범위나운영채택·최소표현·학습·일반CSP·통계적속도우위로확대하지않는다. exact의동일정보비용도함께공개한다.
