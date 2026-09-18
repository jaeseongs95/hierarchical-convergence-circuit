import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import unittest
from helpers import ROOT


class EntrypointTests(unittest.TestCase):
    def test_cli_help(self):
        r=subprocess.run([sys.executable,'-X','utf8','-B',str(ROOT/'scripts/r035_cli.py'),'--help'],capture_output=True,text=True,encoding='utf-8')
        self.assertEqual(r.returncode,0,r.stderr)
        self.assertIn('prepare',r.stdout);self.assertIn('verify',r.stdout)

    def test_cli_required_source(self):
        r=subprocess.run([sys.executable,'-X','utf8','-B',str(ROOT/'scripts/r035_cli.py'),'prepare'],capture_output=True,text=True,encoding='utf-8')
        self.assertEqual(r.returncode,2)

    def test_runner_help(self):
        r=subprocess.run([sys.executable,'-X','utf8','-B',str(ROOT/'Run-HCR-R035.py'),'--help'],capture_output=True,text=True,encoding='utf-8')
        self.assertEqual(r.returncode,0,r.stderr);self.assertIn('--check-only',r.stdout)

    def test_runner_stages_are_separate_process_commands(self):
        s=importlib.util.spec_from_file_location('runner_r035',ROOT/'Run-HCR-R035.py')
        module=importlib.util.module_from_spec(s);s.loader.exec_module(module)
        steps=module.steps(ROOT,Path('/source'),Path('/out'),Path('/plan'))
        self.assertEqual(len(steps),13)
        self.assertEqual([x[1] for x in steps[-4:]],['prepare','execute','audit','verify'])
        self.assertEqual(len(module.steps(ROOT,Path('/source'),None,None)),9)
        self.assertFalse(any('commit' in x or 'push' in x for x in steps))


if __name__=='__main__':unittest.main()
