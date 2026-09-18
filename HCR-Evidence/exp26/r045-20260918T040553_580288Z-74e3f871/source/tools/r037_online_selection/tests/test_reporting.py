from copy import deepcopy
import unittest
from r037_online_selection.reporting import summarize,render,csv_text
from r037_online_selection.audit import information,reachable


def fixture():
    rows=[];finals=[]
    for case in ('available','no_readout'):
        for scope in ('legacy','route_only'):
            for policy in ('native_saved','support_first'):
                tid='-'.join((case,scope,policy));available=case=='available'
                accepted=available and policy=='support_first'
                world={'w':dict(expected=True,external_correct=True if accepted else None)}
                final=dict(trial=dict(id=tid,case=case,scope=scope,policy=policy),
                    native_readouts=2 if available else 0,native_proof_nodes=4 if available else 0,
                    adoption=dict(accepted=accepted,value=True if accepted else None,
                                  reason='stop_supported_policy' if accepted else 'stop_frontier_exhausted' if available else 'stop_initial_budget'),
                    costs=dict(native_kernel_ticks=6 if available else 0,initial_kernel_ticks=3 if available else 0,
                        extra_kernel_ticks=3 if available else 0,selection_usage={'path_checks':2 if available else 0}),world_results=world)
                finals.append(final)
                if available:
                    for i in range(2):
                        yes=i==1 and accepted
                        rows.append(dict(trial_id=tid,case=case,scope=scope,policy=policy,ordinal=i,
                            first_readout=i==0,last_available_readout=i==1,native_view_sha256='common-'+str(i),
                            raw_value=True,native_value=None,policy_value=True if yes else None,policy_accepted=yes,
                            policy_reason='supported' if yes else 'no_supported_existing_path',D_DAG=2 if yes else None,
                            graph_complete=i==1,recovered_same_value_output=yes,kernel_ticks_at_readout=3*(i+1),
                            world_results={'w':dict(expected=True,external_correct=True if yes else None)}))
    return rows,finals


class ReportingTests(unittest.TestCase):
    def setUp(self):
        self.rows,self.finals=fixture();self.s=summarize(self.rows,self.finals)
    def test_cumulative_readout_cost_not_summed(self):
        self.assertEqual(self.s['unique_native_kernel_ticks'],24)
        self.assertEqual(sum(r['kernel_ticks_at_readout'] for r in self.rows),36)
    def test_first_last_not_independent_trials(self):
        self.assertEqual(self.s['native_trials'],8);self.assertEqual(self.s['base_cases'],2)
        self.assertEqual(self.s['prior_policy_pairs'],4)
    def test_no_readout_not_counted_as_measured_abstention(self):
        g=self.s['groups']['first_readout/legacy/native_saved']
        self.assertEqual((g['trials'],g['no_readout'],g['abstained']),(2,1,1))
    def test_same_state_pair(self):
        for p in self.s['paired']:
            if p['case']=='available':self.assertTrue(p['common_native_view_prefix_equal'])
            else:self.assertIsNone(p['first_native_view_equal'])
    def test_recovery_count_separate_from_correctness(self):
        rows,finals=fixture()
        for f in finals:
            if f['adoption']['accepted']:f['world_results']['w']['external_correct']=False
        s=summarize(rows,finals)
        self.assertEqual(sum(p['support_recovery'] for p in s['paired']),2)
        self.assertEqual(sum(p['recovered_correct_all_worlds'] for p in s['paired']),0)
    def test_multiple_worlds_not_counted_as_trials(self):
        rows,finals=fixture()
        for r in rows:r['world_results']['w2']=deepcopy(r['world_results']['w'])
        for f in finals:f['world_results']['w2']=deepcopy(f['world_results']['w'])
        s=summarize(rows,finals);self.assertEqual(s['native_trials'],8)
        self.assertEqual(s['groups']['terminal_adoption/legacy/support_first']['correct_all_worlds'],1)
    def test_improvement_not_required_for_summary(self):
        rows,finals=fixture()
        for r in rows:r['policy_accepted']=False;r['world_results']['w']['external_correct']=None
        for f in finals:f['adoption']['accepted']=False;f['world_results']['w']['external_correct']=None
        self.assertEqual(sum(p['support_recovery'] for p in summarize(rows,finals)['paired']),0)
    def test_render_and_csv(self):
        text=render(self.s);table=csv_text(self.rows)
        self.assertIn('미계측 scan은 null',text);self.assertIn('terminal_adoption',text)
        self.assertEqual(len(table.splitlines()),len(self.rows)+1)
    def test_information_missing_different_from_known_negative(self):
        obs=dict(start='s',goal='g',edges=[dict(id='x',source='s',target='g',score=None)])
        view=dict(observation=obs,min_abs_score=0.0)
        self.assertFalse(information(view)['identifiable'])
        obs['edges'][0]['score']=-0.1;self.assertIs(information(view)['value'],False)
    def test_information_zero_is_underdetermined(self):
        view=dict(observation=dict(start='s',goal='g',edges=[dict(id='x',source='s',target='g',score=0)]),min_abs_score=0.0)
        self.assertFalse(information(view)['identifiable'])
    def test_supported_observation_can_disagree_with_world(self):
        obs=dict(start='s',goal='g',edges=[dict(id='x',source='s',target='g',score=1)])
        self.assertIs(information(dict(observation=obs,min_abs_score=0.0))['value'],True)
        self.assertFalse(reachable(obs,{'x':False}))
