from copy import deepcopy
from unittest.mock import patch
import unittest
from r041_scheduler_direction.runtime import ScheduledTimingTrial,ScheduledOnlineTrial
from r041_scheduler_direction.control_audit import audit_control
from r041_scheduler_direction.trial_audit import check_wrapper
from r041_scheduler_direction.contracts import Budget
from r041_scheduler_direction import scheduler
from fixtures import OBS,CONFIG,MEMORY,Backend,fake_selector_audit

class RuntimeAuditTests(unittest.TestCase):
    def run_one(self,arm='online_support',policy='edge_id_min',budget=None,backend=None):
        b=backend or Backend()
        t=ScheduledTimingTrial(OBS,CONFIG,MEMORY,'legacy',arm,budget,scheduler=policy,backend=b)
        run=t.run();audit_control(run['base'],b.session.states)
        check_wrapper(run,dict(arm=arm,scope='legacy'),view_of=b.project,selector_audit=fake_selector_audit)
        return t,run,b
    def test_all_nine_cells_audited(self):
        for policy in ('input_order','edge_id_min','edge_id_max'):
            for arm in ('native','posthoc_support','online_support'):
                with self.subTest(policy=policy,arm=arm):self.run_one(arm,policy)
    def test_input_order_never_reorders(self):
        _,r,b=self.run_one(policy='input_order');self.assertNotIn('prioritize_frontier',b.session.calls)
    def test_priority_committed_through_api(self):
        _,r,b=self.run_one();self.assertEqual(b.session.calls.count('prioritize_frontier'),1)
        self.assertEqual(r['base']['scheduler_usage']['priority_transitions'],1)
    def test_online_cost_synthetic_fixture(self):
        _,a,_=self.run_one(policy='input_order');_,b,_=self.run_one()
        self.assertEqual((a['usage']['native_kernel_ticks'],b['usage']['native_kernel_ticks']),(9,6))
        self.assertEqual(a['final']['value'],b['final']['value'])
    def test_posthoc_does_not_retroactively_save(self):
        _,r,_=self.run_one('posthoc_support');self.assertEqual(r['usage']['native_kernel_ticks'],9);self.assertTrue(r['final']['accepted'])
    def test_native_abstention_not_converted_by_scheduling(self):
        _,r,_=self.run_one('native');self.assertFalse(r['final']['accepted'])
    def test_first_readout_preserved(self):
        _,r,_=self.run_one();self.assertFalse(r['base']['candidates'][0]['readout']['accepted'])
        events=r['base']['events'];names=[e['event'] for e in events]
        self.assertLess(names.index('readout_committed'),names.index('selection_requested'))
    def test_zero_initial_budget_no_scheduling(self):
        _,r,_=self.run_one(budget=Budget(max_initial_advances=0))
        self.assertEqual(r['base']['scheduler_usage']['decision_calls'],0);self.assertEqual(r['base']['adoption']['reason'],'stop_initial_budget')
    def test_zero_extra_budget_no_priority(self):
        _,r,b=self.run_one(budget=Budget(max_extra_advances=0))
        self.assertEqual(r['base']['adoption']['reason'],'stop_compute_budget');self.assertNotIn('prioritize_frontier',b.session.calls)
    def test_selection_budget_preserved(self):
        _,r,_=self.run_one(backend=Backend(selection_budget=True));self.assertEqual(r['base']['adoption']['reason'],'stop_selection_budget')
    def test_raw_none_not_flipped(self):
        _,r,_=self.run_one(backend=Backend(raw=None));self.assertIsNone(r['final']['value'])
    def test_worker_cannot_retry(self):
        t,_,_=self.run_one()
        with self.assertRaises(ValueError):t.run()
    def test_selector_failure_keeps_original_candidate(self):
        t=ScheduledTimingTrial(OBS,CONFIG,MEMORY,'legacy','online_support',scheduler='edge_id_min',backend=Backend(selection_error=True))
        with self.assertRaises(RuntimeError):t.run()
        partial=t.partial_evidence();self.assertEqual(len(partial['native_partial']['candidates']),1)
    def test_choice_mutation_rejected(self):
        b=Backend();t=ScheduledTimingTrial(OBS,CONFIG,MEMORY,'legacy','online_support',scheduler='edge_id_min',backend=b)
        real=scheduler.choose
        def bad(v,p):
            x=real(v,p);v['edge_ids'].append('injected');return x
        with patch.object(scheduler,'choose',side_effect=bad),self.assertRaises(ValueError):t.run()
    def test_auditor_does_not_call_runtime_or_scheduler(self):
        _,r,b=self.run_one()
        with patch.object(scheduler,'choose',side_effect=AssertionError('production scheduler')), \
             patch.object(scheduler,'project',side_effect=AssertionError('production projection')), \
             patch.object(ScheduledOnlineTrial,'run',side_effect=AssertionError('production runtime')):
            self.assertTrue(audit_control(r['base'],b.session.states)['verified'])
    def test_scheduler_counter_tampering(self):
        _,r,b=self.run_one();r['base']['scheduler_usage']['edge_id_reads']+=1
        with self.assertRaises(ValueError):audit_control(r['base'],b.session.states)
    def test_choice_tampering(self):
        _,r,b=self.run_one()
        next(e for e in r['base']['events'] if e['event']=='schedule_decided')['decision']['selected_edge_ids']=['spoof']
        with self.assertRaises(ValueError):audit_control(r['base'],b.session.states)
    def test_priority_state_change_rejected(self):
        _,r,b=self.run_one();states=deepcopy(b.session.states)
        g=next(i for i,t in enumerate(b.session.transitions) if t['operation']=='prioritize_frontier')
        states[g]['pending']['cost']['kernel_ticks']+=1
        with self.assertRaises(ValueError):audit_control(r['base'],states)
    def test_priority_dependency_deletion_rejected(self):
        _,r,b=self.run_one();states=deepcopy(b.session.states)
        g=next(i for i,t in enumerate(b.session.transitions) if t['operation']=='prioritize_frontier')
        states[g]['pending']['workspace']['frontier'].pop()
        with self.assertRaises(ValueError):audit_control(r['base'],states)
    def test_hidden_tail_event_rejected(self):
        _,r,b=self.run_one();r['base']['events'].append({'event':'extra'})
        with self.assertRaises(ValueError):audit_control(r['base'],b.session.states)
    def test_different_scheduler_label_rejected(self):
        _,r,b=self.run_one();r['base']['scheduler']='input_order'
        with self.assertRaises(ValueError):audit_control(r['base'],b.session.states)
    def test_posthoc_result_tampering(self):
        _,r,b=self.run_one('posthoc_support');r['final']['value']=False
        with self.assertRaises(ValueError):check_wrapper(r,dict(arm='posthoc_support',scope='legacy'),view_of=b.project,selector_audit=fake_selector_audit)
