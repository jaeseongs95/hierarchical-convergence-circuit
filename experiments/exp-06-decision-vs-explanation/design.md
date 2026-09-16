# EXP-06 — Decision vs Explanation

## Status

`draft`

## Research question

Does a post-hoc explanation graph differ systematically from the actual execution path used to reach a decision?

## Working prediction

If decision generation and explanation reconstruction are separable, explanation graphs should sometimes diverge from captured execution traces.

## Required controls

- matched task information
- frozen success criteria
- deterministic seeds where applicable
- repeated trials
- explicit baseline
- ablation of the mechanism under test

## Primary measures

- execution-path / explanation-path agreement
- omitted dependencies
- fabricated dependencies
- decision latency
- explanation latency

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

## 2026-09-16 개념 대조 보강 — 이미 있는 것과 부족한 관측

R0.1 `Engine.infer`는 `decision_readout` 뒤 `explanation_reconstructed`를 기록한다. R0.2도 내부 value를 먼저 결정하고 `proof.reconstruct`를 호출하지만 결과는 하나의 `r02_decision`에 함께 기록한다. 따라서 개념이 전혀 없었던 것은 아니며, 현재 부족한 것은 **R0.2의 독립 이벤트·시간 및 비교 프로토콜**이다.

현재 capture로 가능한 것은 사용 가정의 공개 관측/당시 program 포함 관계와 proof 복원 item 수다. `tools/r02_concepts/review.py`는 이 범위만 관찰한다. 별도 readout 시각·explanation latency와 실제 원인 경로는 과거 기록에서 복원한 척하지 않는다.

R0.2.1의 새 trace schema에서 value 확정, proof reconstruction 시작/끝을 별도 기록한다. 구버전 trace를 변경하지 않고 evaluator도 schema별로 동작하게 한다. 비용 관측은 후속 실행에서만 생긴다.

**중요한 비교 기준:** 실행 signal graph와 논리 proof DAG는 같은 종류의 graph가 아니다. macro를 primitive로 풀어 노드가 많아진 것이 fabricated dependency가 아니다. 탐색했지만 채택하지 않은 가지가 설명에 없다고 omitted dependency로 세지 않는다. 누락/조작은 최종 정당화에 필요한 primitive와 실제 가용 근거를 기준으로 검사한다. 언어 설명 adapter는 별도 미래 실험이다.

판단과 설명의 차이가 반드시 관측되어야 성공인 것은 아니다. 둘이 정합적인 결과도 기록한다. 원래 draft의 working prediction은 검증 대상이며 강제할 출력 패턴이 아니다.
