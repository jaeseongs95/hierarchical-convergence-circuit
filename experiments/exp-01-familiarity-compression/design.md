# EXP-01 — Familiarity Compression

## Status

`draft`

## Research question

Does repeated successful execution reduce effective computation while preserving the frozen accuracy target?

## Working prediction

Repeated validated exposure should reduce search/expansion cost and increase circuit reuse without unacceptable accuracy loss.

## Required controls

- matched task information
- frozen success criteria
- deterministic seeds where applicable
- repeated trials
- explicit baseline
- ablation of the mechanism under test

## Primary measures

- active node count
- event count
- latency
- effective D
- accuracy
- wrong-attractor rate

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
