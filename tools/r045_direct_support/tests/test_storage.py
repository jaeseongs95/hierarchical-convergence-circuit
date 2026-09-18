import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from r045_direct_support import storage as io
from r045_direct_support.cli import bundle


class StorageTests(unittest.TestCase):
    def test_duplicate_keys_rejected(self):
        with self.assertRaises(ValueError):io.loads('{"a":1,"a":2}')
    def test_nonfinite_rejected(self):
        for value in ('NaN','Infinity','-Infinity','1e10000'):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):io.loads(value)
    def test_canonical_nonfinite_rejected(self):
        with self.assertRaises(ValueError):io.canonical({'v':float('nan')})
    def test_text_normalization_not_raw_normalization(self):
        with tempfile.TemporaryDirectory() as d:
            a,b=Path(d)/'a',Path(d)/'b';io.write_bytes(a,b'x\r\n');io.write_bytes(b,b'x\n')
            self.assertEqual(io.text_hash(a),io.text_hash(b));self.assertNotEqual(io.file_hash(a),io.file_hash(b))
    def test_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'raw.json';io.put(p,{'a':1})
            with self.assertRaises(FileExistsError):io.put(p,{'a':2})
            self.assertEqual(io.load(p),{'a':1})
    def test_paths(self):
        with tempfile.TemporaryDirectory() as d:
            for path in ('../x','/tmp/x','a//b','a/./b','C:foo','x\\y'):
                with self.subTest(path=path):
                    with self.assertRaises(ValueError):io.child(d,path)
    def test_symlink(self):
        # Portable boundary test: no Windows symlink privilege, skip or silent pass.
        with tempfile.TemporaryDirectory() as d:
            with patch.object(io,'is_link',side_effect=lambda p:Path(p).name=='link'):
                with self.assertRaises(ValueError):io.safe(Path(d)/'link'/'x')
    def test_disjoint(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):io.disjoint(Path(d),Path(d)/'run')
    def test_partial_bundle_label_and_crc(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'partial';root.mkdir();io.put(root/'failure.json',{'error':'first'})
            r=bundle(root,Path(d)/'partial.zip')
            self.assertFalse(r['raw_complete']);self.assertFalse(r['analysis_present'])
    def test_bundle_with_execution_snapshot(self):
        import zipfile
        with tempfile.TemporaryDirectory() as d:
            d=Path(d);root=d/'run';logs=d/'logs';root.mkdir();logs.mkdir()
            io.put(root/'a.json',{'raw':1});io.put(logs/'prebundle.json',{'checks':True})
            r=bundle(root,d/'bundle.zip',logs)
            self.assertTrue(r['execution_snapshot_included'])
            with zipfile.ZipFile(d/'bundle.zip') as z:
                m=io.loads(z.read('BUNDLE-MANIFEST.json'))
                self.assertIn('execution/prebundle.json',m['files'])
                self.assertEqual(m['files']['run/a.json'],io.file_hash(root/'a.json'))
    def test_bundle_refuses_existing_zip(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'run';root.mkdir();io.put(root/'a.json',{})
            target=Path(d)/'z.zip';bundle(root,target)
            with self.assertRaises(ValueError):bundle(root,target)

if __name__=='__main__':unittest.main()
