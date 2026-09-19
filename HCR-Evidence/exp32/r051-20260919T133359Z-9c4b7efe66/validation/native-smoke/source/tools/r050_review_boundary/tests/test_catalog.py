"""Mock Git catalog fixtures. No connected repository is changed."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock
from types import SimpleNamespace
from tools.r050_review_boundary import maintenance
from tools.r050_review_boundary.common import IntegrityError,text_blob

class CatalogTransactions(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        (self.root/'experiments').mkdir()
        self.base=dict(default_experiment='EXP-30',experiments=[dict(experiment_id='EXP-30')])
        self.raw=json.dumps(self.base).encode();(self.root/'experiments'/'INDEX.json').write_bytes(self.raw)
        self.entry=dict(experiment_id='EXP-31',current_python_entrypoint=None,execution_status='standalone_candidate_contract')
    def tearDown(self):self.tmp.cleanup()
    def call(self):
        with mock.patch.object(maintenance,'INDEX_BLOB',text_blob(self.raw)),mock.patch.object(maintenance.subprocess,'run',return_value=SimpleNamespace(returncode=0,stdout=self.raw)):
            return maintenance.index_change(self.root,self.entry)
    def test_append_preserves_default_and_existing_entry(self):
        before,after=self.call();new=json.loads(after)
        self.assertEqual(before,self.raw);self.assertEqual(new['default_experiment'],'EXP-30')
        self.assertEqual(new['experiments'],self.base['experiments']+[self.entry])
    def test_existing_exact_install_is_idempotent(self):
        _,after=self.call();(self.root/'experiments'/'INDEX.json').write_bytes(after)
        self.assertEqual(self.call(),(after,after))
    def test_external_catalog_change_is_not_overwritten(self):
        changed=deepcopy(self.base);changed['notes']='user edit'
        raw=json.dumps(changed).encode();(self.root/'experiments'/'INDEX.json').write_bytes(raw)
        with self.assertRaises(IntegrityError):self.call()
        self.assertEqual((self.root/'experiments'/'INDEX.json').read_bytes(),raw)
    def test_exp31_collision_rejected(self):
        changed=deepcopy(self.base);changed['experiments'].append(dict(experiment_id='EXP-31',external=True))
        (self.root/'experiments'/'INDEX.json').write_text(json.dumps(changed))
        with self.assertRaises(IntegrityError):self.call()

if __name__=='__main__':unittest.main()
