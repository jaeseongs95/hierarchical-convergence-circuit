"""Known-predecessor patch and rollback on temporary files only."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from tools.r050_review_boundary.common import IntegrityError,sha
from tools.r050_review_boundary import maintenance as m


class Upgrade(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.base=Path(self.tmp.name)
        self.repo=self.base/'repo';self.payload=self.base/'payload';self.receipt=self.base/'receipt'
        for p in (self.repo,self.payload,self.receipt):p.mkdir()
        (self.repo/'engine.py').write_bytes(b'previous\r\n');(self.payload/'engine.py').write_bytes(b'new\n')
        self.known={'engine.py':sha(b'previous\n')}
    def tearDown(self):self.tmp.cleanup()
    def plan(self):return m.plan_payload_operations(self.repo,self.payload,self.receipt,self.known)
    def test_exact_predecessor_replaced_with_preimage_preserved(self):
        ops=self.plan();self.assertEqual(len(ops),1);self.assertEqual(ops[0]['source'],'payload')
        self.assertEqual((self.receipt/'preimages/engine.py').read_bytes(),b'previous\r\n')
        m.apply_operations(self.repo,self.payload,self.receipt,ops,b'')
        self.assertEqual((self.repo/'engine.py').read_bytes(),b'new\n')
    def test_rollback_restores_exact_original_crlf(self):
        ops=self.plan();m.apply_operations(self.repo,self.payload,self.receipt,ops,b'')
        self.assertTrue(m.rollback(self.repo,self.receipt,ops)['complete'])
        self.assertEqual((self.repo/'engine.py').read_bytes(),b'previous\r\n')
    def test_external_changes_not_replaced(self):
        (self.repo/'engine.py').write_bytes(b'user edit')
        with self.assertRaisesRegex(IntegrityError,'neither'):self.plan()
        self.assertEqual((self.repo/'engine.py').read_bytes(),b'user edit')
    def test_exact_new_version_is_idempotent(self):
        (self.repo/'engine.py').write_bytes(b'new\r\n');self.assertEqual(self.plan(),[])
    def test_missing_target_added(self):
        (self.repo/'engine.py').unlink();ops=self.plan();self.assertEqual(ops[0]['kind'],'add')
    def test_plan_does_not_authorize_later_external_edit(self):
        ops=self.plan();(self.repo/'engine.py').write_bytes(b'concurrent edit')
        with self.assertRaisesRegex(IntegrityError,'Concurrent'):m.apply_operations(self.repo,self.payload,self.receipt,ops,b'')
    def test_changed_payload_after_plan_rejected(self):
        ops=self.plan();(self.payload/'engine.py').write_bytes(b'changed')
        with self.assertRaisesRegex(IntegrityError,'plan hash'):m.apply_operations(self.repo,self.payload,self.receipt,ops,b'')
    def test_ownership_survives_journal_failure(self):
        ops=self.plan();owned=[]
        with patch.object(m,'dump',side_effect=OSError('journal fixture failure')):
            with self.assertRaises(OSError):m.apply_operations(self.repo,self.payload,self.receipt,ops,b'',applied=owned)
        self.assertEqual(owned,ops);self.assertTrue(m.rollback(self.repo,self.receipt,owned)['complete'])
    def test_external_postimage_preserved_on_rollback(self):
        ops=self.plan();m.apply_operations(self.repo,self.payload,self.receipt,ops,b'')
        (self.repo/'engine.py').write_bytes(b'new user edit');result=m.rollback(self.repo,self.receipt,ops)
        self.assertFalse(result['complete']);self.assertEqual((self.repo/'engine.py').read_bytes(),b'new user edit')

if __name__=='__main__':unittest.main()
