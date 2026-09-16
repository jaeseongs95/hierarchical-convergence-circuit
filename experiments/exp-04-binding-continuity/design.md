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
