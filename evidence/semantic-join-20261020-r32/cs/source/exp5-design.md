# EXP-05 — Cross-Abstraction Primitive

## Status

`draft`

## Research question

Can one computational convergence primitive solve tasks at low, middle, and high abstraction levels when only the representations and connectivity change?

## Working prediction

A genuinely reusable primitive should retain its core state-transition rules across levels without requiring a different algorithm for each level.

## Required controls

- matched task information
- frozen success criteria
- deterministic seeds where applicable
- repeated trials
- explicit baseline
- ablation of the mechanism under test

## Primary measures

- task accuracy
- convergence dynamics
- parameter/mechanism reuse
- required level-specific additions
- failure modes

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

## 2026-09-16 개념 대조 보강 — A adaptation과 구별

R0.2에는 고정 A0 feature/A1 relation의 공통 `tick`과 top-down link가 이미 있다. 다음 두 질문을 분리한다.

1. **동일 primitive 재사용:** low-A noisy pattern completion, mid-A object/concept association, high-A hypothesis/rule 경쟁을 같은 갱신식으로 계산하는가? 표현·입출력 어댑터의 수작업 정보와 비용을 기록한다. 같은 toy task에 label만 바꿔 세 수준으로 세지 않는다.
2. **cross-A 승격·재귀:** 아래 수준의 수렴 결과를 위 수준의 node로 올릴 때 원래 근거·revision·불확실성·역변환을 보존하는가? 상위 맥락 변화가 하위 후보를 바꾸고, 하위 mismatch가 상위를 수정하는가?

R0.6의 A adaptation은 '표현 수준을 선택/이동하는가'라는 별도 조작이다. 고정된 두 수준 비교는 일반 A 자동화 전에 할 수 있다. bottom-up-only/top-down-on, 공통 kernel/수준별 kernel 대조에서 같은 자원·제공 정보를 통제한다. self-feedback을 새로운 독립 증거로 세지 않는다.

기준: low/high 과제에서 오류의 상위 형식은 비교하되 실제 인간 시각·후각 재현으로 기록하지 않는다. 외부 encoder/LLM은 후보·표현 기여를 분리할 수 있을 때 이후 추가한다. 원문 S05 §7·13, S06 §28·29·40에 대응한다.
