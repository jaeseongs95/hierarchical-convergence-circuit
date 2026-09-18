"""One existing topology, twelve existing observations, one binary native switch."""
from copy import deepcopy
from .contracts import BASE_COMMIT, ORDERS, VARIANTS, SCOPE, ARM, SCHEDULER


def cases(parent_plan):
    from r043_input_order_control.spec import cases as inherited_cases
    return inherited_cases(parent_plan)


def conditions(parent):
    return dict(protocol='exp25-r044-reuse-contribution-v1', basis_commit=BASE_COMMIT,
        budget=deepcopy(parent['conditions']['budget']),
        selection_limits=deepcopy(parent['conditions']['selection_limits']),
        scope=SCOPE, arm=ARM, scheduler=SCHEDULER,
        use_circuits=[True,False], id_variants=list(VARIANTS), branch_orders=list(ORDERS),
        native_trial_count=24, base_topology_count=1, reuse_pairs=12,
        parent_regression_trial_count=6,
        intervention='AdaptiveSession.use_circuits at construction; full circuit-assisted branch',
        frozen_inputs='observation_config_memory_selector_budget_equal_within_pair',
        judgment_prior='route_only; learned pool routing retained only when circuits enabled',
        effect_scope='retrieval_binding_pool_macro_use_total_effect; not_macro_apply_only',
        scheduling='unchanged_input_order; do_not_align_natural_routes_or_readouts',
        inverse_ID_mapping='evaluation_only; original_and_inverse_IDs_preserved',
        memory_policy='same_trained_memory_document; no_zeroing_or_active_flag_edit',
        reservation_policy='inherited_switch_dependent_conservative_bound; actual_and_reserved_reported',
        primary_predictions=dict(
            H_expansion='enabled_expansions_lt_disabled_given_reuse_exposure_and_no_budget_failure',
            H_kernel='enabled_native_ticks_lt_disabled_given_reuse_exposure_and_no_budget_failure',
            H_outcome='same_value_and_acceptance_given_reuse_exposure_and_no_budget_failure'),
        secondary_predictions='within_same_gate_and_order_ID_relabel_invariance',
        counterbalance='variant_order_rotates_by_order; gate_order_alternates_by_pair',
        efficacy_not_audit_requirement=True, circuit_exposure_not_required_for_valid_trial=True,
        no_new_training=True, no_online_feedback=True, automatic_retry=False,
        no_host_correction=True, external_llm=False, native_sources_modified=False,
        measured_cost_units='separate_native_counts_scheduler_selector_wall_seconds',
        unmeasured_costs='energy_peak_memory_minimal_DAG_isomorphism:null',
        population_note='one_topology_12_paired_interventions_not_24_independent_tasks',
        scope_not_claimed='learning_gain_compression_generality_retention_or_hierarchy')


def trials():
    result=[]
    for oi,order in enumerate(ORDERS):
        variants=VARIANTS if oi%2==0 else tuple(reversed(VARIANTS))
        for vi,variant in enumerate(variants):
            pair=2*oi+vi
            gates=(True,False) if pair%2==0 else (False,True)
            for enabled in gates:
                result.append(dict(id=f't{len(result):04d}',case=variant+'__order_'+order,
                    scope=SCOPE,arm=ARM,scheduler=SCHEDULER,use_circuits=enabled))
    return result
