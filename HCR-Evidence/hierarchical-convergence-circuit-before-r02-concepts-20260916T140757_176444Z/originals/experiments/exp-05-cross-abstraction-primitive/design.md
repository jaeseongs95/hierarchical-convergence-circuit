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
