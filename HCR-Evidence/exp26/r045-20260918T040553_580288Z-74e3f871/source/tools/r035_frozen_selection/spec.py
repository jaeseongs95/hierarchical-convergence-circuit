"""사전 고정된 EXP-16 선택 비교 계약. EXP-15 상태를 재사용하는 후향적 개입 실험이다."""
from __future__ import annotations
from copy import deepcopy
from itertools import product

BASE_COMMIT = 'a9c643954696cbe309f29691bf63e5d4fe463f91'


def conditions():
    return dict(protocol='exp16-r035-frozen-proof-v1', basis_commit=BASE_COMMIT,
        source_population='each main/expand_only baseline, lexicographically first world, all native candidates',
        policies=['native_saved', 'native_rebuild', 'support_first'],
        transformations=[dict(id='v'+''.join(str(i) for i in b), node_alias=bool(b[0]), edge_alias=bool(b[1]),
            edge_reverse=bool(b[2]), path_reverse=bool(b[3])) for b in product((0,1), repeat=4)],
        limits=dict(max_ranked_paths=64, max_path_checks=64, max_edge_checks=256, max_proof_nodes=128),
        ablations=['max_ranked_paths', 'max_path_checks', 'max_edge_checks', 'max_proof_nodes'],
        transformation_boundary='after_native_readout_not_before_graph_generation',
        reuses_exp15_states=True, new_native_expansion=False, first_failure_preserved=True,
        memory_frozen=True, same_value_only=True, accuracy_required_for_audit=False,
        autonomous_controller_included=False, hidden_truth_in_policy_input=False)


def cells(snapshot_ids):
    c = conditions(); result = []
    for sid in snapshot_ids:
        for variant in c['transformations']:
            for policy in c['policies']:
                result.append(dict(snapshot_id=sid, variant=deepcopy(variant), policy=policy,
                    group='main', limits=deepcopy(c['limits'])))
        for name in c['ablations']:
            caps = deepcopy(c['limits']); caps[name] = 0
            result.append(dict(snapshot_id=sid, variant=deepcopy(c['transformations'][0]),
                policy='support_first', group='ablation_'+name, limits=caps))
    return [dict(id=f'f{i:05d}', **r) for i,r in enumerate(result)]
