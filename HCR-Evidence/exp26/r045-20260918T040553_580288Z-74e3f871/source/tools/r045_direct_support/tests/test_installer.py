"""Installer tests use temporary synthetic checkouts; never install into a user's repository."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile
ROOT=Path(__file__).resolve().parents[3]
spec=importlib.util.spec_from_file_location('r045_installer_test_target',ROOT/'scripts/install_r045.py')
installer=importlib.util.module_from_spec(spec);spec.loader.exec_module(installer)


def payload(path):
    names=(installer.ROOT_FILES | installer.SCRIPT_FILES)-{'R045_MANIFEST.json'}
    files={n:b'synthetic-installer-test\n' for n in names}
    manifest=dict(schema='hcr-r045-additive-release-v1',basis_commit=installer.BASIS,
                  files={n:installer.text_hash(b) for n,b in files.items()})
    files['R045_MANIFEST.json']=(json.dumps(manifest)+'\n').encode()
    with zipfile.ZipFile(path,'w') as z:
        for n,b in files.items():z.writestr(n,b)
    return files


class InstallerTests(unittest.TestCase):
    def test_payload(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'p.zip';files=payload(p);self.assertEqual(installer.read_payload(p),files)
    def test_non_r045_paths_not_allowed(self):
        for n in ('src/hcr/sessions.py','R044_MANIFEST.json','.git/config','tools/r044_reuse_contribution/runtime.py'):
            self.assertFalse(installer.allowed(n))
    def test_path_hazards(self):
        for n in ('../x','C:foo','x\\y','/tmp/x','CON.txt','a/NUL.py','a.','a/../b','a//b','a\x00b'):
            with self.subTest(name=n):
                with self.assertRaises(ValueError):installer.check_path(n)
    def test_archive_tampering(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'p.zip';files=payload(p);files['R045_README.ko.md']=b'changed'
            with zipfile.ZipFile(p,'w') as z:
                for n,b in files.items():z.writestr(n,b)
            with self.assertRaises(ValueError):installer.read_payload(p)
    def test_case_collision(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'p.zip';payload(p)
            with zipfile.ZipFile(p,'a') as z:z.writestr('docs/R045_DOC.md',b'a');z.writestr('docs/R045_doc.md',b'a')
            with self.assertRaises(ValueError):installer.read_payload(p)
    def test_missing_required_files(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'p.zip'
            with zipfile.ZipFile(p,'w') as z:z.writestr('R045_MANIFEST.json','{}')
            with self.assertRaises(ValueError):installer.read_payload(p)
    def test_new_files_then_identical_reinstall(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'repo';root.mkdir();p=Path(d)/'p.zip';files=payload(p)
            with patch.object(installer,'check_basis',return_value=None):
                first=installer.install(root,p);second=installer.install(root,p)
            self.assertEqual(first['installed'],len(files));self.assertEqual(second['installed'],0)
            self.assertEqual(second['already_identical'],len(files))
    def test_conflicting_existing_file_never_overwritten(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'repo';root.mkdir();p=Path(d)/'p.zip';payload(p)
            (root/'Run-HCR-R045.py').write_text('user-modification')
            with patch.object(installer,'check_basis',return_value=None):
                with self.assertRaises(ValueError):installer.install(root,p)
            self.assertEqual((root/'Run-HCR-R045.py').read_text(),'user-modification')
            self.assertFalse((root/'R045_MANIFEST.json').exists())
            self.assertEqual(len(list((root/'HCR-Evidence/deployments').glob('*/failure.json'))),1)
    def test_bad_baseline_no_install(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'repo';root.mkdir();p=Path(d)/'p.zip';payload(p)
            with self.assertRaises(ValueError):installer.install(root,p)
            self.assertFalse((root/'R045_MANIFEST.json').exists())
    def test_baseline_pin(self):
        self.assertEqual(installer.BASIS,'3bfeb64af877a7512071798fd77d8eba839760a1')
        self.assertEqual(installer.R044_BLOB,'86eaf459d963220845512c766b707ba3b4c0a1f6')

if __name__=='__main__':unittest.main()
