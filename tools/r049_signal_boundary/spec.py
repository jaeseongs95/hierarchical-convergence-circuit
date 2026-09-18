"""Frozen EXP30: two mechanisms, paired interventions, 48 deterministic cells."""
from copy import deepcopy
from tools.r048_precision.spec import CONFIG, NATIVE_BLOBS

BASE_COMMIT = '426ad699235935a97b74b1dcd1acbcd4890313b2'
PARENT_RUN = 'HCR-Evidence/exp29/r048-260918-144636-9af6bf45'
PARENT_BUNDLE_BLOB = '6cdf12b16874b34cd08ff10503777daec869b090'
R048_MANIFEST_BLOB = 'b7a2acd87277d0218ae4a08ae510e1f842d93b74'
LEVELS = (0.02, 0.10, 0.92)
PATTERNS = ('positive', 'mixed_negative')
VARIANTS = ('identity', 'fresh_ids')
ARMS = ('on_neutral', 'off_neutral', 'on_high', 'off_high')
HIGH = 0.99


def intervention(arm):
    if arm not in ARMS: raise ValueError('unknown EXP30 arm')
    td, init = arm.split('_')
    return dict(top_down=td == 'on', initial_mode=init,
                high_value=HIGH, new_goal_initial=0.5,
                initialization_origin='experimental_assignment_NOT_carry',
                reuse_applied=False, learning_applied=False)


def role(level, pattern, arm):
    if pattern == 'positive' and (arm.endswith('neutral') or level == 0.02):
        return 'prior_exploration_replication'
    return 'new_condition_in_frozen_matrix'


def design():
    return dict(schema='hcr-exp30-design-v1', basis_commit=BASE_COMMIT,
        levels=list(LEVELS), patterns=list(PATTERNS), variants=list(VARIANTS), arms=list(ARMS),
        queries=48, source_carry_queries=0, independent_random_replicates=0,
        topology='single_two_edge_A_chain', experimenter_initialization=HIGH,
        initialization='neutral: all .5; high: all edge/prefix .99, goal .5; same assignment for every world',
        manipulation='top_down_runtime_switch_X_initial_state; no_bias_gain_rule_or_world_based_reset',
        effective_signature='stored_program + config + raw_drives + top_down + active_link_indices; initial separately hashed',
        world_contract='explicit world independent of runtime; ++ or +-; sign-consistent noise-free measurements',
        score_contract='signed public drive, not truth; internal edge activation may disagree with score',
        hypotheses=dict(
            H_off_edge_alignment='uncensored OFF: final edge activation has strictly same sign as every nonzero observation',
            H_negative_high_raw='mixed_negative + high + stable raw: raw_value must be False; abstention/budget not evaluable',
            H_adoption_safety='uncensored query: never accept a value inconsistent with the fixed world; rejection not counted as accuracy',
            H_ID_native='same level/pattern/arm: ID relabel preserves numeric trajectory and native counters (not bytes/time)'),
        primary_estimands=['OFF_minus_ON_within_initialization', 'high_minus_neutral_within_top_down',
                            '(on_high-on_neutral)-(off_high-off_neutral)_ticks_and_raw_indicator'],
        boundaries=['immutable_observation','all_tick_activations','first_margin_readout_NOT_adoption',
                    'terminal_raw','native_proof_construction','assumption_support','terminal_adoption'],
        first_margin_readout='first executed tick abs(2*goal-1)>=kernel.margin_threshold; provisional only; never early stops',
        signal_ledger='after execution, all ticks x all groups; bias/external/support/top_down/self_competition/logit/target/damping',
        masked_message='counterfactual per-link term at the observed state, not an executed transmission',
        sign_conflict='strict (2*activation-1)*score<0; exactly .5 is neutral; native proof uses >=.5 as True',
        budget='160 ticks per query; censored/unsupported kept; no fill-after-stop',
        prior_knowledge='positive neutral ON/OFF at all 3 levels and positive .02 high ON/OFF previously explored; 16 ID cells tagged',
        unsupported_decomposition='raw error/proof missing/assumption unsupported/rejected are separate simultaneous flags',
        forbidden=['automatic_retry','host_correction','bias_tuning','goal_copy','proof_reselection','new_learning','post_stop_padding'],
        not_tested=['B_carry','learned_circuit','natural_language_context','full_AdaptiveSession','plasticity',
                    'preallocated_substrate','Graph_reexpansion','energy_efficiency','noisy_measurement'],
        inherited_failures_preserved=['EXP27_total_H_ID','EXP28_actual_precision','EXP29_actual_precision'],
        stopping_scope='this diagnostic step does not optimize the kernel; next design must connect to existing review boundaries')


def body():
    cases=[]; worlds={}; trials=[]
    for li, level in enumerate(LEVELS):
        for pi, pattern in enumerate(PATTERNS):
            for vi, variant in enumerate(VARIANTS):
                key=f's{li:02d}_{pattern}__{variant}'
                ids=['e0','e1'] if variant=='identity' else ['alias_Z9','alias_A1']
                vertices=['u','v','w']
                signs=(1,1) if pattern=='positive' else (1,-1)
                obs=dict(episode_id='exp27-sequential',revision=0,start='u',goal='w',edges=[
                    dict(id=ids[i],source=vertices[i],target=vertices[i+1],score=level*signs[i]) for i in range(2)])
                cases.append(dict(id=key,strength=level,pattern=pattern,variant=variant,observation=obs))
                # World is fixed here, not inferred from state, runtime labels, or a score sign test.
                worlds[key]={ids[0]:True,ids[1]:pattern=='positive'}
                order=(4*li+2*pi+vi)%4
                for arm in ARMS[order:]+ARMS[:order]:
                    trials.append(dict(id=f't{len(trials):04d}',case=key,arm=arm,
                        evidence_role=role(level,pattern,arm)))
    return dict(design=design(),cases=cases,worlds=worlds,trials=trials,kernel_config=deepcopy(CONFIG))
