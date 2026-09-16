# Hierarchical Convergence-Circuit Hypothesis

> A research program on whether perception, intuition, reasoning, and learning can emerge from a common convergence primitive repeated across abstraction levels.

**Status:** working hypothesis / active validation  
**Primary source document:** `theory/source/2026-09-16-integrated-hypothesis-ko.md`  
**Korean README:** [`README.ko.md`](README.ko.md)

## Core hypothesis

The project investigates a computational architecture in which cognition repeatedly applies a common primitive across different representation levels:

```text
Input
  ↓
Candidate activation
  ↓
Binding / dynamic routing
  ↓
Competition / inhibition / recurrence
  ↓
Convergence
  ├─ adequate → learning → reusable circuit
  └─ mismatch → graph expansion → A/D/M adaptation
```

The stronger working hypothesis is that novel problems require dynamic graph expansion, while repeatedly successful graphs can be compressed into reusable circuits. Familiar cognition may therefore behave like fast circuit execution, while novelty or error reopens the graph for further search and adaptation.

## Research boundary

This repository deliberately separates:

1. **Observed results** — effects already reported in the existing LLM experiments.
2. **Working hypotheses** — mechanisms proposed by the integrated model but not yet directly established.
3. **Derived predictions** — falsifiable consequences that future experiments should test.

The current LLM evidence does **not** by itself establish a neural mechanism or a brain-wide theory. See [`evidence/claims.yaml`](evidence/claims.yaml) for the claim-by-claim status.

## Main components

- **A — Abstraction:** representation level.
- **D — Decomposition / Dependency Depth:** dependency depth required to reach a result.
- **M — Modality / Method:** how candidates are generated, compared, corrected, and converged.
- **B — Binding Continuity:** whether identity, meaning, and relations remain stable during execution.
- **Graph ↔ Circuit:** dynamic expansion for novel problems and compression/reuse for familiar ones.
- **Misconvergence:** stable but externally wrong convergence, proposed as a common higher-level error form.

## Repository map

```text
hierarchical-convergence-circuit/
├─ theory/          # hypothesis and source documents
├─ formalism/       # notation and formal model
├─ evidence/        # claim registry and evidence boundary
├─ experiments/     # falsifiable experiment programs
├─ simulations/     # future cognitive / circuit simulations
├─ architecture/    # computational and neuromorphic architecture
├─ related-work/    # literature map; similarities and differences
├─ papers/          # manuscript workspace
├─ src/             # implementation code when stabilized
├─ tests/           # executable validation tests
├─ scripts/         # repository utilities
└─ docs/            # governance and repository documentation
```

See [`docs/repository-structure.md`](docs/repository-structure.md) for the intended role of each directory.

## Initial experiment program

| ID | Experiment | Main question |
|---|---|---|
| EXP-01 | Familiarity Compression | Does repeated successful execution reduce effective computation without losing accuracy? |
| EXP-02 | Novelty-triggered Graph Expansion | Does mismatch trigger graph expansion and A/D/M adaptation? |
| EXP-03 | Misconvergence | Can a learned prior produce stable but externally wrong convergence? |
| EXP-04 | Binding Continuity | How does identity/semantic binding affect graph stability and transfer? |
| EXP-05 | Cross-Abstraction Primitive | Can the same convergence primitive operate across different representation levels? |
| EXP-06 | Decision vs Explanation | Does post-hoc explanation reconstruct a graph different from the execution path? |
| EXP-07 | Attractor Strength vs Revisability | What trade-off exists between compression, speed, and correction ability? |

## Relationship to `thought-graph-simulator`

`thought-graph-simulator` should remain a separate experimental repository. It provides evidence about high-level reasoning graphs, path selection, depth, and binding behavior. This repository is the broader theory and experimental program that can consume those results without conflating an LLM execution study with the full cognitive hypothesis.

## Research discipline

Every substantive claim should have:

- a stable claim ID,
- an explicit status,
- supporting or conflicting evidence,
- a falsification condition,
- and the experiment(s) that can update its status.

See [`docs/research-principles.md`](docs/research-principles.md).

## Repository setup

After extracting the archive:

```bash
git init
git add .
git commit -m "chore: initialize hierarchical convergence-circuit research repository"
```

Windows PowerShell users can run `scripts/init-repo.ps1`. Linux/macOS users can run `scripts/init-repo.sh`.

## License

No open-source license has been selected yet. Until a license is explicitly added, normal copyright rules apply. Select a code/document license before inviting external reuse or contributions.
