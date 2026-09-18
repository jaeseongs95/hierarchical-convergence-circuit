"""분기 배열만 조작한다. eID/nodeID/episode/revision/score/world는 모두 고정한다."""
from copy import deepcopy
from dataclasses import asdict
from itertools import permutations
from .contracts import (ARMS, SCOPES, Budget, SELECTION_LIMITS, BASE_COMMIT,
    CANONICAL_CASE, CANONICAL_OBSERVATION_SHA256, digest, require, validate_public_observation)
BRANCHES = {'S': ('e0','e1'), 'M': ('e2','e3'), 'D': ('e4','e5','e6')}
ORDERS = tuple(''.join(p) for p in permutations('SMD'))


def conditions():
    return dict(protocol='exp20-r039-fixed-identity-order-v1', basis_commit=BASE_COMMIT,
        arms=list(ARMS), scopes=list(SCOPES), budget=asdict(Budget()), selection_limits=dict(SELECTION_LIMITS),
        native_trial_count=36, base_topology_count=1, order_variant_count=6,
        canonical_parent_case=CANONICAL_CASE, branch_orders=list(ORDERS),
        intervention='whole_branch_edge_array_permutation_only',
        edge_id_fixed=True, node_id_fixed=True, episode_id_fixed=True, revision_fixed=True,
        edge_relations_and_scores_fixed=True, evaluation_worlds_fixed=True,
        internal_branch_order_fixed=True, input_hash_recomputed_not_forced=True,
        same_session_identity_across_arms=True, cross_order_session_hash_identity_not_fixed=True,
        completed_path_mapping='audit_only_slots_to_unchanged_edge_ids',
        case_or_order_label_passed_to_runtime=False,
        automatic_retry=False, frozen_memory=True, observations_requested=False, prior_switch=False,
        restart=False, external_llm=False, native_kernel_modified=False,
        support_must_preserve_raw_value=True, support_is_external_truth=False,
        correctness_required_for_audit=False, opportunity_required_for_audit=False,
        improvement_required_for_audit=False, order_effect_required_for_audit=False,
        counterbalance='cyclic_arm_order_by_permutation_and_scope',
        comparison_unit='one_fixed_topology; permutations/prior/arm/world/readout are paired conditions')


def make_cases(parent_case):
    require(parent_case['name']==CANONICAL_CASE, '정해진 EXP19 l3 early 기준 입력 필요')
    original=parent_case['observation']
    require(digest(original)==CANONICAL_OBSERVATION_SHA256, '기준 observation fingerprint 불일치')
    validate_public_observation(original)
    lookup={e['id']:deepcopy(e) for e in original['edges']}
    old_index={e['id']:i for i,e in enumerate(original['edges'])}
    require(set(lookup)==set(sum((list(v) for v in BRANCHES.values()),[])), '기준 edge inventory')
    cases=[]
    for order in ORDERS:
        edge_ids=[eid for label in order for eid in BRANCHES[label]]
        obs=deepcopy(original);obs['edges']=[deepcopy(lookup[eid]) for eid in edge_ids]
        cases.append(dict(name='order_'+order, family='fixed_identity_branch_order', cohort='order_only',
            observation=obs, worlds=deepcopy(parent_case['worlds']),
            manipulation=dict(branch_order=order, edge_id_order=edge_ids,
                new_to_canonical_slot=[old_index[eid] for eid in edge_ids],
                canonical_observation_sha256=digest(original))))
    return cases


def public_cases(cases):
    return [{k:deepcopy(v) for k,v in c.items() if k!='worlds'} for c in cases]


def trials(cases):
    rows=[]
    for ci,case in enumerate(cases):
        for si,scope in enumerate(SCOPES):
            shift=(ci+si)%len(ARMS)
            for arm in ARMS[shift:]+ARMS[:shift]:
                rows.append(dict(id=f't{len(rows):04d}',case=case['name'],scope=scope,arm=arm))
    return rows
