"""Synthetic 출처 fixture로 동결/복사/실패 보존만 검사한다. native 과학 결과가 아니다."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from r037_online_selection import io,spec,sources,protocol
from r037_online_selection.contracts import ContractError,digest
from helpers import OBS,CONFIG,MEMORY,FakeBackend
from r037_online_selection.runtime import OnlineTrial


def make_parent(root):
    cases=[]
    for n in spec.CASE_NAMES:
        obs=deepcopy(OBS);obs['episode_id']=n
        cases.append(dict(name=n,family='synthetic',observation=obs,worlds={'w':{'e0':True}}))
    old=dict(schema='hcr-exp15-plan-v1',source_hashes={},conditions=dict(training_count=6,cases=cases))
    core=dict(config=CONFIG,memory=MEMORY)
    doc={'engine':core};seed=dict(document=doc,sha256=digest(doc))
    io.put(root/'upstream/plan.json',old);io.put(root/'upstream/seed/6.json',seed);io.put(root/'upstream/training.json',[])
    io.put(root/'upstream/manifest.json',dict(schema='hcr-exp15-raw-manifest-v1',state='raw_complete',
        files={n:io.file_hash(root/'upstream'/n) for n in ('plan.json','seed/6.json','training.json')}))
    public=[{k:c[k] for k in ('name','family','observation')} for c in cases]
    parent=dict(schema='hcr-exp17-plan-v1',cases=public,dependency_source_hashes={},
                memory_sha256=digest(MEMORY),config_sha256=digest(CONFIG))
    io.put(root/'plan.json',parent)
    io.put(root/'manifest.json',dict(schema='hcr-exp17-raw-manifest-v1',state='raw_complete',
        files={n:io.file_hash(root/n) for n in sources.PARENT_FILES[1:]}))


class SourcesProtocolTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.parent=self.root/'parent'
        make_parent(self.parent)
        self.dep=patch.object(sources,'dependencies',return_value={});self.dep.start()
        self.code=patch.object(sources,'code_hashes',return_value={});self.code.start()
    def tearDown(self):
        self.dep.stop();self.code.stop();self.tmp.cleanup()
    def test_make_plan_uses_all_eight_cases(self):
        plan=protocol.make_plan(self.parent)
        self.assertEqual(len(plan['cases']),8);self.assertEqual(len(plan['trials']),32)
        self.assertTrue(all(set(c)=={'name','family','observation'} for c in plan['cases']))
    def test_original_seed_reused_without_training(self):
        plan=protocol.make_plan(self.parent);self.assertEqual(plan['memory_sha256'],digest(MEMORY))
        self.assertFalse(plan['conditions']['retraining'])
    def test_plan_revalidation(self):
        plan=protocol.make_plan(self.parent);self.assertEqual(protocol.validate_plan(plan),self.parent)
    def test_plan_policy_swap_rejected(self):
        plan=protocol.make_plan(self.parent);plan['trials'][0]['policy']='support_first'
        with self.assertRaises(ContractError):protocol.validate_plan(plan)
    def test_population_deletion_rejected(self):
        plan=protocol.make_plan(self.parent);plan['trials'].pop()
        with self.assertRaises(ContractError):protocol.validate_plan(plan)
    def test_changed_sources_after_freeze_rejected(self):
        plan=protocol.make_plan(self.parent)
        with patch.object(sources,'code_hashes',return_value={'changed.py':'x'}):
            with self.assertRaises(ContractError):protocol.validate_plan(plan)
    def test_upstream_corruption_rejected(self):
        plan=protocol.make_plan(self.parent);(self.parent/'upstream/training.json').write_text('corrupted')
        with self.assertRaises(ContractError):protocol.validate_plan(plan)
    def test_existing_plan_not_overwritten(self):
        target=self.root/'plan.json';protocol.prepare(self.parent,target)
        original=target.read_bytes()
        with self.assertRaises(ContractError):protocol.prepare(self.parent,target)
        self.assertEqual(target.read_bytes(),original)
    def test_plan_inside_source_rejected(self):
        with self.assertRaises(ContractError):protocol.prepare(self.parent,self.parent/'newplan.json')
    def test_output_inside_source_rejected(self):
        plan=protocol.make_plan(self.parent)
        with self.assertRaises(ContractError):protocol.execute(plan,self.parent/'newoutput')
    def test_existing_output_rejected(self):
        plan=protocol.make_plan(self.parent);out=self.root/'out';out.mkdir()
        with self.assertRaises(FileExistsError):protocol.execute(plan,out)
    def test_runtime_failure_retained_no_retry(self):
        plan=protocol.make_plan(self.parent);out=self.root/'failure'
        def factory(obs,cfg,mem,scope,policy,budget,**kwargs):
            return OnlineTrial(obs,cfg,mem,scope,policy,budget,backend=FakeBackend(selection_error=True),**kwargs)
        with patch.object(protocol,'OnlineTrial',side_effect=factory) as p:
            with self.assertRaises(RuntimeError):protocol.execute(plan,out)
            self.assertEqual(p.call_count,1)
        failure=io.load(out/'failure.json');self.assertEqual(failure['status'],'runtime_failure')
        self.assertEqual(len(failure['partial_evidence']['candidates']),1)
        self.assertFalse((out/'manifest.json').exists())
        stream=[io.loads(x) for x in (out/'attempts.jsonl').read_text().splitlines()]
        self.assertEqual(sum(e['event']=='trial_started' for e in stream),1)
    def test_synthetic_backend_rejected_in_experiment(self):
        plan=protocol.make_plan(self.parent);out=self.root/'synthetic'
        def factory(obs,cfg,mem,scope,policy,budget,**kwargs):
            return OnlineTrial(obs,cfg,mem,scope,policy,budget,backend=FakeBackend(),**kwargs)
        with patch.object(protocol,'OnlineTrial',side_effect=factory):
            with self.assertRaises(ContractError):protocol.execute(plan,out)
        self.assertEqual(io.load(out/'failure.json')['status'],'schema_contract_failure')
        self.assertFalse((out/'manifest.json').exists())
    def test_failure_nonfinite_partial_preserved_as_repr(self):
        target=self.root/'badjson';target.mkdir()
        io.write_failure(target,dict(status='schema_contract_failure',partial_evidence={'score':float('nan')}))
        record=io.load(target/'failure.json');self.assertIn('partial_evidence_serialization_error',record)
        self.assertIn('nan',(target/'failure-partial.repr.txt').read_text())
