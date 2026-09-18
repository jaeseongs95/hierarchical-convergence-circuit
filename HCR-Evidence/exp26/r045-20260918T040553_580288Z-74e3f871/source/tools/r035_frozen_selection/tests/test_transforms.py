import unittest
from copy import deepcopy
from helpers import make_view,negative_view
from r035_frozen_selection.transforms import variants,transform
from r035_frozen_selection.selection import run_policy,POLICIES
from r035_frozen_selection.native_bridge import rebuild
from r035_frozen_selection.audit import check_transform,audit_result,AuditError


class TransformTests(unittest.TestCase):
    def test_all_sixteen(self):
        v=make_view();before=deepcopy(v)
        self.assertEqual(len(variants()),16)
        for t in variants():
            x=transform(v,t);y=check_transform(v,x);self.assertEqual(x['input'],y)
            for policy in POLICIES:
                r=run_policy(y,policy);audit_result(y,r)
                self.assertIs(r['value'],True if policy=='support_first' else None)
        self.assertEqual(v,before)

    def test_identity_is_exact(self):
        v=make_view();self.assertEqual(transform(v,variants()[0])['input'],v)

    def test_original_proof_ids_are_opaque(self):
        v=make_view();x=transform(v,variants()[-1]);check_transform(v,x)
        self.assertEqual([n['id'] for n in x['input']['original_proof']['nodes']],[n['id'] for n in v['original_proof']['nodes']])
        for policy in POLICIES:audit_result(x['input'],run_policy(x['input'],policy))

    def test_negative_transport(self):
        v=negative_view()
        for t in variants():
            x=transform(v,t);check_transform(v,x)
            for policy in POLICIES:
                r=run_policy(x['input'],policy);self.assertIs(r['value'],False);audit_result(x['input'],r)

    def test_tie_order_change_is_visible(self):
        v=make_view();v['state']['p:1:1']=v['state']['p:0:1'];v['original_proof']=rebuild(v)[0]
        same=transform(v,variants()[0])['input'];reverse=transform(v,variants()[1])['input']
        a=run_policy(same,'native_rebuild');b=run_policy(reverse,'native_rebuild')
        self.assertIsNone(a['value']);self.assertIs(b['value'],True)
        audit_result(same,a);audit_result(reverse,b)
        self.assertIsNone(run_policy(reverse,'native_saved')['value'])
        self.assertIs(run_policy(reverse,'support_first')['value'],True)

    def test_mapping_mutations_fail(self):
        v=make_view();x=transform(v,variants()[-1])
        mutators=[lambda y:y['maps']['edge_new_to_old'].__setitem__(0,0),
            lambda y:y['input']['state'].__setitem__('p:1:1',.1),
            lambda y:y['input']['observation']['edges'][0].__setitem__('score',.4),
            lambda y:y['input'].__setitem__('raw_value',False),
            lambda y:y['input']['original_proof']['nodes'][1].__setitem__('path_index',0),
            lambda y:y.__setitem__('source_input_sha256','0'*64)]
        for change in mutators:
            y=deepcopy(x);change(y)
            with self.assertRaises((AuditError,KeyError,ValueError)):check_transform(v,y)

    def test_partial_graph_not_completed_by_transform(self):
        v=make_view(expanded=False,complete=False)
        for t in variants():
            x=transform(v,t);check_transform(v,x);self.assertFalse(x['input']['graph_complete'])
            self.assertEqual(len(x['input']['completed_paths']),1)


if __name__=='__main__':unittest.main()
