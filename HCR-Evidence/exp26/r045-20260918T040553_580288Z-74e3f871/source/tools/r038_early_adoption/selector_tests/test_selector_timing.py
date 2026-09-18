"""실제 R035 selector와 R038 wrapper 연결 검사. Graph/state는 합성이다."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT/'src'),str(ROOT/'tools')]
from copy import deepcopy
import unittest
from r035_frozen_selection.selection import run_policy
from r035_frozen_selection.contracts import Limits
from r037_online_selection.backend import NativeBackend
from r037_online_selection.control_audit import audit_control
from r038_early_adoption.contracts import ARMS,Budget,SELECTION_LIMITS,digest
from r038_early_adoption.runtime import TimingTrial
from r038_early_adoption.metrics import assumption_counts,opportunity
from r038_early_adoption.tests._support import FakeBackend,CONFIG,MEMORY,graph_view


class SelectorBackend(FakeBackend):
    kind = 'synthetic_graph_real_R035_selector'
    def capture(self,session):
        c=super().capture(session)
        v=graph_view(session.frame.get('count',1),session.frame.get('frontier',False))
        if session.frame.get('zero_support'): v['observation']['edges'][0]['score']=0
        if session.frame.get('bad_activation'): v['state']['e:0']=.49
        c['synthetic_view']=v;c['decision']['proof']=deepcopy(v['original_proof'])
        return c
    select = NativeBackend.select


def execute(arm,fs=None,budget=None):
    b=SelectorBackend(fs or [dict(count=1,frontier=True),dict(count=2,frontier=True),dict(count=3,frontier=False)])
    w=TimingTrial(graph_view()['observation'],CONFIG,MEMORY,'legacy',arm,budget,backend=b)
    r=w.run();audit_control(r['base'],b.session.states)
    return r,b


class SelectorTimingTests(unittest.TestCase):
    def test_real_selector_three_arms(self):
        r={a:execute(a)[0] for a in ARMS}
        self.assertIsNone(r['native']['final']['value'])
        self.assertIs(r['posthoc_support']['final']['value'],True)
        self.assertIs(r['online_support']['final']['value'],True)
        self.assertEqual([r[a]['usage']['native_kernel_ticks'] for a in ARMS],[9,9,6])

    def test_actual_selected_proof_binds_supported_branch(self):
        for arm in ('online_support','posthoc_support'):
            r,b=execute(arm)
            out=r['posthoc_selection'] if arm=='posthoc_support' else r['base']['selections'][-1]
            self.assertEqual(out['proof']['assumed_edges'],[['e0',True],['e1',True]])
            self.assertEqual(out['proof']['primitive_depth'],2)
            self.assertEqual(out['selected_path_index'],1)
            self.assertEqual(r['final']['proof_sha256'],digest(out['proof']))

    def test_first_missing_path_is_not_repaired(self):
        r,b=execute('online_support')
        first=r['base']['selections'][0]
        self.assertFalse(first['accepted']);self.assertIsNone(first['proof'])
        self.assertEqual(first['reason'],'no_supported_existing_path')

    def test_actual_selector_does_not_flip_false_raw(self):
        v=graph_view();v['raw_value']=False
        # 부정 proof를 별도로 검색하지 않는 실제 기존 selector 계약만 검사한다.
        out=run_policy(v,'support_first')
        self.assertFalse(out['applicable']);self.assertEqual(out['proof'],v['original_proof'])
        self.assertIn(out['value'],(False,None))

    def test_actual_selector_none_raw_passthrough(self):
        v=graph_view();v['raw_value']=None
        out=run_policy(v,'support_first')
        self.assertIsNone(out['value']);self.assertFalse(out['accepted'])

    def test_real_selector_requires_activation(self):
        v=graph_view(2,True);v['state']['e:0']=.49
        self.assertFalse(run_policy(v,'support_first')['accepted'])
        self.assertFalse(opportunity(v,False,1)['differential_opportunity'])

    def test_real_selector_requires_observation_support(self):
        v=graph_view(2,True);v['observation']['edges'][0]['score']=0
        self.assertFalse(run_policy(v,'support_first')['accepted'])

    def test_native_proof_remains_original(self):
        r,b=execute('posthoc_support')
        self.assertTrue(all(x['proof']['assumed_edges']==[['e2',True],['e3',True]] for x in r['base']['selections']))
        self.assertEqual(assumption_counts(b.project(r['base']['candidates'][-1]),r['base']['selections'][-1]['proof'])['supported_assumptions'],1)

    def test_actual_posthoc_scans_are_separate_cost(self):
        r,b=execute('posthoc_support')
        self.assertEqual(r['usage']['native_kernel_ticks'],9)
        self.assertEqual(r['usage']['posthoc_selection_calls'],1)
        self.assertEqual(r['usage']['posthoc_selection']['edge_checks'],4)
        self.assertEqual(r['usage']['posthoc_selection']['proof_nodes_created'],4)
        self.assertEqual(r['usage']['online_selection']['proof_nodes_created'],0)

    def test_real_selector_can_accept_before_graph_complete(self):
        r,b=execute('online_support')
        last=r['base']['candidates'][-1]
        self.assertFalse(b.project(last)['graph_complete'])
        self.assertTrue(r['base']['packet']['document']['engine']['pending']['workspace']['frontier'])
        self.assertTrue(r['final']['accepted'])

    def test_same_kernel_work_if_support_arrives_last(self):
        fs=[dict(count=1,frontier=True),dict(count=2,frontier=False)]
        a,_=execute('posthoc_support',fs);b,_=execute('online_support',fs)
        self.assertEqual(a['usage']['native_kernel_ticks'],b['usage']['native_kernel_ticks'])

    def test_actual_selector_budget_failure_is_not_success(self):
        for limit,reason in ((Limits(max_ranked_paths=1),'ranking_budget'),
                             (Limits(max_edge_checks=1),'scan_budget'),(Limits(max_proof_nodes=1),'proof_budget')):
            with self.subTest(reason=reason):
                out=run_policy(graph_view(),'support_first',limit)
                self.assertFalse(out['accepted']);self.assertEqual(out['reason'],reason)

    def test_misleading_world_does_not_enter_selector(self):
        out=run_policy(graph_view(),'support_first')
        declared_world_answer=False
        self.assertTrue(out['accepted']);self.assertIsNot(out['value'],declared_world_answer)

    def test_unknown_private_field_is_rejected(self):
        v=graph_view();v['worlds']={'declared':False}
        with self.assertRaises(ValueError): run_policy(v,'support_first')
