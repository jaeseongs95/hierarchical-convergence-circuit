from copy import deepcopy
import itertools
import random
import unittest
from r041_scheduler_direction import scheduler,schedule_audit,spec,input_audit
from r039_order_isolation.input_audit import canonical_observation,canonical_worlds
from fixtures import core_for

class SchedulerTests(unittest.TestCase):
    def view(self,paths=None):
        return dict(schema='hcr-frontier-view-r041-v1',edge_ids=['z','a','m'],
                    frontier_paths=[[0],[1],[2]] if paths is None else paths)
    def test_input_order_retains_head(self):self.assertEqual(scheduler.choose(self.view(),'input_order')['selected_index'],0)
    def test_id_min_is_not_slot_min(self):self.assertEqual(scheduler.choose(self.view(),'edge_id_min')['selected_index'],1)
    def test_input_not_modified(self):
        v=self.view();before=deepcopy(v);scheduler.choose(v,'edge_id_min');self.assertEqual(v,before)
    def test_empty_frontier_no_priority(self):
        out=scheduler.choose(self.view([]),'edge_id_min');self.assertIsNone(out['selected_path']);self.assertFalse(out['priority_required'])
    def test_root_path_is_allowed(self):
        out=scheduler.choose(self.view([[]]),'edge_id_min');self.assertEqual(out['selected_path'],[]);self.assertEqual(out['usage']['edge_id_reads'],0)
    def test_already_min_no_transition(self):self.assertFalse(scheduler.choose(self.view([[1],[2]]),'edge_id_min')['priority_required'])
    def test_prefix_lexicographic_order(self):self.assertEqual(scheduler.choose(self.view([[1,2],[1]]),'edge_id_min')['selected_path'],[1])
    def test_counters(self):
        self.assertEqual(scheduler.choose(self.view(),'edge_id_min')['usage'],dict(decision_calls=1,
            frontier_items_examined=3,edge_id_reads=3,key_comparisons=2,priority_transitions=1,priority_match_scans=3))
    def test_native_counters(self):
        out=scheduler.choose(self.view(),'input_order')['usage'];self.assertEqual(out['frontier_items_examined'],1);self.assertEqual(out['priority_match_scans'],0)
    def test_no_scores_or_truth_fields(self):
        for field in ('score','world','raw_value','case','support_path','prior'):
            with self.subTest(field=field),self.assertRaises(ValueError):scheduler.choose(dict(self.view(),**{field:True}),'edge_id_min')
    def test_invalid_paths_rejected(self):
        for paths in ([[True]],[[1.0]],[[-1]],[[3]],[[0]*5],[[0],[0]],'bad'):
            with self.subTest(paths=paths),self.assertRaises(ValueError):scheduler.choose(self.view(paths),'edge_id_min')
    def test_duplicate_ids_rejected(self):
        v=self.view();v['edge_ids']=['a','a','m']
        with self.assertRaises(ValueError):scheduler.choose(v,'edge_id_min')
    def test_unknown_scheduler(self):
        with self.assertRaises(ValueError):scheduler.choose(self.view(),'oracle')
    def test_malformed_view(self):
        for v in (None,[],{},dict(self.view(),schema='bad')):
            with self.subTest(v=v),self.assertRaises(ValueError):scheduler.choose(v,'input_order')
    def test_order_invariant_identity_mapping(self):
        for ids in itertools.permutations(['z','a','m']):
            for ps in itertools.permutations([[0],[1],[2]]):
                v=dict(schema='hcr-frontier-view-r041-v1',edge_ids=list(ids),frontier_paths=list(ps))
                self.assertEqual(scheduler.choose(v,'edge_id_min')['selected_edge_ids'],['a'])
    def test_independent_audit_200_seeded_combinations(self):
        rng=random.Random(4021)
        for iteration in range(200):
            ids=rng.sample(['e7','a1','nodeZ','한글','e0','z0'],rng.randrange(1,7))
            candidates=list({tuple(rng.sample(range(len(ids)),rng.randrange(min(4,len(ids))+1))) for _ in range(15)})
            rng.shuffle(candidates)
            v=dict(schema='hcr-frontier-view-r041-v1',edge_ids=ids,frontier_paths=[list(p) for p in candidates])
            for policy in ('input_order','edge_id_min','edge_id_max'):
                with self.subTest(iteration=iteration,policy=policy):
                    _,expected=schedule_audit.expected_decision(core_for(v),policy)
                    self.assertEqual(scheduler.choose(v,policy),expected)
    def test_108_treatments_exact(self):
        base=dict(name='three_branch_l3_early',observation=canonical_observation(),worlds=canonical_worlds())
        cases=spec.make_cases(base);rows=spec.trials(cases);self.assertEqual(len(rows),108);input_audit.check_trial_schedule(rows)
        input_audit.check_cases(spec.public_cases(cases),{c['name']:c['worlds'] for c in cases},base)
    def test_treatment_dropping_rejected(self):
        base=dict(name='three_branch_l3_early',observation=canonical_observation(),worlds=canonical_worlds())
        rows=spec.trials(spec.make_cases(base))
        for bad in (rows[:-1],rows+[rows[0]],list(reversed(rows))):
            with self.assertRaises(ValueError):input_audit.check_trial_schedule(bad)
    def test_no_accuracy_required(self):
        c=spec.conditions();self.assertFalse(c['correctness_required_for_audit']);self.assertFalse(c['order_gap_reduction_required_for_audit'])
    def test_readout_ready_rejects_projection(self):
        c=core_for(self.view());c['pending']['ready']=True
        with self.assertRaises(ValueError):scheduler.project(c)
