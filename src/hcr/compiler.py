"""실제로 형성한 graph를 역할화한 희소 실행 구조로 저장한다. 정답 값은 저장하지 않는다."""
from .model import Config, Program, Proof, Cost, ContractError, fingerprint
from .binding import Topology
from .circuits import Circuit, Pending
from .workspace import discover_paths,make_program


def validate_structure(topology: Topology, program: Program, config: Config, cost: Cost) -> None:
    probe=Cost();paths=discover_paths(topology,config,probe)
    if program!=make_program(len(topology.edges),paths,config):raise ContractError('graph/program certificate mismatch')
    cost.compilation_items+=probe.search_edge_checks+len(program.groups)+len(program.links)


def compile_pending(item: Pending, config: Config, cost: Cost) -> Circuit:
    if len(set(item.episodes))<config.min_valid_episodes:raise ContractError('insufficient distinct verified episodes')
    validate_structure(item.topology,item.program,config,cost)
    cid='c-'+fingerprint({'topology':{'vertices':item.topology.vertices,'edges':item.topology.edges},
                         'program':item.program.digest,'config':config.signature})[:20]
    return Circuit(cid,item.topology,item.program,config.signature,0.55,
                   item.positive,item.negative,list(item.episodes),list(item.feedback_ids),list(item.proof_digests))


class SubgraphCompiler:
    """실제로 사용한 primitive proof의 연속 부분경로만 역할화한다.

    일반 arbitrary-subgraph mining은 아니다. R0.2 범위는 bounded directed
    path motifs이며 동일 episode의 중복 motif는 독립 검증 횟수로 세지 않는다.
    """
    @staticmethod
    def extract(observation, decision, config, cost):
        from .patterns import make_pattern
        if decision.value is not True or not decision.proof.under_assumptions_valid:
            return ()
        # 최종 증명의 직접 부모만 역추적한다. proof.paths 전체를 학습한 것으로 간주하지 않는다.
        nodes = {n.id: n for n in decision.proof.nodes}
        key = decision.proof.final
        reverse_edges = []
        seen = set()
        while key is not None:
            if key in seen or key not in nodes:
                raise ContractError('subgraph compiler: cyclic/missing proof parent')
            seen.add(key)
            node = nodes[key]
            if node.rule == 'start_edge' and len(node.parents) == 1:
                fact = nodes.get(node.parents[0])
                if fact is None or fact.rule != 'assumed_open':
                    raise ContractError('subgraph compiler: invalid start fact')
                reverse_edges.append(fact.edge_id)
                key = None
            elif node.rule == 'extend_path' and len(node.parents) == 2:
                fact = nodes.get(node.parents[1])
                if fact is None or fact.rule != 'assumed_open':
                    raise ContractError('subgraph compiler: invalid extension fact')
                reverse_edges.append(fact.edge_id)
                key = node.parents[0]
            else:
                raise ContractError('subgraph compiler: not a primitive positive path')
        path = tuple(reversed(reverse_edges))
        if path not in decision.proof.paths:
            raise ContractError('subgraph compiler: unused path')
        edges = {e.id: e for e in observation.edges}
        current = observation.start
        visited = {current}
        for eid in path:
            edge = edges.get(eid)
            if edge is None or edge.source != current or edge.target in visited:
                raise ContractError('subgraph compiler: current-instance binding')
            current = edge.target
            visited.add(current)
        if current != observation.goal:
            raise ContractError('subgraph compiler: incomplete proof route')
        result = []
        for length in config.pattern_lengths:
            if length <= len(path):
                pattern = make_pattern(length, config.kernel)
                # 같은 primitive kind의 경로 motif는 위치가 달라도 하나의 episode 증거다.
                cost.compilation_items += len(pattern.program.groups) + len(pattern.program.links)
                result.append(pattern)
        return tuple(result)
