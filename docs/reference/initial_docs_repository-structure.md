# Repository Structure

## `theory/`
Human-readable hypothesis documents. `theory/source/` stores frozen historical source snapshots.

## `formalism/`
Definitions, notation, equations, state-transition rules, and invariants. Formalism must not silently introduce mechanisms absent from the theory.

## `evidence/`
Claim registry, evidence summaries, known limitations, and mapping to external experiment repositories.

## `experiments/`
One directory per experiment program. Each experiment begins with a frozen `design.md` before implementation or execution.

## `simulations/`
Exploratory simulations. Results here are not automatically evidence until promoted through a controlled experiment.

## `architecture/`
Software, cognitive, and possible neuromorphic architecture descriptions. Keep conceptual architecture separate from implementation details.

## `src/`
Stabilized reusable implementation. Exploratory one-off code should begin under the relevant simulation/experiment directory.

## `tests/`
Unit, invariant, reproducibility, and regression tests for stabilized code.

## `related-work/`
Literature map and explicit similarity/difference analysis. Do not use it as a dumping ground for citations without relevance mapping.

## `papers/`
Manuscript workspace. Claims in papers should be traceable to `evidence/claims.yaml`.
