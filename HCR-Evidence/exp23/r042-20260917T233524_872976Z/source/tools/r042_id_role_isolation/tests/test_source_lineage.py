"""가상 capsule로 신규 계보 검산을 검사한다. 실제 EXP22 raw 재검산을 대신하지 않는다."""
from copy import deepcopy
import sys
import types
import unittest
from unittest.mock import patch,Mock
from r042_id_role_isolation import sources,storage as io
from r042_id_role_isolation.tests.fixtures import parent_fixture


def capsule_fixture():
    parent,seed=parent_fixture()
    for case in parent['cases']:
        for scope in ('legacy','route_only'):
            for arm in ('native','posthoc_support','online_support'):
                for scheduler in ('input_order','edge_id_min','edge_id_max'):
                    parent['trials'].append(dict(id=f"t{len(parent['trials']):04d}",case=case['name'],
                                                scope=scope,arm=arm,scheduler=scheduler))
    packet={'document':{'engine':seed}};packet['sha256']=io.digest(packet['document'])
    docs={'plan.json':parent,'upstream/plan.json':{'fixture':True},
          'upstream/seed/6.json':packet,'upstream/training.json':[]}
    for trial in sources.parent_regression_trials(parent):
        docs['raw/'+trial['id']+'.json']={'schema':'hcr-exp22-raw-trial-v1','trial':trial,'run':{'fixture_only':True}}
    hashes={name:io.digest(doc) for name,doc in docs.items()}
    manifest={'schema':'hcr-exp22-raw-manifest-v1','state':'raw_complete','files':deepcopy(hashes)}
    pin=io.digest(manifest);docs['manifest.json']=manifest;hashes['manifest.json']=pin
    audit={'schema':'hcr-exp22-audit-v1','verified':True,'native_trials':108,'raw_manifest_sha256':pin}
    docs['analysis/audit.json']=audit;hashes['analysis/audit.json']=io.digest(audit)
    analysis={'schema':'hcr-exp22-analysis-manifest-v1','raw_manifest_sha256':pin,
              'files':{'audit.json':hashes['analysis/audit.json']}}
    docs['analysis/manifest.json']=analysis;hashes['analysis/manifest.json']=io.digest(analysis)
    return docs,hashes,pin


class SourceTests(unittest.TestCase):
    def setUp(self):
        self.docs,self.hashes,self.pin=capsule_fixture()
        package=types.ModuleType('r041_scheduler_direction');package.__path__=[]
        protocol=types.ModuleType('r041_scheduler_direction.protocol')
        self.oldcheck=Mock();protocol.validate_plan=self.oldcheck
        self.modules=patch.dict(sys.modules,{'r041_scheduler_direction':package,
                                            'r041_scheduler_direction.protocol':protocol})
        self.modules.start();self.pinpatch=patch.object(sources,'PARENT_RAW_SHA256',self.pin);self.pinpatch.start()
        self.addCleanup(self.modules.stop);self.addCleanup(self.pinpatch.stop)

    def check(self): return sources.validate_parent_documents(self.docs,self.hashes)

    def test_minimal_capsule_has_exactly_12_parent_raw(self):
        self.check()
        self.assertEqual(sum(name.startswith('raw/') for name in self.docs),12)
        self.oldcheck.assert_called_once_with(self.docs['plan.json'],check_parent=False)

    def test_parent_manifest_pin_mismatch(self):
        self.hashes['manifest.json']='wrong'
        with self.assertRaises(io.ContractError): self.check()

    def test_parent_file_checksum_mismatch(self):
        name=next(n for n in self.docs if n.startswith('raw/'));self.hashes[name]='wrong'
        with self.assertRaises(io.ContractError): self.check()

    def test_analysis_link_wrong(self):
        self.docs['analysis/manifest.json']['raw_manifest_sha256']='wrong'
        with self.assertRaises(io.ContractError): self.check()

    def test_seed_seal_wrong(self):
        self.docs['upstream/seed/6.json']['sha256']='wrong'
        with self.assertRaises(io.ContractError): self.check()

    def test_seed_configuration_changed(self):
        packet=self.docs['upstream/seed/6.json'];packet['document']['engine']['config']['x']=1
        packet['sha256']=io.digest(packet['document'])
        with self.assertRaises(io.ContractError): self.check()

    def test_extra_raw_rejected(self):
        self.docs['raw/extra.json']={};self.hashes['raw/extra.json']='extra'
        with self.assertRaises(io.ContractError): self.check()

    def test_raw_trial_binding_rejected(self):
        name=next(n for n in self.docs if n.startswith('raw/'))
        self.docs[name]['trial']=dict(self.docs[name]['trial'],scheduler='input_order')
        with self.assertRaises(io.ContractError): self.check()

    def test_regression_group_missing(self):
        self.docs['plan.json']['trials'].pop()
        with self.assertRaises(io.ContractError): self.check()

    def test_duplicate_parent_cell(self):
        plan=self.docs['plan.json'];selected=sources.parent_regression_trials(plan)
        a,b=selected[:2];a.update({k:v for k,v in b.items() if k!='id'})
        with self.assertRaises(io.ContractError): self.check()

if __name__=='__main__': unittest.main()
