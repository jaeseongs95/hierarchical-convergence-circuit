from copy import deepcopy
import unittest
from r043_input_order_control import spec,input_audit,sources
from r043_input_order_control.storage import ContractError,digest
from r043_input_order_control.tests.fixtures import plan_fixture,full_parent_population

class InputContract(unittest.TestCase):
    def test_all_inputs_and_trial_schedule(self):
        p,old,seed=plan_fixture(); result=input_audit.check_plan_inputs(p,old,seed)
        self.assertEqual(result['native_trials'],12);self.assertEqual(result['identity_regression_trials'],6)
        self.assertEqual(len(result['cases']),12)
        self.assertEqual({t['scheduler'] for t in p['trials']},{'input_order'})
        self.assertEqual(len({t['id'] for t in p['trials']}),12)
    def test_input_cases_identical_to_exp23_generator(self):
        from r042_id_role_isolation.spec import cases as old_cases
        p,old,_=plan_fixture();c,w=old_cases(old)
        self.assertEqual(p['cases'],c);self.assertEqual(p['evaluation_worlds'],w)
    def test_no_input_mutation(self):
        p,old,seed=plan_fixture();before=digest([p,old,seed]);input_audit.check_plan_inputs(p,old,seed)
        self.assertEqual(digest([p,old,seed]),before)
    def test_case_mutations_rejected(self):
        mutations=[lambda c:c['observation']['edges'][0].update(score=.3),
            lambda c:c['observation']['edges'][0].update(target='wrong'),
            lambda c:c['observation']['edges'].reverse(),lambda c:c['observation'].update(episode_id='wrong'),
            lambda c:c['observation'].update(revision=2),lambda c:c['manipulation']['edge_map'].update(e0='e1'),
            lambda c:c.update(parent_case='wrong'),lambda c:c.update(id_variant='invented'),
            lambda c:c['observation']['edges'][0].update(id='e999'),
            lambda c:c['observation']['edges'][0].update(score=True)]
        for f in mutations:
            with self.subTest(mutation=f):
                p,o,s=plan_fixture();f(p['cases'][0])
                with self.assertRaises((ValueError,KeyError)):input_audit.check_plan_inputs(p,o,s)
    def test_world_mutation_rejected(self):
        p,o,s=plan_fixture();p['evaluation_worlds'][p['cases'][0]['name']]['fixture_world']['e0']=False
        with self.assertRaises(ValueError):input_audit.check_plan_inputs(p,o,s)
    def test_condition_mutations_rejected(self):
        for key,value in [('scope','other'),('native_trial_count',24),('schedulers',['edge_id_min']),
                          ('automatic_retry',True),('accuracy_required_for_audit',True),
                          ('invariance_required_for_audit',True),('native_trials_added',99),
                          ('budget',{'max_advances':1})]:
            with self.subTest(key=key):
                p,o,s=plan_fixture();p['conditions'][key]=value
                with self.assertRaises(ValueError):input_audit.check_plan_inputs(p,o,s)
    def test_missing_duplicate_and_reordered_trials_rejected(self):
        for mode in ('missing','duplicate','reverse','scheduler'):
            with self.subTest(mode=mode):
                p,o,s=plan_fixture()
                if mode=='missing':p['trials'].pop()
                elif mode=='duplicate':p['trials'][1]=deepcopy(p['trials'][0])
                elif mode=='reverse':p['trials'].reverse()
                else:p['trials'][0]['scheduler']='edge_id_min'
                with self.assertRaises(ValueError):input_audit.check_plan_inputs(p,o,s)
    def test_exact_seed_references_rejected(self):
        for x in ('e0','e6',{'e3':'v'},{'x':['e4']}):
            with self.subTest(value=x):
                p,o,s=plan_fixture();s['memory']={'ref':x}
                with self.assertRaises(ValueError):input_audit.check_seed_reference_scope(s)
    def test_seed_hash_changed_rejected(self):
        p,o,s=plan_fixture();s['config']['minimum']=.5
        with self.assertRaises(ValueError):input_audit.check_plan_inputs(p,o,s)
    def test_six_parent_input_order_regressions_only(self):
        p,_=full_parent_population();t=sources.parent_regression_trials(p)
        self.assertEqual(len(t),6);self.assertEqual({x['scheduler'] for x in t},{'input_order'})
        self.assertEqual(len(sources.parent_files(p)),13)
    def test_parent_population_mutation_rejected(self):
        p,_=full_parent_population();p['trials'].pop()
        with self.assertRaises(ValueError):sources.parent_regression_trials(p)
    def test_parent_duplicate_regression_rejected(self):
        p,_=full_parent_population();i=[i for i,t in enumerate(p['trials']) if t['scope']=='legacy' and t['arm']=='online_support' and t['scheduler']=='input_order']
        p['trials'][i[1]]=deepcopy(p['trials'][i[0]])
        with self.assertRaises(ValueError):sources.parent_regression_trials(p)
    def test_source_hash_collision_rejected(self):
        with self.assertRaises(ValueError):sources.merge_hashes({'x':'a'},{'x':'b'})
    def test_capsule_names_separate(self):
        self.assertEqual(sources.capsule_name('upstream/seed/6.json'),'upstream/seed/6.json')
        self.assertEqual(sources.prior_capsule_name('plan.json'),'basis/exp23/plan.json')
        with self.assertRaises(ValueError):sources.prior_capsule_name('../bad')
