"""안전한 추가 설치, 실패 보존, 실행 경로의 self-test. Windows 실행 자체는 별도이다."""
from pathlib import Path
from unittest.mock import patch
import importlib.util
import io,json,tempfile,zipfile,unittest,hashlib,ast
ROOT=Path(__file__).resolve().parents[3]
sp=importlib.util.spec_from_file_location('r040_installer_under_test',ROOT/'scripts/install_r040.py')
installer=importlib.util.module_from_spec(sp);sp.loader.exec_module(installer)


def payload(path,data=b'test source',extra=None):
    contents={'R040_README.ko.md':data}
    if extra:contents.update(extra)
    manifest=dict(schema='hcr-r040-additive-release-v1',basis_commit=installer.BASIS,
        files={n:installer.text_hash(v) for n,v in contents.items()})
    contents['R040_MANIFEST.json']=json.dumps(manifest).encode()
    with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_DEFLATED) as z:
        for n,b in contents.items():z.writestr(n,b)
    return path


class InstallerTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);self.path=Path(t.name)
    def test_path_traversal(self):
        for name in ('../x','/tmp/x','a\\b','a/../b','a//b','a:b','a\x00b','CON.py','a./x','x?'):
            with self.subTest(name=name),self.assertRaises(ValueError):installer.check_path(name)
    def test_unicode_safe_path(self):self.assertEqual(installer.check_path('docs/R040_한글.md'),'docs/R040_한글.md')
    def test_existing_source_not_allowed_in_payload(self):
        z=payload(self.path/'x.zip',extra={'src/hcr/runtime.py':b'bad'})
        with self.assertRaises(ValueError):installer.read_payload(z)
    def test_valid_payload(self):self.assertEqual(len(installer.read_payload(payload(self.path/'x.zip'))),2)
    def test_checksum_failure(self):
        z=payload(self.path/'x.zip')
        # 별도 악성 archive fixture: manifest checksum은 유지하고 본문만 변경한다.
        with zipfile.ZipFile(z) as a:objects={n:a.read(n) for n in a.namelist()}
        objects['R040_README.ko.md']=b'altered'
        with zipfile.ZipFile(z,'w') as a:
            for n,b in objects.items():a.writestr(n,b)
        with self.assertRaises(ValueError):installer.read_payload(z)
    def test_idempotent_no_overwrite(self):
        root=self.path/'repo';root.mkdir();z=payload(self.path/'x.zip')
        with patch.object(installer,'check_basis'):
            a=installer.install(root,z);b=installer.install(root,z)
        self.assertEqual(a['installed'],2);self.assertEqual(b['installed'],0);self.assertEqual(b['already_identical'],2)
    def test_conflict_is_detected_before_any_write(self):
        root=self.path/'repo';root.mkdir();(root/'R040_README.ko.md').write_text('user edit');z=payload(self.path/'x.zip')
        with patch.object(installer,'check_basis'),self.assertRaises(ValueError):installer.install(root,z)
        self.assertFalse((root/'R040_MANIFEST.json').exists());self.assertEqual((root/'R040_README.ko.md').read_text(),'user edit')
    def test_unknown_json_keys_duplicate_rejected(self):
        with self.assertRaises(ValueError):installer.loads('{"a":1,"a":2}')
    def test_nonfinite_json_rejected(self):
        with self.assertRaises(ValueError):installer.loads('{"a":NaN}')
    def test_symlink_destination_rejected(self):
        target=self.path/'target';target.mkdir();link=self.path/'link'
        try:link.symlink_to(target,target_is_directory=True)
        except (OSError,NotImplementedError):self.skipTest('OS prevents symlink fixture; installation still rejects detected links')
        with self.assertRaises(ValueError):installer.safe(link)
    def test_baseline_pin_is_exp20_release(self):
        self.assertEqual(installer.R039_BLOB,'daca0bdbbe8bdf3e45e2e7f0a632b84e4a1ae8ca')
        self.assertEqual(installer.BASIS,'ef074f7991733ba0a73d870780d4873718caf1ca')
    def test_runner_native_import_priority(self):
        s=(ROOT/'tools/r040_frontier_schedule/native_tests/test_native_integration.py').read_text()
        self.assertIn("sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tools')]",s)
        self.assertLess(s.index('sys.path[:0]'),s.index('from r037_online_selection'))
    def test_runner_checks_exp20_and_uses_new_output(self):
        s=(ROOT/'Run-HCR-R040.py').read_text()
        self.assertIn("['scripts/r039_cli.py','verify'",s);self.assertIn('HCR-Evidence/exp21',s)
        self.assertIn('HCR_R040_SOURCE_RUN',s)
    def test_bootstrap_has_no_network_install(self):
        s=(ROOT/'scripts/bootstrap_r040.ps1').read_text().lower()
        for word in ('invoke-webrequest','pip install','git pull','git push','start-job'):
            self.assertNotIn(word,s)
    def test_python312_syntax_for_source_files(self):
        for p in (ROOT/'tools/r040_frontier_schedule').rglob('*.py'):
            ast.parse(p.read_text(),filename=str(p),feature_version=(3,12))
