"""Focused checks for the independent R052 role projection."""
from copy import deepcopy
import csv
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from tools.r050_review_boundary.common import IntegrityError, load, seal
from tools.r050_review_boundary.audit import numerical_comparison
import tools.r052_array_roles.audit as audit_module
from tools.r052_array_roles.audit import (
    expected_observation,
    render,
    role_aligned_comparison,
    validate_record,
    validate_spec,
)


ROOT = Path(__file__).resolve().parents[3]
TOLERANCE = dict(abs_tol=1e-12, rel_tol=1e-12)


def observation(swapped=False):
    edges = [dict(id='a-edge', source='v0', target='v1', score=0.02),
             dict(id='z-edge', source='v1', target='v2', score=0.02)]
    if swapped:
        edges.reverse()
    return dict(episode_id='fixture', revision=1, start='v0', goal='v2', edges=edges)


def execution(swapped=False, raw_coordinate_equal=False):
    obs = observation(swapped)
    start_slot, goal_slot = ((1, 0) if swapped else (0, 1))
    values = {'start_edge': 0.2, 'goal_edge': 0.8, 'goal': 0.7,
              'p_start': 0.3, 'p_goal': 0.6}
    state = {
        f'e:{start_slot}': values['start_edge'], f'e:{goal_slot}': values['goal_edge'],
        'goal': values['goal'], 'p:0:0': values['p_start'], 'p:0:1': values['p_goal'],
    }
    if swapped and raw_coordinate_equal:
        state['e:0'], state['e:1'] = values['start_edge'], values['goal_edge']
    paths = [[start_slot, goal_slot]]
    groups = [dict(id=f'e:{slot}', bias=0.0, level=0) for slot in (0, 1)] + [
        dict(id='p:0:0', bias=0.0, level=1),
        dict(id='p:0:1', bias=-2.0, level=1),
        dict(id='goal', bias=0.0, level=1),
    ]
    links = [
        dict(kind='support', source=f'e:{start_slot}', target='p:0:0', weight=2.0),
        dict(kind='top_down', source='p:0:0', target=f'e:{start_slot}', weight=0.35),
        dict(kind='support', source=f'e:{goal_slot}', target='p:0:1', weight=2.0),
        dict(kind='top_down', source='p:0:1', target=f'e:{goal_slot}', weight=0.35),
        dict(kind='support', source='p:0:0', target='p:0:1', weight=2.0),
        dict(kind='top_down', source='p:0:1', target='p:0:0', weight=0.35),
        dict(kind='support', source='p:0:1', target='goal', weight=2.0),
        dict(kind='top_down', source='goal', target='p:0:1', weight=0.35),
    ]
    drives = {f'e:{start_slot}': 0.08, f'e:{goal_slot}': 0.08,
              'goal': 0.0, 'p:0:0': 0.0, 'p:0:1': 0.0}
    network = dict(network_id='network-fixture', decision_id='decision-fixture',
        kind='decision', top_down=False, drives=drives,
        program=dict(edge_count=2, groups=groups, links=links, paths=paths),
        program_digest='ignored', metadata=dict(graph_complete=True, routes=[dict(
            node=dict(node_id='ignored', semantic_id='v2', revision=1),
            path=paths[0], visited=['v0', 'v1', 'v2'], uses=[])]))
    proof = dict(assumed_edges=[['a-edge', True], ['z-edge', True]], final='r-final',
        nodes=[
            dict(id='fact-a', rule='assumed_open', edge_id='a-edge', parents=[], path_index=None),
            dict(id='r-start', rule='start_edge', edge_id=None, parents=['fact-a'], path_index=0),
            dict(id='fact-z', rule='assumed_open', edge_id='z-edge', parents=[], path_index=None),
            dict(id='r-final', rule='extend_path', edge_id=None,
                 parents=['r-start', 'fact-z'], path_index=0),
        ], paths=[['a-edge', 'z-edge']], primitive_depth=2, under_assumptions_valid=True)
    assumptions = []
    for edge_id, slot, role, position in (
            ('a-edge', start_slot, 'start_edge', 0),
            ('z-edge', goal_slot, 'goal_edge', 1)):
        assumptions.append(dict(edge_id=edge_id, assumed=True,
            final_activation=state[f'e:{slot}'], score=0.02, observed_drive=0.08,
            goal_learned_drive=0.0, observation_kind='directional',
            support='directional_support', relation_drives=[dict(
                group=f'p:0:{position}', learned_drive=0.0)], routing_uses=[]))
    diagnostic = dict(assumptions=assumptions,
        explored_path_checks=[dict(directionally_open=True, observed_cut_edges=[], slots=paths[0])],
        boundaries=dict(decision_modified=False, memory_updated=False),
        contract=dict(schema='fixture-support-v1'),
        evidence_support_sufficient=True, graph_complete=True, proof_validity_reported=True,
        negative_coverage_required=False, original_value=True,
        proof_independently_revalidated=False,
        support_gap_edges=[], unknown_edges=[], unknown_outside_selected_proof=[],
        suggestion=dict(action='retain_under_declared_contract', executed=False,
                        edge_ids=[], sign_conflict_edges=[]))
    decision = dict(value=True, failure_reason=None, graph_complete=True,
        convergence=dict(status='stable_decision', ticks=2, residual=0.0,
                         stable_steps=4, margin=0.4),
        expanded_paths=paths, state=list(state.items()), proof=proof)
    readout = dict(accepted=True, value=True, reason='supported_under_sign_contract',
        policy='dependency_gate', truth_accessed=False, intervention=True,
        original_value=True, original_decision_modified=False, new_inferences=0,
        inference_cost_unchanged=True)
    candidate = dict(candidate_id='fixture-candidate', decision=decision,
                     diagnostic=diagnostic, readout=readout)
    pending = dict(state=state, observation=obs, value=True, failure_reason=None,
        convergence=dict(status='stable_decision'), cost=dict(kernel_ticks=2))
    events = [dict(event='r02_network', payload=network), dict(event='r02_tick', payload=dict(
        network_id='network-fixture', tick=1, state=state, residual=0.1, stable_steps=0))]
    return dict(packet=dict(document=dict(events=events, engine=dict(pending=pending))),
                candidate=candidate, stop='readout_ready')


class RoleProjection(unittest.TestCase):
    def test_permutation_equivariance_and_raw_coordinates_remain_distinct(self):
        left, right = execution(False), execution(True)
        report = role_aligned_comparison(left, right, observation(False), observation(True), TOLERANCE)
        self.assertTrue(report['final_state_close'])
        self.assertTrue(report['network_structure_close'])
        self.assertTrue(report['trajectory_close'])
        self.assertTrue(report['candidate_semantics_close'])
        self.assertFalse(numerical_comparison(left, right, TOLERANCE)['final_state_close'])

    def test_raw_coordinate_equality_does_not_create_false_role_equality(self):
        left, right = execution(False), execution(True, raw_coordinate_equal=True)
        self.assertTrue(numerical_comparison(left, right, TOLERANCE)['final_state_close'])
        report = role_aligned_comparison(left, right, observation(False), observation(True), TOLERANCE)
        self.assertFalse(report['final_state_close'])
        self.assertFalse(report['candidate_semantics_close'])

    def test_projection_does_not_modify_raw(self):
        left, right = execution(False), execution(True)
        before = deepcopy((left, right))
        role_aligned_comparison(left, right, observation(False), observation(True), TOLERANCE)
        self.assertEqual((left, right), before)

    def test_unmapped_state_and_malformed_role_map_are_rejected(self):
        left, right = execution(False), execution(True)
        right['packet']['document']['engine']['pending']['state']['mystery'] = 0.5
        with self.assertRaisesRegex(IntegrityError, 'Unmapped numeric state'):
            role_aligned_comparison(left, right, observation(False), observation(True), TOLERANCE)
        malformed = observation(True)
        malformed['edges'][0]['source'] = malformed['start']
        with self.assertRaisesRegex(IntegrityError, 'Unique structural role map'):
            expected_observation(malformed, 'start_edge')

    def test_all_numeric_children_contribute_to_maximum_difference(self):
        close, delta = audit_module._nested_comparison(
            {'first': 1.0, 'later': 2.0}, {'first': 1.1, 'later': 9.0}, TOLERANCE)
        self.assertFalse(close)
        self.assertEqual(delta, 7.0)

    def test_goal_prefix_proof_and_support_changes_are_detected(self):
        left = execution(False)
        mutations = []
        goal = execution(True)
        goal['packet']['document']['engine']['pending']['state']['goal'] += 0.1
        mutations.append(('final_state_close', goal))
        prefix = execution(True)
        prefix['packet']['document']['events'][1]['payload']['state']['p:0:0'] += 0.1
        mutations.append(('trajectory_close', prefix))
        proof = execution(True)
        proof['candidate']['decision']['proof']['primitive_depth'] = 3
        mutations.append(('candidate_semantics_close', proof))
        support = execution(True)
        support['candidate']['diagnostic']['assumptions'][0]['support'] = 'sign_conflict'
        mutations.append(('candidate_semantics_close', support))
        for field, right in mutations:
            with self.subTest(field=field):
                result = role_aligned_comparison(
                    left, right, observation(False), observation(True), TOLERANCE)
                self.assertFalse(result[field])

    def test_budget_unknowns_stay_not_comparable(self):
        def budget(obs):
            pending = dict(state={}, observation=obs, value=None, failure_reason=None,
                convergence=dict(status='budget_exhausted'), cost=dict(kernel_ticks=1280))
            return dict(packet=dict(document=dict(events=[], engine=dict(pending=pending))),
                        candidate=None, stop='external_compute_budget')
        result = role_aligned_comparison(budget(observation(False)), budget(observation(True)),
                                         observation(False), observation(True), TOLERANCE)
        self.assertIsNone(result['final_state_close'])
        self.assertIsNone(result['network_structure_close'])
        self.assertIsNone(result['trajectory_close'])
        self.assertIsNone(result['candidate_semantics_close'])
        self.assertIsNone(result['pending_value_equal'])

    def test_real_native_path_and_swapped_packets_are_projectable(self):
        from hcr.circuits import AdaptiveMemory
        from hcr.model import AdaptiveConfig
        from tools.r050_review_boundary.worker import execute_session

        spec = load(ROOT / 'experiments/exp-33-array-roles/frozen_spec.json')
        cases = (spec['cases'][0], spec['cases'][2])
        plan = dict(spec, empty_memory=AdaptiveMemory.empty(AdaptiveConfig()).document())
        with tempfile.TemporaryDirectory() as folder:
            roots = [Path(folder) / str(index) for index in range(2)]
            for root in roots:
                root.mkdir()
            runs = [execute_session(plan, case, case['observation'], roots[index],
                                    'native-projection', 0) for index, case in enumerate(cases)]
        before = deepcopy(runs)
        report = role_aligned_comparison(runs[0], runs[1], cases[0]['observation'],
                                         cases[1]['observation'], TOLERANCE)
        self.assertTrue(report['role_map_verified'])
        self.assertIsInstance(report['final_state_close'], bool)
        self.assertEqual(runs, before)


class Contract(unittest.TestCase):
    def setUp(self):
        self.spec = load(ROOT / 'experiments/exp-33-array-roles/frozen_spec.json')

    def test_fixed_spec_and_tamper_rejection(self):
        validate_spec(self.spec)
        for mutation in ('order', 'identity', 'score', 'schema'):
            spec = deepcopy(self.spec)
            if mutation == 'order':
                spec['cases'][0]['observation']['edges'].reverse()
            elif mutation == 'identity':
                spec['cases'][0]['identity_variant'] = 1
            elif mutation == 'score':
                spec['cases'][0]['strength'] = 0.1
            else:
                spec['schema'] = 'wrong'
            with self.assertRaises(IntegrityError):
                validate_spec(spec)

    def test_intervention_is_role_based_for_both_array_orders(self):
        for case in (self.spec['cases'][0], self.spec['cases'][2]):
            original = deepcopy(case['observation'])
            start = expected_observation(original, 'start_edge')
            goal = expected_observation(original, 'goal_edge')
            self.assertEqual(next(e['score'] for e in start['edges'] if e['id'] == 'a-edge'), 1.0)
            self.assertEqual(next(e['score'] for e in goal['edges'] if e['id'] == 'z-edge'), 1.0)
            self.assertEqual(original, case['observation'])

    def test_record_schema_pairing_and_tamper(self):
        case = self.spec['cases'][2]
        baseline = seal(dict(schema='hcc-r052-baseline-v1', case=case, execution={}))
        body = dict(schema='hcc-r052-arm-v1', case_id=case['id'], arm='start_edge',
            baseline_sha256=baseline['sha256'],
            observation=expected_observation(case['observation'], 'start_edge'),
            measurement_calls=0, automatic_retry=False, execution={})
        validate_record(seal(body), baseline, case, 'start_edge')
        for field in ('schema', 'binding', 'observation', 'retry'):
            tampered = deepcopy(body)
            if field == 'schema':
                tampered['schema'] = 'wrong'
            elif field == 'binding':
                tampered['baseline_sha256'] = '0' * 64
            elif field == 'observation':
                tampered['observation']['edges'][0]['score'] = 0.5
            else:
                tampered['automatic_retry'] = True
            with self.assertRaises(IntegrityError):
                validate_record(seal(tampered), baseline, case, 'start_edge')

    def test_auditor_import_does_not_import_producer_or_dynamics(self):
        env = dict(os.environ)
        env['PYTHONPATH'] = os.pathsep.join((str(ROOT / 'src'), str(ROOT)))
        code = ("import sys; import tools.r052_array_roles.audit; "
                "assert 'tools.r052_array_roles.worker' not in sys.modules; "
                "assert 'hcr.dynamics' not in sys.modules")
        result = subprocess.run([sys.executable, '-B', '-c', code], cwd=ROOT, env=env,
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_render_does_not_count_rejection_as_wrong_adoption(self):
        rows = []
        for order, accepted, correct in (('path', False, None), ('swapped', True, False)):
            rows.append(dict(case_id=order, strength=0.02, array_order=order, top_down=False,
                arm='hold', restarts=0, changed_roles=[],
                additional_counters=dict(kernel_ticks=0, signal_transmissions=0),
                final=dict(raw_decision=False, proof_valid=True, failure_class='fixture',
                    internal_edge_conflicts=1, accepted=accepted, adopted_correct=correct)))
        artifacts = render(dict(verified=True, purpose='implementation_validation', rows=rows))
        summary = artifacts['summary.ko.md'].decode('utf-8')
        self.assertIn('| path | False | hold | 0 | 0 | 0 | 1 | 0 |', summary)
        self.assertIn('| swapped | False | hold | 1 | 0 | 1 | 0 | 0 |', summary)
        parsed = list(csv.DictReader(io.StringIO(artifacts['trials.csv'].decode('utf-8-sig'))))
        self.assertEqual(parsed[0]['adopted_correct'], '')
        self.assertEqual(parsed[1]['adopted_correct'], 'False')


if __name__ == '__main__':
    unittest.main()
