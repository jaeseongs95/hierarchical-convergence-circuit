"""Test runner outcome semantics, not experiment outcomes."""
import unittest
from tools.r050_review_boundary.selftest import assessment

class StrictSelftest(unittest.TestCase):
    def result(self):
        result=unittest.TestResult();result.testsRun=1;return result
    def test_success(self):self.assertTrue(assessment(self.result(),1)['verified'])
    def test_zero_discovery_rejected(self):self.assertFalse(assessment(unittest.TestResult(),0)['verified'])
    def test_missing_test_rejected(self):self.assertFalse(assessment(self.result(),2)['verified'])
    def test_skip_not_pass(self):
        r=self.result();r.skipped=[(self,'fixture skip')];self.assertFalse(assessment(r,1)['verified'])
    def test_expected_failure_not_pass(self):
        r=self.result();r.expectedFailures=[(self,'fixture xfail')];self.assertFalse(assessment(r,1)['verified'])
    def test_unexpected_success_not_pass(self):
        r=self.result();r.unexpectedSuccesses=[self];self.assertFalse(assessment(r,1)['verified'])
    def test_error_record_preserved(self):
        r=self.result();r.errors=[(self,'original traceback')];report=assessment(r,1)
        self.assertFalse(report['verified']);self.assertEqual(report['errors'][0]['traceback'],'original traceback')

if __name__=='__main__':unittest.main()
