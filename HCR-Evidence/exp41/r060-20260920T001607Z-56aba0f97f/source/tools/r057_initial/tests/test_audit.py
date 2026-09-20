"""Synthetic fixtures: no actual research program is executed here."""
from copy import deepcopy
from pathlib import Path
import unittest

from tools.r050_review_boundary.common import IntegrityError, load, seal, unseal, fingerprint
from tools.r053_feedback.tests.test_audit import CONFIG, original_program
from tools.r056_factorial.tests.test_audit import _trajectory
from tools.r057_initial.audit import (
    CONDITIONS, ORIGINAL_DRIVES, MASK_REMOVALS, _bridge, classify_endpoint,
    initial_contrasts, allocation_comparisons, validate_spec, verify_record,
)


def fixture(condition_id='start_i01', mask='full'):
    condition = CONDITIONS[condition_id]
    original = original_program()
    # This intentionally differs from the research program's -2 prefix bias.
    for group in original['groups']:
        group['bias'] = 0.0
    removed, active, kept = [], [], []
    for link in original['links']:
        if mask == 'drop_P_prefix' and link['kind'] == 'top_down' and (
                link['source'], link['target']) == ('p:0:1', 'p:0:0'):
            removed.append(link)
            continue
        kept.append(link)
        if link['kind'] == 'top_down':
            active.append(link)
    program = {**original, 'links': kept}
    initial = {g['id']: condition['initial_activation'] for g in original['groups']}
    body = dict(schema='hcc-r057-kernel-v1', condition=condition_id, mask=mask,
        orientation=condition['orientation'], initial_activation=condition['initial_activation'],
        input_pair=condition['input_pair'], original_drives=dict(ORIGINAL_DRIVES),
        parent_record_sha256='a'*64, source_program_digest=fingerprint(original),
        program=program, drives=condition['drives'], initial_state=initial, top_down=True,
        active_top_down_links=active, removed_top_down_links=removed, counterfactual=True,
        native_session_packet=None, proof=None, support=None, raw_decision=None, adoption=None,
        actual_energy_joules=None, termination_scope='counterfactual_kernel_termination',
        **_trajectory(program, condition['drives'], initial))
    return seal(body), original


def rows_fixture():
    rows = []
    for name, condition in CONDITIONS.items():
        initial = condition['initial_activation']
        for mask in MASK_REMOVALS:
            # Handwritten outcomes deliberately include low, high, and nonstable.
            goal = {0.1: .2, 0.5: .3, 0.9: .8}[initial]
            status = 'stable_decision'
            if mask == 'drop_P_prefix':
                goal += .05
                if condition['orientation'] == 'goal' and initial == .9:
                    status = 'budget_exhausted'
            rows.append(dict(condition=name, orientation=condition['orientation'],
                initial_activation=initial, input_pair=condition['input_pair'], mask=mask,
                final_state={'goal':goal,'e:0':initial,'e:1':1-initial},
                convergence={'status':status},cost={}))
    return rows


class AuditTests(unittest.TestCase):
    def test_synthetic_initial_and_mask_matrix(self):
        for condition in CONDITIONS.values():
            for mask, removed in MASK_REMOVALS.items():
                with self.subTest(condition=condition['id'], mask=mask):
                    packet, original = fixture(condition['id'], mask)
                    row = verify_record(packet, condition, dict(id=mask,remove=list(removed)),
                                        original, 'a'*64, CONFIG)
                    self.assertEqual(row['initial_activation'],condition['initial_activation'])

    def test_resealed_initial_metadata_and_state_tampering(self):
        packet, original = fixture()
        changes = [
            lambda b: b.update(initial_activation=.5),
            lambda b: b.update(orientation='goal'),
            lambda b: b.update(condition='start_i05'),
            lambda b: b['initial_state'].update(goal=.5),
            lambda b: b.update(initial_state={k:.5 for k in b['initial_state']}),
            lambda b: b['drives'].update({'e:0':3.02}),
            lambda b: b.update(proof={}),
            lambda b: b['program']['links'].pop(),
            lambda b: b['ticks'][0]['state'].update(goal=.123),
        ]
        for change in changes:
            body=deepcopy(unseal(packet,'hcc-r057-kernel-v1'));change(body)
            with self.assertRaises(IntegrityError):
                verify_record(seal(body),CONDITIONS['start_i01'],dict(id='full',remove=[]),
                              original,'a'*64,CONFIG)

    def test_initial_contrasts_direction_and_null_guard(self):
        contrasts=initial_contrasts(rows_fixture())
        self.assertEqual(len(contrasts),8)
        by={(r['orientation'],r['mask'],r['changed_initial']):r for r in contrasts}
        lower=by[('start','full',.1)];higher=by[('start','full',.9)]
        self.assertAlmostEqual(lower['delta_goal'],-.1)
        self.assertAlmostEqual(lower['delta_e0'],-.4)
        self.assertAlmostEqual(lower['delta_e1'],.4)
        self.assertIs(lower['different_stable_regimes'],False)
        self.assertAlmostEqual(higher['delta_goal'],.5)
        self.assertIs(higher['different_stable_regimes'],True)
        self.assertIsNone(by[('goal','drop_P_prefix',.9)]['different_stable_regimes'])
        self.assertAlmostEqual(by[('goal','drop_P_prefix',.9)]['delta_goal'],.5)
        for invalid in [rows_fixture()[:-1],rows_fixture()+[rows_fixture()[0]]]:
            with self.assertRaises(IntegrityError):
                initial_contrasts(invalid)

    def test_nonstable_baseline_is_not_equality(self):
        rows=rows_fixture()
        for row in rows:
            if row['condition']=='start_i05' and row['mask']=='full':
                row['convergence']['status']='oscillating'
        contrasts=initial_contrasts(rows)
        self.assertTrue(all(r['different_stable_regimes'] is None for r in contrasts
                            if r['orientation']=='start' and r['mask']=='full'))

    def test_within_initial_mask_comparison(self):
        comparisons=allocation_comparisons(rows_fixture())
        self.assertEqual(len(comparisons),6)
        for row in comparisons:
            self.assertAlmostEqual(row['delta_goal'],.05)
            self.assertEqual(row['initial_activation'],CONDITIONS[row['condition']]['initial_activation'])
        self.assertIsNone(comparisons[-1]['necessary_for_low_endpoint'])

    def test_endpoint_boundary(self):
        self.assertEqual(classify_endpoint(.499998,'stable_decision'),'low')
        self.assertEqual(classify_endpoint(.500002,'stable_ambiguous'),'high')
        self.assertEqual(classify_endpoint(.499999,'stable_decision'),'inconclusive')
        self.assertEqual(classify_endpoint(.500001,'stable_decision'),'inconclusive')
        self.assertEqual(classify_endpoint(.1,'budget_exhausted'),'inconclusive')

    def test_bridge_requires_same_initial_and_program(self):
        packet,_=fixture('start_i05')
        body=unseal(packet,'hcc-r057-kernel-v1')
        self.assertTrue(_bridge('start_i05','full',body,deepcopy(body))['verified'])
        for field in ['initial_state','program']:
            changed=deepcopy(body)
            if field=='initial_state':changed[field]['goal']=.1
            else:changed[field]['groups'][0]['bias']=.2
            with self.assertRaises(IntegrityError):
                _bridge('start_i05','full',body,changed)

    def test_spec_binding_rejects_resealed_changes(self):
        path=Path(__file__).parents[3]/'experiments/exp-38-initial-state/frozen_spec.json'
        spec=load(path);validate_spec(spec)
        for key in ['initial_levels','baseline_initial','anchor_condition_map','conditions']:
            changed=deepcopy(spec);changed[key]=None
            with self.assertRaises(IntegrityError):validate_spec(changed)


if __name__=='__main__':
    unittest.main()
