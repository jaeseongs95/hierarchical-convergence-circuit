"""Test process bootstraps package search before unittest discovery."""
from pathlib import Path
import argparse
import sys
import unittest
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--suite',choices=['inherited','new'],required=True)
a=p.parse_args();root=a.root.resolve();sys.path[:0]=[str(root/'src'),str(root)]
import hcr
if not Path(hcr.__file__).resolve().is_relative_to(root/'src/hcr'):
    raise RuntimeError('wrong hcr import origin: '+str(hcr.__file__))
folder=root/'tools'/('r047_state_ablation' if a.suite=='inherited' else 'r048_precision')/'tests'
suite=unittest.TestLoader().discover(str(folder),pattern='test_*.py')
if suite.countTestCases()==0:raise RuntimeError('zero tests collected')
result=unittest.TextTestRunner(verbosity=2,failfast=True).run(suite)
raise SystemExit(0 if result.wasSuccessful() else 1)
