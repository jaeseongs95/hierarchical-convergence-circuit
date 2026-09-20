"""Frozen matrix, independent intervention audit and native adapter checks."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from tools.r050_review_boundary.common import IntegrityError, load, seal
from tools.r050_review_boundary.worker import execute_session
from tools.r052_array_roles.worker import intervention
from tools.r052_array_roles.audit import validate_spec, expected_observation, validate_record

ROOT = Path(__file__).resolve().parents[3]


class Contract(unittest.TestCase):
    def setUp(self):
        self.spec = load(ROOT/'experiments/exp-33-array-roles/frozen_spec.json')
        self.case = self.spec['cases'][0]

    def test_complete_matrix(self):
        validate_spec(self.spec)
        self.assertEqual(len(self.spec['cases'])*len(self.spec['arms']), 16)

    def test_config_numeric_representation_is_preserved(self):
        self.spec['config']['kernel']['evidence_gain'] = 4
        with self.assertRaisesRegex(IntegrityError,'numeric representation'):
            validate_spec(self.spec)

    def test_matrix_tampering_rejected(self):
        for field, value in (('top_down', True), ('array_order', 'swapped'), ('strength', 1.0)):
            spec = deepcopy(self.spec)
            spec['cases'][0][field] = value
            with self.assertRaises(IntegrityError):
                validate_spec(spec)

    def test_no_duplicate_or_extra_cases(self):
        for cases in (self.spec['cases'][:-1], self.spec['cases']+[self.case]):
            with self.assertRaises(IntegrityError):
                validate_spec(dict(self.spec,cases=cases))

    def test_all_arms_match_independent_observation(self):
        for case in self.spec['cases']:
            original = deepcopy(case['observation'])
            for arm in self.spec['arms']:
                self.assertEqual(intervention(original,arm), expected_observation(original,arm))
            self.assertEqual(original,case['observation'])

    def test_single_slot_and_revision(self):
        for case in self.spec['cases']:
            for arm, edge_id in (('start_edge','a-edge'),('goal_edge','z-edge')):
                original = case['observation']
                obs = intervention(original,arm)
                self.assertEqual(obs['revision'],1)
                self.assertEqual([e['id'] for e in obs['edges']], [e['id'] for e in original['edges']])
                self.assertEqual({e['id']:e['score'] for e in obs['edges']},
                                 {i:1.0 if i == edge_id else 0.02 for i in ('a-edge','z-edge')})

    def test_echo_and_hold(self):
        hold = intervention(self.case['observation'],'hold')
        echo = intervention(self.case['observation'],'revision_only')
        self.assertEqual(hold['edges'],echo['edges'])
        self.assertEqual((hold['revision'],echo['revision']),(0,1))

    def test_unsupported_arm_rejected(self):
        for arm in ('both','auto_select','retry'):
            with self.assertRaises(IntegrityError):
                intervention(self.case['observation'],arm)

    def test_missing_or_ambiguous_structural_target_rejected(self):
        for count in (0, 2):
            obs = deepcopy(self.case['observation'])
            obs['edges'] = [deepcopy(obs['edges'][0]) for _ in range(count)]
            with self.assertRaisesRegex(IntegrityError, 'Unique structural target'):
                intervention(obs, 'start_edge')

    def test_unexpected_initial_strength_rejected(self):
        obs = deepcopy(self.case['observation'])
        obs['edges'][0]['score'] = 1.0
        with self.assertRaisesRegex(IntegrityError, 'fixed weak positive score'):
            intervention(obs, 'start_edge')

    def record(self):
        baseline = seal(dict(schema='hcc-r052-baseline-v1',case=self.case,execution={}))
        raw = dict(schema='hcc-r052-arm-v1',case_id=self.case['id'],arm='start_edge',
            baseline_sha256=baseline['sha256'],observation=intervention(self.case['observation'],'start_edge'),
            measurement_calls=0,automatic_retry=False,execution={})
        return baseline, raw

    def test_valid_paired_record(self):
        baseline, raw = self.record()
        validate_record(seal(raw),baseline,self.case,'start_edge')

    def test_resealed_input_and_pairing_tampering_rejected(self):
        baseline, original = self.record()
        for field in ('slot','revision','binding','restart','measurement','retry'):
            raw = deepcopy(original)
            if field == 'slot': raw['observation']['edges'].reverse()
            elif field == 'revision': raw['observation']['revision'] = 2
            elif field == 'binding': raw['baseline_sha256'] = '0'*64
            elif field == 'restart': raw['execution'] = None
            elif field == 'measurement': raw['measurement_calls'] = 1
            else: raw['automatic_retry'] = True
            with self.assertRaises(IntegrityError):
                validate_record(seal(raw),baseline,self.case,'start_edge')

    def test_strong_native_sanity_and_no_measurement_path(self):
        from hcr.circuits import AdaptiveMemory
        from hcr.model import AdaptiveConfig
        from hcr.evaluation.review_audit import packet_states
        from tools.r050_review_boundary.candidate_audit import verify_candidate
        plan = dict(self.spec, empty_memory=AdaptiveMemory.empty(AdaptiveConfig()).document())
        for case in self.spec['cases']:
            obs = deepcopy(case['observation'])
            for edge in obs['edges']: edge['score'] = 1.0
            with tempfile.TemporaryDirectory() as folder, \
                    patch('hcr.review.measurement_request', side_effect=AssertionError('hidden request')) as request, \
                    patch('hcr.review.consume_measurement', side_effect=AssertionError('hidden consumption')) as consume, \
                    patch('hcr.review.choose_action', side_effect=AssertionError('hidden selector')) as selector:
                execution = execute_session(plan,case,obs,Path(folder),'sanity',0)
                states, _ = packet_states(execution['packet'])
                verify_candidate(execution['candidate'],execution['packet'],states)
                self.assertIs(execution['candidate']['readout']['accepted'],True)
                self.assertIs(execution['candidate']['readout']['value'],True)
                request.assert_not_called()
                consume.assert_not_called()
                selector.assert_not_called()


if __name__ == '__main__':
    unittest.main()
