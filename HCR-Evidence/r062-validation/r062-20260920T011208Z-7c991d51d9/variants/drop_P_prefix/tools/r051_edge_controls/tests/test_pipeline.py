"""First failure evidence and rendering checks, without a research execution."""
import csv
import io
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch
from tools.r050_review_boundary.common import IntegrityError, load
from tools.r051_edge_controls.pipeline import stage
from tools.r051_edge_controls.audit import render


class Pipeline(unittest.TestCase):
    def test_stage_failure_is_recorded_once_without_retry(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with patch('tools.r051_edge_controls.pipeline.subprocess.run',
                       return_value=SimpleNamespace(returncode=7)) as run:
                with self.assertRaisesRegex(IntegrityError,'first failure retained'):
                    stage(root,root,'failed','tools.r051_edge_controls.worker',[])
                self.assertEqual(run.call_count,1)
            receipt = load(root/'validation/failed.receipt.json')
            self.assertEqual(receipt['returncode'],7)
            self.assertIs(receipt['automatic_retry'],False)
            self.assertTrue((root/'validation/failed.log').exists())
            with self.assertRaises(FileExistsError):
                stage(root,root,'failed','tools.r051_edge_controls.worker',[])

    def test_report_distinguishes_rejection_from_wrong_adoption(self):
        rows = []
        for i, (accepted, correct) in enumerate(((False,None),(True,False))):
            rows.append(dict(case_id=str(i),strength=0.02,top_down=False,
                identity_variant=i,arm='hold',restarts=0,changed_slots=[],
                additional_counters=dict(kernel_ticks=0,signal_transmissions=0),
                final=dict(raw_decision=False,proof_valid=True,failure_class='fixture',
                    internal_edge_conflicts=1,accepted=accepted,adopted_correct=correct)))
        artifacts = render(dict(verified=True,purpose='implementation_validation',rows=rows))
        self.assertIn('| 0.02 | False | hold | 1 | 0 | 1 | 1 | 0 |',
                      artifacts['summary.ko.md'].decode('utf-8'))
        csv_rows = list(csv.DictReader(io.StringIO(artifacts['trials.csv'].decode('utf-8-sig'))))
        self.assertEqual(csv_rows[0]['adopted_correct'],'')
        self.assertEqual(csv_rows[1]['adopted_correct'],'False')


if __name__ == '__main__':
    unittest.main()
