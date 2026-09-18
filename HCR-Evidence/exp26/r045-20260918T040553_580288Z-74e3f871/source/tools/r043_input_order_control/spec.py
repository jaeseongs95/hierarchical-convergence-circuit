"""1 topology × ID 배치 2 × 배열 순열 6 × input_order 1. 결과에 따른 조건 선별 없음."""
from copy import deepcopy
from .contracts import BASE_COMMIT, SCHEDULERS, VARIANTS, ORDERS, SCOPE, ARM, digest
from . import transform


def conditions(parent_plan: dict) -> dict:
    return dict(protocol='exp24-r043-input-order-control-v1', basis_commit=BASE_COMMIT,
        budget=deepcopy(parent_plan['conditions']['budget']),
        selection_limits=deepcopy(parent_plan['conditions']['selection_limits']),
        scope=SCOPE, arm=ARM, id_variants=list(VARIANTS), schedulers=list(SCHEDULERS),
        branch_orders=list(ORDERS), native_trial_count=12, base_topology_count=1,
        parent_regression_trial_count=6, input_boundary='before_native_begin',
        intervention='edge_ID_bijection_only; S_D_ID_rank_exchange; M_unchanged',
        edge_array_slots_fixed_within_order=True, edge_ID_vocabulary_preserved=True,
        node_IDs_and_episode_and_revision_fixed=True, relation_and_score_fixed=True,
        world_truth_transport='same_bijection_on_evaluation_keys_only',
        memory_and_config='byte_semantic_identity; no_current_edge_ID_reference_permitted',
        inherited_runtime='r041_scheduler_direction.runtime.ScheduledTimingTrial',
        inherited_auditor='r041_scheduler_direction.trial_audit.audit_trial',
        scheduler_or_kernel_modified=False, case_map_or_worlds_passed_to_runtime=False,
        automatic_retry=False, online_ID_correction=False, external_llm=False,
        invariance_required_for_audit=False,
        accuracy_required_for_audit=False, canonical_trajectory_equality_required_for_audit=False,
        counterbalance='alternate_variant_order_by_permutation_index',
        comparison_unit='one_topology; six_ID_pairs_not_12_independent_problems',
        tick_cost_scope='native_kernel_only; scheduling_selection_and_wall_time_separate',
        decision_rule='frontier_head_slot; no_ID_ranking; selected_ID_logging_reads_retained',
        primary_prediction='within_order_equal_native_ticks_and_measured_readout_trajectory',
        comparison_across_orders='descriptive_only; array_permutation_invariance_not_predicted',
        final_support_signature_scope='value_depth_assumptions; not_proof_DAG_isomorphism',
        prior_experiment='EXP23_R042', native_trials_added=12, previous_trials_recounted_as_new=0)


def cases(parent_plan: dict) -> tuple[list[dict], dict]:
    result, evaluations = [], {}
    byname = {case['name']: case for case in parent_plan['cases']}
    for order in ORDERS:
        original = byname['order_' + order]
        for variant in VARIANTS:
            name = variant + '__' + original['name']
            row = dict(name=name, family='edge_id_role_isolation', cohort='paired_ID_relabel',
                parent_case=original['name'], id_variant=variant,
                observation=transform.observation(original['observation'], variant),
                manipulation=dict(branch_order=order, edge_map=transform.edge_map(variant),
                    source_observation_sha256=digest(original['observation']),
                    boundary='before_native_begin'))
            result.append(row)
            evaluations[name] = transform.worlds(parent_plan['evaluation_worlds'][original['name']], variant)
    return result, evaluations


def trials() -> list[dict]:
    result = []
    cells = [(variant, scheduler) for variant in VARIANTS for scheduler in SCHEDULERS]
    for index, order in enumerate(ORDERS):
        shift = index % len(cells)
        for variant, scheduler in cells[shift:] + cells[:shift]:
            result.append(dict(id=f't{len(result):04d}', case=variant+'__order_'+order,
                               scope=SCOPE, arm=ARM, scheduler=scheduler))
    return result
