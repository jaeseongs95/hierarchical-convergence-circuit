from pathlib import Path
import importlib.util
import os
import shutil
import subprocess
import tempfile
import unittest
import zipfile
from unittest.mock import patch
from tools.r048_precision import io,provenance
ROOT=Path(__file__).resolve().parents[3]
spec=importlib.util.spec_from_file_location('r048_installer_test',ROOT/'scripts/r048_install.py')
installer=importlib.util.module_from_spec(spec);spec.loader.exec_module(installer)


def fixture_parent(root):
    root.mkdir()
    content={'source/Run-HCR-R047.cmd':b'@echo off\r\necho fixture\r\n',
             'raw/A.json':b'{"fixture":true}\n','source/validation/test.log':b'original log\r\n'}
    for n,b in content.items():io.write(io.child(root,n),b)
    manifest=dict(schema='hcr-exp28-bundle-v1',files={n:io.sha(b) for n,b in content.items()})
    io.put(root/'bundle_manifest.json',manifest)
    return manifest,content

class Storage(unittest.TestCase):
    def test_duplicate_json_rejected(self):
        with self.assertRaises(ValueError):io.loads('{"x":1,"x":2}')
    def test_nonfinite_json_rejected(self):
        for x in ('NaN','Infinity','1e1000'):
            with self.assertRaises(ValueError):io.loads('{"x":'+x+'}')
    def test_no_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'x';io.write(p,b'first')
            with self.assertRaises(FileExistsError):io.write(p,b'second')
            self.assertEqual(io.read(p),b'first')
    def test_path_traversal(self):
        with tempfile.TemporaryDirectory() as d:
            for n in ('../x','/x','C:/x','a\\x','a//x','a/../x'):
                with self.assertRaises(ValueError):io.child(Path(d),n)
    def test_recover_exact_bytes_copy_only(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);m,original=fixture_parent(root/'old')
            for n in original:(root/'old'/n).write_bytes(io.lf(original[n]))
            before=io.hashes(root/'old')
            report=provenance.restore_parent_copy(root/'old',root/'new',m)
            self.assertEqual(report['restored'],2);self.assertEqual(io.hashes(root/'old'),before)
            for n,b in original.items():self.assertEqual(io.read(root/'new'/n),b)
    def test_changed_content_not_blessed_by_new_hash(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);m,_=fixture_parent(root/'old');(root/'old/raw/A.json').write_bytes(b'{"fixture":false}\n')
            with self.assertRaises(ValueError):provenance.restore_parent_copy(root/'old',root/'new',m)
            self.assertFalse((root/'new').exists())
    def test_missing_log_is_not_regenerated(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);m,_=fixture_parent(root/'old');(root/'old/source/validation/test.log').unlink()
            with self.assertRaises(ValueError):provenance.restore_parent_copy(root/'old',root/'new',m)
    def test_extra_file_not_silently_omitted(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);m,_=fixture_parent(root/'old');io.write(root/'old/extra.txt',b'extra')
            with self.assertRaises(ValueError):provenance.restore_parent_copy(root/'old',root/'new',m)
    def test_first_error_preserved(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);io.failure(root,'first',ValueError('one'));b=io.read(root/'failure.json')
            io.failure(root,'second',ValueError('two'));self.assertEqual(io.read(root/'failure.json'),b)

class Publication(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.repo=Path(self.temp.name)/'한글 공백 저장소';self.repo.mkdir()
        self.env=dict(os.environ,GIT_CONFIG_NOSYSTEM='1',GIT_CONFIG_GLOBAL=os.devnull)
        # No user's repository, index, signature settings, or hooks are touched.
        self.patcher=patch.dict(os.environ,{'GIT_CONFIG_NOSYSTEM':'1','GIT_CONFIG_GLOBAL':os.devnull})
        self.patcher.start();self.git('init','-q')
        self.git('config','core.autocrlf','true')
        io.write(self.repo/'.gitattributes',b'* text=auto\n*.py text eol=lf\n*.json text eol=lf\n*.ps1 text eol=crlf\n')
        io.write(self.repo/'.gitignore',b'*.log\n*.zip\n')
        self.run=self.repo/'HCR-Evidence/exp29/r048-fixture'
        self.run.mkdir(parents=True)
        io.write(self.run/'.gitattributes',provenance.ATTRIBUTES)
        io.write(self.run/'.gitignore',b'!*\n')
        io.write(self.run/'source/launcher.cmd',b'@echo off\r\necho preserve\r\n')
        io.write(self.run/'source/test.ps1',b'Write-Host "LF"\n')
        io.write(self.run/'raw/기록.json',b'{"one":1}\n')
        io.write(self.run/'logs/first.log',b'failure preserved\r\n')
    def tearDown(self):self.patcher.stop();self.temp.cleanup()
    def git(self,*args):
        p=subprocess.run(['git','-C',str(self.repo),*args],stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=self.env)
        if p.returncode:raise RuntimeError(p.stderr.decode('utf-8','replace'))
        return p.stdout
    def test_git_clean_hash_identical_and_index_not_written(self):
        self.assertFalse((self.repo/'.git/index').exists())
        self.assertTrue(provenance.publication_check(self.repo,self.run)['verified'])
        self.assertFalse((self.repo/'.git/index').exists())
    def test_missing_override_detected(self):
        (self.run/'.gitattributes').unlink()
        with self.assertRaises(ValueError):provenance.publication_check(self.repo,self.run)
    def test_index_and_checkout_preserve_CMD_PS1_logs_bytes(self):
        before=io.hashes(self.run)
        self.git('add','--','.gitattributes','.gitignore','HCR-Evidence/exp29')
        # Synthetic Git fixture only; checkout-index creates no commit and contacts no remote.
        target=Path(self.temp.name)/'checkout';target.mkdir()
        self.git('-c','core.autocrlf=false','checkout-index','--all','--prefix='+target.as_posix()+'/')
        self.assertEqual(io.hashes(target/'HCR-Evidence/exp29/r048-fixture'),before)
    def test_missing_ignore_override_detected(self):
        (self.run/'.gitignore').unlink()
        with self.assertRaises(ValueError):provenance.publication_check(self.repo,self.run)
    def test_real_import_shadow_regression(self):
        io.write(self.repo/'hcr.py',b'raise RuntimeError("ROOT_SHADOW_SELECTED")\n')
        io.write(self.repo/'src/hcr/__init__.py',b'MARKER="package"\n')
        io.write(self.repo/'tools/r048_precision/tests/test_fixture.py',b'import unittest, hcr\nclass T(unittest.TestCase):\n def test_origin(self): self.assertEqual(hcr.MARKER,"package")\n')
        io.write(self.repo/'scripts/r048_tests.py',io.read(ROOT/'scripts/r048_tests.py'))
        import sys
        p=subprocess.run([sys.executable,'-X','utf8','-B',str(self.repo/'scripts/r048_tests.py'),
            '--root',str(self.repo),'--suite','new'],cwd=self.repo,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        self.assertEqual(p.returncode,0,p.stderr.decode())

class Installer(unittest.TestCase):
    def archive(self,p,badname=None,badhash=False):
        files={'tools/r048_precision/fixture.py':b'# fixture\n'}
        if badname:files[badname]=b'bad'
        m=dict(schema='hcr-r048-release-v1',base_commit=installer.BASE,files={n:io.sha(b) for n,b in files.items()})
        if badhash:m['files']['tools/r048_precision/fixture.py']='0'*64
        with zipfile.ZipFile(p,'w') as z:
            for n,b in files.items():z.writestr(n,b)
            z.writestr('R048_MANIFEST.json',io.encode(m))
    def test_archive_rejects_checksum_and_path_and_old_source_write(self):
        for kw in ({'badname':'../escape'},{'badhash':True},{'badname':'src/hcr/model.py'},{'badname':'TOOLS/r048_precision/FIXTURE.py'}):
            with tempfile.TemporaryDirectory() as d:
                p=Path(d)/'x.zip';self.archive(p,**kw)
                with self.assertRaises(ValueError):installer.read_archive(p)
    def test_additive_install_and_repeat_preserve_old_files(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);repo=root/'repo';repo.mkdir();io.write(repo/'old.py',b'USER FILE')
            p=root/'source.zip';self.archive(p)
            def fake_preflight(repo,entries):return 'synthetic', [n for n in entries if not (repo/n).exists()]
            before=io.read(repo/'old.py')
            with patch.object(installer,'preflight',fake_preflight):
                self.assertEqual(installer.install(repo,p),0);self.assertEqual(installer.install(repo,p),0)
            self.assertEqual(io.read(repo/'old.py'),before)
    def test_installer_first_failure_record_no_source_change(self):
        with tempfile.TemporaryDirectory() as d:
            repo=Path(d)/'repo';repo.mkdir();p=Path(d)/'a.zip';self.archive(p)
            with patch.object(installer,'preflight',side_effect=ValueError('injected fixture failure')):
                with self.assertRaises(ValueError):installer.install(repo,p)
            self.assertFalse((repo/'tools/r048_precision/fixture.py').exists())
            self.assertEqual(len(list(repo.rglob('failure.json'))),1)
