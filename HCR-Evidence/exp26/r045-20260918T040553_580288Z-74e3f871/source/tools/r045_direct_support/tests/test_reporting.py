"""Synthetic results exercise every prediction branch; these numbers are not research results."""
from copy import deepcopy
import unittest
from r045_direct_support import reporting as r
from r045_direct_support.tests.fixtures import report_records


class ReportingTests(unittest.TestCase):
    def test_opposed_predictions_remain_opposed(self):
        s=r.summarize(report_records())
        self.assertEqual(s['hypotheses']['H_kernel'],{'falsified_in_pair':2})
        self.assertEqual(s['hypotheses']['H_expansion'],{'supported_in_pair':2})
        self.assertEqual(s['hypotheses']['H_decision_same'],{'supported_in_pair':2})
    def test_primary_not_all_families_pooled(self):
        s=r.summarize(report_records());self.assertEqual((s['native_trials'],s['gate_pairs'],s['primary_pairs']),(12,6,2))
        self.assertEqual(sum(s['hypotheses']['H_expansion'].values()),2)
    def test_missing_direct_exposure_is_not_failure_of_audit(self):
        rs=report_records();rs[0]['direct_measurements']['direct_circuit_use']=False
        s=r.summarize(rs);self.assertEqual(s['hypotheses']['H_direct']['falsified_in_pair'],1)
        self.assertEqual(s['hypotheses']['H_kernel']['not_evaluable'],1)
    def test_changed_outcome_not_called_efficiency(self):
        rs=report_records();rs[0]['final']['value']=False
        s=r.summarize(rs);self.assertFalse(s['comparisons'][0]['same_outcome_cost_comparison'])
        self.assertEqual(s['hypotheses']['H_outcome']['falsified_in_pair'],1)
    def test_each_censored_reason(self):
        for reason in sorted(r.CENSORED):
            with self.subTest(reason=reason):
                rs=report_records();rs[0]['final']['reason']=reason;s=r.summarize(rs)
                self.assertEqual(s['hypotheses']['H_kernel']['not_evaluable'],1)
    def test_misconvergence_stays_an_outcome(self):
        rs=report_records();rs[0]['classification']='incorrect_in_declared_world'
        s=r.summarize(rs);self.assertEqual(s['trials'][0]['classification'],'incorrect_in_declared_world')
    def test_conflict_abstention_not_counted_as_correct(self):
        rs=report_records()
        for q in rs:
            if q['family']=='conflict_len2':
                q['final'].update(value=None,accepted=False);q['classification']='abstained';q['diagnostics']['final_support_signature']=None
        s=r.summarize(rs)
        self.assertEqual(s['hypotheses']['H_conflict_no_false_positive'],{'supported_in_pair':2})
        self.assertTrue(all(g['correct']==0 and g['abstained']==2 for g in s['groups'] if g['family']=='conflict_len2'))
    def test_conflict_false_acceptance_fails_prediction(self):
        rs=report_records()
        next(q for q in rs if q['family']=='conflict_len2')['final'].update(value=True,accepted=True)
        self.assertEqual(r.summarize(rs)['hypotheses']['H_conflict_no_false_positive']['falsified_in_pair'],1)
    def test_no_pool_is_not_evidence_of_mismatch_rejection(self):
        rs=report_records();q=next(q for q in rs if q['family']=='conflict_len2' and q['trial']['use_circuits'])
        q['direct_measurements'].update(pool_candidate_evaluations=0,matched_candidates=0,mismatch_rejected_evaluations=0)
        self.assertEqual(r.summarize(rs)['hypotheses']['H_conflict_reject']['falsified_in_pair'],1)
    def test_ID_readout_change_detected(self):
        rs=report_records();rs[2]['diagnostics']['canonical_readout_sha256']='changed'
        self.assertTrue(any(x['prediction']=='falsified_in_pair' for x in r.summarize(rs)['ID_controls']))
    def test_ID_decision_change_not_hidden_by_same_readout_and_cost(self):
        rs=report_records()
        changed=next(x for x in rs if x['family']=='supported_len2' and x['id_variant']=='fresh_ids' and x['trial']['use_circuits'])
        changed['direct_measurements']['decision_signature_sequence'][0]['dynamics_sha256']='changed'
        control=next(x for x in r.summarize(rs)['ID_controls'] if x['family']=='supported_len2' and x['use_circuits'])
        self.assertIs(control['canonical_readouts_equal'],True)
        self.assertIs(control['measured_cost_vector_equal'],True)
        self.assertIs(control['decision_computation_signature_equal'],False)
        self.assertEqual(control['prediction'],'falsified_in_pair')
    def test_missing_readouts_not_equal_by_default(self):
        rs=report_records()
        for q in rs:q['diagnostics']['canonical_readout_sha256']=None
        self.assertTrue(all(x['prediction']=='not_evaluable' for x in r.summarize(rs)['ID_controls']))
    def test_unmeasured_cost_not_zero(self):
        rs=report_records();rs[0]['scheduler_usage']['unknown']=None
        s=r.summarize(rs);x=next(x for x in s['cost_differences'] if x['metric']=='scheduler.unknown')
        self.assertIsNone(x['delta']);self.assertIsNone(s['trials'][0]['energy_joules'])
    def test_native_wall_placeholder_excluded(self):
        s=r.summarize(report_records());self.assertNotIn('native_cost.wall_seconds',s['trials'][0])
    def test_duplicate_cell_rejected(self):
        rs=report_records();rs[-1]=deepcopy(rs[0])
        with self.assertRaises(ValueError):r.summarize(rs)
    def test_bad_tick_partition_rejected(self):
        rs=report_records();rs[0]['usage']['native_kernel_ticks']+=1
        with self.assertRaises(ValueError):r.summarize(rs)
    def test_bool_as_gate_not_int(self):
        rs=report_records();rs[0]['trial']['use_circuits']=1
        with self.assertRaises(ValueError):r.summarize(rs)
    def test_render_and_csv(self):
        s=r.summarize(report_records());self.assertIn('## 결론',r.render(s))
        self.assertIn('supported_len2',r.csv_text(s['comparisons']))
        self.assertEqual(r.csv_text([]),'')

if __name__=='__main__':unittest.main()
