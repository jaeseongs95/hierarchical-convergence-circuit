from copy import deepcopy
import csv
import io
import unittest
from r042_id_role_isolation import reporting, trajectory
from r042_id_role_isolation.storage import ContractError
from r042_id_role_isolation.tests.fixtures import report_records


class ReportingTests(unittest.TestCase):
    def test_reversal_classification(self):
        summary=reporting.summarize(report_records())
        self.assertEqual(summary['reversal_orders'],6)
        self.assertTrue(summary['all_group_tick_spreads_zero'])
        self.assertEqual(summary['parent_regression_checked'],12)
        self.assertEqual(summary['finding'],'supports_role_alignment_with_measured_trajectory_reversal')

    def test_no_reversal_is_valid_result(self):
        summary=reporting.summarize(report_records(reverse=False))
        self.assertEqual(summary['reversal_orders'],0)
        self.assertEqual(summary['finding'],'no_cost_reversal_observed')

    def test_equal_cost_not_false_reversal(self):
        summary=reporting.summarize(report_records(equal=True))
        self.assertEqual(summary['reversal_orders'],0)
        self.assertTrue(all(r['exact_cost_exchange'] for r in summary['reversals']))

    def test_partial_reversal(self):
        records=report_records()
        for record in records:
            if record['id_variant']=='swap_SD' and record['branch_order']=='SMD':
                record['usage']['native_kernel_ticks']=130
        summary=reporting.summarize(records)
        self.assertEqual(summary['reversal_orders'],5)
        self.assertFalse(summary['all_group_tick_spreads_zero'])

    def test_outcome_change_not_hidden(self):
        records=report_records();records[-1]['final']['value']=False
        summary=reporting.summarize(records)
        self.assertFalse(summary['all_outcomes_equal'])
        self.assertNotEqual(summary['finding'],'supports_role_alignment_with_measured_trajectory_reversal')

    def test_abstention_not_parse_failure(self):
        records=report_records();records[-1]['final'].update(accepted=False,value=None)
        records[-1]['classification']='abstained'
        summary=reporting.summarize(records)
        self.assertEqual(len(summary['trials']),24)
        self.assertIsNone(summary['trials'][-1]['value'])

    def test_probe_unavailable_is_not_equal(self):
        records=report_records();records[-1]['diagnostics']['pre_competitive_probe']=None
        summary=reporting.summarize(records)
        self.assertFalse(summary['pre_competitive_probe_available'])
        self.assertTrue(any(c['pre_competitive_probe_equal'] is None for c in summary['comparisons']))

    def test_upstream_difference_changes_interpretation(self):
        records=report_records();records[-1]['diagnostics']['pre_competitive_probe']={'fixture':'different'}
        summary=reporting.summarize(records)
        self.assertEqual(summary['reversal_orders'],6)
        self.assertEqual(summary['finding'],'cost_reversal_observed_but_simple_mediation_not_established')

    def test_crossed_trajectory_difference_not_hidden(self):
        records=report_records();records[-1]['diagnostics']['canonical_trajectory_sha256']='different'
        summary=reporting.summarize(records)
        self.assertFalse(summary['crossed_canonical_trajectories_equal'])

    def test_missing_condition_rejected(self):
        with self.assertRaises(ContractError): reporting.summarize(report_records()[:-1])

    def test_duplicate_condition_rejected(self):
        records=report_records();records[1]=deepcopy(records[0])
        with self.assertRaises(ContractError): reporting.summarize(records)

    def test_tick_bool_rejected(self):
        records=report_records();records[0]['usage']['native_kernel_ticks']=True
        with self.assertRaises(ContractError): reporting.summarize(records)

    def test_csv_and_report(self):
        summary=reporting.summarize(report_records())
        rows=list(csv.DictReader(io.StringIO(reporting.csv_text(summary['comparisons']))))
        self.assertEqual(len(rows),24)
        text=reporting.render(summary)
        self.assertIn('D_DAG',text)
        self.assertIn('전체 시간·전력 절감률을 주장하지 않는다',text)

    def test_nested_csv_value_roundtrip(self):
        text=reporting.csv_text([{'path':['e0','e1'],'value':None}])
        self.assertEqual(next(csv.DictReader(io.StringIO(text)))['path'],'["e0","e1"]')

    def test_native_and_canonical_assumptions_separated(self):
        inverse={'e4':'e0','e5':'e1'};original=[['e5',True],['e4',True]];before=deepcopy(original)
        mapped=trajectory.canonical_assumptions(original,inverse)
        self.assertEqual(mapped,[['e0',True],['e1',True]])
        self.assertEqual(original,before)

    def test_unknown_reference_not_repaired(self):
        with self.assertRaises(ContractError): trajectory.canonical_path(['unknown'],{'e0':'e0'})

    def test_state_projection_keeps_activations(self):
        state=dict(edges=[['e4',.2],['e0',.8]],prefixes=[dict(route=['e4'],prefix=['e4'],activation=.3)],goal=.7)
        result=trajectory.canonical_state(state,{'e4':'e0','e0':'e4'})
        self.assertEqual(result['edges'],[['e0',.2],['e4',.8]])
        self.assertEqual(result['prefixes'][0]['activation'],.3)

if __name__=='__main__': unittest.main()
