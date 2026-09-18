from copy import deepcopy
from dataclasses import asdict
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT/"src"),str(ROOT/"tools")]
import json,tempfile,unittest,io,contextlib,random
from hcr.model import Config
from r046_thought_carry import runtime,evaluator,spec,storage,protocol,reporting
from r046_thought_carry.contracts import ARMS,SCENARIOS,VARIANTS


class NativeCarryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg=asdict(Config());cls.aobs,cls.cases,cls.worlds=spec.observations(.85)
        cls.A={v:runtime.run_query(o,cls.cfg) for v,o in cls.aobs.items()}
        cls.results={}
        for c in cls.cases:
            for arm in ARMS:
                cls.results[c['id'],arm]=runtime.run_query(c['observation'],cls.cfg,arm,cls.A[c['variant']])
    def sample(self,sc='extend',arm='relation_carry',v='identity'):
        return deepcopy(self.results[sc+'__'+v,arm]),self.A[v]
    def test_native_A_audited(self):
        for a in self.A.values():self.assertTrue(evaluator.audit_record(a)['verified'])
    def test_source_record_is_not_mutated(self):
        a=deepcopy(self.A['identity']);before=storage.canonical(a)
        runtime.run_query(self.cases[0]['observation'],self.cfg,'relation_carry',a)
        self.assertEqual(before,storage.canonical(a))
    def test_goal_state_is_not_copied(self):
        r,_=self.sample(arm='state_carry');self.assertEqual(r['initial_state']['goal'],.5)
        self.assertNotIn('goal',[m['target_group'] for m in r['transfer_map']])
    def test_numeric_and_relation_arms_not_combined(self):
        r,_=self.sample();self.assertEqual(r['bridge_cost']['state_groups_written'],0)
        r,_=self.sample(arm='state_carry');self.assertEqual(r['bridge_cost']['proof_nodes_reused'],0)
    def test_reference_parent_is_actually_foreign(self):
        r,a=self.sample();foreign=set(r['proof_graph']['external_node_refs'])
        own={n['id'] for n in r['proof_graph']['nodes']}
        self.assertFalse(foreign&own)
        self.assertTrue(any(p in foreign for n in r['proof_graph']['nodes'] for p in n['parents']))
        self.assertIn(a['proof_graph']['final'],foreign)
    def test_unfolded_depth_preserved(self):
        r,a=self.sample();self.assertEqual(evaluator.audit_record(r,a)['proof']['D_DAG'],3)
        self.assertEqual(len(r['proof_graph']['nodes']),2)
    def test_ordinary_memo_not_value_only_strawman(self):
        m,_=self.sample(arm='proof_memo');r,_=self.sample()
        self.assertEqual(m['proof_graph'],r['proof_graph'])
        self.assertGreater(m['bridge_cost']['dependency_checks'],0)
    def test_no_change_to_native_program(self):
        for c in self.cases:
            r=self.results[c['id'],'cold']
            for arm in ARMS:
                q=self.results[c['id'],arm]
                self.assertEqual((r['program'],r['effective_drives']),(q['program'],q['effective_drives']))
    def test_partial_source_is_not_a_positive_relation(self):
        cfg=dict(self.cfg,max_ticks=4)
        a=runtime.run_query(self.aobs['identity'],cfg)
        self.assertTrue(a['censored']);self.assertFalse(a['accepted'])
        self.assertTrue(evaluator.audit_record(a)['verified'])
        r=runtime.run_query(self.cases[0]['observation'],cfg,'relation_carry',a)
        self.assertIsNone(r['carry_packet']);self.assertEqual(r['gate_reason'],'no_adopted_positive_source')
        self.assertTrue(evaluator.audit_record(r,a)['verified'])
    def test_zero_drive_boundary(self):
        from hcr.dynamics import settle
        from hcr.workspace import make_program
        from hcr.model import Cost
        p=make_program(2,((0,1),),Config());d={'e:0':3.68,'e:1':3.68,'goal':0.0}
        a=settle(p,d,Config(),Cost());b=settle(p,dict(d,**{'p:0:0':0.0,'p:0:1':0.0}),Config(),Cost())
        self.assertEqual(a,b);self.assertNotEqual(storage.digest(d),storage.digest(dict(d,**{'p:0:0':0.0,'p:0:1':0.0})))
    def test_changed_score_same_sign_invalidates_snapshot(self):
        o=deepcopy(self.cases[0]['observation']);o['edges'][1]['score']=.84
        r=runtime.run_query(o,self.cfg,'relation_carry',self.A['identity'])
        self.assertEqual(r['gate_reason'],'support_dependency_changed');evaluator.audit_record(r,self.A['identity'])
    def test_revision_only_does_not_invalidate(self):
        r,_=self.sample();self.assertTrue(r['gate_valid'])
        self.assertNotEqual(r['observation']['revision'],r['carry_packet']['origin_revision'])
    def test_same_edge_ID_different_endpoint(self):
        o=deepcopy(self.cases[0]['observation']);o['edges'][0]['target']='vv';o['edges'][1]['source']='vv'
        r=runtime.run_query(o,self.cfg,'relation_carry',self.A['identity'])
        self.assertEqual(r['gate_reason'],'support_dependency_changed');evaluator.audit_record(r,self.A['identity'])
    def test_new_episode_rejects(self):
        o=deepcopy(self.cases[0]['observation']);o['episode_id']='different'
        r=runtime.run_query(o,self.cfg,'proof_memo',self.A['identity'])
        self.assertEqual(r['gate_reason'],'episode_mismatch');evaluator.audit_record(r,self.A['identity'])
    def test_extra_branch_is_not_deleted(self):
        o=deepcopy(self.cases[0]['observation']);o['edges'].append(dict(id='direct',source='u',target='z',score=.9))
        r=runtime.run_query(o,self.cfg,'relation_carry',self.A['identity'])
        self.assertEqual(len(r['program']['paths']),2);evaluator.audit_record(r,self.A['identity'])
    def test_foreign_goal_never_substituted(self):
        r,a=self.sample(sc='different_subject');self.assertEqual(r['gate_reason'],'subject_mismatch')
        self.assertFalse(r['proof_graph']['external_node_refs']);evaluator.audit_record(r,a)
    def test_byte_invariance_is_not_assumed(self):
        a,_=self.sample(v='identity');b,_=self.sample(v='fresh_ids')
        self.assertNotEqual(a['bridge_cost']['export_bytes'],b['bridge_cost']['export_bytes'])
    def test_truth_field_is_rejected(self):
        o=dict(self.aobs['identity'],truth=True)
        with self.assertRaises(ValueError):runtime.run_query(o,self.cfg)
    def test_no_automatic_retry_after_callback_failure(self):
        n=[]
        def emit(e):
            n.append(e)
            if e['event']=='network':raise RuntimeError('injected sink failure')
        with self.assertRaises(RuntimeError):runtime.run_query(self.aobs['identity'],self.cfg,event_sink=emit)
        self.assertEqual(sum(x['event']=='begin' for x in n),1)
    def test_native_path_budget_is_recorded(self):
        cfg=dict(self.cfg,max_search=1)
        r=runtime.run_query(self.aobs['identity'],cfg);self.assertTrue(r['censored'])
        self.assertTrue(evaluator.audit_record(r)['verified'])
    def test_forged_budget_is_rejected(self):
        r,a=self.sample();r.update(program=None,censored=True,reason='path_budget',accepted=False)
        with self.assertRaises(ValueError):evaluator.audit_record(r,a)
    def test_raw_stream_and_report_pipeline_smoke(self):
        plan=dict(sources=self.aobs,cases=self.cases,worlds=self.worlds,trials=spec.trial_order(),kernel_config=self.cfg)
        with tempfile.TemporaryDirectory() as tmp,contextlib.redirect_stdout(io.StringIO()):
            root=Path(tmp);protocol.produce(plan,root)
            a,r,checks,_,_=protocol.record_audit(plan,root)
            s=reporting.summarize(plan,a,r,checks)
            self.assertEqual(len(s['trials']),24);self.assertEqual(len(s['memo_controls']),6)
            for name in ('trials','pairs','ID_controls','proof_refs'):self.assertTrue(reporting.csv_bytes(s[name]))
            self.assertIn('EXP-27',reporting.render(s).decode())
            with self.assertRaises(FileExistsError):protocol.produce(plan,root)
    def test_storage_duplicate_and_nonfinite(self):
        for s in ['{"x":1,"x":2}','{"x":NaN}','{"x":1e999}']:
            with self.assertRaises(ValueError):storage.loads(s)
    def test_storage_path_traversal(self):
        with tempfile.TemporaryDirectory() as t:
            for n in ['../bad','/bad','a//b','a/./b','C:/foo','a\\b']:
                with self.assertRaises(ValueError):storage.child(t,n)
    def test_storage_never_overwrites(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'raw.json';storage.put(p,{'first':1})
            with self.assertRaises(FileExistsError):storage.put(p,{'second':2})
            self.assertEqual(storage.load(p),{'first':1})



    def test_candidate_precedes_native_decision(self):
        r,_=self.sample();candidate=next(e for e in r['events'] if e['event']=='relation_candidate')
        first_tick=next(e for e in r['events'] if e['event']=='tick')
        self.assertIsNotNone(r['pre_decision_candidate'])
        self.assertLess(candidate['ordinal'],first_tick['ordinal'])
    def test_candidate_builder_does_not_take_B_state(self):
        import inspect
        self.assertNotIn('state',inspect.signature(runtime._compose_candidate).parameters)
    def test_candidate_preserved_when_verifier_budget_expires(self):
        cfg=dict(self.cfg,max_ticks=35)
        a=runtime.run_query(self.aobs['identity'],cfg)
        self.assertTrue(a['accepted'])
        r=runtime.run_query(self.cases[0]['observation'],cfg,'relation_carry',a)
        self.assertIsNotNone(r['pre_decision_candidate']);self.assertTrue(r['censored'])
        self.assertFalse(r['accepted']);self.assertGreater(r['bridge_cost']['candidate_discarded_nodes'],0)
        self.assertTrue(evaluator.audit_record(r,a)['verified'])
    def test_forged_predecision_candidate_rejected(self):
        r,a=self.sample();r['pre_decision_candidate']['nodes'][1]['parents'][0]='nonexistent'
        with self.assertRaises(ValueError):evaluator.audit_record(r,a)


def make_case_test(scenario,variant,arm):
    def test(self):
        r=self.results[scenario+'__'+variant,arm];a=self.A[variant]
        report=evaluator.audit_record(r,a,self.worlds[scenario+'__'+variant])
        self.assertTrue(report['verified'])
        # Mechanics only: correctness/efficiency remains a research outcome.
        self.assertEqual(report['native_ticks_replayed'],len(r['ticks']))
    return test
for sc in SCENARIOS:
    for v in VARIANTS:
        for arm in ARMS:setattr(NativeCarryTests,f'test_native_replay_{sc}_{v}_{arm}',make_case_test(sc,v,arm))


def mut_test(mutate,sc='extend',arm='relation_carry'):
    def test(self):
        r,a=self.sample(sc,arm);mutate(r)
        with self.assertRaises((ValueError,KeyError,TypeError)):evaluator.audit_record(r,a)
    return test
mutations={
 'tick_state':lambda r:r['ticks'][0]['state'].__setitem__('goal',.123),
 'tick_residual':lambda r:r['ticks'][0].__setitem__('residual',.9),
 'counter':lambda r:r['native_cost'].__setitem__('group_updates',0),
 'support_cost':lambda r:r['bridge_cost'].__setitem__('support_checks',999),
 'source_identity':lambda r:r.__setitem__('source_sha256','0'*64),
 'depth':lambda r:r['proof_graph'].__setitem__('primitive_depth',1),
 'foreign_parent':lambda r:r['proof_graph']['nodes'][1]['parents'].__setitem__(0,'nonexistent'),
 'cycle':lambda r:r['proof_graph']['nodes'][1]['parents'].__setitem__(0,r['proof_graph']['nodes'][1]['id']),
 'duplicate_node':lambda r:r['proof_graph']['nodes'].append(deepcopy(r['proof_graph']['nodes'][0])),
 'same_value_wrong_term':lambda r:r['carry_packet']['term'].__setitem__('arguments',['p','q']),
 'origin':lambda r:r['carry_packet'].__setitem__('origin_record_sha256','0'*64),
 'predicate':lambda r:r['carry_packet']['term'].__setitem__('predicate','friend_of'),
 'dependency_score':lambda r:r['carry_packet']['dependencies'][0].__setitem__('score',-.9),
 'drive':lambda r:r['raw_drives'].__setitem__('goal',1.0),
 'program_link':lambda r:r['program']['links'][0].__setitem__('weight',3.0),
 'adoption':lambda r:r.__setitem__('accepted',False),
 'censored':lambda r:r.__setitem__('censored',True),
 'event_hidden':lambda r:r['events'].pop(),
 'final_state':lambda r:r['final_state'].__setitem__('goal',.1),
 'gate':lambda r:r.__setitem__('gate_valid',False),
 'false_byte_count':lambda r:r['bridge_cost'].__setitem__('import_bytes',0),
 'references':lambda r:r['proof_graph'].__setitem__('external_node_refs',[]),
 'raw_value':lambda r:r.__setitem__('raw_value',False),
}
for name,mutation in mutations.items():setattr(NativeCarryTests,'test_audit_rejects_'+name,mut_test(mutation))

if __name__=='__main__':unittest.main(failfast=True)
