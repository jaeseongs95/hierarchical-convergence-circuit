"""Independent R050 audit: no worker, controller, runtime, or dynamics execution.

Native session numeric/event replay and proof validation use the existing
hcr.evaluation verifiers. Target selection, intervention, adoption, pairing,
condition coverage and cost aggregation are independently recomputed here.
"""
from __future__ import annotations
import argparse
from collections import Counter
from copy import deepcopy
from pathlib import Path
from math import isclose
import sys
from .common import (CONTRACT, SRC_TREE, TEST_TREE, dump, files, fingerprint,
                     finite_nonnegative, git_tree, load, require, sha, unseal)

ARMS = ('hold', 'same_input_restart', 'echo_revision_restart', 'strength_revision_restart')
FORBIDDEN = {'hcr.runtime', 'hcr.sessions', 'hcr.review', 'hcr.dynamics',
             'tools.r050_review_boundary.worker', 'tools.r050_review_boundary.protocol'}


def validate_reservations(execution: dict, states: dict, limits: dict, kernel_bound: int) -> None:
    """Check the external reservation BEFORE every recorded native advance.

    Final cost alone cannot prove that the frozen admission rule was followed.
    These are audited generation states, not regenerated producer states.
    """
    count = execution['advances']
    require(type(count) is int and 0 <= count <= limits['max_advances_per_session'],
            'Advance count must be an integer inside the frozen budget')
    require(type(execution['ready']) is bool, 'Ready flag must be a boolean')
    transitions = execution['packet']['document']['transitions']
    require(count == len(transitions) - 2, 'Advance count differs from journal')
    for ordinal, transition in enumerate(transitions[2:]):
        require(transition['operation'] == 'advance', 'Unexpected execution operation')
        previous_generation = ordinal + 1
        require(previous_generation in states and previous_generation + 1 in states,
                'Missing independently replayed reservation state')
        before = states[previous_generation]['pending']
        after = states[previous_generation + 1]['pending']
        require(before is not None and after is not None and before['ready'] is False,
                'Advance admitted without a running pending state')
        old_ticks = before['cost']['kernel_ticks']
        new_ticks = after['cost']['kernel_ticks']
        require(type(old_ticks) is int and type(new_ticks) is int and 0 <= old_ticks <= new_ticks,
                'Invalid native tick ledger')
        require(ordinal < limits['max_advances_per_session']
                and old_ticks + kernel_bound <= limits['max_kernel_ticks_per_session'],
                'Advance admitted without its frozen worst-case tick reservation')
        require(new_ticks - old_ticks <= kernel_bound,
                'Native advance exceeded its reserved kernel bound')


def exact_fields(value: dict, names: set[str], context: str) -> None:
    require(isinstance(value, dict) and set(value) == names, context + ' schema fields')


def independent_target(obs: dict, candidate: dict | None) -> dict:
    if candidate is None:
        return {'edge_id': None, 'slot': None, 'reason': 'no_candidate', 'slots_inspected': 0}
    conflicts = candidate['diagnostic']['suggestion']['sign_conflict_edges']
    slots = set()
    for path in candidate['decision']['expanded_paths']:
        for index in path:
            require(type(index) is int and 0 <= index < len(obs['edges']), 'Explored path slot')
            slots.add(index)
    weak = [i for i, e in enumerate(obs['edges']) if type(e['score']) in (int, float)
            and 0 < abs(e['score']) < 1]
    first_pool = [i for i in weak if obs['edges'][i]['id'] in conflicts]
    pool = first_pool if first_pool else [i for i in weak if i in slots]
    if not pool:
        return dict(edge_id=None, slot=None, reason='no_weak_known_dependency', slots_inspected=len(obs['edges']))
    lowest = min(abs(obs['edges'][i]['score']) for i in pool)
    index = next(i for i in range(len(obs['edges'])) if i in pool and abs(obs['edges'][i]['score']) == lowest)
    return dict(edge_id=obs['edges'][index]['id'], slot=index,
                reason='weak_sign_conflict' if first_pool else 'weak_explored_dependency',
                slots_inspected=len(obs['edges']))


def independent_observation(obs: dict, arm: str, target: dict) -> dict:
    require(arm in ARMS, 'Arm whitelist')
    expected = deepcopy(obs)
    if arm.endswith('revision_restart'):
        index = target['slot']
        require(type(index) is int and 0 <= index < len(obs['edges']), 'Probe slot bound')
        require(obs['edges'][index]['id'] == target['edge_id'] and 0 < abs(obs['edges'][index]['score']) < 1,
                'Probe identity/strength')
        expected['revision'] = obs['revision'] + 1
        if arm == 'strength_revision_restart':
            expected['edges'][index]['score'] = float(2 * int(obs['edges'][index]['score'] > 0) - 1)
    return expected


def independent_terminal(candidate: dict | None) -> dict:
    if candidate is None or candidate['readout']['accepted'] is not True:
        return dict(accepted=False, value=None, selected_candidate_id=None)
    value = candidate['decision']['value']
    require(type(value) is bool and candidate['readout']['value'] is value, 'Gate cannot invent or flip a value')
    return dict(accepted=True, value=value, selected_candidate_id=candidate['candidate_id'])


def validate_matrix(plan: dict, spec: dict) -> None:
    require(plan['contract'] == CONTRACT and plan['cases'] == spec['cases'], 'Frozen case matrix')
    require(plan['arms'] == list(ARMS) and spec['arms'] == list(ARMS), 'Frozen arm order')
    require(plan['limits'] == spec['limits'] == dict(max_advances_per_session=8,
                max_kernel_ticks_per_session=1280, max_restarts_per_arm=1, max_probes_per_arm=1), 'Budget drift')
    require(len(plan['cases']) == 24, '24 baseline cases required')
    seen = set()
    for i, case in enumerate(plan['cases']):
        require(case['id'] == f'c{i:03d}', 'Case identity/order')
        require(type(case['top_down']) is bool and type(case['identity_variant']) is int, 'Typed conditions')
        combo = (case['strength'], case['relation'], case['identity_variant'], case['top_down'])
        require(combo not in seen, 'Duplicate condition')
        seen.add(combo)
        obs = case['observation']
        require(obs['episode_id'] == 'r050-' + case['id'] and obs['revision'] == 0, 'Initial observation identity')
        edges = obs['edges']
        nodes = ('v0', 'v1', 'v2') if case['identity_variant'] == 0 else ('v2', 'v1', 'v0')
        ids = ('a-edge', 'z-edge') if case['identity_variant'] == 0 else ('z-edge', 'a-edge')
        require(obs['start'] == nodes[0] and obs['goal'] == nodes[2] and len(edges) == 2, 'Fixed chain topology')
        for slot in (0, 1):
            score = case['strength'] * (-1 if slot == 1 and case['relation'] == '+-' else 1)
            require(edges[slot] == dict(id=ids[slot], source=nodes[slot], target=nodes[slot + 1], score=score),
                    'Paired edge identity/order/score')
    expected = {(s, r, i, t) for s in (0.02, 0.10, 1.0) for r in ('++', '+-') for i in (0, 1) for t in (False, True)}
    require(seen == expected, 'Missing or unexpected condition')
    require(plan['config']['kernel']['max_ticks'] == 160, 'Reservation no longer matches kernel')


def candidate_measures(execution: dict | None, reference_truth: bool) -> dict:
    # A saved partial state is measurable even when no candidate was completed.
    p = None if execution is None else execution['packet']['document']['engine']['pending']
    c = None if execution is None else execution['candidate']
    state = {} if p is None else dict(p['state'])
    obs = None if p is None else p['observation']
    conflicts = None
    if obs is not None and all(f'e:{i}' in state for i in range(len(obs['edges']))):
        conflicts = sum((state[f'e:{i}'] >= 0.5) != (e['score'] > 0)
                        for i, e in enumerate(obs['edges']) if e['score'] is not None and e['score'] != 0)
    measured = dict(numeric_goal_side=None if 'goal' not in state else state['goal'] >= 0.5,
                    numeric_state=state or None, pending_value=None if p is None else p['value'],
                    native_failure_reason=None if p is None else p['failure_reason'],
                    convergence_status=None if p is None else p['convergence']['status'],
                    execution_stop=None if execution is None else execution['stop'],
                    internal_edge_conflicts=conflicts)
    if c is None:
        return dict(**measured, raw_decision=None, raw_correct=None, accepted=False,
                    adopted_value=None, adopted_correct=None, support_gap_count=None,
                    D_DAG=None, proof_valid=None,
                    failure_class='external_compute_budget' if execution is not None
                        and execution['stop'] == 'external_compute_budget' else 'no_completed_candidate')
    d = c['decision']
    valid = d['proof']['under_assumptions_valid']
    adopted = independent_terminal(c)
    if d['convergence']['status'] == 'budget_exhausted':
        failure = 'native_budget_termination'
    elif p['failure_reason'] is not None:
        failure = 'native_failure'
    elif p['value'] is not None and (not valid or not d['proof']['nodes']):
        failure = 'proof_construction_failure'
    elif c['diagnostic']['support_gap_edges']:
        failure = 'dependency_support_failure'
    elif d['value'] is None:
        failure = 'native_abstention'
    elif not adopted['accepted']:
        failure = 'other_gate_rejection'
    else:
        failure = 'supported_adoption'
    raw = d['value']
    return dict(**measured, raw_decision=raw,
                raw_correct=None if raw is None else raw == reference_truth,
                accepted=adopted['accepted'], adopted_value=adopted['value'],
                adopted_correct=None if not adopted['accepted'] else adopted['value'] == reference_truth,
                support_gap_count=len(c['diagnostic']['support_gap_edges']),
                D_DAG=d['proof']['primitive_depth'] if valid else None,
                proof_valid=valid, failure_class=failure)


def numerical_comparison(left: dict, right: dict, tolerance: dict) -> dict:
    """Compare already verified raw records; IDs/timing are not numeric states.

    Network ordinals and native group keys preserve scheduling and binding.
    We never force trajectories to align, interpolate, or repair a value.
    """
    def projection(execution):
        doc = execution['packet']['document']
        networks = []
        ordinals = {}
        ticks = []
        for event in doc['events']:
            p = event['payload']
            if event['event'] == 'r02_network':
                require(p['network_id'] not in ordinals, 'Repeated network identity')
                ordinals[p['network_id']] = len(networks)
                networks.append(dict(kind=p['kind'], program=p['program'], top_down=p['top_down']))
            elif event['event'] == 'r02_tick':
                require(p['network_id'] in ordinals, 'Tick without network')
                ticks.append(dict(network=ordinals[p['network_id']], tick=p['tick'],
                                  state=p['state'], residual=p['residual'], stable_steps=p['stable_steps']))
        return doc['engine']['pending'], networks, ticks
    lp, ln, lt = projection(left)
    rp, rn, rt = projection(right)
    ls, rs = dict(lp['state']), dict(rp['state'])
    final_comparable = bool(ls) and bool(rs) and set(ls) == set(rs)
    close = lambda x, y: isclose(x, y, rel_tol=tolerance['rel_tol'], abs_tol=tolerance['abs_tol'])
    final_close = all(close(ls[k], rs[k]) for k in ls) if final_comparable else None
    max_final = max(abs(ls[k]-rs[k]) for k in ls) if final_comparable else None
    shape_equal = ln == rn and len(lt) == len(rt) and all(
        a['network'] == b['network'] and a['tick'] == b['tick'] and set(a['state']) == set(b['state'])
        for a,b in zip(lt,rt))
    trajectory_close = None
    trajectory_delta = None
    if lt and rt:
        if shape_equal:
            trajectory_delta = max(abs(a['state'][k]-b['state'][k])
                                   for a,b in zip(lt,rt) for k in a['state'])
            trajectory_close = all(all(close(a['state'][k],b['state'][k]) for k in a['state'])
                         and close(a['residual'],b['residual']) and a['stable_steps']==b['stable_steps']
                         for a,b in zip(lt,rt))
        else:
            trajectory_close = False
    return dict(final_state_comparable=final_comparable, final_state_close=final_close,
                final_state_max_abs_difference=max_final, network_structure_equal=ln==rn,
                trajectory_shape_equal=shape_equal, trajectory_close=trajectory_close,
                trajectory_max_abs_difference=trajectory_delta,
                left_tick_records=len(lt), right_tick_records=len(rt),
                kernel_ticks_equal=lp['cost']['kernel_ticks']==rp['cost']['kernel_ticks'],
                pending_value_equal=lp['value']==rp['value'],
                convergence_status_equal=lp['convergence']['status']==rp['convergence']['status'],
                terminal_equal=independent_terminal(left['candidate'])['value']==independent_terminal(right['candidate'])['value']
                    and independent_terminal(left['candidate'])['accepted']==independent_terminal(right['candidate'])['accepted'],
                tolerance=tolerance, numeric_difference_is_not_automatically_audit_failure=True)


def counter_values(execution: dict | None) -> dict:
    from dataclasses import fields
    from hcr.model import AdaptiveCost
    names = [f.name for f in fields(AdaptiveCost) if f.name != 'wall_seconds']
    values = dict.fromkeys(names, 0)
    if execution is not None:
        source = execution['packet']['document']['engine']['pending']['cost']
        for name in names:
            require(type(source[name]) is int and source[name] >= 0, 'Typed native cost: ' + name)
            values[name] = source[name]
        c = execution['candidate']
        if c is not None:
            values['proof_nodes_reconstructed'] += len(c['decision']['proof']['nodes'])
    # Alias fields from AdaptiveCost.snapshot are deliberately excluded.
    return values


class NativeVerifier:
    def __init__(self, plan: dict):
        self.plan = plan
        self.cache = {}

    def execution(self, execution: dict, case: dict, observation: dict, segment: int, label: str) -> None:
        from hcr.evaluation.review_audit import packet_states
        from .candidate_audit import verify_candidate
        packet = execution['packet']
        key = packet['sha256']
        require(key == fingerprint(packet['document']), 'Session packet hash mismatch before cache lookup')
        require(set(execution) == {'packet', 'candidate', 'advances', 'ready', 'stop'}, 'Execution schema')
        if key not in self.cache:
            self.cache[key] = packet_states(packet)
        states, report = self.cache[key]
        validate_reservations(execution, states, self.plan['limits'], self.plan['config']['kernel']['max_ticks'])
        require(report.get('verified') is True, 'Native independent state replay did not verify')
        doc = packet['document']
        core = doc['engine']
        require(doc['session_id'] == 'r050-' + case['id'] + '-' + label, 'Session identity')
        require(core['config'] == self.plan['config'] and core['memory'] == self.plan['empty_memory'], 'Config/frozen memory drift')
        require(core['switches'] == dict(use_circuits=True, top_down=case['top_down'], allow_reexpansion=True), 'Restart switch drift')
        require(not core['held'] and not core['feedback'] and not core['requests'], 'Unexpected learning/feedback/revision API')
        p = core['pending']
        require(p is not None and p['observation'] == observation and p['mode'] == 'frozen_eval', 'Input/mode binding')
        from hcr.prior_policy import read_scope
        require(read_scope(core) == 'legacy', 'Judgment prior drift')
        operations = [t['operation'] for t in doc['transitions']]
        require(operations[:2] == ['init', 'begin'] and all(op == 'advance' for op in operations[2:]), 'Unlisted state operation')
        require(execution['advances'] == len(operations) - 2 <= self.plan['limits']['max_advances_per_session'], 'Advance budget/accounting')
        ticks = p['cost']['kernel_ticks']
        require(ticks <= self.plan['limits']['max_kernel_ticks_per_session'], 'Kernel budget')
        require(execution['ready'] is p['ready'], 'Ready-state mismatch')
        if p['ready']:
            require(execution['stop'] == 'readout_ready' and execution['candidate'] is not None, 'Missing candidate')
            c = execution['candidate']
            require(c['reference']['segment'] == segment, 'Candidate segment binding')
            verify_candidate(c, packet, states)
        else:
            require(execution['stop'] == 'external_compute_budget' and execution['candidate'] is None, 'Budget termination masquerading as completion')
            require(execution['advances'] == self.plan['limits']['max_advances_per_session']
                    or ticks + self.plan['config']['kernel']['max_ticks'] > self.plan['limits']['max_kernel_ticks_per_session'],
                    'Premature termination without exhausted reservation')


def audit_measurement(record: dict, case: dict, first: dict, target: dict, expected_obs: dict, root: Path) -> None:
    arm = record['arm']
    obs = case['observation']
    body = dict(schema='hcr-review-measurement-request-v1', ordinal=1,
                source_candidate_id=first['candidate_id'], observation_digest=fingerprint(obs),
                episode_id=obs['episode_id'], from_revision=0, next_revision=1,
                edge_ids=[target['edge_id']], reason='selected_proof_or_explored_path_support_gap')
    request = dict(body, sha256=fingerprint(body))
    response = dict(request_sha256=request['sha256'], status='measured',
                    scores={target['edge_id']: expected_obs['edges'][target['slot']]['score']},
                    source='r050-public-score-echo' if arm == 'echo_revision_restart' else 'r050-sign-preserving-strength-manipulation')
    require(record['request'] == request and record['reply'] == response, 'Request/response contract or target drift')
    require(record['consumption'] == ('measurement_no_new_information' if arm == 'echo_revision_restart' else 'measurement_applied'), 'Native consumption status')
    where = root / 'measurements' / case['id'] / arm
    require(load(where / 'request.json') == request and load(where / 'response.json') == response, 'Raw measurement record mismatch')


def validate_arm(record: dict, baseline: dict, case: dict, plan: dict, root: Path, verifier: NativeVerifier) -> dict:
    b = unseal(baseline, 'hcc-r050-baseline-v1')
    r = unseal(record, 'hcc-r050-arm-v1')
    exact_fields(r, {'schema', 'case_id', 'arm', 'baseline_sha256', 'initial_candidate_id',
                     'target', 'request', 'reply', 'consumption', 'restart_observation',
                     'execution', 'restart_reason', 'terminal', 'stop_reason',
                     'same_state_continuation', 'learned', 'hidden_world_access', 'arm_wall_seconds'},
                 'Arm')
    arm = r['arm']
    require(arm in ARMS and r['case_id'] == case['id'] and r['baseline_sha256'] == baseline['sha256'], 'Arm/case/baseline binding')
    require(r['same_state_continuation'] is False and r['learned'] is False and r['hidden_world_access'] is False, 'Declared intervention boundary')
    first = b['execution']['candidate']
    require(r['initial_candidate_id'] == (first['candidate_id'] if first else None), 'First judgment was lost or replaced')
    target = independent_target(case['observation'], first)
    require(r['target'] == target, 'Experimental target differs from independently recomputed policy')
    restart = False
    if not b['execution']['ready']:
        stop = 'baseline_external_compute_budget'
    elif first['readout']['accepted']:
        stop = 'initially_supported'
    elif arm == 'hold':
        stop = 'hold_after_gate'
    elif arm != 'same_input_restart' and target['edge_id'] is None:
        stop = 'no_probe_target'
    elif b['execution']['packet']['document']['engine']['pending']['failure_reason'] is not None:
        stop = 'baseline_engine_failure'
    else:
        restart = True
        expected = independent_observation(case['observation'], arm, target)
        require(r['restart_observation'] == expected, 'Unplanned input/revision/topology edit')
        require(r['execution'] is not None, 'Missing explicitly requested computation')
        reason = {'same_input_restart': 'explicit_same_input_recomputation_control',
                  'echo_revision_restart': 'explicit_echo_revision_control_not_native_retry',
                  'strength_revision_restart': 'explicit_single_score_strength_intervention'}[arm]
        require(r['restart_reason'] == reason, 'Unlisted restart reason')
        if arm.endswith('revision_restart'):
            audit_measurement(r, case, first, target, expected, root)
        else:
            require(r['request'] is None and r['reply'] is None and r['consumption'] is None, 'Hidden measurement in same-input arm')
        raw_intervention = load(root / 'interventions' / case['id'] / (arm + '.json'))
        require(raw_intervention == dict(arm=arm, baseline_sha256=baseline['sha256'], reason=reason,
                    observation=expected, target=target, request=r['request'], reply=r['reply'], consumption=r['consumption']), 'Intervention receipt mismatch')
        verifier.execution(r['execution'], case, expected, 1, arm)
        stop = r['execution']['stop']
    if not restart:
        require(all(r[k] is None for k in ('execution', 'restart_observation', 'restart_reason', 'request', 'reply', 'consumption')), 'Extra hidden work in no-op arm')
    require(r['stop_reason'] == stop, 'Stop reason mismatch')
    final_execution = r['execution'] if restart else b['execution']
    expected_terminal = independent_terminal(final_execution['candidate'])
    require(r['terminal'] == expected_terminal, 'Terminal adoption was fabricated/reselected')
    require(finite_nonnegative(r['arm_wall_seconds']), 'Invalid measured arm time')
    # External task truth is assigned by the predeclared world, not inferred from a proof.
    truth = case['relation'] == '++'
    initial = candidate_measures(b['execution'], truth)
    final = candidate_measures(final_execution, truth)
    return dict(case_id=case['id'], arm=arm, strength=case['strength'], relation=case['relation'],
                identity_variant=case['identity_variant'], top_down=case['top_down'],
                baseline_sha256=baseline['sha256'], initial=initial, final=final,
                restarts=int(restart), probe_requests=int(r['request'] is not None),
                additional_advances=0 if not restart else r['execution']['advances'],
                additional_counters=counter_values(r['execution']),
                baseline_counters=counter_values(b['execution']),
                stop_reason=stop, native_observe_first_next_action=b['native_observe_first_next_action'],
                probe_target=target, arm_wall_seconds=r['arm_wall_seconds'],
                raw_path='raw/' + case['id'] + '/' + arm + '.json',
                numeric_state_continuity=False, continued_frontier_operations=0,
                actual_energy_joules=None, measured_process_memory_bytes=None)


def check_progress(root: Path, case_id: str, label: str, execution: dict) -> set[str]:
    """Bind each saved partial snapshot to the independently replayed final trace."""
    final = execution['packet']['document']
    names = set()
    for generation, transition in enumerate(final['transitions']):
        name = f"{case_id}/{label}/step-{generation:03d}-{transition['operation']}.json"
        snap = load(root / 'progress' / name)
        require(snap['sha256'] == fingerprint(snap['document']), 'Progress checksum')
        doc = snap['document']
        require(doc['session_id'] == final['session_id'] and doc['source_hashes'] == final['source_hashes']
                and doc['transitions'] == final['transitions'][:generation + 1]
                and doc['events'] == final['events'][:transition['event_end']]
                and fingerprint(doc['engine']) == transition['after_state'], 'Unbound or edited partial snapshot')
        if generation == len(final['transitions']) - 1:
            require(snap == execution['packet'], 'Last progress snapshot differs from final native packet')
        names.add(name)
    if execution['candidate'] is not None:
        name = f'{case_id}/{label}/candidate.json'
        require(load(root / 'progress' / name) == execution['candidate'], 'Candidate raw copy drift')
        names.add(name)
    return names


def source_integrity(root: Path) -> None:
    manifest = load(root / 'source_manifest.json')
    require(files(root / 'source') == manifest['files'], 'Frozen source bytes/inventory differ')
    require(git_tree(root / 'source' / 'src') == SRC_TREE, 'Core source is not the pinned Git tree')
    require(git_tree(root / 'source' / 'tests') == TEST_TREE, 'Core tests are not the pinned Git tree')
    require(not (FORBIDDEN & set(sys.modules)), 'Auditor imported producer/runtime modules')


def audit_bundle(root: Path) -> dict:
    source_integrity(root)
    raw_seal = load(root / 'raw_manifest.json')
    raw_inventory = {}
    for folder in ('baselines', 'raw', 'progress', 'measurements', 'interventions'):
        if (root / folder).exists():
            raw_inventory.update({folder + '/' + k: v for k, v in files(root / folder).items()})
    require(raw_seal['schema'] == 'hcc-r050-raw-manifest-v1' and raw_seal['files'] == raw_inventory, 'Raw evidence inventory/hash mismatch')
    plan_packet = load(root / 'plan.json')
    plan = unseal(plan_packet, 'hcc-r050-plan-v1')
    require(plan['source_manifest_sha256'] == sha((root / 'source_manifest.json').read_bytes()), 'Plan/source binding')
    spec = load(root / 'source' / 'experiments' / 'exp-31-review-boundary' / 'frozen_spec.json')
    validate_matrix(plan, spec)
    require(plan['config'] == spec['config'], 'Default config drift')
    require(plan['numeric_comparison'] == spec['numeric_comparison'] == dict(abs_tol=1e-12, rel_tol=1e-12), 'Comparison tolerance drift')
    require(plan['frozen_predictions'] == spec['predictions'] and plan['boundaries'] == spec['boundaries'], 'Frozen claims/boundaries drift')
    from hcr.model import AdaptiveConfig
    from hcr.circuits import AdaptiveMemory
    from hcr import codec
    require(plan['config'] == codec.plain(AdaptiveConfig())
            and plan['empty_memory'] == AdaptiveMemory.empty(AdaptiveConfig()).document(), 'Not the pinned default/empty-memory baseline')
    raw_expected = {case['id'] + '/' + arm + '.json' for case in plan['cases'] for arm in ARMS}
    require(set(files(root / 'raw')) == raw_expected, 'Missing/extra raw arms; partial run cannot be called complete')
    require(set(files(root / 'baselines')) == {c['id'] + '.json' for c in plan['cases']}, 'Baseline inventory')
    verifier = NativeVerifier(plan)
    rows = []
    comparisons = []
    baseline_cost = Counter()
    expected_progress = set()
    expected_measurements = set()
    expected_interventions = set()
    from hcr.evaluation.review_audit import next_action
    for case in plan['cases']:
        baseline = load(root / 'baselines' / (case['id'] + '.json'))
        b = unseal(baseline, 'hcc-r050-baseline-v1')
        require(b['case'] == case, 'Baseline condition mismatch')
        verifier.execution(b['execution'], case, case['observation'], 0, 'baseline')
        require(finite_nonnegative(b['preparation_seconds']), 'Baseline measured time')
        expected_target = independent_target(case['observation'], b['execution']['candidate'])
        require(b['experimental_probe_target'] == expected_target, 'Baseline target policy')
        action, target = next_action('observe_first', b['execution']['packet']['document']['engine'], b['execution']['candidate'],
                                     dict(extra_advances=0, extra_kernel_ticks=0, measurements=0, restarts=0),
                                     dict(max_extra_advances=8, max_extra_kernel_ticks=1280, max_measurements=1), False)
        require(b['native_observe_first_next_action'] == dict(action=action, target=target), 'Native selector diagnostic differs')
        baseline_cost.update(counter_values(b['execution']))
        expected_progress.update(check_progress(root, case['id'], 'baseline', b['execution']))
        arm_executions = {}
        for arm in ARMS:
            record = load(root / 'raw' / case['id'] / (arm + '.json'))
            require(record['arm'] == arm, 'File-name/arm mismatch')
            rows.append(validate_arm(record, baseline, case, plan, root, verifier))
            arm_executions[arm] = record['execution']
            if record['execution'] is not None:
                expected_progress.update(check_progress(root, case['id'], arm, record['execution']))
                expected_interventions.add(case['id'] + '/' + arm + '.json')
            if record['request'] is not None:
                expected_measurements.update({case['id'] + '/' + arm + '/' + k + '.json' for k in ('request', 'response')})
        for prediction, left, right, left_label, right_label in (
            ('P1', b['execution'], arm_executions['same_input_restart'], 'baseline', 'same_input_restart'),
            ('P2', arm_executions['same_input_restart'], arm_executions['echo_revision_restart'], 'same_input_restart', 'echo_revision_restart'),
            ('P3', arm_executions['echo_revision_restart'], arm_executions['strength_revision_restart'], 'echo_revision_restart', 'strength_revision_restart')):
            evaluated = left is not None and right is not None
            comparisons.append(dict(case_id=case['id'], prediction=prediction,
                left=left_label, right=right_label, evaluated=evaluated,
                not_evaluated_reason=None if evaluated else 'required_explicit_restart_not_executed',
                comparison=numerical_comparison(left,right,plan['numeric_comparison']) if evaluated else None))
    require(set(files(root / 'progress')) == expected_progress, 'Missing/extra progress snapshots')
    require((set(files(root / 'measurements')) if (root / 'measurements').exists() else set()) == expected_measurements, 'Measurement file inventory')
    require((set(files(root / 'interventions')) if (root / 'interventions').exists() else set()) == expected_interventions, 'Intervention file inventory')
    require(not (FORBIDDEN & set(sys.modules)), 'Independent audit imported producer execution code')
    extra = Counter()
    for row in rows:
        extra.update(row['additional_counters'])
    return dict(schema='hcc-r050-audit-v1', verified=True, plan_sha256=plan_packet['sha256'],
                baseline_count=24, arm_records=96, rows=rows, numerical_comparisons=comparisons,
                unique_baseline_counters=dict(baseline_cost), additional_counters=dict(extra),
                unique_native_ready_packets_verified=len(verifier.cache),
                measurements=sum(r['probe_requests'] for r in rows), restarts=sum(r['restarts'] for r in rows),
                native_state_numeric_event_replay=True, independent_proof_and_support_validation=True,
                rollout_samples_are_independent=False, zero_energy_claim=False,
                learned_circuit_reuse_tested=False, state_preserving_review_tested=False)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--run', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    a = ap.parse_args(argv)
    report = audit_bundle(a.run)
    dump(a.output, report)
    print('VERIFIED: 24 baselines / 96 paired arm records', flush=True)
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
