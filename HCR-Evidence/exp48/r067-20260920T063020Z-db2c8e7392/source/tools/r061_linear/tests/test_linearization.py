"""Synthetic numerical and tamper checks, separate from research evidence."""
from copy import deepcopy
from pathlib import Path
import unittest
from hcr.evaluation.audit import independent_step
from hcr.model import Config
from tools.r050_review_boundary.common import IntegrityError, load, seal
from tools.r053_feedback.tests.test_audit import CONFIG, original_program
from tools.r053_feedback.audit import _close
from tools.r061_linear.audit import (ARMS, COORDINATES, INTERVENTION, UNMEASURED,
                                    reference_jacobian, verify_record, validate_spec, measure)
from tools.r061_linear.linear import jacobian
from tools.r061_linear.worker import execute


def fixture(arm):
    program = original_program()
    state = {c: .3 + .05*i for i, c in enumerate(COORDINATES)}
    anchor = dict(program=program, drives={}, final_state=state)
    raw = dict(schema='hcc-r061-kernel-v1', condition='synthetic', arm=arm,
        anchor_record_sha256='a'*64, anchor_tick=512, program=program, drives={},
        anchor_state=state, intervention=INTERVENTION, horizon=1, top_down=True,
        completion='fixed_horizon_completed', counterfactual=True,
        analytic_jacobian=jacobian(program, state, {}, CONFIG, COORDINATES),
        **{k: None for k in UNMEASURED}, **execute(program, {}, CONFIG, state, arm, 1))
    return raw, anchor


class LinearizationTests(unittest.TestCase):
    def verify(self, raw, anchor, arm):
        return verify_record(seal(raw), 'synthetic', arm, anchor, 'a'*64, CONFIG)

    def test_exact_matrix_and_frozen_spec(self):
        spec = load(Path(__file__).parents[3]/'experiments/exp-42-local-linearization/frozen_spec.json')
        validate_spec(spec)
        self.assertEqual(len(ARMS), 97)
        self.assertEqual(len({a['id'] for a in ARMS}), 97)
        spec['arms'][1]['epsilon'] = .01
        with self.assertRaises(IntegrityError):
            validate_spec(spec)

    def test_all_synthetic_arms_and_no_anchor_mutation(self):
        for arm in ARMS:
            raw, anchor = fixture(arm)
            before = deepcopy(anchor)
            self.verify(raw, anchor, arm)
            self.assertEqual(before, anchor)

    def test_analytic_columns_against_central_differences(self):
        raw, anchor = fixture(ARMS[0])
        matrix = raw['analytic_jacobian']
        self.assertTrue(_close(matrix, reference_jacobian(anchor['program'], anchor['final_state'], {}, CONFIG)))
        for j, c in enumerate(COORDINATES):
            plus, minus = dict(anchor['final_state']), dict(anchor['final_state'])
            plus[c] += 1e-6
            minus[c] -= 1e-6
            hi = independent_step(anchor['program'], plus, {}, Config(**CONFIG), True)
            lo = independent_step(anchor['program'], minus, {}, Config(**CONFIG), True)
            for i, target in enumerate(COORDINATES):
                self.assertAlmostEqual(matrix[i][j], (hi[target]-lo[target])/2e-6, delta=1e-9)

    def test_known_zero_link_derivative(self):
        program = original_program()
        program['links'] = []
        for group in program['groups']:
            group['bias'] = 0
        state = dict.fromkeys(COORDINATES, .5)
        matrix = jacobian(program, state, {}, CONFIG, COORDINATES)
        expected = 1-CONFIG['damping'] + CONFIG['damping']*.25*2*(CONFIG['self_excitation']+CONFIG['inhibition'])/CONFIG['temperature']
        for i, row in enumerate(matrix):
            for j, value in enumerate(row):
                self.assertAlmostEqual(value, expected if i == j else 0)

    def test_reject_jacobian_tampering(self):
        raw, anchor = fixture(ARMS[1])
        for row, col in [(0,0), (1,3), (4,4)]:
            bad = deepcopy(raw)
            bad['analytic_jacobian'][row][col] += .01
            with self.assertRaises(IntegrityError):
                self.verify(bad, anchor, ARMS[1])

    def test_reject_record_tampering(self):
        raw, anchor = fixture(ARMS[12])
        for field, value in [('horizon',2), ('anchor_record_sha256','b'*64), ('raw_decision',True),
                             ('condition','other'), ('arm',ARMS[13])]:
            bad = deepcopy(raw)
            bad[field] = value
            with self.assertRaises(IntegrityError):
                self.verify(bad, anchor, ARMS[12])
        for target in ['initial_state','final_state']:
            bad = deepcopy(raw)
            bad[target]['goal'] += .001
            with self.assertRaises(IntegrityError):
                self.verify(bad, anchor, ARMS[12])
        for mutate in [lambda b: b['ticks'][0]['state'].update(goal=.99),
                       lambda b: b['ticks'][0].update(stable_steps=999),
                       lambda b: b['cost'].update(kernel_ticks=2)]:
            bad = deepcopy(raw)
            mutate(bad)
            with self.assertRaises(IntegrityError):
                self.verify(bad, anchor, ARMS[12])

    def test_out_of_range_and_missing_coordinate_rejected(self):
        raw, anchor = fixture(ARMS[1])
        bad = deepcopy(ARMS[1]);bad['deltas']['goal'] = 2
        with self.assertRaises(IntegrityError):
            execute(anchor['program'], {}, CONFIG, anchor['final_state'], bad, 1)
        del bad['deltas']['goal']
        with self.assertRaises(IntegrityError):
            execute(anchor['program'], {}, CONFIG, anchor['final_state'], bad, 1)

    def test_metrics_include_signed_cancellation_and_control(self):
        control, _ = fixture(ARMS[0])
        self.assertIsNone(measure(control, control)['actual_gain'])
        raw, _ = fixture(ARMS[12])
        row = measure(raw, control)
        for i, c in enumerate(COORDINATES):
            expected = sum(raw['analytic_jacobian'][i][j] *
                (raw['initial_state'][k]-control['initial_state'][k]) for j, k in enumerate(COORDINATES))
            self.assertEqual(row['linear_prediction'][i], expected)
        self.assertAlmostEqual(row['error_over_epsilon_squared'], row['linearization_error']/1e-8)

    def test_self_link_and_duplicate_link_derivative(self):
        program = original_program()
        program['links'] += [dict(source='goal', target='goal', weight=-.2, kind='support')]*2
        state = dict.fromkeys(COORDINATES, .45)
        matrix = jacobian(program, state, {}, CONFIG, COORDINATES)
        self.assertTrue(_close(matrix, reference_jacobian(program, state, {}, CONFIG)))


if __name__ == '__main__':
    unittest.main()
