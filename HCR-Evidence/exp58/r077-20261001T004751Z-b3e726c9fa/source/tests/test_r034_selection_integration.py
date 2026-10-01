"""실제 저장소 엔진 통합 회귀. synthetic oracle로 엔진을 대체하지 않는다.

R0.3.3 전체 소스가 설치된 프로젝트에서 hcr.py check로 실행한다.
이 파일은 독립 selection unit-test 결과와 별도로 보고해야 한다.
"""
from copy import deepcopy
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from hcr import codec
from hcr.model import AdaptiveConfig, Feedback, Mode
from hcr.circuits import AdaptiveMemory
from hcr.sessions import AdaptiveSession
from hcr.review import prepare_baseline, ReviewLimits, ReviewFlow
from hcr.selection import SelectionLimits
from hcr.selection_runtime import SelectionFlow,prepare_running
from hcr.evaluation.selection_audit import audit_flow,SelectionAuditError
from hcr.evaluation.selection_spec import cases,computation_cases
from hcr.evaluation.prior_spec import training_world
from hcr.evaluation.reference import assess


class RealEngineSelectionIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg=AdaptiveConfig();s=AdaptiveSession(cls.cfg,session_id='r034-integration-training')
        for i in range(6):
            w=training_world(i);s.begin(w.observation,Mode.TRAIN);d=s.complete();a=assess(d,w.observation,dict(w.hidden))
            if a.correct is not True:raise AssertionError('original training fixture failed')
            s.feedback(Feedback('f-'+d.id,d.id,w.observation.digest,a.correct,a.proof_valid and a.assumption_correct is True))
        cls.memory=s.memory_document;cls.case_map={c['name']:c for c in cases()};cls.bases={}

    def baseline(self,name,scope='legacy'):
        key=name,scope
        if key not in self.bases:
            obs=codec.observation_from(self.case_map[name]['observation'])
            self.bases[key]=prepare_baseline(obs,self.cfg,AdaptiveMemory.from_document(self.memory,self.cfg),judgment_prior=scope)
        return deepcopy(self.bases[key])

    def run_arm(self,name,arm,scope='legacy',**kw):
        b=self.baseline(name,scope);before=deepcopy(b)
        r=SelectionFlow(b,arm,**kw).run();self.assertEqual(b,before)
        self.assertTrue(audit_flow(b,r)['verified']);return b,r

    def test_original_fixtures_preserved(self):
        from hcr.evaluation.grounding_spec import fixtures
        old={c['name']:c for c in fixtures()}
        self.assertEqual(cases(),[old[c['name']] for c in cases()])

    def test_hold_matches_exp14(self):
        b,r=self.run_arm('weak_negative','hold')
        old=ReviewFlow(b,'hold').run()
        self.assertEqual(r['result']['value'],old['result']['value'])
        self.assertEqual(r['candidates'][0],old['candidates'][0])

    def test_expansion_keeps_original_readout(self):
        b,r=self.run_arm('irrelevant_missing','expand_only')
        old=ReviewFlow(b,'expand_only').run()
        self.assertEqual(r['result']['value'],old['result']['value'])
        self.assertEqual(r['usage']['extra_kernel_ticks'],old['usage']['extra_kernel_ticks'])
        self.assertEqual(r['candidates'][-1]['decision']['proof'],old['candidates'][-1]['decision']['proof'])

    def test_same_policy_restart_is_explicit(self):
        b,r=self.run_arm('weak_negative','restart_same')
        self.assertEqual(r['usage']['restarts'],1)
        self.assertEqual(r['candidates'][0]['decision']['value'],r['candidates'][-1]['decision']['value'])
        self.assertIsNone(r['result']['value'])

    def test_route_restart_changes_prior_not_memory(self):
        b,r=self.run_arm('weak_negative','restart_route_only')
        self.assertIs(r['result']['value'],False)
        self.assertEqual(r['usage']['restarts'],1)
        self.assertEqual(r['segments'][-1]['document']['engine']['memory'],self.memory)

    def test_selection_alone_does_not_invent_path(self):
        b,r=self.run_arm('irrelevant_missing','select_only')
        self.assertIsNone(r['result']['value']);self.assertEqual(r['usage']['extra_advances'],0)
        self.assertEqual(r['candidates'][0],b['first'])

    def test_expansion_then_selection_is_new_candidate(self):
        b,r=self.run_arm('irrelevant_missing','expand_then_select')
        # 새 가설의 결과는 raw 실험에서 판정한다. 이 회귀는 성공을 강요하지 않고 개입 계약을 검사한다.
        self.assertGreaterEqual(r['usage']['selection_calls'],1)
        self.assertEqual(r['candidates'][0],b['first'])
        self.assertEqual(r['segments'][0]['document']['engine']['memory'],self.memory)
        if r['result']['origin']=='selection':
            self.assertIs(r['result']['value'],True)
            self.assertNotEqual(r['result']['candidate_id'],b['first']['candidate_id'])
            self.assertGreater(r['usage']['proof_nodes'],0)

    def test_no_information_is_fabricated(self):
        for arm in ('select_only','expand_then_select','restart_same','restart_route_only'):
            b,r=self.run_arm('critical_missing',arm)
            self.assertIsNone(r['result']['value'])

    def test_observation_reference_audited(self):
        from hcr.evaluation.review_spec import provider_for
        b=self.baseline('critical_missing');case=self.case_map['critical_missing'];world=case['worlds']['first_closed']
        r=SelectionFlow(b,'observe_first').run(provider_for(case['observation'],world,'perfect'))
        self.assertTrue(audit_flow(b,r,world=world)['verified'])
        self.assertIs(r['reference']['result']['value'],False)

    def test_running_control_is_not_fake_first_decision(self):
        c=computation_cases()[0]
        b=prepare_running(codec.observation_from(c['observation']),self.cfg,AdaptiveMemory.from_document(self.memory,self.cfg))
        self.assertIsNone(b['first'])
        r=SelectionFlow(b,'continue').run();self.assertTrue(audit_flow(b,r)['verified'])
        self.assertIs(r['result']['value'],True);self.assertEqual(r['usage']['selection_calls'],0)

    def test_running_budget_exhaustion(self):
        c=computation_cases()[1]
        b=prepare_running(codec.observation_from(c['observation']),self.cfg,AdaptiveMemory.from_document(self.memory,self.cfg))
        r=SelectionFlow(b,'continue',limits=ReviewLimits(max_extra_advances=1)).run()
        self.assertTrue(audit_flow(b,r)['verified']);self.assertIsNone(r['result']['value'])

    def test_memory_correction_is_rejected_by_auditor(self):
        b,r=self.run_arm('weak_negative','hold');r['segments'][0]['document']['engine']['memory']['version']+=1
        with self.assertRaises(ValueError):audit_flow(b,r)

    def test_controller_tampering_is_rejected(self):
        b,r=self.run_arm('irrelevant_missing','select_only');r['actions'][0]['action']='restart'
        with self.assertRaises(ValueError):audit_flow(b,r)

    def test_single_use(self):
        flow=SelectionFlow(self.baseline('strong_positive'),'hold');flow.run()
        with self.assertRaises(ValueError):flow.run()


if __name__=='__main__':unittest.main(verbosity=2)
