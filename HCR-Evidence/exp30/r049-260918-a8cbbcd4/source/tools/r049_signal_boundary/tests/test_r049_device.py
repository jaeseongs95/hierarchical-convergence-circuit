from copy import deepcopy
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import ast
import io as textio
import unittest
from tools.r048_precision import io
from tools.r049_signal_boundary import spec,device,audit,diagnostics,evaluate,reporting,pipeline
ROOT=Path(__file__).resolve().parents[3]


class Matrix(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan=dict(spec.body(),population='implementation_validation');cls.cases={c['id']:c for c in cls.plan['cases']}
        cls.records={};cls.audits={};cls.cells={}
        for t in cls.plan['trials']:
            c=cls.cases[t['case']];r=device.run_query(c['observation'],cls.plan['kernel_config'],t['arm'])
            cls.records[t['id']]=r;cls.audits[t['id']]=audit.audit_record(r,cls.plan['worlds'][t['case']])
            cls.cells[c['strength'],c['pattern'],c['variant'],t['arm']]=(t,r)
        cls.prior=io.load(ROOT/'docs/R049_PRIOR_EXPLORATION.json')
        cls.summary=evaluate.summarize(cls.plan,cls.records,cls.audits,cls.prior)
    def test_matrix_count_and_fixed_design(self):
        self.assertEqual(len(self.records),48);self.assertEqual(io.load(ROOT/'docs/R049_FROZEN_DESIGN.json'),spec.body())
        self.assertEqual(sum(t['evidence_role']=='prior_exploration_replication' for t in self.plan['trials']),16)
    def test_all_native_records_pass_separate_scalar_and_proof_audit(self):
        self.assertTrue(all(x['verified'] for x in self.audits.values()))
    def test_native_prior_exploration_regression(self):
        self.assertEqual(len(self.summary['prior_regressions']),16)
        self.assertTrue(all(x['dynamics_equal'] for x in self.summary['prior_regressions']))
    def test_goal_always_neutral_and_history_not_imported(self):
        for r in self.records.values():self.assertEqual(r['initial_state']['goal'],.5);self.assertEqual(r['initial_stable_steps'],0)
    def test_high_assignment_ignores_world(self):
        hi=[r['initial_state'] for r in self.records.values() if r['arm'].endswith('high')]
        self.assertTrue(all(x==hi[0] for x in hi));self.assertEqual(sum(v==.99 for v in hi[0].values()),4)
    def test_observations_unchanged(self):
        for t in self.plan['trials']:self.assertEqual(self.records[t['id']]['observation'],self.cases[t['case']]['observation'])
    def test_stored_graph_same_but_effective_function_different(self):
        for c in self.cases.values():
            key=(c['strength'],c['pattern'],c['variant'])
            a=self.cells[*key,'on_neutral'][1];b=self.cells[*key,'off_neutral'][1]
            self.assertEqual(a['program'],b['program']);self.assertNotEqual(a['effective_program_sha256'],b['effective_program_sha256'])
    def test_off_message_count_halves_per_tick_without_fake_savings(self):
        for r in self.records.values():
            per=8 if r['intervention']['top_down'] else 4
            self.assertEqual(r['native_cost']['signal_transmissions'],per*len(r['ticks']))
    def test_signal_ledger_covers_every_group_and_tick(self):
        rows=self.summary['signals'];self.assertEqual(len(rows),5*self.summary['unique_native_ticks'])
        for t in self.plan['trials']:
            lr=[x for x in rows if x['trial']==t['id']]
            self.assertEqual(sum(x['support_transmissions']+x['top_down_transmissions'] for x in lr),self.records[t['id']]['native_cost']['signal_transmissions'])
    def test_signal_damping_reconciles_raw(self):
        for x in self.summary['signals']:
            y=(1-x['damping'])*x['before']+x['damping']*x['target_implied_by_native_update']
            self.assertAlmostEqual(y,x['after'],places=14)
    def test_masked_terms_are_not_counted_as_messages(self):
        for x in self.summary['signals']:
            if self.records[x['trial']]['arm'].startswith('off'):
                self.assertEqual(x['top_down_sum'],0.);self.assertEqual(x['top_down_transmissions'],0)
                self.assertIs(x['masked_term_is_executed'],False)
    def test_first_readout_not_silently_used_for_adoption(self):
        for r in self.records.values():
            first=r['first_margin_readout'];self.assertIs(first['adopted'],False)
            self.assertLessEqual(first['tick'],len(r['ticks']))
            self.assertEqual(r['events'][-1]['event'],'adoption')
    def test_prior_weak_failure_types_stay_distinct(self):
        ra=self.cells[.02,'positive','identity','on_neutral'][1]
        rb=self.cells[.02,'positive','identity','off_neutral'][1]
        da=diagnostics.boundary(ra,audit.audit_record(ra,{'e0':True,'e1':True}))
        db=diagnostics.boundary(rb,audit.audit_record(rb,{'e0':True,'e1':True}))
        self.assertTrue(da['proof_assumption_support_conflict']);self.assertFalse(da['proof_construction_failed'])
        self.assertTrue(db['proof_construction_failed']);self.assertFalse(db['proof_assumption_support_conflict'])
    def test_low_strength_observed_crossing_preserved(self):
        r=self.cells[.02,'positive','identity','on_neutral'][1]
        d=diagnostics.boundary(r,audit.audit_record(r,{'e0':True,'e1':True}))
        self.assertEqual(d['first_sign_conflict_tick']['e1'],2)
    def test_flags_are_multilabel(self):
        b=[x for x in self.summary['boundaries'] if x['strength']==.02 and x['pattern']=='positive' and x['arm']=='on_neutral'][0]
        self.assertTrue(b['raw_value_incorrect'] and b['proof_assumption_support_conflict'] and b['adoption_rejected'])
    def test_all_hypotheses_in_rendered_report(self):
        md=reporting.render(self.summary).decode()
        for h in self.summary['hypotheses']:self.assertIn(h['hypothesis'],md);self.assertIn(h['status'],md)
    def test_pairs_match_one_factor_at_a_time(self):
        for p in self.summary['pairs']:
            a,b=p['treatment'].split('_'),p['control'].split('_')
            self.assertEqual(sum(x!=y for x,y in zip(a,b)),1)
            self.assertFalse(p['general_efficiency_claimed'])
    def test_budget_and_unmeasured_fields_not_zero(self):
        for r in self.records.values():self.assertIsNone(r['energy_joules']);self.assertIsNone(r['peak_memory_bytes']);self.assertIsNone(r['native_cost']['wall_seconds'])
    def test_auditor_and_diagnostics_do_not_import_producer_or_hcr(self):
        for mod in (audit,diagnostics):
            tree=ast.parse(Path(mod.__file__).read_text(encoding='utf-8'))
            for n in ast.walk(tree):
                if isinstance(n,ast.Import):self.assertFalse(any(x.name.startswith('hcr') or x.name.endswith('.device') for x in n.names))
                if isinstance(n,ast.ImportFrom):self.assertFalse((n.module or '').startswith('hcr') or (n.module or '').endswith('device'))


class Faults(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        c=spec.body()['cases'][0];cls.ob=c['observation'];cls.world={'e0':True,'e1':True}
        cls.good=device.run_query(cls.ob,spec.CONFIG,'on_neutral')
    def reject(self,fn):
        r=deepcopy(self.good);fn(r)
        with self.assertRaises((ValueError,KeyError,TypeError,IndexError)):audit.audit_record(r,self.world)
    def test_policy_boolean_cannot_be_integer(self):self.reject(lambda r:r['intervention'].__setitem__('top_down',1))
    def test_reuse_flag_cannot_be_integer(self):self.reject(lambda r:r['intervention'].__setitem__('reuse_applied',0))
    def test_changed_initial_goal(self):self.reject(lambda r:r['initial_state'].__setitem__('goal',.99))
    def test_changed_tick(self):self.reject(lambda r:r['ticks'][4]['state'].__setitem__('e:1',.9))
    def test_deleted_tick(self):self.reject(lambda r:r['ticks'].pop(2))
    def test_extra_post_stop_tick(self):self.reject(lambda r:r['ticks'].append(deepcopy(r['ticks'][-1])))
    def test_fake_residual(self):self.reject(lambda r:r['ticks'][3].__setitem__('residual',0.))
    def test_fake_stable_history(self):self.reject(lambda r:r.__setitem__('initial_stable_steps',4))
    def test_wrong_active_link_mask(self):self.reject(lambda r:r['active_link_indices'].pop())
    def test_switch_without_signature(self):self.reject(lambda r:r['intervention'].__setitem__('top_down',False))
    def test_effective_digest_must_bind_policy(self):self.reject(lambda r:r.__setitem__('effective_program_sha256',io.digest(r['program'])))
    def test_deleted_event(self):self.reject(lambda r:r['events'].pop())
    def test_provisional_readout_as_adopted(self):self.reject(lambda r:r['first_margin_readout'].__setitem__('adopted',True))
    def test_dangling_parent(self):self.reject(lambda r:r['proof']['nodes'][-1].__setitem__('parents',['missing']))
    def test_proof_cycle(self):self.reject(lambda r:r['proof']['nodes'][-1].__setitem__('parents',[r['proof']['final']]))
    def test_invented_depth(self):self.reject(lambda r:r['proof'].__setitem__('primitive_depth',0))
    def test_wrong_adoption(self):self.reject(lambda r:r.__setitem__('accepted',True))
    def test_fake_message_count(self):self.reject(lambda r:r['native_cost'].__setitem__('signal_transmissions',0))
    def test_zero_energy_is_not_unknown(self):self.reject(lambda r:r.__setitem__('energy_joules',0))
    def test_world_field_rejected_at_runtime(self):
        ob=deepcopy(self.ob);ob['truth']=True
        with self.assertRaises(ValueError):device.run_query(ob,spec.CONFIG,'on_high')
    def test_input_and_source_not_mutated_by_observer(self):
        ob=deepcopy(self.ob);before=io.digest(ob)
        def sink(ev):ev['payload'].clear()  # Observer receives a copy, cannot mutate raw/internal state.
        r=device.run_query(ob,spec.CONFIG,'on_neutral',event_sink=sink)
        self.assertEqual(io.digest(ob),before);audit.audit_record(r,self.world)
    def test_kernel_budget_is_preserved(self):
        r=device.run_query(self.ob,dict(spec.CONFIG,max_ticks=4),'on_neutral')
        a=audit.audit_record(r,self.world);self.assertEqual(a['classification'],'budget_termination')
    def test_graph_search_budget_is_preserved(self):
        r=device.run_query(self.ob,dict(spec.CONFIG,max_search=1),'on_neutral')
        self.assertEqual(audit.audit_record(r)['classification'],'budget_termination')
    def test_group_budget_is_preserved(self):
        r=device.run_query(self.ob,dict(spec.CONFIG,max_groups=4),'on_neutral')
        self.assertEqual(audit.audit_record(r)['classification'],'budget_termination')
    def test_path_budget_is_preserved(self):
        r=device.run_query(self.ob,dict(spec.CONFIG,max_path_length=1),'on_neutral')
        self.assertEqual(audit.audit_record(r)['classification'],'budget_termination')
    def test_ambiguous_missing_observation_not_repaired(self):
        ob=deepcopy(self.ob)
        for e in ob['edges']:e['score']=None
        r=device.run_query(ob,spec.CONFIG,'off_neutral');self.assertTrue(audit.audit_record(r)['verified'])
    def test_edge_input_reorder_uses_structural_path(self):
        ob=deepcopy(self.ob);ob['edges'].reverse()
        r=device.run_query(ob,spec.CONFIG,'on_high');self.assertEqual(r['program']['paths'],[[1,0]]);audit.audit_record(r,self.world)


class Streams(unittest.TestCase):
    def test_roundtrip_raw_event_stream_and_analysis(self):
        with TemporaryDirectory() as d:
            root=Path(d);plan=dict(spec.body(),population='implementation_validation')
            with redirect_stdout(textio.StringIO()):device.produce(plan,root)
            records,audits,count=evaluate.read_audit(plan,root)
            self.assertEqual(len(records),48);self.assertGreater(count,48*5)
            s=evaluate.summarize(plan,records,audits,io.load(ROOT/'docs/R049_PRIOR_EXPLORATION.json'))
            self.assertEqual(s['population'],'implementation_validation');self.assertEqual(len(s['signals']),5*s['unique_native_ticks'])
    def test_extra_retry_is_detected(self):
        with TemporaryDirectory() as d:
            root=Path(d);plan=dict(spec.body(),population='implementation_validation')
            with redirect_stdout(textio.StringIO()):device.produce(plan,root)
            with (root/'attempts.jsonl').open('ab') as f:f.write(b'{}\n')
            with self.assertRaises(ValueError):evaluate.read_audit(plan,root)
    def test_first_failure_not_retried(self):
        with TemporaryDirectory() as d:
            root=Path(d);plan=dict(spec.body(),population='implementation_validation');calls=[]
            def fail(*args,**kwargs):
                calls.append(1);kwargs['event_sink'](dict(ordinal=0,event='test_injected_failure',payload={}));raise RuntimeError('intentional fixture failure')
            with patch.object(device,'run_query',fail):
                with self.assertRaises(RuntimeError):device.produce(plan,root)
            self.assertEqual(len(calls),1);self.assertEqual(io.load(root/'partial_progress.json')['completed'],0)
            self.assertTrue(io.load(root/'failure.json')['message']);self.assertGreater((root/'attempts.jsonl').stat().st_size,0)
    def test_serialized_plan_order_is_fixed(self):
        p=dict(schema='hcr-exp30-plan-v1',population='implementation_validation',created_utc='test',source_hashes={},parent_bundle_sha256='test',**spec.body())
        pipeline.validate_plan(io.loads(io.encode(p)))
        p['trials'].reverse()
        with self.assertRaises(ValueError):pipeline.validate_plan(p)
