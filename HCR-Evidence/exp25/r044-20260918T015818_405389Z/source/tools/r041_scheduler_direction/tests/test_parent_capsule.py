"""EXP21 capsule 배치·기존 72개 trial binding 검사. 이전 native 재생만 명시적 stub이다."""
from copy import deepcopy
from contextlib import ExitStack
import unittest
from unittest.mock import patch
from r037_online_selection import io
from r039_order_isolation.tests._fixtures import parent,cases
from r040_frontier_schedule import protocol as parent_protocol, spec as parent_spec
from r041_scheduler_direction import sources
from r041_scheduler_direction.contracts import digest,PARENT_RAW_SHA256


class ParentCapsuleTests(unittest.TestCase):
    def setUp(self):
        self.cases=cases();self.base=parent();self.core={'memory':{},'config':{}}
        self.docs={n:{'synthetic_parent_capsule':n} for n in sources.PARENT_FILES}
        self.hashes={n:digest(v) for n,v in self.docs.items()}
        self.hashes['manifest.json']=PARENT_RAW_SHA256
        self.oldhashes={n:self.hashes[n if n.startswith('upstream/') else 'basis/exp20/'+n]
                       for n in sources.previous.PARENT_FILES}
        self.docs['plan.json']=dict(cases=sources.spec.public_cases(self.cases),
            evaluation_worlds={c['name']:c['worlds'] for c in self.cases},
            canonical_parent_case=self.base,trials=parent_spec.trials(self.cases),
            parent_file_hashes=self.oldhashes,memory_sha256=digest({}),config_sha256=digest({}))
        for t in self.docs['plan.json']['trials']:
            self.docs['raw/'+t['id']+'.json']=dict(schema='hcr-exp21-raw-trial-v1',trial=t)
        self.docs['manifest.json']=dict(schema='hcr-exp21-raw-manifest-v1',state='raw_complete',files=dict(self.hashes))
        self.docs['analysis/manifest.json']=dict(schema='hcr-exp21-analysis-manifest-v1',raw_manifest_sha256=PARENT_RAW_SHA256,
            files={'audit.json':self.hashes['analysis/audit.json']})
        self.docs['analysis/audit.json']=dict(verified=True,native_trials=72,fixed_identity_input_isolation_checked=True,
                                           raw_manifest_sha256=PARENT_RAW_SHA256)
    def check(self):
        with patch.object(parent_protocol,'validate_plan'),patch.object(sources.previous,'validate_parent_documents',
                    return_value=(self.cases,self.core,self.base)):
            return sources.validate_parent_documents(self.docs,self.hashes)
    def test_parent_population_and_distinct_capsule_paths(self):
        self.assertEqual(len(sources.PARENT_RAW_FILES),72)
        self.assertEqual(len(set(sources.capsule_name(n) for n in sources.PARENT_FILES)),len(sources.PARENT_FILES))
    def test_nested_capsule_path_matches_R040_storage(self):
        for n in sources.previous.PARENT_FILES:
            expected=n if n.startswith('upstream/') else 'basis/exp20/'+n
            self.assertIn(expected,sources.PARENT_FILES)
    def test_seed_keeps_top_level_upstream_path(self):
        self.assertEqual(sources.capsule_name('upstream/seed/6.json'),'upstream/seed/6.json')
    def test_native_selftest_old_case_path_exists_in_capsule_inventory(self):
        self.assertIn('basis/exp20/basis/exp19/plan.json',sources.PARENT_FILES)
    def test_valid_parent_binding(self):
        result=self.check();self.assertEqual(result,(self.cases,self.core,self.base))
        self.assertIsNot(result[0],self.cases)
    def test_wrong_pinned_manifest_rejected(self):
        self.hashes['manifest.json']='0'*64
        with self.assertRaises(ValueError):self.check()
    def test_truncated_parent_inventory_rejected(self):
        self.docs.pop('raw/t0071.json')
        with self.assertRaises(ValueError):self.check()
    def test_raw_trial_binding_rejected(self):
        self.docs['raw/t0071.json']['trial']={'id':'wrong'}
        with self.assertRaises(ValueError):self.check()
    def test_incomplete_parent_not_success(self):
        self.docs['manifest.json']['state']='failed'
        with self.assertRaises(ValueError):self.check()
    def test_wrong_world_mapping_rejected(self):
        self.docs['plan.json']['evaluation_worlds']['order_SMD']['missing_closed']['e0']=False
        with self.assertRaises(ValueError):self.check()
    def test_capsule_hash_tampering_rejected(self):
        self.hashes['raw/t0000.json']='a'*64
        with self.assertRaises(ValueError):self.check()
