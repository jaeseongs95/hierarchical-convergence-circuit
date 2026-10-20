# R37 / EXP-83: joint 보존과 주변곱 정보손실이 분리됐다

**native_joint는 1024/1,024조건과 4096/4,096개의 tuple eligibility를 맞혔다.** native_marginal의 원래 full tuple 기준 strict는944/1,024이며, 선언한 주변곱 개입 기준 strict는1024/1,024였다. 추가 보류는80건, 잘못된 확정은0건이다. joint 전체 검사 통과는`True`, native marginal 개입 검사 통과는`True`다.

이는 **주어진 완전2×2폐쇄 관계표와 초기상태0.5**에서의 유한 결과다. 학습, 임의 다변수 CSP, 외부 세계의 참·거짓, 누락 자동 발견, 확률 교정, 계산 재사용·효율 우위나 운영 도입을 입증하지 않는다. 코드·입력·Program·판정 기준을 봉인한 뒤 native 재실행과 사후 튜닝은0회다.

## 비중복 질문과 구현

[R36](../exp-82-overlap-composition/RESULTS.ko.md)은 실제 겹치는 unary 조건에서 여섯 논리함수를 구별했지만 여러 변수의 상관관계는 시험하지 않았다. R37은 X/Y각2값의 공개 domain을 Cartesian으로 열거한4개 가상 assignment를 비교한다. 이는 세계에서 지지된 네 사실이라는 주장이 아니다. C/T 관계의 positive 원천16개(이름2×predicate2×쌍4)는 실제 native path와 조건부 primitive proof로 만든다.

C/T의 각16개 관계표 × 이름2 × 결합 순서2 =1,024조건을 고정하고, native_joint/native_marginal/exact_joint 총3,072평가를 수행했다. 순서 변형은 candidate와 관계행 순서를 함께 역전한다. 모든 domain과 관계목록의 완전성은 외부에서 준 폐쇄표 계약이다. 원천이 목록에 없다는 것은 목록 membership이 없다는 뜻이며 세계 관계가 거짓이라는 증거가 아니다. source의 조건부 지지와 확률 교정도 구분한다.

기존 R35 Builder/3bit equality/pair AND/feasible4/query4와 공통 native kernel을 재사용했다. 각 assignment와 관계행의 X/Y 필드를 별도 native equality 두 개에 넣고 pair AND 뒤 관계행 OR를 계산한다. 새 OR 그래프는 행 수, projection 그래프는 공개 tuple layout만으로 만든다. host는 공개domain 열거·필드별 encoding·메타데이터 검사만 한다. numeric 경로에서 C/T tuple 일치나 feasible 집합을 풀어 답을 고치지 않았다.

native_joint는4개의 joint eligibility를 보존한다. native_marginal은 같은 원래 C를 실제로 계산한 뒤 native OR로 X/Y 주변집합을 만들고 native AND로 재결합하는 **명시적 정보손실 개입**이다. 별도 T 소비자는 binding과 T만 받고 처음 C·case/mask·oracle·source registry를 받지 않는다. C source refs는 출처 결속과 hash에만 쓰며 T의 수치 결정에는 쓰지 않는다. 출처 hash까지 같은 전체 packet byte의 동일성 정리로 확대하지 않는다. exact_joint는 같은 최초 전체 관계 정보의 명시적 symbolic 기준이다.

## 결과: 개입 정합성과 정보손실의 분리

strict는 kind·selected index·value·reason을 모두 비교한다. tuple eligibility는 최종 답과 따로 비교한다. 개입 기준은 native_marginal에는 Cartesian closure oracle, 나머지에는 full tuple oracle이다. 대조군의 full 기준 오답을 개입 구현 오류로 바꾸어 세지 않는다.

| 방식 | full strict | full eligibility | 개입 기준 strict | 추가 보류 | 잘못된 확정 |
|---|---:|---:|---:|---:|---:|
| exact_joint | 1024/1024 | 4096/4096 | 1024/1024 | 0 | 0 |
| native_joint | 1024/1024 | 4096/4096 | 1024/1024 | 0 | 0 |
| native_marginal | 944/1024 | 3584/4096 | 1024/1024 | 80 | 0 |

준비 단계의 symbolic 기대는 marginal full strict944/1024, eligibility3584/4096, 추가보류80/잘못된확정0이었다. 이는 실행 전 예측이며 위 표가 실제 관측이다. joint의 membership·승격·소비가 틀리거나 marginal 개입이 closure와 다르면, 정보손실만의 효과로 채택하지 않도록 사전에 정했다.

| native 방식 | field equality | pair AND | 관계 membership | 주변곱 projection |
|---|---:|---:|---:|---:|
| native_joint | 32768/32768 | 16384/16384 | 8192/8192 | 0/0 |
| native_marginal | 32768/32768 | 16384/16384 | 8192/8192 | 4096/4096 |

최종 답이 맞아도 중간값·eligibility가 틀리면 joint 보존 채택을 보류한다. 중간 단계의 첫 실패 종류도 analysis.json에 남겼다. exact의 중간 native 호출은0이므로 native 중간 검사 성공에 합산하지 않는다.

핵심 반례는 C의 대각선쌍`{(x0,y0),(x1,y1)}`과 교차쌍`{(x0,y1),(x1,y0)}`다. 두 X/Y 주변집합은 모두 같은 전체 domain이다. T가 대각선 관계이면 첫 C의 모든 assignment는 T를 만족하고 둘째는 모두 만족하지 않는다. 주변곱 상태는 두 경우 모두 네 tuple을 허용하므로 이 차이를 잃는다. 관계표mask9/6와 Tmask9/6의 전체16조건/arm 원자료와 관측 답은 analysis.json의 `same_marginals_counterexamples`에 별도로 남겼다.

| 방식 | canonical 서로 다른 eligibility 서명 | 이름·순서 정규화 불변성 |
|---|---:|---:|
| exact_joint | 16 | 768/768 |
| native_joint | 16 | 768/768 |
| native_marginal | 10 | 768/768 |

joint의 기대 서명은16개, 주변곱은10개다. 서명은 canonical T=empty 조건에서 허용 tuple의 endpoint index 집합으로 센다. 모든4개 eligibility의 정답 여부를 함께 검사하므로 동적 보류를 False와 같다고 간주하지 않는다. 이름·순서 변형을 독립 통계 표본으로 세지 않는다.

## 실제 계산·자원·비용

AI Research SSH 새 전용 폴더에서 작업자1개·재시도0회로 실행했다. 준비·본 계산·감사3단계가 exit0이고 봉인까지 **242.630780초**였다. 원천16 + numeric119,808 = **119,824회 실제 settle·3,649,280tick**이다. native_joint의 조건별 호출은12×(|C|+|T|)+10회, marginal은 projection1회가 더 많다. 학습과 세계 측정은0회다.

| 방식 | 상위 native 호출 | 원천 포함 tick | core CPU(s) | 저장 CPU(s) | 배분한 원천 포함 CPU(s) |
|---|---:|---:|---:|---:|---:|
| exact_joint | 0 | 528 | 2.607162 | 0.001419 | 2.725550 |
| native_joint | 59,392 | 1,809,600 | 79.583048 | 29.983900 | 109.683917 |
| native_marginal | 60,416 | 1,840,208 | 81.125810 | 30.531214 | 111.773993 |

원천은 물리적으로 한 번 계산했고 비용은528tick·2,640group·4,224link·CPU0.033438초다. core에는 Program생성·검증, source export/guard, encoding·native 계산·packet/hash를 포함한다. work CPU224.116584초 중 공통 잔여 비용은0.250593초다. 마지막 열은 각 arm에 원천 한 번과 공통 비용1/3을 배분한 회계 가정이다. 원천 포함 열을 합산해 물리적 총비용이라고 부르지 않는다. 준비·감사·봉인은 별도 단계 기록에 있다.

모든119,808numeric 호출은 실제로 수행했다. fullkernel+Config의 canonical bytes가 정확히 같은 기록의 **저장만 공유**해598개 고유trace를 남겼다. 같은 digest도 전체bytes를 확인하며 cache/record 상한을 검사했다. 저장 비용은 첫 작성 순서의 영향을 받고3arms는 고정 회전 순서다. 계산 생략·가속·통계적 속도 우위를 주장하지 않는다.

상한은 R36 raw해시와 호출·평가·원천·trace별 실측 스케일로 정했다. 계획work287.741초/전체308.723초에 선택 안전계수3과60초 올림을 적용해 단계900초·전체960초로 고정했다. raw64MiB/주소공간부모·자식각512MiB/파일66·8MiB/canonical최대1272×128KiB/LRU18은 운영 중단선이며 통계적 보장이나 실제RSS 추정이 아니다. 한평가 최대107개 trace 검산과 장기LRU18을 구분한다. `ru_maxrss_raw`는 플랫폼 원값으로 저장했고 단위 변환을 주장하지 않는다.

## 검증과 한계

사전 준비1,703검사·메타데이터 변조8개·codec roundtrip2개·저장/캐시/용량 변조8개와5개Python파일 AST/UTF8/LF 검사를 통과했다. 로컬 `settle`을 금지했으며 실제 로컬native0회다. 이후 JSON **672개·14,759,997bytes**를 수신하고 manifest 대상671개JSON의 원본 크기·SHA를 전부 대조했다. source126개도 로컬 pin과 원격 postcheck에서 변경되지 않았다.

고유trace598개를 전체 tick dictionary로 복원하고 모든119,808물리참조의 scalar/controller/카운터·생성비용을 검산했다. 원천16개 primitive proof,3,072출력, 별도 set tuple oracle, 역할·변수·Program·drive·packet·revision·T 결속과12개 저장기록 의미 변조를 확인했다. 로컬 최대scalar오차6.9388939039072284e-18는 고정 tolerance이내이며 서버와 로컬 의미·비용집계가 같다. 작성자의 별도 수식·저장 데이터 검산이고 독립 감사가 아니다. CS bundle도 구조·파일 해시 결속 검사이며 실행·권한·독립성 보증을 대신하지 않는다.

서버ZIP과 manifest상 빈 stdout/stderr6개는 수신하지 않았다. 모든 native tick과 판단 자료는 수신JSON에 있다. 동일채널 SHA는 외부host attestation이 아니고 upstream 완전성을 독립 보장하지 않는다. 기대한 JSON 이름·개수·크기·해시는 모두 대조했다. C/T완전목록·공개domain·별도3bit코드를 전제로 하므로 학습된 표현, 알수없는 누락, 겹치는 변수domain, 더 큰관계, 여러관계 조합이나확률교정으로확대하지않는다.

## 다음 판단

이번 완전2×2 문법에서 joint eligibility 보존의 유한 충분성과 주변곱만 남겼을 때의 상관관계 손실을 채택한다. 다음 비중복 후보는 여러 이항 관계를 공유 변수로 연결할 때 개별 관계의 주변 정보 또는 pair 일치만으로는 전역적으로 양립하지 않는 경우다. 별도 계약에서 동일 domain의 joint exact oracle와 cycle/불일치 반례를 먼저 정해야 한다.

이 방향은 후속 계약 후보다. 현재 결과를 일반적 다변수 CSP 해결이나 학습·효율의 성취로 세지 않는다.

## 근거

- [설계](DESIGN.ko.md), [판별 계획](OUTCOMES.ko.md), [동결 입력](frozen_spec.json), [상한 산출](BUDGET.ko.md)
- [관측·반례·비용](../../evidence/joint-tuple-20261020-r37/analysis.json), [로컬 검산](../../evidence/joint-tuple-20261020-r37/local-verification.json), [수신 검산](../../evidence/joint-tuple-20261020-r37/receipt-verification.json)
- [서버 단계 결과](../../evidence/joint-tuple-20261020-r37/raw/result.json), [원본 manifest](../../evidence/joint-tuple-20261020-r37/raw/manifest.json), [계산 ledger](../../evidence/joint-tuple-20261020-r37/raw/work-ledger.json)
- [tuple 실행 경계](../../tools/r37_joint_tuple/runtime.py), [집합 oracle·저장 검산](../../tools/r37_joint_tuple/verify.py), [실험 실행](../../tools/r37_joint_tuple/probe.py)
- [작성자 CS 검토](../../evidence/joint-tuple-20261020-r37/cs/review.json), [bundle 검사](../../evidence/joint-tuple-20261020-r37/cs/bundle-check.json)
