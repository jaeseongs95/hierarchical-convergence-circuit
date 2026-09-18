from copy import deepcopy
import unittest
from r044_reuse_contribution import gate_audit as a,storage as io
from r044_reuse_contribution.tests.fixtures import state_fixture,event_fixture

class StateGate(unittest.TestCase):
    def test_enabled(self):self.assertTrue(a.check_states(*state_fixture(True))['verified'])
    def test_disabled_keeps_memory(self):self.assertTrue(a.check_states(*state_fixture(False))['memory_unchanged'])
    def test_memory_mutation(self):
        s,o,m,t=state_fixture();s[1]['memory']['circuits']=[]
        with self.assertRaises(ValueError):a.check_states(s,o,m,t)
    def test_other_switch_change(self):
        s,o,m,t=state_fixture();s[1]['switches']['top_down']=False
        with self.assertRaises(ValueError):a.check_states(s,o,m,t)
    def test_switch_drift(self):
        s,o,m,t=state_fixture();s[1]['switches']['use_circuits']=False
        with self.assertRaises(ValueError):a.check_states(s,o,m,t)
    def test_integer_switch_is_not_bool(self):
        s,o,m,t=state_fixture();s[0]['switches']['use_circuits']=1
        with self.assertRaises(ValueError):a.check_states(s,o,m,t)
    def test_legacy_scope_rejected(self):
        s,o,m,t=state_fixture();s[1].pop('prior_policy')
        with self.assertRaises(ValueError):a.check_states(s,o,m,t)
    def test_policy_seal(self):
        s,o,m,t=state_fixture();s[0]['prior_policy']['sha256']='invalid'
        with self.assertRaises(ValueError):a.check_states(s,o,m,t)
    def test_feedback_hidden(self):
        s,o,m,t=state_fixture();s[0]['feedback']={'hidden':True}
        with self.assertRaises(ValueError):a.check_states(s,o,m,t)
    def test_learning_counter(self):
        s,o,m,t=state_fixture();s[1]['pending']['cost']['learning_updates']=1
        with self.assertRaises(ValueError):a.check_states(s,o,m,t)
    def test_observation_mutation(self):
        s,o,m,t=state_fixture();s[1]['pending']['observation']['revision']=1
        with self.assertRaises(ValueError):a.check_states(s,o,m,t)
    def test_missing_generations(self):
        s,o,m,t=state_fixture();s[2]=s.pop(1)
        with self.assertRaises(ValueError):a.check_states(s,o,m,t)

class Events(unittest.TestCase):
    def setUp(self):self.r,self.t,self.c=event_fixture()
    def result(self):return a.measure_execution(self.r,self.t,self.c)
    def events(self):return self.r['base']['packet']['document']['events']
    def cost(self):return self.r['base']['packet']['document']['engine']['pending']['cost']
    def test_pool_decision_partition(self):
        d=self.result();self.assertEqual((d['pool_kernel_ticks'],d['decision_kernel_ticks']),(2,2))
        self.assertEqual(d['macro_actions'],1);self.assertEqual(d['macro_span_edge_items'],2)
    def test_primitive_only(self):
        r,t,c=event_fixture(False);d=a.measure_execution(r,t,c)
        self.assertEqual(d['pool_kernel_ticks'],0);self.assertEqual(d['primitive_actions'],1)
    def test_raw_unmodified(self):
        h=io.digest(self.r);self.result();self.assertEqual(io.digest(self.r),h)
    def test_unmeasured_remains_null(self):
        d=self.result();self.assertIsNone(d['energy_joules']);self.assertIsNone(d['process_peak_memory_bytes'])
    def test_disabled_binding(self):
        self.t['use_circuits']=False
        with self.assertRaises(ValueError):self.result()
    def test_tick_tamper(self):
        next(e for e in self.events() if e['event']=='r02_tick')['payload']['tick']=2
        with self.assertRaises(ValueError):self.result()
    def test_settle_tamper(self):
        next(e for e in self.events() if e['event']=='r02_settled')['payload']['convergence']['ticks']=3
        with self.assertRaises(ValueError):self.result()
    def test_counter_tamper(self):
        self.cost()['kernel_ticks']+=1
        with self.assertRaises(ValueError):self.result()
    def test_binding_count_tamper(self):
        self.cost()['binding_checks']+=1
        with self.assertRaises(ValueError):self.result()
    def test_recall_count_tamper(self):
        self.cost()['recall_checks']+=1
        with self.assertRaises(ValueError):self.result()
    def test_macro_count_tamper(self):
        self.cost()['circuit_reuses']=0
        with self.assertRaises(ValueError):self.result()
    def test_group_count_tamper(self):
        self.cost()['group_updates']+=1
        with self.assertRaises(ValueError):self.result()
    def test_signal_count_tamper(self):
        self.cost()['signal_transmissions']+=1
        with self.assertRaises(ValueError):self.result()
    def test_missing_measurement_is_error_not_zero(self):
        self.cost()['recall_checks']=None
        with self.assertRaises(ValueError):self.result()
    def test_judgment_prior_leak(self):
        next(e for e in self.events() if e['event']=='r02_network' and e['payload']['kind']=='decision')['payload']['drives']['goal']=1
        with self.assertRaises(ValueError):self.result()
    def test_unknown_network_kind(self):
        next(e for e in self.events() if e['event']=='r02_network')['payload']['kind']='oracle'
        with self.assertRaises(ValueError):self.result()
    def test_proposal_gate(self):
        next(e for e in self.events() if e['event']=='r02_proposals')['payload']['circuits_enabled']=False
        with self.assertRaises(ValueError):self.result()
    def test_multi_edge_primitive_rejected(self):
        p=next(e for e in self.events() if e['event']=='r02_expansion')['payload'];p['candidate']['source']='primitive'
        with self.assertRaises(ValueError):self.result()
    def test_unknown_macro_slot(self):
        p=next(e for e in self.events() if e['event']=='r02_expansion')['payload'];p['candidate']['edges']=[100]
        with self.assertRaises(ValueError):self.result()
    def test_unexpected_feedback(self):
        self.events().append({'seq':len(self.events()),'event':'r02_feedback','payload':{}})
        with self.assertRaises(ValueError):self.result()
