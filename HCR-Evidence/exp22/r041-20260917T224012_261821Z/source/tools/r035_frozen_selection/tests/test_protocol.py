"""Synthetic I/O 통합 시험. full_native_audit를 대체하는 mock은 이 테스트 안에만 있다."""
import ast
from contextlib import ExitStack
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from helpers import make_view,native_candidate
from r035_frozen_selection import storage as io,protocol,spec,verification,upstream
from r035_frozen_selection.contracts import digest
from r035_frozen_selection.native_bridge import project
from r035_frozen_selection.audit import AuditError


class ProtocolTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.source=self.root/'source';self.source.mkdir()
        candidate=native_candidate(make_view())
        cell=dict(id='s0001',case='synthetic',scope='legacy',group='main',arm='expand_only',world='declared',baseline_key='synthetic/legacy')
        raw=dict(cell=cell,result=dict(candidates=[candidate],schema='hcr-selection-flow-r034-v1',arm='expand_only'))
        baseline=dict(first=candidate)
        io.put(self.source/'raw/s0001.json',raw);io.put(self.source/'baselines/synthetic/legacy.json',baseline)
        cases=[dict(name='synthetic',worlds={'declared':dict(e0=True,e1=True,e2=False,e3=True)})]
        oldplan=dict(schema='hcr-exp15-plan-v1',conditions=dict(cases=cases,scopes=['legacy']),source_hashes={})
        io.put(self.source/'plan.json',oldplan)
        io.put(self.source/'manifest.json',dict(schema='hcr-exp15-raw-manifest-v1',state='raw_complete',files={n:io.file_hash(self.source/n) for n in io.inventory(self.source)}))
        self.population=[dict(path='raw/s0001.json',baseline_path='baselines/synthetic/legacy.json',raw=raw,baseline=baseline,
            raw_bytes=io.read(self.source/'raw/s0001.json'),baseline_bytes=io.read(self.source/'baselines/synthetic/legacy.json'))]
        self.saved=upstream.snapshots(self.population);self.cases={c['name']:c for c in cases}
        stack=ExitStack();self.addCleanup(stack.close)
        stack.enter_context(patch('r035_frozen_selection.upstream.check_native',return_value={'files':{}}))
        stack.enter_context(patch('r035_frozen_selection.protocol.code_hashes',return_value={}))
        self.plan=protocol.make_plan(self.source)
        self.out=self.root/'run'

    def synthetic_source_audit(self):
        files={'upstream/plan.json','upstream/manifest.json','upstream/raw/s0001.json','upstream/baselines/synthetic/legacy.json'}
        return self.saved,self.cases,{'verified':True,'test_only_mock':True},files

    def generate(self):return protocol.generate(self.plan,self.out)

    def test_generate_audit_verify_pipeline(self):
        r=self.generate();self.assertEqual(r['conditions'],52)
        with patch('r035_frozen_selection.verification.independent_sources',return_value=self.synthetic_source_audit()):
            a=verification.write_analysis(self.out);self.assertTrue(a['verified'])
            b=verification.write_analysis(self.out,check_only=True);self.assertEqual(a,b)
        self.assertEqual(len(io.load(self.out/'analysis/summary.json')['rows']),52)

    def test_independent_source_projection_and_population(self):
        self.generate()
        fakecell=self.population[0]['raw']['cell']
        with (patch('hcr.evaluation.selection_spec.cells',return_value=[fakecell]),
              patch('r035_frozen_selection.upstream.full_native_audit',return_value={'verified':True,'test_only_mock':True})):
            saved,_,_,_=verification.independent_sources(self.out,self.plan,self.source)
        self.assertEqual(saved,self.saved)

    def test_snapshot_tamper_detected(self):
        self.generate();p=self.out/'snapshots/n0000.json';v=io.load(p);v['input']['state']['goal']=.1
        p.write_text(json.dumps(v),encoding='utf-8')
        with self.assertRaises(ValueError):verification.verify_raw(self.out)

    def test_rehashed_result_tamper_detected(self):
        self.generate();p=self.out/'raw/f00002.json';v=io.load(p);v['result']['proof']['primitive_depth']=123
        p.write_text(json.dumps(v),encoding='utf-8');m=io.load(self.out/'manifest.json');m['files']['raw/f00002.json']=io.file_hash(p)
        (self.out/'manifest.json').write_text(json.dumps(m),encoding='utf-8')
        with patch('r035_frozen_selection.verification.independent_sources',return_value=self.synthetic_source_audit()):
            with self.assertRaises(AuditError):verification.write_analysis(self.out)
        self.assertFalse((self.out/'analysis').exists());self.assertTrue(list((self.out/'audit_failures').glob('*.json')))

    def test_rehashed_stream_log_tamper_detected(self):
        self.generate();p=self.out/'attempts.jsonl';lines=p.read_text().splitlines();x=json.loads(lines[0]);x['cell_id']='other';lines[0]=json.dumps(x)
        p.write_text('\n'.join(lines)+'\n',encoding='utf-8');m=io.load(self.out/'manifest.json');m['files']['attempts.jsonl']=io.file_hash(p)
        (self.out/'manifest.json').write_text(json.dumps(m),encoding='utf-8')
        with patch('r035_frozen_selection.verification.independent_sources',return_value=self.synthetic_source_audit()):
            with self.assertRaises(AuditError):verification.verify_raw(self.out)

    def test_failure_is_preserved_no_retry(self):
        with patch('r035_frozen_selection.protocol.run_policy',side_effect=ValueError('injected contract failure')) as f:
            with self.assertRaises(ValueError):self.generate()
            self.assertEqual(f.call_count,1)
        fail=io.load(self.out/'failure.json');self.assertEqual(fail['completed_conditions'],0)
        self.assertEqual(fail['status'],'schema_contract_failure');self.assertFalse(fail['automatic_retry'])
        self.assertEqual(len((self.out/'attempts.jsonl').read_text().splitlines()),1)
        self.assertFalse((self.out/'manifest.json').exists())

    def test_existing_output_not_overwritten(self):
        self.generate();m=io.file_hash(self.out/'manifest.json')
        with self.assertRaises(FileExistsError):self.generate()
        self.assertEqual(m,io.file_hash(self.out/'manifest.json'))

    def test_source_unchanged(self):
        before={n:io.file_hash(self.source/n) for n in io.inventory(self.source)}
        self.generate();self.assertEqual(before,{n:io.file_hash(self.source/n) for n in io.inventory(self.source)})

    def test_source_manifest_change_rejected(self):
        (self.source/'manifest.json').write_text('{}')
        with self.assertRaises(ValueError):self.generate()
        self.assertFalse(self.out.exists())

    def test_plan_change_rejected(self):
        self.plan['conditions']['same_value_only']=False
        with self.assertRaises(ValueError):self.generate()

    def test_plan_cannot_write_inside_source(self):
        with self.assertRaises(ValueError):protocol.prepare(self.source,self.source/'new.plan.json')
        self.assertFalse((self.source/'new.plan.json').exists())

    def test_source_output_nested_rejected(self):
        with self.assertRaises(ValueError):protocol.generate(self.plan,self.source/'nested')

    def test_analysis_not_overwritten(self):
        self.generate()
        with patch('r035_frozen_selection.verification.independent_sources',return_value=self.synthetic_source_audit()):
            verification.write_analysis(self.out);h=io.file_hash(self.out/'analysis/summary.json')
            with self.assertRaises(FileExistsError):verification.write_analysis(self.out)
        self.assertEqual(io.file_hash(self.out/'analysis/summary.json'),h)

    def test_selection_population_ignores_analysis_and_world_duplicate(self):
        self.assertEqual(len(upstream.select_population(self.source)),1)
        (self.source/'analysis').mkdir();(self.source/'analysis/summary.json').write_text('{"accuracy":0}')
        self.assertEqual(len(upstream.select_population(self.source)),1)

    def test_all_tool_sources_compile(self):
        for p in Path(protocol.__file__).parent.rglob('*.py'):ast.parse(p.read_text(encoding='utf-8'))


class StorageTests(unittest.TestCase):
    def test_duplicate_keys_rejected(self):
        with self.assertRaises(ValueError):io.loads('{"a":1,"a":2}')

    def test_nonfinite_literals_rejected(self):
        for n in ('NaN','Infinity','-Infinity'):
            with self.assertRaises(ValueError):io.loads('{"a":'+n+'}')

    def test_path_traversal_rejected(self):
        for n in ('../a','/tmp/a','C:/a','x\\y','x//y','./x',''):
            with self.assertRaises(ValueError):io.child('/tmp',n)

    def test_exclusive_write(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'a';io.put(p,{'a':1})
            with self.assertRaises(FileExistsError):io.put(p,{'a':2})
            self.assertEqual(io.load(p),{'a':1})

    def test_read_size_bound(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'a';p.write_bytes(b'012345')
            with self.assertRaises(ValueError):io.read(p,max_bytes=5)

    def test_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'a';p.write_text('x');q=Path(d)/'b'
            try:q.symlink_to(p)
            except OSError:self.skipTest('이 환경은 symlink 생성 권한이 없습니다.')
            with self.assertRaises(ValueError):io.read(q)


if __name__=='__main__':unittest.main()
