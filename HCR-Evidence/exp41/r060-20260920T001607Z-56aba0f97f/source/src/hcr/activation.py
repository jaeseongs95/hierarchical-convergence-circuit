"""여러 부분회로를 후보 상태로 만들고 기존 dynamics.tick/settle로 함께 경쟁시킨다."""
from __future__ import annotations
from dataclasses import dataclass
from .model import (AdaptiveConfig, ExpansionBudget, ContractError, ExpansionLimit,
                    Group, Link, Program, Status)
from .identity import RoleBinding, bind_path
from .workspace import ExpansionCandidate
from .dynamics import settle_recorded
from .codec import plain


@dataclass(frozen=True)
class CircuitActivation:
    circuit_id: str
    binding: RoleBinding
    activation: float
    mismatch: float
    prior: float
    circuit_version: int
    eligible: bool


def instantiate_pool(matches, obs, config):
    """저장된 pattern.program의 node/link를 현재 역할에 바인딩한다."""
    k = config.kernel
    groups = [Group('e:' + str(i), 0) for i in range(len(obs.edges))]
    links = []
    drives = {'e:' + str(i): k.evidence_gain * (e.score or 0.0) for i, e in enumerate(obs.edges)}
    metadata = []
    for i, (circuit, binding) in enumerate(matches):
        binding.check(obs, circuit.pattern.length)
        uncertainty = max(1 - abs(obs.edges[s].score or 0.0) for s in binding.edge_order)
        prior = k.prior_gain * circuit.strength * circuit.balance * uncertainty
        mismatch = max(max(0.0, -(obs.edges[s].score or 0.0)) for s in binding.edge_order)
        def rename(name):
            if name.startswith('e:'):
                return 'e:' + str(binding.edge_order[int(name.split(':')[1])])
            if name == 'goal':
                return 'c:' + str(i)
            return name.replace('p:0:', 'p:' + str(i) + ':', 1)
        for group in circuit.pattern.program.groups:
            if not group.id.startswith('e:'):
                name = rename(group.id)
                groups.append(Group(name, group.level, group.bias))
                drives[name] = prior
        for link in circuit.pattern.program.links:
            links.append(Link(rename(link.source), rename(link.target), link.weight, link.kind))
        metadata.append(dict(circuit_id=circuit.id, circuit_version=circuit.version,
                             binding=plain(binding), prior=prior, mismatch=mismatch))
    groups.append(Group('goal', 1, k.relation_gain * (len(matches) - 1)))
    for i in range(len(matches)):
        key = 'c:' + str(i)
        links.extend((Link(key, 'goal', k.relation_gain, 'support'),
                      Link('goal', key, k.top_down_gain, 'top_down')))
        for j in range(len(matches)):
            if i != j:
                links.append(Link(key, 'c:' + str(j), -config.circuit_inhibition, 'support'))
    program = Program(tuple(groups), tuple(links), tuple(b.edge_order for _, b in matches), len(obs.edges))
    program.validate(k)
    return program, drives, metadata


class CircuitActivationPool:
    def __init__(self, config: AdaptiveConfig, memory, *, top_down=True):
        self.config = config
        self.memory = memory
        self.top_down = top_down

    def activate_candidates(self, workspace, budget: ExpansionBudget) -> tuple[CircuitActivation, ...]:
        prefix = workspace.frontier[0]
        obs = workspace.observation
        cost = workspace.cost
        scans = []
        inspected = []
        matches = []
        reason = None
        # 매칭 예산이 끝나면 부분 후보 목록을 승자로 사용하지 않고 primitive 확장으로 복귀한다.
        for circuit in sorted(self.memory.circuits, key=lambda c: (c.pattern.length, c.id)):
            inspected.append(circuit.id)
            cost.recall_checks += 1
            if not circuit.active or len(prefix.path) + circuit.pattern.length > self.config.kernel.max_path_length:
                continue
            todo = [(prefix.end, prefix.visited, ())]
            while todo and reason is None:
                vertex, visited, slots = todo.pop()
                if len(slots) == circuit.pattern.length:
                    binding = bind_path(obs, circuit.id, slots)
                    matches.append((circuit, binding))
                    cost.candidate_circuits += 1
                    if len(matches) > self.config.max_pool_candidates:
                        reason = 'pool_capacity'
                    continue
                if vertex == obs.goal:
                    continue
                children = []
                for i, edge in enumerate(obs.edges):
                    if len(scans) >= budget.remaining_binding_checks:
                        reason = 'binding_budget'
                        break
                    scans.append([circuit.id, list(slots), i])
                    cost.binding_checks += 1
                    cost.binding_operations += 1
                    if edge.source == vertex and edge.target not in visited:
                        children.append((edge.target, visited + (edge.target,), slots + (i,)))
                todo.extend(reversed(children))
            if reason is not None:
                break
        workspace.trace.emit('r02_binding_scan', dict(decision_id=workspace.decision_id, prefix=plain(prefix),
            inspected=inspected, scans=scans, matched=[dict(circuit_id=c.id, binding=plain(b)) for c, b in matches],
            complete=reason is None, fallback_reason=reason))
        if reason is not None or not matches:
            return ()
        try:
            program, drives, metadata = instantiate_pool(matches, obs, self.config)
        except ExpansionLimit:
            workspace.trace.emit('r02_pool_unavailable', dict(decision_id=workspace.decision_id,
                                                              reason='common_kernel_group_budget'))
            return ()
        # 후보 편성 때 만든 동적 node와 저장 회로에서 실체화한 node를 따로 센다.
        cost.dynamic_groups_created += len(obs.edges) + 1
        cost.dynamic_links_created += 2 * len(matches) + len(matches) * (len(matches) - 1)
        cost.circuit_groups_instantiated += sum(len(c.pattern.program.groups) - c.pattern.length for c, _ in matches)
        cost.pool_calls += 1
        state, convergence, network_id = settle_recorded(program, drives, self.config.kernel, cost,
            workspace.trace, workspace.decision_id, 'pool', dict(prefix=plain(prefix), candidates=metadata),
            top_down=self.top_down)
        stable = convergence.status in (Status.STABLE_DECISION, Status.STABLE_AMBIGUOUS)
        activations = tuple(CircuitActivation(c.id, binding, state['c:' + str(i)],
            metadata[i]['mismatch'], metadata[i]['prior'], c.version,
            stable and state['c:' + str(i)] >= self.config.activation_threshold
            and metadata[i]['mismatch'] <= self.config.mismatch_threshold)
            for i, (c, binding) in enumerate(matches))
        workspace.trace.emit('r02_pool_result', dict(decision_id=workspace.decision_id, network_id=network_id,
                                                    activations=plain(activations)))
        return activations
