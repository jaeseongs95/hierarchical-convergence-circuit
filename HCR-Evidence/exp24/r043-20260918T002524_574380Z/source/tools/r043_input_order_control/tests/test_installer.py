"""Installer fault injection; fake repository checks are not native validation."""
import importlib.util
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest
import zipfile

ROOT=Path(__file__).resolve().parents[3]
spec=importlib.util.spec_from_file_location('r043_installer_for_unit_test',ROOT/'scripts/install_r043.py')
installer=importlib.util.module_from_spec(spec);spec.loader.exec_module(installer)


def archive(path,content=b'fixture-only\n',extra=None):
    payload={'R043_README.ko.md':content}
    if extra:payload.update(extra)
    manifest={'schema':'hcr-r043-additive-release-v1','basis_commit':installer.BASIS,
        'files':{n:installer.text_hash(b) for n,b in payload.items()}}
    with zipfile.ZipFile(path,'w') as z:
        for n,b in payload.items():z.writestr(n,b)
        z.writestr('R043_MANIFEST.json',json.dumps(manifest).encode())

class Installer(unittest.TestCase):
    def test_archive_validated(self):
        with TemporaryDirectory() as d:
            p=Path(d)/'x.zip';archive(p);self.assertEqual(len(installer.read_payload(p)),2)
    def test_unsafe_and_foreign_paths_rejected(self):
        for name in ('../escape','src/hcr/core.py','tools/r043_input_order_control/../bad',
                     'tools/r043_input_order_control/CON.txt','docs/R043_bad.md:ads'):
            with self.subTest(name=name),TemporaryDirectory() as d:
                p=Path(d)/'x.zip';archive(p,extra={name:b'bad'})
                with self.assertRaises(ValueError):installer.read_payload(p)
    def test_tampered_bytes_rejected(self):
        with TemporaryDirectory() as d:
            p=Path(d)/'x.zip';archive(p)
            with zipfile.ZipFile(p) as z:content={n:z.read(n) for n in z.namelist()}
            content['R043_README.ko.md']=b'changed'
            with zipfile.ZipFile(p,'w') as z:
                for n,b in content.items():z.writestr(n,b)
            with self.assertRaises(ValueError):installer.read_payload(p)
    def test_additive_idempotent_install(self):
        with TemporaryDirectory() as d:
            root=Path(d)/'repo';root.mkdir();p=Path(d)/'x.zip';archive(p)
            with patch.object(installer,'check_basis'):
                a=installer.install(root,p);b=installer.install(root,p)
            self.assertEqual(a['installed'],2);self.assertEqual(b['installed'],0)
            self.assertEqual(b['already_identical'],2)
            self.assertEqual(len(list((root/'HCR-Evidence/deployments').glob('*/installation.json'))),2)
    def test_conflict_before_source_write_preserves_original(self):
        with TemporaryDirectory() as d:
            root=Path(d)/'repo';root.mkdir();p=Path(d)/'x.zip';archive(p)
            f=root/'R043_README.ko.md';f.write_bytes(b'user edit')
            with patch.object(installer,'check_basis'),self.assertRaises(ValueError):installer.install(root,p)
            self.assertEqual(f.read_bytes(),b'user edit');self.assertFalse((root/'R043_MANIFEST.json').exists())
            failure=list((root/'HCR-Evidence/deployments').glob('*/failure.json'))
            self.assertEqual(len(failure),1);self.assertEqual(json.loads(failure[0].read_text())['created'],[])
    def test_baseline_failure_is_logged_without_new_source(self):
        with TemporaryDirectory() as d:
            root=Path(d)/'repo';root.mkdir();p=Path(d)/'x.zip';archive(p)
            with patch.object(installer,'check_basis',side_effect=ValueError('baseline mismatch')),self.assertRaises(ValueError):installer.install(root,p)
            self.assertFalse((root/'R043_MANIFEST.json').exists())
            self.assertEqual(len(list((root/'HCR-Evidence/deployments').glob('*/failure.json'))),1)
    def test_path_case_collision_rejected(self):
        with TemporaryDirectory() as d:
            p=Path(d)/'x.zip'
            archive(p,extra={'tools/r043_input_order_control/A.py':b'a','tools/r043_input_order_control/a.py':b'b'})
            with self.assertRaises(ValueError):installer.read_payload(p)
