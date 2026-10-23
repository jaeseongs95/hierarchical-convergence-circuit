# EXP-81 / R35 결과: 후보수 확장 양성, 논리조합의 의미 범위는 제한

동일 syntax/count 생성 규칙으로 만든 native 회로와 exact solver가 각각 **864/864조건**의 상태·선택·query 값·사유를 맞혔다. 이 중432조건은 완전한 후보 domain에서의 의미 검사이고,432조건은 명시적 incomplete 입력에 대한 보수적 보류 정책 검사다. R34의 두 후보 전용 문법에서 벗어나 기준 domain3·4와 부정·중첩 syntax를 같은 생성기로 처리했다는 유한 공학 근거다.

그러나 실제 leaf가 서로 배타적이어서 여섯 AST 중 일부는 같은 의미로 축약된다. **고정 행렬은 통과했지만 범용 논리 조합 능력의 채택은 보류한다.** 누락 자동 발견, 학습, 다변수 CSP, 회로 효율 우위나 운영 도입을 보인 결과도 아니다. 검증을 마친 뒤 입력을 바꿔 이 한계를 구제하거나 native를 다시 실행하지 않았다.

## 변경과 비중복성

[R34](../exp-80-feasible-state/RESULTS.ko.md)는 후보별 두 허용 신호를 보존하면 고정된 두 후보 문법에서 해없음/유일/복수와 별도 T 소비가 가능함을 보였다. R35는 하나의 생성기가 공개3bit vocabulary의 역할 일치, 제약 AST, 가변 후보 상태와 모든해 query Program을 만든다. 그래프 모양은 syntax와 후보 수에만 의존한다. numeric host가 role equality나 해집합을 계산해 답을 고치는 방식은 넣지 않았다. core tick/settle, learner와 과거 연구는 그대로 보존했다.

원천24개는 namespace2 × R/S/T각4개의 실제 native path다. source/proof/config/역할/revision을 결속한 조건부 대안이며, path 지지와 실제 세계의 ground truth 또는 확률 교정을 구분한다. 후보마다 C의3match+AST1, 후보 상태1, T의3match+AST1, 최종query1로8n+2번 실제 native settle을 수행한다. 역할 matcher16group, AST4..6group, classifier9..18group, query13..25group은 모두 같은 signed AND/OR 생성 규칙과 공통 kernel을 사용한다. Program 생성·검증도 비용에 포함했다.

최종 `consume_t`는 eligibility와 native coverage activation을 담은 수정 packet 및 독립 T만 받으며 처음 C, case ID, 정답을 받지 않는다. 고정 stable one-hot decoder가 none/unique/many/incomplete와 qtrue/qfalse/empty/mixed/incomplete를 읽는다. 여러 후보라도 query가 같으면 답할 수 있고, 해가 없으면 False 대신 inconsistent로 보류한다.

## 입력과 완전성 계약

864조건은 기준 domain2/3/4 × C AST6 × T AST6 × 이름2 × 순서2 × complete2다. initial은0.5로 고정했고 새 그래프의 다른 초기상태 견고성은 검사하지 않았다. 여섯 AST는 leaf0, OR(0,1), AND(0,1), NOT(0), AND(OR(0,1),NOT(2)), OR(AND(0,1),NOT(2))다. C leaf는 S0/S1/S2, T는 T1/T2/T0에 대응한다. 각864입력에 native와 같은 typed 원천·AST·complete flag의 exact를 적용해 총1,728평가다.

complete=True는 해당 과제가 외부에서 정한 domain의 R 대안을 모두 제공한다는 계약이다. 전체 pool의 다른 domain용 R 원천을 자동 포함하는 뜻이 아니다. False 조건에서는 가장 큰 endpoint 후보를 하나 뺀 뒤 순서를 정해 관측 후보 수가1..3이 된다. complete flag는 연구자가 입력으로 준 신뢰 계약이지 시스템이 알아낸 사실이 아니다. 불완전하면 현재 보이는 답이 우연히 일치하더라도 항상 incomplete로 보류하도록 사전에 정했다. 이 정책의 성공을 알려지지 않은 누락 감지나 최적 정보 추론으로 해석하지 않는다.

## 의미 결과와 실제 범위

strict는 결속 종류·선택 인덱스·query 값·사유가 모두 맞아야 통과한다. `None`만 같고 보류 사유가 틀리면 실패다. native/exact 각각864조건 전부 strict/value/kind/reason이 일치했다.

| 기준 domain | 완전 조건 | native strict | exact strict | 명시적 누락 조건 | native 보류 정확 |
|---|---:|---:|---:|---:|---:|
| 2 | 144 | 144 | 144 | 144 | 144 |
| 3 | 144 | 144 | 144 | 144 | 144 |
| 4 | 144 | 144 | 144 | 144 | 144 |

완전 입력432조건의 native 종류 분포는 `{"many": 264, "none": 72, "unique": 96}`이고, 사유 분포는 `{"abstain_ambiguous": 204, "abstain_inconsistent": 72, "decided": 156}`다. incomplete432조건은 전부 `abstain_incomplete`이며 오확정은0이다. 관측 n=1은 incomplete 조건에만 나타난다. native 실행에서 완전한 단일 후보 domain의 의미까지 검증했다고 주장하지 않는다.

사후 원자료 분석으로 드러난 중요한 한계는 leaf의 배타성이다. C와 T의 세 관측은 서로 다른 endpoint를 가리킨다. 한 candidate는 이 중 최대 하나에만 일치하므로 실제 native AST 입력은 전체2³ Boolean 조합을 실현하지 않는다. 특히 leaf0와 leaf1이 동시에 True인 conjunction은 실제 입력에 없다. AST4는 이 workload에서 OR(0,1)과 같고, AST5도 작은 domain에서는 같은 집합으로 축약된다.

| 기준 domain | C의 실제 leaf 패턴 | C의 서로 다른 AST 의미 | T의 실제 leaf 패턴 | T의 서로 다른 AST 의미 |
|---|---:|---:|---:|---:|
| 2 | 2/8 | 4/6 | 2/8 | 3/6 |
| 3 | 3/8 | 4/6 | 3/8 | 4/6 |
| 4 | 4/8 | 5/6 | 4/8 | 5/6 |

이 표는 각 기준 domain·완전 입력·이름0·순서0의 canonical 조건을 집합 의미로 분석한 것이다. 전체 의미 등가 그룹과 패턴은 analysis.json에 남겼다. 로컬/서버 준비 검사의 모든 Boolean 조합 통과는 실제 native 입력에서 모든 조합을 관측한 증거와 다르다. 여섯 syntax를 여섯 독립 과제로 세지 않으며 이 행렬을 학습된 zero-shot 일반화 표본으로 세지 않는다. 현재 문제는 하나의 결속 변수에 대한 제약과 query이고, 여러 변수의 joint binding이나 상관관계 보존은 검사하지 않았다.

## 실제 계산과 총비용 경계

AI Research SSH 새 R35 폴더에서 worker1/retry0, 전체1800초·단계600초 상한으로 실행했다. 준비·실행·감사3단계 모두 exit0이고 봉인까지 **54.172071초**였다. 원천24 + numeric19008 = **19032회 실제 settle**, 총598480tick이다. 학습·World.measure는0회다.

| 방식 | 상위 native 호출 | 원천 포함 tick | 원천 포함 group update | 원천 포함 link transmission | core CPU(s) | 저장 CPU(s) | 배분한 원천 포함 CPU(s) |
|---|---:|---:|---:|---:|---:|---:|---:|
| exact | 0 | 792 | 3,960 | 6,336 | 4.543134 | 0.001191 | 4.677173 |
| native | 19,008 | 598,480 | 8,212,232 | 21,061,576 | 34.298569 | 12.195674 | 46.627090 |

원천의 실제 비용은792tick·3960group·6336link·CPU 0.043198초다. 물리적으로 한 번 생성하고 각 방식의 원천 포함 비교에 한 번씩 배분했다. 위 원천 포함 열을 합산해 실제 전체 비용이라고 부르지 않는다. core CPU는 source export/guard, native 방식의 Program 생성·검증, 인코딩·계산·packet/hash를 포함한다. 저장 CPU는 trace key·lossless 인코딩·파일 작성 비용이며 첫 작성과 실행 순서에 영향을 받는다. work 프로세스 CPU 51.261065초에서 원천·개별 core/저장에 배정되지 않은 공통 비용은0.179298초다. 마지막 열은 원천 CPU와 공통 비용의1/2을 각 방식에 더한 회계 가정이다. 준비·감사·봉인은 따로 raw result에 기록했다. 고정 교대 순서의 단일 실행이며 순서가 coverage와도 연동되므로 통계적 속도 판정은 하지 않는다.

19008번 numeric 호출은 모두 실제 계산했다. 동일한 전체 kernel+Config digest와 객체 equality가 맞는 기록의 저장만 공유해518개 고유 trace를 남겼다. 모든 physical reference를 합산해 tick/group/link를 계산했다. 저장 공유를 계산 재사용이나 가속으로 세지 않는다. exact의 상위 native는0회이며 동일 원천을 소비한다. 이번 관측으로 학습 포함 효율 우위를 주장하지 않는다.

## 검증과 증거 한계

로컬 준비에서 Boolean·구조·행렬1716검사, synthetic codec roundtrip2개·변조4개,6개 Python 파일 AST/UTF8/LF 검사를 통과했다. 실제 로컬 native 실행은0회다. 서버 이후 JSON537개를 수신해 manifest 대상536개의 원래 byte 수와 SHA256을 모두 대조했다. 수신 JSON은9,010,188bytes다. source105개가 로컬 및 원격 postcheck에서 그대로였다.

518개 고유 trace를 원래 tick dictionary로 복원해 전체 kernel+Config digest를 확인하고 모든19008물리 reference의 비용을 합산했다. 별도 scalar/controller/count 및 원천24개 primitive proof, 역할·Program·drive·AST·순서·packet·coverage·T 결속, 집합 기반 정답을 검사했다. 로컬 최대 scalar 오차는1.1102230246251565e-16로 동결 tolerance 이내이며 서버와 로컬 의미·비용 집계가 같다. revision/origin/eligibility/coverage/selected/C_message/T_hash/value/network_ref/alternative_role의10개 변조를 모두 거부했다. 작성자의 별도 수식·저장 데이터 검산이며 독립 감사자를 통한 검증은 아니다. CS bundle 결과는 해당 파일에 기록하며 구조·원시 해시 결속 검사이지 실행·정확성·권한·독립성의 증명 자체는 아니다.

서버 ZIP 자체와 manifest가 빈 것으로 기록한 stdout/stderr6개는 수신하지 않았다. 실험 판정과 모든 native tick은 수신 JSON에 있다. 동일 채널 manifest 일치는 외부 host attestation이 아니며 SSH upstream 완전성은 독립 보장되지 않는다. 기대한 JSON 목록·개수·크기·해시는 전부 일치했다. source/input/generator/decoder/threshold 사후 수정과 native 재실행은0회다.

## 판정과 다음 연구

가변 후보수와 공개 syntax 생성 규칙은 현재 행렬에서 의미를 보존했다. 이를 유한한 unary 해집합 인터페이스의 공학 결과로 채택한다. 실제 leaf 패턴이 제한돼 있으므로 일반 논리 조합·다변수 추론·자율 계층 형성·학습·운영 core 도입은 보류한다. 준비 Boolean 검사나 명시적 incomplete 정책 성공을 이 미검증 영역의 증거로 이전하지 않는다.

다음 우선 과제는 후보 수만 더 늘리는 것이 아니라 **실제 원천에서 leaf가 겹치는 조건과 중첩 제약의 실효성을 확인하는 것**이다. 서로 다른 관계/목표의 원천으로 여러 leaf가 동시에 True가 되는 경우를 만들어, 서로 같아지는 AST와 구별해야 하는 AST를 사전에 나눈 계약이 필요하다. 그 뒤 여러 결속 변수의 joint 상관관계를 검토한다. 학습 회로나 계산 절약과 연결할 때도 별도 가설·같은 정보의 exact·원천/생성/검증/학습 포함 총비용 계약이 필요하다. 이번 고정 workload를 바꾸어 현재 성공률을 늘리지는 않는다.

## 근거

- [설계](DESIGN.ko.md), [동결 입력·Program·상한](frozen_spec.json)
- [집계·의미 등가·비용](../../evidence/compositional-slot-20261020-r35/analysis.json), [로컬 검산](../../evidence/compositional-slot-20261020-r35/local-verification.json), [수신 검산](../../evidence/compositional-slot-20261020-r35/receipt-verification.json)
- [원래 manifest](../../evidence/compositional-slot-20261020-r35/raw/manifest.json), [물리 호출 ledger](../../evidence/compositional-slot-20261020-r35/raw/work-ledger.json), [서버 단계 결과](../../evidence/compositional-slot-20261020-r35/raw/result.json)
- [문법 생성기](../../tools/r35_compositional_slot/compiler.py), [native/exact 구현](../../tools/r35_compositional_slot/runtime.py), [저장·실행](../../tools/r35_compositional_slot/probe.py), [집합 의미·경계 검사기](../../tools/r35_compositional_slot/verify.py)
- [작성자 CS 검토](../../evidence/compositional-slot-20261020-r35/cs/review.json), [bundle 검사](../../evidence/compositional-slot-20261020-r35/cs/bundle-check.json)
