# R39 / EXP-85: 봉인한 결합 상태가 후속 조건부 Z 질의를 보존했다

**결합 상태 방식은 160/160질의를, 주변집합 방식은 136/160질의를 맞혔다.** 주변집합 방식은 XY 조건부 질의 24개에서 원래 하나인 Z 값을 둘 다 허용했다. Z 전체의 허용집합만 묻는 질의는 두 방식 모두32/32였다. 결합 상태 보존 검사 `True`, 주변집합 개입 구현 정합성 검사 `True`다. 같은 최초 정보를 받은 symbolic exact도160/160이다.

AI Research SSH에서 단일 실행을 마쳤고, 준비·실험·감사·봉인까지 **13.058401초**였다. 학습·세계측정·동결 후 재실행·사후튜닝0회다. 이 결과는 선택한8개 완전2×2×2관계표와5종 공개 질의의 유한 검증이다. 표현의 최소성·임의CSP·학습·속도우위·운영채택은 입증하지 않았다.

## 토론으로 정한 질문

[R38](../exp-84-shared-witness/RESULTS.ko.md)은 같은 Z 증인을 사용해 세 관계의 양립성을 보존했지만, 최종 상태는 XY 투영이었다. 이번에는 원래 관계나 중간 메시지에 다시 접근하지 않고, 봉인한 상태만으로 후속 Z 질의를 답할 수 있는지 시험했다.

[MEDIUM 토론](DELIBERATION.ko.md)은 의미·실행 관점2개를 독립 검토한 뒤 서로의 쟁점을 교차 검토했다. 원시 응답 대신 검증한 주장 요약과 출처만 남겼다. Coordinator가 근거를 확인했으며 완전 독립 감사는 아니다. 교차 검토에서 대각 조건만으로는 XY 위치 교환 오류를 놓칠 수 있어, 동결 전에 교차 XY 양성 대조를 추가했다. 별도 Judge는 이 강도에서 요구되지 않았고 생성하지 않았다.

R(X,Y), S(Y,Z), U(X,Z)의 mask조합은 (9,9,9), (9,6,6), (9,5,5), (9,10,10), (9,9,6), (1,1,1), (1,3,3), (6,9,6)이다. 이름2×관계행·XY배치 순서2를 적용해32맥락을 만든다. 각 맥락에서 공개 XY4위치별 허용Z질의4개와 Z전체질의1개를 묻는다. 총160맥락-질의쌍×3방식=480출력을96개 arm기록에 보존했다. 480개 서로 다른 질의나 독립 통계표본으로 세지 않는다.

## 허용한 정보와 계산 경계

세 변수는 서로 겹치지 않는2값 domain이며, 표의 완전성은 외부 폐쇄계약이다. 가상 assignment는 세계에서 지지된 사실이 아니고, 목록 부재는 세계의 부정 증거가 아니다. 초기값0.5·설정·임계값·후보상한·기존 수렴기는 고정했다. 이름 변형의 문자열은 다르지만 필드 code 대응은 같다. Z의 공개 순서0,1은 고정한다.

24개 fresh conditional path 원천과 기존 R37 field membership을 사용해 세 관계의 수치표를 만든다. native_joint는 기존3leaf AND로 R·S·U를 같은 X,Y,Z에서 결합해 두 Z별 XY4 slice, 총8수치를 보존한다. native_compact는 **같은8수치를 먼저 실제 계산한 다음**, native OR로 XY4와 Z2, 총6수치만 남긴다. 개입 arm에 원래 관계 계산을 생략하는 이득을 주지 않았다.

생산자는 질의를 입력받지 않고 맥락당 한 번 상태를 봉인한다. 소비자는 선언한 numeric payload·공개 질의slot·표현종류·고정설정/Program/초기값만 받는다. 원래 사실·case·mask·중간메시지·출처hash·등록부는 접근할 수 없다. 바깥 metadata와 hash는 보관·변조 검사용이며 답을 고르는 분기가 아니다. 다섯 질의 전후 payload 및 봉인 hash가 같음을 확인했다.

조건부 질의에서 joint는 공개 XYslot의 두 Z수치를 기존 feasible2에 전달한다. host가 관계의 답이나 argmax를 계산하지 않는다. compact는 XYslot수치와 각 Z주변수치를 native AND한 뒤 같은 feasible2를 쓴다. 전체Z질의에서는 joint가 각slice를 native OR4로 투영하며 compact는 저장한 Z2를 사용한다. 각 질의의 회로 초기상태는 독립 재설정한다.

## 관측과 오류의 의미

별도 set oracle는 원래8개 triple을 직접 검사한다. full strict는 두 Z eligibility·none/unique/many·선택위치가 모두 맞아야 성공이다. compact의 별도 개입 oracle는 πXY(T)×πZ(T)이며, 이 oracle와 원래 full oracle를 구분한다. 주변집합의 정보 손실과 구현 불량을 같은 것으로 집계하지 않는다.

| 방식 | full strict | Z eligibility | XY조건부 | Z전체 | 개입 strict | 추가/누락 Z |
|---|---:|---:|---:|---:|---:|---:|
| exact_joint | 160/160 | 320/320 | 128/128 | 32/32 | 160/160 | 0/0 |
| native_compact | 136/160 | 296/320 | 104/128 | 32/32 | 160/160 | 24/0 |
| native_joint | 160/160 | 320/320 | 128/128 | 32/32 | 160/160 | 0/0 |

24개 full 실패는 모두 `unique → many`였다. 잘못된 하나의 Z를 확정하거나 원래 허용된 Z를 버린 경우는 없었다. compact는 선언한 개입 oracle160/160을 맞혔으므로, 이번 경계에서는 의도한 주변집합 손실이 나타난 것으로 판단한다. 실제 수치결과가 실행 전 Boolean 기대136/160·296/320·추가Z24와 일치했다. Boolean 준비검사 자체를 수치검증 근거로 세지는 않는다.

| 방식 | 필드 equality | pair AND | membership | triple AND | 투영 | 질의 입력 |
|---|---:|---:|---:|---:|---:|---:|
| native_compact | 1408/1408 | 704/704 | 384/384 | 256/256 | 192/192 | 576/576 |
| native_joint | 1408/1408 | 704/704 | 384/384 | 256/256 | 0/0 | 384/384 |

이름·순서를 정규화한24맥락쌍/120질의쌍은 arm마다 전부 불변이었다. 모든 중간층이 맞는지 별도로 확인했고 첫 실패층은 없었다. 원래 oracle 기준 최종 답의 실패를 숨기지 않았다.

R=S=U=9의 해는 {000,111}, R=9,S=6,U=6의 해는 {001,110}이다. XY허용집합 {00,11}와 Z허용집합 {0,1}는 같지만 XY=00의 답은 Z=0과 Z=1로 반대다. (6,9,6)의 교차XY 대조도 함께 검산했다. `analysis.json`에 모든 변형·질의·고정 margin의 semantic payload signature를 남겼다. **원시 packet이나 모든 연속수치가 같다는 주장, 정보이론적 불가능성 증명은 아니다.** 고정한 의미적 support표현과 수치 판독에서 관측한 충돌이다.

## 실제 비용과 자원

native_joint의 맥락당 상위호출은12L+27, compact는12L+39이며 L=|R|+|S|+|U|다. 32맥락에서 상위6,336회와 원천24회, 총 **6,360회 settle·190,552tick**을 실제 실행했다. exact는 상위 native0회다. 결합 상태를 보존했다는 의미에서의 질의 재사용이며, 원천 계산이나 native 연산을 건너뛰는 가속은 수행하지 않았다.

| 방식 | 상위 native호출 | 원천 포함 tick | core CPU(s) | 저장 CPU(s) | 배분한 원천 포함 CPU(s) |
|---|---:|---:|---:|---:|---:|
| exact_joint | 0 | 792 | 0.111545 | 0.000050 | 0.198842 |
| native_compact | 3,360 | 100,796 | 3.680476 | 1.468947 | 5.236670 |
| native_joint | 2,976 | 90,548 | 3.505432 | 1.415876 | 5.008554 |

원천은 CPU0.042668초·792tick·3,960group·6,336link다. core는 Program 생성·검증, encoding, native 연산, packet/hash 및 제어비용을 포함한다. work CPU10.358730초의 공통 잔여는0.133736초다. 마지막 열은 원천 한 번을 각arm에 부과하고 공통비용1/3을 배분한 회계 가정이다. 이 열을 더해 실제 총비용으로 해석하지 않는다. 단일 고정 실행이며 통계적 속도 비교가 아니다.

| 단계 | wall(s) | process CPU(s) | exit | ru_maxrss_raw |
|---|---:|---:|---:|---:|
| preparation | 0.316120 | 0.306014 | 0 | 23840 |
| work | 10.384167 | 10.358730 | 0 | 30192 |
| audit | 2.170317 | 2.126815 | 0 | 27332 |

봉인 포함 전체시간에는 별도 상위 프로세스 비용도 들어간다. RSS값은 원시 platform-native 값이며 단위 변환이나 절대 메모리 보장을 주장하지 않는다. 모든 계산을 실행하고 fullkernel+Config exactbytes가 같은 trace의 **저장만** 공유해131개를 남겼다. 같은 digest도 전체 bytes를 비교했다. 저장비용은 첫 기록 순서 영향을 받으며 arm순서는 고정 회전이다.

R38 실측의 원천·호출·질의·기록비용을 따로 비례시킨 계획치는 work10.844603초/전체44.805885초였다. 기타 단계 잔여는 줄이지 않았다. 선택안전계수3·60초올림·최소단계120초로 단계120초/전체180초를 고정했다. 작업자1·재시도0, raw128MiB/cache192MiB/건당128KiB/부모·자식AS각512MiB/파일130·8MiB/LRU18은 운영 중단선이다. 고유trace≤6,336은 호출수에 따른 논리상한이며 byte상한이 먼저 중단시킬 수도 있다. 메모리점관측과 계획치는 이후 가용량이나 완료·성능을 보장하지 않는다.

## 검산·실패 기록·제약

준비599검사·metadata변조8개·소비자정보격리10개·synthetic codec왕복2개·저장/cache/용량변조9개·Python5파일AST/UTF8/LF를 확인했다. 준비 중 Boolean stub에 기존 onehot이 요구하는 `convergence`metadata가 빠져 `KeyError: 'convergence'`가 났고, 동결 전에 stub만 수정해 새 준비폴더에서 통과했다. native회로·임계값은 바꾸지 않았다. 새 sandbox 계정의 Git소유자 불일치는 해당 repo에 한정한 프로세스 설정으로 해결했고 전역설정은 바꾸지 않았다.

JSON143개/1,392,416bytes를 수신했다. manifest대상142개 중141개는 수신bytes의 크기·SHA가 직접 일치한다. 출처검사표1개는 SSHadapter가 공개문서경로 한 곳을 `[REDACTED:entropy:39].ko.md`로 마스킹해 최초 원본해시 대조가 실패했다. 수신본을 그대로 보존하고, 동결144파일 목록에 이미 있는 공개경로 `experiments/exp-85-z-query/DELIBERATION.ko.md`를 넣은 **별도 복원본**의6,753bytes·SHA가 원본manifest와 정확히 일치함을 확인했다. 이는 metadata복원이며 원본bytes를 직접 수신했다고 세지 않는다. manifest는 자기 자신의 해시 대상이 아니다. 서버ZIP·빈stdout/stderr6개는 받지 않았다.

모든native tick자료와96기록/480출력은 수신한JSON에 있다. 전체131trace를 lossless복원하고6,336물리참조·24원천의 scalar/controller/cost/proof 및 Program/drive/initial/packet/revision/봉인/출처를 검산했다. 최대scalar오차2.7755575615628914e-17는 고정1e-14이내다. 서버와 로컬 의미·비용집계가 일치한다. 저장기록 의미변조12개도 모두 거부했다. source144개/input110pin은 변하지 않았으며 원본/복원 출처검사표의144flag도 일치했다. 검산과 CS검토는 작성자의 별도 자료 재계산이며 **독립 감사가 아니다**. CS bundle27개파일/필수의무3개 PASS는 참조·원시해시 결속을 확인하며 실행·정확성·권한을 독립 보증하지 않는다.

SSH 재조회는 마스킹된 metadata1개 확인뿐이며 native실행 재시도는0회다. 동일채널해시는 외부host attestation이나 upstream완전성의 독립보장이 아니다. 기존 폭넓은512/608조건 결과로 이번 새 질의의 검증범위를 확대하지 않는다. 다른 관계표 크기·큰domain·불완전표·확률적 자료·임의후속질의는 검증하지 않았다.

## 다음 연구의 조건

이번 유한 질의군에서는 Z별 결합slice를 보존하는 방식을 정확성 기준으로 유지한다. XY·Z주변집합만 보존한 상태는 조건부Z질의용으로 채택하지 않는다. 다음 비중복 후보는 **원래 factor 또는 separator를 보존한 상태가 같은 질의정보 경계에서 답을 보존하면서, 생산·봉인·질의·검산을 포함한 전체비용을 줄이는가**다. 더 작은 표현이라는 이유만으로 채택하지 않으며, 동일 최초정보의 exact와 결합slice 기준, 불일치·질의손익분기를 먼저 고정하는 별도 계약이 필요하다. 최소표현·효율우위는 다음 실험 전에는 주장하지 않는다.

## 근거

- [토론](DELIBERATION.ko.md), [설계](DESIGN.ko.md), [결과별 판단](OUTCOMES.ko.md), [동결입력](frozen_spec.json), [비용상한](BUDGET.ko.md)
- [집계·충돌·비용](../../evidence/z-query-20261020-r39/analysis.json), [수신검산](../../evidence/z-query-20261020-r39/receipt-verification.json), [로컬검산](../../evidence/z-query-20261020-r39/local-verification.json)
- [마스킹 복원검증](../../evidence/z-query-20261020-r39/restoration-verification.json), [별도 복원본](../../evidence/z-query-20261020-r39/restored-source-postcheck.json)
- [서버결과](../../evidence/z-query-20261020-r39/raw/result.json), [원본manifest](../../evidence/z-query-20261020-r39/raw/manifest.json), [호출ledger](../../evidence/z-query-20261020-r39/raw/work-ledger.json)
- [실행경계](../../tools/r39_z_query/runtime.py), [oracle·검산](../../tools/r39_z_query/verify.py), [실험실행](../../tools/r39_z_query/probe.py)
- [작성자CS검토](../../evidence/z-query-20261020-r39/cs/review.json), [bundle검사](../../evidence/z-query-20261020-r39/cs/bundle-check.json)
