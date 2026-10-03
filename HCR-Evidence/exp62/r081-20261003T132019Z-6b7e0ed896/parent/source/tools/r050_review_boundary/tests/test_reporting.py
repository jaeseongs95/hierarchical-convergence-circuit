"""Aggregation-only fixtures. Not actual HCC experimental evidence."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from tools.r050_review_boundary.common import dump,load,IntegrityError,seal
from tools.r050_review_boundary.reporting import create

ARMS=('hold','same_input_restart','echo_revision_restart','strength_revision_restart')

def fixture():
    outcome=dict(adopted_correct=None,accepted=False,adopted_value=None,raw_decision=None,
                 pending_value=None,numeric_goal_side=None,failure_class='external_compute_budget',
                 internal_edge_conflicts=None,convergence_status=None,native_failure_reason=None,D_DAG=None)
    counters=dict(kernel_ticks=0,signal_transmissions=0,proof_nodes_reconstructed=0)
    rows=[];comparisons=[]
    for i in range(24):
        for arm in ARMS:
            rows.append(dict(case_id=f'c{i:03d}',arm=arm,strength=.02,relation='++',identity_variant=0,top_down=False,
              initial=deepcopy(outcome),final=deepcopy(outcome),restarts=0,probe_requests=0,
              baseline_sha256='fixture-baseline-'+str(i),baseline_counters=deepcopy(counters),
              additional_counters=deepcopy(counters),native_observe_first_next_action=dict(action='advance',target=None),
              probe_target=dict(edge_id=None,slot=None,slots_inspected=0,reason='no_candidate'),
              stop_reason='baseline_external_compute_budget',arm_wall_seconds=0.001,raw_path='fixture-only'))
        for prediction in ('P1','P2','P3'):
            comparisons.append(dict(case_id=f'c{i:03d}',prediction=prediction,evaluated=False,comparison=None))
    return dict(verified=True,baseline_count=24,arm_records=96,rows=rows,numerical_comparisons=comparisons,
                unique_baseline_counters=deepcopy(counters),additional_counters=deepcopy(counters),
                restarts=0,measurements=0,plan_sha256=seal(dict(schema='hcc-r050-plan-v1',fixture_only=True))['sha256'],fixture_only=True)

def write_fixture(root: Path, value=None):
    audit = fixture() if value is None else value
    dump(root/'plan.json', seal(dict(schema='hcc-r050-plan-v1',fixture_only=True)))
    dump(root/'raw_manifest.json', dict(schema='hcc-r050-raw-manifest-v1',files={}))
    dump(root/'analysis'/'audit.json', audit)
    return audit

class Reporting(unittest.TestCase):
    def test_unknown_and_skipped_comparison_not_reported_as_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);write_fixture(root);summary=create(root)
            self.assertEqual(summary['groups']['hold']['correct_adoptions'],0)
            self.assertEqual(summary['groups']['hold']['abstentions'],24)
            self.assertEqual(summary['numeric_predictions']['P1']['applicable'],0)
            self.assertEqual(summary['numeric_predictions']['P1']['not_applicable'],24)
            self.assertEqual(summary['numeric_predictions']['P1']['final_state_close'],0)
    def test_csv_preserves_initial_pending_and_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);write_fixture(root);create(root)
            header=(root/'analysis'/'trials.csv').read_text(encoding='utf-8-sig').splitlines()[0]
            for column in ('initial_pending_value','initial_failure_class','final_pending_value','native_failure_reason','actual_energy_joules'):
                self.assertIn(column,header)
    def test_partial_audit_cannot_be_reported_complete(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);f=fixture();f['arm_records']=95;write_fixture(root,f)
            with self.assertRaises(IntegrityError):create(root)
            self.assertFalse((root/'analysis'/'summary.json').exists())
    def test_reporting_does_not_replace_previous_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);write_fixture(root);create(root)
            previous=(root/'analysis'/'summary.json').read_bytes()
            with self.assertRaises(IntegrityError):create(root)
            self.assertEqual((root/'analysis'/'summary.json').read_bytes(),previous)

if __name__=='__main__':unittest.main()
