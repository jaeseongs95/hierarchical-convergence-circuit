import unittest
from copy import deepcopy
from r036_helpers import view
from test_readout_audit import fixture
from r036_input_representation.audit import check_readouts
from r036_input_representation.reporting import summarize,render,csv_text


class ReportingTests(unittest.TestCase):
    def setup_rows(self):
        v,r,c=fixture();rows,_=check_readouts(r,[v],c)
        reports={'t0000':dict(status='readout_ready',kernel_ticks=102,extra_kernel_ticks=34,advances=2,stop_reason='stop_frontier_exhausted')}
        trials=[dict(case='synthetic',scope='legacy',variant={'id':'i000'})]
        return rows,reports,trials
    def test_native_work_not_tripled_by_policies(self):
        rows,reports,trials=self.setup_rows();s=summarize(rows,reports,trials,{})
        self.assertEqual(s['unique_native_task_kernel_ticks'],102);self.assertEqual(s['initial_native_kernel_ticks'],68)
        self.assertEqual(s['selector_evaluations'],3)
    def test_worlds_not_counted_as_independent_states(self):
        rows,reports,trials=self.setup_rows();s=summarize(rows,reports,trials,{})
        self.assertEqual(s['groups']['first_readout/legacy/support_first']['states'],1)
        self.assertEqual(s['groups']['first_readout/legacy/support_first']['correct_in_all_declared_worlds'],1)
    def test_native_unmeasured_not_zero(self):
        rows,reports,trials=self.setup_rows();s=summarize(rows,reports,trials,{})
        self.assertEqual(s['unmeasured_counter_rows']['native_rebuild/edge_checks'],1)
        self.assertNotIn('edge_checks',s['selection_usage']['native_rebuild'])
    def test_missing_variant_reported(self):
        rows,reports,trials=self.setup_rows();trials.append(dict(case='synthetic',scope='legacy',variant={'id':'i001'}))
        p=summarize(rows,reports,trials,{})['paired'][0]
        self.assertFalse(p['all_variants_have_native_readout']);self.assertEqual(p['expected_variants'],2)
    def test_noninvariance_kept_not_failure(self):
        rows,reports,trials=self.setup_rows();r=deepcopy(rows[0]);r['variant']='i001';r['canonical']['completed_route_set']=[];rows.append(r)
        self.assertFalse(summarize(rows,reports,trials,{})['paired'][0]['route_set_invariant'])
    def test_output_and_route_invariance_differ(self):
        rows,reports,trials=self.setup_rows();r=deepcopy(rows[0]);r['variant']='i001';r['canonical']['outputs']['support_first']['route']=['e2','e3'];rows.append(r)
        p=summarize(rows,reports,trials,{})['paired'][0]
        self.assertTrue(p['support_output_invariant']);self.assertFalse(p['support_route_invariant'])
    def test_no_activation_is_unmeasured(self):
        rows,reports,trials=self.setup_rows();rows[0]['canonical']['edge_activation']={}
        self.assertIsNone(summarize(rows,reports,trials,{})['paired'][0]['max_edge_activation_absolute_difference'])
    def test_actual_activation_difference(self):
        rows,reports,trials=self.setup_rows();r=deepcopy(rows[0]);r['variant']='i001';r['canonical']['edge_activation']['e0']-=.1;rows.append(r)
        self.assertAlmostEqual(summarize(rows,reports,trials,{})['paired'][0]['max_edge_activation_absolute_difference'],.1)
    def test_initial_no_readout_separate(self):
        _,reports,trials=self.setup_rows();reports['t0000'].update(status='initial_budget_exhausted',stop_reason='initial_budget_exhausted')
        s=summarize([],reports,trials,{});self.assertEqual(s['initial_without_readout'],1);self.assertEqual(s['native_readouts'],0)
    def test_render_and_csv(self):
        rows,reports,trials=self.setup_rows();s=summarize(rows,reports,trials,{})
        self.assertIn('102',render(s));self.assertIn('last_available',csv_text(rows));self.assertIn('EXP-17',render(s))
