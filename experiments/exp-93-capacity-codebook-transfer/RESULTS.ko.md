# R47 / EXP-93: 고정 8토큰 가변 후보 용량(n=1..4) 중첩-AST 구성 및 다중해·보류 보편 질의 코드북 전이에서 의미 불변성 채택

[R46 후속 방향 숙의](DELIBERATION.ko.md)에 따라 가변 후보 용량(`n ∈ {1, 2, 3, 4}`) 단항 구성 파이프라인(`R35`: `role -> expr0..5 -> feasible1..4 -> query1..4`)에서 중첩 leaf(`6/6` 서로 다른 AST 부울 함수), 다중 적격 후보(`|F| ∈ {0, 1, 2, 3, 4}`)의 쌍별 상호 억제(`pair0_1..pair2_3 -> at_least_two`), 다중해 만장일치(`qtrue`/`qfalse`) 대 분할(`mixed`) 및 미완결 후보(`complete=False -> incomplete`) 보류 경계, 그리고 8개 3비트 코드북·4용량 단계별 전이 프로브(`1,188`회 settle)를 고정해 AI Research SSH에서 1회 실행했다. **native 1,280조건(용량당 320조건)·exact 160조건(용량당 40조건)과 1,120개 non-identity→identity 의미 대응을 검산했다. 전체 단계의 유한 의미 보존 및 용량별 전이 판정은 `True`다.** 전체 파이프라인 40,320개 전수 실행이나 `64^n` 전체 곱집합 열거, 학습된 코드북·학습 효율·H03 구조 재사용의 증거는 아니다.

## 질문과 고정된 개입

[R35](../exp-81-compositional-slot/RESULTS.ko.md), [R36](../exp-82-overlap-composition/RESULTS.ko.md), [R45](../exp-91-codebook-transfer-coverage/RESULTS.ko.md), [R46](../exp-92-relational-codebook-transfer/RESULTS.ko.md)을 거치며 다음 세 가지 구조적 공백이 남아 있었다:
1. [R35](../exp-81-compositional-slot/RESULTS.ko.md)는 `feasible1..4`(9, 11, 14, 18 그룹)와 `query1..4`(13, 17, 21, 25 그룹)를 정의했으나 3개 leaf를 상호배타적으로 두어 8개 leaf 패턴 중 `2/8~4/8`만 나타났고, 그 결과 6개 AST(`0..5`)가 `3/6~5/6`개 함수로 축약되었으며 `AST 2`(`and(0,1)`)는 적격 해집합을 단 1건도 만들지 못했다. 또한 `n=1, complete=True`와 `n=4, complete=False` 조합은 실행되지 않았다.
2. [R36](../exp-82-overlap-composition/RESULTS.ko.md), [R44](../exp-90-codebook-invariance/RESULTS.ko.md), [R45](../exp-91-codebook-transfer-coverage/RESULTS.ko.md)는 중첩 leaf와 8토큰 코드북 전이를 오직 **`n=2, complete=True`(`feasible2`, `query2`)로만 제한**했고, [R46](../exp-92-relational-codebook-transfer/RESULTS.ko.md)의 관계형 소비기도 `feasible2`(`Z` 후보 2개)만 사용했다.
3. 따라서 `n ∈ {3, 4}`에서 다중 적격 후보(`|F| ∈ {2, 3, 4}`)가 동시에 경쟁할 때 비등거리 코드북의 Hamming 거리 섭동(`d ∈ {1, 2, 3}`)이 `feasible3`(쌍별 억제 3개)·`feasible4`(쌍별 억제 6개 `pair0_1..pair2_3 -> at_least_two`)와 `query3`·`query4`(만장일치 `qtrue`/`qfalse` 대 분할 `mixed` 대 미완결 `incomplete`)의 수렴 판정 및 수렴 tick을 흔드는지 한 번도 검증되지 않았다.

이번 R47은 원래 `R35` Program 생성기·Config·initial 0.5·guard·controller·history·Cost와 `execute` 경로를 전혀 수정하지 않고:
1. 56개 원천(`8 토큰 × {R, P0..2, Q0..2}`) 위에서 용량 `n ∈ {1, 2, 3, 4}`별로 각 **40개 base 조건**(Part I 24개: `6 AST × 4 상보 마스크`, `complete=True` + Part II 8개: `|F| ∈ {0..n}` 카디널리티 및 만장일치/분할 질의, `complete=True` + Part III 8개: `complete=False` 미완결 보류 대조) = **총 160개 base 조건(`1,280` native + `160` exact = `1,440` 평가, `28,160`회 상위 settle)**을 구성했다. 160개 모든 base 조건이 8개 코드북에서 **8/8 서로 다른 제한 사상(`restricted_map_classes_per_base = [8]`, 무변경 `0/1,120`, 변경 `1,120/1,120`)**을 유도하고, 각 코드북이 **64/64 ordered 코드쌍** 전체를 실제 파이프라인에서 소비하며, 모든 용량 `n ∈ {1, 2, 3, 4}`에서 **6/6 서로 다른 AST 부울 함수**를 실현하게 했다.
2. 직접 `role`(64회)과 전수 `expr0..5`(384회) 전이 위에서 4개 용량 전체의 `feasible1..4`(`4 + 8 + 16 + 32 = 60`회)와 `query1..4`(`8 + 32 + 128 + 512 = 680`회) 최악 내부 마진(`[false_max, true_min]`) 극값 모서리 전이(`1,188`회 settle)를 분리해 측정했다. 계약과 입력은 [설계](DESIGN.ko.md), [동결 spec](frozen_spec.json), [방향 판정 기록](decision-record.json)에 있다.

## 용량별(`n=1..4`) 및 코드북별 실제 파이프라인 결과

| 용량(`n`) | Base 수 (`complete=T/F`) | 평가 수 (`native/exact`) | AST 구별 (`C/T`) | `feasible_n` 극값 모서리 | `query_n` 극값 모서리 | `feasible_n` 거짓/참 eligibility 구간 | 비등거리 최대 상태 편차 | 실현 의미 구간 수 |
|---|---:|---:|---:|---:|---:|---|---:|---:|
| `n=1` | 40 (32 / 8) | 320 / 40 | 6/6 | 4/4 | 8/8 | `[1.309421e-04, 0.000133]` / `[0.999869, 0.999869]` | 1.153241e-08 | 6개 구간 |
| `n=2` | 40 (32 / 8) | 320 / 40 | 6/6 | 8/8 | 32/32 | `[6.502294e-05, 0.000264]` / `[0.999738, 0.999935]` | 1.190027e-08 | 11개 구간 |
| `n=3` | 40 (32 / 8) | 320 / 40 | 6/6 | 16/16 | 128/128 | `[3.229085e-05, 0.000139]` / `[0.999478, 0.999967]` | 1.121053e-08 | 18개 구간 |
| `n=4` | 40 (32 / 8) | 320 / 40 | 6/6 | 32/32 | 512/512 | `[1.603473e-05, 0.000071]` / `[0.998956, 0.999984]` | 9.196364e-08 | 18개 구간 |

| 코드북 | 상위 strict | 역할(`role`) | AST(`C+T`) | 상위 tick (`role/expr/feasible/query`) | 실제 코드쌍 | 비트쌍 패턴 | 이종 비영 Hamming 삼중항 | 실제 파이프라인 Hamming 거리 분포 |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| `bit_reverse` | 160/160 | 2400/2400 | 800/800 | 109,626 (77,304/22,101/5,140/5,081) | 64/64 | 64/64 | 256/800 | `{"0": 739, "1": 496, "2": 891, "3": 274}` |
| `cnot01` | 160/160 | 2400/2400 | 800/800 | 109,703 (77,381/22,101/5,140/5,081) | 64/64 | 64/64 | 269/800 | `{"0": 739, "1": 589, "2": 790, "3": 282}` |
| `cnot12` | 160/160 | 2400/2400 | 800/800 | 109,870 (77,548/22,101/5,140/5,081) | 64/64 | 64/64 | 263/800 | `{"0": 739, "1": 658, "2": 770, "3": 233}` |
| `cnot20` | 160/160 | 2400/2400 | 800/800 | 109,562 (77,240/22,101/5,140/5,081) | 64/64 | 64/64 | 336/800 | `{"0": 739, "1": 636, "2": 649, "3": 376}` |
| `cnot_chain` | 160/160 | 2400/2400 | 800/800 | 110,187 (77,865/22,101/5,140/5,081) | 64/64 | 64/64 | 262/800 | `{"0": 739, "1": 789, "2": 732, "3": 140}` |
| `identity` | 160/160 | 2400/2400 | 800/800 | 109,626 (77,304/22,101/5,140/5,081) | 64/64 | 64/64 | 256/800 | `{"0": 739, "1": 496, "2": 891, "3": 274}` |
| `swap01` | 160/160 | 2400/2400 | 800/800 | 109,604 (77,282/22,101/5,140/5,081) | 64/64 | 64/64 | 295/800 | `{"0": 739, "1": 568, "2": 772, "3": 321}` |
| `xor7` | 160/160 | 2400/2400 | 800/800 | 109,626 (77,304/22,101/5,140/5,081) | 64/64 | 64/64 | 256/800 | `{"0": 739, "1": 496, "2": 891, "3": 274}` |

1. **전 용량(`n=1..4`)·전 코드북(`8종`) 완전 정확 및 1,120짝 의미 불변**: 8개 코드북 전체에서 용량 `n=1..4`에 걸친 160개 base 조건(`320`개 역할 비교 × 2단계 = 코드북당 `960`회 역할 비교, `320`회 AST 평가)이 **160/160(총 1,280/1,280, exact 160/160)** 모두 `oracle` 정답과 일치했다. 160개 base × 7개 비항등 코드북 = **1,120개 대응 조건** 전체에서 비항등 코드북은 `identity` 기준선과 `kind`(`none`/`unique`/`many`/`incomplete`), `tag`(`qtrue`/`qfalse`/`mixed`/`empty`/`incomplete`), `selected_code`, `value`, `reason`을 **1,120/1,120(100%)** 그대로 보존했다.
2. **다중해(`|F| ∈ {2, 3, 4}`) 만장일치 대 분할 및 `complete=False` 보류 경계의 보존**:
   - `n=3`에서 `|F|=3` 3원 적격 해집합의 만장일치 참(`3:0 -> many:qtrue`), 만장일치 거짓(`0:3 -> many:qfalse`), 분할(`2:1`, `1:2 -> many:mixed`)과 `|F|=2`(`2:0 -> many:qtrue`, `0:2 -> many:qfalse`), `|F|=1`(`unique`), `|F|=0`(`none:empty`) 및 `complete=False`(`incomplete:abstain_incomplete`)의 18개 세부 의미 구간이 8개 코드북 모두에서 100% 보존되었다.
   - `n=4`에서 6개 쌍별 억제 노드(`pair0_1..pair2_3`)가 모두 동시에 활성화되는 `|F|=4` 4원 적격 해집합의 만장일치 참(`4:0 -> many:qtrue`), 만장일치 거짓(`0:4 -> many:qfalse`), 3종 분할(`3:1`, `2:2`, `1:3 -> many:mixed`)과 `|F|=3`(`3:0`, `0:3`, `1:2`), `|F|=2`(`2:0`, `0:2`, `1:1`), `|F|=1`, `|F|=0`, `complete=False`의 18개 세부 의미 구간이 8개 코드북 모두에서 100% 보존되었다.
3. **등거리 대 비등거리 연속 상태(`state_sha256`) 변동의 정량 분리 및 비역할 단계 tick 불변성**:
   - 등거리 코드북(`bit_reverse`, `xor7`, 320쌍)에서는 `feasible_n` 연속 상태 최대 절대 차이가 `0.000e+00`였고 **320/320쌍(`320/320`)** 모두가 `state_sha256`까지 동일했다.
   - 비등거리 코드북(`cnot01`, `cnot12`, `cnot20`, `cnot_chain`, `swap01`, 800쌍)에서는 Hamming 거리 재배치로 인해 **`648/800`쌍**에서 `state_sha256`이 실제로 변했고 연속 eligibility/coverage 스칼라가 최대 `9.196364e-08` 변했으나, 최종 의미 판정은 단 1건도 바뀌지 않았다.
   - 코드북 간 총 상위 tick 차이(`109,562`~`110,187` tick)는 **100% `role_ticks`(`77,240`~`77,865` tick)에만 국한**되었으며, `expr_ticks`(`22,101`), `feasible_ticks`(`5,140`), `query_ticks`(`5,081`)는 4개 용량과 8개 코드북 전체에서 단 1 tick의 차이도 없이 정확히 불변(`nonrole_stage_ticks_invariant_across_codebooks = True`)이었다.

## 4-용량 단계별 전이 프로브(1,188회 settle) 분석

- **1단계 `role`(64회 settle) → 2단계 `expr0..5`(384회 전수 settle)**: 64개 숫자 역할 입력은 4개 Hamming 동치류(`d=0: 0.986470535294`, `d=1: 0.008324815594`, `d=2: 0.000003567999`, `d=3: 0.000000019441`, 동치류 내부 최대 편차 `1.041e-17`)로 분해된다. 6개 AST × `4^3 = 64`개 Hamming 삼중항 = **384회 전수 settle**에서 `384/384` 모두 정확했고(거짓 구간 `[4.091034650497e-06, 0.012816242093]`, 참 구간 `[0.987183259968, 0.999995907353]`), 40,320개 모든 3비트 전단사에 대한 `role -> expr` 동치류 합성 검사(`15,482,880`건)에서 오답은 `0`건이었다.
- **3단계 `feasible1..4`(`4 + 8 + 16 + 32 = 60`회 최악 내부 마진 극값 settle)**: `expr` 단계의 최악 내부 마진 경계(`expr_false_max = 0.012816242093`, `expr_true_min = 0.987183259968`)를 4개 용량 `n ∈ {1, 2, 3, 4}`의 모든 `2^{n+1}` 부울 모서리에 주입한 60회 settle에서 `60/60` 모두 `none`/`unique`/`many`/`incomplete` 판정을 정확히 복원했다.
- **4단계 `query1..4`(`8 + 32 + 128 + 512 = 680`회 용량별 최악 내부 마진 극값 settle)**: 각 용량 `n`의 `feasible_n`에서 관측된 최악 내부 마진 eligibility 경계(`[false_max, true_min]`) 및 `complete` 경계를 `query1..4`의 모든 `2^{2n+1}` 부울 모서리에 주입한 680회 settle에서 `680/680` 모두 `qtrue`/`qfalse`/`empty`/`mixed`/`incomplete` 판정을 정확히 복원했다. 이는 최악 내부 마진 모서리 검증이며 `64^n` 전체 곱집합 열거 증명이 아니다.

## 실행·검산·비용

서버 Linux/Python 3.12.3에서 준비(`preparation`, 2.621260초, exit 0)와 본 실행(`work`, 70.415005초, exit 0)이 완료되어 원천 56 + 4용량 단계별 전이 프로브 1,188(직접 `role` 64 포함) + 상위 파이프라인 28,160 = **29,404회 actual settle**(총 915,408 tick, 2360개 고유 trace)과 1,440개 평가 기록(`batch00..17`, `metrics00..17`, `sources.json`, `roles.json`, `transfer.json`, `work-ledger.json`, `n000..n2359`)이 100% 생성되었다. 저장 감사(`audit`, 5.893281초, exit 1) 단계에서는 모든 trace·drive·contract·scalar 검사를 통과한 뒤 `tools/r35_compositional_slot/verify.py` 53행 반환 딕셔너리의 `c['base_n']` 메타데이터 키 참조(`R47` `frozen_spec.json`은 `capacity`로 기록)로 인해 `KeyError('base_n')`이 발생했고, 전체 봉인 포함 **80.516029초**(상한 600초 이내)에 종료되었다. stage 240초/total 600초·worker 1/retry 0·학습/World.measure/local native 0을 지켰고, 동결 뒤 코드 수정·native 재실행·튜닝·조건 추가는 0(`native_rerun = False`)이다.

로컬 saved-data 재생 검산(`analyze.py`)에서 먼저 무수정 `verify.bundle`의 `KeyError('base_n')`을 그대로 재현한 뒤, `r35_audit` 반환용 메타데이터(`base_n=capacity, namespace=0`)만 주입해 전체 1,440개 평가·1,188개 단계 전이·2,360개 고유 trace와 25개 합성 변조 거부(`25/25`: `revision`, `origin`, `eligibility`, `coverage`, `selected`, `C_message`, `T_hash`, `value`, `network_ref`, `alternative_role`, `leaf_contract`, `C_predicate`, `C_target`, `T_predicate`, `T_target`, `candidate_subject`, `nonbijective_map`, `inverse_vocab_mismatch`, `capacity_mismatch`, `incomplete_policy_bypass`, `numeric_role_coverage`, `incomplete_tokenpair_coverage`, `collapsed_restricted_codebook`, `expr_transfer_table_tamper`, `capacity_envelope_tamper`)가 100% 통과함을 확인했다. scalar 최대오차는 로컬 `1.1102230246251565e-16` / tolerance `1e-9`였다. 로컬 검산과 CS 리뷰는 작성자의 saved-data 검산이며 독립 감사가 아니다.

고유 trace 2360개는 kernel+Config의 전체 canonical bytes를 확인해 **저장만** 공유했다. 모든 29,404회 추론 계산은 실제로 수행했다. 모든 phase CPU + parent 봉인 + launcher CPU 합계는 80.619945초이며, 기록 core 48.338408초, 저장 17.215742초, 원천 0.075050초, 4용량 전이 프로브(역할 포함) 4.508802초와 준비·audit·봉인 비용을 분석에 분리해 기록했다. 하위 항목 시간은 전체 process 비용의 부분집합이며 다시 더하지 않는다. 속도 비교·통계적 우위·학습 포함 효율 채택선은 없다.

## 근거와 한계

[분석](../../evidence/capacity-codebook-transfer-20261023-r47/analysis.json), [로컬 검산](../../evidence/capacity-codebook-transfer-20261023-r47/local-verification.json), [수신 검산](../../evidence/capacity-codebook-transfer-20261023-r47/receipt-verification.json), [서버 manifest](../../evidence/capacity-codebook-transfer-20261023-r47/raw/manifest.json), [서버 완료](../../evidence/capacity-codebook-transfer-20261023-r47/server-completion.json), [CS 검토](../../evidence/capacity-codebook-transfer-20261023-r47/cs/review.json)에 연결한다. manifest 대상 비어 있지 않은 파일 2405개와 manifest 자체를 받아 원본 크기·SHA-256을 직접 대조했다(어댑터 엔트로피 마스킹 감지 여부: `True`, 복원 파일 수: `3`). source 145파일·input 109핀은 변하지 않았다. 빈 stdout/stderr 5개와 evidence ZIP 자체는 받지 않았다. manifest는 자기 해시 밖에 있고 same-channel hash는 host attestation이 아니다.

## 판정과 다음 방향

**고정 8토큰 가변 후보 용량(n=1..4) 중첩-AST 구성 및 다중해·보류 보편 질의 코드북 전이에서 의미 불변성 채택.** 이 결과는 가변 후보 용량(`n ∈ {1, 2, 3, 4}`) 단항 구성 파이프라인(`R35`)에서 중첩 leaf(`6/6` 서로 다른 AST)와 8개 토큰·64개 ordered 코드쌍을 모두 활성화하여 비등거리 코드북이 `feasible1..4` 연속 상태를 실제로 섭동시키는 조건에서도, 다중 적격 후보(`|F| ∈ {2, 3, 4}`)의 쌍별 상호 억제(`pair_i_j -> at_least_two`), 만장일치(`qtrue`/`qfalse`) 대 분할(`mixed`) 보편 질의, `complete=False` 미완결 기권(`incomplete`), 그리고 비역할 3개 상위 단계(`expr`, `feasible`, `query`)의 수렴 tick이 8개 코드북 전체에서 정확히 보존됨을 보인 유한 증거다. authored codebook을 학습된 표현·H03 구조 재사용·원계산 대체·속도/효율 증거로 합산하지 않으며, 최악 내부 마진 모서리 검증을 `64^n` 전체 곱집합 열거로 과장하지 않는다. core에 자동 반영하지 않으며, 이번 요청에서 추가 후속 실험은 자동 시작하지 않는다.
