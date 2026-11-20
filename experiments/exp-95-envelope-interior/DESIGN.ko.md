# R49 / EXP-95 설계: R48 6단계 전이 프로브의 "최악 모서리"는 실제 최악인가 — 실제 입력 포함 검사와 내부점 반증 시험

작성 2026-11-20. 이 문서와 [frozen_spec.json](frozen_spec.json)은 실행 전에 작성했고 실행 뒤에는 수정하지 않는다. 결과 문서에 두 파일의 SHA-256을 기록한다.
번호 R49 / EXP-95는 R48 / EXP-94 다음 순번을 잠정 사용한 것이다(과거 `R049`·EXP-30과 다른 계열).

## 1. 출발점

[R48 / EXP-94](../exp-94-joint-tuple-codebook-transfer/RESULTS.ko.md)의 809-settle 6단계 전이 프로브는 각 단계의 출력에서 관측한 최솟값·최댓값을 다음 단계의 입력 "모서리"로 주입했다. 거짓 입력은 관측 최댓값(`false_max`), 참 입력은 관측 최솟값(`true_min`)만 사용했고, 결과 문서는 이를 "최악 내부 마진 모서리"라 부르면서 `64^n` 전체 열거가 아니라고 한계를 적었다.

이 프로브가 실제 파이프라인(768 평가, 32,832 상위 settle)과 그 밖의 조합에 대한 충분조건 역할을 하려면 R48이 직접 검사하지 않은 두 전제가 필요하다.

1. **포함 전제**: 실제 상위 파이프라인에서 각 단계가 받은 입력이 프로브가 가정한 입력 구간(envelope) 안에 있다.
2. **극값 전제**: 입력 구간의 내부점은 모서리보다 나쁘지 않다. 즉 내부점에서도 판정이 유지되고, 출력이 모서리에서 얻은 출력 구간을 벗어나지 않는다.

극값 전제는 자명하지 않다. `settle`은 residual이 tolerance(1e-6) 이하로 patience(4)회 지속되면 멈추므로 종료 tick이 입력에 따라 불연속적으로 바뀌고, 프로그램에는 음의 가중치(억제, NOT 항)와 top-down 링크가 있어 출력이 입력의 단조 함수라는 보장이 없다.

## 2. 질문과 사전 예측

- **Q-A (포함, 저장 자료 분석, 새 settle 0회)**: R48 서버 raw의 768 평가가 참조한 모든 상위 trace에서, 단계 입력 drive와 단계 출력이 `transfer.json`의 구간 안에 있는가?
- **Q-B1 (의미 보존)**: 구간 내부점에서 각 단계의 판정(`adopted`, e 출력의 참/거짓 분류, `feasible4` kind, `query4` tag)이 같은 부울 패턴의 R48 모서리 판정과 같은가?
- **Q-B2 (극값성)**: 내부점의 출력이 R48 모서리에서 얻은 출력 구간 밖으로 나가는가?

사전 예측(작성자, 실행 전): B1은 전부 보존될 것으로 예상한다(판정 임계 0.35/0.65에 비해 구간이 매우 좁다). B2는 불확실하며, 종료 tick 불연속 때문에 1e-6 근방 크기의 초과가 나올 수 있다고 본다. A는 role 출력의 동치류 내부 편차(1e-17 규모)가 하류로 전파되므로 엄밀한 포함이 깨질 가능성이 있다고 본다. 어느 쪽이든 그대로 보고한다.

## 3. 고정 입력

모든 기준값은 R48 서버 raw `evidence/joint-tuple-codebook-transfer-20261023-r48/raw/transfer.json`의 `*_bounds`와 행에서 읽는다. Program·Config는 `experiments/exp-94-joint-tuple-codebook-transfer/frozen_spec.json`의 `programs`·`kernel` 그대로다. 초기 상태는 0.5, drive는 원 runtime과 같은 식 `evidence_gain*(2*v-1)`이다. 핀 목록은 [input_manifest.json](input_manifest.json).

## 4. 절차

### C0 통제: 로컬 모서리 프로브 재계산
R48 `probe.run_stage_transfer`를 수정 없이 로컬에서 호출해 809 settle을 다시 계산하고, `network_id`를 제외한 전체 결과가 서버 `transfer.json`·`roles.json`과 **완전히 같은 값**(JSON float 정확 일치)인지 확인한다. 불일치하면 이 호스트의 수치가 기준과 다르다는 뜻이므로 B의 극값성 판정은 `CONTROL_FAILED`로 표시하고 해석하지 않는다(의미 보존 수치는 기술만 한다).

### A 포함 검사 (저장 자료)
`batch00..11.json`의 `network_ids`가 참조하는 trace(참조 횟수 포함)를 `program_key`로 분류한다.

| 단계 | 입력 검사 | 출력 검사 |
|---|---|---|
| `pair` | `m0`,`m1` drive가 4개 role 대표값의 drive 중 하나와 정확히 같음, `m2 = -gain` | `goal` ∈ pair 거짓 구간 또는 = `true_val` |
| `or0..4` | 각 `m_i` ∈ pair 거짓 구간 또는 = pair `true_val` | `goal` ∈ membership 거짓/참 구간 |
| `projection0/1` | 각 `f_i` ∈ membership 거짓/참 구간 | `e0..3` ∈ projection 거짓/참 구간 |
| `feasible` | 각 `e_i` ∈ membership 또는 projection 거짓/참 구간, `complete = +gain` | `e0..3` ∈ eligibility 거짓/참 구간, `complete` ∈ cov 참 구간 |
| `query` | `e_i` ∈ eligibility 구간, `t_i` ∈ membership 구간, `complete` ∈ cov 구간 | (다음 단계 없음) |

구간 비교는 drive 공간에서 한다(`v -> gain*(2*v-1)`은 부동소수에서도 비감소). 구간 밖 항목 수(고유 trace 기준과 참조 가중 기준)와 최대 초과량(값 단위)을 기록한다.

### B 내부점 시험 (새 로컬 settle)

| 단계 | 표본 | settle 수 |
|---|---|---:|
| B1 `or0..4` | 서버 `pair_transfer` 16개 실제 출력값의 모든 L-튜플, L=0..4 **전수** | 69,905 |
| B2 `projection0/1` | order 2 × 부울 패턴 16 × 좌표별 {하한, 중점, 상한}^4 = 81 | 2,592 × 2 arm |
| B3 `feasible` | 입력원 2(`direct_or`: membership 구간, `via_projection`: projection 구간) × 패턴 32 × {하한, 중점, 상한}^4 (`complete`는 R48과 같이 ±gain 고정) | 5,184 × 2 arm |
| B4 `query` | 패턴 512 × 16개 수준 배정(R48 모서리, 전부 중점, 반대 모서리, 고정 seed 무작위 {하한, 중점, 상한}^9 13개) | 8,192 × 2 arm |

"하한/상한"은 좌표의 부울 분류에 해당하는 R48 구간의 양 끝, "중점"은 `(lo+hi)/2`다. B4의 무작위 배정은 `random.Random('r49-query-<패턴번호>')`로 고정한다.

arm 두 개:
- `envelope`: R48 구간 그대로. Q-B1과 Q-B2를 판정한다.
- `inflated`: 각 구간을 양쪽으로 δ=1e-3 넓힌 구간([0,1]로 절단). Q-B1만 판정한다(구간 여유에 대한 민감도). B1은 유한 전수이므로 `inflated`가 없다.

검사:
- 의미: B1 `adopted == any(bools)` 그리고 `stable_decision`; B2 각 `e_i`가 R48 같은 (order, 패턴) 행의 `expected_e` 분류와 일치(참 ≥ 0.65, 거짓 ≤ 0.35); B3 `onehot` kind가 R48 같은 (입력원, 패턴) 행의 kind와 일치; B4 `onehot` tag가 R48 같은 패턴 행의 tag와 일치.
- 극값(`envelope` arm): B1 `goal` ∈ membership 구간; B2 `e_i` ∈ projection 구간; B3 `e_i`·`complete` 상태 ∈ eligibility·cov 구간. B4는 하류 구간이 없어 극값 검사 없이 판정 여유만 기록한다.
- 모든 단계에서 최소 판정 여유(참 출력의 `v-0.65`, 거짓 출력의 `0.35-v`의 최솟값)와 tick 범위를 기록한다.

새 settle 합계: 809 + 69,905 + 2×(2,592 + 5,184 + 8,192) = **102,650**. 학습 0, `World.measure` 0, 엔진·R48 도구 수정 0. worker 1, retry 0, **본 실행 1회**. 결정성 확인을 위한 동일 명령 재실행 1회는 새 조건이 아니며 행 digest 일치 여부만 본다.

## 5. 판정 규칙 (실행 전 고정)

- A: 입력·출력 모두 구간 밖 0건이면 `COVERED`, 아니면 `NOT_COVERED`(건수·최대 초과량 병기).
- B1(의미): arm·단계별 불일치 0건이면 `PRESERVED`, 아니면 `VIOLATED`.
- B2(극값): 단계별 구간 밖 출력 0건이면 `NOT_REFUTED_IN_SAMPLE`, 1건 이상이면 `REFUTED`(반례 좌표·초과량 보존).
- 종합 문장은 위 세 판정을 그대로 조합한다. 결과를 본 뒤 δ·표본·구간·임계를 바꾸지 않는다. 추가 조건이 필요해 보이면 다음 사이클 후보로만 적는다.

## 6. 해석 경계

- B의 표본은 격자·전수(B1)·고정 무작위이며 구간 전체에 대한 증명이 아니다. `NOT_REFUTED_IN_SAMPLE`은 극값 전제의 증명이 아니고, `PRESERVED`는 구간 전체의 의미 보존 증명이 아니다.
- `REFUTED`가 나와도 R48의 768 평가 결과나 448짝 의미 불변 판정을 뒤집지 않는다. 바뀌는 것은 "모서리 = 최악"이라는 표현과, 모서리 프로브를 충분조건으로 쓸 때 필요한 여유의 크기다.
- B1의 전수는 "서버 표의 16개 pair 출력값"에 대한 전수다. 실제 파이프라인의 pair 출력이 이 16개 값과 정확히 같은지는 A가 따로 본다.
- C0는 같은 코드를 다른 호스트에서 다시 실행한 것이며 독립 구현 감사가 아니다. 서버 libc 버전은 원 기록에 없어 UNKNOWN이다.
- authored codebook·수작업 Program에 대한 수치 강건성 연구다. 학습된 표현, H03 구조 재사용, 원계산 대체, 속도·효율에 대한 증거로 합산하지 않는다. 새 독립 표본 0.
- 설계·구현·실행·검산을 한 작성자(AI 연구 보조)가 한 세션에서 수행했다. blind 토론·별도 Judge는 없었다.
