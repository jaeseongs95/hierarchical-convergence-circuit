"""Synthetic proof/readout projection tests, separate from the native proof auditor."""
from copy import deepcopy
import sys
import types
import unittest
from unittest.mock import patch
from r045_direct_support.trajectory import describe
from r045_direct_support.storage import digest
from r045_direct_support.tests.fixtures import plan_fixture


def fixture(variant='identity',accepted=True,value=True):
    p,_,_=plan_fixture();c=deepcopy(next(x for x in p['cases'] if x['name']=='supported_len2__'+variant))
    obs=c['observation'];ids=[e['id'] for e in obs['edges']]
    state={'e:0':.9,'e:1':.9,'p:0:0':.8,'p:0:1':.8,'goal':.8}
    view=dict(observation=deepcopy(obs),completed_paths=[[0,1]],state=state)
    proof=dict(assumed_edges=[[ids[0],True],[ids[1],value]],paths=[ids])
    candidate={'fixture_view':view}
    final=dict(accepted=accepted,value=value if accepted else None,readout_ordinal=0)
    row=dict(ordinal=0,kernel_ticks_at_readout=7,raw_value=value,native_accepted=accepted,native_value=value if accepted else None,
             policy_accepted=accepted,policy_value=value if accepted else None,frontier_count=0,native_D_DAG=2,D_DAG=1 if not value else 2,
             native_assumptions=proof['assumed_edges'],selected_assumptions=proof['assumed_edges'] if accepted else None)
    run=dict(base=dict(candidates=[candidate],selections=[{'proof':proof if accepted else None}],
        packet=dict(document=dict(engine=dict(pending=dict(workspace={'routes':[{'path':[0,1]}]}))))))
    record=dict(final=final,readouts=[row])
    return run,record,c


def view_module():
    m=types.ModuleType('r041_scheduler_direction.trial_audit')
    m.candidate_view=lambda c:deepcopy(c['fixture_view'])
    return m


class TrajectoryTests(unittest.TestCase):
    def call(self,*args):
        with patch.dict(sys.modules,{'r041_scheduler_direction.trial_audit':view_module()}):return describe(*args)
    def test_readout_ID_invariance(self):
        a=self.call(*fixture());b=self.call(*fixture('fresh_ids'))
        self.assertEqual(a['canonical_readout_sha256'],b['canonical_readout_sha256'])
        self.assertEqual(a['final_support_signature'],b['final_support_signature'])
    def test_D_DAG_is_audited_depth_not_path_length(self):
        d=self.call(*fixture(value=False))
        self.assertEqual(d['final_support_signature']['D_DAG'],1)
        self.assertEqual(len(d['final_support_signature']['paths'][0]),2)
        self.assertIsNone(d['minimal_goal_proof_DAG_isomorphism'])
    def test_no_positive_adoption_signature_not_invented(self):
        d=self.call(*fixture(accepted=False));self.assertIsNone(d['final_support_signature'])
    def test_no_readout_is_null_not_equal_hash(self):
        run,record,case=fixture(accepted=False)
        run['base']['candidates']=[];record['readouts']=[]
        self.assertIsNone(self.call(run,record,case)['canonical_readout_sha256'])
    def test_unknown_proof_ID_rejected(self):
        run,record,case=fixture();run['base']['selections'][0]['proof']['assumed_edges'][0][0]='invented'
        with self.assertRaises(ValueError):self.call(run,record,case)
    def test_observation_mismatch_rejected(self):
        run,record,case=fixture();run['base']['candidates'][0]['fixture_view']['observation']['revision']=1
        with self.assertRaises(ValueError):self.call(run,record,case)
    def test_no_raw_mutation(self):
        args=fixture();before=digest(args[0]);self.call(*args);self.assertEqual(before,digest(args[0]))
    def test_missing_state_fails_instead_of_zero(self):
        run,record,case=fixture();del run['base']['candidates'][0]['fixture_view']['state']['goal']
        with self.assertRaises(KeyError):self.call(run,record,case)

if __name__=='__main__':unittest.main()
