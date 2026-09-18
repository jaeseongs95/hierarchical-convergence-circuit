"""Test subprocesses explicitly select the package before unittest collection."""
from pathlib import Path
import argparse
import sys
import unittest
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
p.add_argument('--suite',choices=['inherited','new'],required=True)
a=p.parse_args();root=a.root.resolve();sys.path[:0]=[str(root/'src'),str(root)]
import hcr
if not Path(hcr.__file__).resolve().is_relative_to(root/'src/hcr'):raise RuntimeError('wrong hcr import origin')
# Different directories use separate processes to avoid unittest top-level name collisions.
folders=['r047_state_ablation','r048_precision'] if a.suite=='inherited' else ['r049_signal_boundary']
if a.suite=='inherited':
    import subprocess
    for name in ('inherited','new'):
        r=subprocess.run([sys.executable,'-X','utf8','-B',str(root/'scripts/r048_tests.py'),'--root',str(root),'--suite',name],cwd=root/'src')
        if r.returncode:raise SystemExit(r.returncode)
else:
    suite=unittest.TestLoader().discover(str(root/'tools/r049_signal_boundary/tests'),pattern='test_*.py')
    if suite.countTestCases()==0:raise RuntimeError('zero tests collected')
    result=unittest.TextTestRunner(verbosity=2,failfast=True).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)
