# R46 / EXP-92 방향성 토론

## 1. Executive Verdict
조건부 합의(`conditional_consensus`)다. R44(`exp-90-codebook-invariance`)와 R45(`exp-91-codebook-transfer-coverage`)는 단일 변수 unary AST 파이프라인(`r35/r36`, 깊이 3단계)에서만 8토큰·64코드쌍 코드북 불변성과 단계별 전이를 검증했다. 반면 R37~R43의 다변수 관계형 생산–소비 파이프라인(`r37/r38/r39/r40`, 깊이 6단계)은 어휘 8개 중 6개(`코드 0..5`)만 사용하고 보조 슬롯 `aux6, aux7`(`코드 6, 7`)을 단 한 번도 소비하지 않았으며, 모든 도메인 `X={0,1}, Y={2,3}, Z={4,5}`의 내부 XOR이 `1`로 고정되어 불일치 역할 비교의 100%가 Hamming 거리 $d=1$에서만 발생했고 `pair` 게이트는 가능한 16개 $(d_1, d_2) \in \{0,1,2,3\}^2$ 조합 중 4개($\{0,1\}^2$)만 경험했다. 또한 `r39`/`r40`에서는 생산자(`produce`)가 연속 부동소수점 배열(`slices` 8개, `factors` 12개, `xy/z` 6개)을 `payload_sha256`으로 봉인해 어휘·도메인 접근이 차단된 소비자(`consume`)에게 넘기므로, 비등거리 코드북(`cnot01`, `cnot12`, `cnot20`, `cnot_chain`, `swap01`)이 $d \in \{1,2,3\}$을 바꾸면 봉인된 연속 `payload` 수치와 `payload_sha256` 자체가 코드북마다 달라진다. R46(`exp-92-relational-codebook-transfer`)은 이 다변수 관계형 봉인 상태 경계에서 8토큰·16 Hamming쌍 coverage와 6단계 전이 충분조건을 한 번의 동결된 실험으로 검증한다.

## 2. Consensus Proposal
공개 8토큰 어휘(`amber..coral`, 코드 `0..7`) 전체를 균등하게 소비하는 대칭 4-cohort 도메인 분할(생략 쌍 `{5,6}, {3,4}, {1,2}, {0,7}`, 총 48개 원천)과 16개 base(8개 판별 마스크 삼중쌍 × 2 `order`) × 8개 코드북(`128`개 mapped context) 및 3개 봉인 표현(`native_joint`, `native_factor`, `native_compact`) + `exact_joint`(총 `512`개 평가, `2,560`개 질의 응답)를 동결한다. 이와 동시에 `role`(64회) → `pair`(16회 전수) → `or0..4`(121회) → `triple`(64회) → `projection`(`or2` 16회 + `or4` 256회 = 272회) → `consume`(`pair` 16회 + `feasible2` 16회 = 32회)의 **총 569회 6단계 연속 스칼라 전이 프로브**를 분리 실행·검산한다.

## 3. Strong Consensus
`r38/r39/r40`의 `validate()`는 단일 맥락의 활성 도메인이 서로소 2원소 도메인 3개(`|X ∪ Y ∪ Z| = 6`)임을 요구하고, `membership()`은 각 변수 도메인 내부에서만 토큰을 비교한다. 따라서 고정 도메인 `(0,1), (2,3), (4,5)`에 8개 코드북을 그대로 적용하면 `cnot12`, `cnot20`, `swap01`에서 도메인 내부 Hamming 거리가 `(1,1,1)`로 불변이 되어 봉인 `payload`가 전혀 섭동되지 않는다. 생략 쌍이 `{5,6}, {3,4}, {1,2}, {0,7}`인 대칭 4-cohort(`C0: X=[0,2],Y=[1,4],Z=[3,7]`, `C1: X=[0,6],Y=[2,5],Z=[1,7]`, `C2: X=[0,7],Y=[5,6],Z=[3,4]`, `C3: X=[2,3],Y=[1,6],Z=[4,5]`)를 사용하면 8개 토큰이 각각 정확히 3/4 cohort(24개 슬롯 중 3개)에 등장하고, 모든 cohort에서 `0`과 `1`이 분리되어 16개 모든 base에서 제한 대응이 8/8 구별(`mapped_pairs_actual_code_unchanged = 0/336`)되며, 7개 비영 XOR 차분 $\Delta \in \{1..7\}$을 모두 포괄해 8개 모든 코드북이 $d \in \{0,1,2,3\}$ 전체를 경험한다.

## 4. Material Disagreements
초기 검토에서는 2-cohort(`24` 원천, `order=0`)와 4-cohort(`48` 원천, `order in {0,1}`)가 비교됐으나, 교차 검토에서 (1) 2-cohort로는 상위 파이프라인 `pair` 단계에서 9개 비일치 쌍 $\{1,2,3\}^2$을 모두 덮을 수 없고, (2) `C0`에 `X=[0,1]`을 두면 `swap01`이 도메인 내부 원소만 맞바꿔 Hamming 거리를 바꾸지 못하며, (3) 3-도메인 구조상 비둘기집 원리에 의해 4-cohort에서 $(3,3)$ 쌍은 `identity`/`bit_reverse`/`xor7` 및 전체 행렬 합집합과 `pair(16)` 전수 전이 프로브에서 100% 덮고 개별 코드북에서는 $d \in \{0,1,2,3\}$ 4개 동치류 전수 실현으로 검증해야 함을 확인해 대칭 4-cohort 설계로 통합했다. 또한 `order=1`에서 `r39`(`slot = 3-i`)와 `r40`(`slot = i`)의 인덱싱 규약 차이를 맞추기 위해 각 실행기에 정규화된 질의 목록을 전달해 무수정 재사용(`ponytail`)하기로 합의했다.

## 5. Decision by Axis
- **Coverage**: 48개 원천과 대칭 4-cohort × 16 base × 8 코드북 × 3 native arm(`384` native + `128` exact)으로 모든 base에서 제한 대응 8/8 구별(무변경 0/336), 8토큰 균등 소비, 코드북별 $d \in \{0,1,2,3\}$ 전수 실현, 상위 파이프라인 `16/16` ordered Hamming 쌍 실현을 검증한다.
- **TransferSufficiency**: `role`(64) → `pair`(16 전수, 40,320개 bijection 전수 포괄) → `or0..4`(121) → `triple`(64) → `projection`(272) → `consume`(32) 총 569회 6단계 전이 프로브와, 비선형 코드북에서 연속 봉인 `payload`(`payload_sha256`)가 달라질 때 비역할 단계(`pair`, `membership`, `triple`, `projection`, `query_input`, `feasible`) tick 완전 불변 및 `native_compact`의 `96/640` 조건부 `unique -> many` 보류 경계 보존을 검산한다.
- **BudgetAndNonDuplication**: 총 `48 + 569 + 38,272 = 38,889`회 물리 native settle을 `worker=1`, `retry=0`, 단계 `240`초 / 전체 `600`초 상한으로 AI Research SSH(`ssh-ai-mcp`)에서 1회 실행하며, `preparation()` 단계에서 22개 합성 변조 거부 스위트를 사전 실행해 R45 유형의 서버 감사 예외 불일치를 원천 차단한다.

## 6. Evidence
`experiments/exp-91-codebook-transfer-coverage/RESULTS.ko.md`, `experiments/exp-85-z-query/{RESULTS.ko.md,frozen_spec.json}`, `experiments/exp-86-factor-query/RESULTS.ko.md`, `tools/r37_joint_tuple/runtime.py`, `tools/r38_shared_witness/runtime.py`, `tools/r39_z_query/{runtime.py,probe.py,verify.py}`, `tools/r40_factor_query/{runtime.py,probe.py,verify.py}`를 직접 확인했다. 상세 출처와 검증 기록은 [decision-record.json](decision-record.json)에 보존한다.

## 7. Required Actions
공통 엔진(`src/hcr/`)과 기존 R37~R45 실행기를 수정하지 않고, 48개 원천·569회 6단계 전이 프로브·128 case × 4 arm 행렬을 동결한 뒤 사전 변조 검사를 통과시켜 지정 AI Research SSH에서 1회 실행하고 전체 저장 trace를 로컬에서 재생 검산한다.

## 8. Optional Optimizations
회로 구조 수정, 임계값 튜닝, 학습 루프 결합, R40 비용 가설 재시도, $64^n$ 조합 무차별 열거는 추가하지 않는다.

## 9. Unresolved
비등거리 코드북 섭동으로 봉인된 연속 `payload`(`slices`, `factors`, `xy/z`)와 `payload_sha256`이 변할 때 6단계 관계형 체인의 비역할 단계 tick 불변과 격리된 소비자의 질의 판정 및 `native_compact` 보류 경계가 실제로 100% 유지되는지는 서버 실행 전 미관측이다.

## 10. Method / Run Summary
MEDIUM 등급, `degraded_ok` 기본 경로로 2명의 격리된 blind reviewer(`3dbc1505`, `004d994e`)와 각 1회 교차 검토를 수행한 뒤 Coordinator가 원자료를 대조해 통합했다. 별도 Judge 요구가 없어 생성하지 않았으며 assurance는 `partially_independent`다.
