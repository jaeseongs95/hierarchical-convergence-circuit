"""Independent fixed design and input checks; no producer spec/transform import."""
from itertools import permutations
from r043_input_order_control.input_audit import check_case, check_seed_reference_scope
from .storage import digest, require


def expected_conditions(parent):
    return dict(protocol='exp25-r044-reuse-contribution-v1',
        basis_commit='6b8ff8ab4c4858a3ab8f1a24e82b9033372133fc',
        budget=parent['conditions']['budget'],selection_limits=parent['conditions']['selection_limits'],
        scope='route_only',arm='online_support',scheduler='input_order',use_circuits=[True,False],
        id_variants=['identity','swap_SD'],branch_orders=[''.join(p) for p in permutations('SMD')],
        native_trial_count=24,base_topology_count=1,reuse_pairs=12,parent_regression_trial_count=6,
        intervention='AdaptiveSession.use_circuits at construction; full circuit-assisted branch',
        frozen_inputs='observation_config_memory_selector_budget_equal_within_pair',
        judgment_prior='route_only; learned pool routing retained only when circuits enabled',
        effect_scope='retrieval_binding_pool_macro_use_total_effect; not_macro_apply_only',
        scheduling='unchanged_input_order; do_not_align_natural_routes_or_readouts',
        inverse_ID_mapping='evaluation_only; original_and_inverse_IDs_preserved',
        memory_policy='same_trained_memory_document; no_zeroing_or_active_flag_edit',
        reservation_policy='inherited_switch_dependent_conservative_bound; actual_and_reserved_reported',
        primary_predictions={
            'H_expansion':'enabled_expansions_lt_disabled_given_reuse_exposure_and_no_budget_failure',
            'H_kernel':'enabled_native_ticks_lt_disabled_given_reuse_exposure_and_no_budget_failure',
            'H_outcome':'same_value_and_acceptance_given_reuse_exposure_and_no_budget_failure'},
        secondary_predictions='within_same_gate_and_order_ID_relabel_invariance',
        counterbalance='variant_order_rotates_by_order; gate_order_alternates_by_pair',
        efficacy_not_audit_requirement=True,circuit_exposure_not_required_for_valid_trial=True,
        no_new_training=True,no_online_feedback=True,automatic_retry=False,no_host_correction=True,
        external_llm=False,native_sources_modified=False,
        measured_cost_units='separate_native_counts_scheduler_selector_wall_seconds',
        unmeasured_costs='energy_peak_memory_minimal_DAG_isomorphism:null',
        population_note='one_topology_12_paired_interventions_not_24_independent_tasks',
        scope_not_claimed='learning_gain_compression_generality_retention_or_hierarchy')


def check_plan_inputs(plan,parent,seed):
    require(digest(plan['conditions'])==digest(expected_conditions(parent)),'frozen experiment conditions changed')
    for field in ('memory','config'):
        require(digest(seed[field])==plan[field+'_sha256']==parent[field+'_sha256'],'frozen '+field+' changed')
    reference_report=check_seed_reference_scope(seed)
    require(seed['memory'].get('circuits'), 'trained seed must contain circuits; no empty-memory substitution')
    orders=[''.join(p) for p in permutations('SMD')]
    originals={c['name']:c for c in parent['cases']}
    require(len(originals)==len(parent['cases'])==6 and set(originals)=={'order_'+o for o in orders},'parent cases')
    cases=plan['cases'];worlds=plan['evaluation_worlds'];byname={c['name']:c for c in cases}
    names={v+'__order_'+o for o in orders for v in ('identity','swap_SD')}
    require(len(cases)==12 and set(byname)==set(worlds)==names,'case/world population')
    reports={}
    for name,c in byname.items():
        old=originals[c['parent_case']]
        reports[name]=check_case(c,worlds[name],old,parent['evaluation_worlds'][old['name']])
    require(len(plan['trials'])==24,'requires 24 trials, not 24 independent tasks')
    expected=[]
    for oi,order in enumerate(orders):
        for vi in range(2):
            variant=('identity','swap_SD')[(vi+oi)%2]
            pair=oi*2+vi
            for gi in range(2):
                flag=((pair+gi)%2==0)
                expected.append(dict(id=f't{len(expected):04d}',case=variant+'__order_'+order,
                    scope='route_only',arm='online_support',scheduler='input_order',use_circuits=flag))
    require(digest(plan['trials'])==digest(expected),'gate pairing/counterbalance/trial fields changed')
    require(all(type(t['use_circuits']) is bool for t in plan['trials']),'gate type')
    return dict(verified=True,cases=reports,seed_reference_scope=reference_report,
        native_trials=24,reuse_pairs=12,parent_regression_trials=6,
        same_memory_retained_in_both_arms=True,inverse_mapping_is_evaluator_only=True)
