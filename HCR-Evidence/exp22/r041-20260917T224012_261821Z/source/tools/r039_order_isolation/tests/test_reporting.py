import unittest,csv,io
from r039_order_isolation.reporting import summarize,render,trial_csv
from r039_order_isolation.tests._fixtures import reporting_fixture


class ReportingTests(unittest.TestCase):
    def test_total_only_terminal_ticks(self):
        s=summarize(reporting_fixture());self.assertEqual(s['costs']['native_kernel_ticks'],288)
        self.assertEqual(s['native_trials'],36);self.assertEqual(s['base_topologies'],1)
        self.assertEqual(s['paired_trios'],12);self.assertEqual(s['native_readouts'],96)
    def test_savings_retained(self):
        p=summarize(reporting_fixture())['paired'][0];self.assertEqual(p['saved_native_ticks'],3)
        self.assertEqual(p['remaining_native_ticks_after_first_differential'],3)
    def test_same_outcome_no_order_effect(self):
        self.assertTrue(all(not r['native_tick_order_effect_observed'] for r in summarize(reporting_fixture())['order_effects']))
    def test_order_tick_spread_is_observed_not_forced(self):
        r=reporting_fixture();r[0]['usage']['native_kernel_ticks']=10
        self.assertTrue(summarize(r)['order_effects'][0]['native_tick_order_effect_observed'])
    def test_wrong_output_not_called_correct(self):
        r=reporting_fixture()
        for row in r:
            if row['trial']['arm']!='native':row['classification']='incorrect_in_some_declared_world'
        self.assertTrue(all(not p['correct_output_preserving_tick_saving'] for p in summarize(r)['paired']))
    def test_confounded_prefix_blocks_claim(self):
        r=reporting_fixture();r[2]['native_event_semantic_hashes'][0]='different'
        self.assertEqual(next(p for p in summarize(r)['paired'] if p['case']=='order_SMD' and p['scope']=='legacy')['finding'],'paired_execution_not_comparable')
    def test_negative_saving_preserved(self):
        r=reporting_fixture();r[2]['usage']['native_kernel_ticks']=12
        self.assertEqual(next(p for p in summarize(r)['paired'] if p['case']=='order_SMD' and p['scope']=='legacy')['saved_native_ticks'],-3)
    def test_no_opportunity_not_failure(self):
        r=reporting_fixture()
        for x in r:
            x['order_diagnostics']['first_differential_readout']=None
            for y in x['readouts']:y['differential_opportunity']=False
        s=summarize(r);self.assertTrue(all(p['finding']=='no_differential_opportunity_observed' for p in s['paired']))
    def test_missing_arm_refused(self):
        with self.assertRaises(ValueError):summarize(reporting_fixture()[:-1])
    def test_duplicated_arm_refused(self):
        r=reporting_fixture()
        with self.assertRaises(ValueError):summarize(r+[r[0]])
    def test_render_and_csv(self):
        s=summarize(reporting_fixture());text=render(s)
        self.assertIn('EXP-20',text);self.assertIn('topology 1',text)
        rows=list(csv.DictReader(io.StringIO(trial_csv(s['trials']))));self.assertEqual(len(rows),36)
    def test_ID_irrelevance_never_claimed(self):self.assertTrue(all(not x['claims_ID_irrelevance'] for x in summarize(reporting_fixture())['order_effects']))
