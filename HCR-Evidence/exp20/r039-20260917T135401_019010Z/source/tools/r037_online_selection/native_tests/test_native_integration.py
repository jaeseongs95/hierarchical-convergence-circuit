"""사용자 저장소에서 실행하는 실제 native self-test. 본 EXP-18 evidence와 별개다.

기본 엔진은 import 실패를 skip으로 숨기지 않는다. EXP-17 원자료와 native_saved parity를
검사하되 support_first의 정확도 향상을 구현 합격 조건으로 강제하지 않는다.
"""
from copy import deepcopy
import os
from pathlib import Path
import sys
import unittest

# 저장소 루트의 hcr.py가 src/hcr 패키지를 가리는 것을 막는다.
# R036 native integration test와 동일하게 src/tools를 import 최우선 경로로 고정한다.
ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT/'src'), str(ROOT/'tools')]

from r037_online_selection import io, sources, spec
from r037_online_selection.audit import audit_native
from r037_online_selection.contracts import Budget, digest
from r037_online_selection.runtime import OnlineTrial


class NativeIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from hcr.evaluation.selection_audit import source_view
        cls.source_view = staticmethod(source_view)
        cls.root = Path(os.environ.get('HCR_R037_SOURCE_RUN', sources.repo_root()/'HCR-Evidence/exp17/r036-first'))
        _, public, cls.seed, _ = sources.read_parent(cls.root)
        original = io.load(cls.root/'upstream/plan.json')
        cls.cases = {c['name']:c for c in original['conditions']['cases']}
        cls.results = {}
        for name in ('irrelevant_missing','weak_negative'):
            case = cls.cases[name]
            for scope in ('legacy','route_only'):
                for policy in ('native_saved','support_first'):
                    trial = dict(id='native-selftest',case=name,scope=scope,policy=policy)
                    run = OnlineTrial(case['observation'],cls.seed['config'],cls.seed['memory'],scope,policy,Budget()).run()
                    report,rows = audit_native(run,case['observation'],cls.seed,trial,spec.conditions(),case)
                    cls.results[(name,scope,policy)] = (run,report,rows)

    def test_all_native_sessions_independently_audited(self):
        for run, report, rows in self.results.values():
            self.assertEqual(run['backend'],'native_hcr')
            self.assertTrue(report['controller']['verified'])
            self.assertEqual(len(run['candidates']),len(rows))

    def test_same_native_first_input_before_policy(self):
        for name in ('irrelevant_missing','weak_negative'):
            for scope in ('legacy','route_only'):
                a=self.results[(name,scope,'native_saved')][2]
                b=self.results[(name,scope,'support_first')][2]
                self.assertEqual(a[0]['native_view_sha256'],b[0]['native_view_sha256'])

    def test_native_saved_matches_exp17_raw_views(self):
        manifest=io.load(self.root/'manifest.json')
        for name in ('irrelevant_missing','weak_negative'):
            case_index=spec.CASE_NAMES.index(name)
            for scope in ('legacy','route_only'):
                old_id=f't{case_index*16+(8 if scope=="route_only" else 0):04d}'
                path='raw/'+old_id+'.json'
                self.assertEqual(io.file_hash(self.root/path),manifest['files'][path])
                previous=io.load(self.root/path)['native']['flow']['candidates']
                run=self.results[(name,scope,'native_saved')][0]
                self.assertEqual(len(previous),len(run['candidates']))
                for old,new in zip(previous,run['candidates']):
                    fields=('observation','raw_value','state','completed_paths','graph_complete','original_proof','min_abs_score')
                    a,b=self.source_view(old),self.source_view(new)
                    self.assertEqual({k:a[k] for k in fields},{k:b[k] for k in fields})

    def test_raw_value_never_flipped_by_proof_selection(self):
        for run,_,_ in self.results.values():
            for c,s in zip(run['candidates'],run['selections']):
                self.assertIs(s['value'],c['decision']['value'] if s['accepted'] else None)

    def test_frozen_memory_preserved(self):
        for run,_,_ in self.results.values():
            self.assertEqual(run['packet']['document']['engine']['memory'],self.seed['memory'])

    def test_tampered_adoption_rejected(self):
        name,scope,policy='irrelevant_missing','legacy','support_first'
        run=deepcopy(self.results[(name,scope,policy)][0]);run['adoption']['accepted']=not run['adoption']['accepted']
        with self.assertRaises(ValueError):
            audit_native(run,self.cases[name]['observation'],self.seed,
                dict(id='tamper',case=name,scope=scope,policy=policy),spec.conditions(),self.cases[name])

    def test_unknown_parent_not_repaired(self):
        name,scope,policy='irrelevant_missing','legacy','support_first'
        run=deepcopy(self.results[(name,scope,policy)][0])
        run['candidates'][0]['decision']['proof']['nodes'][0]['parents']=['nonexistent-parent']
        with self.assertRaises(ValueError):
            audit_native(run,self.cases[name]['observation'],self.seed,
                dict(id='tamper',case=name,scope=scope,policy=policy),spec.conditions(),self.cases[name])
