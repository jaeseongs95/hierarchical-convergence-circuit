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
