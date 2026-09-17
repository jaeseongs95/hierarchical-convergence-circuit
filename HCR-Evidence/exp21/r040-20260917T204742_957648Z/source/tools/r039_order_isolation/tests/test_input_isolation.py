from copy import deepcopy
import unittest
from unittest.mock import patch
from r039_order_isolation import spec,input_audit
from r039_order_isolation.contracts import digest,CANONICAL_OBSERVATION_SHA256
from r039_order_isolation.tests._fixtures import parent,cases


class InputTests(unittest.TestCase):
    def setUp(self):self.base=parent();self.cases=cases()
    def check(self,rows=None,worlds=None):
        return input_audit.check_cases(spec.public_cases(rows or self.cases),
            worlds or {c['name']:c['worlds'] for c in self.cases},self.base)
    def test_anchor_hash_matches_actual_exp19(self):self.assertEqual(digest(self.base['observation']),CANONICAL_OBSERVATION_SHA256)
    def test_six_orders_exhaustive(self):self.assertEqual([c['manipulation']['branch_order'] for c in self.cases],list(input_audit.EXPECTED_ORDERS))
    def test_fixed_semantics(self):self.assertEqual(len({r['fixed_semantic_sha256'] for r in self.check()}),1)
    def test_six_distinct_order_hashes(self):self.assertEqual(len({r['observation_sha256'] for r in self.check()}),6)
    def test_anchor_input_is_unchanged(self):self.assertEqual(self.cases[0]['observation'],self.base['observation'])
    def test_parent_and_cases_are_not_shared(self):
        self.cases[0]['observation']['edges'][0]['score']=0
        self.assertEqual(parent(),self.base);self.assertEqual(self.cases[1]['observation']['edges'][0]['score'],.92)
    def test_no_truth_in_public_payload(self):self.assertTrue(all('worlds' not in c for c in spec.public_cases(self.cases)))
    def test_36_trial_schedule(self):
        rows=spec.trials(self.cases);self.assertEqual(len(rows),36);input_audit.check_trial_schedule(rows)
    def test_all_arm_scope_combinations(self):
        from collections import Counter
        c=Counter((t['scope'],t['arm']) for t in spec.trials(self.cases));self.assertEqual(set(c.values()),{6})
    def test_auditor_does_not_call_generator(self):
        with patch.object(spec,'make_cases',side_effect=AssertionError('generator invoked')):self.check()
    def test_no_trial_drop(self):
        with self.assertRaises(ValueError):input_audit.check_trial_schedule(spec.trials(self.cases)[:-1])
    def test_no_trial_reorder(self):
        with self.assertRaises(ValueError):input_audit.check_trial_schedule(list(reversed(spec.trials(self.cases))))
    def test_effect_not_a_pass_requirement(self):
        for field in ('correctness_required_for_audit','improvement_required_for_audit','order_effect_required_for_audit'):
            self.assertIs(spec.conditions()[field],False)


def mutation(name,fn):
    def test(self):
        fn(self.cases[0])
        with self.assertRaises((ValueError,KeyError,TypeError)):self.check()
    test.__name__='test_reject_'+name
    setattr(InputTests,test.__name__,test)
for name,fn in {
    'edge_id':lambda c:c['observation']['edges'][0].update(id='renamed'),
    'node_id':lambda c:c['observation']['edges'][0].update(target='new'),
    'episode':lambda c:c['observation'].update(episode_id='new-episode'),
    'revision':lambda c:c['observation'].update(revision=1),
    'score':lambda c:c['observation']['edges'][0].update(score=.5),
    'missing_as_zero':lambda c:c['observation']['edges'][2].update(score=0),
    'missing_as_false':lambda c:c['observation']['edges'][2].update(score=False),
    'internal_edge_order':lambda c:c['observation']['edges'].__setitem__(slice(0,2),list(reversed(c['observation']['edges'][:2]))),
    'slot_map':lambda c:c['manipulation']['new_to_canonical_slot'].__setitem__(0,1),
    'branch_label':lambda c:c['manipulation'].update(branch_order='DSM'),
    'population_label':lambda c:c.update(name='other'),
    'edge_drop':lambda c:c['observation']['edges'].pop(),
    'extra_truth':lambda c:c['observation'].update(world=True),
    'world_flip':lambda c:c['worlds']['missing_closed'].__setitem__('e4',True),
    'world_bool_int':lambda c:c['worlds']['missing_closed'].__setitem__('e0',1),
}.items():mutation(name,fn)
