"""공개 topology와 공통 수렴 pool만 사용하는 결정적 D-expansion policy."""
from __future__ import annotations
from typing import Protocol
from .model import ExpansionBudget, MismatchSignal, ExpansionLimit
from .workspace import AdaptiveWorkspace, ExpansionCandidate
from .activation import CircuitActivationPool
from .codec import plain


class ExpansionPolicy(Protocol):
    def propose(self, workspace: AdaptiveWorkspace, mismatch: MismatchSignal,
                budget: ExpansionBudget) -> list[ExpansionCandidate]:
        ...


class DeterministicExpansionPolicy:
    def __init__(self, config, memory, *, use_circuits=True, top_down=True):
        self.config = config
        self.use_circuits = use_circuits
        self.pool = CircuitActivationPool(config, memory, top_down=top_down)

    def propose(self, workspace, mismatch, budget):
        if budget.remaining_expansions <= 0:
            raise ExpansionLimit('D expansion budget exhausted')
        prefix = workspace.frontier[0]
        primitive_slots = workspace.outgoing(prefix)
        workspace.cost.primitive_candidates += len(primitive_slots)
        activations = self.pool.activate_candidates(workspace, budget) if self.use_circuits and primitive_slots else ()
        circuits = [ExpansionCandidate(a.binding.edge_order, 'circuit', a.activation, a.mismatch,
                                       a.circuit_id, a.binding, a.prior, a.circuit_version)
                    for a in activations if a.eligible]
        # 활성도를 우선하고, 동률일 때만 긴 부분구조와 결정적 순서를 우선한다.
        circuits.sort(key=lambda c: (-c.activation, -len(c.edges), c.edges, c.circuit_id))
        primitive = [ExpansionCandidate((i,)) for i in primitive_slots]
        candidates = circuits + primitive
        reason = ('circuit_candidate' if circuits else
                  'circuit_mismatch' if activations else 'no_applicable_circuit')
        workspace.trace.emit('r02_proposals', dict(decision_id=workspace.decision_id, prefix=plain(prefix),
            mismatch=plain(mismatch), primitive_slots=primitive_slots, candidates=plain(candidates),
            reason=reason, circuits_enabled=self.use_circuits))
        return candidates
