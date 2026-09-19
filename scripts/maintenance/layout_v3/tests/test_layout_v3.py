from __future__ import annotations
import ast
import copy
from contextlib import redirect_stdout, redirect_stderr
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from fixtures import PKG, UPSTREAM, fixture_preflight, put, repository
import audit
import fsops
import layout
import main


def module(path):
    spec = importlib.util.spec_from_file_location('loaded_'+path.stem.replace('-','_'),path)
    obj = importlib.util.module_from_spec(spec); spec.loader.exec_module(obj); return obj


def freeze(root, package):
    stage=root/'HCR-Evidence/repository-layout/layout-v3-test'
    stage.mkdir(parents=True,exist_ok=False)
    plan=main.freeze(root,package,stage,fixture_preflight(root,package))
    return stage,plan,fsops.Transaction(root,stage,plan)


def result(ids=('test.a','test.b'), skipped=()):
    return {'tests_run':len(ids),'collected_ids':list(ids),'failures':0,'errors':0,
            'expected_failures':0,'unexpected_successes':0,
            'skipped':[{'test':k,'reason':v} for k,v in skipped],
            'outcomes':{k:'skip' if k in dict(skipped) else 'pass' for k in ids}}

class VerifiedSources(unittest.TestCase):
    def test_git_blob_identity_of_six_launchers(self):
        for name in layout.LEGACY:
            b=(UPSTREAM/name).read_bytes()
            self.assertEqual(hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest(),layout.PINS[name])

    def test_current_real_index_git_blob_identity(self):
        b=(UPSTREAM/'INDEX.json').read_bytes()
        self.assertEqual(hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest(),'1e2208b837969a7b32b9a5fa3f138296d9cfe5ad')

    def test_real_launchers_commands_keep_repository_root(self):
        with tempfile.TemporaryDirectory() as d:
            root,package=repository(Path(d))
            for name in ('Run-HCR-R031.py','Run-HCR-R032.py','Run-HCR-R033.py'):
                new=put(root,'scripts/legacy/'+name,layout.relocate_launcher(name,(root/name).read_bytes()))
                a,b=module(root/name),module(new)
                self.assertEqual(a.commands(None),b.commands(None))
                self.assertEqual(a.commands(Path('new-output')),b.commands(Path('new-output')))
                self.assertEqual(b.commands(None)[-1][-1],str(root))

    def test_real_launchers_checkonly_keeps_cwd(self):
        with tempfile.TemporaryDirectory() as d:
            root,package=repository(Path(d))
            for name in ('Run-HCR-R031.py','Run-HCR-R032.py','Run-HCR-R033.py'):
                p=put(root,'scripts/legacy/'+name,layout.relocate_launcher(name,(root/name).read_bytes()))
                obj=module(p)
                with patch.object(obj.subprocess,'run') as called, redirect_stdout(io.StringIO()):
                    self.assertEqual(obj.main(['--check-only']),0)
                self.assertTrue(called.call_count>0)
                self.assertTrue(all(c.kwargs['cwd']==root for c in called.call_args_list))
                self.assertFalse(any('demo' in c.args[0] for c in called.call_args_list))

    def test_real_launcher_help_in_fresh_process(self):
        with tempfile.TemporaryDirectory() as d:
            root,package=repository(Path(d))
            for name in ('Run-HCR-R031.py','Run-HCR-R032.py','Run-HCR-R033.py'):
                p=put(root,'scripts/legacy/'+name,layout.relocate_launcher(name,(root/name).read_bytes()))
                r=subprocess.run([sys.executable,'-X','utf8','-B',str(p),'--help'],cwd=root,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
                self.assertEqual(r.returncode,0,r.stderr.decode()); self.assertIn(b'--check-only',r.stdout)

    def test_powershell_bom_and_crlf_not_normalized_by_relocation(self):
        for name in ('Run-HCR-R02.ps1','Run-HCR-R021.ps1','Run-HCR-R03.ps1'):
            before=(UPSTREAM/name).read_bytes().replace(b'\n',b'\r\n')
            after=layout.relocate_launcher(name,before)
            self.assertEqual(before.count(b'\r\n'),after.count(b'\r\n'))
            self.assertEqual(before.startswith(b'\xef\xbb\xbf'),after.startswith(b'\xef\xbb\xbf'))
            self.assertIn(b'Split-Path -Parent (Split-Path -Parent $PSScriptRoot)',after)

    def test_unknown_bootstrap_is_refused(self):
        with self.assertRaises(fsops.LayoutError):layout.relocate_launcher('Run-HCR-R031.py',b'print(1)\n')

    def test_multiple_test_references_are_refused(self):
        with self.assertRaises(fsops.LayoutError):layout.relocate_test('Run-HCR-R031.py',b'# Run-HCR-R031.py Run-HCR-R031.py')

class CatalogAndDispatcher(unittest.TestCase):
    def build(self,root):
        idx=layout.catalog(root); put(root,'experiments/INDEX.json',fsops.encode(idx))
        for old,new in layout.move_map().items():
            put(root,new,layout.relocate_launcher(old,(root/old).read_bytes()))
        return idx

    def test_all_31_catalog_identities_are_preserved(self):
        with tempfile.TemporaryDirectory() as d:
            root,p=repository(Path(d));old=json.loads((root/'experiments/INDEX.json').read_bytes());new=layout.catalog(root)
            self.assertEqual([r['experiment_id'] for r in old['experiments']],[r['experiment_id'] for r in new['experiments']])
            self.assertEqual(len(new['experiments']),31)

    def test_28_archived_paths_are_repaired(self):
        with tempfile.TemporaryDirectory() as d:
            root,p=repository(Path(d));idx=layout.catalog(root)
            n=sum(str(row.get(k) or '').startswith('archive/releases/') for row in idx['experiments'] for k in ('release_manifest','legacy_python_entrypoint'))
            self.assertEqual(n,28)

    def test_default_r049_unchanged(self):
        with tempfile.TemporaryDirectory() as d:
            root,p=repository(Path(d));idx=self.build(root);driver=module(PKG/'payload/run_indexed_experiment.py')
            with patch.object(driver.subprocess,'call',return_value=7) as call:
                self.assertEqual(driver.main([],root=root),7)
            self.assertEqual(call.call_args.args[0], [sys.executable,'-X','utf8','-B',str(root/'Run-HCR-R049.py')])
            self.assertEqual(call.call_args.kwargs['cwd'],root)

    def test_exp29_dispatch_preserves_current_r048(self):
        with tempfile.TemporaryDirectory() as d:
            root,p=repository(Path(d));self.build(root);driver=module(PKG/'payload/run_indexed_experiment.py')
            with patch.object(driver.subprocess,'call',return_value=0) as call:
                self.assertEqual(driver.main(['--experiment','EXP-29'],root=root),0)
            self.assertTrue(call.call_args.args[0][-1].endswith('Run-HCR-R048.py'))

    def test_historical_dispatch_never_runs(self):
        with tempfile.TemporaryDirectory() as d:
            root,p=repository(Path(d));self.build(root);driver=module(PKG/'payload/run_indexed_experiment.py')
            for exp in ('EXP-12','EXP-15','EXP-28'):
                with patch.object(driver.subprocess,'call') as call, redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
                    driver.main(['--experiment',exp],root=root)
                self.assertEqual(caught.exception.code,2);call.assert_not_called()

    def test_list_and_describe_and_check_do_not_run_study(self):
        with tempfile.TemporaryDirectory() as d:
            root,p=repository(Path(d));self.build(root);driver=module(PKG/'payload/run_indexed_experiment.py')
            for args in (['--list'],['--describe','EXP-15'],['--check-index']):
                with patch.object(driver.subprocess,'call') as call,redirect_stdout(io.StringIO()):
                    self.assertEqual(driver.main(args,root=root),0)
                call.assert_not_called()

    def test_research_metadata_not_promoted(self):
        with tempfile.TemporaryDirectory() as d:
            root,p=repository(Path(d));old=json.loads((root/'experiments/INDEX.json').read_bytes());idx=layout.catalog(root)
            for a,b in zip(old['experiments'],idx['experiments']):
                for key in ('source_commit','run_status','source_commit_note','design','frozen_design'):
                    self.assertEqual(a[key],b[key])

    def test_path_traversal_rejected(self):
        driver=module(PKG/'payload/run_indexed_experiment.py')
        for s in ('../x','/tmp/x','C:/x','a\\b','a/../b','a//b','.git/config'):
            with self.assertRaises(ValueError):driver.local_path(Path('/tmp'),s)

    def test_injected_dispatch_target_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root,p=repository(Path(d));idx=self.build(root)
            row=next(r for r in idx['experiments'] if r['experiment_id']=='EXP-30');row['current_python_entrypoint']='scripts/legacy/Run-HCR-R031.py'
            put(root,'experiments/INDEX.json',fsops.encode(idx))
            with self.assertRaises(ValueError):module(PKG/'payload/run_indexed_experiment.py').read_index(root)

class TransactionChecks(unittest.TestCase):
    def test_apply_and_independent_inventory_audit(self):
        with tempfile.TemporaryDirectory() as d:
            root,p=repository(Path(d));stage,plan,tx=freeze(root,p);tx.apply();r=audit.evaluate(root,stage)
            self.assertTrue(r['verified']);self.assertEqual(r['transformations']['checked'],6)
            self.assertEqual(r['catalog']['resolved_paths'],sum(row.get(k) is not None for row in layout.catalog(root)['experiments'] for k in ('directory','design','frozen_design','evidence_directory','implementation_validation_directory','legacy_python_entrypoint','release_manifest','current_python_entrypoint')))

    def test_originals_and_engine_evidence_bytes_preserved(self):
        with tempfile.TemporaryDirectory() as d:
            root,p=repository(Path(d));before={n:(root/n).read_bytes() for n in layout.LEGACY};raw=(root/'HCR-Evidence/old-raw/query.bin').read_bytes()
            stage,plan,tx=freeze(root,p);tx.apply()
            for n,b in before.items():self.assertEqual((root/layout.ORIGINALS/n).read_bytes(),b)
            self.assertEqual((root/'HCR-Evidence/old-raw/query.bin').read_bytes(),raw)

    def test_rollback_after_partial_publication(self):
        for number in (0,8,25):
            with self.subTest(after_operation=number),tempfile.TemporaryDirectory() as d:
                root,p=repository(Path(d));stage,plan,tx=freeze(root,p)
                original=tx.change
                calls=[]
                def failing(op,after,prefix):
                    original(op,after,prefix);calls.append(op['path'])
                    if len(calls)==number+1:raise OSError('injected after durable publication')
                with patch.object(tx,'change',side_effect=failing),self.assertRaises(OSError):tx.apply()
                self.assertTrue(tx.recover()['complete']);self.assertTrue(audit.evaluate(root,stage,rolled_back=True)['verified'])

    def test_all_applied_operations_rollback(self):
        with tempfile.TemporaryDirectory() as d:
            root,p=repository(Path(d));stage,plan,tx=freeze(root,p);tx.apply();self.assertTrue(tx.recover()['complete']);audit.evaluate(root,stage,rolled_back=True)

    def test_external_modified_output_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as d:
            root,p=repository(Path(d));stage,plan,tx=freeze(root,p);tx.apply();put(root,'README.md',b'external edit')
            report=tx.recover();self.assertFalse(report['complete']);self.assertEqual((root/'README.md').read_bytes(),b'external edit')

    def test_external_unplanned_file_is_detected_but_not_deleted(self):
        with tempfile.TemporaryDirectory() as d:
            root,p=repository(Path(d));stage,plan,tx=freeze(root,p);tx.apply();put(root,'user-notes.txt',b'owned by user')
            with self.assertRaises(ValueError):audit.evaluate(root,stage)
            tx.recover();self.assertEqual((root/'user-notes.txt').read_bytes(),b'owned by user')

    def test_changed_source_before_first_write_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            root,p=repository(Path(d));stage,plan,tx=freeze(root,p)
            # Choose an existing target; simulated editor update must never be replaced.
            op=next(x for x in plan['operations'] if x['path']=='README.md');put(root,'README.md',b'new editor bytes')
            with self.assertRaises(fsops.LayoutError):tx.change(op,True,'apply')
            self.assertEqual((root/'README.md').read_bytes(),b'new editor bytes')

    def test_mutated_frozen_plan_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root,p=repository(Path(d));stage,plan,tx=freeze(root,p);tx.apply();(stage/'plan.json').write_bytes(b'{}')
            with self.assertRaises(ValueError):audit.evaluate(root,stage)

    def test_mutated_assertion_is_detected(self):
        with tempfile.TemporaryDirectory() as d:
            root,p=repository(Path(d));stage,plan,tx=freeze(root,p);tx.apply()
            test=root/'tests/test_r031_prior_scope.py';test.write_bytes(test.read_bytes().replace(b'call.assert_not_called()',b'pass'))
            with self.assertRaises(ValueError):audit.transform_checks(root,plan,stage)

    def test_case_collision_refused(self):
        with self.assertRaises(fsops.LayoutError):
            fsops.ensure_case_unique(['README.md','ReadMe.md'])

    def test_evidence_cache_named_directory_is_not_excluded(self):
        with tempfile.TemporaryDirectory() as d:
            root,p=repository(Path(d));put(root,'HCR-Evidence/old-raw/__pycache__/raw.bin',b'raw')
            snap=fsops.snapshot(root,p.relative_to(root).as_posix(),'none')
            self.assertIn('HCR-Evidence/old-raw/__pycache__/raw.bin',snap)

    def test_symlink_target_path_is_refused_without_creation_in_production(self):
        with tempfile.TemporaryDirectory() as d:
            root,p=repository(Path(d))
            if os.name == 'nt':
                with patch.object(Path,'is_symlink',lambda q: q == root/'linked'):
                    with self.assertRaises(fsops.LayoutError):fsops.safe(root,'linked')
                    with self.assertRaises(ValueError):audit.confined(root,'linked')
            else:
                (root/'linked').symlink_to(root/'README.md')
                with self.assertRaises(fsops.LayoutError):fsops.safe(root,'linked')
                with self.assertRaises(ValueError):audit.confined(root,'linked')

class RegressionAcceptance(unittest.TestCase):
    baseline={'tests_run':2,'skipped':[{'test':'test.b','reason':'existing environment'}]}
    def test_identical_skip_is_unmeasured_not_pass(self):
        r=main.accept(self.baseline,result(skipped=(('test.b','existing environment'),)),0)
        self.assertEqual(r['passed'],1);self.assertEqual(len(r['unchanged_environment_skips']),1)
    def test_skip_resolved_by_real_pass_is_accepted(self):
        r=main.accept(self.baseline,result(),0);self.assertEqual(r['previous_skips_now_passed'],['test.b'])
    def test_new_skip_refused(self):
        with self.assertRaises(fsops.LayoutError):main.accept(self.baseline,result(skipped=(('test.a','new'),)),0)
    def test_changed_skip_reason_refused(self):
        with self.assertRaises(fsops.LayoutError):main.accept(self.baseline,result(skipped=(('test.b','new reason'),)),0)
    def test_disappeared_skip_without_pass_refused(self):
        r=result();r['outcomes'].pop('test.b')
        with self.assertRaises(fsops.LayoutError):main.accept(self.baseline,r,0)
    def test_error_failure_expectedfailure_and_exitcode_refused(self):
        for key in ('errors','failures','expected_failures','unexpected_successes'):
            r=result();r[key]=1
            with self.assertRaises(fsops.LayoutError):main.accept(self.baseline,r,0)
        with self.assertRaises(fsops.LayoutError):main.accept(self.baseline,result(),2)
    def test_missing_or_duplicate_collection_refused(self):
        for ids in (('test.a',),('test.a','test.a')):
            with self.assertRaises(fsops.LayoutError):main.accept(self.baseline,result(ids=ids),0)

class Orchestration(unittest.TestCase):
    def test_production_preflight_refuses_other_head(self):
        with tempfile.TemporaryDirectory() as d:
            root,p=repository(Path(d))
            with self.assertRaisesRegex(fsops.LayoutError,'pinned to'):main.preflight(root,p)

    def test_real_six_upstream_assertions_final_once_after_audit(self):
        # This is a REAL subprocess running ONLY the six extracted upstream tests.
        # The tiny hcr import stub is not an HCC implementation and no 602-test claim is made.
        with tempfile.TemporaryDirectory() as d:
            root,p=repository(Path(d));events=[];actual_reg=main.final_regression;actual_audit=audit.evaluate
            def reg(*args):events.append('core');return actual_reg(*args)
            def aud(*args,**kw):events.append('audit');return actual_audit(*args,**kw)
            with patch.object(main,'preflight',side_effect=fixture_preflight),patch.object(main,'final_regression',side_effect=reg),patch.object(audit,'evaluate',side_effect=aud),redirect_stdout(io.StringIO()):
                rc=main.apply(root,p)
            self.assertEqual(rc,0);self.assertEqual(events,['audit','core','audit'])
            stage=main.find_success(root);r=json.loads((stage/'regression.json').read_bytes())
            self.assertEqual(r['tests_run'],6);self.assertEqual(r['failures'],0);self.assertEqual(r['errors'],0)
            self.assertTrue(all(x=='pass' for x in r['outcomes'].values()))
            # Idempotent re-entry must not run a project test.
            with patch.object(main,'final_regression',side_effect=AssertionError('duplicate regression')),redirect_stdout(io.StringIO()):
                self.assertEqual(main.apply(root,p),0)

    def test_failed_final_regression_restores_files(self):
        with tempfile.TemporaryDirectory() as d:
            root,p=repository(Path(d));bad=result(ids=tuple(str(i) for i in range(6)));bad['errors']=1
            with patch.object(main,'preflight',side_effect=fixture_preflight),patch.object(main,'final_regression',return_value=(2,bad)),redirect_stdout(io.StringIO()),redirect_stderr(io.StringIO()):
                rc=main.apply(root,p)
            self.assertEqual(rc,2);self.assertFalse((root/layout.STATE).exists())
            for n in layout.LEGACY:self.assertTrue((root/n).is_file())
            stage=next((root/main.ROOT_EVIDENCE).glob('layout-v3-*'))
            self.assertTrue(json.loads((stage/'rollback.json').read_bytes())['complete'])

    def test_recovery_refuses_a_live_process(self):
        with tempfile.TemporaryDirectory() as d:
            root,p=repository(Path(d));put(root,main.LOCK,fsops.encode({'stage':'anywhere','pid':os.getpid()}))
            with self.assertRaisesRegex(fsops.LayoutError,'still running'):main.recover(root)

    def test_pending_transaction_blocks_reentry(self):
        with tempfile.TemporaryDirectory() as d:
            root,p=repository(Path(d));put(root,main.LOCK,b'{}')
            with self.assertRaises(fsops.LayoutError):main.apply(root,p)

    def test_explicit_recovery_of_partially_applied_transaction(self):
        with tempfile.TemporaryDirectory() as d:
            root,p=repository(Path(d));stage,plan,tx=freeze(root,p)
            for op in plan['operations'][:10]:tx.change(op,True,'apply')
            put(root,main.LOCK,fsops.encode({'stage':stage.relative_to(root).as_posix()}))
            with redirect_stdout(io.StringIO()):self.assertEqual(main.recover(root),0)
            self.assertFalse((root/main.LOCK).exists());audit.evaluate(root,stage,rolled_back=True)

    def test_fault_after_success_marker_but_before_seal_does_not_claim_success(self):
        with tempfile.TemporaryDirectory() as d:
            root,p=repository(Path(d));ok=result(ids=tuple(str(i) for i in range(6)))
            with patch.object(main,'preflight',side_effect=fixture_preflight),patch.object(main,'final_regression',return_value=(0,ok)),patch.object(main,'seal',side_effect=OSError('injected seal failure')),redirect_stdout(io.StringIO()),redirect_stderr(io.StringIO()):
                self.assertEqual(main.apply(root,p),2)
            self.assertIsNone(main.find_success(root));stage=next((root/main.ROOT_EVIDENCE).glob('layout-v3-*'))
            self.assertIn('FAILED',(stage/'summary.ko.md').read_text());self.assertTrue((stage/'provisional-success.json').exists())

if __name__=='__main__':unittest.main(verbosity=2)
