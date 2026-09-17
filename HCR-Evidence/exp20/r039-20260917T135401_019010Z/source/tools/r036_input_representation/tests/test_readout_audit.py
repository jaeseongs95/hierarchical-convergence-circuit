import unittest
from copy import deepcopy
from r036_helpers import view,candidate,results
from r035_frozen_selection.contracts import digest
from r036_input_representation.audit import check_readouts


def fixture():
    v=view();c=candidate(v);res=results(v)
    raw=dict(trial=dict(id='t0000',case='synthetic',scope='legacy',variant={'id':'i000'}),
        transformed=dict(maps=dict(edge_names={e['id']:e['id'] for e in v['observation']['edges']})),
        native=dict(flow=dict(candidates=[c])),readouts=[dict(ordinal=0,candidate_id=c['candidate_id'],candidate_sha256=digest(c),input_sha256=digest(v),results=res)])
    case=dict(name='synthetic',observation=deepcopy(v['observation']),worlds={
        'open':dict(e0=True,e1=True,e2=True,e3=True),'closed':dict(e0=True,e1=True,e2=False,e3=True)})
    return v,raw,case


class ReadoutAuditTests(unittest.TestCase):
    def test_actual_selector_independent_proof_audit(self):
        v,r,c=fixture();rows,a=check_readouts(r,[v],c)
        self.assertEqual(rows[0]['diagnostic']['label'],'proof_selection_gap_recovered')
        self.assertEqual(a[0]['support_first']['D_DAG'],2)
    def test_rehashed_changed_value_rejected(self):
        v,r,c=fixture();r['readouts'][0]['results']['support_first']['value']=False
        with self.assertRaises(ValueError):check_readouts(r,[v],c)
    def test_parent_corruption_rejected(self):
        v,r,c=fixture();r['readouts'][0]['results']['support_first']['proof']['nodes'][-1]['parents']=['missing']
        with self.assertRaises(ValueError):check_readouts(r,[v],c)
    def test_wrong_depth_rejected(self):
        v,r,c=fixture();r['readouts'][0]['results']['support_first']['proof']['primitive_depth']=99
        with self.assertRaises(ValueError):check_readouts(r,[v],c)
    def test_source_candidate_corruption_rejected(self):
        v,r,c=fixture();r['readouts'][0]['candidate_sha256']='f'*64
        with self.assertRaises(ValueError):check_readouts(r,[v],c)
    def test_input_corruption_rejected(self):
        v,r,c=fixture();r['readouts'][0]['input_sha256']='0'*64
        with self.assertRaises(ValueError):check_readouts(r,[v],c)
    def test_native_rebuild_wrong_choice_rejected(self):
        v,r,c=fixture();r['readouts'][0]['results']['native_rebuild']['proof']=r['readouts'][0]['results']['support_first']['proof']
        with self.assertRaises(ValueError):check_readouts(r,[v],c)
    def test_missing_policy_rejected(self):
        v,r,c=fixture();del r['readouts'][0]['results']['native_rebuild']
        with self.assertRaises(ValueError):check_readouts(r,[v],c)
    def test_extra_readout_rejected(self):
        v,r,c=fixture();r['readouts'].append(deepcopy(r['readouts'][0]))
        with self.assertRaises(ValueError):check_readouts(r,[v],c)
    def test_original_gate_disagreement_rejected(self):
        v,r,c=fixture();r['native']['flow']['candidates'][0]['readout']['accepted']=True
        r['readouts'][0]['candidate_sha256']=digest(r['native']['flow']['candidates'][0])
        with self.assertRaises(ValueError):check_readouts(r,[v],c)
    def test_wrong_world_does_not_invalidate_audit(self):
        v,r,c=fixture();c['worlds']={'wrong':dict(e0=False,e1=True,e2=False,e3=True)}
        rows,_=check_readouts(r,[v],c)
        self.assertIs(rows[0]['world_results']['support_first']['wrong']['external_correct'],False)
    def test_first_and_last_markers_do_not_duplicate_rows(self):
        v,r,c=fixture();rows,_=check_readouts(r,[v],c)
        self.assertEqual(len(rows),1);self.assertTrue(rows[0]['first_readout'] and rows[0]['last_available_readout'])
    def test_cost_inventory(self):
        v,r,c=fixture();rows,_=check_readouts(r,[v],c);u=rows[0]['selection_usage']
        self.assertIsNone(u['native_rebuild']['edge_checks']);self.assertEqual(u['support_first']['edge_checks'],4)
