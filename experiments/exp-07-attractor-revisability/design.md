# EXP-07 — Attractor Strength vs Revisability

## Status

`draft`

## Research question

How does increasing attractor strength change familiar speed/accuracy versus shifted-data correction and graph expansion?

## Working prediction

Stronger attractors should improve familiar execution up to a point while increasing correction cost under contradiction or distribution shift.

## Required controls

- matched task information
- frozen success criteria
- deterministic seeds where applicable
- repeated trials
- explicit baseline
- ablation of the mechanism under test

## Primary measures

- familiar latency
- familiar accuracy
- shifted-data error
- correction time
- graph-expansion probability

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
