"""Input construction only. Does not inspect trial outcomes or mutate learned memory."""
from copy import deepcopy
from .contracts import BASE_COMMIT, FAMILIES, VARIANTS, SCORE


def cases():
    result, worlds = [], {}
    for family in FAMILIES:
        if family == 'no_match_len1':
            edges = [dict(id='e0', source='v0', target='v2', score=SCORE)]
        else:
            edges = [dict(id='e0', source='v0', target='v1', score=SCORE),
                     dict(id='e1', source='v1', target='v2',
                          score=-SCORE if family == 'conflict_len2' else SCORE)]
        for variant in VARIANTS:
            mapping = {e['id']: (e['id'] if variant == 'identity' else
                       {'e0': 'alias_Z9', 'e1': 'alias_A1'}[e['id']]) for e in edges}
            obs = dict(episode_id='exp26-fixed-path', revision=0, start='v0', goal='v2',
                       edges=[dict(e, id=mapping[e['id']]) for e in edges])
            name = family + '__' + variant
            result.append(dict(name=name, family=family, cohort=family, id_variant=variant,
                observation=obs, manipulation=dict(edge_map=mapping,
                    boundary='before_native_begin', input_array_order_unchanged=True)))
            # Truth is an evaluator-only declaration. The worker receives only obs/config/memory/budget/gate.
            worlds[name] = {'declared': {e['id']: e['score'] > 0 for e in obs['edges']}}
    return result, worlds


def trials():
    rows = []
    for fi, family in enumerate(FAMILIES):
        variants = VARIANTS if fi % 2 == 0 else tuple(reversed(VARIANTS))
        for vi, variant in enumerate(variants):
            gates = (True, False) if (2 * fi + vi) % 2 == 0 else (False, True)
            for enabled in gates:
                rows.append(dict(id=f't{len(rows):04d}', case=family + '__' + variant,
                    scope='route_only', arm='online_support', scheduler='input_order', use_circuits=enabled))
    return rows


def conditions(parent):
    return dict(protocol='exp26-r045-direct-support-v1', basis_commit=BASE_COMMIT,
        budget=deepcopy(parent['conditions']['budget']),
        selection_limits=deepcopy(parent['conditions']['selection_limits']),
        scope='route_only', arm='online_support', scheduler='input_order',
        families=list(FAMILIES), id_variants=list(VARIANTS), use_circuits=[True, False],
        score_magnitude=SCORE, native_trial_count=12, gate_pairs=6,
        primary_gate_pairs=2, ID_controls=6, topology_count=2,
        counterbalance='variant_order_rotates_by_family; gate_order_alternates_by_pair',
        input_interventions='fresh_edge_IDs_only; conflict_changes_second_score_only; len1_is_separate_topology_control',
        gate_intervention='unchanged_native_constructor_use_circuits_total_branch_gate',
        memory_policy='same_frozen_EXP25_memory; no_pruning_no_retraining_no_active_flag_edits',
        route_policy='single_topological_path_by_input_design; no_host_route_alignment',
        no_new_training=True, no_online_feedback=True, automatic_retry=False, no_host_correction=True,
        native_sources_modified=False, external_llm=False,
        source_question='EXP25 macro was not on final adopted support path; test direct substitution',
        primary_predictions={
            'H_direct': 'supported_len2_ON_direct_use_on_positive_adopted_route',
            'H_expansion': 'ON_expansions_lt_OFF_given_direct_exposure_and_uncensored_pair',
            'H_kernel': 'ON_native_ticks_lt_OFF_given_direct_exposure_and_uncensored_pair',
            'H_decision_same': 'decision_program_drive_and_tick_state_sequence_equal_given_direct_exposure_and_uncensored_pair',
            'H_outcome': 'value_acceptance_preserved_in_uncensored_supported_len2_pair'},
        negative_predictions={
            'H_no_match': 'len1_ON_has_no_matched_candidate_pool_or_macro',
            'H_no_match_ticks': 'len1_ON_OFF_native_ticks_equal_not_total_cost_equal',
            'H_conflict_reject': 'conflict_len2_matched_pool_candidates_observed_mismatched_ineligible_and_no_macro',
            'H_conflict_no_false_positive': 'neither_conflict_arm_adopts_True; abstention_reported_separately'},
        ID_prediction='same_gate_same_family_canonical_readouts_decision_signatures_and_measured_counts_equal',
        decision_signature_scope='recorded_program_drives_top_down_and_all_tick_states; event_identifiers_excluded',
        comparison_scope='within_family_gate_pairs; no_len1_vs_len2_pure_matching_or_D_effect_claim',
        reservation_policy='inherited_conservative_switch_dependent_bound; reservations_not_actual_ticks',
        validity_independent_of_predictions=True, missing_direct_exposure_is_result=True,
        unmeasured='energy_peak_memory_minimal_goal_DAG_isomorphism:null',
        scope_not_claimed='learning_gain_relearning_dynamic_reexpansion_optimality_full_HCC_cycle')
