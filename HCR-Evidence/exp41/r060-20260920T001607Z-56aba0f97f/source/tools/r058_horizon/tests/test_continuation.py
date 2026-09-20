"""Producer continuation checks with a one-group synthetic system."""
from copy import deepcopy
import unittest
from tools.r053_feedback.tests.test_audit import CONFIG
from tools.r058_horizon.worker import execute_continued

PROGRAM=dict(edge_count=1,groups=[dict(id='goal',level=1,bias=0.0)],links=[],paths=[[0]])


class ContinuationTests(unittest.TestCase):
    def test_stable_marker_preserved_and_counter_not_reset(self):
        initial={'goal':.5}
        result=execute_continued(PROGRAM,{},CONFIG,initial,512)
        marker=result['first_termination']
        self.assertEqual(marker['convergence']['status'],'stable_ambiguous')
        self.assertEqual(marker['convergence']['ticks'],4)
        self.assertEqual(result['ticks'][4]['stable_steps'],5)
        self.assertEqual(result['ticks'][-1]['stable_steps'],512)
        self.assertEqual(marker['cost']['kernel_ticks'],4)
        self.assertEqual(result['continuation_cost']['kernel_ticks'],508)
        self.assertEqual(result['cost']['kernel_ticks'],512)
        self.assertEqual(initial,{'goal':.5})

    def test_budget_marker_retained_after_later_stability(self):
        cfg={**CONFIG,'damping':.5,'self_excitation':0.0,'inhibition':0.0,'max_ticks':4}
        result=execute_continued(PROGRAM,{'goal':1e6},cfg,{'goal':.5},512)
        self.assertEqual(result['first_termination']['convergence']['status'],'budget_exhausted')
        self.assertEqual(result['first_termination']['final_state']['goal'],.96875)
        self.assertEqual(result['ticks'][4]['state']['goal'],.984375)
        self.assertGreater(result['ticks'][-1]['stable_steps'],4)

    def test_oscillation_marker_retained_and_suffix_continues(self):
        program=deepcopy(PROGRAM)
        program['links']=[dict(source='goal',target='goal',weight=-1e6,kind='support')]
        cfg={**CONFIG,'damping':1.0,'self_excitation':0.0,'inhibition':0.0,'max_ticks':4}
        result=execute_continued(program,{},cfg,{'goal':1.0},512)
        self.assertEqual(result['first_termination']['convergence']['status'],'oscillating')
        self.assertEqual(result['first_termination']['convergence']['ticks'],2)
        self.assertEqual([t['state']['goal'] for t in result['ticks'][:4]],[0.0,1.0,0.0,1.0])
        self.assertEqual(result['cost']['kernel_ticks'],512)


if __name__=='__main__':unittest.main()
