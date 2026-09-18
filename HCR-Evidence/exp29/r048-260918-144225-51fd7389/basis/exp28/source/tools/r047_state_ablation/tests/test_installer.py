from pathlib import Path
import importlib.util
import json
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT=Path(__file__).resolve().parents[3]
spec=importlib.util.spec_from_file_location('r047_installer_test',ROOT/'scripts/install_r047.py')
installer=importlib.util.module_from_spec(spec);spec.loader.exec_module(installer)


def archive(path,extra=None):
    files={'tools/example.py':b'# fixture, not experiment\n'}
    if extra:files.update(extra)
    m=dict(schema='hcr-r047-release-v1',base_commit='b'*40,native_blobs={},files={n:installer.sha(b) for n,b in files.items()})
    with zipfile.ZipFile(path,'w') as z:
        for n,b in files.items():z.writestr(n,b)
        z.writestr('R047_MANIFEST.json',json.dumps(m))
    return files,m


class InstallerTests(unittest.TestCase):
    def test_release_hash_verified(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'source.zip';files,m=archive(p)
            content,actual=installer.read_archive(p)
            self.assertEqual(actual,m);self.assertEqual(content['tools/example.py'],files['tools/example.py'])
    def test_zip_traversal_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'source.zip';archive(p,{'../evil.py':b'x'})
            with self.assertRaises(ValueError):installer.read_archive(p)
    def test_zip_case_alias_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'source.zip';archive(p,{'TOOLS/EXAMPLE.PY':b'x'})
            with self.assertRaises(ValueError):installer.read_archive(p)
    def test_archive_corruption_detected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'source.zip';files,m=archive(p)
            m['files']['tools/example.py']='0'*64
            with zipfile.ZipFile(p,'w') as z:
                z.writestr('tools/example.py',files['tools/example.py']);z.writestr('R047_MANIFEST.json',json.dumps(m))
            with self.assertRaises(ValueError):installer.read_archive(p)
    def test_install_exclusive_idempotent_fixture(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'repo';root.mkdir();z=Path(d)/'source.zip';archive(z)
            def preflight(repo,payload,m):return 'fixture_only',[n for n in payload if not (repo/n).exists()]
            # Only Git ancestry is mocked in this installer fixture; no research pipeline is launched.
            with patch.object(installer,'validate_target',preflight):
                first=installer.install(root,z);second=installer.install(root,z)
            self.assertNotEqual(first,second)
            self.assertEqual(json.loads((second/'completed.json').read_text())['created'],[])
    def test_preflight_failure_writes_first_failure_no_source(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'repo';root.mkdir();z=Path(d)/'source.zip';archive(z)
            with patch.object(installer,'validate_target',side_effect=ValueError('fixture baseline failure')):
                with self.assertRaises(ValueError):installer.install(root,z)
            self.assertFalse((root/'tools/example.py').exists())
            self.assertEqual(len(list(root.rglob('failure.json'))),1)
    def test_existing_different_file_refused(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'x.py').write_bytes(b'user edits')
            class P:
                returncode=0;stderr=''
                stdout=''
            def fakegit(command,**kwargs):
                p=P();p.stdout=str(root) if '--show-toplevel' in command else 'b'*40;return p
            with patch.object(installer.subprocess,'run',fakegit):
                with self.assertRaises(ValueError):installer.validate_target(root,{'x.py':b'new'},dict(base_commit='b'*40,native_blobs={}))
            self.assertEqual((root/'x.py').read_bytes(),b'user edits')
