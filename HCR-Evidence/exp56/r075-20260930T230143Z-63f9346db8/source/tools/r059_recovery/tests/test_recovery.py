"""Synthetic fixtures and deliberate corruption, never new research outcomes."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch
from hcr.evaluation.audit import independent_step
from hcr.model import Config
from tools.r050_review_boundary.common import IntegrityError, dump, load, seal, unseal
from tools.r053_feedback.tests.test_audit import CONFIG, original_program
from tools.r059_recovery.audit import ARMS, INTERVENTION, UNMEASURED, measure, validate_spec, verify_record
from tools.r059_recovery.pipeline import kernel_and_audit, stage
from tools.r059_recovery.worker import execute, produce


def spec():
    return load(Path(__file__).parents[3]/'experiments/exp-40-local-recovery/frozen_spec.json')


def fixture(arm):
    program = original_program()
    for group in program['groups']:
        group['bias'] = 0.0
    anchor = dict(program=program, drives={}, final_state={g['id']: .5 for g in program['groups']})
    initial = dict(anchor['final_state'])
    if arm['coordinate'] is not None:
        initial[arm['coordinate']] += arm['delta']
    state, stable, ticks = dict(initial), 0, []
    for n in range(1,129):
        nxt = independent_step(program, state, {}, Config(**CONFIG), True)
        residual = max(abs(nxt[k]-state[k]) for k in state)
        stable = stable+1 if residual <= CONFIG['residual_tolerance'] else 0
        ticks.append(dict(tick=n, state=nxt, residual=residual, stable_steps=stable))
        state = nxt
    raw = dict(schema='hcc-r059-kernel-v1', condition='synthetic', arm=arm,
        anchor_record_sha256='a'*64, anchor_tick=512, program=program, drives={},
        anchor_state=anchor['final_state'], intervention=dict(INTERVENTION), horizon=128,
        top_down=True, completion='fixed_horizon_completed', counterfactual=True,
        initial_state=initial, final_state=state, ticks=ticks,
        cost=dict(kernel_ticks=128, group_updates=640, normalization_ops=640, signal_transmissions=1024),
        **{k: None for k in UNMEASURED})
    return raw, anchor


class RecoveryTests(unittest.TestCase):
    def test_all_synthetic_arms_independent_recurrence(self):
        for arm in ARMS:
            raw, anchor = fixture(arm)
            verify_record(seal(raw), 'synthetic', arm, anchor, 'a'*64, CONFIG)
            produced = execute(anchor['program'], {}, CONFIG, anchor['final_state'], arm, 128)
            body = {**raw, **produced}
            verify_record(seal(body), 'synthetic', arm, anchor, 'a'*64, CONFIG)

    def test_resealed_corruption_rejected(self):
        raw, anchor = fixture(ARMS[1])
        changes = [lambda b: b['initial_state'].update(goal=.501),
            lambda b: b['arm'].update(delta=0.0), lambda b: b.update(anchor_record_sha256='b'*64),
            lambda b: b['ticks'][0]['state'].update(goal=.2),
            lambda b: b['ticks'][0].update(residual=.2),
            lambda b: b['ticks'][0].update(stable_steps=512),
            lambda b: b['ticks'][0].update(tick=0), lambda b: b['ticks'].pop(),
            lambda b: b['cost'].update(kernel_ticks=127), lambda b: b['drives'].update(goal=.1),
            lambda b: b['program']['links'].pop(), lambda b: b.update(proof={}),
            lambda b: b.update(final_state=b['initial_state']),
            lambda b: b['intervention'].update(clipping=True)]
        for change in changes:
            bad = deepcopy(raw); change(bad)
            with self.assertRaises(IntegrityError):
                verify_record(seal(bad), 'synthetic', ARMS[1], anchor, 'a'*64, CONFIG)

    def test_range_rejected_without_clipping(self):
        raw, anchor = fixture(ARMS[1]); anchor['final_state']['e:0'] = 0.0
        before = deepcopy(anchor)
        with self.assertRaises(IntegrityError):
            execute(anchor['program'], {}, CONFIG, anchor['final_state'], ARMS[1], 128)
        self.assertEqual(anchor, before)

    def test_fresh_state_and_counter_reset_without_early_stop(self):
        raw, anchor = fixture(ARMS[0]); before = deepcopy(anchor)
        result = execute(anchor['program'], {}, CONFIG, anchor['final_state'], ARMS[0], 128)
        self.assertEqual(result['ticks'][0]['stable_steps'], 1)
        self.assertEqual(result['ticks'][-1]['stable_steps'], 128)
        self.assertEqual(result['cost']['kernel_ticks'], 128)
        self.assertEqual(anchor, before)

    def test_recovery_uses_entire_tail_and_all_coordinates(self):
        control, _ = fixture(ARMS[0]); raw = deepcopy(control)
        raw['arm'] = ARMS[1]; raw['initial_state']['e:0'] -= 1e-4
        self.assertTrue(measure(raw, control)['recovered'])
        self.assertEqual(measure(raw, control)['first_tick_with_all_remaining_distances_within_tolerance'], 1)
        raw['ticks'][112]['state']['e:0'] += 2e-8
        row = measure(raw, control)
        self.assertFalse(row['recovered'])
        self.assertEqual(row['final_distance'], 0)
        self.assertEqual(row['first_tick_with_all_remaining_distances_within_tolerance'], 114)
        raw['ticks'][-1]['state']['e:0'] += 2e-8
        self.assertIsNone(measure(raw, control)['first_tick_with_all_remaining_distances_within_tolerance'])
        self.assertIsNone(measure(control, control)['recovered'])

    def test_band_preservation_is_not_recovery(self):
        control, _ = fixture(ARMS[0]); raw = deepcopy(control)
        raw['arm'] = ARMS[1]; raw['initial_state']['e:0'] -= 1e-4
        for row in raw['ticks']:
            row['state']['e:0'] -= 1e-4
        result = measure(raw, control)
        self.assertTrue(result['band_preserved'])
        self.assertFalse(result['recovered'])

    def test_exact_spec_rejects_changed_matrix_and_threshold(self):
        frozen = spec(); validate_spec(frozen)
        self.assertEqual(len(frozen['conditions'])*len(frozen['arms']), 22)
        for key in ['arms', 'horizon', 'recovery_tolerance', 'recovery_tail_ticks', 'anchor_files', 'intervention']:
            bad = deepcopy(frozen); bad[key] = None
            with self.assertRaises(IntegrityError): validate_spec(bad)

    def test_produce_exact_matrix_and_anchor_initials(self):
        for purpose, count in [('research',22), ('implementation_validation',6)]:
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp); frozen = spec()
                dump(root/'plan.json', seal(dict(schema='hcc-r059-plan-v1', purpose=purpose, spec=frozen, config=CONFIG)))
                _, anchor = fixture(ARMS[0])
                for c in frozen['conditions']:
                    dump(root/'anchors'/f'study/{c}/full.json', seal(dict(schema='hcc-r058-kernel-v1', horizon=512, **anchor)))
                with patch('tools.r059_recovery.worker.read_network', return_value=(anchor['program'],{})):
                    produce(root)
                paths = list((root/('study' if purpose=='research' else 'smoke')).rglob('*.json'))
                self.assertEqual(len(paths), count)
                for path in paths:
                    body = unseal(load(path), 'hcc-r059-kernel-v1')
                    verify_record(load(path), path.parent.name, body['arm'], anchor,
                                  body['anchor_record_sha256'], CONFIG)

    def test_evidence_change_stops_before_worker(self):
        for key in ('parent_files','anchor_files'):
            with tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp); frozen=dict(parent_files={},anchor_files={})
                frozen[key]={'missing.json':'a'*64};dump(root/'plan.json',dict(spec=frozen))
                with patch('tools.r059_recovery.pipeline.stage') as launch:
                    with self.assertRaises(IntegrityError):kernel_and_audit(root,root,'test')
                    launch.assert_not_called()

    def test_first_failure_retained_and_no_retry(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            with patch('tools.r059_recovery.pipeline.subprocess.run',return_value=SimpleNamespace(returncode=7)) as launch:
                with self.assertRaises(IntegrityError):stage(root,root,'failed','tools.r059_recovery.worker',[])
                self.assertEqual(launch.call_count,1)
            self.assertEqual(load(root/'validation/failed.receipt.json')['returncode'],7)
            with self.assertRaises(FileExistsError):stage(root,root,'failed','tools.r059_recovery.worker',[])


if __name__ == '__main__':
    unittest.main()
