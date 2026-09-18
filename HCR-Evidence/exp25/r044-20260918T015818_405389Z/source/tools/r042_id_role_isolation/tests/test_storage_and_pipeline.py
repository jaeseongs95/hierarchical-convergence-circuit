from copy import deepcopy
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch
import zipfile
from r042_id_role_isolation import storage as io, protocol, runtime, sources, audit, reporting
from r042_id_role_isolation.cli import bundle
from r042_id_role_isolation.tests.fixtures import plan_fixture,report_records


class StorageTests(unittest.TestCase):
    def test_duplicate_json_key(self):
        with self.assertRaises(io.ContractError): io.loads('{"x":1,"x":2}')

    def test_nonfinite_literal(self):
        for value in ('NaN','Infinity','-Infinity','1e999'):
            with self.subTest(value=value),self.assertRaises(io.ContractError): io.loads('{"x":'+value+'}')

    def test_nonfinite_serialization(self):
        with self.assertRaises(io.ContractError): io.canonical({'x':float('nan')})

    def test_exclusive_write(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'x.json';io.put(path,{'x':1})
            with self.assertRaises(FileExistsError): io.put(path,{'x':2})
            self.assertEqual(io.load(path),{'x':1})

    def test_inventory_path_boundary(self):
        with tempfile.TemporaryDirectory() as d:
            for name in ('../x','/tmp/x','a/../x','a\\x','C:/x','a//b','a/./b'):
                with self.subTest(name=name),self.assertRaises(io.ContractError): io.child(d,name)

    def test_disjoint(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(io.ContractError): io.disjoint(d,Path(d)/'child')

    @unittest.skipUnless(hasattr(os,'symlink'),'platform has no symlink API')
    def test_symlink_not_followed(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'real').mkdir()
            try: (root/'link').symlink_to(root/'real',target_is_directory=True)
            except OSError as exc: self.skipTest('symlink privilege unavailable: '+str(exc))
            with self.assertRaises(io.ContractError): io.child(root,'link/file')

    def test_text_hash_only_normalizes_checkout_newlines(self):
        with tempfile.TemporaryDirectory() as d:
            a,b=Path(d)/'a',Path(d)/'b';io.write_bytes(a,b'x\r\n');io.write_bytes(b,b'x\n')
            self.assertEqual(io.text_hash(a),io.text_hash(b))
            self.assertNotEqual(io.file_hash(a),io.file_hash(b))

    def test_hash_merge_collision(self):
        with self.assertRaises(io.ContractError): sources.merge_hashes({'a':'1'},{'a':'2'})

    def test_capsule_scope(self):
        self.assertEqual(sources.capsule_name('raw/t0005.json'),'basis/exp22/raw/t0005.json')
        self.assertEqual(sources.capsule_name('upstream/seed/6.json'),'upstream/seed/6.json')

    def test_forensic_bundle_preserves_failure(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'run';root.mkdir();io.put(root/'failure.json',{'status':'fixture_failure'})
            target=Path(d)/'failure.zip';result=bundle(root,target)
            self.assertFalse(result['complete_raw'])
            with zipfile.ZipFile(target) as z: self.assertIn('run/failure.json',z.namelist())
            with self.assertRaises(io.ContractError): bundle(root,target)


class PipelineTests(unittest.TestCase):
    def test_runtime_passes_only_public_arguments(self):
        captured={}
        class DummyBudget:
            def __init__(self,**kwargs): self.kwargs=kwargs
        class DummyWorker:
            def __init__(self,*args,**kwargs): captured.update(args=args,kwargs=kwargs)
        package=types.ModuleType('r041_scheduler_direction');package.__path__=[]
        rt=types.ModuleType('r041_scheduler_direction.runtime');rt.ScheduledTimingTrial=DummyWorker
        ct=types.ModuleType('r041_scheduler_direction.contracts');ct.Budget=DummyBudget
        modules={'r041_scheduler_direction':package,'r041_scheduler_direction.runtime':rt,'r041_scheduler_direction.contracts':ct}
        plan,_,seed=plan_fixture();obs=plan['cases'][0]['observation'];before=deepcopy(obs)
        with patch.dict(sys.modules,modules):
            runtime.worker(obs,seed['config'],seed['memory'],{'x':3},'edge_id_min',None)
        self.assertEqual(captured['args'][:5],(obs,seed['config'],seed['memory'],'legacy','online_support'))
        self.assertEqual(set(captured['kwargs']),{'scheduler','event_sink'})
        captured['args'][0]['edges'][0]['score']=123
        self.assertEqual(obs,before)

    def test_first_failure_preserved_without_retry(self):
        plan,_,seed=plan_fixture();plan['dependency_source_hashes']={};plan['addon_source_hashes']={};plan['parent_file_hashes']={}
        class Failed:
            def run(self): raise RuntimeError('intentional_unit_failure')
            def partial_evidence(self): return {'fixture_partial':True}
        with tempfile.TemporaryDirectory() as d:
            source=Path(d)/'source';source.mkdir();out=Path(d)/'out'
            with patch.object(protocol,'validate_plan',return_value=(source,{},seed,{})),\
                 patch.object(protocol,'repository_head',return_value=None),\
                 patch.object(runtime,'worker',return_value=Failed()) as worker:
                with self.assertRaisesRegex(RuntimeError,'intentional_unit_failure'): protocol.execute(plan,out)
                self.assertEqual(worker.call_count,1)
            failure=io.load(out/'failure.json')
            self.assertEqual(failure['completed_trials'],0)
            self.assertFalse(failure['automatic_retry'])
            self.assertTrue(failure['partial_evidence']['fixture_partial'])
            self.assertFalse((out/'manifest.json').exists())
            self.assertEqual(len((out/'attempts.jsonl').read_text().splitlines()),1)

    def test_synthetic_backend_rejected(self):
        plan,_,seed=plan_fixture();plan['dependency_source_hashes']={};plan['addon_source_hashes']={};plan['parent_file_hashes']={}
        class Synthetic:
            def run(self): return {'backend':'synthetic_fixture','base':{'backend':'synthetic_fixture'}}
            def partial_evidence(self): return {'fixture':True}
        with tempfile.TemporaryDirectory() as d:
            source=Path(d)/'source';source.mkdir();out=Path(d)/'out'
            with patch.object(protocol,'validate_plan',return_value=(source,{},seed,{})),\
                 patch.object(protocol,'repository_head',return_value=None),\
                 patch.object(runtime,'worker',return_value=Synthetic()):
                with self.assertRaisesRegex(io.ContractError,'synthetic'): protocol.execute(plan,out)
            self.assertEqual(io.load(out/'failure.json')['status'],'schema_contract_failure')

    def test_analysis_recomputed_not_blindly_trusted(self):
        records=report_records();summary=reporting.summarize(records)
        byid={r['trial']['id']:r for r in records}
        fake_audit={'verified':True,'raw_manifest_sha256':'unit_fixture_only'}
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            with patch.object(audit,'verify_raw',return_value=(summary,fake_audit,byid)):
                audit.write_analysis(root)
                audit.write_analysis(root,check_only=True)
                path=root/'analysis/summary.json';value=io.load(path);value['reversal_orders']=0
                path.write_bytes(io.canonical(value)+b'\n')
                with self.assertRaises(io.ContractError): audit.write_analysis(root,check_only=True)
                self.assertTrue(list((root/'audit_failures').glob('*.json')))

    def test_analysis_existing_not_overwritten(self):
        records=report_records();summary=reporting.summarize(records)
        with tempfile.TemporaryDirectory() as d:
            with patch.object(audit,'verify_raw',return_value=(summary,{'raw_manifest_sha256':'fixture'},{})):
                audit.write_analysis(d)
                with self.assertRaises(FileExistsError): audit.write_analysis(d)

    def test_failure_classification(self):
        examples=[(KeyboardInterrupt(),'interrupted'),(UnicodeError(),'parsing_failure'),
            (ImportError(),'dependency_failure'),(ValueError(),'schema_contract_failure'),
            (OSError(),'runtime_io_failure'),(RuntimeError(),'runtime_failure')]
        for exc,kind in examples:
            with self.subTest(kind=kind): self.assertEqual(protocol.failure_kind(exc),kind)

if __name__=='__main__': unittest.main()
