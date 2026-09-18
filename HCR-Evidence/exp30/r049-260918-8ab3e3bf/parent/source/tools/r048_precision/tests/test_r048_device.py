from copy import deepcopy
from pathlib import Path
import ast
import contextlib
import io as textio
import tempfile
import unittest
from unittest.mock import patch
from tools.r048_precision import spec,io,device,evaluate,reporting
from tools.r047_state_ablation import runtime,audit

ANCHOR={
 'cold':'b803bfc0ab010dc490e7fcf74ca3eaf6c6ada354cb508a0a9dae8cdc74b7c6ec',
 'carry_edge':'cb9f963ccd7ead4581002e7ffee39b37f9f59a2e2406fe782eeb3687b2fd1585',
 'carry_prefix':'7d1950e1b1fafe7ce130525cd48e7947d24a420173383bde288ef7d808a70cee',
 'carry_both':'c0fec31d522cea86e591869bcee572cfa075f1848d21d50f04b6eec9a85b499c',
 'fixed_edge':'8b1d2b4b7887b495d05b05cdc9fb5f54aa12a55e2a125de6c355868a0851f46f',
 'fixed_prefix':'c88a35f73be1434395954c833c9eb9621e7369aeed6d260248ec379ac46b82a7',
 'fixed_both':'b3e9904b0bdc6bb3292c195e780efe72d88afd8f480bc67f0f671796ee4ad0ca',
}

class Matrix(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan=dict(spec.body(),population='implementation_validation')
        cls.sources={};cls.records={};cls.sa={};cls.ba={};cls.cells={}
        by={x['id']:x for x in cls.plan['cases']}
        for c in cls.plan['cases']:
            key=c['source'];ob=cls.plan['sources'][key]['observation']
            r=runtime.run_query(ob,spec.CONFIG);cls.sources[key]=r
            cls.sa[key]=evaluate.stable_audit(r,None,{e['id']:True for e in ob['edges']})
        for t in cls.plan['trials']:
            c=by[t['case']];r=runtime.run_query(c['observation'],spec.CONFIG,t['arm'],cls.sources[t['source']])
            cls.records[t['id']]=r;cls.ba[t['id']]=evaluate.stable_audit(r,cls.sources[t['source']],cls.plan['worlds'][t['case']])
            cls.cells[c['strength'],c['variant'],t['arm']]=(t['id'],r)
        cls.summary=evaluate.summarize(cls.plan,cls.sources,cls.records,cls.sa,cls.ba)
    def at(self,arm,level=.92):return self.cells[level,'identity',arm][1]
    def test_plan_exact_count_and_frozen_hash(self):
        self.assertEqual((len(self.sources),len(self.records)),(14,98))
        self.assertEqual(io.digest(spec.body()),'c84c7e380852bd46231c8fab86310f218ea1fb56e0cebcf8e51f757149cd6ba2')
    def test_all_112_records_replayed(self):
        self.assertTrue(all(x['verified'] for x in list(self.sa.values())+list(self.ba.values())))
    def test_shared_support_is_identical_between_A_B(self):
        for c in self.plan['cases']:
            self.assertEqual(self.plan['sources'][c['source']]['observation']['edges'],c['observation']['edges'][:2])
            self.assertEqual(c['observation']['edges'][2]['score'],.92)
    def test_world_fixed_not_calculated_from_result(self):
        self.assertTrue(all(all(w.values()) for w in self.plan['worlds'].values()))
    def test_both_ID_anchor_complete_dynamics_match_EXP28(self):
        for v in spec.VARIANTS:
            for arm,h in ANCHOR.items():
                r=self.cells[.92,v,arm][1]
                self.assertEqual(io.digest(dict(ticks=r['ticks'],convergence=r['convergence'])),h)
    def test_mask_controls_only_previous_positions(self):
        for r in self.records.values():
            self.assertEqual(r['initial_state']['goal'],.5)
            self.assertEqual(r['initial_state']['e:2'],.5)
            self.assertEqual(r['initial_state']['p:0:2'],.5)
            self.assertEqual(r['initial_stable_steps'],0)
    def test_fixed_uses_identical_packet_and_mask(self):
        for c in self.plan['cases']:
            for mask in ('edge','prefix','both'):
                a=self.cells[c['strength'],c['variant'],'carry_'+mask][1]
                b=self.cells[c['strength'],c['variant'],'fixed_'+mask][1]
                self.assertEqual(a['carry_packet'],b['carry_packet'])
                self.assertEqual([x['target_group'] for x in a['transfer_map']],[x['target_group'] for x in b['transfer_map']])
                self.assertTrue(all(x['value']==.99 for x in b['transfer_map']))
    def test_ineligible_source_not_dropped_or_retried(self):
        for key,r in self.sources.items():
            group=[t for t in self.plan['trials'] if t['source']==key];self.assertEqual(len(group),7)
            if not(r['accepted'] and r['raw_value'] is True):
                for t in group:
                    b=self.records[t['id']];self.assertEqual(b['transfer_map'],[]);self.assertIsNone(b['carry_packet'])
                pairs=[p for p in self.summary['pairs'] if p['case']==key]
                self.assertTrue(all(not p['eligible'] for p in pairs))
    def test_native_construction_not_changed_between_arms(self):
        for c in self.plan['cases']:
            baseline=self.cells[c['strength'],c['variant'],'cold'][1]
            for arm in spec.ARMS:
                r=self.cells[c['strength'],c['variant'],arm][1]
                self.assertEqual((r['program'],r['effective_drives']),(baseline['program'],baseline['effective_drives']))
    def test_A_counted_once_in_unique_cost(self):
        self.assertEqual(self.summary['unique_native_ticks'],sum(r['native_cost']['kernel_ticks'] for r in list(self.sources.values())+list(self.records.values())))
    def test_failed_predictions_visible_in_report(self):
        text=reporting.render(self.summary).decode('utf-8')
        self.assertIn('falsified',text)
        for h in self.summary['hypotheses']:self.assertIn(h['hypothesis'],text);self.assertIn(h['status'],text)
    def test_new_goal_and_history_mutation_detected(self):
        for field,value in [('old_goal_imported',True),('initial_stable_steps',4)]:
            r=deepcopy(self.at('carry_both'));r[field]=value
            with self.assertRaises(ValueError):audit.audit_record(r,self.sources['s05__identity'])
    def test_fake_tick_detected(self):
        r=deepcopy(self.at('carry_both'));r['ticks'][2]['state']['goal']=.1234
        with self.assertRaises(ValueError):audit.audit_record(r,self.sources['s05__identity'])
    def test_fake_parent_reference_detected(self):
        r=deepcopy(self.at('carry_both'));r['proof_graph']['nodes'][-1]['parents']=['missing']
        with self.assertRaises(ValueError):audit.audit_record(r,self.sources['s05__identity'])
    def test_eligibility_excludes_wrong_or_unapplied(self):
        a,b=self.at('carry_both'),self.at('fixed_both');source=self.sources['s05__identity']
        good=dict(accepted_correct=True);bad=dict(accepted_correct=False)
        ok,reason=evaluate.eligibility(a,b,source,good,bad,good)
        self.assertFalse(ok);self.assertIn('actual_B_not_correct_adoption',reason)
    def test_checkpoint_never_pads_stopped_trajectory(self):
        a,b=deepcopy(self.at('carry_both')),self.at('fixed_both');a['ticks']=a['ticks'][:2]
        n=len(a['ticks']);cp=evaluate.checkpoint_comparison(a,b)
        self.assertEqual(len(a['ticks']),n)
        self.assertTrue(all(x['group_Linf'] is None for x in cp if x['tick']>2))
    def test_source_is_not_mutated(self):
        s=self.sources['s05__identity'];before=io.digest(s)
        runtime.run_query(self.at('cold')['observation'],spec.CONFIG,'carry_both',s)
        self.assertEqual(before,io.digest(s))
    def test_evaluator_never_imports_producer_or_hcr(self):
        for path in (Path(evaluate.__file__),Path(audit.__file__)):
            tree=ast.parse(path.read_text())
            for node in ast.walk(tree):
                if isinstance(node,ast.ImportFrom):self.assertNotIn('runtime',node.module or '');self.assertFalse((node.module or '').startswith('hcr'))
    def test_budgets_preserve_nonanswers(self):
        r=runtime.run_query(self.at('cold')['observation'],dict(spec.CONFIG,max_ticks=4))
        self.assertEqual(audit.audit_record(r)['classification'],'budget_termination')
    def test_no_energy_or_peak_memory_zero_claim(self):
        for r in self.records.values():self.assertIsNone(r['energy_joules']);self.assertIsNone(r['peak_memory_bytes'])

class Streams(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.root=Path(cls.temp.name)
        plan=dict(spec.body(),population='implementation_validation');io.put(cls.root/'plan.json',plan)
        # Canonical JSON reorders dictionary keys; execution order must follow the frozen case list.
        cls.plan=io.load(cls.root/'plan.json')
        with contextlib.redirect_stdout(textio.StringIO()):device.execute(plan,cls.root)
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()
    def test_serialized_plan_roundtrip_event_order(self):
        a,b,sa,ba,n=evaluate.read_audit(self.plan,self.root)
        self.assertEqual((len(a),len(b)),(14,98));self.assertGreater(n,112)
    def test_extra_retry_is_detected(self):
        original=io.read(self.root/'attempts.jsonl')
        try:
            (self.root/'attempts.jsonl').write_bytes(original+b'{}\n')
            with self.assertRaises(ValueError):evaluate.read_audit(self.plan,self.root)
        finally:(self.root/'attempts.jsonl').write_bytes(original)
    def test_first_failure_preserves_partial_stream(self):
        with tempfile.TemporaryDirectory() as d:
            calls=[]
            def injected(*args,**kwargs):
                calls.append(1);kwargs['event_sink']({'event':'injected_fixture_failure','ordinal':0,'payload':{}})
                raise RuntimeError('deliberate test-only error')
            with patch.object(runtime,'run_query',injected):
                with self.assertRaises(RuntimeError):device.execute(self.plan,Path(d))
            self.assertEqual(len(calls),1);self.assertTrue((Path(d)/'failure.json').exists())
            self.assertGreater((Path(d)/'attempts.jsonl').stat().st_size,0)
            self.assertEqual(io.load(Path(d)/'partial_progress.json')['completed'],0)
