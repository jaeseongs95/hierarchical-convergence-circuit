# R45 / EXP-91 방향성 토론

## 1. Executive Verdict
조건부 합의(`conditional_consensus`)다. R44(`exp-90-codebook-invariance`)가 남긴 두 미해결 과제—(1) 실제 파이프라인에서 등장하는 토큰이 전체 3-bit 코드 공간(`0..7`, 64개 ordered 코드쌍)을 모두 덮는지와 (2) 역할 단계(`equality`)의 유한 전이가 후속 계산(`expr` → `feasible2` → `query2`)까지 성립하는 조건의 분리—를 한 번의 동결된 실험으로 검증한다.

## 2. Consensus Proposal
8개 어휘 토큰 전체(`amber..coral`, 코드 `0..7`)를 덮는 56개 원천(`R` 8 + `P0..2` 24 + `Q0..2` 24)과 128개 base × 8개 코드북(`1,024` native + `128` exact)을 구성해 모든 단일 base에서 8개 코드북의 제한 대응이 8/8 서로 구별되도록(`mapped_pairs_actual_code_unchanged = 0`) 동결한다. 이와 동시에 역할 64입력의 4개 Hamming 동치류($d \in \{0,1,2,3\}$) 분해, 6개 AST × $4^3 = 384$개 `expr` 전수 전이, `feasible2`(16회)·`query2`(64회) 극값 구간 경계를 분리 실행·검산한다.

## 3. Strong Consensus
`equality(cfg)`는 비트 위치·극성 대칭이므로 초기값 `0.5`에서 64개 ordered 3-bit 입력쌍의 수렴 스칼라 `state['goal']`과 tick 수는 오직 Hamming 거리 $d \in \{0,1,2,3\}$에 의해서만 결정되는 4개 값($d=0$: `35` tick, $d=1$: `32` tick, $d=2$: `31` tick, $d=3$: `29` tick)을 갖는다. R44에서 `cnot01`(`73,916` tick)과 `cnot_chain`(`72,380` tick)의 상위 tick 감소(`-768`, `-2,304`)는 768개 불일치 역할 호출이 $d=1$에서 $d=2, 3$으로 이동한 것과 정확히 일치한다. 또한 `evaluate()`는 이산 `adopted`가 아니라 연속 스칼라 `4*(2*goal-1)`을 `expr`에 전달하므로, 이산 역할 일치만으로 후속 수렴을 가정하지 않는다.

## 4. Material Disagreements
초기 후보에서는 8개 토큰을 `(0,1),(2,3),(4,5),(6,7)` 후보 쌍으로만 나누는 방안이 검토됐으나, 교차 검토에서 단일 base 안에 2개 토큰만 등장하면 제한 대응이 여전히 4~6개로 축약되고 `(c_mask=7, t_mask=7)`에서 거짓 leaf 슬롯이 사라지는 결함을 확인했다. 이를 해결하기 위해 1-토큰 구별 앵커를 갖는 후보 쌍 `(0,6),(1,2),(3,5),(4,7)`과 `xor_offsets = [7,1,2,4]`를 결합해 모든 128개 base에서 제한 대응 8/8 구별과 코드북당 64/64 ordered 코드쌍 소비를 동시에 만족하도록 합의했다.

## 5. Decision by Axis
- **Coverage**: 56개 원천과 128개 base × 8개 코드북으로 모든 base에서 제한 대응 8/8 구별(무변경 0/896) 및 코드북당 64/64 ordered 코드쌍과 이종 비영 Hamming 삼중쌍 소비를 검증한다.
- **TransferSufficiency**: 64개 역할 입력의 4개 Hamming 동치류 분해 → `6 AST × 4^3 = 384`회 `expr` 전수 전이(40,320개 모든 bijection이 `expr` 단계에 줄 수 있는 입력 전수 포괄) → `feasible2`(16회)·`query2`(64회) 극값 구간 경계 검사를 분리한다. `feasible2`/`query2`에 대해 $64^n$ 전체 열거를 주장하지 않는다.
- **BudgetAndNonDuplication**: 총 `56 + 64 + 384 + 80 + 18,432 = 19,016`회 native settle을 `worker=1`, `retry=0`, 단계 `240`초 / 전체 `600`초 상한으로 AI Research SSH(`ssh-ai-mcp`)에서 1회 실행한다. R31 학습비용 음성 및 R43 미세최적화 미채택을 보존한다.

## 6. Evidence
`experiments/exp-90-codebook-invariance/RESULTS.ko.md`, `evidence/codebook-invariance-20261020-r44/analysis.json` 및 `raw/n000..n007.json`, `tools/r35_compositional_slot/{compiler.py,runtime.py}`, `src/hcr/dynamics.py`를 직접 확인했다. 상세 출처와 검증 기록은 [decision-record.json](decision-record.json)에 보존한다.

## 7. Required Actions
공통 엔진(`src/hcr/`)과 R36 `execute`를 수정하지 않고, 56개 원천·128 base·64 역할·384 `expr`·80 극값 경계를 동결한 뒤 지정 AI Research SSH에서 1회 실행하고 전체 저장 trace를 로컬에서 재생 검산한다.

## 8. Optional Optimizations
회로 구조 수정, 임계값 튜닝, 학습 루프 결합, $64^n$ 조합 무차별 열거는 추가하지 않는다.

## 9. Unresolved
이종 비영 Hamming 거리($d \in \{1,2,3\}$)가 섞인 384개 `expr` 입력과 80개 극값 경계 및 8토큰·64쌍 파이프라인 전체에서의 실제 수렴 여부는 서버 실행 전 미관측이다.

## 10. Method / Run Summary
MEDIUM 등급, `degraded_ok` 기본 경로로 2명의 격리된 blind reviewer(`33d0e25a`, `1960553a`)와 각 1회 교차 검토를 수행한 뒤 Coordinator가 원자료를 대조해 통합했다. 별도 Judge 요구가 없어 생성하지 않았으며 assurance는 `partially_independent`다.
