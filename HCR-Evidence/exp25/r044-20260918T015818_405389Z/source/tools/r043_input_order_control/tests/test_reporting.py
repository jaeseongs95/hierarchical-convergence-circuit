from copy import deepcopy
import unittest
from r043_input_order_control import reporting
from r043_input_order_control.tests.fixtures import report_records

class Reporting(unittest.TestCase):
    def test_pair_invariance_not_across_order_invariance(self):
        s=reporting.summarize(report_records())
        self.assertEqual(s['primary_supported_pairs'],6)
        self.assertGreater(s['groups'][0]['tick_spread'],0)
        self.assertFalse(s['cross_permutation_equality_required'])
    def test_tick_difference_is_result_not_exception(self):
        rs=report_records();rs[1]['usage']['native_kernel_ticks']+=5
        s=reporting.summarize(rs);self.assertEqual(s['primary_falsified_pairs'],1)
    def test_trace_difference_with_equal_ticks(self):
        rs=report_records();rs[1]['diagnostics']['canonical_readouts'][0]['state']['goal']=.5
        s=reporting.summarize(rs);p=s['comparisons'][0]
        self.assertTrue(p['native_ticks_equal']);self.assertEqual(p['primary_prediction_status'],'falsified_in_pair')
        self.assertEqual(p['first_readout_difference']['fields'],['state'])
    def test_no_readouts_is_not_evaluable(self):
        rs=report_records()
        for r in rs:r['diagnostics']['canonical_readouts']=[]
        s=reporting.summarize(rs);self.assertEqual(s['primary_not_evaluable_pairs'],6)
    def test_abstention_does_not_fail_audit(self):
        rs=report_records()
        for r in rs:
            r['final'].update(accepted=False,value=None,reason='budget')
            r['classification']='abstention';r['diagnostics']['final_support_signature']=None
            r['diagnostics']['final_proof_projection']=None
        s=reporting.summarize(rs);self.assertEqual(s['primary_supported_pairs'],6)
        self.assertIsNone(s['comparisons'][0]['final_support_signature_equal'])
    def test_wrong_answer_preserved(self):
        rs=report_records()
        for r in rs:r['final']['value']=False;r['classification']='incorrect'
        s=reporting.summarize(rs);self.assertEqual(s['trials'][0]['classification'],'incorrect')
    def test_proof_signature_and_path_inventory_separate(self):
        rs=report_records();rs[1]['diagnostics']['completed_path_inventory'].append(['e4','e5','e6'])
        p=reporting.summarize(rs)['comparisons'][0]
        self.assertTrue(p['final_support_signature_equal']);self.assertFalse(p['completed_path_inventory_equal'])
        self.assertIsNone(p['minimal_goal_proof_DAG_isomorphism'])
    def test_unmeasured_cost_is_not_zero(self):
        rs=report_records();rs[0]['native_cost']['unknown']=None
        s=reporting.summarize(rs);d=next(x for x in s['cost_differences'] if x['metric']=='native_cost.unknown')
        self.assertIsNone(d['swap_minus_identity']);self.assertIsNone(d['equal'])
        self.assertIsNone(s['comparisons'][0]['observed_cost_vector_equal'])
        rs[1]['native_cost']['expansions']+=1
        s=reporting.summarize(rs)
        self.assertFalse(s['comparisons'][0]['observed_cost_vector_equal'])
        self.assertTrue(s['comparisons'][0]['secondary_difference_detected'])
    def test_runtime_wall_placeholder_excluded(self):
        s=reporting.summarize(report_records())
        self.assertNotIn('native_cost.wall_seconds',{r['metric'] for r in s['cost_differences']})
        self.assertIsNone(s['trials'][0]['energy_joules'])
    def test_count_mismatch_rejected(self):
        r=report_records();r.pop()
        with self.assertRaises(ValueError):reporting.summarize(r)
    def test_duplicate_cells_rejected(self):
        r=report_records();r[1]=deepcopy(r[0])
        with self.assertRaises(ValueError):reporting.summarize(r)
    def test_csv_and_summary_include_conditions(self):
        s=reporting.summarize(report_records());text=reporting.render(s)
        self.assertIn('12조건',text);self.assertIn('ID 읽기',text)
        self.assertEqual(len(reporting.csv_text(s['comparisons']).splitlines()),7)
    def test_readout_count_divergence(self):
        a=[{'ordinal':0}];b=[{'ordinal':0},{'ordinal':1}]
        self.assertEqual(reporting.first_readout_difference(a,b)['reason'],'readout_count')

    def test_measured_tick_difference_even_without_readouts_falsifies(self):
        rs=report_records();rs[1]['usage']['native_kernel_ticks']+=1
        rs[1]['diagnostics']['canonical_readouts']=[]
        s=reporting.summarize(rs);self.assertEqual(s['primary_falsified_pairs'],1)
    def test_secondary_difference_is_not_hidden(self):
        rs=report_records();rs[1]['scheduler_usage']['edge_id_reads']+=1
        s=reporting.summarize(rs)
        self.assertEqual(s['primary_supported_pairs'],6)
        self.assertEqual(s['secondary_difference_pairs'],1)
        self.assertIn('secondary_ID',s['finding'])
