"""Temporary fixture file mutations only; no user repository is modified by tests."""
from pathlib import Path
import tempfile
import unittest
from tools.r050_review_boundary.common import IntegrityError, publish, sha
from tools.r050_review_boundary.maintenance import apply_operations, replace_guarded, rollback

class Transactions(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.base=Path(self.tmp.name)
        self.root=self.base/'repo';self.root.mkdir()
        self.payload=self.base/'payload';self.payload.mkdir()
        self.receipt=self.base/'receipt';self.receipt.mkdir()
    def tearDown(self):self.tmp.cleanup()
    def addition(self):
        (self.payload/'new.py').write_bytes(b'new\n')
        return dict(kind='add',path='new.py',before_sha256=None,after_sha256=sha(b'new\n'))
    def test_add_and_owned_rollback(self):
        op=self.addition();applied=apply_operations(self.root,self.payload,self.receipt,[op],b'')
        self.assertEqual((self.root/'new.py').read_bytes(),b'new\n')
        self.assertTrue(rollback(self.root,self.receipt,applied)['complete'])
        self.assertFalse((self.root/'new.py').exists())
    def test_external_edit_preserved_on_rollback(self):
        op=self.addition();apply_operations(self.root,self.payload,self.receipt,[op],b'')
        (self.root/'new.py').write_bytes(b'user change')
        result=rollback(self.root,self.receipt,[op])
        self.assertFalse(result['complete']);self.assertEqual((self.root/'new.py').read_bytes(),b'user change')
    def test_existing_file_not_overwritten(self):
        op=self.addition();(self.root/'new.py').write_bytes(b'user')
        with self.assertRaises(IntegrityError):apply_operations(self.root,self.payload,self.receipt,[op],b'')
        self.assertEqual((self.root/'new.py').read_bytes(),b'user')
    def test_replace_and_restore_original_bytes(self):
        before=b'original\r\n';after=b'changed\n';path=self.root/'INDEX.json';path.write_bytes(before)
        publish(self.receipt/'preimages'/'INDEX.json',before)
        op=dict(kind='replace',path='INDEX.json',before_sha256=sha(before),after_sha256=sha(after))
        apply_operations(self.root,self.payload,self.receipt,[op],after)
        self.assertTrue(rollback(self.root,self.receipt,[op])['complete'])
        self.assertEqual(path.read_bytes(),before)
    def test_compare_before_replace(self):
        path=self.root/'x';path.write_bytes(b'changed externally')
        with self.assertRaises(IntegrityError):replace_guarded(path,b'old',b'new')
        self.assertEqual(path.read_bytes(),b'changed externally')
    def test_wrong_preimage_never_restored(self):
        path=self.root/'INDEX.json';path.write_bytes(b'after')
        publish(self.receipt/'preimages'/'INDEX.json',b'corrupt')
        op=dict(kind='replace',path='INDEX.json',before_sha256=sha(b'before'),after_sha256=sha(b'after'))
        self.assertFalse(rollback(self.root,self.receipt,[op])['complete'])
        self.assertEqual(path.read_bytes(),b'after')
    def test_missing_owned_addition_is_not_a_failure(self):
        op=self.addition()
        self.assertTrue(rollback(self.root,self.receipt,[op])['complete'])
    def test_raw_evidence_not_a_rollback_target(self):
        raw=self.root/'HCR-Evidence'/'raw.json';publish(raw,b'first failure')
        op=self.addition();apply_operations(self.root,self.payload,self.receipt,[op],b'')
        result=rollback(self.root,self.receipt,[op])
        self.assertFalse(result['raw_evidence_deleted']);self.assertEqual(raw.read_bytes(),b'first failure')

if __name__=='__main__':unittest.main()
