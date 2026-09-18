from copy import deepcopy
import random
import unittest
from unittest.mock import patch
from r037_online_selection.control_audit import audit_control
from r038_early_adoption.contracts import Budget,ARMS,digest
from r038_early_adoption.runtime import TimingTrial
from r038_early_adoption.audit import check_wrapper
from r038_early_adoption.tests._support import FakeBackend,OBS,CONFIG,MEMORY,frames,fake_audit


def run_arm(arm,fs=None,budget=None,backend=None,sink=None):
    b = backend if backend is not None else FakeBackend(frames() if fs is None else fs)
    w = TimingTrial(OBS,CONFIG,MEMORY,'legacy',arm,budget,backend=b,event_sink=sink)
    return w,w.run(),b


class RuntimeTests(unittest.TestCase):
    def test_three_arms_split_output_and_work(self):
        result = {a:run_arm(a)[1] for a in ARMS}
        self.assertIsNone(result['native']['final']['value'])
        self.assertTrue(result['posthoc_support']['final']['value'])
        self.assertTrue(result['online_support']['final']['value'])
        self.assertEqual([result[a]['usage']['native_kernel_ticks'] for a in ARMS],[9,9,6])

    def test_posthoc_does_not_change_base_flow(self):
        _,a,ab = run_arm('native'); _,b,bb = run_arm('posthoc_support')
        self.assertEqual(ab.session.calls,bb.session.calls)
        self.assertEqual(a['base']['packet'],b['base']['packet'])
        self.assertEqual(a['base']['candidates'],b['base']['candidates'])

    def test_original_first_candidate_preserved(self):
        runs = [run_arm(a)[1] for a in ARMS]
        self.assertTrue(all(r['base']['candidates'][0] == runs[0]['base']['candidates'][0] for r in runs))
        self.assertFalse(runs[-1]['base']['selections'][0]['accepted'])

    def test_online_does_not_execute_tail(self):
        _,r,b = run_arm('online_support',frames()[:2]+[{'raise':'must not run'}])
        self.assertTrue(r['final']['accepted']); self.assertEqual(b.session.calls,['advance','continue_dependency','advance'])

    def test_no_remaining_frontier_has_no_work_saving(self):
        _,a,_ = run_arm('posthoc_support',frames(False)); _,b,_ = run_arm('online_support',frames(False))
        self.assertEqual(a['usage']['native_kernel_ticks'],b['usage']['native_kernel_ticks'])

    def test_no_supported_frame_stays_abstained(self):
        for arm in ARMS:
            _,r,_ = run_arm(arm,[dict(native=False,support=False,frontier=False)])
            self.assertIsNone(r['final']['value'])

    def test_initial_budget_does_not_fabricate_readout(self):
        _,r,b = run_arm('posthoc_support',budget=Budget(max_initial_advances=0))
        self.assertEqual(r['posthoc_status'],'no_readout'); self.assertFalse(r['base']['candidates'])
        self.assertFalse(b.policies); self.assertIsNone(r['final']['value'])

    def test_incomplete_terminal_cannot_use_last_readout(self):
        fs=[dict(native=False,support=True,frontier=True),dict(ready=False,frontier=True)]
        _,r,b = run_arm('posthoc_support',fs,budget=Budget(max_extra_advances=1))
        self.assertEqual(r['posthoc_status'],'terminal_incomplete')
        self.assertEqual(len(r['base']['candidates']),1); self.assertEqual(b.policies,['native_saved'])
        self.assertFalse(r['final']['accepted'])

    def test_engine_failure_disables_posthoc_adoption(self):
        _,r,_ = run_arm('posthoc_support',[dict(failure='synthetic_failure',native=False,support=True)])
        self.assertEqual(r['posthoc_status'],'engine_failure'); self.assertFalse(r['final']['accepted'])

    def test_raw_false_passthrough(self):
        for arm in ARMS:
            _,r,_ = run_arm(arm,[dict(raw=False,native=True,support=True)])
            self.assertIs(r['final']['value'],False)

    def test_raw_none_not_changed(self):
        for arm in ARMS:
            _,r,_ = run_arm(arm,[dict(raw=None,native=True,support=True)])
            self.assertIsNone(r['final']['value'])

    def test_retry_is_rejected(self):
        w,r,b = run_arm('online_support'); before=len(b.session.calls)
        with self.assertRaises(ValueError): w.run()
        self.assertEqual(len(b.session.calls),before)

    def test_first_candidate_logged_before_posthoc(self):
        events=[]; _,r,_=run_arm('posthoc_support',sink=events.append)
        base_end=next(i for i,e in enumerate(events) if e['event']=='base_completed')
        post_start=next(i for i,e in enumerate(events) if e['event']=='posthoc_action')
        self.assertLess(base_end,post_start)
        self.assertEqual(events[-1]['event'],'arm_finished')

    def test_no_learning_or_input_mutation(self):
        original=deepcopy((OBS,CONFIG,MEMORY)); _,r,b=run_arm('posthoc_support')
        self.assertEqual((OBS,CONFIG,MEMORY),original)
        self.assertEqual(b.session.current['memory'],MEMORY)

    def test_private_fields_not_accepted(self):
        bad=dict(OBS,external_truth=True)
        with self.assertRaises(ValueError): TimingTrial(bad,CONFIG,MEMORY,'legacy','native',backend=FakeBackend())

    def test_unknown_arm_rejected(self):
        with self.assertRaises(ValueError): TimingTrial(OBS,CONFIG,MEMORY,'legacy','oracle',backend=FakeBackend())

    def test_native_failure_preserves_first_evidence(self):
        events=[]; b=FakeBackend([dict(native=False,support=False,frontier=True),{'raise':'native synthetic error'}])
        w=TimingTrial(OBS,CONFIG,MEMORY,'legacy','native',backend=b,event_sink=events.append)
        with self.assertRaises(RuntimeError): w.run()
        self.assertEqual(len(w.partial_evidence()['native_partial']['candidates']),1)
        self.assertTrue(any(e['event']=='native_action' and e['record']['event']=='readout_committed' for e in events))

    def test_posthoc_failure_retains_base(self):
        class Broken(FakeBackend):
            def select(self,v,p,l):
                if p=='support_first': raise RuntimeError('posthoc synthetic failure')
                return super().select(v,p,l)
        w=TimingTrial(OBS,CONFIG,MEMORY,'legacy','posthoc_support',backend=Broken(frames()))
        with self.assertRaises(RuntimeError): w.run()
        partial=w.partial_evidence()
        self.assertIsNotNone(partial['base']); self.assertEqual(len(partial['posthoc_events']),1)

    def test_posthoc_mutation_rejected(self):
        class Broken(FakeBackend):
            def select(self,v,p,l):
                r=super().select(v,p,l)
                if p=='support_first': v['raw_value']=False
                return r
        with self.assertRaises(ValueError): run_arm('posthoc_support',backend=Broken(frames()))

    def test_posthoc_raw_flip_rejected(self):
        class Broken(FakeBackend):
            def select(self,v,p,l):
                r=super().select(v,p,l)
                if p=='support_first': r['value']=False
                return r
        with self.assertRaises(ValueError): run_arm('posthoc_support',backend=Broken(frames()))

    def test_posthoc_null_counter_rejected(self):
        class Broken(FakeBackend):
            def select(self,v,p,l):
                r=super().select(v,p,l)
                if p=='support_first': r['usage']['edge_checks']=None
                return r
        with self.assertRaises(ValueError): run_arm('posthoc_support',backend=Broken(frames()))

    def test_wrapper_recomputed_without_runtime(self):
        for arm in ARMS:
            _,r,b=run_arm(arm)
            with patch.object(TimingTrial,'run',side_effect=AssertionError('production call')):
                self.assertTrue(check_wrapper(r,dict(arm=arm,scope='legacy'),view_of=b.project,selector_audit=fake_audit)['verified'])
                self.assertTrue(audit_control(r['base'],b.session.states)['verified'])

    def test_tampered_final_and_usage_rejected(self):
        _,r,b=run_arm('posthoc_support')
        for key in ('final','usage','posthoc_status','posthoc_events'):
            bad=deepcopy(r)
            if key=='final': bad[key]['value']=False
            elif key=='usage': bad[key]['native_kernel_ticks']+=1
            elif key=='posthoc_status': bad[key]='not_applicable'
            else: bad[key].reverse()
            with self.subTest(key=key),self.assertRaises(ValueError):
                check_wrapper(bad,dict(arm='posthoc_support',scope='legacy'),view_of=b.project,selector_audit=fake_audit)

    def test_seeded_synthetic_boundary_grid(self):
        rng=random.Random(3819)
        for index in range(100):
            fs=[dict(native=False,support=bool(rng.randrange(2)),frontier=True) for _ in range(3)]
            fs[-1]['frontier']=False
            for arm in ARMS:
                budget=Budget(max_initial_advances=rng.randrange(2),max_extra_advances=rng.randrange(3))
                _,r,b=run_arm(arm,fs,budget)
                with self.subTest(index=index,arm=arm):
                    self.assertTrue(audit_control(r['base'],b.session.states)['verified'])
                    self.assertTrue(check_wrapper(r,dict(arm=arm,scope='legacy'),view_of=b.project,selector_audit=fake_audit)['verified'])
