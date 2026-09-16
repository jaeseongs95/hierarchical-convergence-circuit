# EXP-03 — Misconvergence

## Status

`draft`

## Research question

Can a normally learned prior produce a stable, high-confidence, but externally wrong attractor on ambiguous or adversarially selected inputs?

## Working prediction

The model predicts a separable regime of stable-but-wrong convergence rather than only non-convergence or random error.

## Required controls

- matched task information
- frozen success criteria
- deterministic seeds where applicable
- repeated trials
- explicit baseline
- ablation of the mechanism under test

## Primary measures

- selected attractor
- convergence stability
- external mismatch
- correction latency
- post-feedback revision

## Falsification / failure condition

Define before execution. The experiment is not considered supportive merely because the system can produce the desired behavior at least once.

## Artifacts

Expected future layout:

```text
plan/
runs/          # gitignored
analysis/
report.md
```

---

## 2026-09-16 개념 대조 보강 — 착시 analogue와 다중안정

현재 R0.2 fixture의 stable wrong와 feedback 후 수정은 개발 검증이다. EXP-03 전체가 완료됐다는 뜻이 아니다. `retention/reload` 재오답을 '의도된 성공'으로 해석하지 않는다. memory 직접 실행/reload 및 pre/post 대조는 EXP-09에서 수행한다.

다중안정을 나눈다. (a) 같은 입력/설정에서 초기 상태에 따라 다른 안정점: 기존 `test_same_input_can_have_two_stable_states_in_explicit_unit_fixture`가 있다. (b) **한 지속 trajectory 안에서** 같은 입력의 지배 후보가 전환: R0.5a 기반 후의 별도 질문이다. (a)만으로 (b)를 구현했다고 하지 않는다.

후속 조작은 reset/carry/감쇠·적응·명시적 seeded noise를 분리한다. dwell time, 전환 횟수, basin dependence, 최초 readout, external error, 수정비용을 측정한다. 상태 전환을 특정 tick에 강제하지 않는다. 주입한 noise/적응을 자연 발생 원인으로 기록하지 않는다.

EXP-05의 low-A/high-A 고정 표현에서 같은 입력 모호성·prior 대조를 적용한다. 이는 illusion-like와 bad-intuition-like의 공통 계산 형식 비교이며 생물학적 착시 전체의 설명은 아니다. 원문 S05 §10·11, S06 §10·19·38에 대응한다.
