import inspect
from copy import deepcopy
import unittest
from r037_online_selection.contracts import Budget, ContractError
from r037_online_selection.runtime import OnlineTrial
from r037_online_selection.control_audit import audit_control
from helpers import FakeBackend, OBS, CONFIG, MEMORY


class RuntimeTests(unittest.TestCase):
    def make(self, policy='support_first', frames=None, budget=None, **kwargs):
        backend=FakeBackend(frames,**kwargs)
        worker=OnlineTrial(OBS,CONFIG,MEMORY,'legacy',policy,budget,backend=backend)
        return worker,backend

    def test_online_support_stops_on_adoption(self):
        worker,backend=self.make();r=worker.run()
        self.assertTrue(r['adoption']['accepted']);self.assertEqual(r['usage']['extra_kernel_ticks'],3)
        self.assertEqual(backend.session.calls,['advance','continue_dependency','advance'])
        self.assertTrue(audit_control(r,backend.session.states)['verified'])

    def test_native_policy_does_not_adopt_support_proof(self):
        worker,backend=self.make('native_saved');r=worker.run()
        self.assertFalse(r['adoption']['accepted']);self.assertEqual(r['adoption']['reason'],'stop_frontier_exhausted')
        audit_control(r,backend.session.states)

    def test_first_candidate_not_replaced(self):
        worker,backend=self.make();r=worker.run()
        self.assertFalse(r['candidates'][0]['readout']['accepted'])
        self.assertFalse(r['candidates'][1]['readout']['accepted'])
        self.assertTrue(r['selections'][1]['accepted'])

    def test_native_success_no_further_work(self):
        worker,backend=self.make('native_saved',[dict(native=True,support=True,frontier=True)])
        r=worker.run();self.assertEqual(len(r['candidates']),1);self.assertEqual(r['usage']['extra_advances'],0)
        audit_control(r,backend.session.states)

    def test_policy_is_checked_even_when_native_accepts(self):
        worker,backend=self.make('support_first',[dict(native=True,support=False,frontier=False)])
        r=worker.run();self.assertEqual(backend.policies,['support_first']);self.assertFalse(r['adoption']['accepted'])

    def test_zero_initial_advance_budget_is_not_fake_abstention(self):
        worker,backend=self.make(budget=Budget(max_initial_advances=0));r=worker.run()
        self.assertEqual(r['candidates'],[]);self.assertEqual(r['adoption']['reason'],'stop_initial_budget')
        self.assertFalse(r['terminal_pending_ready']);audit_control(r,backend.session.states)

    def test_initial_tick_reservation_before_work(self):
        worker,backend=self.make(budget=Budget(max_initial_kernel_ticks=4));r=worker.run()
        self.assertEqual(backend.session.calls,[]);audit_control(r,backend.session.states)

    def test_exact_tick_reservation_is_allowed(self):
        worker,backend=self.make(frames=[dict(native=True,support=True)],budget=Budget(max_initial_kernel_ticks=5))
        r=worker.run();self.assertTrue(r['adoption']['accepted']);audit_control(r,backend.session.states)

    def test_zero_extra_budget_preserves_first_failure(self):
        worker,backend=self.make(budget=Budget(max_extra_advances=0));r=worker.run()
        self.assertEqual(len(r['candidates']),1);self.assertEqual(r['adoption']['reason'],'stop_compute_budget')
        self.assertEqual(r['usage']['extra_advances'],0);audit_control(r,backend.session.states)

    def test_extra_ticks_reservation(self):
        worker,backend=self.make(budget=Budget(max_extra_kernel_ticks=4));r=worker.run()
        self.assertEqual(backend.session.calls,['advance']);audit_control(r,backend.session.states)

    def test_unfinished_terminal_not_last_readout(self):
        frames=[dict(frontier=True),dict(ready=False,frontier=True),dict(support=True)]
        worker,backend=self.make(frames=frames,budget=Budget(max_extra_advances=1));r=worker.run()
        self.assertEqual(len(r['candidates']),1);self.assertFalse(r['terminal_pending_ready'])
        self.assertEqual(r['usage']['extra_kernel_ticks'],3);audit_control(r,backend.session.states)

    def test_selection_budget_stops_without_extra_graph(self):
        for reason in ('ranking_budget','scan_budget','proof_budget'):
            with self.subTest(reason=reason):
                worker,backend=self.make(frames=[dict(reason=reason,frontier=True)])
                r=worker.run();self.assertEqual(r['adoption']['reason'],'stop_selection_budget')
                self.assertEqual(r['usage']['extra_advances'],0);audit_control(r,backend.session.states)

    def test_engine_failure_is_not_budget(self):
        worker,backend=self.make(frames=[dict(failure='native_failure',frontier=True)])
        r=worker.run();self.assertEqual(r['adoption']['reason'],'stop_engine_failure');audit_control(r,backend.session.states)

    def test_running_engine_failure(self):
        worker,backend=self.make(frames=[dict(ready=False,failure='native_failure')])
        r=worker.run();self.assertEqual(r['candidates'],[]);audit_control(r,backend.session.states)

    def test_selection_error_preserves_raw_first_attempt(self):
        worker,backend=self.make(selection_error=True)
        with self.assertRaises(RuntimeError):worker.run()
        partial=worker.partial_evidence();self.assertEqual(len(partial['candidates']),1)
        self.assertEqual(partial['events'][-1]['event'],'selection_requested')
        self.assertEqual(backend.policies,['support_first'])

    def test_runtime_error_preserves_committed_packet(self):
        worker,backend=self.make(frames=[{'raise':'native fail'}])
        with self.assertRaises(RuntimeError):worker.run()
        self.assertIsNotNone(worker.partial_evidence()['packet'])
        self.assertEqual(worker.events[-1]['event'],'work_requested')

    def test_single_use(self):
        worker,_=self.make();worker.run()
        with self.assertRaises(ContractError):worker.run()

    def test_selector_mutation_is_not_repaired(self):
        worker,_=self.make(mutation=True)
        with self.assertRaises(ContractError):worker.run()
        self.assertEqual(len(worker.partial_evidence()['candidates']),1)

    def test_capture_mutation_is_rejected(self):
        worker,_=self.make(capture_mutation=True)
        with self.assertRaises(ContractError):worker.run()

    def test_advance_over_budget_is_contract_failure(self):
        worker,_=self.make(frames=[dict(ticks=6)])
        with self.assertRaises(ContractError):worker.run()

    def test_negative_raw_passthrough(self):
        worker,backend=self.make(frames=[dict(raw=False,native=True,support=False)])
        r=worker.run();self.assertIs(r['adoption']['value'],False);audit_control(r,backend.session.states)

    def test_none_raw_is_not_fabricated(self):
        worker,backend=self.make(frames=[dict(raw=None,native=False,support=True)])
        r=worker.run();self.assertIsNone(r['adoption']['value']);audit_control(r,backend.session.states)

    def test_policy_pair_has_same_session_identity(self):
        a,_=self.make('native_saved');b,_=self.make('support_first')
        x=a.run();y=b.run();self.assertEqual(x['packet']['document']['session_id'],y['packet']['document']['session_id'])
        self.assertEqual(x['candidates'][0],y['candidates'][0])

    def test_input_deep_copy(self):
        obs=deepcopy(OBS);memory=deepcopy(MEMORY)
        worker=OnlineTrial(obs,CONFIG,memory,'legacy','support_first',backend=FakeBackend())
        obs['edges'][0]['score']=-1;memory['circuits'].append({'changed':True})
        worker.run();self.assertEqual(worker.observation,OBS);self.assertEqual(worker.memory,MEMORY)

    def test_public_api_excludes_truth_and_case(self):
        names=set(inspect.signature(OnlineTrial.__init__).parameters)
        self.assertFalse(names & {'case','world','truth','expected','case_name','diagnostic'})

    def test_memory_mutation_rejected(self):
        worker,backend=self.make(frames=[dict(native=True,support=True)])
        original=backend.select
        def bad(*args):
            value=original(*args);backend.session._current['memory']['changed']=1;return value
        backend.select=bad
        with self.assertRaises(ContractError):worker.run()

    def test_sink_records_first_before_selection(self):
        worker,_=self.make();events=[];worker.event_sink=events.append;r=worker.run()
        self.assertEqual(events,r['events']);names=[e['event'] for e in events]
        self.assertLess(names.index('readout_committed'),names.index('selection_requested'))
