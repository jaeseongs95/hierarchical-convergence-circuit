"""역방향 scheduler·불리한 불변 조건·독립 검산의 반례 self-test. 모두 합성이다."""
from copy import deepcopy
import itertools
import unittest
from unittest.mock import patch
from r041_scheduler_direction import scheduler,schedule_audit,reporting,spec
from r041_scheduler_direction.runtime import ScheduledTimingTrial,ScheduledOnlineTrial
from r041_scheduler_direction.control_audit import audit_control
from r041_scheduler_direction.contracts import Budget,SCHEDULERS,digest
from fixtures import OBS,CONFIG,MEMORY,Backend,core_for
from test_reporting_pipeline import fixture
from r040_frontier_schedule import scheduler as old_scheduler
from r040_frontier_schedule.runtime import ScheduledTimingTrial as OldTrial
from r041_scheduler_direction.baseline_audit import compare_parent


class MaxSchedulerTests(unittest.TestCase):
    def view(self,paths=None):
        return dict(schema='hcr-frontier-view-r041-v1',edge_ids=['a','z','m'],
                    frontier_paths=[[0],[1],[2]] if paths is None else paths)
    def test_max_is_not_slot_max(self):
        out=scheduler.choose(self.view(),'edge_id_max')
        self.assertEqual(out['selected_edge_ids'],['z']);self.assertEqual(out['selected_index'],1)
    def test_max_prefix_uses_tuple_order(self):
        out=scheduler.choose(self.view([[1],[1,2]]),'edge_id_max')
        self.assertEqual(out['selected_path'],[1,2])
    def test_max_root_path(self):
        out=scheduler.choose(self.view([[]]),'edge_id_max')
        self.assertEqual(out['selected_edge_ids'],[]);self.assertFalse(out['priority_required'])
    def test_max_empty_frontier(self):
        out=scheduler.choose(self.view([]),'edge_id_max')
        self.assertIsNone(out['selected_index']);self.assertEqual(out['usage']['key_comparisons'],0)
    def test_max_already_at_head(self):
        out=scheduler.choose(self.view([[1],[0]]),'edge_id_max')
        self.assertFalse(out['priority_required']);self.assertEqual(out['usage']['priority_match_scans'],0)
    def test_max_counts_same_work_as_min(self):
        # 중간 ID 기준으로 min/max 둘 다 head 이동이 필요한 조건.
        v=self.view([[2],[0],[1]])
        self.assertEqual(scheduler.choose(v,'edge_id_min')['usage'],scheduler.choose(v,'edge_id_max')['usage'])
    def test_max_no_mutation(self):
        v=self.view();old=deepcopy(v);scheduler.choose(v,'edge_id_max');self.assertEqual(v,old)
    def test_max_forbids_private_fields(self):
        for k in ('scores','truth','raw_value','case','branch_order','support'):
            with self.subTest(k=k),self.assertRaises(ValueError):scheduler.choose(dict(self.view(),**{k:1}),'edge_id_max')
    def test_max_rejects_duplicate_dependency(self):
        with self.assertRaises(ValueError):scheduler.choose(self.view([[0],[0]]),'edge_id_max')
    def test_36_identity_position_permutations(self):
        for ids in itertools.permutations(['a','z','m']):
            for order in itertools.permutations([[0],[1],[2]]):
                v=dict(self.view(),edge_ids=list(ids),frontier_paths=list(order))
                self.assertEqual(scheduler.choose(v,'edge_id_max')['selected_edge_ids'],['z'])
    def test_independent_max_spec_not_production(self):
        v=self.view()
        with patch.object(scheduler,'choose',side_effect=AssertionError('production')):
            _,answer=schedule_audit.expected_decision(core_for(v),'edge_id_max')
        self.assertEqual(answer['selected_edge_ids'],['z'])
    def test_old_policies_unchanged_except_versioned_envelope(self):
        for paths in ([[0],[1],[2]],[[2],[0]],[[]],[]):
            for policy in ('input_order','edge_id_min'):
                a=scheduler.choose(self.view(paths),policy)
                b=old_scheduler.choose(dict(self.view(paths),schema='hcr-frontier-view-r040-v1'),policy)
                for item in (a,b):item.pop('schema');item.pop('input_sha256')
                self.assertEqual(a,b)


class MaxControlTests(unittest.TestCase):
    def run_one(self,arm='online_support',budget=None,backend=None):
        b=backend or Backend();t=ScheduledTimingTrial(OBS,CONFIG,MEMORY,'legacy',arm,budget,
                                               scheduler='edge_id_max',backend=b)
        r=t.run();audit_control(r['base'],b.session.states)
        return r,b
    def test_slower_synthetic_max_result_is_valid(self):
        high,_=self.run_one();low=ScheduledTimingTrial(OBS,CONFIG,MEMORY,'legacy','online_support',
                            scheduler='edge_id_min',backend=Backend()).run()
        self.assertEqual((low['usage']['native_kernel_ticks'],high['usage']['native_kernel_ticks']),(6,9))
        self.assertTrue(high['final']['accepted']);self.assertEqual(low['final']['value'],high['final']['value'])
    def test_max_control_can_move_head(self):
        class ReverseBackend(Backend):
            def begin(self,*args):
                s=super().begin(*args);original=s.advance
                def advance():
                    # 합성 fixture의 초기 생성 순서만 바꾼다. 실제 실행에는 없는 test 더블이다.
                    if not s.current['pending']['workspace']['frontier'][0]['path']:
                        original()
                        s._core['pending']['workspace']['frontier'].reverse()
                        # synthetic state recorder이며 native seal 검사 대상이 아니다.
                        s.states[s.generation]=deepcopy(s._core)
                        s.transitions[-1]['after_state']=digest(s._core)
                    else: original()
                s.advance=advance
                return s
        r,b=self.run_one(backend=ReverseBackend())
        self.assertEqual(r['base']['scheduler_usage']['priority_transitions'],1)
        self.assertIn('prioritize_frontier',b.session.calls)
    def test_max_with_zero_extra_budget_has_no_priority(self):
        r,b=self.run_one(budget=Budget(max_extra_advances=0))
        self.assertEqual(r['base']['adoption']['reason'],'stop_compute_budget')
        self.assertNotIn('prioritize_frontier',b.session.calls)
    def test_max_audit_rejects_min_label(self):
        r,b=self.run_one();r['base']['scheduler']='edge_id_min'
        with self.assertRaises(ValueError):audit_control(r['base'],b.session.states)
    def test_max_audit_independent_of_choose(self):
        r,b=self.run_one()
        with patch.object(scheduler,'choose',side_effect=AssertionError('production')):
            self.assertTrue(audit_control(r['base'],b.session.states)['verified'])
    def test_both_previous_schedulers_can_regress(self):
        for policy in ('input_order','edge_id_min'):
            for arm in ('native','posthoc_support','online_support'):
                new=ScheduledTimingTrial(OBS,CONFIG,MEMORY,'legacy',arm,scheduler=policy,backend=Backend()).run()
                old=OldTrial(OBS,CONFIG,MEMORY,'legacy',arm,scheduler=policy,backend=Backend()).run()
                # 합성 candidate에는 별도 view가 있다. 실제 회귀에서는 native source_view를 쓴다.
                with patch('r041_scheduler_direction.baseline_audit.candidate_view',side_effect=lambda c:c['synthetic_view']):
                    report=compare_parent(new,dict(trial={'id':'old'},run=old))
                self.assertTrue(report['scheduler_decisions_equal'])
    def test_parent_scheduler_mismatch_rejected(self):
        new=ScheduledTimingTrial(OBS,CONFIG,MEMORY,'legacy','native',scheduler='edge_id_min',backend=Backend()).run()
        old=OldTrial(OBS,CONFIG,MEMORY,'legacy','native',scheduler='input_order',backend=Backend()).run()
        with self.assertRaises(ValueError):compare_parent(new,dict(trial={'id':'old'},run=old))
    def test_native_failure_not_retried(self):
        backend=Backend(selection_error=True)
        trial=ScheduledTimingTrial(OBS,CONFIG,MEMORY,'legacy','online_support',scheduler='edge_id_max',backend=backend)
        with self.assertRaises(RuntimeError):trial.run()
        self.assertEqual(len(trial.partial_evidence()['native_partial']['candidates']),1)
        with self.assertRaises(ValueError):trial.run()


class InvarianceEfficiencyTests(unittest.TestCase):
    def test_three_pairwise_contrasts_per_cell(self):
        r=reporting.summarize(fixture())
        self.assertEqual(len(r['scheduler_contrasts']),108)
        self.assertEqual(len(r['mediation']),12);self.assertEqual(len(r['invariance_efficiency']),6)
    def test_equal_cost_result_not_forced_into_predicted_pattern(self):
        r=reporting.summarize(fixture())
        self.assertTrue(all(x['finding']=='invariant_same_outcome_equal_native_cost' for x in r['invariance_efficiency']))
    def test_invariant_but_slower_is_valid(self):
        rows=fixture()
        for r in rows:
            if r['trial']['scheduler']=='edge_id_max':
                r['usage']['native_kernel_ticks']+=8;r['native_cost']['kernel_ticks']+=8
        report=reporting.summarize(rows)
        for item in report['invariance_efficiency']:
            self.assertTrue(item['both_native_tick_invariant'])
            self.assertEqual(item['max_minus_min_total_native_ticks'],48)
            self.assertEqual(item['max_is_more_expensive_pairs'],6)
            self.assertEqual(item['finding'],'invariant_same_outcome_different_native_cost')
    def test_faster_max_is_not_rejected(self):
        rows=fixture()
        for r in rows:
            if r['trial']['scheduler']=='edge_id_min':
                r['usage']['native_kernel_ticks']+=8;r['native_cost']['kernel_ticks']+=8
        report=reporting.summarize(rows)
        self.assertTrue(all(x['max_is_less_expensive_pairs']==6 for x in report['invariance_efficiency']))
    def test_noninvariant_max_is_retained(self):
        rows=fixture()
        for r in rows:
            if r['trial']['scheduler']=='edge_id_max' and r['trial']['case']=='order_DMS':
                r['usage']['native_kernel_ticks']+=8;r['native_cost']['kernel_ticks']+=8
        report=reporting.summarize(rows)
        self.assertTrue(all(not x['both_native_tick_invariant'] for x in report['invariance_efficiency']))
    def test_outcome_change_is_not_hidden_by_cost(self):
        rows=fixture()
        for r in rows:
            if r['trial']['scheduler']=='edge_id_max':
                r['classification']='incorrect_in_some_declared_world'
        report=reporting.summarize(rows)
        self.assertTrue(all(not x['all_paired_final_outcomes_equal'] for x in report['invariance_efficiency']))
    def test_case_dimension_duplicate_rejected_even_with_unique_ids(self):
        rows=fixture();rows[-1]['trial']['case']=rows[-2]['trial']['case']
        # same case already (fixture grouping), force duplicate complete tuple on purpose
        unique_id=rows[-1]['trial']['id'];rows[-1]['trial']=dict(rows[-2]['trial'],id=unique_id)
        with self.assertRaises(ValueError):reporting.summarize(rows)
    def test_report_does_not_add_scheduler_cost_to_ticks(self):
        r=reporting.summarize(fixture());self.assertNotIn('total_cost',r['costs'])
        self.assertIn('순열 불변성',reporting.__doc__)
    def test_max_effect_not_acceptance_condition(self):
        c=spec.conditions();self.assertTrue(c['slower_invariant_result_is_valid'])
        self.assertFalse(c['correctness_required_for_audit']);self.assertFalse(c['improvement_required_for_audit'])
