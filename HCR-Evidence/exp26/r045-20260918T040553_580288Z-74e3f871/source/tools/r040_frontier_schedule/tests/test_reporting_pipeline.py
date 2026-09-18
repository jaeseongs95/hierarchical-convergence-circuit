"""보고/파일 경계 self-test. native/seed 재생은 명시적 stub이며 연구 결과가 아니다."""
from copy import deepcopy
from pathlib import Path
import json,tempfile,types,sys,unittest
from unittest.mock import patch
from r040_frontier_schedule import reporting,spec,sources,protocol,audit
from r040_frontier_schedule.contracts import SCHEDULE_USAGE,digest
from r039_order_isolation.tests._fixtures import parent,cases,reporting_fixture as old_fixture
from r039_order_isolation.spec import trials as old_trials
from r037_online_selection import io


def fixture():
    old={(r['trial']['case'],r['trial']['scope'],r['trial']['arm']):r for r in old_fixture()};rows=[]
    for trial in spec.trials(cases()):
        r=deepcopy(old[(trial['case'],trial['scope'],trial['arm'])]);r['trial']=trial
        r['scheduler_usage']={k:0 for k in SCHEDULE_USAGE};r['scheduler_usage']['decision_calls']=r['audit']['controller']['native_advances']
        r['audit']['controller']['scheduler_choices']=[dict(before_generation=i,selected_edge_ids=['e0'],selected_index=0,
            frontier_paths_edge_ids=[['e0']],reordered=False) for i in range(r['scheduler_usage']['decision_calls'])]
        for step,e in enumerate(r['order_diagnostics']['completion_trace']):e.update(expansion=step+1,event_seq=step)
        r['parent_regression']={'verified':True,'synthetic_test_stub':True} if trial['scheduler']=='input_order' else None
        rows.append(r)
    return rows


class ReportingTests(unittest.TestCase):
    def test_full_synthetic_population(self):
        s=reporting.summarize(fixture());self.assertEqual(s['native_trials'],72);self.assertEqual(len(s['paired']),24)
        self.assertEqual(len(s['order_effects']),12);self.assertEqual(len(s['scheduler_contrasts']),36)
        self.assertEqual(s['parent_regression_checked'],36)
    def test_ticks_not_multiplied_by_readouts(self):
        r=fixture();s=reporting.summarize(r);self.assertEqual(s['costs']['native_kernel_ticks'],sum(x['usage']['native_kernel_ticks'] for x in r))
    def test_scheduler_cost_separate(self):
        s=reporting.summarize(fixture());self.assertIn('scheduler',s['costs']);self.assertNotIn('total_cost',s['costs'])
    def test_event_sequence_bookkeeping_excluded(self):
        a=fixture()[0];b=deepcopy(a);b['order_diagnostics']['completion_trace'][0]['event_seq']+=20
        self.assertEqual(reporting.computational_signature(a),reporting.computational_signature(b))
    def test_real_computation_change_not_excluded(self):
        a=fixture()[0];b=deepcopy(a);b['order_diagnostics']['completion_trace'][0]['expansion']+=1
        self.assertNotEqual(reporting.computational_signature(a),reporting.computational_signature(b))
    def test_gap_removed_is_observation_not_required(self):
        rows=fixture()
        for r in rows:
            if r['trial']['scheduler']=='input_order' and r['order_diagnostics']['branch_order']=='DMS':
                r['usage']['native_kernel_ticks']+=5;r['native_cost']['kernel_ticks']+=5
        s=reporting.summarize(rows)
        self.assertTrue(all(x['finding']=='tick_gap_removed' for x in s['mediation']))
    def test_no_gap_accepted(self):
        self.assertTrue(all(x['finding']=='no_input_order_tick_gap' for x in reporting.summarize(fixture())['mediation']))
    def test_missing_trial_rejected(self):
        with self.assertRaises(ValueError):reporting.summarize(fixture()[:-1])
    def test_duplicate_trial_rejected(self):
        rows=fixture();rows[-1]=rows[0]
        with self.assertRaises(ValueError):reporting.summarize(rows)
    def test_csv_contains_separate_scheduler_fields(self):
        text=reporting.trial_csv(reporting.summarize(fixture())['trials'])
        self.assertIn('scheduler_key_comparisons',text);self.assertIn('posthoc_selection_edge_checks',text)
    def test_render_preserves_nonclaims(self):
        text=reporting.render(reporting.summarize(fixture()));self.assertIn('최적',text);self.assertIn('원인 분리',text)


class PipelineTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);self.root=Path(tmp.name)/'run';self.root.mkdir()
        self.core={'memory':{},'config':{}};self.cases=cases();self.base=parent()
        for n in sources.PARENT_FILES:
            value={'synthetic_fixture':True}
            if n=='plan.json':value={'trials':old_trials(self.cases)}
            io.put(self.root/sources.capsule_name(n),value)
        hashes={n:io.file_hash(self.root/sources.capsule_name(n)) for n in sources.PARENT_FILES}
        for name,value in [('dependencies',{}),('addon_hashes',{}),('read_parent',(self.root,self.cases,self.core,hashes,self.base)),
                           ('validate_parent_documents',(self.cases,self.core,self.base))]:
            p=patch.object(sources,name,return_value=value);p.start();self.addCleanup(p.stop)
        plan=protocol.make_plan(self.root);io.put(self.root/'plan.json',plan)
        io.put(self.root/'environment.json',dict(mode='native_experiment',synthetic_backend=False,
            automatic_retry=False,external_llm_used=False,unit_test_stub_not_experiment=True))
        seedmodule=types.ModuleType('r036_input_representation.audit')
        seedmodule.check_seed=lambda r,p:(self.core,{},dict(synthetic_seed_stub=True))
        p=patch.dict(sys.modules,{'r036_input_representation.audit':seedmodule});p.start();self.addCleanup(p.stop)
        records={r['trial']['id']:r for r in fixture()}
        p=patch.object(audit,'audit_trial',side_effect=lambda run,t,c,seed,conditions:deepcopy(records[t['id']]))
        p.start();self.addCleanup(p.stop)
        p=patch.object(audit.trajectory,'describe',side_effect=lambda run,r,c:r['order_diagnostics']);p.start();self.addCleanup(p.stop)
        p=patch.object(audit,'compare_parent',return_value={'verified':True,'synthetic_stub':True});p.start();self.addCleanup(p.stop)
        events=[]
        for trial in plan['trials']:
            run=dict(base={'events':[]},posthoc_events=[],final=records[trial['id']]['final'],synthetic_native_stub=True)
            raw=dict(schema='hcr-exp21-raw-trial-v1',trial=trial,run=run);io.put(self.root/'raw'/(trial['id']+'.json'),raw)
            events += [dict(event='trial_started',trial=trial),
                dict(event='trial_action',trial_id=trial['id'],record=dict(event='base_completed',base_sha256=digest(run['base']))),
                dict(event='trial_action',trial_id=trial['id'],record=dict(event='arm_finished',final=run['final'])),
                dict(event='trial_completed',trial_id=trial['id'],raw_sha256=digest(raw))]
        io.write_bytes(self.root/'attempts.jsonl',(''.join(json.dumps(e)+'\n' for e in events)).encode())
        self.seal()
    def seal(self):
        p=self.root/'manifest.json'
        if p.exists():p.unlink() # 합성 fixture를 위한 재봉인. 제품 API에는 재봉인 기능이 없다.
        io.put(p,dict(schema='hcr-exp21-raw-manifest-v1',state='raw_complete',independent_audit_pending=True,
            files={n:io.file_hash(self.root/n) for n in sorted(io.inventory(self.root)) if not n.startswith(('analysis/','audit_failures/'))}))
    def test_roundtrip_raw_analysis_verify(self):
        a=audit.write_analysis(self.root);b=audit.write_analysis(self.root,check_only=True);self.assertEqual(a,b)
        self.assertEqual(a['native_trials'],72)
        for name in ('mediation.csv','scheduler_contrasts.csv','scheduler_decisions.csv','readouts.csv'):
            self.assertTrue((self.root/'analysis'/name).is_file())
    def test_stream_tail_rejected(self):
        with (self.root/'attempts.jsonl').open('a') as f:f.write('{}\n')
        self.seal()
        with self.assertRaises(ValueError):audit.verify_raw(self.root)
    def test_stream_trial_binding_rejected(self):
        p=self.root/'attempts.jsonl';lines=p.read_text().splitlines();lines[0]='{}';p.write_text('\n'.join(lines)+'\n');self.seal()
        with self.assertRaises(ValueError):audit.verify_raw(self.root)
    def test_missing_raw_rejected(self):
        (self.root/'raw/t0000.json').unlink()
        with self.assertRaises(ValueError):audit.verify_raw(self.root)
    def test_checksum_error_recorded(self):
        (self.root/'raw/t0000.json').write_text('{}')
        with self.assertRaises(ValueError):audit.write_analysis(self.root)
        self.assertEqual(len(list((self.root/'audit_failures').glob('*.json'))),1)
    def test_analysis_not_overwritten(self):
        audit.write_analysis(self.root)
        with self.assertRaises(FileExistsError):audit.write_analysis(self.root)
    def test_analysis_tampering_not_repaired(self):
        audit.write_analysis(self.root);p=self.root/'analysis/summary.ko.md';p.write_text('tamper')
        with self.assertRaises(ValueError):audit.write_analysis(self.root,check_only=True)
        self.assertEqual(p.read_text(),'tamper')
