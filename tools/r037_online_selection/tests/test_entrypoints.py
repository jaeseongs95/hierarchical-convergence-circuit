from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[3]


class EntrypointTests(unittest.TestCase):
    def test_entrypoints_help_outside_root(self):
        for path in ('Run-HCR-R037.py','scripts/r037_cli.py','scripts/verify_r037.py'):
            with self.subTest(path=path),tempfile.TemporaryDirectory() as cwd:
                p=subprocess.run([sys.executable,'-B',str(ROOT/path),'--help'],cwd=cwd,
                                 capture_output=True,text=True,encoding='utf-8')
                self.assertEqual(p.returncode,0,p.stderr)
    def test_missing_plan_does_not_execute(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'out'
            p=subprocess.run([sys.executable,'-B',str(ROOT/'scripts/r037_cli.py'),'execute','--plan',str(Path(tmp)/'missing'),
                              '--out',str(out)],capture_output=True,text=True,encoding='utf-8')
            self.assertEqual(p.returncode,2);self.assertFalse(out.exists())
    def test_workflow_prepare_execute_audit_verify_once(self):
        module=runpy.run_path(str(ROOT/'Run-HCR-R037.py'))
        steps=module['steps'](ROOT,Path('parent'),Path('out'),Path('plan'))
        commands=[s[1] for s in steps if s[0]=='scripts/r037_cli.py']
        self.assertEqual(commands,['prepare','execute','audit','verify'])
        self.assertIn(['scripts/r036_cli.py','verify','--run','parent'],steps)
    def test_check_only_never_runs_experiment(self):
        module=runpy.run_path(str(ROOT/'Run-HCR-R037.py'))
        steps=module['steps'](ROOT,Path('parent'),None,Path('plan'))
        self.assertFalse(any(s[0]=='scripts/r037_cli.py' for s in steps))
    def test_no_network_or_git_write_steps(self):
        module=runpy.run_path(str(ROOT/'Run-HCR-R037.py'))
        steps=module['steps'](ROOT,Path('parent'),Path('out'),Path('plan'))
        self.assertFalse(any(s[0] in ('git','pip','curl','wget','ollama') for s in steps))
