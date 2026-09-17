"""실제 사용자 저장소 엔진 통합시험. native/EXP-15 source 부재는 skip이 아니라 실패다."""
from pathlib import Path
import os
import sys
import unittest
from copy import deepcopy
ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tools')]
from r035_frozen_selection import storage as io
from r035_frozen_selection.contracts import digest,Limits
from r035_frozen_selection.native_bridge import project
from r035_frozen_selection.selection import run_policy
from r036_input_representation import sources,spec
from r036_input_representation.transforms import transform_input
from r036_input_representation.native_bridge import NativeTrial
from r036_input_representation.audit import check_native,check_transform,check_readouts


class NativeIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sources.check_dependencies()
        src=Path(os.environ.get('HCR_R036_SOURCE_RUN',str(ROOT/'HCR-Evidence/exp15/r034-first')))
        cls.source,_,p,seed=sources.read_source(src);cls.core=seed['document']['engine']
        cls.case=next(c for c in p['conditions']['cases'] if c['name']=='irrelevant_missing');cls.cp=spec.conditions()
        t=transform_input(cls.case['observation'],spec.variants()[0])
        cls.identity=cls.execute(t['observation'],'legacy')
    @classmethod
    def execute(cls,obs,scope,maximum=None):
        return NativeTrial(obs,cls.core['config'],cls.core['memory'],scope,
            cls.cp['max_initial_advances'] if maximum is None else maximum,cls.cp['continuation_limits']).run()
    def test_identity_matches_historical_first_semantics(self):
        old=io.load(self.source/'baselines/irrelevant_missing/legacy.json')['first']['decision']
        new=self.identity['baseline']['first']['decision']
        for k in ('value','expanded_paths','graph_complete','proof'):self.assertEqual(new[k],old[k])
        a=dict(new['state']);b=dict(old['state']);self.assertEqual(set(a),set(b))
        self.assertLessEqual(max(abs(a[k]-b[k]) for k in a),1e-10)
    def test_identity_native_and_controller_audit(self):
        report,views,_=check_native(self.identity,self.case['observation'],self.core,'legacy',self.cp)
        self.assertGreaterEqual(report['kernel_ticks'],0);self.assertTrue(views)
    def test_real_three_way_readout_audit(self):
        native=self.identity;compared=[]
        for i,c in enumerate(native['flow']['candidates']):
            v=project(c);compared.append(dict(ordinal=i,candidate_id=c['candidate_id'],candidate_sha256=digest(c),input_sha256=digest(v),
                results={p:run_policy(v,p,Limits()) for p in spec.POLICIES}))
        t=spec.trials([dict(name=self.case['name'])])[0]
        raw=dict(trial=t,native=native,transformed=transform_input(self.case['observation'],t['variant']),readouts=compared)
        _,views,_=check_native(native,self.case['observation'],self.core,'legacy',self.cp)
        rows,_=check_readouts(raw,views,self.case);self.assertEqual(len(rows),len(compared))
    def test_eight_input_variants_replay(self):
        for variant in spec.variants():
            t=transform_input(self.case['observation'],variant);check_transform(self.case['observation'],t,variant)
            native=self.identity if variant['id']=='i000' else self.execute(t['observation'],'legacy')
            check_native(native,t['observation'],self.core,'legacy',self.cp)
    def test_route_only_replay(self):
        n=self.execute(self.case['observation'],'route_only');check_native(n,self.case['observation'],self.core,'route_only',self.cp)
    def test_zero_initial_budget_no_fake_first(self):
        n=self.execute(self.case['observation'],'legacy',0);cp=deepcopy(self.cp);cp['max_initial_advances']=0
        report,views,_=check_native(n,self.case['observation'],self.core,'legacy',cp)
        self.assertIsNone(n['baseline']);self.assertEqual(views,[]);self.assertEqual(report['status'],'initial_budget_exhausted')
    def test_frozen_memory_preserved(self):
        self.assertEqual(self.identity['initial_packet']['document']['engine']['memory'],self.core['memory'])
        for p in self.identity['flow']['segments']:self.assertEqual(p['document']['engine']['memory'],self.core['memory'])
