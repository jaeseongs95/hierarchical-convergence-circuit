"""EXP-17의 결과를 보기 전 고정할 비교 범위. 결과 불변성은 통과 조건이 아니다."""
from __future__ import annotations
from copy import deepcopy
from itertools import product

BASE_COMMIT = '28b1dea8a309df62bd89ac36e340cd904726a45a'
POLICIES = ('native_saved', 'native_rebuild', 'support_first')


def variants() -> list[dict]:
    return [dict(id='i'+''.join(map(str,bits)), node_alias=bool(bits[0]),
                 edge_alias=bool(bits[1]), edge_reverse=bool(bits[2]))
            for bits in product((0,1), repeat=3)]


def conditions() -> dict:
    return dict(protocol='exp17-r036-input-representation-v1', basis_commit=BASE_COMMIT,
        variants=variants(), scopes=['legacy','route_only'], policies=list(POLICIES),
        max_initial_advances=64,
        continuation_limits=dict(max_extra_advances=8,max_extra_kernel_ticks=2048,max_measurements=0),
        selection_limits=dict(max_ranked_paths=64,max_path_checks=64,max_edge_checks=256,max_proof_nodes=128),
        continuation_policy='expand_only', continuation_stops_on_native_support=True,
        native_graph_executed_from_each_input=True, transformation_boundary='before_native_begin',
        state_or_completed_paths_transported=False, episode_id_changed=False,
        memory_frozen=True, memory_reused_from_exp15=True, new_training=False,
        no_measurements=True, no_prior_switch_within_trial=True,
        selectors_do_not_control_continuation=True, policy_learning=False,
        automatic_retry=False, correction_of_model_output=False,
        invariance_required_for_audit=False, external_correctness_required_for_audit=False,
        comparison_unit='base_case_scope; representations and candidate states are paired, not independent problems')


def public_cases(source_plan: dict) -> list[dict]:
    return [dict(name=c['name'],family=c['family'],observation=deepcopy(c['observation']))
            for c in source_plan['conditions']['cases']]


def trials(cases: list[dict]) -> list[dict]:
    out=[]
    for case in cases:
        for scope in ('legacy','route_only'):
            for variant in variants():
                out.append(dict(id=f't{len(out):04d}',case=case['name'],scope=scope,variant=deepcopy(variant)))
    return out
