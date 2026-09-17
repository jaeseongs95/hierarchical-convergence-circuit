"""주입된 stub으로 계획·실패 기록·CLI 경계를 검사한다. 모델 실행 결과가 아니다."""
from pathlib import Path
from copy import deepcopy
import importlib.util,json,subprocess,sys,tempfile,unittest
from unittest.mock import patch
from r037_online_selection import io
from r039_order_isolation import protocol,sources,spec
from r039_order_isolation.contracts import digest
from r039_order_isolation.tests._fixtures import parent,cases
ROOT=Path(__file__).resolve().parents[3]


class ProtocolTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.dir=Path(self.temp.name);self.source=self.dir/'source';self.source.mkdir()
        self.cases=cases();self.core={'memory':{},'config':{}}
        self.hashes={n:'0'*64 for n in sources.PARENT_FILES}
        for fn,value in [('read_parent',(self.source,self.cases,self.core,self.hashes,parent())),('dependencies',{}),('addon_hashes',{})]:
            p=patch.object(sources,fn,return_value=value);p.start();self.addCleanup(p.stop)
    def test_plan_validate(self):protocol.validate_plan(protocol.make_plan(self.source))
    def test_plan_rejects_world_change(self):
        p=protocol.make_plan(self.source);p['evaluation_worlds']['order_SMD']['missing_closed']['e4']=True
        with self.assertRaises(ValueError):protocol.validate_plan(p)
    def test_plan_rejects_order_scope_leak(self):
        p=protocol.make_plan(self.source);p['cases'][0]['observation']['branch_order']='SMD'
        with self.assertRaises(ValueError):protocol.validate_plan(p)
    def test_plan_rejects_boolean_budget(self):
        p=protocol.make_plan(self.source);p['conditions']['automatic_retry']=0
        with self.assertRaises(ValueError):protocol.validate_plan(p)
    def test_plan_overwrite_refused(self):
        target=self.dir/'out.plan.json';protocol.prepare(self.source,target)
        with self.assertRaises(ValueError):protocol.prepare(self.source,target)
    def test_prepare_has_36_trials(self):self.assertEqual(protocol.prepare(self.source,self.dir/'p.json')['native_trials'],36)
    def setup_execute(self):
        seed='upstream/seed/6.json';io.put(self.source/seed,dict(document={'engine':self.core}))
        plan=protocol.make_plan(self.source);plan['parent_file_hashes']={seed:io.file_hash(self.source/seed)}
        return plan
    def test_synthetic_backend_refused_and_failure_preserved(self):
        plan=self.setup_execute();seen=[]
        class Worker:
            def __init__(self,*a,**k):seen.append(a[0])
            def run(self):return dict(backend='synthetic',base={'backend':'synthetic'})
            def partial_evidence(self):return {'first_failure':'preserved'}
        out=self.dir/'out'
        with patch.object(protocol,'validate_plan',return_value=self.source),patch.object(protocol,'TimingTrial',Worker):
            with self.assertRaises(ValueError):protocol.execute(plan,out)
        f=io.load(out/'failure.json');self.assertEqual(f['completed_trials'],0);self.assertFalse(f['automatic_retry'])
        self.assertEqual(len(seen),1);self.assertEqual(seen[0],self.cases[0]['observation'])
        self.assertNotIn('worlds',seen[0]);self.assertNotIn('branch_order',seen[0]);self.assertFalse((out/'manifest.json').exists())
    def test_nonserializable_partial_is_not_repaired(self):
        plan=self.setup_execute()
        class Worker:
            def __init__(self,*a,**k):pass
            def run(self):raise RuntimeError('runtime failure')
            def partial_evidence(self):return {'bad':float('nan')}
        out=self.dir/'out'
        with patch.object(protocol,'validate_plan',return_value=self.source),patch.object(protocol,'TimingTrial',Worker):
            with self.assertRaises(RuntimeError):protocol.execute(plan,out)
        self.assertTrue((out/'failure-partial.repr.txt').exists());self.assertIn('nan',(out/'failure-partial.repr.txt').read_text())
    def test_existing_evidence_not_overwritten(self):
        plan=self.setup_execute();out=self.dir/'out';out.mkdir();(out/'old.txt').write_text('keep')
        with patch.object(protocol,'validate_plan',return_value=self.source):
            with self.assertRaises(FileExistsError):protocol.execute(plan,out)
        self.assertEqual((out/'old.txt').read_text(),'keep')
    def test_copy_checksum_failure_stops_before_native(self):
        plan=self.setup_execute();plan['parent_file_hashes']['upstream/seed/6.json']='wrong';out=self.dir/'out'
        with patch.object(protocol,'validate_plan',return_value=self.source),patch.object(protocol,'TimingTrial') as worker:
            with self.assertRaises(ValueError):protocol.execute(plan,out)
            worker.assert_not_called()
        self.assertEqual(io.load(out/'failure.json')['stage'],'copy_sources')
    def test_failure_taxonomy(self):
        self.assertEqual(protocol.failure_kind(ImportError()),'dependency_failure')
        self.assertEqual(protocol.failure_kind(KeyboardInterrupt()),'interrupted')
        self.assertEqual(protocol.failure_kind(OSError()),'runtime_io_failure')
    def test_capsule_paths_are_unique(self):
        paths=[sources.capsule_name(x) for x in sources.PARENT_FILES]
        self.assertEqual(len(paths),len(set(paths)));self.assertIn('upstream/seed/6.json',paths)
    def test_cli_help_works_outside_repo(self):
        for name in ('Run-HCR-R039.py','scripts/r039_cli.py'):
            p=subprocess.run([sys.executable,'-X','utf8','-B',str(ROOT/name),'--help'],cwd=self.dir,capture_output=True,text=True)
            self.assertEqual(p.returncode,0,p.stderr)
    def test_native_import_bootstrap_present(self):
        text=(ROOT/'tools/r039_order_isolation/native_tests/test_native_integration.py').read_text()
        self.assertIn("sys.path[:0] = [str(ROOT/'src'),str(ROOT/'tools')]",text)
    def test_native_runtime_is_reused_not_rewritten(self):
        from r038_early_adoption.runtime import TimingTrial
        self.assertIs(protocol.TimingTrial,TimingTrial)
