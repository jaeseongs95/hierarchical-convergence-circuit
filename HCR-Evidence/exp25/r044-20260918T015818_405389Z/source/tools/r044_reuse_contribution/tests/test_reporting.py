from r044_reuse_contribution import reporting
from copy import deepcopy
import unittest
from r044_reuse_contribution import reporting as r,storage as io
from r044_reuse_contribution.tests.fixtures import report_records

class Reporting(unittest.TestCase):
    def setUp(self):self.records=report_records()
    def summary(self):return r.summarize(self.records)
    def test_beneficial_fixture(self):
        s=self.summary();self.assertEqual(s['hypotheses']['H_kernel']['supported_in_pair'],12)
        self.assertEqual(s['parent_regression_checked'],6)
    def test_harmful_kernel_not_audit_failure(self):
        self.records[0]['usage']['native_kernel_ticks']=150
        s=self.summary();self.assertEqual(s['comparisons'][0]['H_kernel'],'falsified_in_pair')
        self.assertEqual(s['comparisons'][0]['observation_class'],'fewer_expansions_but_more_native_ticks')
    def test_equal_expansion_falsifies_strict_prediction(self):
        self.records[0]['native_cost']['expansions']=4
        self.assertEqual(self.summary()['comparisons'][0]['H_expansion'],'falsified_in_pair')
    def test_changed_outcome_is_preserved(self):
        self.records[0]['final']['value']=False;self.records[0]['classification']='incorrect'
        p=self.summary()['comparisons'][0]
        self.assertEqual(p['H_outcome'],'falsified_in_pair');self.assertEqual(p['observation_class'],'value_or_acceptance_changed')
    def test_abstention_is_result(self):
        self.records[0]['final'].update(accepted=False,value=None,reason='stop_frontier_exhausted')
        self.assertEqual(self.summary()['comparisons'][0]['H_outcome'],'falsified_in_pair')
    def test_budget_is_not_logical_failure(self):
        self.records[0]['final'].update(accepted=False,value=None,reason='stop_compute_budget')
        p=self.summary()['comparisons'][0]
        self.assertEqual(p['H_kernel'],'not_evaluable_for_registered_prediction')
        self.assertEqual(p['observation_class'],'budget_or_engine_failure_censored')
    def test_pool_only_effect_not_called_macro_reuse(self):
        self.records[0]['reuse_measurements'].update(macro_actions=0,exposure='pool_only')
        p=self.summary()['comparisons'][0];self.assertFalse(p['prediction_eligible'])
        self.assertEqual(p['enabled_minus_disabled_ticks'],-20)
    def test_missing_readout_ID_control_not_equal(self):
        self.records[0]['diagnostics']['canonical_readouts']=[]
        self.assertEqual(self.summary()['ID_controls'][0]['prediction'],'not_evaluable_in_pair')
    def test_known_tick_difference_not_hidden_by_missing_readout(self):
        self.records[0]['diagnostics']['canonical_readouts']=[]
        self.records[0]['usage']['native_kernel_ticks']=85
        self.assertEqual(self.summary()['ID_controls'][0]['prediction'],'falsified_in_pair')
    def test_duplicate_cell_rejected(self):
        self.records[1]=deepcopy(self.records[0])
        with self.assertRaises(ValueError):self.summary()
    def test_missing_cell_rejected(self):
        self.records.pop()
        with self.assertRaises(ValueError):self.summary()
    def test_non_target_scope_rejected(self):
        self.records[0]['trial']['scope']='legacy'
        with self.assertRaises(ValueError):self.summary()
    def test_unmeasured_are_null(self):
        t=self.summary()['trials'][0]
        for key in ('energy_joules','process_peak_memory_bytes','minimal_goal_proof_DAG_isomorphism'):
            self.assertIsNone(t[key])
    def test_unknown_cost_does_not_become_zero(self):
        self.records[0]['native_cost']['unknown_field']=None
        matches=[d for d in self.summary()['cost_differences'] if d['metric']=='native_cost.unknown_field']
        self.assertIsNone(matches[0]['enabled_minus_disabled'])
    def test_wall_time_does_not_enter_count_vector(self):
        self.assertFalse(any('wall' in key for key in r.metric_vector(self.records[0])))
    def test_no_input_repair(self):
        before=io.digest(self.records);self.summary();self.assertEqual(before,io.digest(self.records))
    def test_summary_deterministic(self):self.assertEqual(io.digest(self.summary()),io.digest(self.summary()))
    def test_render_scope_boundaries(self):
        text=r.render(self.summary());self.assertIn('새 학습',text);self.assertIn('route_only',text)
        self.assertIn('## 판별 실험',text);self.assertIn('## 현재 주장 가능한 범위',text)
    def test_no_learning_claim(self):
        c=self.summary()['claims'];self.assertFalse(c['new_learning_tested']);self.assertFalse(c['retention_tested'])


class MissingMetricEqualityTests(unittest.TestCase):
    def test_unknown_equality_not_asserted(self):
        self.assertIsNone(reporting.vector_equal({'x':None},{'x':None}))
        self.assertIsNone(reporting.vector_equal({'x':3},{}))
    def test_known_difference_not_hidden_by_unknown(self):
        self.assertFalse(reporting.vector_equal({'x':1,'y':None},{'x':2,'y':None}))
