from __future__ import annotations
import ast
from copy import deepcopy
from contextlib import redirect_stdout
import io as textio
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile
from tools.r047_state_ablation import spec, runtime, audit, storage as io, reporting, protocol, provenance, regression


class Matrix(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.a,cls.cases,cls.worlds=spec.observations();cls.sources={}
        for v,ob in cls.a.items():cls.sources[v]=runtime.run_query(ob,spec.CONFIG)
        cls.records={};cls.reports={};cls.cells={}
        cases={c['id']:c for c in cls.cases}
        for t in spec.trials():
            c=cases[t['case']];r=runtime.run_query(c['observation'],spec.CONFIG,t['arm'],cls.sources[t['source']])
            cls.records[t['id']]=r;cls.reports[t['id']]=audit.audit_record(r,cls.sources[t['source']],cls.worlds[c['id']])
            cls.cells[c['scenario'],c['variant'],t['arm']]=r
        cls.plan=dict(spec.expected_plan_body(),population='implementation_validation')

    def warm(self):return deepcopy(self.cells['extend','identity','carry_both'])
    def test_all_44_records_independent_replay(self):
        for r in self.sources.values():self.assertTrue(audit.audit_record(r)['verified'])
        self.assertEqual(len(self.records),42)
        self.assertTrue(all(a['verified'] for a in self.reports.values()))
    def test_masks_select_two_two_four(self):
        for mode in ('carry','fixed'):
            for mask,n in [('edge',2),('prefix',2),('both',4)]:
                r=self.cells['extend','identity',mode+'_'+mask]
                self.assertEqual(len(r['transfer_map']),n)
                self.assertEqual(r['bridge_cost']['matched_groups'],4)
    def test_unselected_and_new_goal_stay_neutral(self):
        for arm in spec.ARMS:
            r=self.cells['extend','identity',arm];written={m['target_group'] for m in r['transfer_map']}
            for key,val in r['initial_state'].items():
                if key not in written:self.assertEqual(val,.5)
            self.assertEqual(r['initial_state']['goal'],.5)
            self.assertEqual(r['initial_stable_steps'],0)
    def test_fixed_and_actual_share_mask_packet_guard(self):
        for mask in ('edge','prefix','both'):
            a=self.cells['extend','identity','carry_'+mask];f=self.cells['extend','identity','fixed_'+mask]
            self.assertEqual(a['carry_packet'],f['carry_packet'])
            self.assertEqual([m['target_group'] for m in a['transfer_map']],[m['target_group'] for m in f['transfer_map']])
            self.assertTrue(all(m['value']==.99 for m in f['transfer_map']))
            self.assertEqual(f['bridge_cost']['source_state_values_read'],0)
    def test_source_remains_immutable(self):
        s=deepcopy(self.sources['identity']);before=io.digest(s)
        runtime.run_query(self.cases[0]['observation'],spec.CONFIG,'carry_both',s)
        self.assertEqual(io.digest(s),before)
    def test_subject_rejection(self):
        for arm in spec.ARMS[1:]:
            r=self.cells['different_subject','identity',arm]
            self.assertFalse(r['gate_valid']);self.assertEqual(r['gate_reason'],'subject_mismatch');self.assertEqual(r['transfer_map'],[])
    def test_stale_dependency_rejection(self):
        for v in spec.VARIANTS:
            for arm in spec.ARMS[1:]:
                r=self.cells['premise_changed',v,arm]
                self.assertEqual(r['gate_reason'],'support_dependency_changed');self.assertEqual(r['transfer_map'],[])
    def test_id_dependency_cost_is_not_normalized(self):
        for arm in spec.ARMS[1:]:
            a=self.cells['premise_changed','identity',arm];b=self.cells['premise_changed','fresh_ids',arm]
            self.assertEqual(a['bridge_cost']['dependency_checks'],2);self.assertEqual(b['bridge_cost']['dependency_checks'],1)
    def test_all_native_graphs_unchanged_by_treatment(self):
        for sc in spec.SCENARIOS:
            for v in spec.VARIANTS:
                base=self.cells[sc,v,'cold']
                for arm in spec.ARMS:
                    r=self.cells[sc,v,arm]
                    self.assertEqual(r['program'],base['program']);self.assertEqual(r['raw_drives'],base['raw_drives'])
    def test_no_proof_reuse(self):
        for r in self.records.values():self.assertEqual(r['proof_graph']['external_node_refs'],[])
    def test_depth_is_proof_not_ticks(self):
        for t in spec.trials():
            self.assertEqual(self.reports[t['id']]['D_DAG'],2 if t['case'].startswith('premise_changed') else 3)
    def test_original_exp27_full_trajectory_regression(self):
        self.assertEqual(regression.run_reference()['B_comparisons'],12)
    def test_report_contains_every_hypothesis(self):
        s=reporting.summarize(self.plan,self.sources,self.records,self.reports)
        md=reporting.render(s).decode()
        for h in s['hypotheses']:self.assertIn(h['hypothesis'],md);self.assertIn(h['status'],md)
        self.assertEqual(len(s['ID_controls']),21)
    def test_equal_ticks_falsify_only_strict_specificity(self):
        records=deepcopy(self.records)
        # Reporting-only hypothetical: all carry/fixed pairs receive equal copied native tick counts.
        for t in spec.trials():
            if t['case'].startswith('extend') and t['arm'].startswith('fixed'):
                actual=self.cells['extend',t['source'],t['arm'].replace('fixed','carry')]
                records[t['id']]['native_cost']['kernel_ticks']=actual['native_cost']['kernel_ticks']
        s=reporting.summarize(self.plan,self.sources,records,self.reports)
        h=[h for h in s['hypotheses'] if h['hypothesis']=='H_source_specificity']
        self.assertEqual(len(h),6);self.assertTrue(all(x['status']=='falsified' for x in h))
    def test_report_does_not_credit_incorrect_savings(self):
        labels=deepcopy(self.reports)
        for x in labels.values():x['classification']='logical_failure'
        s=reporting.summarize(self.plan,self.sources,self.records,labels)
        self.assertTrue(all(not p['efficiency_evaluable'] for p in s['pairs']))
    def test_shared_A_counted_once_in_actual_run_cost(self):
        s=reporting.summarize(self.plan,self.sources,self.records,self.reports)
        self.assertEqual(s['unique_native_ticks'],sum(r['native_cost']['kernel_ticks'] for r in list(self.sources.values())+list(self.records.values())))
    def test_renaming_does_not_prove_semantic_understanding(self):
        s=reporting.summarize(self.plan,self.sources,self.records,self.reports)
        self.assertFalse(s['claims']['learned_context_competition_tested']);self.assertFalse(s['claims']['preallocated_substrate_tested'])


class InterventionFaults(Matrix):
    # Inherited matrix tests are excluded by the test loader below to avoid double-counting.
    def reject(self,mutator):
        r=self.warm();mutator(r)
        with self.assertRaises((ValueError,KeyError,TypeError)):
            audit.audit_record(r,self.sources['identity'],self.worlds['extend__identity'])
    def test_wrong_initial_goal(self):self.reject(lambda r:r['initial_state'].__setitem__('goal',.99))
    def test_wrong_transfer_slot(self):self.reject(lambda r:r['transfer_map'][0].__setitem__('target_group','e:2'))
    def test_wrong_transfer_value(self):self.reject(lambda r:r['transfer_map'][0].__setitem__('value',.1))
    def test_missing_tick(self):self.reject(lambda r:r['ticks'].pop(2))
    def test_changed_tick_state(self):self.reject(lambda r:r['ticks'][5]['state'].__setitem__('goal',.1))
    def test_changed_tick_residual(self):self.reject(lambda r:r['ticks'][2].__setitem__('residual',.9))
    def test_wrong_stable_history(self):self.reject(lambda r:r.__setitem__('initial_stable_steps',4))
    def test_wrong_convergence_tick_count(self):self.reject(lambda r:r['convergence'].__setitem__('ticks',1))
    def test_extra_tick_after_terminal(self):self.reject(lambda r:r['ticks'].append(deepcopy(r['ticks'][-1])))
    def test_wrong_proof_depth(self):self.reject(lambda r:r['proof_graph'].__setitem__('primitive_depth',1))
    def test_dangling_parent(self):self.reject(lambda r:r['proof_graph']['nodes'][-1].__setitem__('parents',['missing']))
    def test_cycle_in_proof(self):self.reject(lambda r:r['proof_graph']['nodes'][-1].__setitem__('parents',[r['proof_graph']['final']]))
    def test_fake_foreign_reference(self):self.reject(lambda r:r['proof_graph'].__setitem__('external_node_refs',['foreign']))
    def test_packet_changed_with_recomputed_checksum(self):
        def change(r):
            r['carry_packet']['dependencies'][0]['source']='wrong'
            r['carry_packet']['sha256']=io.digest({k:v for k,v in r['carry_packet'].items() if k!='sha256'})
        self.reject(change)
    def test_fake_source_provenance(self):self.reject(lambda r:r.__setitem__('source_sha256','0'*64))
    def test_false_adoption(self):self.reject(lambda r:r.__setitem__('accepted',False))
    def test_missing_event(self):self.reject(lambda r:r['events'].pop())
    def test_fake_cost_counter(self):self.reject(lambda r:r['native_cost'].__setitem__('group_updates',0))
    def test_unknown_energy_is_not_zero(self):self.reject(lambda r:r.__setitem__('energy_joules',0))


def load_tests(loader, tests, pattern):
    suite=unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(Matrix))
    # Only locally defined fault tests, not inherited Matrix tests.
    suite.addTests(InterventionFaults(n) for n in sorted(InterventionFaults.__dict__) if n.startswith('test_'))
    suite.addTests(loader.loadTestsFromTestCase(Boundaries))
    suite.addTests(loader.loadTestsFromTestCase(StorageAndWorkflow))
    return suite


class Boundaries(unittest.TestCase):
    def setUp(self):
        self.a,self.cs,self.w=spec.observations();self.source=runtime.run_query(self.a['identity'],spec.CONFIG)
    def test_same_start_but_internal_endpoints_change_rejected(self):
        b=deepcopy(self.cs[0]['observation']);b['edges'][0]['target']='x';b['edges'][1]['source']='x'
        r=runtime.run_query(b,spec.CONFIG,'carry_both',self.source)
        self.assertEqual(r['gate_reason'],'support_dependency_changed');self.assertTrue(audit.audit_record(r,self.source)['verified'])
    def test_reordered_edge_slots_bind_by_identity(self):
        b=deepcopy(self.cs[0]['observation']);b['edges']=[b['edges'][2],b['edges'][1],b['edges'][0]]
        r=runtime.run_query(b,spec.CONFIG,'carry_both',self.source)
        self.assertTrue(audit.audit_record(r,self.source)['verified'])
        self.assertIn(('e:0','e:2'),[(m['source_group'],m['target_group']) for m in r['transfer_map']])
    def test_world_label_is_rejected_at_runtime_boundary(self):
        b=deepcopy(self.cs[0]['observation']);b['world']={'e0':True}
        with self.assertRaises(ValueError):runtime.run_query(b,spec.CONFIG)
    def test_kernel_budget_is_measurement_not_logical_failure(self):
        cfg=dict(spec.CONFIG,max_ticks=4)
        r=runtime.run_query(self.cs[0]['observation'],cfg)
        self.assertEqual(audit.audit_record(r,world=self.w[self.cs[0]['id']])['classification'],'budget_termination')
    def test_graph_search_budget_is_preserved(self):
        r=runtime.run_query(self.cs[0]['observation'],dict(spec.CONFIG,max_search=1))
        self.assertEqual(audit.audit_record(r)['classification'],'budget_termination')
    def test_group_budget_is_preserved(self):
        r=runtime.run_query(self.cs[0]['observation'],dict(spec.CONFIG,max_groups=6))
        self.assertEqual(audit.audit_record(r)['classification'],'budget_termination')
    def test_configuration_change_rejects_transfer(self):
        r=runtime.run_query(self.cs[0]['observation'],dict(spec.CONFIG,damping=.4),'carry_both',self.source)
        self.assertEqual(r['gate_reason'],'config_changed');self.assertTrue(audit.audit_record(r,self.source)['verified'])
    def test_nonpositive_source_is_not_exported(self):
        a=deepcopy(self.a['identity']);a['edges'][1]['score']=-.92
        source=runtime.run_query(a,spec.CONFIG)
        r=runtime.run_query(self.cs[0]['observation'],spec.CONFIG,'carry_both',source)
        self.assertEqual(r['gate_reason'],'no_adopted_positive_source');self.assertTrue(audit.audit_record(r,source)['verified'])
    def test_ambiguous_readout_is_not_forced(self):
        ob=deepcopy(self.a['identity']);ob['edges']=ob['edges'][:1];ob['goal']='v';ob['edges'][0]['score']=None
        r=runtime.run_query(ob,spec.CONFIG)
        self.assertIsNone(r['raw_value']);self.assertFalse(r['accepted']);self.assertTrue(audit.audit_record(r)['verified'])
    def test_auditor_has_no_native_or_runtime_import(self):
        tree=ast.parse(Path(audit.__file__).read_text())
        for n in ast.walk(tree):
            if isinstance(n,ast.ImportFrom):self.assertFalse((n.module or '').startswith('hcr') or 'runtime' in (n.module or ''))
            if isinstance(n,ast.Import):self.assertTrue(all(not a.name.startswith('hcr') and 'runtime' not in a.name for a in n.names))


class StorageAndWorkflow(unittest.TestCase):
    def test_json_duplicate_key_rejected(self):
        with self.assertRaises(ValueError):io.loads('{"x":1,"x":2}')
    def test_json_nonfinite_rejected(self):
        for v in ('NaN','Infinity','1e999'):
            with self.assertRaises(ValueError):io.loads('{"x":'+v+'}')
    def test_inventory_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            for n in ('../a','/a','a/../b','a\\b','a//b','C:/a'):
                with self.assertRaises(ValueError):io.child(Path(d),n)
    def test_exclusive_raw_write(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'x.json';io.put(p,{'x':1})
            with self.assertRaises(FileExistsError):io.put(p,{'x':2})
            self.assertEqual(io.load(p),{'x':1})
    def test_missing_parent_file_is_fatal(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):provenance.check_inventory(Path(d),{'missing.log':'0'*64})
    def test_bad_parent_hash_is_fatal(self):
        with tempfile.TemporaryDirectory() as d:
            io.write(Path(d)/'x',b'wrong')
            with self.assertRaises(ValueError):provenance.check_inventory(Path(d),{'x':'0'*64})
    def test_plan_tampering_rejected(self):
        p=spec.expected_plan_body();p['design']['fixed_initial_value']=.999
        with self.assertRaises(ValueError):spec.validate_body(p)
    def test_producer_first_failure_and_partial_stream_preserved(self):
        with tempfile.TemporaryDirectory() as d:
            plan=dict(spec.expected_plan_body(),population='implementation_validation')
            original=runtime.run_query
            calls=[]
            def fail_after_begin(*args,**kwargs):
                calls.append(1)
                kwargs['event_sink']({'ordinal':0,'event':'injected_before_return','payload':{}})
                raise RuntimeError('deliberate test-only failure')
            with patch.object(runtime,'run_query',fail_after_begin):
                with self.assertRaises(RuntimeError):protocol.produce(plan,Path(d))
            self.assertEqual(len(calls),1)
            self.assertTrue((Path(d)/'failure.json').exists());self.assertTrue((Path(d)/'attempts.jsonl').read_text())
            self.assertEqual(io.load(Path(d)/'partial_progress.json')['completed'],0)
    def test_full_raw_stream_roundtrip_without_research_claim(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);p=dict(spec.expected_plan_body(),population='implementation_validation')
            with redirect_stdout(textio.StringIO()):protocol.produce(p,root)
            src,rows,checks,sc,count=protocol.read_and_audit(p,root)
            self.assertEqual((len(src),len(rows)),(2,42));self.assertGreater(count,1000)
            summary=reporting.summarize(p,src,rows,checks)
            self.assertEqual(summary['population'],'implementation_validation')
    def test_stream_tail_retry_detected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);p=dict(spec.expected_plan_body(),population='implementation_validation')
            with redirect_stdout(textio.StringIO()):protocol.produce(p,root)
            with (root/'attempts.jsonl').open('a',encoding='utf-8') as f:f.write('{}\n')
            with self.assertRaises(ValueError):protocol.read_and_audit(p,root)
    def test_sealed_bundle_and_zip_bytes(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'run';root.mkdir();io.write(root/'a.txt',b'original')
            protocol.seal_bundle(root);receipt=protocol.archive(root)
            self.assertTrue((root.parent/receipt['archive']).exists())
            io.write(root/'extra.txt',b'bad')
            with self.assertRaises(ValueError):protocol.verify_bundle_files(root)
    def test_first_error_not_overwritten(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);protocol.failure(root,'first',ValueError('first'));before=(root/'failure.json').read_bytes()
            protocol.failure(root,'second',ValueError('second'))
            self.assertEqual((root/'failure.json').read_bytes(),before)
