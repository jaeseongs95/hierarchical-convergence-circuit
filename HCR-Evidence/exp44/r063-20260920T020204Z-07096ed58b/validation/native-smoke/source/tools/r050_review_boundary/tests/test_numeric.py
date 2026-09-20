"""Synthetic numeric-event fixtures only; not native HCC research observations."""
from copy import deepcopy
import unittest
from tools.r050_review_boundary.audit import candidate_measures, numerical_comparison

TOL=dict(abs_tol=1e-12,rel_tol=1e-12)

def execution(identity='n',states=(.5,.6),final=.6):
    program=dict(groups=[{'id':'goal'}],links=[])
    events=[dict(event='r02_network',payload=dict(network_id=identity,kind='decision',program=program,top_down=False))]
    for tick,value in enumerate(states,1):
        events.append(dict(event='r02_tick',payload=dict(network_id=identity,tick=tick,state={'goal':value},residual=.1,stable_steps=0)))
    pending=dict(state={'goal':final},value=False,cost=dict(kernel_ticks=len(states)),
                 convergence=dict(status='stable_decision'),observation=dict(edges=[]),failure_reason=None)
    return dict(packet=dict(document=dict(events=events,engine=dict(pending=pending))),candidate=None,
                stop='external_compute_budget')

class NumericComparisons(unittest.TestCase):
    def test_identity_labels_are_not_numeric_differences(self):
        c=numerical_comparison(execution('original'),execution('new-session'),TOL)
        self.assertTrue(c['trajectory_close']);self.assertTrue(c['final_state_close'])
    def test_final_equality_does_not_imply_trajectory_equality(self):
        c=numerical_comparison(execution(states=(.4,.6)),execution(states=(.5,.6)),TOL)
        self.assertTrue(c['final_state_close']);self.assertFalse(c['trajectory_close'])
    def test_different_tick_count_not_interpolated(self):
        c=numerical_comparison(execution(states=(.4,.5,.6)),execution(states=(.4,.6)),TOL)
        self.assertFalse(c['trajectory_shape_equal']);self.assertFalse(c['trajectory_close'])
        self.assertIsNone(c['trajectory_max_abs_difference'])
    def test_declared_tolerance_is_applied(self):
        c=numerical_comparison(execution(),execution(states=(.5,.6+1e-14),final=.6+1e-14),TOL)
        self.assertTrue(c['final_state_close']);self.assertTrue(c['trajectory_close'])
    def test_large_numeric_difference_is_reported_not_raised(self):
        c=numerical_comparison(execution(),execution(states=(.5,.7),final=.7),TOL)
        self.assertFalse(c['final_state_close']);self.assertAlmostEqual(c['final_state_max_abs_difference'],.1)
    def test_empty_state_is_unknown_not_zero(self):
        a=execution();b=execution()
        a['packet']['document']['engine']['pending']['state']={}
        c=numerical_comparison(a,b,TOL)
        self.assertFalse(c['final_state_comparable']);self.assertIsNone(c['final_state_close'])
    def test_empty_tick_records_are_unmeasured(self):
        c=numerical_comparison(execution(states=()),execution(states=()),TOL)
        self.assertIsNone(c['trajectory_close'])
    def test_network_change_is_preserved(self):
        a=execution();b=execution();b['packet']['document']['events'][0]['payload']['top_down']=True
        c=numerical_comparison(a,b,TOL)
        self.assertFalse(c['network_structure_equal']);self.assertFalse(c['trajectory_close'])
    def test_state_key_mismatch_is_not_zero_filled(self):
        a=execution();b=execution()
        b['packet']['document']['engine']['pending']['state']['extra']=.1
        c=numerical_comparison(a,b,TOL)
        self.assertFalse(c['final_state_comparable']);self.assertIsNone(c['final_state_close'])
    def test_residual_difference_is_also_a_trajectory_difference(self):
        a=execution();b=execution();b['packet']['document']['events'][1]['payload']['residual']=.2
        c=numerical_comparison(a,b,TOL)
        self.assertFalse(c['trajectory_close']);self.assertEqual(c['trajectory_max_abs_difference'],0.)
    def test_partial_execution_retains_measured_state(self):
        m=candidate_measures(execution(),True)
        self.assertEqual(m['numeric_state'],{'goal':.6});self.assertIsNone(m['raw_correct'])
        self.assertEqual(m['failure_class'],'external_compute_budget')
    def test_native_expansion_budget_not_mislabelled_generic_failure(self):
        e=execution();p=e['packet']['document']['engine']['pending']
        p['failure_reason']='expansion budget fixture'
        e['candidate']={'decision':{'value':None,'proof':{'under_assumptions_valid':False,'nodes':[]},
                         'convergence':{'status':'budget_exhausted'}},
                        'readout':{'accepted':False},'diagnostic':{'support_gap_edges':[]}}
        self.assertEqual(candidate_measures(e,True)['failure_class'],'native_budget_termination')
    def test_non_budget_native_failure_remains_distinct(self):
        e=execution();p=e['packet']['document']['engine']['pending']
        p['failure_reason']='non-budget fixture'
        e['candidate']={'decision':{'value':None,'proof':{'under_assumptions_valid':False,'nodes':[]},
                         'convergence':{'status':'no_candidate'}},
                        'readout':{'accepted':False},'diagnostic':{'support_gap_edges':[]}}
        self.assertEqual(candidate_measures(e,True)['failure_class'],'native_failure')
    def test_comparison_never_mutates_evidence(self):
        a=execution();b=execution();saved=deepcopy([a,b])
        numerical_comparison(a,b,TOL)
        self.assertEqual([a,b],saved)

if __name__=='__main__':unittest.main()
