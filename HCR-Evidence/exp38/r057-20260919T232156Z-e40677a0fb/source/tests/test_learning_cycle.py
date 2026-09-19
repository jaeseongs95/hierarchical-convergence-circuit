from dataclasses import replace
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
import tempfile
import unittest
from helpers import trained,adapt
from hcr import codec
from hcr.model import Mode,Config,Feedback,ContractError,Status,Cost
from hcr.runtime import Engine
from hcr.circuits import Memory
from hcr.tasks.toy_world import chain
from hcr.evaluation.reference import assess,validate_proof


class LearningCycle(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.trained=trained().memory
    def test_empty_memory_not_preinstalled_circuit(self):
        e=Engine();self.assertEqual(e.memory.circuits,[]);d=e.infer(chain('x').observation)
        self.assertEqual(d.method,'graph_expansion');self.assertGreater(d.cost['dynamic_groups_created'],0)
    def test_compilation_requires_three_distinct_verified_episodes(self):
        e=trained(2);self.assertEqual(len(e.memory.circuits),0);self.assertEqual(len(e.memory.pending),1)
        e=trained(3);self.assertEqual(len(e.memory.circuits),1);self.assertEqual(len(e.memory.pending),0)
    def test_repeated_feedback_does_not_count_twice(self):
        e=Engine();w=chain('x');d=e.infer(w.observation,Mode.TRAIN);a=assess(d,w.observation,dict(w.hidden))
        feedback=Feedback('f',d.id,d.observation_digest,a.correct,a.proof_valid);e.feedback(feedback)
        h=e.memory.digest
        with self.assertRaises(ContractError):e.feedback(feedback)
        self.assertEqual(h,e.memory.digest)
    def test_same_episode_cannot_be_relabelled_as_new_attempt(self):
        e=Engine();obs=chain('x').observation;e.infer(obs)
        with self.assertRaises(ContractError):e.infer(obs)
    def test_same_topology_new_names_reuses_real_program(self):
        e=Engine(memory=deepcopy(self.trained));d=e.infer(chain('new',prefix='never-seen').observation)
        self.assertEqual(d.method,'circuit_reuse');self.assertGreater(d.cost['signal_transmissions'],0)
        self.assertEqual(d.cost['search_edge_checks'],0);self.assertEqual(d.cost['dynamic_groups_created'],0)
    def test_reused_circuit_not_constant_answer_cache(self):
        e=Engine(memory=deepcopy(self.trained))
        positive=chain('a',(True,True),prefix='same');negative=chain('b',(False,True),prefix='same')
        d1=e.infer(positive.observation);d2=e.infer(negative.observation)
        self.assertEqual(d1.circuit_id,d2.circuit_id);self.assertIs(d1.value,True);self.assertIs(d2.value,False)
    def test_compiled_program_does_not_contain_previous_instance_names(self):
        p=codec.dumps(self.trained.circuits[0].program)
        self.assertNotIn('train-instance',p);self.assertNotIn('train-0',p)
    def test_frozen_eval_does_not_modify_memory(self):
        e=Engine(memory=deepcopy(self.trained));before=e.memory.digest
        for i in range(3):e.infer(chain('new'+str(i)).observation)
        self.assertEqual(before,e.memory.digest)
    def test_frozen_eval_cannot_accept_feedback(self):
        e=Engine(memory=deepcopy(self.trained));d=e.infer(chain('x').observation)
        with self.assertRaises(ContractError):e.feedback(Feedback('f',d.id,d.observation_digest,True,True))
    def test_feedback_before_decision_rejected(self):
        with self.assertRaises(ContractError):Engine().feedback(Feedback('f','unknown','0'*64,True,True))
    def test_changed_memory_without_version_increment_rejected(self):
        e=Engine(memory=deepcopy(self.trained));d=e.infer(chain('x').observation,Mode.TRAIN)
        e.memory.circuits[0].strength=.1
        with self.assertRaises(ContractError):e.feedback(Feedback('f',d.id,d.observation_digest,True,True))
    def test_decision_mutation_before_feedback_rejected(self):
        e=Engine();d=e.infer(chain('x').observation,Mode.TRAIN);d.cost['kernel_ticks']=0
        with self.assertRaises(ContractError):e.feedback(Feedback('f',d.id,d.observation_digest,True,True))
    def test_positive_label_without_valid_proof_not_compiled(self):
        e=Engine()
        for i in range(4):
            d=e.infer(chain('x'+str(i)).observation,Mode.TRAIN)
            e.feedback(Feedback('f'+str(i),d.id,d.observation_digest,True,False))
        self.assertEqual(e.memory.circuits,[]);self.assertEqual(e.memory.pending,[])
    def test_memory_save_reload_checks_provenance_and_structure(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'memory.json';self.trained.save(p);loaded=Memory.load(p,Config())
            self.assertEqual(loaded.digest,self.trained.digest)
            d=Engine(memory=loaded).infer(chain('new').observation);self.assertEqual(d.method,'circuit_reuse')
    def test_forged_program_rejected_even_with_updated_checksum(self):
        data=deepcopy(self.trained.document());data['circuits'][0]['program']['links'][0]['weight']=100
        with self.assertRaises(ContractError):Memory.from_document(data,Config())
    def test_memory_settings_mismatch_rejected(self):
        with self.assertRaises(ContractError):Memory.from_document(self.trained.document(),Config(top_down_gain=.2))
    def test_stable_incorrect_can_have_valid_proof_under_wrong_assumptions(self):
        e=Engine(memory=deepcopy(self.trained));w=chain('x',(False,True),(-.06,.92));d=e.infer(w.observation);a=assess(d,w.observation,dict(w.hidden))
        self.assertEqual(d.convergence.status,Status.STABLE_DECISION);self.assertFalse(a.correct)
        self.assertTrue(a.proof_valid);self.assertFalse(a.assumption_correct)
    def test_feedback_reopens_graph_and_retains_initial_error(self):
        e,w,first,a,later,b=adapt(self.trained)
        self.assertFalse(a.correct);self.assertTrue(b.correct);self.assertNotEqual(first.id,later.id)
        self.assertEqual(first.value,True);self.assertEqual(later.method,'graph_expansion')
        self.assertGreater(later.cost['dynamic_groups_created'],0);self.assertEqual(later.cost['observation_requests'],1)
    def test_new_measurement_only_after_feedback_and_in_allowed_slots(self):
        e=Engine(memory=deepcopy(self.trained));w=chain('x',(False,True),(-.06,.92));d=e.infer(w.observation,Mode.ADAPT)
        with self.assertRaises(ContractError):e.request_revision(d.id)
        e.feedback(Feedback('f',d.id,d.observation_digest,False,False));req=e.request_revision(d.id)
        self.assertEqual(req.edge_ids,(w.observation.edges[0].id,))
        obs=w.measure(req);bad=replace(obs,edges=(obs.edges[0],replace(obs.edges[1],score=-.98)))
        with self.assertRaises(ContractError):e.infer(bad,Mode.ADAPT,revision_of=d.id)
    def test_no_reexpansion_control_keeps_initial_decision_record(self):
        e,w,d,a,later,b=adapt(self.trained,reexpand=False)
        self.assertFalse(a.correct);self.assertIsNone(later)
        self.assertFalse(any(x['event']=='graph_expanded' for x in e.trace.records))
    def test_error_with_no_new_available_observation_not_forced_correct(self):
        e=Engine(memory=deepcopy(self.trained));w=chain('x',(True,True),(.98,.98));d=e.infer(w.observation,Mode.ADAPT)
        e.feedback(Feedback('f',d.id,d.observation_digest,False,False))
        self.assertIsNone(e.request_revision(d.id));self.assertIs(d.value,True)
    def test_corrected_measurement_does_not_immediately_restore_bad_prior(self):
        e,w,d,a,later,b=adapt(self.trained)
        self.assertAlmostEqual(e.memory.circuits[0].strength,self.trained.circuits[0].strength*Config().weakening)
        self.assertEqual(e.memory.circuits[0].negative,1)
    def test_relearning_persists_and_normal_case_remains_correct(self):
        e,*_=adapt(self.trained)
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'memory.json';e.memory.save(p);next_engine=Engine(memory=Memory.load(p,Config()))
            weak=chain('next-weak',(False,True),(-.06,.92));normal=chain('next-normal')
            self.assertIs(next_engine.infer(weak.observation).value,False)
            self.assertIs(next_engine.infer(normal.observation).value,True)
    def test_hidden_truth_not_read_during_inference(self):
        w=chain('x',(False,True),(-.06,.92));e=Engine(memory=deepcopy(self.trained))
        with patch('hcr.evaluation.reference.assess',side_effect=AssertionError('oracle leakage')),patch('hcr.evaluation.reference.reachable',side_effect=AssertionError('oracle leakage')):
            d=e.infer(w.observation)
        self.assertIs(d.value,True)
    def test_identical_public_input_does_not_reveal_changed_hidden_truth(self):
        w=chain('same',(True,True),(.1,.1));other=replace(w,hidden=tuple((eid,False) for eid,_ in w.hidden))
        a=Engine(memory=deepcopy(self.trained)).infer(w.observation)
        b=Engine(memory=deepcopy(self.trained)).infer(other.observation)
        self.assertEqual(a.state,b.state);self.assertEqual(a.value,b.value)
    def test_proof_depth_not_macro_call_count(self):
        cold=Engine().infer(chain('cold').observation);warm=Engine(memory=deepcopy(self.trained)).infer(chain('warm').observation)
        self.assertEqual(cold.proof.primitive_depth,warm.proof.primitive_depth);self.assertEqual(warm.proof.primitive_depth,2)
        self.assertGreater(warm.cost['signal_transmissions'],1)
    def test_missing_direct_premise_invalidates_proof(self):
        w=chain('x');d=Engine().infer(w.observation);nodes=list(d.proof.nodes)
        nodes[-1]=replace(nodes[-1],parents=nodes[-1].parents[:1])
        broken=replace(d.proof,nodes=tuple(nodes))
        self.assertFalse(validate_proof(broken,w.observation,True)[0])
    def test_final_boolean_does_not_repair_unsupported_graph(self):
        e=Engine(memory=deepcopy(self.trained),top_down=False);w=chain('x',(False,True),(-.06,.92));d=e.infer(w.observation);a=assess(d,w.observation,dict(w.hidden))
        self.assertIs(d.value,True);self.assertFalse(a.proof_valid)

    def test_decision_readout_precedes_explanation_without_repair(self):
        from hcr.model import Proof
        e=Engine();world=chain('x')
        with patch('hcr.runtime.reconstruct',return_value=Proof((),None,None,(),False)):
            d=e.infer(world.observation)
        self.assertIs(d.value,True);self.assertFalse(d.proof.under_assumptions_valid)
        events=[x['event'] for x in e.trace.records]
        self.assertLess(events.index('decision_readout'),events.index('explanation_reconstructed'))
        self.assertLess(events.index('explanation_reconstructed'),events.index('decision'))
