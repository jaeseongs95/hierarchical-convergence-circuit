from copy import deepcopy
import unittest
from r038_early_adoption import metrics,spec
from r038_early_adoption.tests._support import graph_view


class MetricsTests(unittest.TestCase):
    def test_examined_and_supported_are_not_same(self):
        v=graph_view(); r=metrics.assumption_counts(v,v['original_proof'])
        self.assertEqual(r,dict(assumptions_checked=2,supported_assumptions=1,unsupported_assumptions=1))

    def test_missing_and_zero_are_unsupported(self):
        for s in (None,0,0.0):
            v=graph_view(); v['observation']['edges'][2]['score']=s
            self.assertEqual(metrics.assumption_counts(v,v['original_proof'])['supported_assumptions'],1)

    def test_negative_supports_negative_assumption(self):
        v=graph_view();p={'assumed_edges':[['e4',False]]}
        self.assertEqual(metrics.assumption_counts(v,p)['supported_assumptions'],1)

    def test_threshold_is_strict(self):
        v=graph_view();v['min_abs_score']=.2;v['observation']['edges'][3]['score']=.2
        self.assertEqual(metrics.assumption_counts(v,v['original_proof'])['supported_assumptions'],0)

    def test_no_selected_proof_has_zero_assumptions(self):
        self.assertEqual(metrics.assumption_counts(graph_view(),None)['assumptions_checked'],0)

    def test_unknown_or_duplicate_assumptions_fail(self):
        for a in ([['unknown',True]],[['e0',True],['e0',True]],[['e0',1]]):
            with self.assertRaises(ValueError): metrics.assumption_counts(graph_view(),{'assumed_edges':a})

    def test_opportunity_requires_completed_support(self):
        self.assertFalse(metrics.opportunity(graph_view(1,True),False,2)['supported_frontier_opportunity'])

    def test_differential_opportunity_requires_all_four_conditions(self):
        self.assertTrue(metrics.opportunity(graph_view(2,True),False,1)['differential_opportunity'])

    def test_completed_graph_has_no_timing_opportunity(self):
        r=metrics.opportunity(graph_view(),False,0)
        self.assertTrue(r['supported_positive_available']);self.assertFalse(r['differential_opportunity'])

    def test_native_acceptance_removes_differential_opportunity(self):
        r=metrics.opportunity(graph_view(2,True),True,1)
        self.assertTrue(r['supported_frontier_opportunity']);self.assertFalse(r['differential_opportunity'])

    def test_ineligible_activation_does_not_count(self):
        v=graph_view(2,True);v['state']['e:0']=.49
        self.assertFalse(metrics.opportunity(v,False,1)['differential_opportunity'])

    def test_false_raw_does_not_count(self):
        v=graph_view();v['raw_value']=False
        self.assertFalse(metrics.opportunity(v,False,1)['differential_opportunity'])

    def test_frontier_at_candidate_uses_prefix_only(self):
        events=[dict(event='r02_workspace_created',payload={}),
            dict(event='r02_expansion',payload={'added':[{'visited':['s','g']},{'visited':['s','a']},{'visited':['s','c']}]}),
            dict(event='r02_expansion',payload={'added':[{'visited':['s','a','g']}]}),
            dict(event='r02_dead_end',payload={})]
        run={'packet':{'document':dict(engine={'pending':{'observation':{'goal':'g'}}},events=events,
                                       transitions=[{'event_end':i} for i in range(5)])}}
        for g,wanted in ((2,2),(3,1),(4,0)):
            self.assertEqual(metrics.frontier_at(run,{'reference':{'generation':g}}),wanted)

    def test_frontier_unmeasurable_is_not_zero(self):
        run={'packet':{'document':dict(engine={'pending':{'observation':{'goal':'g'}}},events=[],transitions=[{'event_end':0}])}}
        with self.assertRaises(ValueError): metrics.frontier_at(run,{'reference':{'generation':0}})

    def test_semantic_signature_keeps_work_not_time(self):
        a=[dict(event='tick',sha256='a',previous='x',payload=dict(wall_seconds=1.0,kernel_ticks=4,state={'x':.7}))]
        b=deepcopy(a);b[0]['sha256']='b';b[0]['payload']['wall_seconds']=2
        self.assertEqual(metrics.semantic_events(a),metrics.semantic_events(b))
        b[0]['payload']['kernel_ticks']=5
        self.assertNotEqual(metrics.semantic_events(a),metrics.semantic_events(b))

    def test_wrong_world_and_abstention_distinct(self):
        self.assertEqual(metrics.correctness(None,{'w':{'external_correct':None}}),'abstained')
        self.assertEqual(metrics.correctness(True,{'w':{'external_correct':False}}),'incorrect_in_some_declared_world')


class SpecificationTests(unittest.TestCase):
    def test_six_predeclared_topologies(self):
        cases=spec.new_cases();self.assertEqual(len(cases),6)
        self.assertEqual([c['topology']['edges'] for c in cases],[6,6,7,7,8,8])
        self.assertTrue(all(c['topology']['topology_paths']==3 for c in cases))

    def test_no_result_conditioned_case_generation(self):
        self.assertEqual(spec.new_cases(),spec.new_cases())
        self.assertFalse(spec.conditions()['opportunity_required_for_audit'])
        self.assertFalse(spec.conditions()['improvement_required_for_audit'])

    def test_grid_orders_and_lengths(self):
        for c in spec.new_cases():
            self.assertEqual(c['topology']['path_lengths'],[2,2,c['manipulation']['distractor_length']])
            first=c['observation']['edges'][0]['score']
            self.assertEqual(first,.92 if c['manipulation']['side_branch_order']=='early' else -.92)

    def test_world_is_evaluator_only(self):
        public=spec.public_cases(spec.new_cases())
        self.assertTrue(all('worlds' not in c for c in public))
        self.assertTrue(all('world' not in c['observation'] for c in public))

    def test_all_conditions_counted_once_per_arm(self):
        cs=[dict(name=n) for n in spec.BASE_CASES]+spec.new_cases()
        ts=spec.trials(cs);self.assertEqual(len(ts),84)
        self.assertEqual(len({(t['case'],t['scope'],t['arm']) for t in ts}),84)
        self.assertEqual(len({t['id'] for t in ts}),84)

    def test_input_identity_is_not_case_label(self):
        for c in spec.new_cases(): self.assertNotEqual(c['name'],c['observation']['episode_id'])

    def test_oversize_input_rejected(self):
        obs=deepcopy(spec.new_cases()[-1]['observation']);obs['edges'].append(dict(id='e8',source='s',target='z',score=1))
        with self.assertRaises(ValueError): spec.structural_inventory(obs)
