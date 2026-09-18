"""Mocked pipeline failure/preservation tests. Synthetic workers here are never native evidence."""
from contextlib import ExitStack
from copy import deepcopy
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from r045_direct_support import protocol,audit,sources,storage as io
from r045_direct_support.tests.fixtures import plan_fixture
ROOT=Path(__file__).resolve().parents[3]
s=importlib.util.spec_from_file_location('r045_launcher_test_target',ROOT/'Run-HCR-R045.py')
launcher=importlib.util.module_from_spec(s);s.loader.exec_module(launcher)


def stream_fixture(root):
    trial=dict(id='t0000',case='synthetic_only',scope='route_only',arm='online_support',scheduler='input_order',use_circuits=True)
    run=dict(base=dict(events=[dict(event='fixture_only')]),posthoc_events=[],final={'value':None,'accepted':False})
    raw=dict(schema='synthetic_only',trial=trial,run=run);io.put(root/'raw/t0000.json',raw)
    rows=[dict(event='trial_started',trial=trial),
        dict(event='trial_action',trial_id='t0000',record=dict(event='native_action',record=run['base']['events'][0])),
        dict(event='trial_action',trial_id='t0000',record=dict(event='base_completed',base_sha256=io.digest(run['base']))),
        dict(event='trial_action',trial_id='t0000',record=dict(event='arm_finished',final=run['final'])),
        dict(event='trial_completed',trial_id='t0000',raw_sha256=io.digest(raw))]
    return {'trials':[trial]},rows


class PipelineTests(unittest.TestCase):
    def test_stream_exact(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);p,rows=stream_fixture(root)
            io.write_bytes(root/'attempts.jsonl',b''.join(io.canonical(x)+b'\n' for x in rows))
            self.assertEqual(audit.check_attempt_stream(root,p),5)
    def test_stream_corruptions_rejected(self):
        for operation in ('drop_first','duplicate','trailing','changed_hash'):
            with self.subTest(operation=operation),tempfile.TemporaryDirectory() as d:
                root=Path(d);p,rows=stream_fixture(root)
                if operation=='drop_first':rows.pop(0)
                if operation=='duplicate':rows.insert(0,deepcopy(rows[0]))
                if operation=='trailing':rows.append({'event':'retry'})
                if operation=='changed_hash':rows[-1]['raw_sha256']='wrong'
                io.write_bytes(root/'attempts.jsonl',b''.join(io.canonical(x)+b'\n' for x in rows))
                with self.assertRaises(ValueError):audit.check_attempt_stream(root,p)
    def test_runtime_first_failure_preserved(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);source=root/'prior';source.mkdir();out=root/'out';io.put(source/'manifest.json',{'synthetic_only':True})
            p,_,seed=plan_fixture();p.update(dependency_source_hashes={},addon_source_hashes={},
                parent_file_hashes={'manifest.json':io.file_hash(source/'manifest.json')})
            calls=[]
            class Broken:
                def run(self):calls.append(1);raise RuntimeError('original-first-failure')
                def partial_evidence(self):return {'first_response':'preserved-synthetic-fixture'}
            with patch.object(protocol,'validate_plan',return_value=(source,None,seed,{})),patch.object(protocol,'repository_head',return_value=None),\
                 patch.object(protocol.runtime,'worker',return_value=Broken()):
                with self.assertRaisesRegex(RuntimeError,'original-first-failure'):protocol.execute(p,out)
            f=io.load(out/'failure.json')
            self.assertEqual(len(calls),1);self.assertEqual(f['completed_trials'],0);self.assertFalse(f['automatic_retry'])
            self.assertIn('preserved',f['partial_evidence']['first_response']);self.assertFalse((out/'manifest.json').exists())
            self.assertEqual(len((out/'attempts.jsonl').read_text().splitlines()),1)
    def test_producer_does_not_mark_raw_independently_verified(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);source=root/'prior';source.mkdir();out=root/'out';io.put(source/'manifest.json',{'synthetic_only':True})
            p,_,seed=plan_fixture();p['trials']=p['trials'][:1]
            p.update(dependency_source_hashes={},addon_source_hashes={},parent_file_hashes={'manifest.json':io.file_hash(source/'manifest.json')})
            class Fake:
                def run(self):return {'backend':'native_hcr','base':{'backend':'native_hcr'}}
            with patch.object(protocol,'validate_plan',return_value=(source,None,seed,{})),patch.object(protocol,'repository_head',return_value=None),\
                 patch.object(protocol.runtime,'worker',return_value=Fake()),patch('builtins.print'):protocol.execute(p,out)
            m=io.load(out/'manifest.json');self.assertTrue(m['independent_audit_pending']);self.assertNotIn('verified',m)
    def test_synthetic_backend_blocked_by_production_boundary(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);source=root/'prior';source.mkdir();out=root/'out';io.put(source/'manifest.json',{})
            p,_,seed=plan_fixture();p.update(dependency_source_hashes={},addon_source_hashes={},parent_file_hashes={'manifest.json':io.file_hash(source/'manifest.json')})
            class Fake:
                def run(self):return {'backend':'synthetic','base':{'backend':'synthetic'}}
                def partial_evidence(self):return {'fixture':True}
            with patch.object(protocol,'validate_plan',return_value=(source,None,seed,{})),patch.object(protocol,'repository_head',return_value=None),\
                 patch.object(protocol.runtime,'worker',return_value=Fake()):
                with self.assertRaises(ValueError):protocol.execute(p,out)
            self.assertFalse((out/'manifest.json').exists())
    def test_launcher_order(self):
        cs=launcher.commands('source','plan','out')
        flattened=[' '.join(c) for c in cs]
        self.assertLess(next(i for i,s in enumerate(flattened) if 'native_tests' in s),next(i for i,s in enumerate(flattened) if ' prepare ' in s))
        self.assertLess(next(i for i,s in enumerate(flattened) if 'audit' in s),len(cs)-1)
        self.assertIn('verify',cs[-1]);self.assertFalse(any('pip' in c or 'git' in c for c in cs))
    def test_check_only_has_native_checks_no_research_execute(self):
        cs=launcher.commands('source','plan','out',True)
        self.assertEqual(len(cs),5);self.assertTrue(any('native_tests' in ' '.join(c) for c in cs))
        self.assertFalse(any('execute' in c for c in cs))
    def test_forensic_bundle_separate_from_success(self):
        import zipfile
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);logs=root/'logs';logs.mkdir();out=root/'partial';out.mkdir()
            io.put(logs/'failure.json',{'error':'first'});io.put(out/'partial.json',{'raw':'partial'})
            z=launcher.forensic_bundle(logs,out,None)
            with zipfile.ZipFile(z) as f:self.assertFalse(io.loads(f.read('FORENSIC-MANIFEST.json'))['complete'])
    def test_validation_failure_types(self):
        self.assertEqual(protocol.failure_kind(ImportError()),'dependency_failure')
        self.assertEqual(protocol.failure_kind(ValueError()),'schema_contract_failure')
        self.assertEqual(protocol.failure_kind(KeyboardInterrupt()),'interrupted')
    def test_parent_hash_pin_before_native_import(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);io.put(root/'manifest.json',{})
            with self.assertRaises(ValueError):sources.read_parent(root)

if __name__=='__main__':unittest.main()
