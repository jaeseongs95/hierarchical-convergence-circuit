import unittest
from copy import deepcopy
from itertools import product
from r036_helpers import observation
from r036_input_representation.transforms import transform_input,validate_observation
from r036_input_representation.spec import variants,conditions,trials
from r036_input_representation.audit import check_transform
from r036_input_representation.diagnostics import reachable


class TransformTests(unittest.TestCase):
    def test_eight_unique_variants(self):
        self.assertEqual(len(variants()),8);self.assertEqual(len({v['id'] for v in variants()}),8)
    def test_identity_exact(self):
        o=observation();self.assertEqual(transform_input(o,variants()[0])['observation'],o)
    def test_all_variants_audit(self):
        o=observation();before=deepcopy(o)
        for v in variants():self.assertEqual(check_transform(o,transform_input(o,v),v),transform_input(o,v)['observation'])
        self.assertEqual(o,before)
    def test_world_reachability_preserved_all_assignments(self):
        o=observation()
        for v in variants():
            t=transform_input(o,v)
            for bits in product((False,True),repeat=4):
                w=dict(zip([e['id'] for e in o['edges']],bits));mapped={t['maps']['edge_names'][k]:b for k,b in w.items()}
                self.assertEqual(reachable(o,w),reachable(t['observation'],mapped))
    def test_no_posthoc_state(self):
        for v in variants():
            t=transform_input(observation(),v)
            self.assertNotIn('state',t);self.assertNotIn('completed_paths',t)
    def test_alias_only_preserves_edge_position(self):
        for v in variants():
            t=transform_input(observation(),v)
            self.assertEqual(t['maps']['edge_new_to_old'],[3,2,1,0] if v['edge_reverse'] else [0,1,2,3])
    def test_episode_and_revision_preserved(self):
        o=observation();o['revision']=9
        for v in variants():
            t=transform_input(o,v)['observation'];self.assertEqual(t['episode_id'],o['episode_id']);self.assertEqual(t['revision'],9)
    def test_mutated_score_fails_independent_audit(self):
        o=observation();v=variants()[1];t=transform_input(o,v);t['observation']['edges'][0]['score']=-.9
        with self.assertRaises(ValueError):check_transform(o,t,v)
    def test_mutated_endpoint_fails(self):
        o=observation();v=variants()[0];t=transform_input(o,v);t['observation']['goal']='a'
        with self.assertRaises(ValueError):check_transform(o,t,v)
    def test_mutated_map_fails(self):
        o=observation();v=variants()[-1];t=transform_input(o,v);t['maps']['edge_new_to_old'].reverse()
        with self.assertRaises(ValueError):check_transform(o,t,v)
    def test_hidden_truth_rejected(self):
        o=observation();o['truth']=True
        with self.assertRaises(ValueError):transform_input(o,variants()[0])
    def test_bool_score_rejected(self):
        o=observation();o['edges'][0]['score']=True
        with self.assertRaises(ValueError):validate_observation(o)
    def test_nonfinite_score_rejected(self):
        for x in (float('nan'),float('inf'),2,-2):
            o=observation();o['edges'][0]['score']=x
            with self.assertRaises(ValueError):validate_observation(o)
    def test_duplicate_edge_rejected(self):
        o=observation();o['edges'][1]['id']='e0'
        with self.assertRaises(ValueError):validate_observation(o)
    def test_selfloop_rejected(self):
        o=observation();o['edges'][0]['target']='s'
        with self.assertRaises(ValueError):validate_observation(o)
    def test_unknown_variant_rejected(self):
        v=variants()[0];v['id']='oops'
        with self.assertRaises(ValueError):transform_input(observation(),v)
    def test_integer_variant_flag_rejected(self):
        v=variants()[0];v['node_alias']=0
        with self.assertRaises(ValueError):transform_input(observation(),v)
    def test_matrix_128(self):
        cases=[dict(name='case'+str(i)) for i in range(8)];t=trials(cases)
        self.assertEqual(len(t),128);self.assertEqual(len({x['id'] for x in t}),128)
    def test_matrix_does_not_receive_world(self):
        t=trials([{'name':'a','worlds':{'bad':True}}]);self.assertTrue(all(set(x)=={'id','case','scope','variant'} for x in t))
    def test_no_independent_path_order_factor(self):
        self.assertTrue(all('path_reverse' not in v for v in variants()));self.assertFalse(conditions()['state_or_completed_paths_transported'])
