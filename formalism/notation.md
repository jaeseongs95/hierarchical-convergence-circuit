# Notation

This file is intentionally minimal until the computational prototype freezes the exact state model.

| Symbol | Working meaning |
|---|---|
| `A` | Abstraction / representation level |
| `D` | Decomposition or dependency depth |
| `M` | Modality / computational method |
| `B` | Binding continuity |
| `R_{A,t}` | representation state at abstraction level `A` and time `t` |
| `R_A*` | converged state at level `A` |
| `G` | dynamic graph / transient relational structure |
| `C` | reusable compiled circuit |
| `E` | external/reality mismatch or error signal |

Working transition:

```text
R_{A,t+1} = F_M(R_{A,t}, Context, Memory, Binding, Competition)
```

Working structural transition:

```text
Repeated valid G → C
Mismatch / novelty in C → graph expansion
```

These expressions define research targets; they are not yet a complete mathematical theory.
