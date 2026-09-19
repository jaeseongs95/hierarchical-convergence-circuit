"""별도 Python 프로세스에서 checkpoint를 복원하며 원시 기록의 변경 여부를 확인한다."""
from pathlib import Path
from copy import deepcopy
import ast
import hashlib
import subprocess
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from hcr import codec
from hcr.model import ContractError
from hcr.sessions import AdaptiveSession
from hcr.evaluation.session_protocol import run_demo, verify_run
from hcr.tasks.toy_world import chain

ROOT=Path(__file__).resolve().parents[1]


class SessionCLI(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='R021 프로세스 ');self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)

    def run_cli(self,*args,ok=True):
        r=subprocess.run([sys.executable,'-X','utf8','-B',str(ROOT/'hcr.py'),'session',*map(str,args)],cwd=ROOT,capture_output=True,text=True,encoding='utf-8',timeout=30)
        self.assertEqual(r.returncode==0,ok,r.stdout+'\n'+r.stderr)
        return codec.loads(r.stdout if r.returncode==0 else r.stderr)

    def test_resume_is_an_actual_separate_process(self):
        o=self.root/'input.json';codec.save(o,chain('a',(True,)*3).observation)
        p,q=self.root/'step.json',self.root/'done.json'
        one=self.run_cli('start','--input',o,'--out',p,'--steps',1)
        self.assertEqual(one['phase'],'running');before=p.read_bytes()
        two=self.run_cli('resume','--checkpoint',p,'--out',q,'--complete','--expect-sha256',one['checkpoint_sha256'])
        self.assertEqual(two['phase'],'idle');self.assertTrue(two['decision']['value'])
        self.assertEqual(before,p.read_bytes());self.assertEqual(two['decision']['cost']['expansions'],3)
        self.assertTrue(self.run_cli('verify','--checkpoint',q)['verified'])

    def test_resume_completed_snapshot_refused(self):
        s=AdaptiveSession();s.begin(chain('a').observation);s.complete();p=self.root/'done.json';s.save(p)
        self.run_cli('resume','--checkpoint',p,'--out',self.root/'no.json','--complete',ok=False)
        self.assertFalse((self.root/'no.json').exists())

    def test_existing_output_rejected(self):
        o=self.root/'input.json';codec.save(o,chain('a').observation);p=self.root/'exists.json';p.write_bytes(b'keep')
        self.run_cli('start','--input',o,'--out',p,ok=False)
        self.assertEqual(p.read_bytes(),b'keep')

    def test_public_input_rejects_truth(self):
        o=self.root/'input.json';codec.save(o,dict(codec.plain(chain('a').observation),truth=True))
        self.run_cli('start','--input',o,'--out',self.root/'no.json',ok=False)

    def test_readout_ready_checkpoint_not_finished_implicitly(self):
        o=self.root/'input.json';codec.save(o,chain('a',(True,)).observation);p=self.root/'r.json'
        r=self.run_cli('start','--input',o,'--out',p,'--steps',1)
        self.assertEqual(r['phase'],'readout_ready');self.assertIsNone(r['decision'])
        d=codec.loads(p.read_bytes())['document'];self.assertEqual(d['engine']['held'],{})
        self.assertTrue(d['engine']['pending']['value'])

    def test_wrong_expected_hash_refused(self):
        s=AdaptiveSession();s.begin(chain('a').observation);p=self.root/'a.json';s.save(p)
        self.run_cli('resume','--checkpoint',p,'--out',self.root/'b.json','--expect-sha256','0'*64,ok=False)

    def test_auditor_has_no_production_inference_imports(self):
        file=ROOT/'src/hcr/evaluation/session_audit.py'
        tree=ast.parse(file.read_text(encoding='utf-8'))
        forbidden={'runtime','dynamics','state','sessions','expansion','activation','learning','workspace'}
        self.assertFalse(forbidden.intersection(n.module for n in ast.walk(tree) if isinstance(n,ast.ImportFrom)))


class SessionDemo(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory(prefix='EXP10 ');cls.root=Path(cls.tmp.name)/'run'
        cls.result=run_demo(cls.root)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_full_development_comparison(self):
        self.assertTrue(self.result['equivalent'])
        self.assertEqual(self.result['comparison_inferences'],30)
        self.assertTrue(verify_run(self.root)['verified'])

    def test_original_weak_error_and_retention_still_wrong(self):
        s=codec.loads((self.root/'summary.json').read_bytes())
        rows={r['case']:r for r in s['baseline_behavior'] if r['group']=='main'}
        self.assertFalse(rows['weak_conflict']['correct']);self.assertFalse(rows['retention']['correct'])
        self.assertTrue(rows['same_score_revision']['correct']);self.assertEqual(rows['same_score_revision']['circuits'],[])

    def test_summary_tamper_even_after_rehash_rejected(self):
        p=self.root/'summary.json';old=p.read_bytes()
        m=self.root/'manifest.json';oldm=m.read_bytes()
        try:
            s=codec.loads(old);s['baseline_behavior'][0]['kernel_ticks']+=1;p.write_text(codec.dumps(s),encoding='utf-8')
            manifest=codec.loads(oldm);manifest['files']['summary.json']=hashlib.sha256(p.read_bytes()).hexdigest()
            m.write_text(codec.dumps(manifest),encoding='utf-8')
            with self.assertRaises(ContractError):verify_run(self.root)
        finally:p.write_bytes(old);m.write_bytes(oldm)

    def test_extra_artifact_rejected(self):
        p=self.root/'extra.txt';p.write_bytes(b'x')
        try:
            with self.assertRaises(ContractError):verify_run(self.root)
        finally:p.unlink()


class OutputContracts(unittest.TestCase):
    def test_sealed_evidence_cannot_be_polluted(self):
        from hcr import session_io
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'bundle_manifest.json').write_bytes(b'{}')
            with self.assertRaises(ContractError):session_io.new_output(root/'new.json')

    def test_failed_run_cannot_receive_new_checkpoint(self):
        from hcr import session_io
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'FAILED.json').write_bytes(b'{}')
            with self.assertRaises(ContractError):session_io.new_output(root/'new.json')

    def test_windows_launcher_native_parser_when_available(self):
        import shutil
        exe=shutil.which('pwsh') or shutil.which('powershell')
        if exe is None:self.skipTest('PowerShell native parser unavailable in this environment')
        path=str(ROOT/'Run-HCR-R021.ps1').replace("'","''")
        code="$t=$null;$e=$null;[void][System.Management.Automation.Language.Parser]::ParseFile('"+path+"',[ref]$t,[ref]$e);if($e.Count){$e;exit 1}"
        r=subprocess.run([exe,'-NoProfile','-Command',code],capture_output=True)
        self.assertEqual(r.returncode,0,r.stdout.decode(errors='replace'))


class ReleaseTextContracts(unittest.TestCase):
    def run_manifest(self, content, *, declare=True):
        import importlib.util
        spec=importlib.util.spec_from_file_location('r021_release_verifier',ROOT/'scripts/verify_release.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);base=b'print(1)\n'
            m=dict(release='0.2.1',files={'x.py':hashlib.sha256(base).hexdigest()})
            if declare:m['text_normalized_sha256']={'x.py':hashlib.sha256(base).hexdigest()}
            (root/'RELEASE_MANIFEST.json').write_bytes(codec.dumps(m).encode('utf-8'))
            (root/'x.py').write_bytes(content)
            return module.verify(root)

    def test_release_exact_bytes(self):
        self.assertEqual(self.run_manifest(b'print(1)\n')['line_ending_only_variants'],[])

    def test_release_declared_crlf_only(self):
        self.assertEqual(self.run_manifest(b'print(1)\r\n')['line_ending_only_variants'],['x.py'])

    def test_release_old_manifest_keeps_raw_contract(self):
        with self.assertRaises(ValueError):self.run_manifest(b'print(1)\r\n',declare=False)

    def test_release_code_change_still_rejected(self):
        with self.assertRaises(ValueError):self.run_manifest(b'print(2)\r\n')
