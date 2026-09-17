import unittest
from copy import deepcopy
from helpers import make_view,negative_view
from r035_frozen_selection.selection import run_policy
from r035_frozen_selection.audit import audit_result,check_proof,AuditError,reachable


class AuditTests(unittest.TestCase):
    def test_positive_D_DAG(self):
        v=make_view();a=audit_result(v,run_policy(v,'support_first'));self.assertEqual(a['D_DAG'],2)

    def test_invalid_parents_detected(self):
        v=make_view();r=run_policy(v,'support_first');r['proof']['nodes'][-1]['parents'][0]='nonexistent'
        with self.assertRaises(AuditError):audit_result(v,r)

    def test_cycle_detected(self):
        v=make_view();r=run_policy(v,'support_first');r['proof']['nodes'][-1]['parents'][0]=r['proof']['final']
        with self.assertRaises(AuditError):audit_result(v,r)

    def test_validity_fabrication_detected(self):
        v=make_view();r=run_policy(v,'support_first');r['proof']['under_assumptions_valid']=False
        with self.assertRaises(AuditError):audit_result(v,r)

    def test_mutations(self):
        mutations=[lambda r:r.__setitem__('value',False),lambda r:r.__setitem__('accepted',False),
            lambda r:r['usage'].__setitem__('proof_nodes_created',0),lambda r:r.__setitem__('reason','ok'),
            lambda r:r.__setitem__('input_sha256','0'*64),lambda r:r.__setitem__('selected_path_index',0),
            lambda r:r['proof'].__setitem__('primitive_depth',1),lambda r:r['proof']['nodes'][0].__setitem__('edge_id','e2'),
            lambda r:r['proof']['assumed_edges'][0].__setitem__(1,False),lambda r:r['proof'].__setitem__('paths',[]),
            lambda r:r['selection_trace'][0].__setitem__('observation_supported',True),
            lambda r:r['boundaries'].__setitem__('new_kernel_ticks',1),lambda r:r.__setitem__('extra',1)]
        v=make_view();base=run_policy(v,'support_first')
        for f in mutations:
            r=deepcopy(base);f(r)
            with self.assertRaises((AuditError,KeyError,ValueError)):audit_result(v,r)

    def test_native_wrong_path_not_accepted(self):
        v=make_view();r=run_policy(v,'support_first');r['policy']='native_rebuild';r['reason']='native_reconstructed'
        r['usage'].update(ranked_paths=None,path_checks=None,edge_checks=None);r['selection_trace']=[]
        with self.assertRaises(AuditError):audit_result(v,r)

    def test_support_is_not_external_truth(self):
        v=make_view(score=.92);r=run_policy(v,'support_first');self.assertTrue(audit_result(v,r)['verified'])
        truth={'e0':False,'e1':True,'e2':False,'e3':True}
        self.assertIs(r['value'],True);self.assertFalse(reachable(v['observation'],truth))

    def test_negative_missing_cut_fails(self):
        v=negative_view();r=run_policy(v,'native_rebuild');r['proof']['nodes'][-1]['parents'].pop()
        with self.assertRaises(AuditError):audit_result(v,r)

    def test_no_production_selector_used(self):
        from unittest.mock import patch
        v=make_view();r=run_policy(v,'support_first')
        with (patch('r035_frozen_selection.selection.run_policy',side_effect=AssertionError('should not call generator')),
              patch('r035_frozen_selection.native_bridge.rebuild',side_effect=AssertionError('should not call native builder'))):
            self.assertTrue(audit_result(v,r)['verified'])


if __name__=='__main__':unittest.main()
