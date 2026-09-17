from copy import deepcopy
import csv
import io
import unittest
from r038_early_adoption.reporting import summarize,render,csv_text,trial_csv
from r038_early_adoption.contracts import ARMS,USAGE_KEYS


def fixture():
    records=[]
    for arm,ticks,end,accepted in (('native',9,3,False),('posthoc_support',9,3,True),('online_support',6,2,True)):
        zeros={k:0 for k in USAGE_KEYS}
        rows=[dict(native_view_sha256='v'+str(i),ordinal=i,supported_frontier_opportunity=i==1,
                   differential_opportunity=i==1) for i in range(end)]
        records.append(dict(trial=dict(id=arm,case='synthetic',scope='legacy',arm=arm),cohort='new_topology',
            native_event_semantic_hashes=['a','b','c'][:end],readouts=rows,
            final=dict(accepted=accepted,value=True if accepted else None,reason='fixture'),
            classification='correct_in_all_declared_worlds' if accepted else 'abstained',
            native_cost=dict(expansions=end,kernel_ticks=ticks,wall_seconds=0),
            usage=dict(native_kernel_ticks=ticks,online_selection_calls=end,online_selection=zeros.copy(),
                       posthoc_selection_calls=int(arm=='posthoc_support'),posthoc_selection=zeros.copy()),
            audit={'controller':{'native_advances':end}},native_finish_proof_nodes=end*4,
            final_frontier_count=1 if arm=='online_support' else 0,terminal_pending_ready=True,
            base_stop_reason='fixture',final_assumption_counts=None))
    return records


class ReportingTests(unittest.TestCase):
    def test_only_terminal_cumulative_ticks_added(self):
        s=summarize(fixture());self.assertEqual(s['costs']['native_kernel_ticks'],24)
        self.assertEqual(s['native_trials'],3);self.assertEqual(s['base_cases'],1)
        self.assertEqual(s['native_readouts'],8);self.assertEqual(s['paired_trios'],1)

    def test_correct_output_preserving_saving_detected(self):
        p=summarize(fixture())['paired'][0]
        self.assertEqual(p['saved_native_ticks'],3)
        self.assertEqual(p['finding'],'correct_output_preserving_tick_saving')

    def test_wrong_supported_output_is_not_correct_saving(self):
        r=fixture();r[1]['classification']=r[2]['classification']='incorrect_in_some_declared_world'
        p=summarize(r)['paired'][0]
        self.assertFalse(p['correct_output_preserving_tick_saving'])
        self.assertEqual(p['finding'],'supported_wrong_output_preserving_tick_saving')

    def test_no_opportunity_is_not_refutation(self):
        r=fixture()
        for rec in r:
            for row in rec['readouts']: row['differential_opportunity']=False
        p=summarize(r)['paired'][0]
        self.assertEqual(p['finding'],'no_differential_opportunity_observed')

    def test_prefix_mismatch_blocks_saving_claim(self):
        r=fixture();r[-1]['native_event_semantic_hashes'][0]='changed'
        p=summarize(r)['paired'][0]
        self.assertFalse(p['correct_output_preserving_tick_saving'])
        self.assertEqual(p['finding'],'paired_execution_not_comparable')

    def test_full_baseline_trace_mismatch_detected(self):
        r=fixture();r[1]['native_event_semantic_hashes'][-1]='changed'
        self.assertFalse(summarize(r)['paired'][0]['native_posthoc_full_trace_equal'])

    def test_absent_initial_readout_not_fake_equality(self):
        r=fixture()
        for x in r: x['readouts']=[]
        self.assertIsNone(summarize(r)['paired'][0]['first_view_equal'])

    def test_negative_saving_retained(self):
        r=fixture();r[-1]['usage']['native_kernel_ticks']=12
        self.assertEqual(summarize(r)['paired'][0]['saved_native_ticks'],-3)

    def test_missing_or_duplicate_arm_rejected(self):
        r=fixture()
        with self.assertRaises(ValueError): summarize(r[:-1])
        with self.assertRaises(ValueError): summarize(r+[r[0]])

    def test_unknown_native_scan_is_null(self):
        self.assertIsNone(summarize(fixture())['costs']['native_capture_scan_checks'])

    def test_render_and_csv_round_trip(self):
        s=summarize(fixture());text=render(s)
        self.assertIn('합산 총비용',text);self.assertIn('no',str(s['interpretation']))
        self.assertEqual(len(list(csv.DictReader(io.StringIO(csv_text(s['paired']))))),1)
        self.assertEqual(len(list(csv.DictReader(io.StringIO(trial_csv(s['trials']))))),3)

    def test_wall_time_not_used_as_paired_cost_equality(self):
        r=fixture();r[1]['native_cost']['wall_seconds']=100
        self.assertTrue(summarize(r)['paired'][0]['native_posthoc_cost_equal'])
