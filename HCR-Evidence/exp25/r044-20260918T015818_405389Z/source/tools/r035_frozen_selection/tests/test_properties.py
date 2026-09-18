import random
import unittest
from dataclasses import asdict
from copy import deepcopy
from helpers import make_view,negative_view,native_candidate
from r035_frozen_selection.selection import run_policy,POLICIES
from r035_frozen_selection.native_bridge import rebuild
from r035_frozen_selection.transforms import transform,variants
from r035_frozen_selection.audit import check_transform,audit_result,check_proof


class PropertyTests(unittest.TestCase):
    def test_192_synthetic_states_all_policies(self):
        rng=random.Random(35016)
        for i in range(192):
            v=make_view(raw=None)
            v['raw_value']=(True,False,None)[i%3]
            v['graph_complete']=bool(i%2)
            for j,e in enumerate(v['observation']['edges']):
                e['score']=rng.choice([None,0.,-.92,.92,-.06,.06])
                v['state']['e:'+str(j)]=rng.choice([.1,.49,.5,.7,.99])
            for name in v['state']:
                if name.startswith('p:'):v['state'][name]=rng.choice([.1,.5,.9])
            v['original_proof']=rebuild(v)[0]
            for t in (variants()[0],variants()[7],variants()[15]):
                wrapped=transform(v,t);check_transform(v,wrapped)
                for policy in POLICIES:audit_result(wrapped['input'],run_policy(wrapped['input'],policy))

    def test_reference_r034_support_first_parity(self):
        from hcr.selection import project_candidate,select_supported,SelectionLimits
        for raw in (True,):
            for score in (None,0.,-.1,.1,.92):
                v=make_view(raw=raw,score=score)
                for t in variants():
                    moved=transform(v,t)['input']
                    old_view=project_candidate(native_candidate(moved))
                    old=select_supported(old_view,SelectionLimits())
                    new=run_policy(moved,'support_first')
                    self.assertEqual(new['proof'],old['proof']);self.assertIs(new['accepted'],old['accepted'])
                    self.assertIs(new['value'],old['value']);self.assertEqual(new['selected_path_index'],old['selected_path_index'])
                    for key in ('ranked_paths','path_checks','edge_checks'):self.assertEqual(new['usage'][key],old['usage_delta'][key])
                    self.assertEqual(new['usage']['proof_nodes_created'],old['usage_delta']['proof_nodes'])

    def test_shared_negative_feature(self):
        v=make_view(raw=None)
        v['observation']['edges']=[dict(id='e0',source='s',target='x',score=-.9),
            dict(id='e1',source='x',target='a',score=.9),dict(id='e2',source='a',target='g',score=.9),
            dict(id='e3',source='x',target='b',score=.9),dict(id='e4',source='b',target='g',score=.9)]
        v['completed_paths']=[[0,1,2],[0,3,4]];v['raw_value']=False
        v['state']={'goal':.1,**{'e:'+str(i):.1 if i==0 else .9 for i in range(5)},
                    **{f'p:{i}:{j}':.1 for i in range(2) for j in range(3)}}
        v['original_proof']=rebuild(v)[0]
        self.assertEqual(len(v['original_proof']['nodes']),4)
        for t in variants():
            moved=transform(v,t)['input']
            for policy in POLICIES:self.assertEqual(audit_result(moved,run_policy(moved,policy))['D_DAG'],2)


if __name__=='__main__':unittest.main()
