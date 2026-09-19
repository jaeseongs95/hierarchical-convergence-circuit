"""Pure protocol and tamper tests. All constructed candidates are synthetic fixtures."""
from __future__ import annotations
import ast
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock
from tools.r050_review_boundary import audit, protocol
from tools.r050_review_boundary.common import (IntegrityError, canonical, dump, fingerprint,
             git_blob, git_tree, load, publish, relative, safe, seal, sha, unseal)

ROOT=Path(__file__).resolve().parents[3]
SPEC=json.loads((ROOT/'experiments'/'exp-31-review-boundary'/'frozen_spec.json').read_text(encoding='utf-8'))

def fixture(conflicts=(),paths=((0,1),),accepted=False,value=False):
    return dict(candidate_id='synthetic-candidate',decision=dict(value=value,expanded_paths=[list(x) for x in paths]),
                diagnostic=dict(suggestion=dict(sign_conflict_edges=list(conflicts))),
                readout=dict(accepted=accepted,value=value if accepted else None))

class MatrixAndInterventions(unittest.TestCase):
    def plan(self):
        return dict(contract=SPEC['contract'],cases=deepcopy(SPEC['cases']),arms=SPEC['arms'],limits=SPEC['limits'],config=SPEC['config'])
    def test_full_matrix_is_frozen(self):
        audit.validate_matrix(self.plan(),SPEC)
        self.assertEqual(len(SPEC['cases'])*len(SPEC['arms']),96)
    def test_missing_case_rejected(self):
        p=self.plan();p['cases'].pop()
        with self.assertRaises(IntegrityError):audit.validate_matrix(p,SPEC)
    def test_duplicate_case_rejected(self):
        p=self.plan();p['cases'][1]=deepcopy(p['cases'][0])
        with self.assertRaises(IntegrityError):audit.validate_matrix(p,SPEC)
    def test_budget_change_rejected(self):
        p=self.plan();p['limits']=dict(p['limits'],max_restarts_per_arm=2)
        with self.assertRaises(IntegrityError):audit.validate_matrix(p,SPEC)
    def test_default_kernel_not_tuned(self):
        self.assertEqual(SPEC['config']['kernel']['top_down_gain'],.35)
        self.assertEqual(SPEC['config']['kernel']['relation_gain'],2.)
        self.assertFalse(SPEC['boundaries']['changes_to_kernel'])
    def test_all_weak_cases_have_independent_target_agreement(self):
        for c in SPEC['cases']:
            for conflicts in ((),(c['observation']['edges'][1]['id'],)):
                f=fixture(conflicts)
                self.assertEqual(protocol.select_probe(c['observation'],f),audit.independent_target(c['observation'],f))
    def test_id_tie_break_uses_observation_slot(self):
        obs=SPEC['cases'][2]['observation']
        self.assertEqual(obs['edges'][0]['id'],'z-edge')
        self.assertEqual(protocol.select_probe(obs,fixture())['slot'],0)
        self.assertEqual(audit.independent_target(obs,fixture())['slot'],0)
    def test_conflict_priority_over_strength(self):
        obs=deepcopy(SPEC['cases'][0]['observation']);obs['edges'][1]['score']=.9
        f=fixture((obs['edges'][1]['id'],))
        self.assertEqual(protocol.select_probe(obs,f)['slot'],1)
        self.assertEqual(audit.independent_target(obs,f)['slot'],1)
    def test_no_unexpanded_fallback(self):
        obs=SPEC['cases'][0]['observation']
        self.assertIsNone(protocol.select_probe(obs,fixture(paths=()))['edge_id'])
    def test_no_unknown_or_zero_strength_probe(self):
        obs=deepcopy(SPEC['cases'][0]['observation'])
        for scores in ((None,0),(True,False)):
            for e,s in zip(obs['edges'],scores):e['score']=s
            self.assertIsNone(protocol.select_probe(obs,fixture())['edge_id'])
            self.assertIsNone(audit.independent_target(obs,fixture())['edge_id'])
    def test_unit_strength_is_not_remeasured(self):
        obs=SPEC['cases'][-1]['observation']
        self.assertIsNone(protocol.select_probe(obs,fixture())['edge_id'])
    def test_no_candidate_no_target(self):
        obs=SPEC['cases'][0]['observation']
        self.assertEqual(protocol.select_probe(obs,None),audit.independent_target(obs,None))
    def test_echo_only_changes_revision(self):
        for c in SPEC['cases'][:16]:
            obs=c['observation'];target=protocol.select_probe(obs,fixture())
            changed=protocol.revised_input(obs,'echo_revision_restart',target)
            self.assertEqual(changed['edges'],obs['edges'])
            self.assertEqual(changed['revision'],obs['revision']+1)
            self.assertEqual(changed,audit.independent_observation(obs,'echo_revision_restart',target))
    def test_strength_changes_only_one_score_and_revision(self):
        for c in SPEC['cases'][:16]:
            obs=c['observation'];target=protocol.select_probe(obs,fixture())
            changed=protocol.revised_input(obs,'strength_revision_restart',target)
            self.assertEqual(changed,audit.independent_observation(obs,'strength_revision_restart',target))
            self.assertEqual(sum(a!=b for a,b in zip(obs['edges'],changed['edges'])),1)
            self.assertEqual(changed['edges'][1],obs['edges'][1])
    def test_negative_probe_preserves_sign(self):
        obs=SPEC['cases'][4]['observation'];f=fixture((obs['edges'][1]['id'],))
        target=protocol.select_probe(obs,f)
        self.assertEqual(protocol.revised_input(obs,'strength_revision_restart',target)['edges'][1]['score'],-1.)
    def test_same_input_keeps_revision(self):
        obs=SPEC['cases'][0]['observation']
        self.assertEqual(protocol.revised_input(obs,'same_input_restart',{}),obs)
    def test_original_observation_and_candidate_unchanged(self):
        obs=deepcopy(SPEC['cases'][0]['observation']);f=fixture()
        initial=fingerprint([obs,f])
        t=protocol.select_probe(obs,f)
        protocol.revised_input(obs,'strength_revision_restart',t)
        self.assertEqual(fingerprint([obs,f]),initial)
    def test_forged_target_rejected(self):
        obs=SPEC['cases'][0]['observation']
        for function in (protocol.revised_input,audit.independent_observation):
            with self.assertRaises(IntegrityError):function(obs,'strength_revision_restart',dict(slot=0,edge_id='wrong'))
    def test_unknown_arm_rejected(self):
        with self.assertRaises(IntegrityError):protocol.revised_input(SPEC['cases'][0]['observation'],'automatic_retry',{})
    def test_terminal_rejection_is_not_answer(self):
        self.assertEqual(protocol.terminal(fixture()),dict(accepted=False,value=None,selected_candidate_id=None))
        self.assertEqual(audit.independent_terminal(fixture()),protocol.terminal(fixture()))
    def test_terminal_cannot_flip_original_value(self):
        f=fixture(accepted=True,value=False);f['readout']['value']=True
        with self.assertRaises(IntegrityError):audit.independent_terminal(f)
    def test_no_candidate_is_unknown_not_false(self):
        row=audit.candidate_measures(None,True)
        self.assertIsNone(row['raw_correct']);self.assertIsNone(row['D_DAG'])
        self.assertIsNone(row['internal_edge_conflicts'])
    def test_auditor_does_not_import_producer_execution(self):
        tree=ast.parse(Path(audit.__file__).read_text(encoding='utf-8'))
        modules=[n.module or '' for n in ast.walk(tree) if isinstance(n,ast.ImportFrom)]
        self.assertFalse(any(m in audit.FORBIDDEN or m in ('worker','protocol','hcr.review','hcr.runtime') for m in modules))
    def test_energy_and_state_reuse_not_claimed(self):
        self.assertFalse(SPEC['boundaries']['state_preserving_review'])
        self.assertFalse(SPEC['boundaries']['independent_sensor_data'])

class IntegrityIO(unittest.TestCase):
    def test_duplicate_json_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'x.json';p.write_text('{"a":1,"a":2}')
            with self.assertRaises(IntegrityError):load(p)
    def test_nonfinite_json_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'x.json';p.write_text('{"a":NaN}')
            with self.assertRaises(IntegrityError):load(p)
    def test_hash_tamper_rejected(self):
        p=seal(dict(schema='test',value=1));p['value']=2
        with self.assertRaises(IntegrityError):unseal(p,'test')
    def test_no_reseal(self):
        with self.assertRaises(IntegrityError):seal(seal(dict(schema='test')))
    def test_publish_is_exclusive(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'x';publish(p,b'first')
            with self.assertRaises(IntegrityError):publish(p,b'second')
            self.assertEqual(p.read_bytes(),b'first')
    def test_partial_publish_leaves_no_temp_on_success(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'x';dump(p,dict(value=1))
            self.assertEqual({x.name for x in Path(t).iterdir()},{'x'})
    def test_path_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            for name in ('../bad','a/../b','/absolute','C:/data','a\\b','a//b','.git/config','x\x00y'):
                with self.subTest(name=name),self.assertRaises(IntegrityError):relative(Path(t),name)
    def test_link_guard_without_platform_privileges(self):
        with mock.patch.object(Path,'is_symlink',return_value=True):
            with self.assertRaises(IntegrityError):safe(Path('not-a-real-link'))
    def test_git_blob_known_value(self):
        self.assertEqual(git_blob(b'hello\n'),'ce013625030ba8dba906f756967f9e9ca394464a')
    def test_git_tree_crlf_normalization(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);(p/'a.py').write_bytes(b'a\nb\n');one=git_tree(p)
            (p/'a.py').write_bytes(b'a\r\nb\r\n');self.assertEqual(git_tree(p),one)
    def test_byte_hash_does_not_hide_crlf(self):
        self.assertNotEqual(sha(b'a\n'),sha(b'a\r\n'))

if __name__=='__main__':unittest.main()
