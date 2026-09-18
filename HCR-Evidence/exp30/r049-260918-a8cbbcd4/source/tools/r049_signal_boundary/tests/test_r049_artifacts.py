from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import importlib.util
import os
import shutil
import subprocess
import sys
import unittest
import zipfile
from tools.r048_precision import io
from tools.r049_signal_boundary import spec,provenance,pipeline
ROOT=Path(__file__).resolve().parents[3]
ms=importlib.util.spec_from_file_location('r049_installer_fixture',ROOT/'scripts/r049_install.py')
installer=importlib.util.module_from_spec(ms);ms.loader.exec_module(installer)


def fixture_archive(path, files=None):
    files=files or {'tools/r049_signal_boundary/example.py':b'# fixture\n'}
    m=dict(schema='hcr-r049-release-v1',base_commit=spec.BASE_COMMIT,files={n:io.sha(io.lf(b)) for n,b in files.items()})
    with zipfile.ZipFile(path,'w') as z:
        for n,b in files.items():z.writestr(n,b)
        z.writestr('R049_MANIFEST.json',io.encode(m)+b'\n')
    return files,m


def git(root,*args):
    p=subprocess.run(['git','-C',str(root),*args],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    if p.returncode:raise RuntimeError(p.stderr.decode('utf-8','replace'))
    return p.stdout


class Installer(unittest.TestCase):
    def test_archive_checksum_and_inventory(self):
        with TemporaryDirectory() as d:
            z=Path(d)/'source.zip';files,m=fixture_archive(z)
            entries,actual=installer.read_archive(z);self.assertEqual(actual,m);self.assertEqual(len(entries),2)
    def test_archive_path_traversal_rejected(self):
        with TemporaryDirectory() as d:
            z=Path(d)/'source.zip';fixture_archive(z,{'../escape.py':b'x'})
            with self.assertRaises(ValueError):installer.read_archive(z)
    def test_archive_private_git_write_rejected(self):
        with TemporaryDirectory() as d:
            z=Path(d)/'source.zip';fixture_archive(z,{'.git/config':b'x'})
            with self.assertRaises(ValueError):installer.read_archive(z)
    def test_archive_old_source_write_rejected(self):
        with TemporaryDirectory() as d:
            z=Path(d)/'source.zip';fixture_archive(z,{'src/hcr/model.py':b'x'})
            with self.assertRaises(ValueError):installer.read_archive(z)
    def test_archive_casefold_duplicate_rejected(self):
        with TemporaryDirectory() as d:
            z=Path(d)/'source.zip';fixture_archive(z,{'tools/r049_signal_boundary/x.py':b'x','TOOLS/r049_signal_boundary/X.PY':b'x'})
            with self.assertRaises(ValueError):installer.read_archive(z)
    def test_archive_changed_manifest_hash_rejected(self):
        with TemporaryDirectory() as d:
            z=Path(d)/'source.zip'
            with zipfile.ZipFile(z,'w') as f:
                f.writestr('tools/r049_signal_boundary/x.py',b'new')
                f.writestr('R049_MANIFEST.json',io.encode(dict(schema='hcr-r049-release-v1',base_commit=spec.BASE_COMMIT,
                    files={'tools/r049_signal_boundary/x.py':'0'*64})))
            with self.assertRaises(ValueError):installer.read_archive(z)
    def test_existing_different_file_never_overwritten(self):
        with TemporaryDirectory() as d:
            root=Path(d);target=root/'tools/r049_signal_boundary/x.py';target.parent.mkdir(parents=True);target.write_bytes(b'user content')
            class Result:returncode=0;stderr=b'';stdout=b''
            def simulate(command,**kw):
                p=Result();p.stdout=str(root).encode() if '--show-toplevel' in command else spec.BASE_COMMIT.encode();return p
            with patch.object(installer.subprocess,'run',simulate):
                with self.assertRaises(ValueError):installer.preflight(root,{'tools/r049_signal_boundary/x.py':b'new'})
            self.assertEqual(target.read_bytes(),b'user content')
    def test_install_fixture_idempotent_no_launch(self):
        with TemporaryDirectory() as d:
            root=Path(d)/'한글 공백';root.mkdir();z=Path(d)/'source.zip';fixture_archive(z)
            def preflight(repo,entries):return spec.BASE_COMMIT,[n for n in entries if not (repo/n).exists()]
            with patch.object(installer,'preflight',preflight):
                self.assertEqual(installer.install(root,z,False),0);self.assertEqual(installer.install(root,z,False),0)
            self.assertEqual(len(list(root.glob('HCR-Evidence/deployments/r049-install-*'))),2)
    def test_failed_preflight_preserves_journal(self):
        with TemporaryDirectory() as d:
            root=Path(d)/'repo';root.mkdir();z=Path(d)/'source.zip';fixture_archive(z)
            with patch.object(installer,'preflight',side_effect=ValueError('intentional test failure')):
                with self.assertRaises(ValueError):installer.install(root,z)
            self.assertEqual(len(list(root.rglob('failure.json'))),1)
            self.assertFalse((root/'tools').exists())


class ParentAndSeal(unittest.TestCase):
    def test_parent_copy_restores_only_hash_exact_line_endings(self):
        with TemporaryDirectory() as d:
            root=Path(d);src=root/'original';src.mkdir();dest=root/'copy'
            raw=b'@echo off\r\necho evidence\r\n';m=dict(schema='hcr-exp29-bundle-v1',files={'x.cmd':io.sha(raw)})
            io.write(src/'x.cmd',io.lf(raw));io.put(src/'bundle_manifest.json',m)
            before=io.hashes(src);result=provenance.restore_copy(src,dest,m)
            self.assertEqual(result['restored'],1);self.assertEqual(io.read(dest/'x.cmd'),raw);self.assertEqual(before,io.hashes(src))
    def test_parent_changed_content_refused_before_copy(self):
        with TemporaryDirectory() as d:
            src=Path(d)/'src';src.mkdir();m=dict(schema='hcr-exp29-bundle-v1',files={'x.txt':io.sha(b'original\n')})
            io.write(src/'x.txt',b'wrong\n');io.put(src/'bundle_manifest.json',m);dest=Path(d)/'copy'
            with self.assertRaises(ValueError):provenance.restore_copy(src,dest,m)
            self.assertFalse(dest.exists())
    def test_parent_missing_original_log_not_generated(self):
        with TemporaryDirectory() as d:
            src=Path(d)/'src';src.mkdir();m=dict(schema='hcr-exp29-bundle-v1',files={'first_failure.log':'0'*64});io.put(src/'bundle_manifest.json',m)
            with self.assertRaises(ValueError):provenance.restore_copy(src,Path(d)/'copy',m)
    def test_extra_parent_file_not_silently_skipped(self):
        with TemporaryDirectory() as d:
            src=Path(d)/'src';src.mkdir();m=dict(schema='hcr-exp29-bundle-v1',files={});io.put(src/'bundle_manifest.json',m);io.write(src/'extra.txt',b'x')
            with self.assertRaises(ValueError):provenance.restore_copy(src,Path(d)/'copy',m)
    def test_zip_roundtrip_exact_bytes(self):
        with TemporaryDirectory() as d:
            root=Path(d)/'run';root.mkdir();io.write(root/'x.cmd',b'cmd\r\n');pipeline.seal_bundle(root)
            r=pipeline.archive(root)
            with zipfile.ZipFile(root.parent/r['archive']) as z:self.assertEqual(z.read('x.cmd'),b'cmd\r\n')
    def test_postseal_extra_file_refused(self):
        with TemporaryDirectory() as d:
            root=Path(d)/'run';root.mkdir();io.write(root/'x',b'initial');pipeline.seal_bundle(root);io.write(root/'new',b'extra')
            with self.assertRaises(ValueError):pipeline.archive(root)
    def test_second_seal_does_not_overwrite(self):
        with TemporaryDirectory() as d:
            root=Path(d);io.write(root/'x',b'v');pipeline.seal_bundle(root)
            with self.assertRaises(FileExistsError):pipeline.seal_bundle(root)
    def test_paths_and_nonfinite_json_refused(self):
        with TemporaryDirectory() as d:
            for n in ('../x','C:/x','a\\b','a//b'):
                with self.assertRaises(ValueError):io.child(Path(d),n)
            for s in ('{"a":1,"a":2}','{"x":NaN}','{"x":1e999}'):
                with self.assertRaises(ValueError):io.loads(s)
    def test_link_paths_refused(self):
        with patch.object(Path,'is_symlink',return_value=True):
            with self.assertRaises(ValueError):io.safe('fixture')


class GitPublication(unittest.TestCase):
    def test_clean_filter_and_checkout_preserve_sealed_bytes(self):
        # All git writes below target a disposable fixture, never the user's repository/index.
        with TemporaryDirectory() as d:
            repo=Path(d)/'한글 공백';repo.mkdir();git(repo,'init');git(repo,'config','core.autocrlf','true')
            run=repo/'HCR-Evidence/exp30/fixture';run.mkdir(parents=True)
            io.write(repo/'.gitattributes',b'* text=auto\n*.ps1 text eol=crlf\n')
            io.write(run/'.gitattributes',provenance.ATTRIBUTES);io.write(run/'.gitignore',b'!*\n')
            io.write(run/'a.cmd',b'first\r\nsecond\r\n');io.write(run/'b.py',b'first\nsecond\n')
            io.write(run/'c.ps1',b'first\n');io.write(run/'first_failure.log',b'failure\r\n')
            before=io.hashes(run);result=provenance.publication_check(repo,run);self.assertTrue(result['verified'])
            git(repo,'add','--','.');git(repo,'-c','user.name=HCR-Fixture','-c','user.email=fixture@example.invalid','-c','commit.gpgsign=false','commit','-m','isolated fixture')
            for n,h in before.items():self.assertEqual(io.sha(git(repo,'show','HEAD:HCR-Evidence/exp30/fixture/'+n)),h)
            for n in before:(run/n).unlink()
            git(repo,'checkout','--','HCR-Evidence/exp30/fixture')
            self.assertEqual(io.hashes(run),before)
    def test_unprotected_text_conversion_detected(self):
        with TemporaryDirectory() as d:
            root=Path(d);git(root,'init');git(root,'config','core.autocrlf','true')
            run=root/'run';run.mkdir();io.write(root/'.gitattributes',b'* text=auto\n');io.write(run/'x.cmd',b'x\r\n')
            with self.assertRaises(ValueError):provenance.publication_check(root,run)
    def test_ignored_evidence_detected(self):
        with TemporaryDirectory() as d:
            root=Path(d);git(root,'init');io.write(root/'.gitignore',b'*.log\n')
            run=root/'run';run.mkdir();io.write(run/'.gitattributes',provenance.ATTRIBUTES);io.write(run/'missing.log',b'x')
            with self.assertRaises(ValueError):provenance.publication_check(root,run)
