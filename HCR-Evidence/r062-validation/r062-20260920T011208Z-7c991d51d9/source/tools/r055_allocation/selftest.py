"""Strict implementation checks; skipped tests are not counted as passes."""
import argparse
from pathlib import Path
import unittest
from tools.r050_review_boundary.common import dump


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    suite = unittest.defaultTestLoader.discover(str(args.source / 'tools/r055_allocation/tests'))
    # Reused numerical verifier: retain its synthetic stable/budget/oscillation checks.
    suite.addTests(unittest.defaultTestLoader.loadTestsFromName('tools.r053_feedback.tests.test_audit'))
    count = suite.countTestCases()
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    verified = count > 0 and result.testsRun == count and result.wasSuccessful() and not (
        result.skipped or result.expectedFailures or result.unexpectedSuccesses)
    dump(args.output, dict(verified=verified, tests_run=result.testsRun,
        failures=[dict(test=t.id(), traceback=msg) for t, msg in result.failures],
        errors=[dict(test=t.id(), traceback=msg) for t, msg in result.errors],
        skipped=[dict(test=t.id(), reason=msg) for t, msg in result.skipped],
        expected_failures=[t.id() for t, _ in result.expectedFailures],
        unexpected_successes=[t.id() for t in result.unexpectedSuccesses],
        research_experiment=False))
    return 0 if verified else 2


if __name__ == '__main__':
    raise SystemExit(main())
