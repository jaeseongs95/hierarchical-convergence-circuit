"""Independent R052 replay and topology-role comparison.

The producer packet is never rewritten.  Array-indexed coordinates are mapped
to structural roles only inside comparisons, after native replay has accepted
the original packet.
"""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
import csv
import io
from math import isclose
from pathlib import Path
import re
import sys

from tools.r050_review_boundary.common import (
    SRC_TREE, TEST_TREE, dump, files, fingerprint, git_tree, load, publish,
    require, sha, unseal,
)
from tools.r050_review_boundary.audit import (
    FORBIDDEN as R050_FORBIDDEN,
    NativeVerifier,
    candidate_measures,
    check_progress,
    counter_values,
    numerical_comparison,
)


ARMS = ('hold', 'revision_only', 'start_edge', 'goal_edge')
FORBIDDEN = R050_FORBIDDEN | {
    'tools.r052_array_roles.worker',
    'tools.r052_array_roles.producer',
}
_GROUP = re.compile(r'p:(\d+):(\d+)\Z')


def validate_spec(spec: dict) -> None:
    from hcr import codec
    from hcr.model import AdaptiveConfig

    require(spec['schema'] == 'hcc-r052-frozen-spec-v1', 'Spec schema')
    require(spec['contract'] == 'r052-array-role-controls-v1'
            and spec['frozen_before_research_execution'] is True, 'Frozen contract')
    require(fingerprint(spec['config']) == fingerprint(codec.plain(AdaptiveConfig())),
            'Exact default config including numeric representation')
    require(spec['arms'] == list(ARMS), 'Arm matrix')
    require(spec['limits'] == dict(max_advances_per_session=8,
            max_kernel_ticks_per_session=1280), 'Budget contract')
    require(spec['numeric_comparison'] == dict(abs_tol=1e-12, rel_tol=1e-12),
            'Tolerance')
    expected = []
    for order in ('path', 'swapped'):
        for top_down in (False, True):
            number = len(expected)
            edges = [dict(id='a-edge', source='v0', target='v1', score=0.02),
                     dict(id='z-edge', source='v1', target='v2', score=0.02)]
            if order == 'swapped':
                edges.reverse()
            case_id = f'r052-c{number:03d}'
            expected.append(dict(id=case_id, strength=0.02, relation='++',
                identity_variant=0, array_order=order, top_down=top_down,
                observation=dict(episode_id=case_id, revision=0, start='v0', goal='v2',
                                 edges=edges)))
    require(fingerprint(spec['cases']) == fingerprint(expected),
            'Predeclared array permutation matrix')


def _roles(observation: dict) -> dict:
    require(isinstance(observation, dict) and set(observation) ==
            {'episode_id', 'revision', 'start', 'goal', 'edges'}, 'Observation fields')
    edges = observation['edges']
    require(isinstance(edges, list) and len(edges) == 2, 'Two-edge observation required')
    require(all(isinstance(edge, dict) and set(edge) ==
                {'id', 'source', 'target', 'score'} for edge in edges), 'Edge fields')
    starts = [i for i, edge in enumerate(edges) if edge['source'] == observation['start']]
    goals = [i for i, edge in enumerate(edges) if edge['target'] == observation['goal']]
    require(len(starts) == len(goals) == 1 and starts[0] != goals[0],
            'Unique structural role map')
    require(edges[starts[0]]['target'] == edges[goals[0]]['source'],
            'Broken start-to-goal topology')
    require(len({edge['id'] for edge in edges}) == 2, 'Duplicate edge identity')
    slot_to_role = {starts[0]: 'start_edge', goals[0]: 'goal_edge'}
    return dict(slot_to_role=slot_to_role,
                role_to_slot={role: slot for slot, role in slot_to_role.items()},
                id_to_role={edges[slot]['id']: role for slot, role in slot_to_role.items()})


def expected_observation(observation: dict, arm: str) -> dict:
    require(arm in ARMS, 'Arm whitelist')
    roles = _roles(observation)
    result = deepcopy(observation)
    if arm != 'hold':
        result['revision'] = 1
    if arm in ('start_edge', 'goal_edge'):
        result['edges'][roles['role_to_slot'][arm]]['score'] = 1.0
    return result


def validate_record(record: dict, baseline: dict, case: dict, arm: str) -> dict:
    raw = unseal(record, 'hcc-r052-arm-v1')
    require(set(raw) == {'schema', 'case_id', 'arm', 'baseline_sha256', 'observation',
                        'measurement_calls', 'automatic_retry', 'execution'}, 'Arm fields')
    require(raw['case_id'] == case['id'] and raw['arm'] == arm
            and raw['baseline_sha256'] == baseline['sha256'], 'Paired baseline identity')
    require(raw['observation'] == expected_observation(case['observation'], arm),
            'Input differs from fixed structural-role intervention')
    require(type(raw['measurement_calls']) is int and raw['measurement_calls'] == 0
            and raw['automatic_retry'] is False, 'Hidden measurement or retry')
    require((raw['execution'] is None) == (arm == 'hold'), 'Fixed restart count')
    return raw


def _program_projection(program: dict, roles: dict) -> tuple[dict, dict]:
    require(set(program) == {'edge_count', 'groups', 'links', 'paths'}, 'Program fields')
    slot_to_role = roles['slot_to_role']
    raw_paths = program['paths']
    require(isinstance(raw_paths, list), 'Program paths')
    path_roles = []
    for path in raw_paths:
        require(isinstance(path, list) and path, 'Nonempty program path')
        require(all(type(slot) is int and slot in slot_to_role for slot in path),
                'Unmapped program path slot')
        path_roles.append(tuple(slot_to_role[slot] for slot in path))
    require(len(set(path_roles)) == len(path_roles), 'Duplicate canonical path')
    ordered_paths = sorted(path_roles)
    path_index = {raw: ordered_paths.index(path_roles[raw]) for raw in range(len(path_roles))}

    group_map = {'goal': 'goal'}
    for slot, role in slot_to_role.items():
        group_map[f'e:{slot}'] = 'e:' + role
    for group in program['groups']:
        name = group.get('id') if isinstance(group, dict) else None
        match = _GROUP.fullmatch(name or '')
        if match:
            raw_path, step = map(int, match.groups())
            require(raw_path < len(path_roles) and step < len(path_roles[raw_path]),
                    'Unmapped path group')
            group_map[name] = f'p:{path_index[raw_path]}:{path_roles[raw_path][step]}'
    require(len(group_map) == len(program['groups'])
            and {group['id'] for group in program['groups']} == set(group_map),
            'Unmapped or duplicate program group')
    require(len(set(group_map.values())) == len(group_map), 'Non-bijective group projection')

    groups = []
    for group in program['groups']:
        require(set(group) == {'id', 'bias', 'level'}, 'Program group fields')
        groups.append(dict(id=group_map[group['id']], bias=group['bias'], level=group['level']))
    links = []
    for link in program['links']:
        require(set(link) == {'kind', 'source', 'target', 'weight'}
                and link['source'] in group_map and link['target'] in group_map,
                'Unmapped program link')
        links.append(dict(kind=link['kind'], source=group_map[link['source']],
                          target=group_map[link['target']], weight=link['weight']))
    groups.sort(key=lambda item: item['id'])
    links.sort(key=lambda item: (item['kind'], item['source'], item['target']))
    canonical = dict(edge_count=program['edge_count'], groups=groups, links=links,
                     paths=[list(path) for path in ordered_paths])
    return canonical, group_map


def _binding_projection(binding: dict, roles: dict) -> dict:
    require(isinstance(binding, dict) and isinstance(binding.get('edge_order'), list),
            'Binding edge order')
    result = deepcopy(binding)
    result.pop('observation_digest', None)
    result['edge_order'] = [roles['slot_to_role'][slot] for slot in binding['edge_order']]
    require(len(result['edge_order']) == len(binding['edge_order']), 'Binding slot map')
    return result


def _routes_projection(metadata: dict, roles: dict) -> list:
    require(isinstance(metadata, dict) and set(metadata) == {'graph_complete', 'routes'},
            'Network metadata fields')
    routes = []
    for route in metadata['routes']:
        require(set(route) == {'node', 'path', 'uses', 'visited'}, 'Route fields')
        node = route['node']
        require(isinstance(node, dict) and 'semantic_id' in node and 'revision' in node,
                'Route node')
        uses = []
        for use in route['uses']:
            require(isinstance(use, dict) and 'binding' in use, 'Route binding use')
            projected = deepcopy(use)
            projected['binding'] = _binding_projection(use['binding'], roles)
            uses.append(projected)
        path = [roles['slot_to_role'][slot] for slot in route['path']]
        routes.append(dict(node=dict(semantic_id=node['semantic_id'], revision=node['revision']),
                           path=path, visited=route['visited'], uses=uses))
    routes.sort(key=fingerprint)
    return routes


def _state_projection(state: dict, group_map: dict, complete=True) -> dict:
    require(isinstance(state, dict) and set(state) <= set(group_map)
            and (not complete or set(state) == set(group_map)),
            'Unmapped numeric state coordinate')
    return {group_map[key]: value for key, value in state.items()}


def _edge_ids(values, roles: dict) -> list:
    require(isinstance(values, list), 'Edge identity list')
    require(all(value in roles['id_to_role'] for value in values), 'Unmapped edge identity')
    return sorted(roles['id_to_role'][value] for value in values)


def _proof_projection(proof: dict, roles: dict) -> dict:
    require(isinstance(proof, dict), 'Proof packet')
    paths = []
    for path in proof['paths']:
        require(all(edge_id in roles['id_to_role'] for edge_id in path), 'Unmapped proof path')
        paths.append(tuple(roles['id_to_role'][edge_id] for edge_id in path))
    require(len(set(paths)) == len(paths), 'Duplicate canonical proof path')
    ordered_paths = sorted(paths)
    path_index = {raw: ordered_paths.index(paths[raw]) for raw in range(len(paths))}
    nodes = proof['nodes']
    by_id = {node['id']: node for node in nodes}
    require(len(by_id) == len(nodes), 'Duplicate proof node')
    cache, active = {}, set()

    def signature(node_id):
        require(node_id in by_id and node_id not in active, 'Invalid proof topology')
        if node_id in cache:
            return cache[node_id]
        active.add(node_id)
        node = by_id[node_id]
        edge_id = node['edge_id']
        require(edge_id is None or edge_id in roles['id_to_role'], 'Unmapped proof edge')
        raw_index = node['path_index']
        require(raw_index is None or type(raw_index) is int and raw_index in path_index,
                'Unmapped proof path index')
        value = dict(rule=node['rule'],
                     edge_role=None if edge_id is None else roles['id_to_role'][edge_id],
                     path_index=None if raw_index is None else path_index[raw_index],
                     parents=sorted((signature(parent) for parent in node['parents']), key=fingerprint))
        active.remove(node_id)
        cache[node_id] = value
        return value

    projected_nodes = sorted((signature(node_id) for node_id in by_id), key=fingerprint)
    final = None if proof['final'] is None else signature(proof['final'])
    assumed = []
    for edge_id, value in proof['assumed_edges']:
        require(edge_id in roles['id_to_role'] and type(value) is bool, 'Proof assumption')
        assumed.append([roles['id_to_role'][edge_id], value])
    assumed.sort()
    return dict(assumed_edges=assumed, final=final, nodes=projected_nodes,
                paths=[list(path) for path in ordered_paths],
                primitive_depth=proof['primitive_depth'],
                under_assumptions_valid=proof['under_assumptions_valid'])


def _candidate_projection(candidate: dict | None, roles: dict, group_map: dict) -> dict | None:
    if candidate is None:
        return None
    decision = candidate['decision']
    expanded = []
    for path in decision['expanded_paths']:
        require(all(slot in roles['slot_to_role'] for slot in path), 'Unmapped expanded path')
        expanded.append([roles['slot_to_role'][slot] for slot in path])
    expanded.sort()
    assumptions = []
    for item in candidate['diagnostic']['assumptions']:
        require(item['edge_id'] in roles['id_to_role'], 'Unmapped diagnostic assumption')
        relation_drives = []
        for term in item['relation_drives']:
            require(term['group'] in group_map, 'Unmapped diagnostic relation group')
            relation_drives.append(dict(group=group_map[term['group']],
                                         learned_drive=term['learned_drive']))
        relation_drives.sort(key=lambda term: term['group'])
        assumptions.append(dict(edge_role=roles['id_to_role'][item['edge_id']],
            assumed=item['assumed'], final_activation=item['final_activation'], score=item['score'],
            observed_drive=item['observed_drive'], goal_learned_drive=item['goal_learned_drive'],
            observation_kind=item['observation_kind'], support=item['support'],
            relation_drives=relation_drives,
            routing_uses=[_binding_projection(use, roles) if 'edge_order' in use else deepcopy(use)
                          for use in item['routing_uses']]))
    assumptions.sort(key=lambda item: item['edge_role'])
    checks = []
    for check in candidate['diagnostic']['explored_path_checks']:
        checks.append(dict(directionally_open=check['directionally_open'],
            slots=[roles['slot_to_role'][slot] for slot in check['slots']],
            observed_cut_edges=_edge_ids(check['observed_cut_edges'], roles)))
    checks.sort(key=fingerprint)
    diagnostic = candidate['diagnostic']
    suggestion = diagnostic['suggestion']
    support = dict(
        assumptions=assumptions,
        explored_path_checks=checks,
        boundaries=deepcopy(diagnostic['boundaries']),
        contract=deepcopy(diagnostic['contract']),
        evidence_support_sufficient=diagnostic['evidence_support_sufficient'],
        graph_complete=diagnostic['graph_complete'],
        negative_coverage_required=diagnostic['negative_coverage_required'],
        original_value=diagnostic['original_value'],
        proof_independently_revalidated=diagnostic['proof_independently_revalidated'],
        proof_validity_reported=diagnostic['proof_validity_reported'],
        support_gap_edges=_edge_ids(diagnostic['support_gap_edges'], roles),
        unknown_edges=_edge_ids(diagnostic['unknown_edges'], roles),
        unknown_outside_selected_proof=_edge_ids(diagnostic['unknown_outside_selected_proof'], roles),
        suggestion=dict(action=suggestion['action'], executed=suggestion['executed'],
                        edge_ids=_edge_ids(suggestion['edge_ids'], roles),
                        sign_conflict_edges=_edge_ids(suggestion['sign_conflict_edges'], roles)),
    )
    readout = candidate['readout']
    return dict(
        raw_decision=decision['value'], failure_reason=decision['failure_reason'],
        convergence=decision['convergence'], graph_complete=decision['graph_complete'],
        expanded_paths=expanded, state=_state_projection(dict(decision['state']), group_map),
        proof=_proof_projection(decision['proof'], roles), support=support,
        readout={key: readout[key] for key in (
            'accepted', 'value', 'reason', 'policy', 'truth_accessed', 'intervention',
            'original_value', 'original_decision_modified', 'new_inferences',
            'inference_cost_unchanged')},
    )


def _projection(execution: dict, observation: dict) -> dict:
    roles = _roles(observation)
    doc = execution['packet']['document']
    networks, ticks, maps = [], [], {}
    for event in doc['events']:
        payload = event['payload']
        if event['event'] == 'r02_network':
            require(payload['network_id'] not in maps, 'Repeated network identity')
            program, group_map = _program_projection(payload['program'], roles)
            maps[payload['network_id']] = (len(networks), group_map)
            require(set(payload['drives']) <= set(group_map), 'Unmapped network drive')
            networks.append(dict(kind=payload['kind'], top_down=payload['top_down'],
                program=program, drives={group_map[key]: value for key, value in payload['drives'].items()},
                graph_complete=payload['metadata']['graph_complete'],
                routes=_routes_projection(payload['metadata'], roles)))
        elif event['event'] == 'r02_tick':
            require(payload['network_id'] in maps, 'Tick without network')
            ordinal, group_map = maps[payload['network_id']]
            ticks.append(dict(network=ordinal, tick=payload['tick'],
                state=_state_projection(payload['state'], group_map), residual=payload['residual'],
                stable_steps=payload['stable_steps']))
    pending = doc['engine']['pending']
    require(pending is not None, 'Missing pending state')
    final_map = (maps[next(reversed(maps))][1] if maps else
                 {'goal': 'goal', **{f'e:{slot}': 'e:' + role
                                    for slot, role in roles['slot_to_role'].items()}})
    return dict(
        final_state=_state_projection(pending['state'], final_map, complete=bool(networks)),
        networks=networks, ticks=ticks,
        kernel_ticks=pending['cost']['kernel_ticks'], pending_value=pending['value'],
        native_failure_reason=pending['failure_reason'],
        convergence_status=pending['convergence']['status'], execution_stop=execution['stop'],
        candidate=_candidate_projection(execution['candidate'], roles, final_map),
    )


def _nested_comparison(left, right, tolerance: dict) -> tuple[bool, float | None]:
    differences = []

    def compare(a, b):
        if type(a) is bool or type(b) is bool or a is None or b is None:
            return type(a) is type(b) and a == b
        if type(a) in (int, float) and type(b) in (int, float):
            differences.append(abs(a - b))
            return isclose(a, b, rel_tol=tolerance['rel_tol'], abs_tol=tolerance['abs_tol'])
        if isinstance(a, dict) and isinstance(b, dict):
            if set(a) != set(b):
                return False
            return all([compare(a[key], b[key]) for key in a])
        if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
            if len(a) != len(b):
                return False
            return all([compare(x, y) for x, y in zip(a, b)])
        return type(a) is type(b) and a == b

    equal = compare(left, right)
    return equal, max(differences) if differences else None


def role_aligned_comparison(left: dict, right: dict, left_observation: dict,
                            right_observation: dict, tolerance: dict) -> dict:
    """Compare verified executions after a strict topology-role projection."""
    lp = _projection(left, left_observation)
    rp = _projection(right, right_observation)
    final_comparable = bool(lp['final_state']) and bool(rp['final_state']) \
        and set(lp['final_state']) == set(rp['final_state'])
    final_close, final_delta = (_nested_comparison(lp['final_state'], rp['final_state'], tolerance)
                                if final_comparable else (None, None))
    network_comparable = bool(lp['networks']) and bool(rp['networks'])
    network_close, network_delta = (_nested_comparison(lp['networks'], rp['networks'], tolerance)
                                    if network_comparable else (None, None))
    shape_equal = (len(lp['ticks']) == len(rp['ticks'])
                   and all(a['network'] == b['network'] and a['tick'] == b['tick']
                           and set(a['state']) == set(b['state'])
                           for a, b in zip(lp['ticks'], rp['ticks'])))
    trajectory_close = None
    trajectory_delta = None
    if shape_equal and lp['ticks'] and rp['ticks']:
        trajectory_close, trajectory_delta = _nested_comparison(lp['ticks'], rp['ticks'], tolerance)
    candidate_comparable = lp['candidate'] is not None and rp['candidate'] is not None
    candidate_close, candidate_delta = (_nested_comparison(lp['candidate'], rp['candidate'], tolerance)
                                         if candidate_comparable else (None, None))
    pending_value_comparable = lp['pending_value'] is not None and rp['pending_value'] is not None
    return dict(
        role_map_verified=True,
        final_state_comparable=final_comparable,
        final_state_close=final_close, final_state_max_abs_difference=final_delta,
        network_structure_comparable=network_comparable, network_structure_close=network_close,
        network_structure_max_abs_difference=network_delta,
        trajectory_shape_equal=shape_equal, trajectory_close=trajectory_close,
        trajectory_max_abs_difference=trajectory_delta,
        left_tick_records=len(lp['ticks']), right_tick_records=len(rp['ticks']),
        kernel_ticks_equal=lp['kernel_ticks'] == rp['kernel_ticks'],
        pending_value_comparable=pending_value_comparable,
        pending_value_equal=(lp['pending_value'] == rp['pending_value']
                             if pending_value_comparable else None),
        native_failure_reason_equal=lp['native_failure_reason'] == rp['native_failure_reason'],
        convergence_status_equal=lp['convergence_status'] == rp['convergence_status'],
        execution_stop_equal=lp['execution_stop'] == rp['execution_stop'],
        candidate_semantics_comparable=candidate_comparable,
        candidate_semantics_close=candidate_close,
        candidate_semantics_max_abs_difference=candidate_delta,
        tolerance=tolerance,
        numeric_or_semantic_difference_is_not_automatically_audit_failure=True,
    )


def audit(run: Path) -> dict:
    manifest = load(run / 'source_manifest.json')
    require(manifest['schema'] == 'hcc-r052-source-manifest-v1'
            and files(run / 'source') == manifest['files'], 'Frozen source inventory/hash')
    require(git_tree(run / 'source/src') == SRC_TREE
            and git_tree(run / 'source/tests') == TEST_TREE, 'Core/test tree drift')
    plan_packet = load(run / 'plan.json')
    plan = unseal(plan_packet, 'hcc-r052-plan-v1')
    require(plan['source_manifest_sha256'] == sha((run / 'source_manifest.json').read_bytes()),
            'Plan/source binding')
    spec = load(run / 'source/experiments/exp-33-array-roles/frozen_spec.json')
    require(plan['spec'] == spec, 'Frozen spec binding')
    validate_spec(spec)
    from hcr import codec
    from hcr.model import AdaptiveConfig
    from hcr.circuits import AdaptiveMemory
    require(plan['config'] == spec['config'] == codec.plain(AdaptiveConfig())
            and plan['empty_memory'] == AdaptiveMemory.empty(AdaptiveConfig()).document()
            and plan['limits'] == spec['limits'], 'Native config or memory drift')
    require(plan['purpose'] in ('implementation_validation', 'research'), 'Run purpose')
    smoke = plan['purpose'] == 'implementation_validation'
    root = run / ('smoke' if smoke else 'study')
    cases = [spec['cases'][i] for i in (0, 2)] if smoke else spec['cases']
    raw_manifest = load(run / 'raw_manifest.json')
    require(raw_manifest['schema'] == 'hcc-r052-raw-manifest-v1'
            and files(root) == raw_manifest['files'], 'Raw inventory/hash')
    require(set(files(root / 'baselines')) == {case['id'] + '.json' for case in cases},
            'Baseline inventory')
    expected_names = {case['id'] + '/' + arm + '.json' for case in cases for arm in ARMS}
    require(set(files(root / 'raw')) == expected_names
            and set(files(root / 'interventions')) == expected_names, 'Arm/receipt inventory')

    verifier = NativeVerifier(plan)
    progress, rows, comparisons, by_case, observations = set(), [], [], {}, {}
    baseline_cost, extra_cost = Counter(), Counter()
    for case in cases:
        baseline = load(root / 'baselines' / (case['id'] + '.json'))
        base = unseal(baseline, 'hcc-r052-baseline-v1')
        require(set(base) == {'schema', 'case', 'execution'} and base['case'] == case,
                'Baseline fields')
        initial = base['execution']
        verifier.execution(initial, case, case['observation'], 0, 'baseline')
        progress.update(check_progress(root, case['id'], 'baseline', initial))
        baseline_cost.update(counter_values(initial))
        executions, arm_observations = {}, {}
        for arm in ARMS:
            raw = validate_record(load(root / 'raw' / case['id'] / (arm + '.json')),
                                  baseline, case, arm)
            receipt = {key: value for key, value in raw.items()
                       if key not in ('schema', 'execution')}
            require(receipt == load(root / 'interventions' / case['id'] / (arm + '.json')),
                    'Intervention receipt')
            execution = raw['execution']
            if execution is not None:
                verifier.execution(execution, case, raw['observation'], 1, arm)
                progress.update(check_progress(root, case['id'], arm, execution))
            final = initial if arm == 'hold' else execution
            executions[arm] = final
            arm_observations[arm] = raw['observation']
            counters = counter_values(execution)
            extra_cost.update(counters)
            changed_roles = [role for role in ('start_edge', 'goal_edge')
                if raw['observation']['edges'][_roles(raw['observation'])['role_to_slot'][role]]['score']
                != case['observation']['edges'][_roles(case['observation'])['role_to_slot'][role]]['score']]
            rows.append(dict(case_id=case['id'], strength=case['strength'],
                array_order=case['array_order'], top_down=case['top_down'], arm=arm,
                baseline_sha256=baseline['sha256'], initial=candidate_measures(initial, True),
                final=candidate_measures(final, True), restarts=int(execution is not None),
                changed_roles=changed_roles, baseline_counters=counter_values(initial),
                additional_counters=counters, actual_energy_joules=None, measurement_calls=0))
        for left, right in (('hold', 'revision_only'), ('revision_only', 'start_edge'),
                            ('revision_only', 'goal_edge'), ('start_edge', 'goal_edge')):
            comparisons.append(dict(case_id=case['id'], left=left, right=right,
                comparison=numerical_comparison(executions[left], executions[right],
                                                spec['numeric_comparison'])))
        by_case[case['id']] = executions
        observations[case['id']] = arm_observations

    require(set(files(root / 'progress')) == progress, 'Progress inventory')
    expected_all = {folder + '/' + name for folder in ('raw', 'interventions')
                    for name in expected_names}
    expected_all |= {'baselines/' + case['id'] + '.json' for case in cases}
    expected_all |= {'progress/' + name for name in progress}
    require(set(files(root)) == expected_all, 'Extra raw artifacts')
    require(not (FORBIDDEN & set(sys.modules)), 'Auditor imported a producer/native dynamics')

    role_comparisons = []
    for left_index, right_index in ((0, 2), (1, 3)):
        if right_index >= len(spec['cases']):
            continue
        left_case, right_case = spec['cases'][left_index], spec['cases'][right_index]
        if left_case not in cases or right_case not in cases:
            continue
        for arm in ARMS:
            left, right = left_case['id'], right_case['id']
            role_comparisons.append(dict(left_case=left, right_case=right, arm=arm,
                role_aligned=role_aligned_comparison(by_case[left][arm], by_case[right][arm],
                    observations[left][arm], observations[right][arm], spec['numeric_comparison']),
                raw_array_coordinates=numerical_comparison(by_case[left][arm], by_case[right][arm],
                                                           spec['numeric_comparison'])))
    top_down_comparisons = []
    for left_index, right_index in ((0, 1), (2, 3)):
        if right_index >= len(spec['cases']):
            continue
        left_case, right_case = spec['cases'][left_index], spec['cases'][right_index]
        if left_case not in cases or right_case not in cases:
            continue
        for arm in ARMS:
            left, right = left_case['id'], right_case['id']
            top_down_comparisons.append(dict(left_case=left, right_case=right, arm=arm,
                comparison=numerical_comparison(by_case[left][arm], by_case[right][arm],
                                                spec['numeric_comparison'])))
    return dict(schema='hcc-r052-audit-v1', verified=True, plan_sha256=plan_packet['sha256'],
        research_experiment=not smoke, purpose=plan['purpose'], baseline_count=len(cases),
        arm_records=len(rows), rows=rows, comparisons=comparisons,
        role_aligned_array_comparisons=role_comparisons,
        top_down_comparisons=top_down_comparisons,
        unique_baseline_counters=dict(baseline_cost), additional_counters=dict(extra_cost),
        independent_samples=False, native_state_replay=True,
        role_projection_changes_raw_evidence=False)


def render(report: dict) -> dict[str, bytes]:
    require(report['verified'] is True, 'Verified audit required')
    rows = report['rows']
    lines = ['# EXP-33 / R052', '', '실행 목적: ' + report['purpose'], '',
        '독립 원자료 검산을 통과했다. 검산 통과는 배열 불변성 가설 지지를 뜻하지 않는다.', '',
        '| 배열 순서 | top-down | 개입 | 채택 | 정답 채택 | 오답 채택 | 보류 | 추가 ticks |',
        '|---|---|---|---:|---:|---:|---:|---:|']
    flat = []
    for row in rows:
        final = row['final']
        flat.append(dict(case_id=row['case_id'], strength=row['strength'],
            array_order=row['array_order'], top_down=row['top_down'], arm=row['arm'],
            raw_value=final['raw_decision'], proof_valid=final['proof_valid'],
            failure_class=final['failure_class'], edge_conflicts=final['internal_edge_conflicts'],
            accepted=final['accepted'], adopted_correct=final['adopted_correct'],
            restarts=row['restarts'], changed_roles=','.join(row['changed_roles']),
            additional_kernel_ticks=row['additional_counters']['kernel_ticks'],
            additional_signal_transmissions=row['additional_counters']['signal_transmissions']))
    for order in ('path', 'swapped'):
        for top_down in (False, True):
            for arm in ARMS:
                group = [row for row in rows if (row['array_order'], row['top_down'], row['arm'])
                         == (order, top_down, arm)]
                if not group:
                    continue
                lines.append(f'| {order} | {top_down} | {arm} | ' + ' | '.join(str(value) for value in (
                    sum(row['final']['accepted'] for row in group),
                    sum(row['final']['adopted_correct'] is True for row in group),
                    sum(row['final']['adopted_correct'] is False for row in group),
                    sum(not row['final']['accepted'] for row in group),
                    sum(row['additional_counters']['kernel_ticks'] for row in group))) + ' |')
    lines += ['', '동일 기준선의 분기와 배열 순서 대조는 독립 확률 표본이 아니다.',
        'role-aligned 비교는 원 packet을 수정하지 않고 구조 역할로만 투영한다.',
        '수치·궤적·proof/support/readout 차이는 연구 결과이며 audit 실패로 바꾸지 않는다.',
        '구현 검증 실행은 연구 결과로 합산하지 않는다.']
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, fieldnames=list(flat[0]))
    writer.writeheader()
    writer.writerows(flat)
    return {'summary.ko.md': ('\n'.join(lines) + '\n').encode('utf-8'),
            'trials.csv': stream.getvalue().encode('utf-8-sig')}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', type=Path, required=True)
    args = parser.parse_args(argv)
    report = audit(args.run)
    dump(args.run / 'analysis/audit.json', report)
    rendered = render(report)
    for name, content in rendered.items():
        publish(args.run / 'analysis' / name, content)
    require(all((args.run / 'analysis' / name).read_bytes() == content
                for name, content in render(load(args.run / 'analysis/audit.json')).items()),
            'Derived artifact mismatch')
    dump(args.run / 'validation/analysis_consistency.json', dict(verified=True,
        files={name: sha(content) for name, content in rendered.items()}, new_inferences=0))
    print('VERIFIED:', report['baseline_count'], 'baselines /', report['arm_records'],
          'arm records', flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
