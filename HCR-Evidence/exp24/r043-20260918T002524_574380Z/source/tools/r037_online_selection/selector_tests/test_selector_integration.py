"""실제 R035 selector + 통제된 synthetic view 연결 검사. native Graph 실험이 아니다."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest

from r035_frozen_selection.contracts import Limits, ContractError
from r035_frozen_selection.selection import run_policy
from r037_online_selection.backend import NativeBackend
from r037_online_selection.contracts import Budget, SELECTION_LIMITS, digest
from r037_online_selection.runtime import OnlineTrial
from r037_online_selection.control_audit import audit_control

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tests'))
from helpers import FakeBackend, CONFIG, MEMORY


def view(complete=True):
    observation = dict(episode_id='selector-unit', revision=0, start='s', goal='g', edges=[
        dict(id='e0', source='s', target='a', score=1.0),
        dict(id='e1', source='a', target='g', score=1.0),
        dict(id='e2', source='s', target='b', score=None),
        dict(id='e3', source='b', target='g', score=1.0)])
    paths = [[2,3],[0,1]] if complete else [[2,3]]
    state = {'goal':.99, **{f'e:{i}':.9 for i in range(4)}}
    for pi,path in enumerate(paths):
        for j in range(len(path)):
            state[f'p:{pi}:{j}'] = .99 if pi == 0 else .9
    proof = dict(nodes=[
        dict(id='f2',rule='assumed_open',edge_id='e2',parents=[],path_index=None),
        dict(id='r0',rule='start_edge',edge_id=None,parents=['f2'],path_index=0),
        dict(id='f3',rule='assumed_open',edge_id='e3',parents=[],path_index=None),
        dict(id='r1',rule='extend_path',edge_id=None,parents=['r0','f3'],path_index=0)],
        final='r1',primitive_depth=2,assumed_edges=[['e2',True],['e3',True]],
        under_assumptions_valid=True,
        paths=[[observation['edges'][i]['id'] for i in path] for path in paths])
    return dict(schema='hcr-frozen-proof-view-r035-v1',observation=observation,
        raw_value=True,state=state,completed_paths=paths,graph_complete=complete,
        original_proof=proof,min_abs_score=0.0)


class ActualSelectorBackend(FakeBackend):
    """Graph/state만 synthetic. 정책 구현은 실제 baseline 모듈 그대로 사용한다."""
    kind = 'synthetic_graph_real_baseline_selector'

    def capture(self, session):
        candidate = super().capture(session)
        v = view(session.frame.get('complete',False))
        candidate['synthetic_view'] = v
        candidate['decision']['proof'] = deepcopy(v['original_proof'])
        return candidate

    select = NativeBackend.select


class SelectorIntegrationTests(unittest.TestCase):
    def test_missing_completed_support_stays_abstained(self):
        out=NativeBackend().select(view(False),'support_first',SELECTION_LIMITS)
        self.assertFalse(out['accepted'])
        self.assertEqual(out['reason'],'no_supported_existing_path')

    def test_existing_lower_activation_support_is_selected(self):
        out=NativeBackend().select(view(),'support_first',SELECTION_LIMITS)
        self.assertTrue(out['accepted']);self.assertEqual(out['selected_path_index'],1)
        self.assertIs(out['value'],True)
        self.assertEqual(out['proof']['primitive_depth'],2)
        self.assertEqual(out['proof']['assumed_edges'],[['e0',True],['e1',True]])

    def test_native_saved_proof_not_replaced(self):
        v=view();out=NativeBackend().select(v,'native_saved',SELECTION_LIMITS)
        self.assertFalse(out['accepted']);self.assertEqual(out['proof'],v['original_proof'])
        self.assertEqual(out['selected_path_index'],0)

    def test_view_and_original_proof_unmodified(self):
        v=view();before=deepcopy(v)
        NativeBackend().select(v,'support_first',SELECTION_LIMITS)
        self.assertEqual(v,before)

    def test_activation_ineligible_support_not_accepted(self):
        v=view();v['state']['e:0']=.49
        self.assertFalse(NativeBackend().select(v,'support_first',SELECTION_LIMITS)['accepted'])

    def test_zero_is_not_support(self):
        v=view();v['observation']['edges'][0]['score']=0
        self.assertFalse(NativeBackend().select(v,'support_first',SELECTION_LIMITS)['accepted'])

    def test_negative_evidence_does_not_flip_raw_value(self):
        v=view();v['observation']['edges'][0]['score']=-1.0
        out=NativeBackend().select(v,'support_first',SELECTION_LIMITS)
        self.assertFalse(out['accepted']);self.assertIsNone(out['value']);self.assertIs(v['raw_value'],True)

    def test_positive_observation_can_still_be_wrong_in_hidden_world(self):
        # selector는 외부 truth 인자를 받지 않는다. 아래 false는 synthetic 대조 라벨일 뿐이다.
        external_truth=False
        out=NativeBackend().select(view(),'support_first',SELECTION_LIMITS)
        self.assertTrue(out['accepted']);self.assertIsNot(out['value'],external_truth)

    def test_ranking_budget(self):
        out=run_policy(view(),'support_first',Limits(max_ranked_paths=1))
        self.assertEqual(out['reason'],'ranking_budget');self.assertFalse(out['accepted'])

    def test_scan_budget(self):
        out=run_policy(view(),'support_first',Limits(max_path_checks=1))
        self.assertEqual(out['reason'],'scan_budget');self.assertFalse(out['accepted'])

    def test_proof_budget(self):
        out=run_policy(view(),'support_first',Limits(max_proof_nodes=3))
        self.assertEqual(out['reason'],'proof_budget');self.assertFalse(out['accepted'])

    def test_nonpositive_raw_is_native_passthrough(self):
        v=view();v['raw_value']=None
        out=NativeBackend().select(v,'support_first',SELECTION_LIMITS)
        self.assertFalse(out['applicable']);self.assertFalse(out['accepted']);self.assertIsNone(out['value'])
        self.assertEqual(out['proof'],v['original_proof'])

    def test_hidden_field_rejected(self):
        v=view();v['external_truth']=True
        with self.assertRaises(ContractError):
            NativeBackend().select(v,'support_first',SELECTION_LIMITS)

    def test_online_adoption_controls_stop_after_actual_selector(self):
        backend=ActualSelectorBackend([
            dict(complete=False,frontier=True),dict(complete=True,frontier=True),
            {'raise':'must not execute after supported adoption'}])
        run=OnlineTrial(view()['observation'],CONFIG,MEMORY,'legacy','support_first',Budget(),backend=backend).run()
        self.assertTrue(run['adoption']['accepted']);self.assertEqual(len(run['candidates']),2)
        self.assertEqual(run['selections'][0]['reason'],'no_supported_existing_path')
        self.assertEqual(run['selections'][1]['selected_path_index'],1)
        self.assertTrue(audit_control(run,backend.session.states)['verified'])
        self.assertEqual(backend.session.calls,['advance','continue_dependency','advance'])

    def test_native_policy_does_not_use_supported_alternative(self):
        backend=ActualSelectorBackend([dict(complete=False,frontier=True),dict(complete=True,frontier=False)])
        run=OnlineTrial(view()['observation'],CONFIG,MEMORY,'legacy','native_saved',Budget(),backend=backend).run()
        self.assertFalse(run['adoption']['accepted'])
        self.assertEqual(run['adoption']['reason'],'stop_frontier_exhausted')
        self.assertTrue(audit_control(run,backend.session.states)['verified'])

    def test_selector_costs_accounted_separately_from_graph_ticks(self):
        backend=ActualSelectorBackend([dict(complete=False,frontier=True),dict(complete=True,frontier=False)])
        run=OnlineTrial(view()['observation'],CONFIG,MEMORY,'legacy','support_first',Budget(),backend=backend).run()
        self.assertEqual(run['usage']['initial_kernel_ticks']+run['usage']['extra_kernel_ticks'],6)
        self.assertEqual(run['usage']['selection']['edge_checks'],6)
        self.assertEqual(run['usage']['selection']['proof_nodes_created'],4)
        self.assertEqual(run['adoption']['proof_sha256'],digest(run['selections'][-1]['proof']))


if __name__ == '__main__':
    unittest.main()
