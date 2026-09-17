from copy import deepcopy
import unittest
from unittest.mock import patch
from r035_frozen_selection.selection import run_policy
from r035_frozen_selection.audit import audit_result
from r035_frozen_selection.contracts import Limits
from r038_early_adoption.metrics import assumption_counts
from r039_order_isolation import trajectory
from r039_order_isolation.tests._fixtures import cases,view,trajectory_fixture


class SelectorMappingTests(unittest.TestCase):
    def test_all_six_fixed_id_permutations(self):
        for c in cases():
            with self.subTest(order=c['name']):
                v=view(c['observation']);before=deepcopy(v)
                out=run_policy(v,'support_first');report=audit_result(v,out)
                self.assertTrue(report['verified']);self.assertTrue(out['accepted']);self.assertEqual(v,before)
                self.assertEqual(out['proof']['assumed_edges'],[['e0',True],['e1',True]])
                self.assertEqual(report['D_DAG'],2)
    def test_native_missing_proof_stays_missing(self):
        for c in cases():
            v=view(c['observation']);out=run_policy(v,'native_saved');audit_result(v,out)
            self.assertFalse(out['accepted']);self.assertEqual(assumption_counts(v,out['proof']),
                dict(assumptions_checked=2,supported_assumptions=1,unsupported_assumptions=1))
    def test_unbuilt_support_is_not_created(self):
        for c in cases():self.assertFalse(run_policy(view(c['observation'],1),'support_first')['accepted'])
    def test_mapping_state_invariant_across_slot_positions(self):
        states=[trajectory.aligned_state(view(c['observation'])) for c in cases()]
        self.assertTrue(all(v==states[0] for v in states))
    def test_bad_parent_is_rejected_not_fixed(self):
        v=view(cases()[0]['observation']);o=run_policy(v,'support_first');o['proof']['nodes'][-1]['parents']=['bad']
        with self.assertRaises(ValueError):audit_result(v,o)
    def test_budget_is_not_hidden_retry(self):
        v=view(cases()[0]['observation']);o=run_policy(v,'support_first',Limits(max_edge_checks=1))
        self.assertFalse(o['accepted']);self.assertEqual(o['reason'],'scan_budget');audit_result(v,o)
    def test_auditor_does_not_execute_selector(self):
        import r035_frozen_selection.selection as s
        v=view(cases()[0]['observation']);o=run_policy(v,'support_first')
        with patch.object(s,'run_policy',side_effect=AssertionError('production')):self.assertTrue(audit_result(v,o)['verified'])


class TrajectoryTests(unittest.TestCase):
    def test_early_frontier_trace(self):
        run,report,c=trajectory_fixture();d=trajectory.describe(run,report,c,view_of=lambda x:x['view'])
        self.assertEqual(d['support_route_completion_rank'],2)
        self.assertEqual(d['first_differential_readout'],dict(ordinal=1,ticks=102,frontier_count=1))
    def test_mapping_does_not_change_native(self):
        run,report,c=trajectory_fixture();before=deepcopy(run)
        trajectory.describe(run,report,c,view_of=lambda x:x['view']);self.assertEqual(before,run)
    def test_all_permutations_have_same_ID_paths(self):
        paths=[]
        for c in cases():
            run,report,c=trajectory_fixture(c)
            paths.append(trajectory.describe(run,report,c,view_of=lambda x:x['view'])['terminal_completed_paths_edge_ids'])
        self.assertTrue(all(p==paths[0] for p in paths))
    def test_slot_bool_refused(self):
        with self.assertRaises(ValueError):trajectory.id_path(cases()[0]['observation'],[True])
    def test_slot_negative_refused(self):
        with self.assertRaises(ValueError):trajectory.id_path(cases()[0]['observation'],[-1])
    def test_slot_out_of_range_refused(self):
        with self.assertRaises(ValueError):trajectory.id_path(cases()[0]['observation'],[7])
    def test_duplicate_completion_refused(self):
        run,report,c=trajectory_fixture();ev=run['base']['packet']['document']['events'];ev.append(deepcopy(ev[-1]))
        with self.assertRaises(ValueError):trajectory.describe(run,report,c,view_of=lambda x:x['view'])
    def test_missing_completion_refused(self):
        run,report,c=trajectory_fixture();run['base']['packet']['document']['events'].pop()
        with self.assertRaises(ValueError):trajectory.describe(run,report,c,view_of=lambda x:x['view'])
    def test_corrupted_observation_refused(self):
        run,report,c=trajectory_fixture();run['base']['candidates'][0]['view']['observation']['revision']=1
        with self.assertRaises(ValueError):trajectory.describe(run,report,c,view_of=lambda x:x['view'])
    def test_empty_no_state_valid(self):
        self.assertEqual(trajectory.aligned_state(dict(observation={'edges':[]},completed_paths=[],state={})),dict(edges=[],prefixes=[],goal=None))
    def test_nonempty_missing_state_refused(self):
        v=view(cases()[0]['observation']);v['state']={}
        with self.assertRaises(ValueError):trajectory.aligned_state(v)
