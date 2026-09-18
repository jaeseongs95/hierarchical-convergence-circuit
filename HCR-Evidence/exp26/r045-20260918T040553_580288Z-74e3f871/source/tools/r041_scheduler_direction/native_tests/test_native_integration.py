"""실제 native/priority replay 사전 검사. 실패를 skip/synthetic 성공으로 대체하지 않는다.

기존 대조 2개와 별도 contract probe 사용. 새 6개 순열을 사전 실행/선별하지 않는다.
54개 treatment self-test + R040 대조 6회 + API probe 1회. 본 108회와 별도다.
"""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tools')]
from copy import deepcopy
import os,unittest
from unittest.mock import patch
from r037_online_selection import io
from r037_online_selection.backend import NativeBackend
from r037_online_selection.runtime import OnlineTrial
from r038_early_adoption.runtime import TimingTrial
from r038_early_adoption.metrics import semantic_events
from r041_scheduler_direction import sources,spec,scheduler
from r041_scheduler_direction.runtime import ScheduledTimingTrial,ScheduledOnlineTrial
from r041_scheduler_direction.trial_audit import audit_trial,candidate_view
from r041_scheduler_direction.contracts import ARMS,SCHEDULERS


def probe(direction='min'):
    obs=dict(episode_id='r041-native-contract-probe-'+direction,revision=0,start='s',goal='g',edges=[
        dict(id='z0',source='s',target='b',score=None),dict(id='z1',source='b',target='g',score=.92),
        dict(id='y0',source='s',target='c',score=-.92),dict(id='y1',source='c',target='g',score=.92),
        dict(id='a0',source='s',target='a',score=.92),dict(id='a1',source='a',target='g',score=.92)])
    if direction=='max':
        obs['edges']=obs['edges'][:2]+obs['edges'][4:]+obs['edges'][2:4]
    worlds={}
    for value in (False,True):
        world={e['id']:True for e in obs['edges']};world.update(z0=value,y0=False);worlds[str(value)]=world
    return dict(name='contract_probe_'+direction,observation=obs,worlds=worlds,cohort='selftest_not_experiment')


class NativeIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source=Path(os.environ.get('HCR_R041_SOURCE_RUN',ROOT/'HCR-Evidence/exp21/r040-20260917T204742_957648Z'))
        _,_,cls.seed,_,_=sources.read_parent(cls.source)
        old=io.load(cls.source/'basis/exp20/basis/exp19/plan.json')
        cls.cases={c['name']:dict(c,worlds=old['evaluation_worlds'][c['name']]) for c in old['cases']
                   if c['name'] in ('irrelevant_missing','weak_negative')}
        cls.cases['contract_probe_min']=probe('min');cls.cases['contract_probe_max']=probe('max')
        cls.runs={};cls.reports={}
        for name,c in cls.cases.items():
            for scope in (('legacy',) if name.startswith('contract_probe') else ('legacy','route_only')):
                for arm in ARMS:
                    for schedule in SCHEDULERS:
                        key=(name,scope,arm,schedule)
                        trial=dict(id=f'selftest-{len(cls.runs)}',case=name,scope=scope,arm=arm,scheduler=schedule)
                        run=ScheduledTimingTrial(c['observation'],cls.seed['config'],cls.seed['memory'],scope,arm,scheduler=schedule).run()
                        cls.runs[key]=run;cls.reports[key]=audit_trial(run,trial,c,cls.seed,spec.conditions())

    def test_all_54_native_selftests_audited(self):
        self.assertEqual(len(self.runs),54)
        self.assertTrue(all(r['audit']['controller']['verified'] and r['wrapper']['verified'] for r in self.reports.values()))

    def test_priority_path_exercised_in_native_controller(self):
        counts=[r['base']['scheduler_usage']['priority_transitions'] for key,r in self.runs.items()
                if key[0]=='contract_probe_min' and key[3]=='edge_id_min']
        self.assertGreater(sum(counts),0,'contract probe가 priority 분기를 실행하지 못했습니다. 본 실험과 별도 coverage 실패입니다.')

    def test_both_retained_schedulers_match_R040(self):
        from r040_frontier_schedule.runtime import ScheduledTimingTrial as ParentTrial
        from r041_scheduler_direction.baseline_audit import compare_parent
        c=self.cases['irrelevant_missing']
        for policy in ('input_order','edge_id_min'):
            for arm in ARMS:
                previous=ParentTrial(c['observation'],self.seed['config'],self.seed['memory'],
                                     'legacy',arm,scheduler=policy).run()
                current=self.runs[('irrelevant_missing','legacy',arm,policy)]
                report=compare_parent(current,dict(run=previous,trial={'id':'R040-native-selftest'}))
                self.assertTrue(report['verified'])

    def test_max_priority_coverage(self):
        counts=[r['base']['scheduler_usage']['priority_transitions'] for key,r in self.runs.items()
                if key[0]=='contract_probe_max' and key[3]=='edge_id_max']
        self.assertGreater(sum(counts),0,'별도 contract probe에서 max priority API coverage 실패')

    def test_public_priority_operation_changes_only_frontier(self):
        from hcr.evaluation.review_audit import packet_states
        c=probe();backend=NativeBackend()
        session=backend.begin(c['observation'],self.seed['config'],self.seed['memory'],'legacy','r041-api-contract-test')
        session.advance()
        if session.phase=='readout_ready':session.continue_dependency()
        before=session.current;frontier=before['pending']['workspace']['frontier'];self.assertGreaterEqual(len(frontier),2)
        path=frontier[-1]['path'];self.assertEqual(session.prioritize_frontier(path),len(frontier)-1)
        expected=deepcopy(before);expected['pending']['workspace']['frontier']=[frontier[-1]]+frontier[:-1]
        self.assertEqual(session.current,expected)
        _,report=packet_states(session.packet());self.assertTrue(report['verified'])

    def test_frozen_memory_and_observation(self):
        for key,run in self.runs.items():
            core=run['base']['packet']['document']['engine']
            self.assertEqual(core['memory'],self.seed['memory'])
            self.assertEqual(core['pending']['observation'],self.cases[key[0]]['observation'])
            self.assertFalse(core['requests']);self.assertFalse(core['feedback'])

    def test_input_order_has_no_native_priority_calls(self):
        for key,run in self.runs.items():
            if key[3]=='input_order':
                self.assertNotIn('prioritize_frontier',[t['operation'] for t in run['base']['packet']['document']['transitions']])

    def test_scheduler_view_never_has_scores_or_worlds(self):
        for run in self.runs.values():
            for event in run['base']['events']:
                if event['event']=='schedule_requested':self.assertEqual(set(event['view']),{'schema','edge_ids','frontier_paths'})

    def test_raw_selection_value_preserved(self):
        for run in self.runs.values():
            for candidate,out in zip(run['base']['candidates'],run['base']['selections']):
                self.assertIs(out['value'],candidate['decision']['value'] if out['accepted'] else None)

    def test_no_missing_parent_correction(self):
        key=('contract_probe_min','legacy','online_support','edge_id_min');run=deepcopy(self.runs[key])
        run['base']['candidates'][0]['decision']['proof']['nodes'][0]['parents']=['missing-parent']
        with self.assertRaises(ValueError):audit_trial(run,self.reports[key]['trial'],self.cases[key[0]],self.seed,spec.conditions())

    def test_priority_counter_tampering_rejected(self):
        key=('contract_probe_min','legacy','online_support','edge_id_min');run=deepcopy(self.runs[key])
        run['base']['scheduler_usage']['priority_transitions']+=1
        with self.assertRaises(ValueError):audit_trial(run,self.reports[key]['trial'],self.cases[key[0]],self.seed,spec.conditions())

    def test_independent_audit_does_not_execute_production(self):
        from r035_frozen_selection import selection
        key=('contract_probe_min','legacy','posthoc_support','edge_id_min')
        with (
            patch.object(ScheduledTimingTrial,'run',side_effect=AssertionError('production')),
            patch.object(ScheduledOnlineTrial,'run',side_effect=AssertionError('production')),
            patch.object(OnlineTrial,'run',side_effect=AssertionError('production')),
            patch.object(scheduler,'choose',side_effect=AssertionError('production scheduler')),
            patch.object(selection,'run_policy',side_effect=AssertionError('production selector')),
        ):
            result=audit_trial(self.runs[key],self.reports[key]['trial'],self.cases[key[0]],self.seed,spec.conditions())
            self.assertTrue(result['audit']['controller']['verified'])
