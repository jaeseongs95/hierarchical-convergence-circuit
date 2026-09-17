"""입출력/검산 배선 시험. NativeTrial·native audit는 명시적인 test double이다."""
import unittest
from unittest.mock import patch
from contextlib import ExitStack
from pathlib import Path
from tempfile import TemporaryDirectory
from copy import deepcopy
from r036_helpers import view,candidate,mock_rebuild
from r035_frozen_selection import storage as io
from r035_frozen_selection.contracts import digest
from r036_input_representation import protocol,verification,spec
from r036_input_representation.audit import check_readouts


class ProtocolTests(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory();self.root=Path(self.tmp.name);self.source=self.root/'source';self.repo=self.root/'repo'
        self.source.mkdir();self.repo.mkdir();self.run=self.root/'run';self.view=view();self.cand=candidate(self.view)
        self.core=dict(memory={'synthetic_memory':True},config={'synthetic_config':True})
        self.case=dict(name='synthetic',family='test_only',observation=self.view['observation'],worlds={'one':dict(e0=True,e1=True,e2=False,e3=True)})
        old=dict(schema='hcr-exp15-plan-v1',conditions=dict(cases=[self.case]))
        io.put(self.source/'plan.json',old);io.put(self.source/'training.json',[])
        seed=dict(document=dict(engine=self.core));seed['sha256']=digest(seed['document']);io.put(self.source/'seed/6.json',seed)
        manifest=dict(schema='hcr-exp15-raw-manifest-v1',state='raw_complete',files={n:io.file_hash(self.source/n) for n in ('plan.json','training.json','seed/6.json')})
        io.put(self.source/'manifest.json',manifest)
        public=spec.public_cases(old);self.plan=dict(schema='hcr-exp17-plan-v1',conditions=spec.conditions(),cases=public,
            trials=spec.trials(public)[:1],source_run=str(self.source),upstream_file_hashes={n:io.file_hash(self.source/n) for n in protocol.sources.UPSTREAM_FILES},
            memory_sha256=digest(self.core['memory']),config_sha256=digest(self.core['config']),dependency_source_hashes={},addon_source_hashes={})
        self.stack=ExitStack();self.addCleanup(self.stack.close);self.addCleanup(self.tmp.cleanup)
        self.stack.enter_context(patch.object(protocol,'validate_plan',side_effect=lambda p,*a,**kw:self.source if kw.get('check_upstream',True) else None))
        self.stack.enter_context(patch.object(protocol.sources,'repo_root',return_value=self.repo))
        self.stack.enter_context(patch.object(protocol,'project',return_value=deepcopy(self.view)))
        self.stack.enter_context(patch('r035_frozen_selection.native_bridge.rebuild',side_effect=mock_rebuild))
        outer=self
        class FakeNativeTrial:
            def __init__(s,observation,config,memory,scope,max_initial,limits,event_sink=None):
                outer.args=(observation,config,memory,scope);s.sink=event_sink
            def run(s):return dict(status='readout_ready',flow=dict(candidates=[outer.cand]))
            def partial_evidence(s):return {'synthetic_partial':True}
        self.worker=self.stack.enter_context(patch.object(protocol,'NativeTrial',FakeNativeTrial))
        self.stack.enter_context(patch.object(verification,'check_seed',return_value=(self.core,old,{'synthetic_audit':True})))
        report=dict(status='readout_ready',stop_reason='stop_frontier_exhausted',kernel_ticks=102,extra_kernel_ticks=34,advances=2)
        self.stack.enter_context(patch.object(verification,'check_native',return_value=(report,[self.view],[])))

    def generate(self):return protocol.generate(self.plan,self.run)
    def rehash(self,name):
        m=io.load(self.run/'manifest.json');m['files'][name]=io.file_hash(self.run/name)
        (self.run/'manifest.json').unlink();io.put(self.run/'manifest.json',m)
    def rewrite(self,name,obj):
        path=self.run/name;path.unlink();io.put(path,obj);self.rehash(name)
    def test_generate_audit_verify_pipeline(self):
        self.generate();a=verification.write_analysis(self.run);self.assertTrue(a['verified'])
        self.assertEqual(verification.write_analysis(self.run,check_only=True),a)
    def test_native_receives_only_public_observation(self):
        self.generate();self.assertEqual(set(self.args[0]),{'episode_id','revision','start','goal','edges'})
        self.assertNotIn('worlds',self.args[0])
    def test_raw_first_attempts_present(self):
        self.generate();log=[io.loads(x) for x in io.read(self.run/'attempts.jsonl').decode().splitlines()]
        self.assertEqual(log[0]['event'],'trial_started');self.assertEqual(log[-1]['event'],'trial_completed')
    def test_existing_run_not_overwritten(self):
        self.generate()
        with self.assertRaises(FileExistsError):self.generate()
    def test_analysis_not_overwritten(self):
        self.generate();verification.write_analysis(self.run)
        with self.assertRaises(FileExistsError):verification.write_analysis(self.run)
    def test_source_untouched(self):
        old={n:io.file_hash(self.source/n) for n in io.inventory(self.source)};self.generate()
        self.assertEqual(old,{n:io.file_hash(self.source/n) for n in io.inventory(self.source)})
    def test_nested_output_rejected(self):
        with self.assertRaises(ValueError):protocol.generate(self.plan,self.source/'nested')
        self.assertFalse((self.source/'nested').exists())
    def test_failure_preserves_partial_and_does_not_retry(self):
        count=[]
        def fail(s):count.append(1);raise RuntimeError('synthetic failure')
        with patch.object(protocol.NativeTrial,'run',fail):
            with self.assertRaises(RuntimeError):self.generate()
        f=io.load(self.run/'failure.json');self.assertEqual(len(count),1)
        self.assertTrue(f['partial_evidence']['synthetic_partial']);self.assertFalse(f['automatic_retry'])
        self.assertFalse((self.run/'manifest.json').exists())
    def test_rehashed_bad_transform_detected(self):
        self.generate();r=io.load(self.run/'raw/t0000.json');r['transformed']['observation']['edges'][0]['score']=-.8
        self.rewrite('raw/t0000.json',r)
        with self.assertRaises(ValueError):verification.verify_raw(self.run)
    def test_rehashed_bad_selector_detected(self):
        self.generate();r=io.load(self.run/'raw/t0000.json');r['readouts'][0]['results']['support_first']['proof']['primitive_depth']=77
        self.rewrite('raw/t0000.json',r)
        with self.assertRaises(ValueError):verification.verify_raw(self.run)
    def test_rehashed_bad_stream_detected(self):
        self.generate();p=self.run/'attempts.jsonl';rows=io.read(p).decode().splitlines();rows=rows[:-1]
        p.unlink();io.put_bytes(p,('\n'.join(rows)+'\n').encode());self.rehash('attempts.jsonl')
        with self.assertRaises(ValueError):verification.verify_raw(self.run)
    def test_extra_file_rejected(self):
        self.generate();io.put(self.run/'raw/extra.json',{})
        with self.assertRaises(ValueError):verification.verify_raw(self.run)
    def test_empty_population_not_hidden(self):
        self.generate();r=io.load(self.run/'raw/t0000.json');r['readouts']=[];self.rewrite('raw/t0000.json',r)
        with self.assertRaises(ValueError):verification.verify_raw(self.run)
    def test_summary_tampering_detected(self):
        self.generate();verification.write_analysis(self.run);p=self.run/'analysis/summary.json';s=io.load(p);s['native_trials']=0;p.unlink();io.put(p,s)
        with self.assertRaises(ValueError):verification.write_analysis(self.run,check_only=True)
    def test_manifest_missing_raw_rejected(self):
        self.generate();(self.run/'raw/t0000.json').unlink()
        with self.assertRaises((ValueError,OSError)):verification.verify_raw(self.run)
