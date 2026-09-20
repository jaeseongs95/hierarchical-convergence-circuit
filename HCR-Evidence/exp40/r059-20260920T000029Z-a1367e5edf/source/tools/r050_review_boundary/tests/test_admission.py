"""External scheduler reservation fixtures, never native HCC measurements."""
from copy import deepcopy
import unittest
from tools.r050_review_boundary.audit import validate_reservations
from tools.r050_review_boundary.common import IntegrityError


def evidence(ticks=(0,100,150), ready=True):
    operations=['init','begin']+['advance']*(len(ticks)-1)
    states={i+1:{'pending':{'ready':bool(ready and i==len(ticks)-1),'cost':{'kernel_ticks':t}}}
            for i,t in enumerate(ticks)}
    run={'advances':len(ticks)-1,'ready':ready,'packet':{'document':{'transitions':[{'operation':op} for op in operations]}}}
    return run,states


class Admission(unittest.TestCase):
    limits={'max_advances_per_session':8,'max_kernel_ticks_per_session':1280}
    def test_valid_reservations(self):
        run,states=evidence();validate_reservations(run,states,self.limits,160)
    def test_pre_advance_reservation_required_not_just_final_cost(self):
        run,states=evidence((0,160,170));limits=dict(self.limits,max_kernel_ticks_per_session=300)
        with self.assertRaisesRegex(IntegrityError,'reservation'):validate_reservations(run,states,limits,160)
    def test_boolean_count_rejected(self):
        run,states=evidence((0,20));run['advances']=True
        with self.assertRaisesRegex(IntegrityError,'integer'):validate_reservations(run,states,self.limits,160)
    def test_non_boolean_ready_rejected(self):
        run,states=evidence();run['ready']=1
        with self.assertRaisesRegex(IntegrityError,'boolean'):validate_reservations(run,states,self.limits,160)
    def test_missing_replayed_generation_rejected(self):
        run,states=evidence();states.pop(2)
        with self.assertRaisesRegex(IntegrityError,'Missing'):validate_reservations(run,states,self.limits,160)
    def test_native_tick_delta_cannot_exceed_reservation(self):
        run,states=evidence((0,161))
        with self.assertRaisesRegex(IntegrityError,'exceeded'):validate_reservations(run,states,self.limits,160)
    def test_tick_rollback_rejected(self):
        run,states=evidence((0,100,80))
        with self.assertRaisesRegex(IntegrityError,'tick ledger'):validate_reservations(run,states,self.limits,160)
    def test_no_advance_after_ready(self):
        run,states=evidence();states[2]['pending']['ready']=True
        with self.assertRaisesRegex(IntegrityError,'running'):validate_reservations(run,states,self.limits,160)
    def test_unlisted_operation_rejected(self):
        run,states=evidence();run['packet']['document']['transitions'][-1]['operation']='feedback'
        with self.assertRaisesRegex(IntegrityError,'Unexpected'):validate_reservations(run,states,self.limits,160)
    def test_initial_budget_stop_with_zero_advances_is_representable(self):
        run,states=evidence((0,),False);validate_reservations(run,states,self.limits,160)

if __name__=='__main__':unittest.main()
