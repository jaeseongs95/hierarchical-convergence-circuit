"""Strict new-test runner. A skipped or expected-failure test is not a pass."""
from __future__ import annotations
import argparse
from pathlib import Path
import unittest
from .common import dump


def assessment(result: unittest.TestResult, discovered: int) -> dict:
    failures = [dict(test=t.id(), traceback=text) for t, text in result.failures]
    errors = [dict(test=t.id(), traceback=text) for t, text in result.errors]
    skipped = [dict(test=t.id(), reason=reason) for t, reason in result.skipped]
    expected = [dict(test=t.id(), traceback=text) for t, text in result.expectedFailures]
    unexpected = [t.id() for t in result.unexpectedSuccesses]
    verified = (discovered > 0 and result.testsRun == discovered and result.wasSuccessful()
                and not skipped and not expected and not unexpected)
    return dict(schema='hcc-r050-unit-selftest-v1', verified=verified,
                discovered=discovered, tests_run=result.testsRun,
                failures=failures, errors=errors, skipped=skipped,
                expected_failures=expected, unexpected_successes=unexpected,
                implementation_validation=True, research_experiment=False,
                actual_hcc_session_tested=True, full_core_regression=False)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--tests', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    a = p.parse_args(argv)
    suite = unittest.defaultTestLoader.discover(str(a.tests))
    count = suite.countTestCases()
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    report = assessment(result, count)
    dump(a.output, report)
    return 0 if report['verified'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
