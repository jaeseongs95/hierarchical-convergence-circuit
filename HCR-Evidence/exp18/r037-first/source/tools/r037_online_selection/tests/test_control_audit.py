from copy import deepcopy
import unittest
from unittest.mock import patch
from r037_online_selection.runtime import OnlineTrial
from r037_online_selection.control_audit import audit_control
from r037_online_selection.contracts import AuditError
from helpers import FakeBackend, OBS, CONFIG, MEMORY


class ControlAuditTests(unittest.TestCase):
    def setUp(self):
        self.backend=FakeBackend();self.worker=OnlineTrial(OBS,CONFIG,MEMORY,'legacy','support_first',backend=self.backend)
        self.run=self.worker.run();self.states=self.backend.session.states

    def reject(self,mutator):
        run=deepcopy(self.run);mutator(run)
        with self.assertRaises((AuditError,KeyError,TypeError)):audit_control(run,self.states)

    def test_genuine_synthetic_trace_checks(self):
        self.assertTrue(audit_control(self.run,self.states)['verified'])

    def test_adoption_flip_rejected(self):
        self.reject(lambda r:r['adoption'].__setitem__('value',False))

    def test_cost_tampering_rejected(self):
        self.reject(lambda r:r['usage'].__setitem__('extra_kernel_ticks',0))

    def test_extra_readout_rejected(self):
        self.reject(lambda r:r['candidates'].append(deepcopy(r['candidates'][0])))

    def test_missing_first_readout_rejected(self):
        self.reject(lambda r:r['candidates'].pop(0))

    def test_missing_selection_rejected(self):
        self.reject(lambda r:r['selections'].pop(0))

    def test_policy_swap_rejected(self):
        self.reject(lambda r:r.__setitem__('policy','native_saved'))

    def test_stale_generation_rejected(self):
        self.reject(lambda r:r['candidates'][0]['reference'].__setitem__('generation',3))

    def test_duplicate_event_rejected(self):
        self.reject(lambda r:r['events'].append(deepcopy(r['events'][-1])))

    def test_missing_event_rejected(self):
        self.reject(lambda r:r['events'].pop(3))

    def test_hidden_restart_rejected(self):
        self.reject(lambda r:r['packet']['document']['transitions'][2].__setitem__('operation','begin'))

    def test_changed_budget_rejected(self):
        self.reject(lambda r:r['budget'].__setitem__('max_extra_advances',0))

    def test_terminal_readiness_tampering_rejected(self):
        self.reject(lambda r:r.__setitem__('terminal_pending_ready',False))

    def test_nonfinite_timing_rejected(self):
        self.reject(lambda r:r.__setitem__('wall_seconds',float('nan')))

    def test_duplicate_cost_readout_summing_rejected(self):
        self.reject(lambda r:r['usage'].__setitem__('initial_kernel_ticks',9))

    def test_audit_does_not_call_producer(self):
        with patch('r037_online_selection.runtime.OnlineTrial.run',side_effect=AssertionError('producer forbidden')):
            self.assertTrue(audit_control(self.run,self.states)['verified'])
