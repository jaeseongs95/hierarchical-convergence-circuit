"""공개 topology에서 후보 경로를 형성하고 같은 신호 커널의 회로로 전개한다.
관측 score나 숨은 passability로 경로를 선택하는 전역 정답 solver가 아니다.
"""
from .model import Config, Cost, Group, Link, Program, ContractError, ExpansionLimit
from .binding import Topology


def discover_paths(topology: Topology, config: Config, cost: Cost):
    topology.validate(config)
    results=[];checks=0
    def walk(node, visited, path):
        nonlocal checks
        if node==topology.goal:
            results.append(tuple(path))
            if len(results)>config.max_paths: raise ExpansionLimit('path budget exhausted; incomplete set not used')
            return
        for i,(a,b) in enumerate(topology.edges):
            cost.search_edge_checks+=1;checks+=1
            if checks>config.max_search: raise ExpansionLimit('search budget exhausted')
            if a!=node or b in visited: continue
            if len(path)>=config.max_path_length: raise ExpansionLimit('path length limit; not silently discarded')
            walk(b,visited|{b},path+[i])
    walk(topology.start,{topology.start},[])
    return tuple(results)


def make_program(edge_count: int, paths: tuple[tuple[int,...],...], config: Config,
                 cost: Cost | None=None) -> Program:
    groups=[Group('e:'+str(i),0) for i in range(edge_count)]
    links=[];finals=[];gain=config.relation_gain
    for pi,path in enumerate(paths):
        previous=None
        for position,edge in enumerate(path):
            key=f'p:{pi}:{position}'
            parents=['e:'+str(edge)]+([previous] if previous is not None else [])
            groups.append(Group(key,1,-gain*(len(parents)-1)))
            for parent in parents:
                links.append(Link(parent,key,gain,'support'))
                # EXP-43: predeclared structural intervention, before execution.
                if (key, parent) != ('p:0:1', 'p:0:0'):
                    links.append(Link(key,parent,config.top_down_gain,'top_down'))
            previous=key
        if previous is not None: finals.append(previous)
    # OR of route hypotheses. Same kernel as edge and prefix groups.
    groups.append(Group('goal',1,gain*(len(finals)-1)))
    for last in finals:
        links.append(Link(last,'goal',gain,'support'))
        links.append(Link('goal',last,config.top_down_gain,'top_down'))
    program=Program(tuple(groups),tuple(links),paths,edge_count);program.validate(config)
    if cost is not None:
        cost.dynamic_groups_created+=len(groups)
        cost.dynamic_links_created+=len(links)
    return program


def expand(topology: Topology, config: Config, cost: Cost, emit=None) -> Program | None:
    paths=discover_paths(topology,config,cost)
    if not paths: return None
    program=make_program(len(topology.edges),paths,config,cost)
    if emit:
        emit('graph_expanded',{'paths':[list(x) for x in paths],'groups':len(program.groups),
                             'links':len(program.links),'program_digest':program.digest})
    return program


# R0.2 dynamic dependency graph. 위 R0.1 전체경로 전개 함수는 그대로 보존한다.
from dataclasses import dataclass
from .model import Observation, AdaptiveConfig, AdaptiveCost
from .identity import NodeRef, NodeIdentity, SemanticIdentity, RoleBinding
from .codec import plain


@dataclass(frozen=True)
class AppliedCircuit:
    circuit_id: str
    circuit_version: int
    offset: int
    binding: RoleBinding
    prior: float


@dataclass(frozen=True)
class RoutePrefix:
    node: NodeRef
    path: tuple[int, ...]
    visited: tuple[str, ...]
    uses: tuple[AppliedCircuit, ...] = ()

    @property
    def end(self) -> str:
        return self.visited[-1]


@dataclass(frozen=True)
class ExpansionCandidate:
    edges: tuple[int, ...]
    source: str = 'primitive'
    activation: float = 0.0
    mismatch: float = 0.0
    circuit_id: str | None = None
    binding: RoleBinding | None = None
    prior: float = 0.0
    circuit_version: int = 0


class AdaptiveWorkspace:
    """실행 후보 graph. 실제 topology, event trace, primitive proof와 구분한다."""
    def __init__(self, obs: Observation, config: AdaptiveConfig, cost: AdaptiveCost, trace, decision_id: str):
        self.observation = obs
        self.config = config
        self.cost = cost
        self.trace = trace
        self.decision_id = decision_id
        self._next_node = 1
        first = RoutePrefix(NodeRef(NodeIdentity('node:' + obs.digest[:20] + ':0'),
                                   SemanticIdentity(obs.start), obs.revision), (), (obs.start,))
        self.frontier = [first]
        self.routes: list[RoutePrefix] = []
        self.known = {()}
        self.cost.graph_nodes_created += 1
        self.trace.emit('r02_workspace_created', dict(decision_id=decision_id, initial=plain(first)))

    @property
    def complete(self) -> bool:
        return not self.frontier

    def outgoing(self, prefix: RoutePrefix) -> tuple[int, ...]:
        self.cost.topology_edge_checks += len(self.observation.edges)
        return tuple(i for i, edge in enumerate(self.observation.edges)
                     if edge.source == prefix.end and edge.target not in prefix.visited)

    def retire(self) -> None:
        prefix = self.frontier.pop(0)
        self.cost.expansions += 1
        self.cost.frontier_retirements += 1
        self.trace.emit('r02_dead_end', dict(decision_id=self.decision_id, prefix=plain(prefix)))

    def apply(self, candidate: ExpansionCandidate) -> None:
        if not self.frontier or not candidate.edges:
            raise ContractError('expansion requires a frontier and nonempty candidate')
        obs = self.observation
        prefix = self.frontier[0]
        current = prefix.end
        visited = list(prefix.visited)
        for j, index in enumerate(candidate.edges):
            if type(index) is not int or not 0 <= index < len(obs.edges):
                raise ContractError('expansion edge slot')
            edge = obs.edges[index]
            if edge.source != current or edge.target in visited or current == obs.goal:
                raise ContractError('expansion path/binding/goal contract')
            current = edge.target
            visited.append(current)
        if len(prefix.path) + len(candidate.edges) > self.config.kernel.max_path_length:
            raise ExpansionLimit('primitive path length budget; dependency was not silently dropped')
        uses = prefix.uses
        if candidate.source == 'circuit':
            if candidate.binding is None or candidate.circuit_id != candidate.binding.pattern_id:
                raise ContractError('circuit candidate binding identity')
            candidate.binding.check(obs, len(candidate.edges))
            if candidate.binding.edge_order != candidate.edges:
                raise ContractError('circuit candidate path differs from bound pattern')
            uses += (AppliedCircuit(candidate.circuit_id, candidate.circuit_version,
                                    len(prefix.path), candidate.binding, candidate.prior),)
        elif candidate.source != 'primitive' or len(candidate.edges) != 1:
            raise ContractError('only one-edge primitive or certified circuit expansion is permitted')
        planned = [(prefix.path + candidate.edges, tuple(visited), uses)]
        # 선택 motif 내부의 다른 출구도 보존한다. macro 때문에 중간 분기를 삭제하지 않는다.
        for position, selected in enumerate(candidate.edges):
            local_vertices = prefix.visited + tuple(obs.edges[i].target for i in candidate.edges[:position])
            endpoint = local_vertices[-1]
            self.cost.topology_edge_checks += len(obs.edges)
            for i, edge in enumerate(obs.edges):
                if i == selected or edge.source != endpoint or edge.target in local_vertices:
                    continue
                path = prefix.path + candidate.edges[:position] + (i,)
                if len(path) > self.config.kernel.max_path_length:
                    raise ExpansionLimit('side dependency exceeds primitive path bound')
                planned.append((path, local_vertices + (edge.target,), prefix.uses))
        unique = []
        staged = set(self.known)
        for path, vertices, applied in planned:
            if path not in staged:
                staged.add(path)
                unique.append((path, vertices, applied))
        new_frontier_count = len(self.frontier) - 1 + sum(v[-1] != obs.goal for _, v, _ in unique)
        new_route_count = len(self.routes) + sum(v[-1] == obs.goal for _, v, _ in unique)
        if new_frontier_count > self.config.max_frontier or new_route_count > self.config.kernel.max_paths:
            raise ExpansionLimit('frontier/route budget; no partial negative answer allowed')
        additions = []
        for path, vertices, applied in unique:
            ref = NodeRef(NodeIdentity('node:' + obs.digest[:20] + ':' + str(self._next_node)),
                          SemanticIdentity(vertices[-1]), obs.revision)
            self._next_node += 1
            additions.append(RoutePrefix(ref, path, vertices, applied))
        self.frontier = [p for p in additions if p.end != obs.goal] + self.frontier[1:]
        self.routes.extend(p for p in additions if p.end == obs.goal)
        self.known = staged
        self.cost.expansions += 1
        self.cost.graph_nodes_created += len(additions)
        self.cost.graph_edges_created += len(additions)
        self.cost.circuit_reuses += int(candidate.source == 'circuit')
        self.trace.emit('r02_expansion', dict(decision_id=self.decision_id, prefix=plain(prefix),
                                            candidate=plain(candidate), added=plain(additions),
                                            complete=self.complete))


def adaptive_network(workspace: AdaptiveWorkspace, *, judgment_prior="legacy"):
    """이미 도달한 후보 경로만 신호 graph로 만든다. 미탐색 경로를 정답기로 채우지 않는다."""
    from .prior_policy import validate_scope, policy_fields
    validate_scope(judgment_prior)
    obs, config, cost = workspace.observation, workspace.config.kernel, workspace.cost
    paths = tuple(prefix.path for prefix in workspace.routes)
    program = make_program(len(obs.edges), paths, config, cost)
    drives = {'e:' + str(i): config.evidence_gain * (edge.score or 0.0)
              for i, edge in enumerate(obs.edges)}
    priors = []
    for pi, prefix in enumerate(workspace.routes):
        for use in prefix.uses:
            use.binding.check(obs, len(use.binding.edge_order))
            if prefix.path[use.offset:use.offset + len(use.binding.edge_order)] != use.binding.edge_order:
                raise ContractError('applied circuit no longer binds to its route span')
            for j in range(use.offset, use.offset + len(use.binding.edge_order)):
                key = f'p:{pi}:{j}'
                drives[key] = drives.get(key, 0.0) + (use.prior if judgment_prior == 'legacy' else 0.0)
            priors.append(use.prior if judgment_prior == 'legacy' else 0.0)
    drives['goal'] = max(priors, default=0.0)
    return program, drives, dict(routes=plain(workspace.routes), graph_complete=workspace.complete,
                                **policy_fields(judgment_prior))
