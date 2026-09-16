# Minimal Computational Architecture

## Purpose

Define the smallest implementable system that can test the core `Graph ↔ Circuit` hypothesis without claiming biological realism.

## Required components

### 1. Representation layer
Stores typed candidate states and their abstraction level `A`.

### 2. Binding layer
Maintains identity and parent/relation continuity across state transitions.

### 3. Competition layer
Assigns activation, inhibition, and recurrent updates among competing candidates.

### 4. Convergence detector
Determines whether a stable state has been reached and records margin/stability.

### 5. Reality/validation interface
Evaluates whether convergence is adequate under an externally defined criterion.

### 6. Graph expansion controller
On mismatch or insufficient convergence, allows new candidates/relations, deeper dependency structure, or method changes.

### 7. Circuit compiler/cache
Records repeatedly validated subgraphs as reusable structures and tracks reuse strength.

### 8. Revision mechanism
Weakens, invalidates, or reopens a compiled circuit when sustained external error is observed.

## Explicit non-goals for the first prototype

- biological neuron simulation,
- large language generation,
- general intelligence,
- hardware acceleration,
- claiming that the internal structures correspond to actual human neural assemblies.
