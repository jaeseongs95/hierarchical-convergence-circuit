import unittest
from copy import deepcopy
from dataclasses import replace
from itertools import product
from r036_helpers import observation,view,candidate,results
from r036_input_representation.diagnostics import (identifiability,reachable,complete_route,
    proposed_routes,diagnose_state,canonical_state)
from r035_frozen_selection.selection import run_policy
from r035_frozen_selection.contracts import Limits
from r035_frozen_selection.transforms import transform,variants


class DiagnosticTests(unittest.TestCase):
    def test_identifiable_alternative(self):
        self.assertEqual(identifiability(observation())['value'],True)
    def test_missing_information(self):
        o=observation();o['edges']=o['edges'][2:]
        i=identifiability(o);self.assertFalse(i['identifiable']);self.assertIsNone(i['value'])
    def test_zero_is_unknown(self):
        o=observation();o['edges']=o['edges'][2:];o['edges'][0]['score']=0.
        self.assertFalse(identifiability(o)['identifiable'])
    def test_negative_cut(self):
        o=observation();o['edges'][0]['score']=-.1;o['edges'][2]['score']=-.1
        self.assertIs(identifiability(o)['value'],False)
    def test_threshold_boundary_unknown(self):
        o=observation();o['edges']=o['edges'][:2];o['edges'][0]['score']=.1
        self.assertFalse(identifiability(o,.1)['identifiable'])
        o['edges'][0]['score']=-.1;self.assertFalse(identifiability(o,.1)['identifiable'])
    def test_identifiability_matches_all_completions(self):
        o=observation()
        for scores in product((None,0.,-.5,.5),repeat=4):
            for e,s in zip(o['edges'],scores):e['score']=s
            worlds=[]
            for bits in product((False,True),repeat=4):
                if all(s is None or s==0 or (s>0)==b for s,b in zip(scores,bits)):
                    worlds.append(reachable(o,dict(zip([e['id'] for e in o['edges']],bits))))
            i=identifiability(o);self.assertEqual(i['identifiable'],len(set(worlds))==1)
            if i['identifiable']:self.assertEqual(i['value'],worlds[0])
    def test_unknown_proof_is_not_global_information_gap(self):
        v=view();d=diagnose_state(v,candidate(v),results(v));self.assertTrue(d['information']['identifiable'])
        self.assertEqual(d['label'],'proof_selection_gap_recovered')
    def test_proposed_is_not_completed(self):
        v=view(False);d=diagnose_state(v,candidate(v),results(v))
        self.assertEqual(d['label'],'supported_route_proposed_not_completed')
        self.assertEqual(d['completed_supported_indices'],[]);self.assertEqual(d['proposed_supported_complete_routes'],[[0,1]])
    def test_unproposed_not_completed(self):
        v=view(False);c=candidate(v);c['packet']['document']['events']=[e for e in c['packet']['document']['events'] if e['event']!='r02_proposals']
        self.assertEqual(diagnose_state(v,c,results(v))['label'],'supported_route_not_completed')
    def test_activation_gap(self):
        v=view();v['state']['e:0']=.4
        self.assertEqual(diagnose_state(v,candidate(v),results(v))['label'],'completed_support_activation_gap')
    def test_raw_nonpositive_not_named_prior_cause(self):
        v=view();r=results(v);v['raw_value']=False;r['support_first']['accepted']=False
        d=diagnose_state(v,candidate(view()),r)
        self.assertEqual(d['label'],'supported_route_raw_nonpositive');self.assertTrue(d['raw_conflicts_with_identified_value'])
        self.assertFalse(d['label_is_causal_attribution'])
    def test_information_underdetermined_label(self):
        v=view();v['observation']['edges'][0]['score']=None
        self.assertEqual(diagnose_state(v,candidate(v),results(v))['label'],'information_underdetermined')
    def test_budget_unresolved_separate_reason(self):
        v=view();r=results(v);r['support_first']=run_policy(v,'support_first',Limits(max_proof_nodes=0))
        d=diagnose_state(v,candidate(v),r);self.assertEqual(d['label'],'selection_unresolved');self.assertEqual(d['support_first_reason'],'proof_budget')
    def test_proposal_partial_or_cycle_not_complete(self):
        o=observation()
        for p in ([0],[0,3],[2,1],[],[True],[99],[0,1,0]):self.assertFalse(complete_route(o,p))
        self.assertTrue(complete_route(o,[0,1]))
    def test_canonical_route_after_valid_posthoc_fixture_transform(self):
        # 이 테스트 fixture만 posthoc 변환을 이용한다. EXP-17 실행기는 이 함수를 부르지 않는다.
        v=view();t=transform(v,variants()[-1]);tv=t['input']
        r={p:run_policy(tv,'native_saved' if p=='native_rebuild' else p) for p in ('native_saved','native_rebuild','support_first')}
        canon=canonical_state(tv,r,t['maps']['edge_names'])
        self.assertEqual(canon['outputs']['support_first']['route'],['e0','e1'])
        self.assertEqual(canon['completed_route_set'],[['e0','e1'],['e2','e3']])
    def test_canonical_does_not_mutate(self):
        v=view();before=deepcopy(v);canonical_state(v,results(v),{e['id']:e['id'] for e in v['observation']['edges']});self.assertEqual(v,before)
    def test_hidden_world_wrong_type_rejected(self):
        with self.assertRaises(ValueError):reachable(observation(),{'e0':1,'e1':True,'e2':True,'e3':True})
