"""생산 spec/transform을 import하지 않는 독립 입력·조건 검산."""
from copy import deepcopy
from itertools import permutations
import math
from .storage import require, digest


def declared_map(variant: str) -> dict:
    # 생산 edge_map과 다른, 사전 등록된 pair 명세다.
    if variant == 'identity':
        pairs = [('e0','e0'), ('e1','e1'), ('e2','e2'), ('e3','e3'),
                 ('e4','e4'), ('e5','e5'), ('e6','e6')]
    elif variant == 'swap_SD':
        pairs = [('e0','e4'), ('e1','e5'), ('e2','e2'), ('e3','e3'),
                 ('e4','e0'), ('e5','e1'), ('e6','e6')]
    else:
        raise ValueError('audit: 미등록 ID 배치')
    return dict(pairs)


def _check_observation(obs: dict) -> None:
    require(type(obs) is dict and set(obs) == {'episode_id','revision','start','goal','edges'}, 'observation schema')
    require(type(obs['revision']) is int and obs['revision'] >= 0, 'revision type')
    require(all(type(obs[k]) is str and obs[k] for k in ('episode_id','start','goal')), 'observation identity')
    require(type(obs['edges']) is list and len(obs['edges']) == 7, 'edge count')
    for edge in obs['edges']:
        require(type(edge) is dict and set(edge) == {'id','source','target','score'}, 'edge schema')
        require(all(type(edge[k]) is str and edge[k] for k in ('id','source','target')), 'edge identity')
        score = edge['score']
        require(score is None or (type(score) in (int,float) and math.isfinite(score)), 'edge score')
    ids = [edge['id'] for edge in obs['edges']]
    require(len(set(ids)) == len(ids) and set(ids) == {'e0','e1','e2','e3','e4','e5','e6'}, 'edge ID inventory')


def _strings(value, path='$'):
    if type(value) is str:
        yield path, value
    elif type(value) is dict:
        for key, item in value.items():
            yield path + '.<key>', key
            yield from _strings(item, path + '.' + key)
    elif type(value) is list:
        for index, item in enumerate(value):
            yield from _strings(item, f'{path}[{index}]')


def check_seed_reference_scope(seed: dict) -> dict:
    # 이 baseline은 abstract trained memory를 재사용한다. current eID를 담은 새로운
    # memory schema가 나오면 재명명을 추측하지 않고 별도 실험 설계를 요구한다.
    inventory = {'e0','e1','e2','e3','e4','e5','e6'}
    collisions = [(p, v) for field in ('memory','config')
                  for p, v in _strings(seed[field], '$.'+field) if v in inventory]
    require(not collisions, '동결 memory/config에 current edge ID 참조가 있습니다: ' + repr(collisions[:4]))
    return dict(current_edge_ID_references_found=0, memory_changed=False, config_changed=False,
                reference_scope='exact_JSON_string_keys_and_values; pinned_baseline_schema')


def check_case(case: dict, evaluations: dict, original: dict, original_worlds: dict) -> dict:
    require(set(case) == {'name','family','cohort','parent_case','id_variant','observation','manipulation'}, 'case schema')
    variant = case['id_variant']; mapping = declared_map(variant)
    inverse = {target: source for source, target in mapping.items()}
    require(len(inverse) == 7, '비일대일 재명명')
    require(case['name'] == variant+'__'+original['name'] and case['parent_case'] == original['name'], 'case binding')
    require(case['family'] == 'edge_id_role_isolation' and case['cohort'] == 'paired_ID_relabel', 'case labels')
    order = original['manipulation']['branch_order']
    require(case['manipulation'] == dict(branch_order=order, edge_map=mapping,
        source_observation_sha256=digest(original['observation']), boundary='before_native_begin'), 'mapping/등록 경계 변경')
    source, obs = original['observation'], case['observation']
    _check_observation(source); _check_observation(obs)
    restored = deepcopy(obs)
    for edge in restored['edges']:
        edge['id'] = inverse[edge['id']]
    # inverse 후 전체 관측을 비교한다. slots, relation, score, null, node, episode도 포함한다.
    require(digest(restored) == digest(source), '역변환 관측 불일치: ID 외 입력 변경')
    require(type(evaluations) is dict and set(evaluations) == set(original_worlds) and evaluations,
            'world 이름/inventory 변경')
    for name, truth in evaluations.items():
        require(type(truth) is dict and set(truth) == set(inverse), 'world edge inventory 변경')
        require(all(type(value) is bool for value in truth.values()), 'world truth는 bool이어야 합니다.')
        require({inverse[eid]: value for eid,value in truth.items()} == original_worlds[name], 'world 의미 변경')
    return dict(verified=True, inverse_mapping=inverse, restored_observation_sha256=digest(restored))


def check_conditions(current: dict, parent: dict) -> None:
    # 기대하는 전체 명세를 독립 선언한다. 생산 conditions()를 재사용하지 않는다.
    expected = dict(protocol='exp24-r043-input-order-control-v1',
        basis_commit='eedb04f90f02cf3c55693d493d33db18f96a23b5',
        budget=parent['conditions']['budget'], selection_limits=parent['conditions']['selection_limits'],
        scope='legacy', arm='online_support', id_variants=['identity','swap_SD'],
        schedulers=['input_order'],
        branch_orders=[''.join(p) for p in permutations('SMD')],
        native_trial_count=12, base_topology_count=1, parent_regression_trial_count=6,
        input_boundary='before_native_begin',
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
    require(digest(current) == digest(expected), '사전 등록 조건/예산 변경')


def check_plan_inputs(plan: dict, parent: dict, seed: dict) -> dict:
    check_conditions(plan['conditions'], parent)
    require(digest(seed['memory']) == plan['memory_sha256'] == parent['memory_sha256'] and
            digest(seed['config']) == plan['config_sha256'] == parent['config_sha256'], '동결 memory/config 변경')
    reference_report = check_seed_reference_scope(seed)
    originals = {c['name']:c for c in parent['cases']}
    orders = [''.join(p) for p in permutations('SMD')]
    require(len(originals) == len(parent['cases']) == 6 and set(originals) == {'order_'+o for o in orders}, '원 순열 inventory')
    require(type(plan['cases']) is list and len(plan['cases']) == 12, 'case count')
    byname = {c['name']:c for c in plan['cases']}
    names = {v+'__order_'+o for o in orders for v in ('identity','swap_SD')}
    require(set(byname) == names and set(plan['evaluation_worlds']) == names, 'case/world population')
    reports = {}
    for name, case in byname.items():
        original = originals[case['parent_case']]
        reports[name] = check_case(case, plan['evaluation_worlds'][name], original,
                                   parent['evaluation_worlds'][original['name']])
    require(type(plan['trials']) is list and len(plan['trials']) == 12, 'trial population')
    for index, trial in enumerate(plan['trials']):
        oi, offset = divmod(index, 2)
        cell = (oi + offset) % 2
        variant = ('identity','swap_SD')[cell]
        scheduler = 'input_order'
        expected = dict(id=f't{index:04d}', case=variant+'__order_'+orders[oi],
                        scope='legacy', arm='online_support', scheduler=scheduler)
        require(trial == expected, 'trial schedule/counterbalance 변경: '+str(index))
    return dict(verified=True, cases=reports, seed_reference_scope=reference_report,
                identity_regression_trials=6, native_trials=12, inverse_mapping_is_evaluator_only=True)
