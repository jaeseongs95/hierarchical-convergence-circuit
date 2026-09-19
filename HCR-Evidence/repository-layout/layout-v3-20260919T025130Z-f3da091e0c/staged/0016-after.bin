"""R0.2 독립 재검산·논리 변조 탐지·CLI 연결. 배포 시 실행하지 않은 시험 코드다."""
from copy import deepcopy
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from hcr import codec
from hcr.model import ContractError
from hcr.evaluation.adaptive_protocol import run_demo
from hcr.evaluation.adaptive_audit import verify_run
from r02_helpers import rehash_run


class R02AuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.reference = Path(cls.temporary.name) / 'reference'
        cls.summary = run_demo(cls.reference)

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def setUp(self):
        self.case_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.case_dir.name) / 'case'
        shutil.copytree(self.reference, self.root)
        self.addCleanup(self.case_dir.cleanup)

    def events(self):
        return [codec.loads(line) for line in (self.root / 'events.jsonl').read_text(encoding='utf-8').splitlines()]

    def test_complete_demo_passes_independent_audit(self):
        receipt = verify_run(self.root)
        self.assertTrue(receipt['verified'])
        self.assertEqual(receipt['differences'], [])
        self.assertGreater(receipt['scalar_ticks_replayed'], 0)
        self.assertGreater(receipt['binding_scans_checked'], 0)
        self.assertGreater(receipt['memory_updates_checked'], 0)
        self.assertFalse(receipt['hypothesis_proved'])

    def test_r02_cli_verify_autodetects_schema(self):
        from hcr.cli import main
        from contextlib import redirect_stdout
        from io import StringIO
        output = StringIO()
        with redirect_stdout(output):
            result = main(['verify', '--run', str(self.root)])
        self.assertEqual(result, 0, output.getvalue())
        self.assertEqual(codec.loads(output.getvalue())['schema'], 'hcr-independent-audit-r02')

    def test_tick_tamper_rejected_after_chain_and_file_rehash(self):
        events = self.events()
        row = next(e for e in events if e['event'] == 'r02_tick')
        row['payload']['state']['goal'] += .01
        rehash_run(self.root, events)
        with self.assertRaises(ContractError):
            verify_run(self.root)

    def test_summary_tamper_rejected_after_file_rehash(self):
        s = codec.loads((self.root / 'summary.json').read_bytes())
        s['groups']['training/full']['correct'] += 1
        codec.save(self.root / 'summary.json', s, replace=True)
        rehash_run(self.root)
        with self.assertRaises(ContractError):
            verify_run(self.root)

    def test_macro_expansion_record_tamper_rejected(self):
        events = self.events()
        e = next(e for e in events if e['event'] == 'r02_expansion' and e['payload']['candidate']['source'] == 'circuit')
        e['payload']['added'][0]['node']['semantic_id'] = 'not-the-current-node'
        rehash_run(self.root, events)
        with self.assertRaises(ContractError):
            verify_run(self.root)

    def test_learning_transition_tamper_rejected(self):
        events = self.events()
        e = next(e for e in events if e['event'] == 'r02_memory_updated' and e['payload']['memory_document']['circuits'])
        e['payload']['memory_document']['circuits'][0]['strength'] = .999
        rehash_run(self.root, events)
        with self.assertRaises(ContractError):
            verify_run(self.root)

    def test_binding_scan_tamper_rejected(self):
        events = self.events()
        e = next(e for e in events if e['event'] == 'r02_binding_scan' and e['payload']['scans'])
        e['payload']['scans'].pop()
        rehash_run(self.root, events)
        with self.assertRaises(ContractError):
            verify_run(self.root)

    def test_pair_cost_tamper_rejected(self):
        s = codec.loads((self.root / 'summary.json').read_bytes())
        s['familiarity_pairs']['same_structure']['warm_minus_cold']['expansions'] -= 1
        codec.save(self.root / 'summary.json', s, replace=True)
        rehash_run(self.root)
        with self.assertRaises(ContractError):
            verify_run(self.root)

    def test_complete_artifact_inventory_enforced(self):
        (self.root / 'unregistered.txt').write_text('extra', encoding='utf-8')
        with self.assertRaises(ContractError):
            verify_run(self.root)

    def test_manifest_path_traversal_rejected(self):
        m = codec.loads((self.root / 'manifest.json').read_bytes())
        m['files']['../outside.txt'] = '0' * 64
        codec.save(self.root / 'manifest.json', m, replace=True)
        with self.assertRaises(ContractError):
            verify_run(self.root)

    def test_existing_run_is_never_overwritten(self):
        before = (self.root / 'manifest.json').read_bytes()
        with self.assertRaises(FileExistsError):
            run_demo(self.root)
        self.assertEqual((self.root / 'manifest.json').read_bytes(), before)

    def test_first_failure_and_final_revision_have_separate_rows(self):
        rows = [codec.loads(line) for line in (self.root / 'episodes.jsonl').read_text(encoding='utf-8').splitlines()]
        for key, values in self.summary['adaptation'].items():
            phase, arm = key.split('/')
            part = [r for r in rows if r['phase'] == phase and r['arm'] == arm]
            self.assertEqual(values['initial_decision'], part[0]['decision']['id'])
            self.assertEqual(values['final_decision'], part[-1]['decision']['id'])
            if len(part) > 1:
                self.assertIs(part[0]['assessment']['correct'], False)
                self.assertNotEqual(part[0]['decision']['id'], part[-1]['decision']['id'])


class R02CliTests(unittest.TestCase):
    def test_r02_infer_command_needs_no_model_or_network(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'inference'
            result = subprocess.run([sys.executable, '-X', 'utf8', '-B', str(root / 'hcr.py'), 'infer', '--engine', 'r02',
                '--config', str(root / 'configs/r02.toml'), '--input', str(root / 'configs/example_observation.json'),
                '--out', str(out)], capture_output=True, text=True, encoding='utf-8')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(codec.loads((out / 'decision.json').read_bytes())['schema'], 'hcr-decision-r02')
            self.assertFalse(codec.loads((out / 'state.json').read_bytes())['correctness_evaluated'])

    def test_windows_r02_launcher_native_parser_when_available(self):
        exe = shutil.which('pwsh') or shutil.which('powershell')
        if exe is None:
            self.skipTest('PowerShell native parser unavailable in this environment')
        path = str(Path(__file__).resolve().parents[1] / 'Run-HCR-R02.ps1').replace("'", "''")
        code = "$t=$null;$e=$null;[void][System.Management.Automation.Language.Parser]::ParseFile('" + path + "',[ref]$t,[ref]$e);if($e.Count){$e;exit 1}"
        result = subprocess.run([exe, '-NoProfile', '-Command', code], capture_output=True)
        self.assertEqual(result.returncode, 0, result.stdout.decode(errors='replace'))
