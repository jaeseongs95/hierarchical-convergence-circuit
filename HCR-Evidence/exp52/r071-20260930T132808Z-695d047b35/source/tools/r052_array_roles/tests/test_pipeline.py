"""First failure evidence and rendering checks, without a research execution."""
import csv
import io
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch
from tools.r050_review_boundary.common import IntegrityError, load
from tools.r052_array_roles.pipeline import stage


class Pipeline(unittest.TestCase):
    def test_stage_failure_is_recorded_once_without_retry(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with patch('tools.r052_array_roles.pipeline.subprocess.run',
                       return_value=SimpleNamespace(returncode=7)) as run:
                with self.assertRaisesRegex(IntegrityError,'first failure retained'):
                    stage(root,root,'failed','tools.r052_array_roles.worker',[])
                self.assertEqual(run.call_count,1)
            receipt = load(root/'validation/failed.receipt.json')
            self.assertEqual(receipt['returncode'],7)
            self.assertIs(receipt['automatic_retry'],False)
            self.assertTrue((root/'validation/failed.log').exists())
            with self.assertRaises(FileExistsError):
                stage(root,root,'failed','tools.r052_array_roles.worker',[])


if __name__ == '__main__':
    unittest.main()
