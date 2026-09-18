"""원 저장소 필수 native 사전 검사. 신규 EXP20 순열 입력을 사전에 실행/선별하지 않는다.

기존 2개 대조 입력 × prior 2개 × arm 3개만 사용한다. import/출처 실패는 skip이 아니다.
"""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT/'src'),str(ROOT/'tools')]
from copy import deepcopy
import os
import unittest
from unittest.mock import patch
from r037_online_selection import io
from r039_order_isolation import sources,spec
from r038_early_adoption.runtime import TimingTrial
from r038_early_adoption.audit import audit_trial,candidate_view
from r038_early_adoption.contracts import ARMS,digest
from r038_early_adoption.reporting import summarize


class NativeIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source=Path(os.environ.get('HCR_R039_SOURCE_RUN',ROOT/'HCR-Evidence/exp19/r038-20260917T121349_552337Z'))
        _,_,cls.seed,_,_=sources.read_parent(cls.source)
        cls.oldplan=io.load(cls.source/'plan.json')
        cls.cases={c['name']:dict(c,worlds=cls.oldplan['evaluation_worlds'][c['name']]) for c in cls.oldplan['cases']}
        cls.runs={};cls.reports={}
        for name in ('irrelevant_missing','weak_negative'):
            c=cls.cases[name]
            for scope in ('legacy','route_only'):
                for arm in ARMS:
                    trial=dict(id=f'native-selftest-{name}-{scope}-{arm}',case=name,scope=scope,arm=arm)
                    run=TimingTrial(c['observation'],cls.seed['config'],cls.seed['memory'],scope,arm).run()
                    cls.runs[(name,scope,arm)]=run
                    cls.reports[(name,scope,arm)]=audit_trial(run,trial,c,cls.seed,spec.conditions())

    def test_all_native_trials_independently_audited(self):
        self.assertEqual(len(self.runs),12)
        self.assertTrue(all(r['wrapper']['verified'] and r['audit']['controller']['verified'] for r in self.reports.values()))

    def test_native_posthoc_work_and_online_prefix(self):
        s=summarize(list(self.reports.values()))
        self.assertTrue(all(p['first_view_equal'] and p['native_posthoc_full_trace_equal'] and
                            p['native_posthoc_cost_equal'] and p['online_is_native_prefix'] for p in s['paired']))

    def test_native_saved_matches_preserved_exp19(self):
        m=io.load(self.source/'manifest.json')
        for name in ('irrelevant_missing','weak_negative'):
            for scope in ('legacy','route_only'):
                oldtrial=next(t for t in self.oldplan['trials'] if t['case']==name and t['scope']==scope and t['arm']=='native')
                path='raw/'+oldtrial['id']+'.json'
                self.assertEqual(io.file_hash(self.source/path),m['files'][path])
                previous=io.load(self.source/path)['run']['base']
                current=self.runs[(name,scope,'native')]['base']
                self.assertEqual([candidate_view(c) for c in previous['candidates']],
                                 [candidate_view(c) for c in current['candidates']])
                self.assertEqual(previous['usage'],current['usage'])

    def test_frozen_memory_and_no_measurement(self):
        for run in self.runs.values():
            core=run['base']['packet']['document']['engine']
            self.assertEqual(core['memory'],self.seed['memory']);self.assertFalse(core['requests'])

    def test_new_support_count_regression(self):
        r=self.reports[('irrelevant_missing','legacy','native')]
        first=r['readouts'][0]['native_assumption_counts']
        self.assertEqual(first,dict(assumptions_checked=2,supported_assumptions=1,unsupported_assumptions=1))

    def test_existing_source_failure_not_host_corrected(self):
        run=deepcopy(self.runs[('irrelevant_missing','legacy','native')])
        run['base']['candidates'][0]['decision']['proof']['nodes'][0]['parents']=['missing-parent']
        t=self.reports[('irrelevant_missing','legacy','native')]['trial']
        with self.assertRaises(ValueError): audit_trial(run,t,self.cases['irrelevant_missing'],self.seed,spec.conditions())

    def test_posthoc_tampering_rejected(self):
        run=deepcopy(self.runs[('irrelevant_missing','legacy','posthoc_support')]);run['final']['value']=False
        t=self.reports[('irrelevant_missing','legacy','posthoc_support')]['trial']
        with self.assertRaises(ValueError): audit_trial(run,t,self.cases['irrelevant_missing'],self.seed,spec.conditions())

    def test_auditor_does_not_execute_production_runtime_or_selector(self):
        from r037_online_selection.runtime import OnlineTrial
        from r035_frozen_selection import selection
        key=('irrelevant_missing','legacy','posthoc_support');t=self.reports[key]['trial']
        with patch.object(TimingTrial,'run',side_effect=AssertionError('production')), \
             patch.object(OnlineTrial,'run',side_effect=AssertionError('production')), \
             patch.object(selection,'run_policy',side_effect=AssertionError('production')):
            report=audit_trial(self.runs[key],t,self.cases[key[0]],self.seed,spec.conditions())
            self.assertTrue(report['wrapper']['verified'])
