"""Exercise the real owned-child boundary without a scientific policy run."""
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest
import termination_new_server_replication as adapter


@unittest.skipUnless(sys.platform == 'linux', 'Requires Linux owned-child integration')
class NewHostBindingTest(unittest.TestCase):
    def test_child_uses_new_study_entrypoint(self):
        server = adapter.server
        self.assertEqual(server.PUB.name, 'new-server-replication-20261018-r15')
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / 'child'
            receipt = server.owned(['--worker', 'smoke-ok'], out, 3, time.monotonic() + 10)
            self.assertEqual(receipt['status'], 'COMPLETE')
            self.assertEqual(receipt['active_processes'], 0)
            launch = json.loads((out / 'launch.json').read_text())
            self.assertIn(str(Path(adapter.__file__).resolve()), launch['argv'])
            boot = json.loads((out / 'bootstrap.json').read_text())
            self.assertEqual(boot['PDEATHSIG'], 'SIGKILL')
            self.assertEqual(boot['limits']['RLIMIT_AS'], [512 * 1024**2] * 2)


if __name__ == '__main__':
    unittest.main()
