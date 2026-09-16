# EXP-04 — Binding Continuity

## Status

`draft`

## Research question

How do opaque, short-uniform, semantic, and learned/distributed identities affect rebinding, graph completion, stabilization, and transfer?

## Working prediction

Binding quality should predict execution stability beyond nominal path depth alone.

## Required controls

- matched task information
- frozen success criteria
- deterministic seeds where applicable
- repeated trials
- explicit baseline
- ablation of the mechanism under test

## Primary measures

- parent binding accuracy
- graph completion
- convergence time
- wrong candidate activation
- transfer to new structures

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

## 2026-09-16 개념 대조 보강 — 계획 상태 유지

현재 `identity.bind_path`는 객체 문자열을 의미적으로 이해하지 않는다. 따라서 opaque/short/semantic 이름만 바꾼 결정적 실행은 우선 **재명명 불변성 대조**다. LLM에서 관측된 semantic-ID 효과를 HCR에서 반드시 재현해야 하는 정답으로 두지 않는다.

실행 계약의 binding과 학습된 matcher는 분리한다. 후자를 추가할 때만 같은 정보·후보·학습량에서 모호성/충돌을 조작하고 wrong binding, 재참조 정확도, matching cost, 회로 형성·새 구조 transfer를 측정한다. 의미가 같은 서로 다른 실행 node를 허용하는 범위와 현재 단순 경로의 injectivity 제약을 구분한다.

담당: 현재 R0.2 재명명·revision 검사는 기반; EXP-04의 인과 비교는 별도 실행. B는 A/D/M의 네 번째 축이 아니다. `tools/r02_concepts/check.py`는 근거 정의의 존재만 검사한다.
