"""Frozen matrix, independent intervention audit and native adapter checks."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from tools.r050_review_boundary.common import IntegrityError, load, seal
from tools.r050_review_boundary.worker import execute_session
from tools.r051_edge_controls.worker import intervention
from tools.r051_edge_controls.audit import validate_spec, expected_observation, validate_record, render

ROOT = Path(__file__).resolve().parents[3]


class Contract(unittest.TestCase):
    def setUp(self):
        self.spec = load(ROOT/'experiments/exp-32-edge-controls/frozen_spec.json')
        self.case = self.spec['cases'][0]

    def test_complete_matrix(self):
        validate_spec(self.spec)
        self.assertEqual(len(self.spec['cases'])*len(self.spec['arms']), 16)

    def test_config_numeric_representation_is_preserved(self):
        self.spec['config']['kernel']['evidence_gain'] = 4
        with self.assertRaisesRegex(IntegrityError,'numeric representation'):
            validate_spec(self.spec)

    def test_matrix_tampering_rejected(self):
        for field, value in (('top_down', True), ('identity_variant', 1), ('strength', 1.0)):
            spec = deepcopy(self.spec)
            spec['cases'][0][field] = value
            with self.assertRaises(IntegrityError):
                validate_spec(spec)

    def test_no_duplicate_or_extra_cases(self):
        for cases in (self.spec['cases'][:-1], self.spec['cases']+[self.case]):
            with self.assertRaises(IntegrityError):
                validate_spec(dict(self.spec,cases=cases))

    def test_all_arms_match_independent_observation(self):
        original = deepcopy(self.case['observation'])
        for arm in self.spec['arms']:
            self.assertEqual(intervention(original,arm), expected_observation(original,arm))
        self.assertEqual(original,self.case['observation'])

    def test_single_slot_and_revision(self):
        for arm, slot in (('edge0',0),('edge1',1)):
            obs = intervention(self.case['observation'],arm)
            self.assertEqual(obs['revision'],1)
            self.assertEqual([e['score'] for e in obs['edges']], [1.0,0.02] if slot == 0 else [0.02,1.0])
            self.assertEqual(obs['edges'][1-slot],self.case['observation']['edges'][1-slot])

    def test_echo_and_hold(self):
        hold = intervention(self.case['observation'],'hold')
        echo = intervention(self.case['observation'],'revision_only')
        self.assertEqual(hold['edges'],echo['edges'])
        self.assertEqual((hold['revision'],echo['revision']),(0,1))

    def test_unsupported_arm_rejected(self):
        for arm in ('both','auto_select','retry'):
            with self.assertRaises(IntegrityError):
                intervention(self.case['observation'],arm)

    def record(self):
        baseline = seal(dict(schema='hcc-r051-baseline-v1',case=self.case,execution={}))
        raw = dict(schema='hcc-r051-arm-v1',case_id=self.case['id'],arm='edge0',
            baseline_sha256=baseline['sha256'],observation=intervention(self.case['observation'],'edge0'),
            measurement_calls=0,automatic_retry=False,execution={})
        return baseline, raw

    def test_valid_paired_record(self):
        baseline, raw = self.record()
        validate_record(seal(raw),baseline,self.case,'edge0')

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
                validate_record(seal(raw),baseline,self.case,'edge0')

    def test_strong_native_sanity_and_no_measurement_path(self):
        from hcr.circuits import AdaptiveMemory
        from hcr.model import AdaptiveConfig
        from hcr.evaluation.review_audit import packet_states
        from tools.r050_review_boundary.candidate_audit import verify_candidate
        plan = dict(self.spec, empty_memory=AdaptiveMemory.empty(AdaptiveConfig()).document())
        for td in (False,True):
            case = deepcopy(self.case)
            case['top_down'] = td
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
