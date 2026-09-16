# Research Principles

## 1. Separate evidence levels

Use the following statuses consistently:

- `observed` — directly reported by a controlled experiment or source record.
- `partially-supported` — evidence is suggestive but scope is narrower than the claim.
- `hypothesis` — proposed mechanism not yet directly established.
- `derived-prediction` — consequence derived from one or more hypotheses.
- `unsupported` — no current evidence.
- `conflicted` — meaningful evidence points in incompatible directions.
- `falsified` — the frozen prediction failed under its declared test conditions.

## 2. Do not collapse levels of explanation

Keep distinct:

- LLM external behavior,
- internal model computation,
- abstract computational architecture,
- biological neural mechanism,
- physical hardware implementation.

A result at one level does not automatically establish another.

## 3. Falsifiability first

A hypothesis that cannot specify a failing observation should not be promoted as an experimental claim.

## 4. Freeze before running

Pre-register the important parts of an experiment locally before execution. Do not rewrite success criteria after inspecting results.

## 5. Preserve provenance

Historical theory snapshots and raw experiment evidence should be immutable once frozen. New interpretations belong in new files or new versions.

## 6. Prefer discriminating experiments

Experiments should distinguish competing explanations, not merely show that the proposed model can produce a desired behavior.

## 7. Avoid architecture inflation

Do not add mechanisms to the implementation unless they are required by a frozen research question or falsifiable prediction.
