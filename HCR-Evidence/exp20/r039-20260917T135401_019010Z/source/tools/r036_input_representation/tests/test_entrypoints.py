import unittest
import ast
import importlib.util
from pathlib import Path
import subprocess
import sys
from r036_helpers import ROOT
from r036_input_representation import protocol,sources,transforms


class EntrypointTests(unittest.TestCase):
    def run_cli(self,*args):
        return subprocess.run([sys.executable,'-X','utf8','-B',str(ROOT/'scripts/r036_cli.py'),*args],capture_output=True,text=True)
    def test_cli_help(self):self.assertEqual(self.run_cli('--help').returncode,0)
    def test_cli_requires_source(self):self.assertNotEqual(self.run_cli('prepare','--out','irrelevant').returncode,0)
    def test_no_generate_without_plan(self):self.assertNotEqual(self.run_cli('execute','--out','irrelevant').returncode,0)
    def test_runner_help(self):
        cp=subprocess.run([sys.executable,'-B',str(ROOT/'Run-HCR-R036.py'),'--help'],capture_output=True,text=True)
        self.assertEqual(cp.returncode,0)
    def test_separate_process_stages(self):
        s=importlib.util.spec_from_file_location('r036_runner',ROOT/'Run-HCR-R036.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
        steps=m.steps(ROOT,Path('source'),Path('out'),Path('plan'))
        self.assertEqual([x[1] for x in steps[-4:]],['prepare','execute','audit','verify'])
        self.assertTrue(any('tools/r036_input_representation/native_tests' in x for x in steps))
    def test_no_native_mutating_output_transform(self):
        text=Path(transforms.__file__).read_text();self.assertNotIn('completed_paths',text);self.assertNotIn('state[',text)
    def test_producer_does_not_import_diagnostics_or_truth(self):
        for name in ('protocol.py','native_bridge.py','transforms.py'):
            p=Path(protocol.__file__).with_name(name);tree=ast.parse(p.read_text())
            for n in ast.walk(tree):
                if isinstance(n,ast.ImportFrom):self.assertNotIn(n.module,('diagnostics','hcr.evaluation.reference','hcr.tasks.toy_world'))
    def test_auditor_does_not_call_production(self):
        from r036_input_representation import audit
        tree=ast.parse(Path(audit.__file__).read_text())
        called={n.func.id for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name)}
        self.assertFalse(called&{'transform_input','run_policy','NativeTrial'})
    def test_current_files_parse_python312(self):
        for p in (ROOT/'tools/r036_input_representation').rglob('*.py'):
            ast.parse(p.read_text(),filename=str(p),feature_version=(3,12))
