"""기존 native proof 재구성만 호출한다. 새로운 kernel 실행/학습/관측은 없다."""
from __future__ import annotations
from copy import deepcopy
from dataclasses import asdict
import json
from .contracts import validate


def project(candidate: dict) -> dict:
    from hcr.selection import project_candidate
    v = project_candidate(candidate)
    result = {k: deepcopy(v[k]) for k in ('observation', 'raw_value', 'state',
        'completed_paths', 'graph_complete', 'original_proof', 'min_abs_score')}
    result['schema'] = 'hcr-frozen-proof-view-r035-v1'
    validate(result)
    return result


def rebuild(view: dict) -> tuple[dict, int]:
    from hcr.model import EdgeObservation, Observation, Program, Cost
    from hcr.binding import Binding
    from hcr.proof import reconstruct
    validate(view)
    o = view['observation']
    obs = Observation(o['episode_id'], o['revision'], o['start'], o['goal'],
                      tuple(EdgeObservation(**e) for e in o['edges']))
    # reconstruct는 groups/links를 읽지 않고 paths/binding/state만 읽는다.
    # 이 Program은 proof 복원용 투영이며 실행 가능한 새 network를 주장하지 않는다.
    program = Program((), (), tuple(tuple(p) for p in view['completed_paths']), len(obs.edges))
    binding = Binding(obs.digest, obs.revision, tuple(range(len(obs.edges))))
    cost = Cost()
    p = reconstruct(obs, program, binding, dict(view['state']), view['raw_value'], cost)
    return json.loads(json.dumps(asdict(p), ensure_ascii=False, allow_nan=False)), cost.proof_nodes_reconstructed
