"""Generate public inputs and a separate evaluator world; no runtime results used."""
from copy import deepcopy
from .contracts import *

def observations(score=SCORE):
    sources={};cases=[];worlds={}
    for variant in VARIANTS:
        labels=['e0','e1','e2'] if variant=='identity' else ['alias_Z9','alias_A1','alias_M4']
        def obs(vertices,scores,revision):
            return dict(episode_id='exp27-sequential',revision=revision,start=vertices[0],goal=vertices[-1],
                edges=[dict(id=labels[i],source=vertices[i],target=vertices[i+1],score=s) for i,s in enumerate(scores)])
        sources[variant]=obs(['u','v','w'],[score,score],0)
        for scenario in SCENARIOS:
            vertices=['p','q','r','s'] if scenario=='different_subject' else ['u','v','w','z']
            scores=[score,-score if scenario=='premise_changed' else score,score]
            observation=obs(vertices,scores,1)
            key=scenario+'__'+variant
            cases.append(dict(id=key,scenario=scenario,variant=variant,observation=observation))
            worlds[key]={e['id']:e['score']>0 for e in observation['edges']}
    return sources,cases,worlds

def conditions():
    return dict(schema=SCHEMA,basis_commit=BASE_COMMIT,backend='native_hcr_kernel_with_explicit_thought_carry_adapter',
        variants=list(VARIANTS),scenarios=list(SCENARIOS),arms=list(ARMS),source_queries=2,followup_trials=24,
        shared_source_is_not_independent_replication=True,
        retained_memory='frozen_parent_memory_preserved_as_basis_not_executed_by_this_adapter',
        learned_circuit_gate='not_executed; isolate_result_carry_from_learned_circuit_reuse',
        graph_discovery='unchanged_native_discover_paths_in_all_arms',
        native_program='unchanged_native_make_program; all_original_edges_retained',
        decision='unchanged_native_settle; only_state_carry_may_change_initial_state',
        proof='cold/state:native_reconstruct; memo/relation:compose_B_candidate_before_native_settle_then_verify; foreign_parent_refs_and_native_suffix_rules',
        carry_guard='same_episode_and_start; all_source_support_edge_ID_endpoint_score_snapshots_unchanged',
        state_binding='edge_ID_and_endpoints; prefix_edge_sequence; do_not_copy_old_goal_or_stability_history',
        state_transfer='all_prior_support_valid_or_reset_all; untrusted_initialization_not_fact',
        fallback='registered_reuse_rejection_then_cold_computation; never_fix_input_or_proof',
        numeric_tolerance='audit:2e-12; equality_signatures:exact_JSON_except_effective_drive_default_zero',
        automatic_retry=False,host_correction=False,model_download=False,learning_updates=0,
        hypotheses={
          'H_state_ticks':'extend:state_carry B_ticks < cold B_ticks; given nonzero state transfer and uncensored',
          'H_proof_reuse':'extend:relation_carry composes B candidate before native decision using existing A proof node identities and fewer new nodes than cold',
          'H_binding':'different_subject:all_carry_arms reject the A result; never alias equal Boolean values',
          'H_invalidation':'premise_changed:all_carry_arms reject A; descendants do not use stale references',
          'H_outcome':'within each case all arms preserve value and adoption, not necessarily numeric trajectory',
          'H_ID':'within arm/scenario ID relabel preserves operation counts and role-normalized result; byte volumes and wall time excluded',
          'memo_comparison':'no unique HCC advantage assumed; report equality or difference with ordinary dependency-aware memo'},
        not_tested=['automatic_relation_learning','full_HCC_cycle','brain_mechanism','pool_to_decision_warm_start',
                    'runtime_path_scheduling_optimization','graph_expansion_reduction','energy','peak_memory'])

def trial_order():
    rows=[]
    # Counterbalance arm order; no auto repeat/retry.
    for si,scenario in enumerate(SCENARIOS):
        for vi,variant in enumerate(VARIANTS):
            k=(si*2+vi)%len(ARMS)
            for arm in ARMS[k:]+ARMS[:k]:
                rows.append(dict(id=f't{len(rows):04d}',case=scenario+'__'+variant,arm=arm,source=variant))
    return rows
