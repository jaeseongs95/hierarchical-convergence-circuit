"""생산 제어 규칙의 순수 단위시험. engine recurrence를 대신하는 시험은 아니다."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from hcr.selection_control import choose_action
from hcr.selection import SelectionContractError


def action(**changes):
    state=dict(arm='expand_then_select',ready=True,failed=False,frontier=True,candidate_id='candidate',
        native_accepted=False,selection_accepted=False,checked=False,restarts=0,extra_advances=0,
        extra_ticks=0,max_advances=8,max_ticks=2048,tick_reservation=320)
    state.update(changes);return choose_action(**state)


class SelectionControllerTests(unittest.TestCase):
    def test_native_supported_stops(self):self.assertEqual(action(native_accepted=True),'stop_supported_native')
    def test_native_accepted_before_budget(self):self.assertEqual(action(native_accepted=True,max_advances=0),'stop_supported_native')
    def test_hold_running_is_not_an_inference(self):self.assertEqual(action(arm='hold',ready=False,candidate_id=None),'stop_hold')
    def test_hold_ready_abstention(self):self.assertEqual(action(arm='hold'),'stop_hold')
    def test_selection_acceptance(self):self.assertEqual(action(selection_accepted=True),'stop_supported_selection')
    def test_selection_before_more_expansion(self):self.assertEqual(action(),'select_existing_proof')
    def test_no_kernel_budget_needed_for_existing_selection(self):self.assertEqual(action(max_advances=0),'select_existing_proof')
    def test_exhausted_kernel_does_not_suppress_sidecar(self):self.assertEqual(action(max_ticks=0),'select_existing_proof')
    def test_already_checked_then_expand(self):self.assertEqual(action(checked=True),'continue_dependency')
    def test_select_only_never_expands(self):self.assertEqual(action(arm='select_only',checked=True),'stop_no_supported_selection')
    def test_expand_only_never_selects(self):self.assertEqual(action(arm='expand_only'),'continue_dependency')
    def test_no_frontier_does_not_invent_one(self):self.assertEqual(action(checked=True,frontier=False),'stop_frontier_exhausted')
    def test_more_work_exhausted(self):self.assertEqual(action(checked=True,max_advances=0),'stop_compute_budget')
    def test_same_restart(self):self.assertEqual(action(arm='restart_same'),'restart')
    def test_policy_restart(self):self.assertEqual(action(arm='restart_route_only'),'restart')
    def test_same_restart_once(self):self.assertEqual(action(arm='restart_same',restarts=1),'stop_restart_finished')
    def test_policy_restart_once(self):self.assertEqual(action(arm='restart_route_only',restarts=1),'stop_restart_finished')
    def test_restart_is_not_free(self):self.assertEqual(action(arm='restart_same',max_advances=0),'stop_compute_budget')
    def test_running_continues(self):self.assertEqual(action(ready=False,candidate_id=None),'advance')
    def test_running_budget_stops(self):self.assertEqual(action(ready=False,candidate_id=None,max_advances=0),'stop_compute_budget')
    def test_tick_reservation_is_conservative(self):self.assertEqual(action(ready=False,candidate_id=None,max_ticks=319),'stop_compute_budget')
    def test_exact_reservation_allowed(self):self.assertEqual(action(ready=False,candidate_id=None,max_ticks=320),'advance')
    def test_engine_failure_retained(self):self.assertEqual(action(failed=True),'stop_engine_failure')
    def test_completed_prior_success_not_retried(self):self.assertEqual(action(arm='restart_same',native_accepted=True),'stop_supported_native')
    def test_invalid_budget_type(self):
        with self.assertRaises(SelectionContractError):action(extra_advances=True)
    def test_unknown_arm(self):
        with self.assertRaises(SelectionContractError):action(arm='oracle')
    def test_no_phantom_initial_readout(self):
        with self.assertRaises(SelectionContractError):action(candidate_id=None)
    def test_selection_has_a_ready_source(self):
        with self.assertRaises(SelectionContractError):action(ready=False,candidate_id=None,selection_accepted=True)


if __name__=='__main__':unittest.main(verbosity=2)
