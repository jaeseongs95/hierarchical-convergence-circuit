# R47 / EXP-93 방향성 토론

## 1. Executive Verdict
조건부 합의(`conditional_consensus`)다. [R35(`exp-81-compositional-slot`)](../exp-81-compositional-slot/RESULTS.ko.md)는 가변 후보 용량 $n \in \{1,2,3,4\}$의 분류기(`feasible1..4`: 9, 11, 14, 18 그룹)와 보편 질의 회로(`query1..4`: 13, 17, 21, 25 그룹)를 생성했으나, 실제 문맥(`C`)·전제(`T`)의 세 leaf가 서로 배타적이어서 8개 부울 leaf 패턴 중 $2/8, 3/8, 4/8$만 나타났고 6개 AST(`0..5`)가 $3/6, 4/6, 5/6$ 의미로 축약되었으며(`AST 2` 해집합 0건), 관측 $n=1$은 `complete=False`에서만, $n=4$는 `complete=True`에서만 실행되었다. 이후 [R36(`exp-82-overlap-composition`)](../exp-82-overlap-composition/RESULTS.ko.md), [R44(`exp-90-codebook-invariance`)](../exp-90-codebook-invariance/RESULTS.ko.md), [R45(`exp-91-codebook-transfer-coverage`)](../exp-91-codebook-transfer-coverage/RESULTS.ko.md)는 중첩 leaf와 8토큰 코드북 전이를 오직 **$n=2, \text{complete}=\text{True}$(`feasible2`, `query2`)**로만 제한했고, [R46(`exp-92-relational-codebook-transfer`)](../exp-92-relational-codebook-transfer/RESULTS.ko.md)의 다변수 관계형 소비기도 `feasible2`(`Z` 후보 2개)만 사용했다. 따라서 R47(`exp-93-capacity-codebook-transfer`)은 **가변 후보 용량 $n \in \{1,2,3,4\}$ 전체에서 중첩 AST(`6/6` 의미 구별)·다중해 경쟁($|F| \in \{0..4\}$, `feasible3/4`의 3·6개 쌍별 억제 노드)·보편 질의(`qtrue`/`qfalse` 만장일치 대 `mixed` 비대칭 분할 및 `complete=False` 미완결 보류)의 8토큰·64코드쌍 코드북 전이와 1,188회 4-용량 단계별 전이 충분조건**을 한 번의 동결 실험으로 검증한다.

## 2. Consensus Proposal
공개 8토큰 어휘(`amber..coral`, 코드 `0..7`)의 56개 원천(`8토큰 × {R, P0..2, Q0..2}`)과 가변 용량 $n \in \{1,2,3,4\}$ × 40개 base(총 **160개 base**) × 8개 코드북(`1,280` native + `160` exact = **`1,440` 평가**, 상위 파이프라인 **`28,160`회 settle**)을 동결한다. 이와 동시에 `role`(`64`회) → `expr0..5`(`384`회 전수) → `feasible1..4`(`4+8+16+32 = 60`회) → `query1..4`(`8+32+128+512 = 680`회)의 **총 `1,188`회 4-용량 단계별 연속 스칼라 전이 프로브**(원천 포함 총 **`29,404`회 물리 settle**)를 분리 실행·검산한다.

## 3. Strong Consensus
`tools/r35_compositional_slot/compiler.py`의 `feasible(n)`은 $\binom{n}{2} \in \{0,1,3,6\}$개의 쌍별 교집합 노드(`pair0_1..pair2_3`)와 후보 입력 `e_i`당 $1 + (n-1) = n$개의 하향 피드백 링크를 가지며, `query(n)`은 최대 25개 그룹($n=4$)으로 구성된다. 비등거리 코드북(`cnot01`, `cnot12`, `cnot20`, `cnot_chain`, `swap01`)이 역할 단계 Hamming 거리 $d \in \{1,2,3\}$을 바꿀 때 `feasible(n)`의 연속 `binding['eligibility']` 스칼라와 `binding['state_sha256']`이 섭동되므로, 다중 허용 후보($|F| \in \{2,3,4\}$) 경쟁과 `query3/4`의 만장일치(`2:0, 3:0, 4:0 -> qtrue`, `0:2, 0:3, 0:4 -> qfalse`) 대 비대칭 분할(`2:1, 1:2, 3:1, 2:2, 1:3 -> mixed`) 및 `complete=False`(`incomplete`) 경계의 불변성을 직접 검증해야 한다. 대안 후보였던 `r38_shared_witness` 코드북 전이는 R46이 이미 검증한 관계형 생산 단계(`role -> pair -> or0..4 -> triple -> projection`)와 중복되면서 `expr0..5`, `feasible1..3`, `query1..4`, `complete=False`를 모두 누락하므로 기각한다.

## 4. Material Disagreements
초기 검토에서는 용량별 40개 base 안에서 일부 AST 쌍만 표집하는 구성과 6개 AST 전체를 8개 leaf 마스크에 걸치는 구성이 논의되었으나, 교차 검토(`T1`, `T2`)를 통해 $n \in \{2,3,4\}$에서는 첫 두 후보 $(a_0, a_1)$에 상보적 마스크 $m \in \{0,1,2,3\}$과 $7 \oplus m \in \{7,6,5,4\}$를 배치하면 4개 케이스만으로 한 AST의 8개 leaf 패턴(`0..7`)을 모두 포괄한다는 사실을 확인했다. 이에 따라 용량당 40개 base를 **Part I(24개: 6 AST × 4 상보 마스크 완전 격자, `complete=True`) + Part II(8개: 다중해 $|F| \in \{0..4\}$ 및 만장일치/비대칭 분할 질의, `complete=True`) + Part III(8개: `complete=False` 미완결 보류 대조)**로 통일하고, `query{n}` 극값 프로브는 물리 데이터흐름과 동일하게 해당 용량 `feasible{n}`의 최악 내부 마진 경계로 구동하기로 합의했다.

## 5. Decision by Axis
- **CapacityAndOverlapCoverage**: 56개 원천과 160개 base($n=1..4$ 각 40개) × 8개 코드북(`1,280` native + `160` exact = `1,440` 평가)으로 160개 모든 base에서 제한 사상 `8/8` 구별(무변경 `0/1,120`), 코드북당 `64/64` ordered 코드쌍 및 $d \in \{0,1,2,3\}$ 실현, 용량별 `6/6` 서로 다른 AST 의미 및 $|F| \in \{0..4\}$·보편 질의 전 구간을 검증한다.
- **MultiCandidateTransferSufficiency**: `role`(`64`) → `expr0..5`(`384` 전수, `40,320` 전단사 동치류 수준 `15,482,880` 조합) → `feasible1..4`(`4+8+16+32 = 60`) → `query1..4`(`8+32+128+512 = 680`) 총 **`1,188`회 단계별 전이 프로브**와, 비등거리 코드북에서 연속 `eligibility`(`state_sha256`)가 섭동될 때 비역할 단계(`expr`, `feasible1..4`, `query1..4`) tick 불변 및 `1,120`짝 이산 의미 불변을 분리 검산한다.
- **BudgetAndNonDuplication**: 총 `56 + 1,188 + 28,160 = 29,404`회 물리 settle을 `worker=1`, `retry=0`, 단계 `240`초 / 전체 `600`초 상한으로 AI Research SSH(`ssh-ai-mcp`)에서 1회 실행하며, `preparation()`에서 모의 번들로 `25`개 합성 변조 거부 스위트를 사전 검증한다.

## 6. Evidence
`experiments/exp-81-compositional-slot/RESULTS.ko.md`, `evidence/compositional-slot-20261020-r35/analysis.json`, `experiments/exp-82-overlap-composition/RESULTS.ko.md`, `experiments/exp-91-codebook-transfer-coverage/{RESULTS.ko.md,frozen_spec.json}`, `experiments/exp-92-relational-codebook-transfer/RESULTS.ko.md`, `tools/r35_compositional_slot/{compiler.py,runtime.py,verify.py}`, `tools/r36_overlap_composition/{runtime.py,verify.py}`, `tools/r45_codebook_transfer_coverage/{probe.py,verify.py}`를 직접 확인했다. 상세 출처와 검증 기록은 [decision-record.json](decision-record.json)에 보존한다.

## 7. Required Actions
공통 엔진(`src/hcr/`)과 기존 `R35~R46` 실행기를 수정하지 않고, 56개 원천·1,188회 4-용량 전이 프로브·160 base × 8 코드북 행렬을 동결한 뒤 25개 사전 변조 검사를 통과시켜 AI Research SSH에서 1회 실행하고 전체 저장 trace를 로컬에서 재생 검산한다.

## 8. Optional Optimizations
회로 구조 수정, 임계값 튜닝, 학습 루프 결합, 속도 경쟁 가설 재시도, $64^n$ 전체 곱집합 무차별 열거는 추가하지 않는다.

## 9. Unresolved
비등거리 코드북 섭동이 $n \in \{3,4\}$의 다중 하향 피드백(`feasible3/4`의 3개·6개 `pair_i_j` 노드)을 통해 연속 `eligibility`와 `state_sha256`을 변화시킬 때, `query3/4`(21, 25 그룹)의 만장일치(`3:0, 4:0, 0:3, 0:4`) 대 비대칭 분할(`2:1, 1:2, 3:1, 2:2, 1:3 -> mixed`) 판정과 비역할 단계(`expr`, `feasible1..4`, `query1..4`) tick 불변이 실제로 100% 유지되는지는 서버 실행 전 미관측이다.

## 10. Method / Run Summary
`MEDIUM` 등급, `degraded_ok` 기본 경로로 2명의 격리된 blind reviewer(`6c9b3829`, `47a1c7ad`)와 각 1회 교차 검토(`T1`, `T2`)를 수행한 뒤 Coordinator가 원자료를 직접 대조해 통합했다. 별도 Judge 요구가 없어 생성하지 않았으며 assurance는 `partially_independent`다.
