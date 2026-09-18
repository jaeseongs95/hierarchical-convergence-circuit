from copy import deepcopy
from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from r037_online_selection import io
from r038_early_adoption import sources,spec,protocol,audit
from r038_early_adoption.tests._support import OBS,CONFIG,MEMORY
from r038_early_adoption.tests.test_reporting import fixture
from r038_early_adoption.reporting import summarize

ROOT=Path(__file__).resolve().parents[3]


def old_cases():
    return [dict(name=n,family='synthetic_control',observation=deepcopy(OBS),worlds={'synthetic':{'e0':True}})
            for n in spec.BASE_CASES]


class ProtocolTests(unittest.TestCase):
    def test_make_plan_preserves_exact_population_and_seed(self):
        cases=spec.cases_from_parent(old_cases());core=dict(config=CONFIG,memory=MEMORY)
        with patch.object(sources,'read_parent',return_value=(Path('/synthetic'),cases,core,{})),\
             patch.object(sources,'dependencies',return_value={}),patch.object(sources,'addon_hashes',return_value={}):
            plan=protocol.make_plan('/synthetic')
        self.assertEqual(len(plan['trials']),84);self.assertEqual(len(plan['cases']),14)
        self.assertEqual(set(plan),protocol.PLAN_KEYS)
        self.assertEqual(plan['memory_sha256'],protocol.digest(MEMORY))
        self.assertTrue(all('worlds' not in c for c in plan['cases']))

    def test_mutated_conditions_cannot_validate(self):
        cases=spec.cases_from_parent(old_cases());core=dict(config=CONFIG,memory=MEMORY)
        with patch.object(sources,'read_parent',return_value=(Path('/synthetic'),cases,core,{})),\
             patch.object(sources,'dependencies',return_value={}),patch.object(sources,'addon_hashes',return_value={}):
            p=protocol.make_plan('/synthetic');p['conditions']['budget']['max_extra_advances']+=1
            with self.assertRaises(ValueError): protocol.validate_plan(p,check_parent=False)

    def test_prepare_never_overwrites(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);src=root/'parent';src.mkdir();out=root/'plan.json';out.write_text('retained')
            with self.assertRaises(ValueError): protocol.prepare(src,out)
            self.assertEqual(out.read_text(),'retained')

    def test_prepare_not_inside_parent(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            with self.assertRaises(ValueError): protocol.prepare(root,root/'newplan.json')

    def test_addon_manifest_detects_source_mutation(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);p=root/'code.py';p.write_text('x=1\n')
            io.put(root/'manifest.json',{'files':{'code.py':io.text_hash(p)}})
            sources.check_manifest(root,'manifest.json')
            p.write_text('x=2\n')
            with self.assertRaises(ValueError): sources.check_manifest(root,'manifest.json')

    def test_source_lf_crlf_equivalence_not_raw_equivalence(self):
        with tempfile.TemporaryDirectory() as d:
            a,b=Path(d)/'a',Path(d)/'b';a.write_bytes(b'x\n');b.write_bytes(b'x\r\n')
            self.assertEqual(io.text_hash(a),io.text_hash(b));self.assertNotEqual(io.file_hash(a),io.file_hash(b))

    def test_capsule_preserves_upstream_paths(self):
        self.assertEqual(sources.capsule_name('upstream/seed/6.json'),'upstream/seed/6.json')
        self.assertEqual(sources.capsule_name('plan.json'),'basis/exp18/plan.json')
        self.assertEqual(sources.capsule_name('analysis/audit.json'),'basis/exp18/analysis/audit.json')

    def test_production_rejects_synthetic_and_preserves_failure(self):
        class SyntheticWorker:
            calls=0
            def __init__(self,*a,**k): pass
            def run(self):
                type(self).calls+=1
                return dict(backend='synthetic_unit_test',base={'backend':'synthetic_unit_test'})
            def partial_evidence(self): return {'synthetic_partial':True}
        with tempfile.TemporaryDirectory() as d:
            parent,out=Path(d)/'parent',Path(d)/'run';parent.mkdir()
            io.put(parent/'upstream/seed/6.json',{'document':{'engine':{'config':CONFIG,'memory':MEMORY}}})
            plan=dict(dependency_source_hashes={},addon_source_hashes={},
                parent_file_hashes={'upstream/seed/6.json':io.file_hash(parent/'upstream/seed/6.json')},
                cases=[dict(name='test',observation=OBS)],conditions=spec.conditions(),
                trials=[dict(id='t0000',case='test',scope='legacy',arm='native')])
            with patch.object(protocol,'validate_plan',return_value=parent),patch.object(protocol,'TimingTrial',SyntheticWorker):
                with self.assertRaises(ValueError): protocol.execute(plan,out)
                self.assertTrue((out/'failure.json').exists());self.assertFalse((out/'manifest.json').exists())
                f=io.load(out/'failure.json');self.assertEqual(f['completed_trials'],0);self.assertFalse(f['automatic_retry'])
                self.assertEqual(SyntheticWorker.calls,1)
                before=(out/'failure.json').read_bytes()
                with self.assertRaises(FileExistsError): protocol.execute(plan,out)
                self.assertEqual((out/'failure.json').read_bytes(),before)

    def test_failure_types_are_distinct(self):
        errors=[(KeyboardInterrupt(),'interrupted'),(UnicodeError(),'parsing_failure'),
                (ImportError(),'dependency_failure'),(KeyError(),'schema_contract_failure'),
                (OSError(),'runtime_io_failure'),(RuntimeError(),'runtime_failure')]
        for exc,kind in errors:self.assertEqual(protocol.failure_kind(exc),kind)

    def test_analysis_writes_checks_and_preserves_original(self):
        summary=summarize(fixture());report=dict(verified=True,raw_manifest_sha256='synthetic')
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);io.put(root/'raw-preserved.json',{'unchanged':True});before=io.file_hash(root/'raw-preserved.json')
            with patch.object(audit,'verify_raw',return_value=(summary,report,{})):
                self.assertTrue(audit.write_analysis(root)['verified'])
                self.assertTrue(audit.write_analysis(root,check_only=True)['verified'])
                with self.assertRaises(FileExistsError): audit.write_analysis(root)
            self.assertEqual(io.file_hash(root/'raw-preserved.json'),before)
            self.assertTrue(any((root/'audit_failures').iterdir()))

    def test_analysis_tampering_detected(self):
        summary=summarize(fixture());report=dict(verified=True,raw_manifest_sha256='synthetic')
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            with patch.object(audit,'verify_raw',return_value=(summary,report,{})):
                audit.write_analysis(root)
                (root/'analysis/paired.csv').write_text('changed',encoding='utf-8')
                with self.assertRaises(ValueError): audit.write_analysis(root,check_only=True)

    def test_cli_bootstrap_from_other_working_directory(self):
        with tempfile.TemporaryDirectory() as d:
            p=subprocess.run([sys.executable,'-X','utf8','-B',str(ROOT/'scripts/r038_cli.py'),'--help'],
                             cwd=d,capture_output=True,text=True)
            self.assertEqual(p.returncode,0,p.stderr);self.assertIn('errata-exp18',p.stdout)

    def test_runner_help_without_native_import(self):
        p=subprocess.run([sys.executable,'-X','utf8','-B',str(ROOT/'Run-HCR-R038.py'),'--help'],
                         capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stderr);self.assertIn('--check-only',p.stdout)
