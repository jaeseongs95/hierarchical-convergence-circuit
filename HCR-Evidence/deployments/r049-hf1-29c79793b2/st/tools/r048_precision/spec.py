"""Frozen EXP29 design. No solver/model output is used to choose conditions."""
from copy import deepcopy

BASE_COMMIT = 'b10f571eb02e296b2ccb3f16eaf727da7d0e4d45'
PARENT_RUN = 'HCR-Evidence/exp28/r047-20260918T134449_415062Z-82c4ceae'
PARENT_BUNDLE_GIT_BLOB = 'da376a64b5858382be0d3b82fb5957e7697e12fb'
# Chosen before any EXP29 numerical execution. All levels remain in the result.
LEVELS = (0.02, 0.10, 0.25, 0.50, 0.75, 0.92, 1.00)
VARIANTS = ('identity', 'fresh_ids')
ARMS = ('cold', 'carry_edge', 'carry_prefix', 'carry_both', 'fixed_edge', 'fixed_prefix', 'fixed_both')
CHECKPOINTS = (1, 4, 8, 16, 24)
CONFIG = dict(damping=0.45, evidence_gain=4.0, inhibition=0.2, learning_rate=0.25,
    margin_threshold=0.3, max_circuits=16, max_edges=8, max_groups=32,
    max_observation_requests=2, max_path_length=4, max_paths=4, max_search=2048,
    max_ticks=160, min_valid_episodes=3, patience=4, prior_gain=2.0, relation_gain=2.0,
    residual_tolerance=1e-6, self_excitation=0.25, temperature=1.0,
    top_down_gain=0.35, weakening=0.2)
NATIVE_BLOBS = {
    'src/hcr/__init__.py': 'ea6ccdd983eb195aaefb8898057f4fb2493a95f1',
    'src/hcr/model.py': '89e90e7f32e8cf388bbb0f7c7213b4261dc606b4',
    'src/hcr/binding.py': '44aa43f2fd4be7aa3af0b9183f03e1fe5b748d37',
    'src/hcr/codec.py': '44eac9a84681b7ba919fa3cf737ab0dbff8477e1',
    'src/hcr/identity.py': '0214cfe5bf7a5c2d41ca5e353e3f0d880fee374b',
    'src/hcr/workspace.py': '52bc9338f43078bc11835491d5baf80d16195809',
    'src/hcr/dynamics.py': '53de614846489a531f4a8d463fc17eabe1e5a6ca',
    'src/hcr/proof.py': '119c35031a97d57bc8e2c874332e8b9e1ecf6b7a',
}
# Unchanged EXP28 producer and its independently implemented evaluator are inherited.
INHERITED_HASHES = {
 'tools/r047_state_ablation/runtime.py': 'ce4a429f2e63955db29cb0c48e4f4d7359bfad06ca9fab06137d9cc974d781e2',
 'tools/r047_state_ablation/audit.py': '8596d47b05cd2da0a1930bb61953ea13bcdc82699a0a7558848ec40244d404ec',
 'tools/r047_state_ablation/spec.py': '674c79da92403911d567189c2d4bd9d0270e9ea688cd5ab976b907cfe184b7db',
 'tools/r047_state_ablation/storage.py': 'a939291f842813ad8e5e8756f2ff6b7ba6ebe61aa7ef95e2fbbaf564fbed0169',
}

def body():
    sources, cases, worlds, trials = {}, [], {}, []
    for li, level in enumerate(LEVELS):
        for vi, variant in enumerate(VARIANTS):
            key = f's{li:02d}__{variant}'
            ids = ['e0','e1','e2'] if variant == 'identity' else ['alias_Z9','alias_A1','alias_M4']
            def observation(n, scores, revision):
                vertices = ['u','v','w','z']
                return dict(episode_id='exp27-sequential',revision=revision,start='u',goal=vertices[n],
                    edges=[dict(id=ids[i],source=vertices[i],target=vertices[i+1],score=scores[i]) for i in range(n)])
            a = observation(2,[level,level],0)
            b = observation(3,[level,level,0.92],1)
            sources[key] = dict(id=key,strength=level,variant=variant,observation=a)
            cases.append(dict(id=key,source=key,strength=level,variant=variant,observation=b))
            # Fixed world independently specified: all three edges are open at every level.
            # This is a strength/noise-free observation model, not truth learned from a sign test.
            worlds[key] = {eid: True for eid in ids}
            offset = (2*li+vi) % len(ARMS)
            for arm in ARMS[offset:]+ARMS[:offset]:
                trials.append(dict(id=f't{len(trials):04d}',case=key,source=key,arm=arm))
    return dict(design=design(),sources=sources,cases=cases,worlds=worlds,trials=trials,kernel_config=deepcopy(CONFIG))

def design():
    return dict(schema='hcr-exp29-design-v1',basis_commit=BASE_COMMIT,levels=list(LEVELS),variants=list(VARIANTS),
        arms=list(ARMS),source_queries=14,followups=98,shared_A=True,independent_random_replicates=0,
        manipulation='shared_A_support_strength_changes_across_blocks; shared_A_B_edges_identical_within_block',
        unchanged='topology_binding_masks_kernel_config_termination_rules_fixed_value_0.99',
        added_B_edge_score=0.92,fixed_initial_value=0.99,checkpoint_ticks=list(CHECKPOINTS),
        checkpoints='read_only_from_executed_prefix; no_extra_ticks_or_padding_after_native_stop',
        source_gate='unchanged_R047; no_adopted_positive_A_means_reject_and_cold_fallback',
        eligibility='A_correct_positive_adoption_AND_both_B_correct_adoption_AND_both_gates_valid_AND_uncensored',
        source_ineligible_policy='all_7_B_queries_still_run_once; no_filtering_no_extra_A_retry',
        primary_estimand='ticks_actual_minus_fixed_within_same_strength_variant_mask',
        secondary_estimands=['ticks_vs_cold','checkpoint_group_Linf','checkpoint_goal_difference',
                            'checkpoint_residual_difference','overlap_trajectory_max_difference',
                            'raw_correctness','accepted_correctness','D_DAG','separate_cost_counters'],
        hypotheses=dict(
            H_precision_at_cell='eligible_cell: actual_ticks < fixed_ticks; equal_or_greater=falsified',
            H_outcome_at_cell='noncensored_actual_and_fixed: raw_value_and_adoption_equal; correctness_separate',
            H_ID_native='same_strength_arm: native_counts_and_numerical_trajectory_equal_after_consistent_ID_relabel',
            H_gate='A_without_positive_adoption: no_packet_and_no_initial_groups; full_rejection_preserved'),
        anchor='0.92 is an EXP28 regression/control point with known prior tick equality; not novel confirmation',
        analysis='descriptive_paired_conditions; no_p_values_or_independent_sample_claims',
        preserved_prior_failures=['EXP27_total_H_ID_failure','EXP28_6_source_specificity_failures'],
        interventions=dict(automatic_retry=False,host_correction=False,new_learning=False,proof_reuse=False),
        not_tested=['preallocated_substrate','plasticity','natural_language_context','negative_A_reuse',
                    'intra_A_heterogeneous_scores','measurement_noise','energy_efficiency','full_HCC_lifecycle'])
