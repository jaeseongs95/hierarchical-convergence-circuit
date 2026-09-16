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
