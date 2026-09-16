# EXP-02 — Novelty-triggered Graph Expansion

## Status

`draft`

## Research question

Does novelty or mismatch trigger graph expansion and adaptation of A/D/M rather than continued reuse of an inadequate circuit?

## Working prediction

Novel inputs should produce more expansion/adaptation than matched familiar inputs when existing circuits are insufficient.

## Required controls

- matched task information
- frozen success criteria
- deterministic seeds where applicable
- repeated trials
- explicit baseline
- ablation of the mechanism under test

## Primary measures

- convergence time
- candidate count
- D change
- M-switch count
- circuit reuse ratio
- expansion trigger rate

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
