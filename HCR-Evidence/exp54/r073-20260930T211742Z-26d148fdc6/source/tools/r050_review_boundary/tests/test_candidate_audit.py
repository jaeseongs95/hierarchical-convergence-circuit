"""Real native candidates and tampering checks; implementation evidence only."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from hcr import codec
from hcr.circuits import AdaptiveMemory
from hcr.model import AdaptiveConfig, ContractError, fingerprint
from hcr.evaluation.review_audit import packet_states, verify_candidate as legacy_verify
from tools.r050_review_boundary.candidate_audit import verify_candidate
from tools.r050_review_boundary.common import load
from tools.r050_review_boundary.worker import execute_session


class CandidateAudit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path(__file__).resolve().parents[3]
        spec = load(root / 'experiments/exp-31-review-boundary/frozen_spec.json')
        plan = dict(spec, empty_memory=AdaptiveMemory.empty(AdaptiveConfig()).document())
        cls.executions = []
        for strength, td in ((0.02, False), (0.02, True), (1.0, False)):
            case = next(c for c in spec['cases'] if c['strength'] == strength
                        and c['top_down'] is td and c['relation'] == '++'
                        and c['identity_variant'] == 0)
            with tempfile.TemporaryDirectory() as tmp:
                execution = execute_session(plan, case, case['observation'], Path(tmp), 'baseline', 0)
            states, _ = packet_states(execution['packet'])
            cls.executions.append((execution, states))

    def check(self, candidate=None, index=0):
        execution, states = self.executions[index]
        return verify_candidate(candidate or execution['candidate'], execution['packet'], states)

    def test_original_failure_is_reproduced_and_rejected_proof_is_audited(self):
        execution, states = self.executions[0]
        c = execution['candidate']
        self.assertIs(c['decision']['value'], False)
        self.assertIs(c['decision']['proof']['under_assumptions_valid'], False)
        self.assertIs(c['readout']['accepted'], False)
        with self.assertRaisesRegex(ContractError, 'invalid primitive proof'):
            legacy_verify(c, execution['packet'], states)
        self.assertTrue(self.check()['verified'])

    def test_valid_proof_and_supported_candidate_still_verify(self):
        for index in (1, 2):
            self.assertTrue(self.check(index=index)['verified'])
        self.assertTrue(self.executions[2][0]['candidate']['readout']['accepted'])

    def test_tampered_resealed_diagnostic_is_rejected(self):
        c = deepcopy(self.executions[0][0]['candidate'])
        c['diagnostic']['evidence_support_sufficient'] = True
        c['diagnostic']['sha256'] = fingerprint({k:v for k,v in c['diagnostic'].items() if k != 'sha256'})
        with self.assertRaises(ContractError):
            self.check(c)

    def test_tampered_resealed_adoption_is_rejected(self):
        c = deepcopy(self.executions[0][0]['candidate'])
        c['readout']['accepted'] = True
        c['readout']['value'] = False
        c['readout']['sha256'] = fingerprint({k:v for k,v in c['readout'].items() if k != 'sha256'})
        with self.assertRaises(ContractError):
            self.check(c)

    def test_changed_proof_and_identity_are_rejected(self):
        for field in ('proof', 'identity'):
            c = deepcopy(self.executions[0][0]['candidate'])
            if field == 'proof':
                c['decision']['proof']['under_assumptions_valid'] = True
            else:
                c['candidate_id'] += '-tampered'
            with self.assertRaises(ContractError):
                self.check(c)


if __name__ == '__main__':
    unittest.main()
