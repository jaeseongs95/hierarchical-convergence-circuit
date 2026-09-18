from copy import deepcopy
from collections import Counter
import unittest
from r044_reuse_contribution import spec,input_audit,sources,storage as io
from r044_reuse_contribution.tests.fixtures import plan_fixture,full_parent_population

class Design(unittest.TestCase):
    def setUp(self):self.plan,self.parent,self.seed=plan_fixture()
    def check(self):return input_audit.check_plan_inputs(self.plan,self.parent,self.seed)
    def test_valid_frozen_input(self):self.assertTrue(self.check()['verified'])
    def test_population_is_12_pairs_24_trials(self):
        self.assertEqual(len(self.plan['trials']),24)
        self.assertEqual(Counter(t['case'] for t in self.plan['trials']),{c['name']:2 for c in self.plan['cases']})
    def test_pairs_only_gate_differs(self):
        for a,b in zip(self.plan['trials'][::2],self.plan['trials'][1::2]):
            self.assertNotEqual(a['use_circuits'],b['use_circuits'])
            self.assertEqual({k:v for k,v in a.items() if k not in ('id','use_circuits')},
                             {k:v for k,v in b.items() if k not in ('id','use_circuits')})
    def test_gate_first_counterbalance(self):
        self.assertEqual(Counter(t['use_circuits'] for t in self.plan['trials'][::2]),{True:6,False:6})
    def test_budget_unchanged(self):self.assertEqual(self.plan['conditions']['budget'],self.parent['conditions']['budget'])
    def test_no_empty_memory_substitution(self):
        self.seed['memory']={'circuits':[]}
        self.plan['memory_sha256']=self.parent['memory_sha256']=io.digest(self.seed['memory'])
        with self.assertRaises(ValueError):self.check()
    def test_integer_gate_rejected(self):
        self.plan['trials'][0]['use_circuits']=1
        with self.assertRaises(ValueError):self.check()
    def test_false_switch_repetition_rejected(self):
        self.plan['trials'][1]['use_circuits']=True
        with self.assertRaises(ValueError):self.check()
    def test_missing_trial(self):
        self.plan['trials'].pop()
        with self.assertRaises(ValueError):self.check()
    def test_scope_drift(self):
        self.plan['trials'][0]['scope']='legacy'
        with self.assertRaises(ValueError):self.check()
    def test_scheduler_drift(self):
        self.plan['trials'][0]['scheduler']='edge_id_min'
        with self.assertRaises(ValueError):self.check()
    def test_mutated_budget(self):
        self.plan['conditions']['budget']['max_advances']=99
        with self.assertRaises(ValueError):self.check()
    def test_input_score_mutation(self):
        self.plan['cases'][0]['observation']['edges'][0]['score']=.1
        with self.assertRaises(ValueError):self.check()
    def test_side_effect_free_inputs(self):
        h=io.digest([self.plan,self.parent,self.seed]);self.check();self.assertEqual(h,io.digest([self.plan,self.parent,self.seed]))
    def test_parent_regression_is_route_only_not_legacy(self):
        p,_=full_parent_population();ts=sources.parent_regression_trials(p)
        self.assertEqual(len(ts),6);self.assertTrue(all(t['scope']=='route_only' for t in ts))
    def test_parent_population_loss(self):
        p,_=full_parent_population();p['trials'].pop()
        with self.assertRaises(ValueError):sources.parent_regression_trials(p)
    def test_source_hash_conflict(self):
        with self.assertRaises(ValueError):sources.merge_hashes({'a':'x'},{'a':'y'})
    def test_claims_are_not_validity_requirements(self):
        c=spec.conditions(self.parent);self.assertTrue(c['efficacy_not_audit_requirement']);self.assertTrue(c['no_new_training'])
