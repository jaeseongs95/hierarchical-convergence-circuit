# EXP-82 / R36: 실제로 겹치는 조건에서 논리 조합의 의미 보존

**native와 같은 정보를 쓰는 exact가 각각 2,496/2,496조건을 맞혔다.** native의 역할 일치 중간값29,952개와 AST 중간값9,984개도 전부 정확했다. C와 T 각각 실제8개 leaf 패턴에서 여섯 논리식이 서로 구별됐고, 이름·후보 순서 변형192쌍의 정규화한 결과도 모두 같았다. R35에서 빠졌던 ‘여러 leaf가 동시에 참인 실제 입력’의 검증 공백을 닫았다.

이는 고정된 **단일변수·두 완전 후보·여섯 논리식·초기상태0.5** 문법에 대한 유한 공학 결과다. 학습된 회로, 다변수 joint binding, 임의 CSP, 확률 교정, 효율 우위나 운영 도입을 입증하지 않는다. 실행 뒤 입력·생성기·kernel·decoder·threshold를 바꾸거나 native 실험을 다시 실행하지 않았다.

## 비중복 과제와 경계

[R35](../exp-81-compositional-slot/RESULTS.ko.md)는 최종 정답이 모두 맞았지만 실제 세 leaf가 서로 배타적이어서 여섯 AST 중 여러 개가 같은 의미로 축약됐다. 준비 단계의 모든 Boolean 조합 통과만으로 실제 native 조합 범위를 입증할 수 없었다.

R36은 R35 생성기·수식·native 실행·decoder를 그대로 사용한다. 원천의 관계와 목표를 다르게 유지하면서 subject를 두 endpoint에 독립적으로 배치해 실제 겹침을 만든다. 원천28개는 namespace2 × (R후보2 + P0/P1/P2각2 + Q0/Q1/Q2각2)다. 각 원천은 실제 native path와 primitive proof를 가진 조건부 지지다. P와 Q의 서로 다른 predicate·target은 subject가 같아져도 별개 명제를 유지한다.

predicate·target·candidate subject를 확인하는 host guard는 선언한 메타데이터 slot 결속 검사다. 실질적인 candidate.object와 leaf.subject의 일치는 기존3bit native matcher가 계산한다. mask, case ID나 정답을 native 소비자의 인자로 전달하지 않는다. False match는 주어진 leaf 원천과의 join 불일치이며, 세계에서 그 관계가 거짓이라는 증거가 아니다. 조건부 source proof 역시 세계의 진실이나 교정된 확률과 다르다.

최종 T 소비자는 기존 R35 `consume_t`를 그대로 쓴다. 수정 binding과 별도 T를 소비하며 처음 C나 oracle를 받지 않는다. source/proof/config/Program/drive/role/order/revision/packet/contract/T 결속은 저장 데이터에서 다시 검사했다.

## 고정 행렬과 의미 결과

canonical은 C leaf패턴8 × T패턴8 × C AST6 × T AST6 =2,304조건이다. 각 leaf-pattern 쌍의 정해진 AST에 이름·순서 변형3개를 추가한192조건을 합쳐2,496조건을 고정했다. 각 조건에 native와 exact를 적용한 총4,992평가다. 변형을 독립 통계 표본으로 세지 않는다. 모든 입력은 두 후보가 완전하게 주어졌다는 외부 계약이며 누락 감지나 incomplete 정책은 이번 실험의 대상이 아니다.

AST 순서는 leaf0, OR(0,1), AND(0,1), NOT(0), AND(OR(0,1),NOT(2)), OR(AND(0,1),NOT(2))다. 후보0이 mask0..7의 실제 패턴을 받고 후보1은 여집합을 받는다. 다음8bit 문자열은 mask0..7 순서의 진릿값이다. 여섯 기대 함수와 C/T native 함수가 모두 같고 서로 구별된다. 각 phase48/48값이 해결됐다.

| AST | 기대 | native C | native T |
|---|---|---|---|
| 0 | 01010101 | 01010101 | 01010101 |
| 1 | 01110111 | 01110111 | 01110111 |
| 2 | 00010001 | 00010001 | 00010001 |
| 3 | 10101010 | 10101010 | 10101010 |
| 4 | 01110000 | 01110000 | 01110000 |
| 5 | 11110001 | 11110001 | 11110001 |

strict는 상태 종류·선택 인덱스·query 값·사유를 모두 비교한다. 두 방식 모두2,496개 strict/value/kind/reason이 일치했다. native 역할29,952/29,952 및 AST9,984/9,984의 중간 정답도 따로 확인했으므로 중간 오류가 최종 답에 가려진 성공은 없다. 이름과 후보 순서가 달라도 endpoint code로 정규화한 종류·선택·값·사유는192/192쌍 일치했다. 최종 native 상태 분포는 `{"many": 312, "none": 312, "unique": 1872}`이며 사유 분포는 `{"abstain_ambiguous": 234, "abstain_inconsistent": 312, "decided": 1950}`다.

## 실제 계산과 비용

지정한 AI Research SSH의 새 전용 폴더에서 작업자1개·재시도0회로 실행했다. 준비·본 계산·저장 데이터 감사가 모두 exit0이었고, 봉인까지 **132.388706초**였다. source28회와 numeric44,928회를 합쳐 **44,956회 실제 settle·1,442,910tick**을 수행했다. 학습과 세계 측정은0회다.

| 방식 | 상위 native 호출 | 원천 포함 tick | core CPU(s) | 저장 CPU(s) | 배분한 원천 포함 CPU(s) |
|---|---:|---:|---:|---:|---:|
| exact | 0 | 924 | 12.457094 | 0.003395 | 12.653501 |
| native | 44,928 | 1,442,910 | 82.507927 | 27.375657 | 110.076596 |

원천의 실제 비용은924tick·4,620group update·7,392link transmission·CPU 0.051508초다. 원천은 물리적으로 한 번 만들고, 두 방식의 비교에는 각각 한 번의 원천 비용을 배분했다. 위 원천 포함 열을 더한 값을 물리적 총비용이라고 부르지 않는다. core에는 Program 생성·검증, export/guard, encoding·계산·packet/hash가 포함된다. work CPU 122.678589초 중 개별 core/저장과 원천에 배정되지 않은 공통 비용은0.283008초다. 마지막 열은 각 방식에 원천 비용과 공통 비용의 절반을 더한 회계 가정이다. 준비·감사·봉인은 원자료에서 따로 확인한다.

44,928회의 numeric 계산은 전부 실제 실행했다. 전체 kernel+Config의 canonical bytes가 같은 저장 기록만 공유해 **558개 고유 trace**를 남겼다. digest가 같아도 전체 bytes가 다르면 거부하도록 했고, 이를 계산 재사용이나 가속으로 세지 않았다. exact는 같은 원천·AST를 쓰되 상위 native 호출은0회다. 저장 비용은 첫 작성 순서의 영향을 받는다. 단일 고정 순서 실행이므로 통계적 속도 우위는 판정하지 않는다.

## 사전 상한과 검증

상한은 이전 실측을 그대로 복사하지 않았다. [budget.json](budget.json)에 R35 원자료 해시와 call/case/source/고유trace 비율을 고정했다. 계획상 work158.146초·전체171.727초에 명시적으로 선택한 안전계수3과60초 올림을 적용해 단계480초·전체540초를 정했다. raw96MiB는 이전 수신량의 최대 비율에2배 여유와32MiB 올림을 적용했다. 부모/자식 주소공간은 각512MiB, 파일 상한은98/8MiB다. 고유trace≤2692·canonical record≤128KiB, 저장 데이터 LRU18을 별도로 제한했다. 이는 운영 중단선이며 통계적 보장이나 실제 RSS 추정이 아니다. 단계별 `ru_maxrss_raw`는 Linux getrusage 원값으로 저장했으며 단위 변환을 주장하지 않는다.

실행 전 Boolean·구조·입력2,648검사, source slot 변조4개, codec roundtrip2개와 저장/캐시/용량 변조8개를 통과했다. 실제 로컬 native 실행은0회다. 서버 이후 JSON **646개·11,449,630bytes**를 수신했고 manifest 대상 JSON645개의 크기·SHA256이 전부 일치했다. 소스120개도 로컬 pin과 원격 postcheck에서 그대로였다.

저장된 558개 trace를 전체 tick dictionary로 복원해 scalar/controller/상태·카운터와 모든44,928개 물리 참조를 검산했다. 원천28개의 primitive proof와4,992개 출력, 중간값, 별도 집합 oracle,16개 의미·결속 변조를 검사했다. 로컬 최대 scalar 오차는1.1102230246251565e-16이며 고정 tolerance 이내이고 서버 집계와 일치했다. 이는 작성자의 별도 수식·저장 데이터 검산이며 독립 감사가 아니다. CS bundle 검사는 구조와 해시 결속 검사이며 실행·권한·독립성의 증명을 대신하지 않는다.

서버 ZIP과 manifest상 빈 stdout/stderr6개는 수신하지 않았다. 모든 실험 판단과 native tick은 수신한 JSON에 있다. 동일 채널 SHA 일치는 외부 host attestation이 아니고 upstream 완전성을 독립 보장하지 않는다. 기대한 JSON의 이름·개수·크기·해시는 전부 대조했다. 실행 시작 후 OAuth 재인증이 필요했으나 같은 실행의 결과만 조회했으며 실험을 재실행하지 않았다. 완료 전 두 번의 조회에서 아직 없는 완료 파일에 대해 나온 `No such file or directory`는 진행 중 조회 실패이며 실험 실패가 아니다.

## 채택 범위와 다음 방향

사전에 정한 [판별 계획](OUTCOMES.ko.md)의 첫 분기, 즉 모든 역할·AST·최종 출력·함수 구별·변형 불변성이 맞는 결과다. **기존 생성 규칙이 실제로 겹치는 unary 조건의 이번 유한 문법을 보존한다는 결과만 채택한다.** 두 완전 후보·초기0.5·공개 여섯 AST·주어진 typed source 밖으로 확대하지 않는다. 확률 교정, 다른 초기상태, 학습된 표현, 알려지지 않은 누락과 다변수 상관관계는 미검증이다.

다음 비중복 과제는 후보 수나 같은 unary 행렬을 더 늘리는 대신 **여러 결속 변수의 joint 상관관계를 보존하는 조건부 tuple 인터페이스**를 검토하는 것이다. 변수별 허용집합을 따로 압축하면 실제로 없는 교차 tuple을 합성할 수 있다. 따라서 동일한 unary 주변집합을 갖지만 joint 관계가 다른 반례를 먼저 고정하고, 정확한 tuple oracle와 별도 T 소비를 비교해야 한다. 이는 다음 계약의 설계 후보이며 이번 연구에서 구현·검증한 기능으로 세지 않는다. 회로를 학습하거나 계산을 실제 생략하는 연구로 연결할 때는 원천·생성·검증·학습·조회 포함 총비용과 같은 정보의 exact 비교를 새 계약으로 정해야 한다.

## 근거

- [설계](DESIGN.ko.md), [동결 입력](frozen_spec.json), [판별 계획](OUTCOMES.ko.md), [상한 산출](BUDGET.ko.md)
- [집계·비용](../../evidence/overlap-composition-20261020-r36/analysis.json), [로컬 검산](../../evidence/overlap-composition-20261020-r36/local-verification.json), [수신 검산](../../evidence/overlap-composition-20261020-r36/receipt-verification.json)
- [서버 결과](../../evidence/overlap-composition-20261020-r36/raw/result.json), [원래 manifest](../../evidence/overlap-composition-20261020-r36/raw/manifest.json), [호출 ledger](../../evidence/overlap-composition-20261020-r36/raw/work-ledger.json)
- [typed 실행 경계](../../tools/r36_overlap_composition/runtime.py), [기존 생성기](../../tools/r35_compositional_slot/compiler.py), [기존 실행·decoder](../../tools/r35_compositional_slot/runtime.py), [저장 데이터 검산](../../tools/r36_overlap_composition/verify.py)
- [작성자 CS 검토](../../evidence/overlap-composition-20261020-r36/cs/review.json), [bundle 검사](../../evidence/overlap-composition-20261020-r36/cs/bundle-check.json)
