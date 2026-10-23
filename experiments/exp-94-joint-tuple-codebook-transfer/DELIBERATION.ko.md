# R48 / EXP-94 방향성 토론

## 1. Executive Verdict
조건부 합의(`conditional_consensus`)다. [R37(`exp-83-joint-tuple`)](../exp-83-joint-tuple/RESULTS.ko.md)은 이항 관계 $C(X,Y)$와 $T(X,Y)$ 위에서 3층 주변곱 재교차 회로(`projection0`, `projection1`: `f0..3 -> p00..p11 -> e0..3 -> goal`), 4-튜플 분류기(`feasible4`), 봉인된 `hcr-r37-joint-tuple-v1` `binding`, 그리고 격리 소비기(`consume_t -> query4`)를 정의했으나, namespace당 $4/8$개 토큰(`{0,1,2,3}`: `cnot20`의 고정점 집합)만 사용해 $8/64$개 코드쌍만 노출되었고 불일치 역할 비교의 100%가 Hamming 거리 $d=1$($d=2,3$ 발생 `0`회, `pair` 입력 Hamming쌍 $4/16$개)에 갇혀 있었다. 이후 [R46(`exp-92-relational-codebook-transfer`)](../exp-92-relational-codebook-transfer/RESULTS.ko.md)은 3변수 조건부 $Z$ 파이프라인만 검증해 소비기가 $n=2$ 후보(`feasible2`)만 분류했고(`projection0/1`, `feasible4`, `query4` 미포함, 비등거리 코드북에서 $13/16 \sim 14/16$ Hamming쌍 및 $24/64$ 코드쌍만 실현), [R47(`exp-93-capacity-codebook-transfer`)](../exp-93-capacity-codebook-transfer/RESULTS.ko.md)은 단항 AST(`expr0..5`) 파이프라인에서만 `feasible1..4`와 `query1..4`를 검증했다. 따라서 R48(`exp-94-joint-tuple-codebook-transfer`)은 **이항 관계 4-튜플 결합 보존(`native_joint`) 대 주변곱 폐포(`native_marginal`: `projection0/1 -> feasible4 -> 봉인 binding -> consume_t -> query4`) 파이프라인에서 8토큰·코드북당 64/64 코드쌍·16/16 Hamming쌍 완전 coverage와 정보 경계(16 결합 서명 대 10 폐포 서명, 대각/반대각 및 L자형 상관 손실 반례) 보존 및 809회 6단계 전이 충분조건**을 한 번의 동결 실험으로 검증한다.

## 2. Consensus Proposal
공개 8토큰 어휘(`amber..coral`, 코드 `0..7`)의 112개 정방향 이항 관계 원천(`C_{i}_{j}, T_{i}_{j}`, $i \ne j \in \{0..7\}$)과 32개 base(`b00..b31`) × 8개 코드북 × 3개 팔(`native_joint`, `native_marginal`, `exact_joint` = `512` native + `256` exact = **`768` 평가**, 상위 파이프라인 **`32,832`회 settle**)을 동결한다. 이와 동시에 `role`(`64`회) → `pair`(`16`회 전수) → `or0..4`(`121`회) → `projection0/1`(`16+16 = 32`회) → `feasible4`(`32+32 = 64`회) → `query4`(`512`회)의 **총 `809`회 6단계 연속 스칼라 전이 프로브**(원천 포함 총 **`33,753`회 물리 settle**)를 분리 실행·검산한다.

## 3. Strong Consensus
`tools/r37_joint_tuple/runtime.py`의 `native_marginal`은 9그룹 3층 주변곱 재교차 네트워크(`projection0`, `projection1`)의 내부 중간 노드 상태 `e0..e3`(`goal`이 아님)을 추출해 `feasible4`에 전달하고, `promote`가 봉인한 연속 `binding`(`eligibility` 4개, `coverage_activation` 1개, `state_sha256`)을 격리 소비기 `consume_t`가 받아 $T(X,Y)$ 소속 스칼라 4개(`t0..t3`)와 함께 25그룹 `query4`로 구동한다. 비등거리 코드북(`cnot01`, `cnot12`, `cnot20`, `cnot_chain`, `swap01`)이 역할 단계 Hamming 거리 $d \in \{1,2,3\}$을 바꿀 때 `projection0/1` 내부 상태와 봉인된 `binding['eligibility']` 및 `state_sha256`/`binding_sha256`이 섭동되므로, `native_joint`(`16`개 서명, `256/256` strict) 대 `native_marginal`(`10`개 폐포 서명, 비직사각형 `c_mask in {6,9,7,11,13,14}`에서 상관 소실로 인한 `128/256` 기권·`0/256` 오확정)의 정보적 경계와 비역할 단계 tick 불변성을 직접 검증해야 한다. 대안 후보였던 `r38_shared_witness` 코드북 전이는 R46이 이미 검증한 3변수 삼각 관계 전단부와 겹치면서 격리 소비기(`consume_t`), `projection0/1`, `query4`를 모두 결여하므로 기각한다.

## 4. Material Disagreements
초기 검토에서는 16개 코호트 배정과 32개 코호트 배정이 각각 제안되었으나, 교차 검토(`T1`, `T2`)를 통해 `swap01 = [1,0,2,3,4,5,6,7]`이 `{2..7}`을 고정하므로 $|S \cap \{0,1\}| = 0$인 15개 4-토큰 부분집합과 5개 충돌 부분집합($\text{Bad}_5 = \{\{0,1,2,3\}, \{0,1,4,5\}, \{0,2,4,6\}, \{0,2,4,7\}, \{0,2,5,7\}\}$)을 제외한 정확히 **50개 부분집합(`300`개 순서 코호트)**만이 `8/8` 제한 사상 구별을 만족하며, 모든 코드북에서 `64/64` ordered 코드쌍과 `16/16` ordered Hamming쌍을 동시에 덮기 위해 23-코호트 완전 커버를 포함하는 **32-코호트 스케줄(`b00..b31`)**을 배정하기로 합의했다. 또한 `feasible4` 전이 프로브는 `native_joint`(`or0..4` 직접 입력 `32`회)와 `native_marginal`(`projection0/1` 경유 입력 `32`회) 최악 내부 마진 모서리를 모두 포함하는 `64`회(총 `809`회 단계 전이 프로브)로 통일했다.

## 5. Decision by Axis
- **RelationalTupleCoverageAndSignatures**: 112개 원천과 32개 base(Part I 16개 `c_mask=0..15` 완전 격자 + Part II 8개 대각/반대각 `c_mask in {6,9}×t_mask in {6,9}×order in {0,1}` + Part III 8개 L자형 `c_mask in {7,11,13,14}` 반례) × 8개 코드북 × 3개 팔(`768` 평가)로 모든 32개 base의 제한 사상 `8/8` 구별(무변경 `0/448`), 코드북당 `64/64` ordered 코드쌍 및 `16/16` ordered Hamming쌍 실현, `56/56` 교차 도메인 쌍 활성, `16` 결합 서명 대 `10` 주변곱 폐포 서명 및 보편 질의 전 구간을 검증한다.
- **MarginalClosureAndQuery4TransferSufficiency**: `role`(`64`) → `pair`(`16` 전수, `40,320` 전단사 동치류 수준 `645,120` 조합) → `or0..4`(`121`) → `projection0/1`(`32`) → `feasible4`(`64`) → `query4`(`512`) 총 **`809`회 6단계 전이 프로브**와, 비등거리 코드북에서 봉인 `binding`(`state_sha256`, `binding_sha256`)이 섭동될 때 비역할 5개 단계(`pair`, `membership`, `projection`, `feasible4`, `query4`) tick 불변 및 `448`짝 이산 의미·정보 경계 불변을 분리 검산한다.
- **BudgetAndNonDuplication**: 총 `112 + 809 + 32,832 = 33,753`회 물리 settle을 `worker=1`, `retry=0`, 단계 `240`초 / 전체 `600`초 상한으로 AI Research SSH(`ssh-ai-mcp`)에서 1회 실행하며, R47의 `audit` `KeyError` 교훈을 반영해 `preparation()`에서 768개 무변조 모의 레코드 전수 `audit` 통과 후 `ValueError` 전용 `25`개 합성 변조 거부 스위트를 사전 검증한다.

## 6. Evidence
`experiments/exp-83-joint-tuple/{RESULTS.ko.md,frozen_spec.json}`, `experiments/exp-84-shared-witness/RESULTS.ko.md`, `experiments/exp-92-relational-codebook-transfer/RESULTS.ko.md`, `experiments/exp-93-capacity-codebook-transfer/{RESULTS.ko.md,DELIBERATION.ko.md}`, `tools/r37_joint_tuple/{runtime.py,probe.py,verify.py}`, `tools/r38_shared_witness/{runtime.py,verify.py}`, `tools/r46_relational_codebook_transfer/{probe.py,verify.py}`, `tools/r47_capacity_codebook_transfer/{probe.py,verify.py}`를 직접 확인했다. 상세 출처와 검증 기록은 [decision-record.json](decision-record.json)에 보존한다.

## 7. Required Actions
공통 엔진(`src/hcr/`)과 기존 `R35~R47` 실행기를 수정하지 않고, 112개 원천·809회 6단계 전이 프로브·32 base × 8 코드북 × 3 팔 행렬을 동결한 뒤 `preparation()`에서 768개 무변조 레코드 감사와 25개 사전 변조 검사를 통과시켜 AI Research SSH에서 1회 실행하고 전체 저장 trace를 로컬에서 재생 검산한다.

## 8. Optional Optimizations
회로 구조 수정, 임계값 튜닝, 학습 루프 결합, 속도 경쟁 가설 재시도, $64^n$ 전체 곱집합 무차별 열거는 추가하지 않는다.

## 9. Unresolved
비등거리 코드북 섭동이 `role -> pair -> or0..4`와 3층 주변곱 재교차 커널(`projection0`, `projection1`의 내부 상태 `e0..e3`)을 거쳐 봉인된 `hcr-r37-joint-tuple-v1` `binding`(`state_sha256`)과 격리 소비기 `consume_t`(`query4` 25그룹)로 전파될 때, `448`짝 이산 의미 불변과 정보 경계(`native_joint` `256/256` 대 `native_marginal` `128/256` full·`256/256` 폐포·`128/256` 기권·`0/256` 오확정) 및 비역할 5개 단계 tick 불변이 실제로 100% 유지되는지는 서버 실행 전 미관측이다.

## 10. Method / Run Summary
`MEDIUM` 등급, `degraded_ok` 기본 경로로 2명의 격리된 blind reviewer(`c60689fe`, `5ee7fbdd`)와 Stage 4 교차 검토(`T1`, `T2`)를 수행한 뒤 Coordinator가 원자료를 직접 대조해 통합했다. 별도 Judge 요구가 없어 생성하지 않았으며 assurance는 `partially_independent`다.
