# EXP-80 / R34 결과: 해집합 상태 보존과 모든해 후속 query

후보별 두 허용 신호를 보존한 native 회로는 동결한 **576조건 모두에서 결속 상태·선택·후속 답·판정 사유가 exact 의미와 일치**했다. 차이 신호만 남긴 개입군은432조건만 일치했다. 해가 없는144조건을 모두 복수해로 오인한 것이 실패 원인이다. 일반 exact solver도576조건 모두 맞혔고 측정된 CPU 비용이 더 작았다. 따라서 이번 결과는 현재의 두 후보 문법에서 필요한 정보와 안전한 보류 조건을 지지한다. 회로의 일반 알고리즘 우위나 계산 절약을 보인 결과로 확대하지 않는다.

## 무엇을 새로 확인했나

[R33](../exp-79-typed-feedback/RESULTS.ko.md)은 유일한 hard 결속에서는 선택과 별도 T 소비가 가능했지만, 복수해·해없음에서는 strict0/144였다. R34는 두 compatibility의 공통성분을 남겨 `none/u0/u1/many`를 native7group 회로로 구분하고, 별도 T의 답이 모든 허용 결속에서 같을 때만 native15group 회로가 확정하도록 했다. 최종 `consume_t`는 수정된 eligibility packet과 T만 받으며 처음 C, oracle, case ID를 받지 않는다. host의 수리나 의미 기반 후보 제거는 numeric 경로에 없다.

namespace2에서 R/S/T의 원천12개를 실제 native path로 새로 생성했다. 이 positive proof는 완결된 대안 후보를 조건부로 지지한다. 두 후보가 실제 세계에서 동시에 참이라는 증명이나 activation의 확률 교정은 아니다. core tick/settle 및 과거 연구는 바꾸지 않았다. 새 상위 논증을 core primitive proof registry에 등록했다고 주장하지 않는다.

576조건은 C4×T4×이름2×순서2×initial3×softprior3이며 각 조건에 full/delta/exact를 적용해 총1,728평가다. softprior는 hard 허용집합에 적용하지 않는 선호 metadata다. 따라서 이 변형을 가중 prior에 대한 추론 견고성이나 독립 표본으로 해석하지 않는다. delta는 `[0.5-d/2,0.5+d/2]`로 공통성분만 제거하고 full과 동일한 후속 회로·decoder를 사용한다. 정보가 적은 인과 개입군이며, 충분한 일반 대조군은 같은 hard 정보를 받는 exact다. 설계·입력·threshold·decoder·source98개는 실행 전에 동결했고 사후 수정과 native 재실행은0회였다.

## 의미 결과

strict는 결속 종류·선택 인덱스·query 값·사유가 모두 맞아야 통과한다. query 값의 `None`만 같아도 사유가 틀리면 strict 실패다.

| 방식 | strict | 결속 종류 | query 값 | query 사유 |
|---|---:|---:|---:|---:|
| full: 두 신호 보존 | 576/576 | 576/576 | 576/576 | 576/576 |
| delta: 공통성분 제거 | 432/576 | 432/576 | 504/576 | 432/576 |
| exact solver | 576/576 | 576/576 | 576/576 | 576/576 |

| C 상태 | 조건 수 | full strict | delta strict | exact strict |
|---|---:|---:|---:|---:|
| one0: 한 후보 허용 |144|144|144|144|
| one1: 다른 후보 허용 |144|144|144|144|
| either: 둘 다 허용 |144|144|144|144|
| both: 둘 다 금지 |144|144|0|144|

복수해144조건 중 T one0/one1의72조건은 후보에 따라 답이 달라 ambiguous로 보류했다. T either/both의72조건은 모든 후보에서 각각 True/False이므로 답을 확정했다. “결속이 유일해야 질문에 답할 수 있다”는 제한이 이 문법에서는 필요하지 않다. 해가 없는144조건은 모두 inconsistent로 보류해야 한다. full은 이 구분을 지켰다. delta는 이를 모두 many로 분류해72조건에서 부당하게 True/False를 답하고, 나머지72조건에서는 잘못된 ambiguous 사유를 냈다. 이 음성 결과를 원자료와 집계에 보존했다.

## 실제 계산과 비용

AI Research SSH의 새 R34 폴더에서 worker1/retry0, 전체1800초·단계600초 상한으로 실행했다. 준비·실행·감사3단계 모두 exit0이며 봉인까지 **19.654798초**였다. 실제 native 호출은 원천12 + full3456 + delta3456 = **6924회**, 총222108tick이다. 학습과 World.measure는0회다. exact의 상위 native 호출은0회지만 같은 native 원천을 소비한다.

| 방식 | 상위 native 호출 | 원천 포함 tick | 원천 포함 group update | 원천 포함 link transmission | core CPU(s) | 저장 CPU(s) | 배분한 원천 포함 CPU(s) |
|---|---:|---:|---:|---:|---:|---:|---:|
| delta | 3,456 | 114,636 | 998,460 | 2,771,808 | 6.331136 | 1.631727 | 8.043183 |
| exact | 0 | 396 | 1,980 | 3,168 | 2.164924 | 0.000780 | 2.246023 |
| full | 3,456 | 107,868 | 948,012 | 2,627,232 | 6.166298 | 1.587558 | 7.834176 |

원천의 물리 비용은396tick·1980group·3168link·CPU 0.029003초이고 실제로 한 번만 생성했다. 위 원천 포함 열은 각 방식이 이를 한 번 부담한다는 비교용 배분이다. 실제 총합을 구할 때 세 번 더하지 않는다. core CPU에는 원천 export/guard, 인코딩, 회로 계산과 packet/hash 작업이 포함된다. 저장 CPU는 기록 key·손실 없는 인코딩·고유 파일 작성 비용이며 첫 작성 방식과 실행 순서에 영향을 받는다. work 프로세스 CPU는18.065377초, 기록별 core/저장 및 원천에 배정되지 않은 공통 비용은0.153951초다. 마지막 열은 원천 CPU와 이 공통 비용의1/3을 각 방식에 더한 회계 가정이다. 준비·별도 감사·봉인은 per-arm 열에서 제외하고 raw result에 따로 남겼다. 단일 고정 순서 실행이므로 통계적 속도 판정은 하지 않는다. 학습비용은0이지만 일반화·효율 우위를 뜻하지 않는다.

6912개의 numeric 호출은 모두 실제 수행했다. 전체 kernel+Config digest와 객체 equality가 일치하는 기록만 저장 공간을 공유해219개 고유 trace로 남겼다. 각 물리 호출의6개 reference와 원천12개를 기준으로 tick/group/link를 합산했다. 저장 공유는 계산 재사용이나 가속이 아니다.

## 검증과 증거의 범위

로컬 준비에서 Boolean/행렬616검사 및 synthetic codec roundtrip·변조 검사를 통과했고 로컬 native 실행은0회였다. 서버 완료 후 JSON238개를 수신했으며 manifest 대상237개의 원래 byte 수와 SHA256을 모두 대조했다. JSON 총수신량은4,249,051bytes다. frozen source98개 및 source-postcheck도 일치한다.

고유 trace219개를 원래 tick dictionary로 손실 없이 복원해 전체 kernel+Config digest를 확인했다. 별도 scalar/controller/count 재계산과 source primitive proof·역할·revision·메시지·query 입력·집합 기반 정답 대조를 수행했다. 최대 scalar 오차는3.3306690738754696e-16로 동결 tolerance 이내이며, 서버와 로컬 의미·비용 집계가 일치했다. revision/source/eligibility/selected/message/T_hash/value/network_ref의8변조를 모두 거부했다. 이 검산은 구현 작성자가 수행한 별도 수식·저장 데이터 검산이며 독립 감사자를 통한 검증은 아니다. CS bundle check는 PASS/필수 의무3개/원자료23개 해시 확인이다. 해당 도구의 PASS 자체가 실행 사실·소스 정확성·정책 권한·독립 감사를 증명하지는 않는다.

SSH 읽기 요청 하나의 파일 목록이2000자 제한을 넘어 `INVALID_ARGUMENT command maxLength 2000`으로 거부됐다. 파일 목록을24개 이하로 나눠 남은 정상 JSON만 읽었다. 실험을 재실행하지 않았다. manifest가 빈 파일로 기록한 stdout/stderr6개와 서버 ZIP 자체는 수신하지 않았다. 실험 판정과 모든 native tick은 수신 JSON에 있다. 동일 채널로 받은 manifest는 외부 host attestation이 아니며 upstream SSH 완전성은 독립적으로 보장되지 않는다. 다만 기대한 JSON 목록·개수·크기·해시는 모두 맞았다.

## 채택 범위와 다음 방향

현재의 authored 두 후보·완결 원천·정확한 hard 제약 문법에서는 full eligibility packet을 후속 query의 해집합 인터페이스로 채택할 근거가 생겼다. 운영 core 도입은 하지 않았다. 객체 수가 달라지거나 후보가 누락되는 경우, noisy constraint, 새 grammar, learned representation 및 재사용으로 실제 계산을 줄이는 효과는 검증하지 않았다.

다음 비중복 질문은 **후보 수와 제약 조합이 달라져도 같은 생성 규칙으로 만든 해집합 인터페이스가 의미와 보류를 보존하는가**다. case별 새 회로·정답 decoder를 추가하지 않고 가변 후보/누락 후보/새 제약 조합을 처리하는 계약부터 정해야 한다. exact와 같은 정보로 품질을 먼저 맞춘 뒤, 그래프 생성·원천·검증·저장까지 포함한 총비용을 비교한다. 이 단계가 실패하면 일반 추론 체계라는 주장은 보류한다. 기존 한정 문법의 반복이나 정보가 적은 delta군을 이겼다는 이유만으로 규모를 늘리지는 않는다.

## 근거 경로

- [동결 설계](DESIGN.ko.md), [입력·Program·kernel·상한](frozen_spec.json)
- [집계 및 비용](../../evidence/feasible-state-20261020-r34/analysis.json), [로컬 검산](../../evidence/feasible-state-20261020-r34/local-verification.json), [수신 검산](../../evidence/feasible-state-20261020-r34/receipt-verification.json)
- [원래 manifest](../../evidence/feasible-state-20261020-r34/raw/manifest.json), [물리 호출 ledger](../../evidence/feasible-state-20261020-r34/raw/work-ledger.json), [서버 단계 결과](../../evidence/feasible-state-20261020-r34/raw/result.json)
- [실험 구현](../../tools/r34_feasible_state/runtime.py), [손실 없는 기록과 실행](../../tools/r34_feasible_state/probe.py), [수식·의미 검사기](../../tools/r34_feasible_state/verify.py)
- [작성자 CS 검토](../../evidence/feasible-state-20261020-r34/cs/review.json), [bundle 검사](../../evidence/feasible-state-20261020-r34/cs/bundle-check.json)
