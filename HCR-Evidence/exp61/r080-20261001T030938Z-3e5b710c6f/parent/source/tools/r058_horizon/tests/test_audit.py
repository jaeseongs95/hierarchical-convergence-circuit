"""Synthetic continuation fixtures; the actual research conditions are not run."""
from copy import deepcopy
from pathlib import Path
import unittest
from hcr.model import Config
from hcr.evaluation.audit import independent_step
from tools.r050_review_boundary.common import IntegrityError, load, seal, unseal
from tools.r053_feedback.tests.test_audit import CONFIG
from tools.r057_initial.tests.test_audit import fixture
from tools.r057_initial.audit import CONDITIONS
from tools.r058_horizon.audit import INTERVENTION, checkpoint, prefix_packet, validate_spec, verify_record


def continuation_fixture():
    # R057 synthetic fixture deliberately sets the research -2 bias to zero.
    packet,original=fixture('start_i01')
    prefix=unseal(packet,'hcc-r057-kernel-v1');body=deepcopy(prefix)
    marker={k:deepcopy(body[k]) for k in ('final_state','convergence','cost')}
    state=dict(marker['final_state']);stable=marker['convergence']['stable_steps'];cfg=Config(**CONFIG)
    for n in range(len(body['ticks'])+1,513):
        nxt=independent_step(body['program'],state,body['drives'],cfg,True)
        residual=max(abs(nxt[k]-state[k]) for k in state)
        stable=stable+1 if residual<=cfg.residual_tolerance else 0
        body['ticks'].append(dict(tick=n,state=nxt,residual=residual,stable_steps=stable));state=nxt
    totals=dict(kernel_ticks=512,group_updates=2560,normalization_ops=2560,
                signal_transmissions=512*len(body['program']['links']))
    body.pop('convergence')
    body.update(schema='hcc-r058-kernel-v1',termination_scope='counterfactual_fixed_horizon',
        final_state=state,first_termination=marker,cost=totals,
        continuation_cost={k:v-marker['cost'][k] for k,v in totals.items()},horizon=512,
        completion='fixed_horizon_completed',continuation_intervention=dict(INTERVENTION))
    return body,original,prefix


class AuditTests(unittest.TestCase):
    def verify(self,body,original):
        return verify_record(seal(body),CONDITIONS['start_i01'],dict(id='full',remove=[]),
                             original,'a'*64,CONFIG)

    def test_independent_suffix_and_exact_prefix_reconstruction(self):
        body,original,prefix=continuation_fixture()
        self.assertEqual(unseal(prefix_packet(body),'hcc-r057-kernel-v1'),prefix)
        row=self.verify(body,original)
        self.assertEqual(row['cost']['kernel_ticks'],512)
        self.assertEqual(row['continuation_cost']['kernel_ticks'],512-len(prefix['ticks']))
        self.assertEqual(row['checkpoints']['160']['state'],body['ticks'][159]['state'])
        self.assertEqual(row['checkpoints']['512']['state'],body['ticks'][511]['state'])
        self.assertTrue(row['postmarker_band_preserved'])
        self.assertIsNone(row['first_nonmatching_tick'])

    def test_suffix_resealed_tampering_is_rejected(self):
        body,original,_=continuation_fixture();n=body['first_termination']['convergence']['ticks']
        changes=[
            lambda b:b['ticks'][n]['state'].update(goal=.123),
            lambda b:b['ticks'][n].update(stable_steps=1),
            lambda b:b['ticks'][n].update(residual=.123),
            lambda b:b['ticks'][n].update(tick=n),
            lambda b:b['ticks'].pop(),
            lambda b:b['cost'].update(kernel_ticks=511),
            lambda b:b['continuation_cost'].update(kernel_ticks=512),
            lambda b:b.update(final_state=dict(b['initial_state'])),
            lambda b:b['continuation_intervention'].update(reset_state=True),
        ]
        for change in changes:
            bad=deepcopy(body);change(bad)
            with self.assertRaises(IntegrityError):self.verify(bad,original)

    def test_first_termination_is_not_replaceable(self):
        body,original,_=continuation_fixture()
        changes=[
            lambda b:b['first_termination']['convergence'].update(ticks=512),
            lambda b:b['first_termination']['convergence'].update(ticks=1),
            lambda b:b['first_termination']['convergence'].update(status='budget_exhausted'),
            lambda b:b['first_termination']['final_state'].update(goal=.5),
            lambda b:b.update(proof={}),
        ]
        for change in changes:
            bad=deepcopy(body);change(bad)
            with self.assertRaises(IntegrityError):self.verify(bad,original)

    def test_checkpoint_stability_and_band_are_distinct(self):
        point=dict(tick=160,state={'goal':.8},residual=.1,stable_steps=0)
        result=checkpoint(point,CONFIG)
        self.assertEqual(result['goal_band'],'high')
        self.assertEqual(result['stable_regime'],'inconclusive')
        point['stable_steps']=4
        self.assertEqual(checkpoint(point,CONFIG)['stable_regime'],'high')

    def test_frozen_contract_rejects_horizon_and_marker_changes(self):
        spec=load(Path(__file__).parents[3]/'experiments/exp-39-fixed-horizon/frozen_spec.json')
        validate_spec(spec)
        for key in ('horizon','checkpoint_ticks','continuation_intervention','anchor_files'):
            altered=deepcopy(spec);altered[key]=None
            with self.assertRaises(IntegrityError):validate_spec(altered)


if __name__=='__main__':unittest.main()
