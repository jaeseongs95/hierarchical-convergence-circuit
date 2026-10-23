# R47 / EXP-93: 가변 후보 용량(`n=1..4`) 중첩 AST·다중해 보편 질의 코드북 전이 및 1,188회 단계별 충분조건 분리

[MEDIUM 방향 토론](DELIBERATION.ko.md)에 따라 [R35(`exp-81-compositional-slot`)](../exp-81-compositional-slot/RESULTS.ko.md), [R36(`exp-82-overlap-composition`)](../exp-82-overlap-composition/RESULTS.ko.md), [R45(`exp-91-codebook-transfer-coverage`)](../exp-91-codebook-transfer-coverage/RESULTS.ko.md) 사이에 남아 있던 세 가지 구조적 공백을 분리해 검증한다:
1. R35는 `feasible1..4`($9, 11, 14, 18$ 그룹; $\binom{n}{2} \in \{0,1,3,6\}$개 쌍별 억제 노드 `pair0_1..pair2_3`)와 `query1..4`($13, 17, 21, 25$ 그룹)를 정의했으나, 세 leaf가 서로 배타적이어서 6개 AST가 $3/6 \sim 5/6$ 의미로 축약되었고(`AST 2` 해집합 0건), 관측 $n=1$은 `complete=False`에서만, $n=4$는 `complete=True`에서만 실행되었다.
2. R36, R44, R45는 중첩 leaf와 8토큰 코드북 전이를 오직 **$n=2, \text{complete}=\text{True}$(`feasible2`, `query2`)**로만 고정했고, R46의 다변수 관계형 소비기도 `feasible2`(`Z` 후보 2개)만 사용했다.
3. `feasible(n)`에서 각 후보 입력 `e_i`는 $1(\text{goal}) + (n-1)(\text{pair}_{i,j}) = n$개의 하향 피드백 링크를 받으므로, 비등거리 코드북(`cnot01`, `cnot12`, `cnot20`, `cnot_chain`, `swap01`)이 역할 단계 Hamming 거리 $d \in \{1,2,3\}$을 바꿀 때 연속 `binding['eligibility']` 스칼라와 `binding['state_sha256']`이 코드북마다 달라진다. 이때 다중 허용 후보($|F| \in \{2,3,4\}$) 억제 경계와 `query3/4`의 만장일치(`2:0, 3:0, 4:0 -> qtrue`, `0:2, 0:3, 0:4 -> qfalse`) 대 비대칭 분할(`1:1, 2:1, 1:2, 3:1, 2:2, 1:3 -> mixed`) 및 `complete=False`(`incomplete`) 보류 경계, 그리고 비역할 단계(`expr`, `feasible1..4`, `query1..4`)의 수렴 tick이 모두 불변인지 검증한다.

## 1. 56개 원천과 가변 용량(`n=1..4`) 160-Base · 8/8 제한 사상 · 6/6 AST 구별 행렬

공개 8토큰 어휘(`amber`, `cobalt`, `jade`, `violet`, `wheat`, `umber`, `teal`, `coral`, 코드 `0..7`) 전체에 대해 후보 원천 `R` 8개(`n0_R_0..7`), 문맥 원천 `P0/P1/P2` 각 8개(`24`개), 질의 원천 `Q0/Q1/Q2` 각 8개(`24`개)로 총 **56개 실제 native path 원천**을 생성한다.

후보 용량 $n \in \{1, 2, 3, 4\}$ 각각에 대해 **40개 base(총 160개 base)**를 다음 세 파트로 구성하고, 8개 전역 3-bit bijection(`identity`, `bit_reverse`, `xor7`, `cnot01`, `cnot12`, `cnot20`, `cnot_chain`, `swap01`)을 적용해 **`1,280`개 native 평가 + `160`개 exact 평가(총 `1,440` 평가, `18` 배치 × `80` 기록)**를 고정한다:
- **Part I (`24`개 base/용량, `complete = True`) — `6 AST × 4 상보 마스크` 완전 격자**:
  - $n \in \{2, 3, 4\}$에서는 첫 두 후보 $(a_0, a_1)$에 대해 leaf 마스크 $k \in \{0, 1, 2, 3\}$으로 세 leaf subject를 $\{a_0, a_1\}$에서 배정하면 $a_0$이 마스크 $k \in \{0..3\}$을 받는 동시에 $a_1$이 상보 마스크 $7 \oplus k \in \{7, 6, 5, 4\}$를 받는다. 따라서 6개 AST(`0..5`) × 4개 상보 마스크(`24`개 케이스)만으로 용량별 `C`와 `T` 각각에서 **`48/48`개 모든 `(AST, mask)` 조합(`6 AST × 8 마스크 0..7`)**이 실현되고 **`6/6` 서로 다른 8비트 진리벡터 및 해집합 의미**가 구별된다.
  - $n = 1$에서는 단일 후보 $a_0$에 대해 6개 AST를 모두 구별하는 4개 마스크 $M_{4A} = [1, 2, 5, 7]$(`C`)과 나머지 4개 마스크 $M_{4B} = [0, 3, 4, 6]$(`T`)을 교차 배치해 $a_0$ 단독으로 `6/6` 진리벡터 구별과 `C ∪ T` `48/48` `(AST, mask)` 포괄을 달성한다.
- **Part II (`8`개 base/용량, `complete = True`) — 다중해 카디널리티(`|F| in {0..4}`) 및 보편 질의 분할(`qtrue`/`qfalse`/`mixed`/`empty`) 행렬**:
  - $n=1$: $|F|=0$(`none`/`empty`), $|F|=1$(`unique` `qtrue`/`qfalse`).
  - $n=2$: $|F|=0$, $|F|=1$(후보 순서 역전 `order=1` 불변 대조 포함), $|F|=2$(`many`: 만장일치 `2:0 -> qtrue`, `0:2 -> qfalse`, 분할 `1:1 -> mixed`).
  - $n=3$: $|F|=0, 1$, $|F|=2`(`2:0 -> qtrue`, `0:2 -> qfalse`, `1:1 -> mixed`), $|F|=3$(`feasible3`의 `3/3`개 쌍별 억제 노드 활성: 만장일치 `3:0 -> qtrue`, `0:3 -> qfalse`, 비대칭 분할 `2:1 -> mixed`, `1:2 -> mixed`).
  - $n=4$: $|F|=0, 1$, $|F|=2`(`1/6` `pair` 활성), $|F|=3`(`3/6` `pair` 활성: `3:0 -> qtrue`, `0:3 -> qfalse`, `1:2 -> mixed`), $|F|=4$(`feasible4`의 `6/6`개 쌍별 억제 노드 전체 활성: 만장일치 `4:0 -> qtrue`, `0:4 -> qfalse`, 3종 분할 `3:1 -> mixed`, `2:2 -> mixed`, `1:3 -> mixed`).
- **Part III (`8`개 base/용량, `complete = False`) — 미완결 보류(`incomplete` / `abstain_incomplete`) 대조**:
  - 모든 용량 $n \in \{1, 2, 3, 4\}$(R35에서 누락되었던 $n=4, \text{complete}=\text{False}$ 포함)에서 관측 후보들이 $|F|=0$, $|F|=1$, $|F|=n$ 만장일치(`n:0`, `0:n`) 및 분할을 이루는 조건에 `complete = False`를 부여해 오확정 `0`건을 검증한다.
- **제한 사상 `8/8` 구별 및 `64/64` 코드쌍 보장**:
  - 모든 `160`개 base의 활성 토큰 집합은 구별 앵커 부분집합(`{1,6}`, `{1,7}`, `{0,3,5}`, `{0,3,6}`, `{0,5,6}`)을 포함해 **`160/160` 모든 base에서 제한 사상 동치류 수가 정확히 `[8]`(무변경 `0/1,120`짝, 변경 `1,120/1,120`짝)**이며, 각 코드북은 상위 파이프라인에서 **64/64 ordered 코드쌍** 전체를 소비한다.

## 2. 4-용량 단계별 전이 충분조건 분리 (`64 + 384 + 60 + 680 = 1,188` Settles)

1. **`role` 4개 Hamming 동치류 분해 (`64` settles)**:
   $8 \times 8 = 64$개 ordered 3-bit 입력쌍을 실행해 $d(x,y) \in \{0,1,2,3\}$의 4개 동치류 대표값 $G = \{g_0, g_1, g_2, g_3\}$과 $40,320 \times 64 = 2,580,480$건의 전단사 역할 일치 대조를 검산한다.
2. **`role -> expr0..5` 전수 전이 (`6 × 4^3 = 384` settles)**:
   6개 AST × 64개 Hamming 거리 삼중쌍 $(d_0, d_1, d_2) \in \{0,1,2,3\}^3$을 전수 실행해 $384 \times 40,320 = 15,482,880$건의 전단사 동치류 합성이 오답 `0`건임을 확인하고, `expr` 거짓 출력 최댓값 `expr_false_max`와 참 출력 최솟값 `expr_true_min`(최악 내부 마진 경계)을 추출한다.
3. **`feasible1..4` 4-용량 내부 마진 극값 경계 (`4 + 8 + 16 + 32 = 60` settles)**:
   각 용량 $n \in \{1, 2, 3, 4\}$에 대해 모든 $2^{n+1}$개 부울 모서리 $(b_0, \dots, b_{n-1}, \text{complete}) \in \{\text{False}, \text{True}\}^{n+1}$에서 `e_i`를 `{expr_false_max, expr_true_min}`으로, `complete`를 `±gain`으로 구동해 `feasible{n}`의 분류(`none`/`unique`/`many`/`incomplete`), 후보 마진 분리($\ge 0.65$ 대 $\le 0.35$), 그리고 용량별 최악 출력 경계(`elig_false_max[n]`, `elig_true_min[n]`, `cov_false_max[n]`, `cov_true_min[n]`)를 추출한다.
4. **`query1..4` 4-용량 보편 질의 극값 경계 (`8 + 32 + 128 + 512 = 680` settles)**:
   각 용량 $n \in \{1, 2, 3, 4\}$에 대해 모든 $2^{2n+1}$개 부울 모서리 $(eb_0, \dots, eb_{n-1}, tb_0, \dots, tb_{n-1}, \text{complete}) \in \{\text{False}, \text{True}\}^{2n+1}$에서 `e_i`를 해당 용량의 `{elig_false_max[n], elig_true_min[n]}`으로, `t_i`를 `{expr_false_max, expr_true_min}`으로, `complete`를 `{cov_false_max[n], cov_true_min[n]}`으로 구동해 `680/680` 전수 모서리에서 `qtrue`/`qfalse`/`empty`/`mixed`/`incomplete` 판정 보존을 검산한다.

## 3. 비용·자원 상한과 검증 경계

원천 `56` + 단계별 전이 프로브 `1,188`(`64 + 384 + 60 + 680`) + 상위 파이프라인 `28,160`($n=1: 320 \times 10 = 3,200$, $n=2: 320 \times 18 = 5,760$, $n=3: 320 \times 26 = 8,320$, $n=4: 320 \times 34 = 10,880$) = **총 `29,404`회 물리 native settle**(최대 `4,704,640` tick)을 지정 AI Research SSH(`ssh-ai-mcp`)에서 `worker=1`, `retry=0`, 단계 `240`초 / 전체 `600`초, `raw 128MiB` / `cache 128MiB` / `AS 512MiB` 상한으로 1회 실행한다. `preparation()` 단계에서 모의 번들로 `25`개 합성 변조 거부 스위트를 사전 검증하며, 학습·세계 측정·로컬 native 실행은 `0`회다.
