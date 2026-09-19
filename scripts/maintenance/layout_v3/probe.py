"""Final core regression; executed once, after layout publication. No acceptance decisions here."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import socket
import sys
import unittest
from unittest.mock import patch

class DetailedResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.outcomes = {}
    def addSuccess(self, test):
        super().addSuccess(test); self.outcomes[test.id()] = 'pass'
    def addSkip(self, test, reason):
        super().addSkip(test, reason); self.outcomes[test.id()] = 'skip'
    def addError(self, test, err):
        super().addError(test, err); self.outcomes[test.id()] = 'error'
    def addFailure(self, test, err):
        super().addFailure(test, err); self.outcomes[test.id()] = 'failure'
    def addExpectedFailure(self, test, err):
        super().addExpectedFailure(test, err); self.outcomes[test.id()] = 'expected_failure'
    def addUnexpectedSuccess(self, test):
        super().addUnexpectedSuccess(test); self.outcomes[test.id()] = 'unexpected_success'
    def addSubTest(self, test, subtest, err):
        super().addSubTest(test, subtest, err)
        if err:
            self.outcomes[test.id()] = 'subtest_failure'

def ids(suite):
    for x in suite:
        if isinstance(x, unittest.TestSuite):
            yield from ids(x)
        else:
            yield x.id()

def main():
    p = argparse.ArgumentParser(); p.add_argument('--repo', type=Path, required=True); p.add_argument('--result', type=Path, required=True)
    a = p.parse_args(); root = a.repo.resolve()
    sys.path[:0] = [str(root / 'src'), str(root)]
    import hcr
    if not Path(hcr.__file__).resolve().is_relative_to(root / 'src/hcr'):
        raise RuntimeError('Incorrect hcr import origin')
    suite = unittest.TestLoader().discover(str(root / 'tests'), pattern='test_*.py')
    collected = list(ids(suite))
    if not collected or len(set(collected)) != len(collected):
        raise RuntimeError('Empty or duplicate test collection')
    def deny(*a, **kw):
        raise AssertionError('No real network calls in core regression')
    runner = unittest.TextTestRunner(verbosity=2, resultclass=DetailedResult)
    with patch.object(socket.socket, 'connect', deny), patch.object(socket.socket, 'connect_ex', deny), patch.object(socket, 'create_connection', deny):
        result = runner.run(suite)
    data = {'schema': 'hcc-layout-v3-core-regression', 'tests_run': result.testsRun, 'collected_ids': collected,
            'failures': len(result.failures), 'errors': len(result.errors),
            'skipped': [{'test': t.id(), 'reason': why} for t, why in result.skipped],
            'expected_failures': len(result.expectedFailures), 'unexpected_successes': len(result.unexpectedSuccesses),
            'outcomes': result.outcomes,
            'failure_details': [{'test': t.id(), 'traceback': tb} for t, tb in result.failures + result.errors],
            'actual_research_experiment_executed': False}
    with a.result.open('x', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2); f.write('\n')
    print('HCC_LAYOUT_V3_REGRESSION: ' + json.dumps({k: data[k] for k in ('tests_run', 'failures', 'errors', 'skipped')}, ensure_ascii=False))
    return 0 if result.wasSuccessful() else 2

if __name__ == '__main__':
    raise SystemExit(main())
