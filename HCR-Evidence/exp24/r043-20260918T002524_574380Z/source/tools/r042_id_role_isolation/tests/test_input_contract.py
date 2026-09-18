from copy import deepcopy
import ast
from pathlib import Path
import unittest
from r042_id_role_isolation import transform, spec, input_audit
from r042_id_role_isolation.storage import ContractError, digest
from r042_id_role_isolation.tests.fixtures import plan_fixture


class InputTests(unittest.TestCase):
    def setUp(self):
        self.plan,self.parent,self.seed = plan_fixture()

    def check(self): return input_audit.check_plan_inputs(self.plan,self.parent,self.seed)

    def test_full_population(self):
        self.assertEqual(self.check()['native_trials'],24)
        self.assertEqual(len(self.plan['cases']),12)

    def test_inputs_not_mutated(self):
        before=digest(self.parent)
        spec.cases(self.parent)
        self.assertEqual(digest(self.parent),before)

    def test_identity_exact(self):
        for old in self.parent['cases']:
            self.assertEqual(transform.observation(old['observation'],'identity'),old['observation'])

    def test_relabel_is_involution(self):
        for old in self.parent['cases']:
            obs=old['observation']
            self.assertEqual(transform.observation(transform.observation(obs,'swap_SD'),'swap_SD'),obs)

    def test_vocabulary_and_internal_slots_unchanged(self):
        old=self.parent['cases'][0]['observation'];new=transform.observation(old,'swap_SD')
        self.assertEqual({e['id'] for e in old['edges']},{e['id'] for e in new['edges']})
        self.assertEqual([{k:v for k,v in e.items() if k!='id'} for e in old['edges']],
                         [{k:v for k,v in e.items() if k!='id'} for e in new['edges']])

    def test_M_ids_fixed(self):
        mapping=transform.edge_map('swap_SD')
        self.assertEqual((mapping['e2'],mapping['e3']),('e2','e3'))
        self.assertEqual((mapping['e0'],mapping['e4']),('e4','e0'))

    def test_world_transport(self):
        old=self.parent['evaluation_worlds']['order_SMD']
        new=transform.worlds(old,'swap_SD')
        self.assertEqual(new['fixture_world']['e0'],old['fixture_world']['e4'])
        self.assertEqual(transform.worlds(new,'swap_SD'),old)

    def test_effect_not_acceptance_criterion(self):
        for field in ('reversal_required_for_audit','invariance_required_for_audit','accuracy_required_for_audit'):
            self.assertIs(self.plan['conditions'][field],False)

    def test_score_mutation_rejected(self):
        self.plan['cases'][1]['observation']['edges'][0]['score']=.8
        with self.assertRaises(ContractError): self.check()

    def test_relation_mutation_rejected(self):
        self.plan['cases'][1]['observation']['edges'][0]['target']='other'
        with self.assertRaises(ContractError): self.check()

    def test_slot_reordering_rejected(self):
        self.plan['cases'][1]['observation']['edges'].reverse()
        with self.assertRaises(ContractError): self.check()

    def test_duplicate_edge_rejected(self):
        edges=self.plan['cases'][1]['observation']['edges'];edges[1]['id']=edges[0]['id']
        with self.assertRaises(ContractError): self.check()

    def test_unknown_ID_rejected(self):
        self.plan['cases'][1]['observation']['edges'][0]['id']='unknown'
        with self.assertRaises(ContractError): self.check()

    def test_missing_remapped_world_rejected(self):
        case=self.plan['cases'][1];truth=self.plan['evaluation_worlds'][case['name']]['fixture_world'];truth['e0']=not truth['e0']
        with self.assertRaises(ContractError): self.check()

    def test_world_integer_truth_rejected(self):
        case=self.plan['cases'][0];self.plan['evaluation_worlds'][case['name']]['fixture_world']['e0']=1
        with self.assertRaises(ContractError): self.check()

    def test_episode_change_rejected(self):
        self.plan['cases'][1]['observation']['episode_id']='changed'
        with self.assertRaises(ContractError): self.check()

    def test_extra_mapping_field_rejected(self):
        self.plan['cases'][1]['manipulation']['repair']=True
        with self.assertRaises(ContractError): self.check()

    def test_reference_in_seed_rejected(self):
        self.seed['memory']['some_reference']=['e0']
        with self.assertRaises(ContractError): input_audit.check_seed_reference_scope(self.seed)

    def test_reference_key_in_seed_rejected(self):
        self.seed['memory']['e4']=.5
        with self.assertRaises(ContractError): input_audit.check_seed_reference_scope(self.seed)

    def test_trial_missing_rejected(self):
        self.plan['trials'].pop()
        with self.assertRaises(ContractError): self.check()

    def test_trial_duplicate_rejected(self):
        self.plan['trials'][1]=deepcopy(self.plan['trials'][0])
        with self.assertRaises(ContractError): self.check()

    def test_trial_order_mutation_rejected(self):
        self.plan['trials'][0],self.plan['trials'][1]=self.plan['trials'][1],self.plan['trials'][0]
        with self.assertRaises(ContractError): self.check()

    def test_budget_mutation_rejected(self):
        self.plan['conditions']['budget']['max_advances']+=1
        with self.assertRaises(ContractError): self.check()

    def test_hypothesis_cannot_become_gate(self):
        self.plan['conditions']['reversal_required_for_audit']=True
        with self.assertRaises(ContractError): self.check()

    def test_world_not_inside_public_case(self):
        self.plan['cases'][0]['worlds']={}
        with self.assertRaises(ContractError): self.check()

    def test_independent_input_audit_does_not_import_production(self):
        tree=ast.parse(Path(input_audit.__file__).read_text(encoding='utf-8'))
        imports=[node for node in ast.walk(tree) if isinstance(node,(ast.Import,ast.ImportFrom))]
        self.assertFalse(any(getattr(n,'module','') in ('spec','transform') for n in imports))

    def test_unregistered_variant_rejected(self):
        with self.assertRaises(ContractError): transform.edge_map('optimize_until_reversal')



class KeySemanticsTests(unittest.TestCase):
    """명세 자체의 ID 우선순위 변화만 검사한다. Native 비용 결과를 예측값으로 고정하지 않는다."""
    def test_S_D_relative_priority_reversed_for_all_six_arrays(self):
        plan,parent,_=plan_fixture()
        for original in parent['cases']:
            for variant in ('identity','swap_SD'):
                obs=transform.observation(original['observation'],variant)
                mapping=transform.edge_map(variant)
                slots={edge['id']:i for i,edge in enumerate(obs['edges'])}
                paths={'S':[slots[mapping[e]] for e in ('e0','e1')],
                       'D':[slots[mapping[e]] for e in ('e4','e5','e6')]}
                keys={role:tuple(obs['edges'][s]['id'] for s in path) for role,path in paths.items()}
                with self.subTest(order=original['name'],variant=variant):
                    self.assertEqual(min(keys,key=keys.get),'S' if variant=='identity' else 'D')
                    self.assertEqual(max(keys,key=keys.get),'D' if variant=='identity' else 'S')

if __name__=='__main__': unittest.main()
