"""원자료/stream/분석 왕복 테스트. native·seed 재생은 명시적 stub이다."""
from pathlib import Path
from copy import deepcopy
import json,sys,tempfile,types,unittest
from unittest.mock import patch
from r037_online_selection import io
from r039_order_isolation import audit,protocol,sources,spec
from r039_order_isolation.contracts import digest
from r039_order_isolation.tests._fixtures import parent,cases,reporting_fixture


class AuditPipelineTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);self.root=Path(tmp.name)/'run';self.root.mkdir()
        self.core={'memory':{},'config':{}};self.cases=cases();self.base=parent()
        for n in sources.PARENT_FILES:io.put(self.root/sources.capsule_name(n),{'synthetic_fixture':True})
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
        fixture={(r['trial']['case'],r['trial']['scope'],r['trial']['arm']):r for r in reporting_fixture()}
        def audit_stub(run,trial,case,seed,conditions):
            r=deepcopy(fixture[(trial['case'],trial['scope'],trial['arm'])]);r['trial']=deepcopy(trial);return r
        p=patch.object(audit,'audit_trial',side_effect=audit_stub);p.start();self.addCleanup(p.stop)
        p=patch.object(audit.trajectory,'describe',side_effect=lambda run,r,c:r['order_diagnostics']);p.start();self.addCleanup(p.stop)
        events=[]
        for trial in plan['trials']:
            rec=fixture[(trial['case'],trial['scope'],trial['arm'])]
            run=dict(base={'events':[]},posthoc_events=[],final=rec['final'],synthetic_native_stub=True)
            raw=dict(schema='hcr-exp20-raw-trial-v1',trial=trial,run=run)
            io.put(self.root/'raw'/(trial['id']+'.json'),raw)
            events += [dict(event='trial_started',trial=trial),
                dict(event='trial_action',trial_id=trial['id'],record=dict(event='base_completed',base_sha256=digest(run['base']))),
                dict(event='trial_action',trial_id=trial['id'],record=dict(event='arm_finished',final=run['final'])),
                dict(event='trial_completed',trial_id=trial['id'],raw_sha256=digest(raw))]
        io.write_bytes(self.root/'attempts.jsonl',(''.join(json.dumps(e)+'\n' for e in events)).encode('utf-8'))
        self.seal()
    def seal(self):
        manifest=self.root/'manifest.json'
        if manifest.exists():manifest.unlink()  # 테스트 fixture 봉인만 재작성한다. 제품 API에는 없는 조작이다.
        io.put(manifest,dict(schema='hcr-exp20-raw-manifest-v1',state='raw_complete',independent_audit_pending=True,
            files={n:io.file_hash(self.root/n) for n in sorted(io.inventory(self.root)) if not n.startswith(('analysis/','audit_failures/'))}))
    def test_raw_to_analysis_and_verify_roundtrip(self):
        first=audit.write_analysis(self.root);second=audit.write_analysis(self.root,check_only=True)
        self.assertEqual(first,second);self.assertEqual(first['native_trials'],36)
        self.assertTrue((self.root/'analysis/order_effects.csv').is_file())
        self.assertTrue((self.root/'analysis/readouts.csv').is_file())
        self.assertEqual(len(io.load(self.root/'analysis/summary.json')['input_isolation']),6)
    def test_stream_tail_refused_even_when_resealed(self):
        with (self.root/'attempts.jsonl').open('a') as f:f.write('{}\n')
        self.seal()
        with self.assertRaises(ValueError):audit.verify_raw(self.root)
    def test_stream_event_change_refused_even_when_resealed(self):
        p=self.root/'attempts.jsonl';lines=p.read_text().splitlines();lines[0]='{}';p.write_text('\n'.join(lines)+'\n');self.seal()
        with self.assertRaises(ValueError):audit.verify_raw(self.root)
    def test_missing_raw_refused(self):
        (self.root/'raw/t0000.json').unlink()
        with self.assertRaises(ValueError):audit.verify_raw(self.root)
    def test_raw_checksum_failure_preserved(self):
        (self.root/'raw/t0000.json').write_text('{}')
        with self.assertRaises(ValueError):audit.write_analysis(self.root)
        self.assertEqual(len(list((self.root/'audit_failures').glob('*.json'))),1)
    def test_analysis_tampering_not_repaired(self):
        audit.write_analysis(self.root);p=self.root/'analysis/summary.ko.md';p.write_text('tampered')
        with self.assertRaises(ValueError):audit.write_analysis(self.root,check_only=True)
        self.assertEqual(p.read_text(),'tampered')
    def test_analysis_overwrite_refused(self):
        audit.write_analysis(self.root)
        with self.assertRaises(FileExistsError):audit.write_analysis(self.root)
