"""Frozen design. Contains public inputs and a separate evaluator world, not model output."""
from __future__ import annotations
from copy import deepcopy
from .storage import digest, require

BASE_COMMIT = 'bdd24df2d783a1cea82a6050f4f793c9eb06ca0a'
PARENT_RUN = 'HCR-Evidence/exp27/r046-20260918T052020_778586Z-c3aecba2'
PARENT_PLAN_BYTES = 'ad7d7e416b0f185f9d8199ba0d054201db62a8b79f3c8f7d78b6287726ae65f9'
PARENT_MANIFEST_BYTES = 'e488e38589725234db480065b4342666348c624062a4c6558e6cf64c42937270'
VARIANTS = ('identity', 'fresh_ids')
SCENARIOS = ('extend', 'different_subject', 'premise_changed')
ARMS = ('cold', 'carry_edge', 'carry_prefix', 'carry_both',
        'fixed_edge', 'fixed_prefix', 'fixed_both')
FIXED_VALUE = 0.99  # Frozen before EXP-28 tests/runs; not optimized against EXP-28 outcomes.
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

def observations():
    sources = {}; cases = []; worlds = {}
    for variant in VARIANTS:
        labels = ['e0', 'e1', 'e2'] if variant == 'identity' else ['alias_Z9', 'alias_A1', 'alias_M4']
        def obs(vertices, scores, revision):
            return dict(episode_id='exp27-sequential', revision=revision,
                start=vertices[0], goal=vertices[-1], edges=[
                dict(id=labels[i], source=vertices[i], target=vertices[i+1], score=s)
                for i, s in enumerate(scores)])
        sources[variant] = obs(['u', 'v', 'w'], [0.92, 0.92], 0)
        for scenario in SCENARIOS:
            vertices = ['p', 'q', 'r', 's'] if scenario == 'different_subject' else ['u', 'v', 'w', 'z']
            ob = obs(vertices, [0.92, -0.92 if scenario == 'premise_changed' else 0.92, 0.92], 1)
            key = scenario + '__' + variant
            cases.append(dict(id=key, scenario=scenario, variant=variant, observation=ob))
            # Experimental world is deliberately withheld from the runtime.
            worlds[key] = {e['id']: e['score'] > 0 for e in ob['edges']}
    return sources, cases, worlds

def treatment(arm: str) -> tuple[str, str]:
    require(arm in ARMS, 'unknown treatment')
    return ('none', 'none') if arm == 'cold' else tuple(arm.split('_'))

def trials():
    out = []
    for si, scenario in enumerate(SCENARIOS):
        for vi, variant in enumerate(VARIANTS):
            k = (2 * si + vi) % len(ARMS)
            for arm in ARMS[k:] + ARMS[:k]:
                out.append(dict(id=f't{len(out):04d}', case=scenario+'__'+variant,
                                source=variant, arm=arm))
    return out

def design():
    return dict(schema='hcr-exp28-design-v1', basis_commit=BASE_COMMIT,
        scope='single_A_to_B_boundary_state_component_ablation',
        arms=list(ARMS), scenarios=list(SCENARIOS), variants=list(VARIANTS),
        fixed_initial_value=FIXED_VALUE, source_queries=2, followup_trials=42,
        source_queries_shared=True, independent_random_replicates=0,
        kernel='unmodified_hcr.discover_paths_make_program_settle_reconstruct',
        manipulation='only_initial_values_of_bound_previous_edge_and_or_prefix_groups',
        fixed_control='same_guard_same_packet_same_target_mask; fixed_value_instead_of_A_activation',
        fixed_value_rationale='preselected_round_high_value_0.99; no_EXP28_outcome_tuning; one_value_only',
        guard='R046_semantics; full_support_validation; reject_all_on_any_dependency_change',
        dependency_order='preserve_R046_ID_sorted_assumed_edges_with_first_mismatch_exit',
        old_goal_imported=False, stabilization_history_imported=False,
        graph_search_reused=False, proof_nodes_reused=False,
        automatic_retry=False, host_correction=False, new_learning=False,
        hypotheses={
            'H_carry_both_ticks': 'extend: carry_both ticks < cold, if uncensored and outcome preserved',
            'H_edge_ticks': 'extend: carry_edge ticks < cold, if uncensored and outcome preserved',
            'H_prefix_ticks': 'extend: carry_prefix ticks < cold, if uncensored and outcome preserved',
            'H_source_specificity': 'per_mask_extend: carry ticks < fixed ticks; equality falsifies this strict prediction only',
            'H_outcome': 'each_non_cold_arm preserves cold raw_value and accepted',
            'H_rejection': 'mismatch controls reject reuse and have zero imported groups',
            'H_ID_native': 'within_scenario_arm: ID relabel preserves native counts and numeric trajectory',
        },
        estimands={
            'edge_effect_ticks': 'carry_edge - cold',
            'prefix_effect_ticks': 'carry_prefix - cold',
            'both_effect_ticks': 'carry_both - cold',
            'interaction_ticks': 'carry_both - carry_edge - carry_prefix + cold; descriptive_not_independence_proof',
            'source_specificity_ticks': 'carry_mask - fixed_mask',
        },
        legacy_H_ID='EXP27_3_falsified_comparisons_preserved; no_total_operation_invariance_assumed',
        not_tested=['preallocated_substrate', 'plasticity', 'learned_circuit_competition',
                   'natural_language_context', 'full_AdaptiveSession', 'selective_invalidation',
                   'wall_time_efficiency', 'energy', 'peak_memory', 'multi_boundary_composition'])

def expected_plan_body():
    a, c, w = observations()
    return dict(design=design(), sources=a, cases=c, worlds=w, trials=trials(), kernel_config=deepcopy(CONFIG))

def validate_body(plan):
    for k, v in expected_plan_body().items():
        require(plan[k] == v, 'frozen plan changed: ' + k)
