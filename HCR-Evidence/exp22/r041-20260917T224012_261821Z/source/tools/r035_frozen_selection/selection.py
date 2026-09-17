"""세 proof 정책의 동일 상태 대조. 별도 정답·case 분류·원 후보 provenance를 받지 않는다."""
from __future__ import annotations
from copy import deepcopy
from dataclasses import asdict
from time import perf_counter
from .contracts import Limits, digest, require, validate

POLICIES = ('native_saved', 'native_rebuild', 'support_first')


def gate(view: dict, proof: dict | None) -> tuple[bool, int]:
    """R032 dependency_gate의 지지 조건. DAG의 독립 검증은 audit에서 수행한다."""
    if view['raw_value'] is None or proof is None:
        return False, 0
    edges = {e['id']: e for e in view['observation']['edges']}
    assumptions = proof['assumed_edges']; threshold = view['min_abs_score']
    flags = []
    for eid, truth in assumptions:
        require(eid in edges and type(truth) is bool, 'gate 가정 identity')
        score = edges[eid]['score']
        flags.append(score is not None and abs(score) > threshold and (score > 0) is truth)
    return bool(proof['under_assumptions_valid'] and assumptions and all(flags)
        and (view['raw_value'] is not False or view['graph_complete'])), len(assumptions)


def positive_proof(view: dict, pi: int) -> dict:
    """등록된 경로를 primitive DAG로 만든다. 새 경로를 찾는 함수가 아니다."""
    obs = view['observation']; paths = view['completed_paths']
    nodes = []; assumed = []; previous = None
    for j, slot in enumerate(paths[pi]):
        fid = f'f:{slot}:1'; rid = f'r:{pi}:{j}'; eid = obs['edges'][slot]['id']
        nodes.append(dict(id=fid, rule='assumed_open', edge_id=eid, parents=[], path_index=None))
        nodes.append(dict(id=rid, rule='start_edge' if j == 0 else 'extend_path', edge_id=None,
                          parents=[fid] if j == 0 else [previous, fid], path_index=pi))
        assumed.append([eid, True]); previous = rid
    return dict(nodes=nodes, final=previous, primitive_depth=len(paths[pi]),
        assumed_edges=sorted(assumed), under_assumptions_valid=True,
        paths=[[obs['edges'][s]['id'] for s in p] for p in paths])


def run_policy(view: dict, policy: str, limits: Limits | None = None) -> dict:
    start = perf_counter(); validate(view)
    require(policy in POLICIES, '미등록 선택 정책')
    limits = limits or Limits(); require(isinstance(limits, Limits), 'typed limits')
    require(policy == 'support_first' or limits == Limits(), '예산 ablation은 support_first 전용')
    before = digest(view); proof = None; selected = None; trace = []
    usage = dict(ranked_paths=0, path_checks=0, edge_checks=0, proof_nodes_created=0,
                 proof_nodes_reused=0, gate_assumptions_checked=0)
    applicable = view['raw_value'] is not None
    if policy == 'native_saved' or policy == 'support_first' and view['raw_value'] is not True:
        proof = deepcopy(view['original_proof']); usage['proof_nodes_reused'] = len(proof['nodes'])
        reason = 'retained_native_proof' if policy == 'native_saved' else 'nonpositive_native_passthrough'
        if policy == 'support_first': applicable = False
    elif policy == 'native_rebuild':
        from .native_bridge import rebuild
        proof, count = rebuild(view); usage['proof_nodes_created'] = count
        # 기존 함수 내부의 scan 계수는 관측하지 않는다. 0으로 가장하지 않는다.
        usage.update(ranked_paths=None, path_checks=None, edge_checks=None)
        reason = 'native_reconstructed'
    else:
        paths = view['completed_paths']; state = view['state']; edges = view['observation']['edges']
        if len(paths) > limits.max_ranked_paths:
            reason = 'ranking_budget'
        else:
            usage['ranked_paths'] = len(paths); reason = 'no_supported_existing_path'
            ordered = sorted(range(len(paths)), key=lambda i: (-state[f'p:{i}:{len(paths[i])-1}'], i))
            for pi in ordered:
                path = paths[pi]
                if usage['path_checks'] + 1 > limits.max_path_checks or usage['edge_checks'] + len(path) > limits.max_edge_checks:
                    reason = 'scan_budget'; break
                usage['path_checks'] += 1; usage['edge_checks'] += len(path)
                active = all(state[f'e:{s}'] >= .5 for s in path)
                supported = all(edges[s]['score'] is not None and edges[s]['score'] > view['min_abs_score'] for s in path)
                trace.append(dict(path_index=pi, activation_eligible=active, observation_supported=supported))
                if not (active and supported): continue
                if 2 * len(path) > limits.max_proof_nodes:
                    reason = 'proof_budget'; break
                selected = pi; proof = positive_proof(view, pi)
                usage['proof_nodes_created'] = len(proof['nodes']); reason = 'supported_existing_positive_path'; break
    accepted, checked = gate(view, proof); usage['gate_assumptions_checked'] = checked
    if selected is None and proof is not None and proof['final'] is not None and view['raw_value'] is True:
        selected = next(n['path_index'] for n in proof['nodes'] if n['id'] == proof['final'])
    require(before == digest(view), '선택기가 입력 상태를 수정했습니다.')
    return dict(schema='hcr-frozen-proof-result-r035-v1', policy=policy, input_sha256=before,
        limits=asdict(limits), applicable=applicable, proof=proof, selected_path_index=selected,
        accepted=accepted, value=view['raw_value'] if accepted else None, reason=reason,
        selection_trace=trace, usage=usage,
        gate_reason='supported_under_sign_contract' if accepted else
            'original_abstention' if view['raw_value'] is None else 'dependency_support_abstention',
        boundaries=dict(new_kernel_ticks=0, measurements=0, memory_updates=0,
            input_modified=False, raw_value_changed=False, new_routes_generated=False),
        wall_seconds=perf_counter()-start)
