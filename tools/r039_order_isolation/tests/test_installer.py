"""가짜 baseline/소형 archive로 파일 안전성만 검사한다. native 실행이 아니다."""
from pathlib import Path
import importlib.util
import hashlib,json,stat,tempfile,unittest,zipfile
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[3]
loader=importlib.util.spec_from_file_location('_r039_installer',ROOT/'scripts/install_r039.py')
installer=importlib.util.module_from_spec(loader);loader.loader.exec_module(installer)


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)/"연구 ! O'Brien %";self.root.mkdir()
        (self.root/'src/hcr').mkdir(parents=True)
        (self.root/'Run-HCR-R038.py').write_bytes(b'original\n')
        b=(json.dumps(dict(files={'Run-HCR-R038.py':installer.text_hash(b'original\n')}))+'\n').encode()
        (self.root/'R038_MANIFEST.json').write_bytes(b)
        h=hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
        p=patch.object(installer,'R038_BLOB',h);p.start();self.addCleanup(p.stop)
        self.arc=Path(self.temp.name)/'payload.zip'
    def payload(self,files=None,basis=None):
        files=files or {'R039_README.ko.md':b'new\n'}
        manifest=dict(schema='hcr-r039-additive-release-v1',basis_commit=basis or installer.BASIS,
            files={n:installer.text_hash(v) for n,v in files.items()})
        with zipfile.ZipFile(self.arc,'w') as z:
            for n,v in files.items():z.writestr(n,v)
            z.writestr('R039_MANIFEST.json',json.dumps(manifest).encode())
    def test_install_additive_in_special_character_path(self):
        self.payload();r=installer.install(self.root,self.arc)
        self.assertEqual(r['installed'],2);self.assertEqual((self.root/'Run-HCR-R038.py').read_bytes(),b'original\n')
    def test_identical_reinstall_does_not_overwrite(self):
        self.payload();installer.install(self.root,self.arc);r=installer.install(self.root,self.arc)
        self.assertEqual(r['installed'],0);self.assertEqual(r['already_identical'],2)
    def test_user_modified_file_conflict(self):
        self.payload();(self.root/'R039_README.ko.md').write_bytes(b'user edit')
        with self.assertRaises(ValueError):installer.install(self.root,self.arc)
        self.assertFalse((self.root/'R039_MANIFEST.json').exists())
        self.assertEqual((self.root/'R039_README.ko.md').read_bytes(),b'user edit')
    def test_old_baseline_changed(self):
        self.payload();(self.root/'Run-HCR-R038.py').write_bytes(b'changed')
        with self.assertRaises(ValueError):installer.install(self.root,self.arc)
        self.assertFalse((self.root/'R039_MANIFEST.json').exists())
    def test_payload_protected_file_refused(self):
        self.payload({'Run-HCR-R038.py':b'bad'})
        with self.assertRaises(ValueError):installer.install(self.root,self.arc)
    def test_manifest_basis_refused(self):
        self.payload(basis='bad')
        with self.assertRaises(ValueError):installer.install(self.root,self.arc)
    def test_missing_manifest_refused(self):
        with zipfile.ZipFile(self.arc,'w') as z:z.writestr('R039_README.ko.md','a')
        with self.assertRaises(ValueError):installer.read_payload(self.arc)
    def test_unlisted_payload_refused(self):
        self.payload()
        with zipfile.ZipFile(self.arc,'a') as z:z.writestr('docs/R039_unlisted.md','a')
        with self.assertRaises(ValueError):installer.read_payload(self.arc)
    def test_checksum_refused(self):
        self.payload()
        with zipfile.ZipFile(self.arc) as z:manifest=z.read('R039_MANIFEST.json')
        with zipfile.ZipFile(self.arc,'w') as z:z.writestr('R039_MANIFEST.json',manifest);z.writestr('R039_README.ko.md',b'bad')
        with self.assertRaises(ValueError):installer.read_payload(self.arc)
    def test_symlink_in_zip_refused(self):
        info=zipfile.ZipInfo('tools/r039_order_isolation/link');info.create_system=3;info.external_attr=(stat.S_IFLNK|0o777)<<16
        with zipfile.ZipFile(self.arc,'w') as z:z.writestr(info,'../../old')
        with self.assertRaises(ValueError):installer.read_payload(self.arc)
    def test_case_collision_refused(self):
        self.payload({'docs/R039_A.md':b'a','docs/R039_a.md':b'b'})
        with self.assertRaises(ValueError):installer.read_payload(self.arc)
    def test_parent_is_file_refused_before_write(self):
        self.payload({'docs/R039_A.md':b'a'});(self.root/'docs').write_text('block')
        with self.assertRaises(ValueError):installer.install(self.root,self.arc)
        self.assertFalse((self.root/'R039_MANIFEST.json').exists())
    def test_symlink_root_refused(self):
        # Windows의 symlink 생성 권한을 요구하지 않고 metadata 분기를 검사한다.
        self.payload();alias=Path(self.temp.name)/'alias';alias.mkdir();original=Path.is_symlink
        with patch.object(Path,'is_symlink',lambda p:p==alias or original(p)):
            with self.assertRaises(ValueError):installer.install(alias,self.arc)
    def test_failure_mid_install_preserved(self):
        self.payload();original=Path.open
        def fail(path,*args,**kwargs):
            if path==self.root/'R039_README.ko.md' and args and args[0]=='xb':raise OSError('simulated I/O failure')
            return original(path,*args,**kwargs)
        with patch.object(Path,'open',fail),self.assertRaises(OSError):installer.install(self.root,self.arc)
        f=list((self.root/'HCR-Evidence/deployments').glob('*/failure.json'))
        self.assertEqual(len(f),1);self.assertIn('R039_MANIFEST.json',json.loads(f[0].read_text())['created'])
    def test_json_duplicate_rejected(self):
        with self.assertRaises(ValueError):installer.loads('{"a":1,"a":2}')
    def test_json_nan_rejected(self):
        with self.assertRaises(ValueError):installer.loads('{"a":NaN}')
    def test_crlf_text_hash(self):self.assertEqual(installer.text_hash(b'a\r\n'),installer.text_hash(b'a\n'))


def path_test(value):
    def test(self):
        with self.assertRaises(ValueError):installer.check_path(value)
    return test
for i,path in enumerate(('../old','/root','C:/old','a\\b','a//b','a/./b','a/../b','NUL','docs/CON.txt','docs/AUX',
                        'docs/COM1.txt','docs/LPT9','docs/name.','docs/name ','docs/a:b','docs/a?b','docs/a\0b')):
    setattr(InstallerTests,f'test_reject_unsafe_path_{i:02d}',path_test(path))
