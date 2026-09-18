import unittest
from copy import deepcopy
from helpers import make_view,negative_view,native_candidate
from r035_frozen_selection.contracts import Limits,ContractError,digest,validate
from r035_frozen_selection.selection import run_policy,POLICIES
from r035_frozen_selection.native_bridge import rebuild,project
from r035_frozen_selection.audit import audit_result


class SelectionTests(unittest.TestCase):
    def test_three_way_contrast(self):
        v=make_view();a={p:run_policy(v,p) for p in POLICIES}
        self.assertIsNone(a['native_saved']['value']);self.assertIsNone(a['native_rebuild']['value'])
        self.assertIs(a['support_first']['value'],True)
        self.assertEqual(a['native_rebuild']['proof'],v['original_proof'])
        self.assertEqual(a['support_first']['selected_path_index'],1)
        for r in a.values():self.assertTrue(audit_result(v,r)['verified'])

    def test_no_existing_alternative(self):
        v=make_view(expanded=False,complete=False);r=run_policy(v,'support_first')
        self.assertIsNone(r['value']);self.assertEqual(r['reason'],'no_supported_existing_path');audit_result(v,r)

    def test_no_mutation(self):
        v=make_view();before=deepcopy(v)
        for p in POLICIES:
            r=run_policy(v,p);self.assertEqual(v,before)
            if r['proof']:r['proof']['nodes'].clear()
            self.assertEqual(v,before)

    def test_negative_passthrough(self):
        v=negative_view()
        for p in POLICIES:
            r=run_policy(v,p);self.assertIs(r['value'],False);self.assertEqual(audit_result(v,r)['D_DAG'],2)
        self.assertFalse(run_policy(v,'support_first')['applicable'])

    def test_negative_coverage(self):
        v=negative_view(complete=False)
        for p in POLICIES:
            r=run_policy(v,p);self.assertIsNone(r['value']);audit_result(v,r)

    def test_none_does_not_flip(self):
        v=make_view(raw=None)
        for p in POLICIES:
            r=run_policy(v,p);self.assertIsNone(r['value']);self.assertFalse(r['applicable']);audit_result(v,r)

    def test_missing_and_neutral(self):
        for x in (None,0.):
            v=make_view(score=x);r=run_policy(v,'support_first');self.assertEqual(r['selected_path_index'],1);audit_result(v,r)

    def test_score_threshold_strict(self):
        v=make_view(score=.92);v['min_abs_score']=.92
        r=run_policy(v,'support_first');self.assertIsNone(r['value']);audit_result(v,r)
        v['min_abs_score']=.9199;r=run_policy(v,'support_first');self.assertIs(r['value'],True);audit_result(v,r)

    def test_activation_is_required(self):
        v=make_view();v['state']['e:0']=.49
        r=run_policy(v,'support_first');self.assertIsNone(r['value']);audit_result(v,r)

    def test_activation_boundary(self):
        v=make_view();v['state']['e:0']=.5
        r=run_policy(v,'support_first');self.assertIs(r['value'],True);audit_result(v,r)

    def test_all_budget_ablations(self):
        for name in ('max_ranked_paths','max_path_checks','max_edge_checks','max_proof_nodes'):
            v=make_view();caps=Limits(**{name:0});r=run_policy(v,'support_first',caps)
            self.assertIsNone(r['value']);self.assertIsNone(r['proof']);audit_result(v,r)

    def test_exact_budget(self):
        v=make_view();r=run_policy(v,'support_first',Limits(max_ranked_paths=2,max_path_checks=2,max_edge_checks=4,max_proof_nodes=4))
        self.assertIs(r['value'],True);self.assertEqual(r['usage']['proof_nodes_created'],4);audit_result(v,r)

    def test_insufficient_scan_budget(self):
        v=make_view();r=run_policy(v,'support_first',Limits(max_edge_checks=3))
        self.assertEqual(r['usage']['edge_checks'],2);self.assertEqual(r['reason'],'scan_budget');audit_result(v,r)

    def test_native_unmeasured_is_null(self):
        v=make_view();r=run_policy(v,'native_rebuild')
        self.assertIsNone(r['usage']['edge_checks']);self.assertEqual(r['usage']['proof_nodes_created'],4);audit_result(v,r)

    def test_no_hidden_input(self):
        for name in ('truth','case','world','expected','source_path','correct'):
            v=make_view();v[name]=True
            with self.assertRaises(ContractError):run_policy(v,'support_first')

    def test_budget_boolean_rejected(self):
        for x in (True,-1,1.5,100001):
            with self.assertRaises(ContractError):Limits(max_path_checks=x)

    def test_invalid_policy(self):
        with self.assertRaises(ContractError):run_policy(make_view(),'oracle')

    def test_non_support_ablation_rejected(self):
        with self.assertRaises(ContractError):run_policy(make_view(),'native_rebuild',Limits(max_proof_nodes=0))

    def test_nonfinite_and_bool_score(self):
        for x in (float('nan'),float('inf'),True,2):
            v=make_view();v['observation']['edges'][0]['score']=x
            with self.assertRaises(ContractError):validate(v)

    def test_invalid_bindings(self):
        mutations=[lambda v:v['completed_paths'][0].__setitem__(0,True),
            lambda v:v['completed_paths'][0].reverse(),lambda v:v['state'].pop('p:0:1'),
            lambda v:v['observation']['edges'][2].__setitem__('id','e0')]
        for f in mutations:
            v=make_view();f(v)
            with self.assertRaises(ContractError):validate(v)

    def test_native_projection(self):
        v=make_view();candidate=native_candidate(v)
        self.assertEqual(project(candidate),v)

    def test_projection_checksum_failure(self):
        c=native_candidate(make_view());c['packet']['document']['events'][0]['payload']['observation']['revision']=1
        with self.assertRaises(ValueError):project(c)

    def test_deterministic_except_time(self):
        v=make_view()
        for p in POLICIES:
            a=run_policy(v,p);b=run_policy(v,p);a.pop('wall_seconds');b.pop('wall_seconds');self.assertEqual(a,b)


if __name__=='__main__':unittest.main()
