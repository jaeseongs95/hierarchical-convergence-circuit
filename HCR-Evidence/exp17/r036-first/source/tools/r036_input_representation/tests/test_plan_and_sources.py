import unittest
from tempfile import TemporaryDirectory
from pathlib import Path
from contextlib import ExitStack
from unittest.mock import patch
from copy import deepcopy
from r036_helpers import observation
from r035_frozen_selection import storage as io
from r035_frozen_selection.contracts import digest
from r036_input_representation import protocol,sources,spec


class PlanTests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name);self.source=self.root/'upstream';self.source.mkdir()
        self.stack=ExitStack();self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(sources,'check_dependencies',return_value={'files':{}}))
        self.hashes=self.stack.enter_context(patch.object(sources,'code_hashes',return_value={}))
        cases=[dict(name='c'+str(i),family='synthetic',observation=observation(),worlds={'one':dict(e0=True,e1=True,e2=False,e3=True)}) for i in range(8)]
        self.old=dict(schema='hcr-exp15-plan-v1',source_hashes={},conditions=dict(cases=cases,scopes=['legacy','route_only'],training_count=6,protocol='exp15-r034-proof-selection-v1'))
        io.put(self.source/'plan.json',self.old);io.put(self.source/'training.json',[])
        seed=dict(document=dict(engine=dict(memory={'synthetic':True},config={'synthetic':True})));seed['sha256']=digest(seed['document'])
        io.put(self.source/'seed/6.json',seed)
        io.put(self.source/'manifest.json',dict(schema='hcr-exp15-raw-manifest-v1',state='raw_complete',files={n:io.file_hash(self.source/n) for n in sources.UPSTREAM_FILES[1:]}))
    def test_plan_population_128(self):
        p=protocol.make_plan(self.source);self.assertEqual(len(p['trials']),128);protocol.validate_plan(p)
    def test_plan_has_no_world_in_worker_cases(self):
        p=protocol.make_plan(self.source);self.assertTrue(all(set(c)=={'name','family','observation'} for c in p['cases']))
    def test_plan_writes_only_new_path(self):
        out=self.root/'new.plan.json';protocol.prepare(self.source,out)
        with self.assertRaises(ValueError):protocol.prepare(self.source,out)
    def test_plan_not_inside_source(self):
        with self.assertRaises(ValueError):protocol.prepare(self.source,self.source/'new.plan.json')
    def test_conditions_drift_rejected(self):
        p=protocol.make_plan(self.source);p['conditions']['max_initial_advances']=63
        with self.assertRaises(ValueError):protocol.validate_plan(p)
    def test_bool_integer_confusion_rejected(self):
        p=protocol.make_plan(self.source);p['conditions']['memory_frozen']=1
        with self.assertRaises(ValueError):protocol.validate_plan(p)
    def test_matrix_drift_rejected(self):
        p=protocol.make_plan(self.source);p['trials'].pop()
        with self.assertRaises(ValueError):protocol.validate_plan(p)
    def test_source_change_rejected(self):
        p=protocol.make_plan(self.source);f=self.source/'training.json';f.unlink();io.put(f,[1])
        with self.assertRaises(ValueError):protocol.validate_plan(p)
    def test_tool_change_rejected(self):
        p=protocol.make_plan(self.source);self.hashes.return_value={'new':'a'*64}
        with self.assertRaises(ValueError):protocol.validate_plan(p)
    def test_memory_hash_change_rejected(self):
        p=protocol.make_plan(self.source);p['memory_sha256']='0'*64
        with self.assertRaises(ValueError):protocol.validate_plan(p)
    def test_seed_checksum_rejected(self):
        f=self.source/'seed/6.json';x=io.load(f);x['sha256']='0'*64;f.unlink();io.put(f,x)
        m=io.load(self.source/'manifest.json');m['files']['seed/6.json']=io.file_hash(f)
        (self.source/'manifest.json').unlink();io.put(self.source/'manifest.json',m)
        with self.assertRaises(ValueError):sources.read_source(self.source)
    def test_verify_plan_does_not_need_original_source_path(self):
        p=protocol.make_plan(self.source);p['source_run']='/missing/not-used-during-audit'
        self.assertIsNone(protocol.validate_plan(p,check_upstream=False))
