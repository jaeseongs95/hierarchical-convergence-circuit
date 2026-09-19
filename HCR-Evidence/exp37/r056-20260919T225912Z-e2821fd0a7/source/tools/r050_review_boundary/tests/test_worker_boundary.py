"""Mock-native boundary tests. These are not executions of the actual HCC engine."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch
from tools.r050_review_boundary import worker

class FakeSession:
    created=[]
    fail=False
    def __init__(self,cfg,memory,**kw):
        self.kw=kw;self.memory_document=memory;self.phase='idle';self.advances=0
        self.current={'pending':{'cost':{'kernel_ticks':0}}};self.created.append(self)
    def packet(self):
        return {'document':{'engine':{'switches':{k:self.kw[k] for k in ('use_circuits','top_down','allow_reexpansion')},
                                      'pending':deepcopy(self.current['pending'])}}}
    def begin(self,obs,mode):self.phase='running';self.obs=obs
    def advance(self):
        if self.fail:raise RuntimeError('first native failure fixture')
        self.advances+=1;self.current['pending']['cost']['kernel_ticks']+=20
        if self.advances==2:self.phase='readout_ready'

class WorkerBoundary(unittest.TestCase):
    def setUp(self):
        FakeSession.created=[];FakeSession.fail=False
        self.plan={'config':{},'empty_memory':{},'limits':{'max_advances_per_session':8,'max_kernel_ticks_per_session':1280}}
        self.case={'id':'fixture','top_down':False}
        codec=SimpleNamespace(adaptive_config_from=lambda x:SimpleNamespace(kernel=SimpleNamespace(max_ticks=160)),observation_from=deepcopy)
        self.fake=(codec,None,SimpleNamespace(FROZEN_EVAL='frozen_eval'),
                   SimpleNamespace(from_document=lambda d,cfg:d),FakeSession,
                   lambda s,g:{'fixture_only':True,'segment':g},None,None,None,None)
    def invoke(self,path,label='same_input_restart'):
        with patch.object(worker,'native',return_value=self.fake):
            return worker.execute_session(self.plan,self.case,{'revision':0},path,label,1)
    def test_restart_retains_top_down_off(self):
        with tempfile.TemporaryDirectory() as t:
            result=self.invoke(Path(t))
            self.assertIs(FakeSession.created[0].kw['top_down'],False)
            self.assertTrue(result['ready']);self.assertEqual(result['advances'],2)
    def test_frozen_mode_and_memory(self):
        with tempfile.TemporaryDirectory() as t:
            self.invoke(Path(t));s=FakeSession.created[0]
            self.assertEqual(s.memory_document,{})
            self.assertEqual(s.kw['judgment_prior'],'legacy')
    def test_budget_does_not_trigger_retry(self):
        self.plan['limits']['max_advances_per_session']=1
        with tempfile.TemporaryDirectory() as t:
            result=self.invoke(Path(t))
            self.assertFalse(result['ready']);self.assertIsNone(result['candidate'])
            self.assertEqual(result['stop'],'external_compute_budget')
            self.assertEqual(len(FakeSession.created),1)
    def test_exception_preserves_first_completed_snapshots(self):
        FakeSession.fail=True
        with tempfile.TemporaryDirectory() as t:
            with self.assertRaisesRegex(RuntimeError,'first native failure'):
                self.invoke(Path(t))
            self.assertTrue((Path(t)/'step-000-init.json').exists())
            self.assertTrue((Path(t)/'step-001-begin.json').exists())
            self.assertEqual(len(FakeSession.created),1)
    def test_captured_candidate_and_progress_are_separate(self):
        with tempfile.TemporaryDirectory() as t:
            self.invoke(Path(t))
            self.assertTrue((Path(t)/'candidate.json').exists())
            self.assertTrue((Path(t)/'step-003-advance.json').exists())
    def test_each_restart_is_new_session_not_continuation(self):
        with tempfile.TemporaryDirectory() as t:
            self.invoke(Path(t)/'a','echo_revision_restart');self.invoke(Path(t)/'b','strength_revision_restart')
            self.assertEqual(len(FakeSession.created),2)
            self.assertNotEqual(FakeSession.created[0].kw['session_id'],FakeSession.created[1].kw['session_id'])

if __name__=='__main__':unittest.main()
