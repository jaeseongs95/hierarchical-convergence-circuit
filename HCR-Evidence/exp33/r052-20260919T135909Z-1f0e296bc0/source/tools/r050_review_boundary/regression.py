"""Exactly one final core suite run. Existing capability skips remain skips."""
from __future__ import annotations
import argparse
from pathlib import Path
import unittest
from .common import dump

BASELINE_SKIPS = {
    'test_r021_sessions.CheckpointIO.test_file_symlink_rejected': 'symlink creation is not available',
    'test_r021_sessions.CheckpointIO.test_symlink_parent_rejected': 'symlink creation is not available',
    'test_r034_selection.ProtocolAndIO.test_symlink_rejected': 'local symlink creation not supported',
}

def main(argv=None) -> int:
    p=argparse.ArgumentParser()
    p.add_argument('--repo',required=True,type=Path)
    p.add_argument('--output',required=True,type=Path)
    a=p.parse_args(argv)
    suite=unittest.defaultTestLoader.discover(str(a.repo/'tests'))
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    skips=[dict(test=t.id(),reason=reason) for t,reason in result.skipped]
    new=[row for row in skips if BASELINE_SKIPS.get(row['test']) != row['reason']]
    verified=(result.wasSuccessful() and result.testsRun==602 and not new
              and not result.expectedFailures and not result.unexpectedSuccesses)
    report=dict(schema='hcc-r050-core-regression-v1',verified=verified,tests_run=result.testsRun,
                passed=result.testsRun-len(result.failures)-len(result.errors)-len(result.skipped)
                       -len(result.expectedFailures)-len(result.unexpectedSuccesses),
                expected_failures=[dict(test=t.id(),traceback=text) for t,text in result.expectedFailures],
                unexpected_successes=[t.id() for t in result.unexpectedSuccesses],
                failures=[dict(test=t.id(),traceback=text) for t,text in result.failures],
                errors=[dict(test=t.id(),traceback=text) for t,text in result.errors],
                environment_skips=skips,new_skips=new,expected_baseline_count=602,final_core_runs=1,
                skip_is_pass=False,research_experiment=False)
    dump(a.output,report)
    return 0 if verified else 2

if __name__=='__main__':
    raise SystemExit(main())
