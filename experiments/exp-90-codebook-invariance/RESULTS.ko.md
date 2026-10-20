# R44 / EXP-90: 고정 행렬에서 의미 불변성 채택

R43 HIGH 방향 판정의 B에 따라 token→3bit 코드 배치만 바꿔 AI Research SSH에서 한 번 실행했다. **native1024조건·exact128조건과896개 nonidentity→identity 의미 대응을 검산했다. 전체 단계의 유한 의미 보존 판정은 True다.** 역할 단계는 가능한64숫자 입력쌍을 실제 실행한 결과에서 모든40320bijection의2580480tokenpair 대응을 saved lookup으로 확인했다. 전체 파이프라인40320실행이나 학습된 codebook·학습 효율의 증거는 아니다.

## 질문과 고정된 개입

[R43 방향 결정](../exp-89-exp-once/DELIBERATION.ko.md)의 B를 이어갔다. R35/R36의 namespace 변형은 실제 code 대응을 보존했다. 이번은 bit 위치·극성·일부 Hamming 거리가 달라지는8개 전역 bijection을 고정했다. 기존 encoder에 inverse vocabulary를 전달해 같은 의미/AST/Config/원천/순서/initial0.5와 원래 Program 생성기·guard·settle/controller/history/Cost를 유지했다. monkeypatch·core 수정·host 정답 보정은 없다. R43의 미세최적화나 R31의 learned macro 비용 대조를 반복하지 않는다.

R36 canonical Cmask8×Tmask8×ASTpair(4,5)/(5,4)=128base에8codebooks를 적용했다. native1024·의미가 같은 exact128이다. actual source leaf의8패턴은 C와T 양쪽에 존재한다. 새로운 독립 데이터셋·8개 독립 문제 가족·다른 이름/순서/initial/topology 일반화는 아니다. 계약과 입력은 [설계](DESIGN.ko.md), [동결 spec](frozen_spec.json)에 있다.

## 실제 coverage와 의미 결과

| 코드북 | strict | 역할 | AST 중간값 | 상위 tick | 실제 ordered code쌍 수 | Hamming별 실제 비교수 |
|---|---:|---:|---:|---:|---:|---|
| bit_reverse | 128/128 | 1536/1536 | 512/512 | 74,684 | 4 | {"0": 768, "1": 768} |
| cnot01 | 128/128 | 1536/1536 | 512/512 | 73,916 | 4 | {"0": 768, "2": 768} |
| cnot12 | 128/128 | 1536/1536 | 512/512 | 74,684 | 4 | {"0": 768, "1": 768} |
| cnot20 | 128/128 | 1536/1536 | 512/512 | 74,684 | 4 | {"0": 768, "1": 768} |
| cnot_chain | 128/128 | 1536/1536 | 512/512 | 72,380 | 4 | {"0": 768, "3": 768} |
| identity | 128/128 | 1536/1536 | 512/512 | 74,684 | 4 | {"0": 768, "1": 768} |
| swap01 | 128/128 | 1536/1536 | 512/512 | 74,684 | 4 | {"0": 768, "1": 768} |
| xor7 | 128/128 | 1536/1536 | 512/512 | 74,684 | 4 | {"0": 768, "1": 768} |

각 코드북은128조건에서1536개의 실제 역할 비교와512개의 AST 결과를 소비했다. 서로 다른8전역 bijection이라도 이 workload의 실제 등장 token에 제한하면 같은 인코딩일 수 있다. base별 서로 다른 **실제 token→code 제한 대응 수는 [6]**다. 이 중복을8개의 독립 표현 개입으로 세지 않는다. 표의 실제 ordered code쌍/Hamming 빈도는 전체 token공간과 구별한다. bit별 대응과 전역 Hamming 변화 수는 analysis.json에 보존했다.

전체896짝 중 896짝이 kind·선택 후보 identity·value·reason과 C/T역할·AST 의미를 보존했다. 이 중 실제 사용 token의 code가 그대로인 256짝과 실제 배치가 바뀐 640짝을 구별한다. 선택된 후보의 code정수·activation·ticks·state hash는 같을 필요가 없다. 같은None만으로 정답을 채택하지 않았고 다른 보류 사유도 구분했다. 모든 조건에는 독립 집합 oracle을 적용했다. 서로 다른 코드북의 trace bytes 동일을 요구하는 실험이 아니다.

역할64입력은 고정된16group equality Program/Config/initial0.5에 가능한 모든3bit ordered pair drive를 한 번씩 실제 계산했다. 정확 64/64,40320bijection 전이 중 잘못된 tokenpair 0개였다. encode_role의 index대응과 bijection의 equality 보존을 통해 같은 역할 함수의 이 유한 입력공간만 덮는다. 이후 AST·classifier·consumer의 수치 수렴까지40320maps에서 보장하는 증명이 아니며, 그 전체 단계는8maps에서만 실행했다. 준비 symbolic2580480검사와 실제 native64/그 결과 전이검사는 구별했다.

## 실행·검산·비용

서버 Linux/Python3.12.3, 준비·work·audit3단계 모두exit0, 전체 봉인 포함 54.296893초였다. 원천28+직접role64+상위18432=**18524회 actual settle**, 총 597,348tick이다. stage240초/total600초·worker1/retry0·학습/World.measure/localnative0을 지켰다. 동결 뒤 native 재실행·튜닝·조건 추가는0이다.

각 kernel의 full Program/Config/drives/initial/tick state/residual/stable_steps/convergence/readout/logical Cost를 재생하고 모든 physical reference를 합산했다. 원천28개 proof/source/revision/typedslot·packet-only Tconsumer 경계, 중간층과 실제 코드 drive, 원장·mapping/coverage 교란을 확인했다. scalar 최대오차 1.3877787807814457e-17 / tolerance1e-14였다. 의미 비교는 scalar 오차 허용으로 완화하지 않았다. 변조 18개를 거부했다. 로컬 검산과 CS 리뷰는 작성자의 saved-data 검산이며 독립 감사가 아니다.

첫 로컬 후처리는 전체 summary의 정확 일치를 요구해 `AssertionError: server vs local semantic/physical results`를 반환했다. 차이 필드를 기록해 확인한 결과 `max_scalar_error` 하나뿐이었다. 서버의 재생 오차는 0.0, 로컬은 1.3877787807814457e-17로 둘 다 실행 전에 동결한1e-14 이하다. 후처리에서 이 오차 통계량에만 기존 허용오차 검사를 적용하도록 고쳤고, 의미·물리 집계는 여전히 정확 일치를 요구했다. 원자료·동결 실행 코드·수용 임계값은 바꾸지 않았고 native 재실행도 하지 않았다. 실행환경 차이가 정확한 원인이라는 독립 검증까지 수행한 것은 아니다.

고유 trace360개는 kernel+Config의 전체 canonical bytes를 확인해 **저장만** 공유했다. 모든 추론 계산은 수행했다. cache128MiB/raw128MiB/AS각512MiB/건당128KiB/고유6000/LRU18은 운영 중단선이며 미래 완료·RSS 보장이 아니다.

모든phase CPU+parent봉인+launcher CPU 합계는 54.297965초다. 기록 core 34.868500초, 저장 11.361668초와 그 밖 준비·source·role·audit·봉인 비용을 분석에 구별했다. source/role/기록 시간은 전체 process 비용의 부분집합이며 다시 더하지 않는다. bootstrap wall은 전체에 포함돼 중복 가산하지 않는다. 속도 비교·통계적 우위·학습 포함 효율 채택선은 없다. 로컬 개발·패키징·MCP 전송/수신·인력 비용도 위 서버 실행비용에 포함하지 않는다.

## 근거와 한계

[분석](../../evidence/codebook-invariance-20261020-r44/analysis.json), [로컬 검산](../../evidence/codebook-invariance-20261020-r44/local-verification.json), [수신 검산](../../evidence/codebook-invariance-20261020-r44/receipt-verification.json), [서버 manifest](../../evidence/codebook-invariance-20261020-r44/raw/manifest.json), [서버 완료](../../evidence/codebook-invariance-20261020-r44/server-completion.json), [CS 검토](../../evidence/codebook-invariance-20261020-r44/cs/review.json)에 연결한다. manifest 대상 JSON406개와 manifest 자체를 받았고 원본 크기·SHA를 직접 대조했다. source125파일·input94핀은 변하지 않았다. 빈stdout/stderr6개와 evidence ZIP자체는 받지 않았다. manifest는 자기 해시 밖에 있고 same-channel hash는 host attestation이 아니다. upstream SSH completeness는unknown이다.

초기 자동 승인 검토가 비공개 sourceZIP 전송의 구체적 승인을 요구해 업로드를 거절했다. 사용자의 해당ZIP·지정server·600초1회실험 승인을 받은 뒤 같은 동결ZIP을 전송·실행했다. 우회 전송이나 그 사이 원격 native 실행은 없었다. 원자료읽기2개를겹쳐보낸시점에한요청이INVALID_ARGUMENT/Request refused or failed를반환해출력참조를받지못했다. 먼저받은출력을보존했고해당읽기를순차처리했을때성공했다. 근본원인을독립확정한것은아니며수신검증에관측과복구를기록했다. 추론은재실행하지않았다. 준비 중 CS CLI에중복 --rule플래그를준명령이INVALID_INPUT을반환했고쉼표목록으로정정해카드를읽었다. baseline/contract/CS조건·준비검사는통과한후동결했다.

## 판정과 다음 방향

**고정 행렬에서 의미 불변성 채택.** 이 결과는 기존 공통 kernel의 고정 equality·두 AST 조합·typed 후보/소비 계약에서의 표현 불변성이다. authored codebook을 학습된 표현·H03 구조 재사용·원계산 대체·효율 증거로 합산하지 않는다. 실제 token 제한 대응 중복과2ASTpair 범위를 그대로 남긴다. core에 자동 반영하지 않는다.

다음 과제는 같은 maps/AST 행렬을 늘려 성공률을 높이는 반복보다, 실제 사용 token이 전체코드공간을덮는지와 역할결과의유한전이가후속계산까지성립하는조건을먼저분리해야한다. 학습 구조로돌아갈경우 R31의음성대조를보존하고 learner산출물과실제원계산대체를연결하는별도계약이필요하다. 이번요청에서추가R45실험은자동시작하지않는다.
