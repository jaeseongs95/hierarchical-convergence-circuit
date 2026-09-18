from pathlib import Path
import tempfile,unittest,zipfile,json,hashlib,importlib.util,warnings
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[3]
spec=importlib.util.spec_from_file_location('r046_installer',ROOT/'scripts/install_r046.py')
installer=importlib.util.module_from_spec(spec);spec.loader.exec_module(installer)

class InstallerTests(unittest.TestCase):
    def make_root(self,root):
        root.mkdir();(root/'R045_MANIFEST.json').write_bytes((ROOT/'tools/r046_thought_carry/tests/data/R045_MANIFEST.fixture.json').read_bytes())
    def archive(self,path,files=None,modify=None):
        files={'R046_README.ko.md':b'test payload\n'} if files is None else files
        m=dict(schema='hcr-r046-additive-v1',basis_commit=installer.BASE,
               files={n:hashlib.sha256(b.replace(b'\r\n',b'\n')).hexdigest() for n,b in files.items()})
        if modify:modify(m)
        with zipfile.ZipFile(path,'w') as z:
            for n,b in files.items():z.writestr(n,b)
            z.writestr('R046_MANIFEST.json',json.dumps(m))
        return path
    def test_discovery_modules_import_without_environment_pythonpath(self):
        import os,subprocess,sys
        env=dict(os.environ);env.pop('PYTHONPATH',None)
        paths=[str(ROOT/'tools/r046_thought_carry/tests'/n) for n in ('test_carry.py','test_parent_regression.py')]
        code="import runpy; "+"; ".join("runpy.run_path("+repr(n)+",run_name='packaging_import_check')" for n in paths)
        result=subprocess.run([sys.executable,'-X','utf8','-B','-c',code],cwd=ROOT,env=env,
                              stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=20)
        self.assertEqual(result.returncode,0,result.stdout.decode('utf-8','replace'))
    def test_install_and_identical_second_install(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)/'repo';self.make_root(root);z=self.archive(Path(t)/'p.zip')
            self.assertTrue(installer.install(root,z)['installed']);before=(root/'R046_README.ko.md').read_bytes()
            self.assertTrue(installer.install(root,z)['installed']);self.assertEqual(before,(root/'R046_README.ko.md').read_bytes())
    def test_conflict_is_detected_before_any_payload_write(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)/'repo';self.make_root(root);(root/'R046_README.ko.md').write_text('user edit')
            z=self.archive(Path(t)/'p.zip',{'Run-HCR-R046.py':b'x=1','R046_README.ko.md':b'new'})
            with self.assertRaises(ValueError):installer.install(root,z)
            self.assertFalse((root/'Run-HCR-R046.py').exists());self.assertEqual((root/'R046_README.ko.md').read_text(),'user edit')
    def test_wrong_old_baseline_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)/'repo';self.make_root(root);(root/'R045_MANIFEST.json').write_text('{}')
            z=self.archive(Path(t)/'p.zip')
            with self.assertRaises(ValueError):installer.install(root,z)
            self.assertFalse((root/'R046_MANIFEST.json').exists())
    def test_crlf_equivalent_file_is_not_rewritten(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)/'repo';self.make_root(root);p=root/'R046_README.ko.md';p.write_bytes(b'test payload\r\n')
            z=self.archive(Path(t)/'p.zip');installer.install(root,z);self.assertEqual(p.read_bytes(),b'test payload\r\n')
    def test_wrong_payload_hash_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            z=self.archive(Path(t)/'p.zip',modify=lambda m:m['files'].__setitem__('R046_README.ko.md','0'*64))
            with self.assertRaises(ValueError):installer.payload(z)
    def test_wrong_schema_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            z=self.archive(Path(t)/'p.zip',modify=lambda m:m.__setitem__('schema','wrong'))
            with self.assertRaises(ValueError):installer.payload(z)
    def test_duplicate_zip_entry_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            z=self.archive(Path(t)/'p.zip')
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')
                with zipfile.ZipFile(z,'a') as f:f.writestr('R046_README.ko.md','duplicate')
            with self.assertRaises(ValueError):installer.payload(z)
    def test_native_source_cannot_be_installed(self):
        with tempfile.TemporaryDirectory() as t:
            z=self.archive(Path(t)/'p.zip',{'src/hcr/dynamics.py':b'no'})
            with self.assertRaises(ValueError):installer.payload(z)
    def test_manifest_duplicate_json_rejected(self):
        with self.assertRaises(ValueError):installer.strict('{"x":1,"x":2}')
    def test_archive_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            z=Path(t)/'p.zip'
            with zipfile.ZipFile(z,'w') as f:
                info=zipfile.ZipInfo('R046_README.ko.md');info.create_system=3;info.external_attr=0o120777<<16;f.writestr(info,b'elsewhere')
            with self.assertRaises(ValueError):installer.payload(z)
    def test_host_link_rejected_without_privilege(self):
        with patch.object(Path,'is_symlink',return_value=True):
            with self.assertRaises(ValueError):installer.safe(Path.cwd()/'fake')
    def test_duplicate_hash_manifest_cannot_change_inventory(self):
        with tempfile.TemporaryDirectory() as t:
            z=self.archive(Path(t)/'p.zip',modify=lambda m:m['files'].__setitem__('Run-HCR-R046.py','0'*64))
            with self.assertRaises(ValueError):installer.payload(z)
    def test_path_boundaries(self):
        for n in ['../R046_README.ko.md','/absolute','C:/absolute','tools/r046_thought_carry/../bad','tools//r046_thought_carry/x','src/hcr/model.py','scripts/install_other.py','foo\\bar']:
            with self.subTest(n=n),self.assertRaises(ValueError):installer.check_name(n)
