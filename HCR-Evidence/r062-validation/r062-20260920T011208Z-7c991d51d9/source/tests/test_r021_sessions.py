"""R0.2.1 동작 보존·거부 계약. 작은 symbolic 자체시험이며 새 연구 표본이 아니다."""
from __future__ import annotations
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from hcr import codec, session_io
from hcr.model import AdaptiveConfig, ContractError, Feedback, Mode, fingerprint
from hcr.runtime import AdaptiveEngine
from hcr.sessions import AdaptiveSession, verify_packet
from hcr.tasks.toy_world import chain, diamond
from hcr.evaluation.reference import assess
from r02_helpers import train_r02


def decision_content(d):
    raw = codec.plain(d)
    raw['cost'].pop('wall_seconds')
    return raw


def norm_events(events):
    result = []
    for e in events:
        p = deepcopy(e['payload'])
        if 'cost' in p:
            p['cost'].pop('wall_seconds', None)
        result.append(dict(seq=e['seq'], event=e['event'], payload=p))
    return result


def rehash(packet, *, core=False):
    """외피 hash뿐 아니라 tip state hash를 고쳐도 의미 검산이 변조를 잡는지 확인."""
    doc = packet['document']
    if core:
        t = doc['transitions'][-1]
        t['after_state'] = fingerprint(doc['engine'])
        t['sha256'] = fingerprint({k:v for k,v in t.items() if k != 'sha256'})
    packet['sha256'] = fingerprint(doc)
    return packet


class SessionBehavior(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.memory = train_r02().memory

    def equivalent(self, world, *, config=None, memory=None, flags=None):
        config = config or AdaptiveConfig()
        flags = flags or {}
        plain = AdaptiveEngine(config, deepcopy(memory), **flags)
        ref = plain.infer(world.observation)
        s = AdaptiveSession(config, deepcopy(memory), session_id='same', **flags)
        s.begin(world.observation)
        s = AdaptiveSession.from_packet(s.packet())
        while s.phase == 'running':
            s.advance()
            s = AdaptiveSession.from_packet(s.packet())
        # 판단과 proof 생성 사이를 실제로 나눈다.
        self.assertEqual(s.phase, 'readout_ready')
        self.assertEqual(s.current['held'], {})
        value = s.current['pending']['value']
        result = s.finish()
        self.assertIs(value, result.value)
        self.assertEqual(decision_content(ref), decision_content(result))
        self.assertEqual(plain.memory.document(), s.memory_document)
        self.assertEqual(norm_events(plain.trace.records), norm_events(s.events))
        self.assertTrue(verify_packet(s.packet())['verified'])
        return s, result

    def test_cold_resume_every_dependency(self):
        self.equivalent(chain('e',(True,True,True)))

    def test_familiar_resume_every_dependency(self):
        self.equivalent(chain('e',(True,True,True)), memory=self.memory)

    def test_counterfactual_not_cached_answer(self):
        _, d = self.equivalent(chain('e',(False,True,True)), memory=self.memory)
        self.assertIs(d.value, False)

    def test_longer_macro_plus_expansion(self):
        self.equivalent(chain('e',(True,)*4), memory=self.memory)

    def test_side_branch_survives_resume(self):
        self.equivalent(diamond('e',(False,True,True,True)), memory=self.memory)

    def test_all_negative_dependency_coverage(self):
        _, d = self.equivalent(diamond('e',(False,True,False,True)), memory=self.memory)
        self.assertIs(d.value, False)
        self.assertTrue(d.graph_complete)

    def test_unknown_is_not_forced_correct(self):
        _, d = self.equivalent(chain('e',(True,True),(None,None)), flags={'use_circuits':False})
        self.assertIsNone(d.value)

    def test_budget_abstention_preserved(self):
        _, d = self.equivalent(chain('e',(True,)*3), config=replace(AdaptiveConfig(),max_expansions=1))
        self.assertIsNone(d.value)
        self.assertEqual(d.convergence.status.value,'budget_exhausted')

    def test_top_down_off_preserved(self):
        self.equivalent(chain('e',(True,)*3), memory=self.memory,flags={'top_down':False})

    def test_empty_route_dead_end(self):
        w=chain('e',(True,));w=replace(w,observation=replace(w.observation,start='v-1',goal='v-0'))
        _,d=self.equivalent(w)
        self.assertIsNone(d.value)

    def test_training_changes_memory_after_snapshot_only(self):
        s=AdaptiveSession();e=AdaptiveEngine()
        for i in range(4):
            w=chain('t'+str(i),(True,)*3)
            s.begin(w.observation,Mode.TRAIN);s=AdaptiveSession.from_packet(s.packet());d=s.complete()
            dr=e.infer(w.observation,Mode.TRAIN)
            self.assertEqual(decision_content(d),decision_content(dr))
            f=Feedback('f-'+d.id,d.id,w.observation.digest,True,True)
            s.feedback(f);e.feedback(f);s=AdaptiveSession.from_packet(s.packet())
            self.assertEqual(e.memory.document(),s.memory_document)

    def test_weak_error_request_revision_and_retention_preserved(self):
        s=AdaptiveSession(memory=deepcopy(self.memory))
        w=chain('weak',(False,True,True),(-.06,.92,.92))
        s.begin(w.observation,Mode.ADAPT);d=s.complete()
        self.assertIs(d.value,True)
        self.assertEqual(d.circuit_ids,('pattern-ac8909863fce4682a84bf769',))
        s.feedback(Feedback('f-'+d.id,d.id,w.observation.digest,False,False))
        s=AdaptiveSession.from_packet(s.packet())
        req=s.request_revision(d.id)
        s=AdaptiveSession.from_packet(s.packet())
        revised=replace(w.observation,revision=req.revision)  # same-score control
        s.begin(revised,Mode.ADAPT,revision_of=d.id)
        s=AdaptiveSession.from_packet(s.packet());d2=s.complete()
        self.assertIs(d2.value,False);self.assertEqual(d2.circuit_ids,())
        self.assertEqual(d2.cost['kernel_ticks'],39)
        s.feedback(Feedback('f-'+d2.id,d2.id,revised.digest,True,True))
        s=AdaptiveSession.from_packet(s.packet())
        fresh=replace(w.observation,episode_id='weak-next')
        s.begin(fresh);d3=s.complete()
        self.assertIs(d3.value,True)
        self.assertEqual(d3.circuit_ids,('pattern-d7053e8a62ed20d50b15444c',))
        self.assertIn(d.id,s.current['held'])
        self.assertFalse(s.memory_document['patches'][-1]['changes'])
        self.assertTrue(verify_packet(s.packet())['verified'])

    def test_request_disabled_keeps_noop_generation(self):
        s=AdaptiveSession(memory=deepcopy(self.memory),allow_reexpansion=False)
        w=chain('w',(False,True,True),(-.06,.92,.92))
        s.begin(w.observation,Mode.ADAPT);d=s.complete()
        s.feedback(Feedback('f-'+d.id,d.id,w.observation.digest,False,False))
        n=len(s.events);self.assertIsNone(s.request_revision(d.id))
        self.assertEqual(n,len(s.events));verify_packet(s.packet())

    def test_generation_is_not_kernel_tick_or_revision(self):
        s=AdaptiveSession();w=chain('e',(True,True,True));s.begin(w.observation)
        while s.phase=='running':s.advance()
        p=s.current['pending']
        self.assertEqual(s.generation,4)
        self.assertEqual(p['observation']['revision'],0)
        self.assertGreater(p['cost']['kernel_ticks'],s.generation)

    def test_failed_transition_is_atomic(self):
        s=AdaptiveSession();s.begin(chain('x',(True,)*3).observation)
        before=s.packet()
        with self.assertRaises(ContractError):s.finish()
        self.assertEqual(before,s.packet())
        with self.assertRaises(ContractError):s.begin(chain('y').observation)
        self.assertEqual(before,s.packet())

    def test_runtime_exception_does_not_commit_partial_step(self):
        s=AdaptiveSession();s.begin(chain('x',(True,)*3).observation);before=s.packet()
        def crash(ws,c):
            ws.frontier.clear();ws.cost.expansions+=1
            raise RuntimeError('injected implementation failure')
        with patch('hcr.workspace.AdaptiveWorkspace.apply',crash),self.assertRaises(RuntimeError):s.advance()
        self.assertEqual(before,s.packet())

    def test_frozen_feedback_rejected_after_resume(self):
        s=AdaptiveSession();o=chain('a').observation;s.begin(o);d=s.complete();s=AdaptiveSession.from_packet(s.packet())
        before=s.packet()
        with self.assertRaises(ContractError):s.feedback(Feedback('f',d.id,o.digest,True,True))
        self.assertEqual(before,s.packet())

    def test_duplicate_feedback_rejected_after_resume(self):
        s=AdaptiveSession();o=chain('a').observation;s.begin(o,Mode.TRAIN);d=s.complete()
        f=Feedback('f',d.id,o.digest,True,True);s.feedback(f);s=AdaptiveSession.from_packet(s.packet())
        with self.assertRaises(ContractError):s.feedback(f)

    def test_unrequested_revision_rejected(self):
        s=AdaptiveSession();o=chain('a').observation;s.begin(o,Mode.ADAPT);d=s.complete();s=AdaptiveSession.from_packet(s.packet())
        with self.assertRaises(ContractError):s.begin(replace(o,revision=1),Mode.ADAPT,revision_of=d.id)

    def test_pending_memory_mutation_rejected(self):
        s=AdaptiveSession(memory=deepcopy(self.memory));s.begin(chain('a').observation)
        s._engine.memory.circuits[0].strength+=.01
        with self.assertRaises(ContractError):s.advance()
        with self.assertRaises(ContractError):s.packet()

    def test_returned_data_is_not_live_state(self):
        s=AdaptiveSession();s.begin(chain('x').observation);p=s.packet();p['document']['engine']['attempts'].clear()
        self.assertTrue(s.current['attempts']);verify_packet(s.packet())


class SnapshotTampering(unittest.TestCase):
    def setUp(self):
        self.s=AdaptiveSession(session_id='test');self.s.begin(chain('a',(True,)*3).observation);self.s.advance()
        self.packet=self.s.packet()

    def rejected(self, mutation, core=True):
        p=deepcopy(self.packet);mutation(p['document']);rehash(p,core=core)
        with self.assertRaises(ContractError):AdaptiveSession.from_packet(p)

    def test_frontier_loss_even_after_rehash(self):
        self.rejected(lambda d:d['engine']['pending']['workspace']['frontier'].clear())

    def test_node_identity_mutation(self):
        self.rejected(lambda d:d['engine']['pending']['workspace']['frontier'][0]['node'].update(node_id='other'))

    def test_semantic_identity_mutation(self):
        self.rejected(lambda d:d['engine']['pending']['workspace']['frontier'][0]['node'].update(semantic_id='other'))

    def test_stale_node_revision(self):
        self.rejected(lambda d:d['engine']['pending']['workspace']['frontier'][0]['node'].update(revision=1))

    def test_next_node_counter(self):
        self.rejected(lambda d:d['engine']['pending']['workspace'].update(next_node=999))

    def test_visited_set_mutation(self):
        self.rejected(lambda d:d['engine']['pending']['workspace']['frontier'][0]['visited'].append('fake'))

    def test_known_paths_mutation(self):
        self.rejected(lambda d:d['engine']['pending']['workspace']['known'].clear())

    def test_primitive_count_mutation(self):
        self.rejected(lambda d:d['engine']['pending']['cost'].update(expansions=0))

    def test_alias_count_mutation(self):
        self.rejected(lambda d:d['engine']['pending']['cost'].update(signal_events=33))

    def test_false_readout_ready(self):
        self.rejected(lambda d:d['engine']['pending'].update(ready=True,value=True))

    def test_revision_authorization_mutation(self):
        self.rejected(lambda d:d['engine']['requests'].update(fake={'decision_id':'fake'}))

    def test_runtime_flags_mutation(self):
        self.rejected(lambda d:d['engine']['switches'].update(use_circuits=False))

    def test_generation_ancestry_mutation(self):
        self.rejected(lambda d:d['transitions'][-1].update(previous='0'*64))

    def test_generation_boundary_mutation(self):
        self.rejected(lambda d:d['transitions'][-1].update(event_start=0))

    def test_injected_unknown_generation(self):
        self.rejected(lambda d:d['transitions'][-1].update(operation='answer_fix'))

    def test_event_truncation(self):
        self.rejected(lambda d:d['events'].pop())

    def test_program_mismatch(self):
        self.s.complete();self.packet=self.s.packet()
        self.rejected(lambda d:next(iter(d['engine']['held'].values()))['decision'].update(program_digest='0'*64))

    def test_wrong_external_reference(self):
        self.s.advance()
        with self.assertRaises(ContractError):AdaptiveSession.from_packet(self.packet,expected_ref=self.s.reference)

    def test_wrong_external_observation(self):
        with self.assertRaises(ContractError):AdaptiveSession.from_packet(self.packet,expected_observation=chain('another').observation)

    def test_wrong_external_memory(self):
        with self.assertRaises(ContractError):AdaptiveSession.from_packet(self.packet,expected_memory_hash='0'*64)

    def test_wrong_external_program(self):
        with self.assertRaises(ContractError):AdaptiveSession.from_packet(self.packet,expected_program_digest='0'*64)

    def test_source_mismatch(self):
        p=deepcopy(self.packet);p['document']['source_hashes']['src/hcr/runtime.py']='0'*64;rehash(p)
        with self.assertRaises(ContractError):AdaptiveSession.from_packet(p)

    def test_restore_cannot_disable_source_check(self):
        with self.assertRaises(ContractError):AdaptiveSession.from_packet(self.packet,check_source=False)

    def test_memory_null_tamper(self):
        self.rejected(lambda d:d['engine'].update(memory=None))


class CheckpointIO(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='상태 검증 ');self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.s=AdaptiveSession();self.s.begin(chain('o',(True,)*3).observation);self.s.advance()

    def test_save_restore_keeps_reference_and_counters(self):
        p=self.root/'a.json';reference=self.s.reference;self.s.save(p)
        restored=AdaptiveSession.load(p,expected_ref=reference)
        self.assertEqual(self.s.packet(),restored.packet())
        self.assertEqual(reference,restored.reference)
        self.assertGreater(self.s.last_io['bytes'],0)

    def test_existing_checkpoint_unchanged(self):
        p=self.root/'a.json';self.s.save(p);before=p.read_bytes()
        with self.assertRaises(FileExistsError):self.s.save(p)
        self.assertEqual(before,p.read_bytes())

    def test_relocated_checkpoint(self):
        p=self.root/'a.json';self.s.save(p);q=self.root/'moved'/'b.json';q.parent.mkdir();p.rename(q)
        self.assertEqual(self.s.packet(),AdaptiveSession.load(q).packet())

    def test_source_path_independent(self):
        self.assertNotIn(str(session_io.project_root()),codec.dumps(self.s.packet()))

    def test_utf8_lf_stable_bytes(self):
        p=self.root/'a.json';self.s.save(p);self.assertNotIn(b'\r\n',p.read_bytes())

    def test_publication_failure_leaves_no_partial_checkpoint(self):
        p=self.root/'a.json';before=self.s.packet()
        with patch('hcr.session_io.os.link',side_effect=OSError('no hardlink')),self.assertRaises(OSError):self.s.save(p)
        self.assertFalse(p.exists());self.assertEqual(list(self.root.iterdir()),[]);self.assertEqual(before,self.s.packet())

    def test_repository_evidence_path_allowed(self):
        with patch('hcr.session_io.project_root',return_value=self.root), patch('hcr.session_io.source_hashes',return_value=self.s._sources):
            self.s.save(self.root/'HCR-Evidence'/'exp10'/'one.json')
            with self.assertRaises(ContractError):self.s.save(self.root/'src'/'bad.json')

    def test_symlink_parent_rejected(self):
        link=self.root/'link';target=self.root/'target';target.mkdir()
        try:link.symlink_to(target,target_is_directory=True)
        except OSError:self.skipTest('symlink creation is not available')
        with self.assertRaises(ContractError):self.s.save(link/'bad.json')

    def test_file_symlink_rejected(self):
        p=self.root/'a.json';self.s.save(p);link=self.root/'link.json'
        try:link.symlink_to(p)
        except OSError:self.skipTest('symlink creation is not available')
        with self.assertRaises(ContractError):AdaptiveSession.load(link)

    def test_duplicate_json_keys_rejected(self):
        p=self.root/'bad.json';p.write_bytes(b'{"schema":1,"schema":2}')
        with self.assertRaises(ContractError):AdaptiveSession.load(p)

    def test_truncated_checkpoint_rejected(self):
        p=self.root/'bad.json';p.write_bytes(codec.dumps(self.s.packet()).encode()[:100])
        with self.assertRaises(ContractError):AdaptiveSession.load(p)


class AdditionalBoundaries(unittest.TestCase):
    equivalent = SessionBehavior.equivalent

    @classmethod
    def setUpClass(cls):
        cls.memory = train_r02().memory

    def test_signal_group_budget_after_expansion(self):
        config=replace(AdaptiveConfig(),kernel=replace(AdaptiveConfig().kernel,max_groups=4))
        _,d=self.equivalent(chain('e',(True,)*3),config=config)
        self.assertIsNone(d.value)

    def test_frontier_capacity_preserves_failure(self):
        config=replace(AdaptiveConfig(),max_frontier=1)
        _,d=self.equivalent(diamond('e'),config=config)
        self.assertIsNone(d.value)

    def test_binding_budget_fallback_preserves_costs(self):
        config=replace(AdaptiveConfig(),max_binding_checks=1)
        engine=train_r02(config=config)
        self.equivalent(chain('e',(True,)*3),config=config,memory=engine.memory)

    def test_ready_snapshot_signal_tamper_rejected(self):
        s=AdaptiveSession();s.begin(chain('e',(True,)*3).observation)
        while s.phase=='running':s.advance()
        p=s.packet();p['document']['engine']['pending']['state']['e:0']=.1;rehash(p,core=True)
        with self.assertRaises(ContractError):AdaptiveSession.from_packet(p)

    def test_cost_pause_not_counted_as_inference(self):
        from unittest.mock import patch
        s=AdaptiveSession();s.begin(chain('e',(True,)*3).observation)
        before=s.current['pending']['active_seconds']
        with patch('hcr.runtime.perf_counter',side_effect=[10000.,10000.001]):s.advance()
        self.assertAlmostEqual(s.current['pending']['active_seconds']-before,.001,places=7)

