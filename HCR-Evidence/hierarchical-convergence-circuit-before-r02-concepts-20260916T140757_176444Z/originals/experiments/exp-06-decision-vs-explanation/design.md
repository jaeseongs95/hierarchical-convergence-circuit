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
