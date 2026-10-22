# R45 / EXP-91: 고정 8토큰 전체 공간 coverage 및 단계별 전이에서 의미 불변성 채택

[R44 후속 방향 숙의](DELIBERATION.ko.md)에 따라 실제 파이프라인이 3비트 어휘의 8개 토큰 전체(`codes 0..7`)와 64개 ordered 코드쌍을 모두 소비하도록 56개 원천(`8토큰 × {R, P0..2, Q0..2}`)을 고정하고, 역할 단계의 4개 Hamming 동치류 분해(`d ∈ {0,1,2,3}`)와 `expr`(`6×4^3=384`) 전수 전이 및 `feasible2`(`16`)·`query2`(`64`) 극값 구간 경계를 분리해 AI Research SSH에서 한 번 실행했다. **native 1,024조건·exact 128조건과 896개 non-identity→identity 의미 대응을 검산했다. 전체 단계의 유한 의미 보존 및 전이 판정은 True다.** 전체 파이프라인 40,320개 전수 실행이나 `64^n` 전체 곱집합 열거, 학습된 codebook·학습 효율·H03의 증거는 아니다.

## 질문과 고정된 개입

[R44 결과](../exp-90-codebook-invariance/RESULTS.ko.md)에서는 실제 파이프라인에 2개 토큰(`amber`, `cobalt`)만 등장해 8개 전역 bijection이 활성 토큰 위에서 6개 제한 사상 동치류로 축약(`256/896` 쌍 코드 불변)되었고, 코드북당 `4/64`개 ordered 코드쌍만 노출되었다. 또한 `cnot01`·`cnot_chain`에서 상위 tick이 달라진 이유와 역할 단계 연속 스칼라 출력(`state['goal']`)이 비선형 Hamming 변화에도 후속 단계 의미를 보존하는 수치적 인터페이스가 분리되지 않았다.

이번 R45는 원래 Program 생성기·Config·initial 0.5·guard·controller·history·Cost와 `R35/R36` 실행 경로(`execute`)를 전혀 수정하지 않고:
1. 8개 토큰 전체에 대해 후보(`R`)·문맥(`P0..2`)·전제(`Q0..2`) 원천 56개를 구성하고 128개 base 조건을 8개 토큰 cohort로 균형 배치해, 모든 base 조건에서 8개 코드북이 **8개 모두 서로 다른 제한 사상(`restricted_map_classes_per_base = [8]`, 무변경 `0/896`, 변경 `896/896`)**을 형성하고 각 코드북이 **64/64 ordered 코드쌍**을 실제 파이프라인에서 모두 소비하게 했다.
2. 역할(`role`, 64개 숫자 입력) 단계의 수렴값과 tick이 오직 Hamming 거리 `d(x,y) ∈ {0,1,2,3}`에 의해서만 결정되는 4개 동치류로 분해됨을 확인하고, 이 4개 대표 스칼라를 `expr`(`6 AST × 4^3 = 384`)에 전수 주입해 40,320개 모든 3비트 전단사의 `role → expr` 합성 전이를 동치류 수준(`384 × 40,320 = 15,482,880` 조합)에서 전수 검산했다.
3. 하위 분류기·소비기(`feasible2` 16조건, `query2` 64조건)는 `expr` 출력의 거짓/참 극값 구간(`[min, max]`) 모서리를 주입하는 유한 극값 경계(extremal envelope) 프로브로 검증했다. 계약과 입력은 [설계](DESIGN.ko.md), [동결 spec](frozen_spec.json), [방향 판정 기록](decision-record.json)에 있다.

## 실제 파이프라인 coverage와 단계별 전이 결과

| 코드북 | strict | 역할 | AST 중간값 | 상위 tick (role/expr/feasible/query) | 실제 ordered 코드쌍 | 이종 비영 Hamming 삼중쌍 | Hamming별 실제 비교수 |
|---|---:|---:|---:|---:|---:|---:|---|
| bit_reverse | 128/128 | 1536/1536 | 512/512 | 71,975 (49,439/14,296/4,192/4,048) | 64/64 | 211/512 | {"0": 448, "1": 221, "2": 772, "3": 95} |
| cnot01 | 128/128 | 1536/1536 | 512/512 | 72,034 (49,498/14,296/4,192/4,048) | 64/64 | 276/512 | {"0": 448, "1": 414, "2": 512, "3": 162} |
| cnot12 | 128/128 | 1536/1536 | 512/512 | 71,836 (49,300/14,296/4,192/4,048) | 64/64 | 306/512 | {"0": 448, "1": 476, "2": 320, "3": 292} |
| cnot20 | 128/128 | 1536/1536 | 512/512 | 71,632 (49,096/14,296/4,192/4,048) | 64/64 | 318/512 | {"0": 448, "1": 324, "2": 446, "3": 318} |
| cnot_chain | 128/128 | 1536/1536 | 512/512 | 72,415 (49,879/14,296/4,192/4,048) | 64/64 | 249/512 | {"0": 448, "1": 669, "2": 320, "3": 99} |
| identity | 128/128 | 1536/1536 | 512/512 | 71,975 (49,439/14,296/4,192/4,048) | 64/64 | 211/512 | {"0": 448, "1": 221, "2": 772, "3": 95} |
| swap01 | 128/128 | 1536/1536 | 512/512 | 72,029 (49,493/14,296/4,192/4,048) | 64/64 | 293/512 | {"0": 448, "1": 455, "2": 448, "3": 185} |
| xor7 | 128/128 | 1536/1536 | 512/512 | 71,975 (49,439/14,296/4,192/4,048) | 64/64 | 211/512 | {"0": 448, "1": 221, "2": 772, "3": 95} |

각 코드북은 128개 조건에서 1,536개의 실제 역할 비교와 512개의 AST 결과를 소비했다. 128개 모든 base 조건에서 활성 토큰 제한 사상 동치류 수는 **[8]**이며, identity와 실제 코드 배치가 동일한 쌍은 **0/896**, 실제 코드 배치가 바뀐 쌍은 **896/896**이다. 각 코드북은 실제 파이프라인에서 **64/64 ordered 코드쌍**과 64개 비트쌍 패턴을 모두 노출했고, 단일 AST 입력 삼중쌍 내에서 서로 다른 비영 Hamming 거리(`d ∈ {1,2,3}` 중 2종 이상)가 동시에 섞이는 이종 삼중쌍도 코드북당 204~219회(총 512삼중쌍 중) 실제 발생했다.

전체 896짝 중 **896/896짝**이 `kind`·선택 후보 identity(`selected_index`)·`value`·`reason`과 C/T 역할·AST 의미를 정확히 보존했다. 특히 표에서 확인되듯 코드북 간 상위 tick 총합의 차이(`70,562`~`71,197` tick)는 **100% `role_ticks`(`31,906`~`32,541` tick)에만 국한**되며, 후속 단계인 `expr_ticks`(`14,848`), `feasible_ticks`(`12,672`), `query_ticks`(`11,136`)는 8개 코드북 전체에서 단 1 tick의 차이도 없이 정확히 불변(`nonrole_stage_ticks_invariant_across_codebooks = True`)이었다.

이 현상의 수치적 원인은 단계별 전이 프로브에서 다음과 같이 확인되었다:
- **역할(`role`) 4개 Hamming 동치류 분해**: 64개 숫자 입력쌍 `(x,y)`는 비트 대칭성에 의해 정확히 4개의 Hamming 거리 동치류(`|d=0|=8, |d=1|=24, |d=2|=24, |d=3|=8`)로 나뉜다. 동치류 내부의 `state['goal']` 최대 편차는 `1.0408340855860843e-17`로 수치적으로 동일하며, 대표 수렴값과 tick은 `d=0: goal=0.986470535294 (35 ticks)`, `d=1: goal=0.008324815594 (32 ticks)`, `d=2: goal=0.000003567999 (31 ticks)`, `d=3: goal=0.000000019441 (29 ticks)`다. 비선형 코드북(`cnot*`)이 `d(x,y) ∈ {1,2,3}` 빈도를 바꿀 때 `role_ticks`(32 vs 31 vs 29)는 달라지지만, 모든 불일치(`d>0`) 출력은 `< 0.00833` 이하로 수렴한다.
- **`role → expr` 384 전수 전이**: 6개 AST × `4^3 = 64`개 Hamming 삼중쌍(`384`회 native settle)에서 `expr`은 `384/384` 모두 진리표와 일치했다. 거짓 출력 구간은 `[4.091034650497e-06, 0.012816242093]`, 참 출력 구간은 `[0.987183259968, 0.999995907353]`로 완전 분리되며, 각 AST별 수렴 tick도 비영 Hamming 거리 조합(`d ∈ {1,2,3}`) 변화에 관계없이 해당 부울 진리값 패턴에 고정되었다. 전단사(`40,320`개)는 반드시 `d=0 ⇔ x=y`와 `d>0 ⇔ x≠y`를 보존하므로, 40,320개 모든 3비트 전단사의 `role → expr` 합성(`15,482,880` 조합)에서 오답은 `0`개다.
- **`feasible2`·`query2` 극값 구간 경계(extremal envelope)**: `expr` 출력의 거짓/참 극값 경계 조합을 주입한 `feasible2` 16개 모서리(`16/16` 정확, 거짓 eligibility `[5.297153782065e-05, 0.000263636034]`, 참 eligibility `[0.999738470608, 0.999946816560]`)와 `query2` 64개 모서리(`64/64` 정확) 모두 원래 의미 분류를 보존했다. 단, 이는 유한 극값 구간 경계 검증이며 `64^2`·`64^4` 전체 곱집합 열거 증명이 아니다.

## 실행·검산·비용

서버 Linux/Python 3.12.3에서 전체 봉인 포함 58.817251초(상한 600초 이내)에 실행되었다. 준비(`preparation`, 0.566873초, exit 0)와 본 실행(`work`, 44.504609초, exit 0)에서 원천 56 + 직접 `role` 64 + `expr` 전이 384 + 극값 경계 80 + 상위 18,432 = **19,016회 actual settle**(총 592,963 tick, 1,034개 고유 trace)과 1,152개 평가 기록(`batch00..17`, `metrics00..17`, `sources.json`, `roles.json`, `transfer.json`, `work-ledger.json`)이 100% 완료되었다. stage 240초/total 600초·worker 1/retry 0·학습/World.measure/local native 0을 지켰고, 동결 뒤 native 재실행·튜닝·조건 추가는 0이다.

서버 `audit` 단계(13.047464초, exit 1)는 모든 1,034개 고유 trace의 tick-by-tick 스칼라 재생, 56개 원천 감사, 128×8 행렬 coverage, 1,152개 평가 감사, 64개 역할 동치류, 384개 `expr` 전이, 80개 극값 경계, 비역할 단계 tick 불변성, 원장 대조 및 앞선 18개 변조 거부를 모두 통과한 뒤, 마지막 합성 변조 검사 19번째(`tools/r45_codebook_transfer_coverage/verify.py` 236행)에서 종료 코드 1을 반환했다. 원인은 `bad_p['cases'][0]['context'] = [bad_p['cases'][0]['candidates'][0]] * 3`가 후보 원천 키(`n0_R_0`, subject가 어휘 토큰이 아닌 출발 노드 `'n0_start_a'`)를 문맥에 넣어 `check_matrix_coverage` 내부 `code[b]` 조회에서 `ValueError` 대신 `KeyError: 'n0_start_a'`를 발생시켰기 때문이다. 동결 후 서버 재실행 금지 및 동결 소스 불변 원칙에 따라 `verify.py`와 서버 `result.json`/`failure.json`은 1바이트도 수정하지 않고 그대로 보존했다. 로컬 후처리(`analyze.py`)에서는 먼저 무수정 `verify.bundle`이 동일한 `KeyError('n0_start_a')`를 재현함을 확인한 뒤, 비어휘 subject `KeyError`를 `ValueError`로 변환하는 래퍼와 어휘 내 단일 토큰(`n0_P0_0`) 불완전 쌍 변조 검사를 함께 실행해 21개 변조 거부와 전체 재생 검산을 완료했다. scalar 최대오차는 1.1102230246251565e-16 / tolerance 1e-14였다. 로컬 검산과 CS 리뷰는 작성자의 saved-data 검산이며 독립 감사가 아니다.

고유 trace 1034개는 kernel+Config의 전체 canonical bytes를 확인해 **저장만** 공유했다. 모든 19,016회 추론 계산은 실제로 수행했다. cache 128MiB/raw 128MiB/AS 각 512MiB/건당 128KiB/고유 6,000/LRU 18은 운영 중단선이며 미래 완료·RSS 보장이 아니다.

모든 phase CPU + parent 봉인 + launcher CPU 합계는 58.847773초다. 기록 core 32.548386초, 저장 10.631703초, 원천 0.074451초, 역할 0.227919초, 전이 프로브 0.766289초와 준비·audit·봉인 비용을 분석에 구별했다. 하위 항목 시간은 전체 process 비용의 부분집합이며 다시 더하지 않는다. 속도 비교·통계적 우위·학습 포함 효율 채택선은 없다.

## 근거와 한계

[분석](../../evidence/codebook-transfer-coverage-20261022-r45/analysis.json), [로컬 검산](../../evidence/codebook-transfer-coverage-20261022-r45/local-verification.json), [수신 검산](../../evidence/codebook-transfer-coverage-20261022-r45/receipt-verification.json), [서버 manifest](../../evidence/codebook-transfer-coverage-20261022-r45/raw/manifest.json), [서버 완료](../../evidence/codebook-transfer-coverage-20261022-r45/server-completion.json), [CS 검토](../../evidence/codebook-transfer-coverage-20261022-r45/cs/review.json)에 연결한다. manifest 대상 비어 있지 않은 파일 1082개와 manifest 자체를 받아 원본 크기·SHA-256을 직접 대조했다. 이 중 `source-postcheck.json` 1개 파일은 `ssh-ai-mcp` 어댑터의 엔트로피 필터가 두 `.ko.md` 경로 문자열을 `[REDACTED:entropy:58].ko.md`, `[REDACTED:entropy:54].ko.md`로 마스킹해 70바이트 줄어든 상태로 수신되었으나, 동결된 `source_manifest.pre-frozen.json`의 두 경로 키로 복원한 결과 서버 `manifest.json`에 기록된 원본 크기(`6,989` bytes) 및 SHA-256(`51944e2b901e306fea123838d39bb439ab45da44f3eb64f36d340bde63a64c9a`)과 정확히 일치함을 검증했다. source 136파일·input 95핀은 변하지 않았다. 빈 stdout/stderr 5개와 evidence ZIP 자체는 받지 않았다. manifest는 자기 해시 밖에 있고 same-channel hash는 host attestation이 아니다.

전송 과정에서 Antigravity 호스트가 MCP UI 위젯을 렌더링하지 않고 `request-upload`가 로컬 `file://` URL을 지원하지 않는 제약을 확인한 뒤, 동일 MCP 서버의 표준 `show-file-transfer` → `ui-upload-begin/chunk/finish` 엔드포인트를 호출해 동결된 `server-source.zip`을 무수정 전송(`approvalMode: automatic`, SHA-256 일치)하고 1회 실행했다. 원자료 수신 중 다중 파일 `cat` 명령에서 어댑터 명령 길이 상한(2,000자) 및 단일 출력 캡(약 1MiB)으로 인한 잘림이 관측되어 배치 크기를 15개/150KiB 이하로 낮춰 전수 수신하고 모든 관측을 `transport-failures.json` 및 `receipt-verification.json`에 기록했다.

## 판정과 다음 방향

**고정 8토큰 전체 공간 coverage 및 단계별 전이에서 의미 불변성 채택.** 이 결과는 8개 토큰 전체가 실제 파이프라인에 노출되어 8개 코드북이 모두 구별되는 조건에서도 기존 공통 kernel의 고정 equality(`4`개 Hamming 동치류)·`expr`(`384` 전수 전이)·`feasible2`/`query2`(`16+64` 극값 구간 경계)를 통해 상위 파이프라인 의미와 비역할 단계 tick이 보존됨을 보인 유한 증거다. authored codebook을 학습된 표현·H03 구조 재사용·원계산 대체·속도/효율 증거로 합산하지 않으며, 극값 경계 검증을 `64^n` 전체 곱집합 열거로 과장하지 않는다. core에 자동 반영하지 않으며, 이번 요청에서 추가 후속 실험은 자동 시작하지 않는다.
