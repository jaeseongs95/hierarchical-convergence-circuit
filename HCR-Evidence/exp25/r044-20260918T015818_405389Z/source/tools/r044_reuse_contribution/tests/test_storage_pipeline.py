from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import json
import unittest
import zipfile
from r044_reuse_contribution import storage as io,protocol,cli,audit,reporting
from r044_reuse_contribution.tests.fixtures import plan_fixture,report_records

class Storage(unittest.TestCase):
    def test_json_rejects_duplicates_nonfinite(self):
        for value in ('{"x":1,"x":2}','{"x":NaN}','{"x":1e999}'):
            with self.subTest(value=value),self.assertRaises(ValueError):io.loads(value)
    def test_no_overwrite(self):
        with TemporaryDirectory() as d:
            p=Path(d)/'raw.json';io.put(p,{'x':1})
            with self.assertRaises(FileExistsError):io.put(p,{'x':2})
            self.assertEqual(io.load(p),{'x':1})
    def test_path_traversal(self):
        with TemporaryDirectory() as d:
            for n in ('../escape','/abs','x//y','x/./y','x\\y','C:x'):
                with self.subTest(name=n),self.assertRaises(ValueError):io.child(d,n)
    def test_symlink_rejected(self):
        # Inject the OS link predicate; requires no Windows symlink privilege.
        with TemporaryDirectory() as d,patch.object(Path,'is_symlink',return_value=True):
            with self.assertRaises(ValueError):io.safe(Path(d)/'link')
    def test_raw_bytes_not_newline_normalized(self):
        with TemporaryDirectory() as d:
            p=Path(d)/'x';p.write_bytes(b'a\r\n')
            self.assertNotEqual(io.file_hash(p),io.text_hash(p))
    def test_forensic_bundle_preserves_partial(self):
        with TemporaryDirectory() as d:
            root=Path(d)/'partial';io.put(root/'failure.json',{'failed':True})
            target=Path(d)/'result.zip';r=cli.bundle(root,target)
            self.assertFalse(r['complete_raw']);self.assertFalse(r['analysis_present'])
            with zipfile.ZipFile(target) as z:self.assertIsNone(z.testzip())
            with self.assertRaises(ValueError):cli.bundle(root,target)

class Pipeline(unittest.TestCase):
    def test_failure_kind(self):
        pairs=[(KeyboardInterrupt(),'interrupted'),(ImportError(),'dependency_failure'),
            (ValueError(),'schema_contract_failure'),(OSError(),'runtime_io_failure'),
            (RuntimeError(),'runtime_failure'),(UnicodeError(),'parsing_failure')]
        for error,kind in pairs:
            with self.subTest(kind=kind):self.assertEqual(protocol.failure_kind(error),kind)
    def test_freeze_rejects_changed_addon(self):
        p,_,_=plan_fixture()
        p.update(schema='hcr-exp25-plan-v1',created_at_utc='fixture',source_run='x',prior_run='y',
            prior_file_hashes={},parent_file_hashes={},dependency_source_hashes={'a':'a'},addon_source_hashes={'b':'b'})
        with patch.object(protocol.sources,'dependencies',return_value={'a':'a'}),patch.object(protocol.sources,'addon_hashes',return_value={'b':'changed'}):
            with self.assertRaises(ValueError):protocol.validate_plan(p,check_parent=False)
    def test_first_failure_stops_and_keeps_partial_raw(self):
        with TemporaryDirectory() as d:
            root=Path(d);parentpath=root/'old';priorpath=root/'prior';parentpath.mkdir();priorpath.mkdir()
            p,parent,seed=plan_fixture();p.update(parent_file_hashes={},prior_file_hashes={},
                dependency_source_hashes={},addon_source_hashes={},prior_run=str(priorpath))
            calls=[]
            class FakeWorker:
                def __init__(self,sink):self.sink=sink
                def run(self):
                    self.sink({'event':'synthetic_partial_only'});raise RuntimeError('injected first failure')
                def partial_evidence(self):return {'fixture':True,'preserved':True}
            def make_worker(*args):calls.append(args);return FakeWorker(args[-1])
            with patch.object(protocol,'validate_plan',return_value=(parentpath,parent,seed,{})),patch.object(protocol.runtime,'worker',side_effect=make_worker):
                out=root/'run'
                with self.assertRaises(RuntimeError):protocol.execute(p,out,parentpath,priorpath)
                self.assertEqual(len(calls),1);self.assertFalse((out/'manifest.json').exists())
                f=io.load(out/'failure.json');self.assertEqual(f['completed_trials'],0)
                self.assertTrue(f['partial_evidence']['preserved']);self.assertFalse(f['automatic_retry'])
                self.assertIn('synthetic_partial_only',(out/'attempts.jsonl').read_text())
                with self.assertRaises(FileExistsError):protocol.execute(p,out,parentpath,priorpath)
                self.assertEqual(len(calls),1)
    def test_synthetic_backend_rejected_from_main_run(self):
        with TemporaryDirectory() as d:
            r=Path(d);a=r/'a';b=r/'b';a.mkdir();b.mkdir()
            p,old,seed=plan_fixture();p.update(parent_file_hashes={},prior_file_hashes={},dependency_source_hashes={},addon_source_hashes={},prior_run=str(b))
            class Fake:
                def run(self):return {'backend':'synthetic','base':{'backend':'synthetic'}}
                def partial_evidence(self):return {'fixture':True}
            with patch.object(protocol,'validate_plan',return_value=(a,old,seed,{})),patch.object(protocol.runtime,'worker',return_value=Fake()) as m:
                with self.assertRaises(ValueError):protocol.execute(p,r/'out',a,b)
                self.assertEqual(m.call_count,1)
    def test_analysis_roundtrip_and_tampering(self):
        with TemporaryDirectory() as d:
            r=Path(d);records=report_records();s=reporting.summarize(records)
            a=dict(schema='hcr-exp25-audit-v1',raw_manifest_sha256='fixture',verified=True)
            with patch.object(audit,'verify_raw',return_value=(s,a,{})):
                audit.write_analysis(r);audit.write_analysis(r,check_only=True)
                (r/'analysis/summary.ko.md').write_text('tampered',encoding='utf-8')
                with self.assertRaises(ValueError):audit.write_analysis(r,check_only=True)
                self.assertEqual(len(list((r/'audit_failures').glob('*.json'))),1)
    def test_analysis_does_not_overwrite(self):
        with TemporaryDirectory() as d:
            s=reporting.summarize(report_records());a={'raw_manifest_sha256':'fixture'}
            with patch.object(audit,'verify_raw',return_value=(s,a,{})):
                audit.write_analysis(d)
                with self.assertRaises(FileExistsError):audit.write_analysis(d)


class AdditionalFailureBoundaryTests(unittest.TestCase):
    def test_first_failure_after_completed_trial_is_retained(self):
        with TemporaryDirectory() as d:
            r=Path(d);a=r/'a';b=r/'b';a.mkdir();b.mkdir()
            p,old,seed=plan_fixture();p.update(parent_file_hashes={},prior_file_hashes={},dependency_source_hashes={},addon_source_hashes={},prior_run=str(b))
            calls=[]
            class Fake:
                def __init__(self,n,sink): self.n=n; self.sink=sink
                def run(self):
                    self.sink({'fixture_only':True,'index':self.n})
                    if self.n==1: raise RuntimeError('injected second-trial first failure')
                    return {'backend':'native_hcr','base':{'backend':'native_hcr'},'fixture_only':True}
                def partial_evidence(self): return {'fixture_only':True,'last_index':self.n}
            def worker(*args):
                obj=Fake(len(calls),args[-1]);calls.append(obj);return obj
            with patch.object(protocol,'validate_plan',return_value=(a,old,seed,{})),patch.object(protocol.runtime,'worker',side_effect=worker):
                with self.assertRaises(RuntimeError): protocol.execute(p,r/'out',a,b)
            self.assertEqual(len(calls),2)
            self.assertTrue((r/'out/raw/t0000.json').is_file())
            self.assertFalse((r/'out/raw/t0001.json').exists())
            self.assertFalse((r/'out/manifest.json').exists())
            f=io.load(r/'out/failure.json');self.assertEqual(f['completed_trials'],1)
            self.assertEqual(f['trial']['id'],'t0001');self.assertEqual(f['partial_evidence']['last_index'],1)
            stream=[io.loads(x) for x in (r/'out/attempts.jsonl').read_text().splitlines()]
            self.assertEqual(sum(x['event']=='trial_completed' for x in stream),1)
            self.assertEqual(sum(x['event']=='trial_started' for x in stream),2)

    def test_audit_measurement_failure_separated(self):
        from r044_reuse_contribution.gate_audit import MeasurementError
        with TemporaryDirectory() as d,patch.object(audit,'verify_raw',side_effect=MeasurementError('bad count')):
            with self.assertRaises(MeasurementError): audit.write_analysis(d)
            f=io.load(next((Path(d)/'audit_failures').glob('*.json')))
            self.assertEqual(f['status'],'measurement_failure')

    def test_audit_intervention_failure_separated(self):
        from r044_reuse_contribution.gate_audit import GateContractError
        with TemporaryDirectory() as d,patch.object(audit,'verify_raw',side_effect=GateContractError('bad gate')):
            with self.assertRaises(GateContractError): audit.write_analysis(d)
            f=io.load(next((Path(d)/'audit_failures').glob('*.json')))
            self.assertEqual(f['status'],'intervention_contract_failure')
