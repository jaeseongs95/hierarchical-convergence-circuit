"""R0.2 의존 확장·부분회로 경쟁·학습·오류 수정 수용 시험."""
from copy import deepcopy
from dataclasses import replace
from unittest.mock import patch
import unittest
from hcr import codec
from hcr.model import (AdaptiveConfig, AdaptiveCost, Config, ContractError, ExpansionLimit, EdgeObservation,
                       Observation, Mode, Feedback, Status, ExpansionBudget, MismatchSignal)
from hcr.circuits import AdaptiveMemory
from hcr.runtime import AdaptiveEngine
from hcr.workspace import AdaptiveWorkspace, ExpansionCandidate
from hcr.activation import CircuitActivationPool
from hcr.expansion import DeterministicExpansionPolicy
from hcr.identity import bind_path
from hcr.trace import Trace
from hcr.tasks.toy_world import chain, diamond
from hcr.evaluation.reference import assess
from r02_helpers import train_r02, report_feedback, r02_events


class AdaptiveRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.learned = train_r02()

    def test_cold_graph_grows_one_primitive_at_a_time(self):
        engine = AdaptiveEngine()
        world = chain('cold', (True, True, True))
        d = engine.infer(world.observation)
        self.assertTrue(assess(d, world.observation, dict(world.hidden)).correct)
        actions = r02_events(engine, 'r02_expansion')
        self.assertEqual([e['candidate']['source'] for e in actions], ['primitive'] * 3)
        self.assertEqual(d.cost['expansions'], 3)
        self.assertEqual(d.proof.primitive_depth, 3)

    def test_familiarity_compresses_dependency_search_not_proof_depth(self):
        world = chain('fresh-instance', (True, True, True), prefix='new-role')
        cold = AdaptiveEngine().infer(world.observation)
        warm = AdaptiveEngine(memory=deepcopy(self.learned.memory)).infer(world.observation)
        self.assertIs(cold.value, True)
        self.assertEqual(warm.value, cold.value)
        self.assertTrue(warm.circuit_ids)
        self.assertLess(warm.cost['graph_nodes_created'], cold.cost['graph_nodes_created'])
        self.assertLess(warm.cost['expansions'], cold.cost['expansions'])
        self.assertEqual(warm.proof.primitive_depth, cold.proof.primitive_depth)
        self.assertGreater(warm.cost['binding_operations'], 0)
        self.assertGreater(warm.cost['pool_calls'], 0)

    def test_longer_novel_structure_combines_macro_and_expansion(self):
        world = chain('longer', (True, True, True, True), prefix='unseen-four')
        engine = AdaptiveEngine(memory=deepcopy(self.learned.memory))
        d = engine.infer(world.observation)
        self.assertTrue(assess(d, world.observation, dict(world.hidden)).correct)
        self.assertTrue(d.circuit_ids)
        self.assertEqual(d.proof.primitive_depth, 4)
        self.assertGreaterEqual(d.cost['expansions'], 2)
        self.assertEqual(d.expanded_paths, ((0, 1, 2, 3),))

    def test_rename_and_edge_permutation_keep_current_bindings(self):
        world = chain('permuted', (True, True, True), prefix='unseen')
        obs = replace(world.observation, edges=tuple(reversed(world.observation.edges)))
        d = AdaptiveEngine(memory=deepcopy(self.learned.memory)).infer(obs)
        self.assertTrue(assess(d, obs, dict(world.hidden)).correct)
        self.assertEqual(d.expanded_paths, ((2, 1, 0),))
        self.assertEqual(d.proof.primitive_depth, 3)

    def test_graph_only_does_not_scan_or_use_circuits(self):
        engine = AdaptiveEngine(memory=deepcopy(self.learned.memory), use_circuits=False)
        d = engine.infer(chain('graph-only', (True, True, True)).observation)
        self.assertFalse(d.circuit_ids)
        self.assertEqual(d.cost['pool_calls'], 0)
        self.assertEqual(d.cost['binding_operations'], 0)
        self.assertEqual(d.cost['expansions'], 3)

    def test_pool_uses_multiple_competing_candidates_and_common_kernel(self):
        from hcr import dynamics
        engine = AdaptiveEngine(memory=deepcopy(self.learned.memory))
        with patch.object(dynamics, 'tick', wraps=dynamics.tick) as tick:
            d = engine.infer(chain('pool', (True, True, True)).observation)
        pools = [p for p in r02_events(engine, 'r02_network') if p['kind'] == 'pool']
        self.assertTrue(pools)
        self.assertTrue(any(len(p['metadata']['candidates']) >= 2 for p in pools))
        self.assertTrue(any(link['weight'] < 0 and link['source'].startswith('c:') and link['target'].startswith('c:')
                            for p in pools for link in p['program']['links']))
        self.assertEqual(tick.call_count, d.cost['convergence_ticks'])

    def test_binding_budget_discards_partial_pool_and_falls_back(self):
        config = replace(AdaptiveConfig(), max_binding_checks=1)
        trained = train_r02(config=config)
        engine = AdaptiveEngine(config, deepcopy(trained.memory))
        d = engine.infer(chain('binding-budget', (True, True, True)).observation)
        self.assertIs(d.value, True)
        self.assertFalse(d.circuit_ids)
        self.assertEqual(d.cost['binding_operations'], 1)
        self.assertTrue(any(p['fallback_reason'] == 'binding_budget' for p in r02_events(engine, 'r02_binding_scan')))

    def test_pool_capacity_discards_incomplete_candidate_list(self):
        config = replace(AdaptiveConfig(), max_pool_candidates=1)
        trained = train_r02(config=config)
        engine = AdaptiveEngine(config, deepcopy(trained.memory))
        engine.infer(chain('pool-capacity', (True, True, True)).observation)
        scans = r02_events(engine, 'r02_binding_scan')
        self.assertTrue(any(s['fallback_reason'] == 'pool_capacity' for s in scans))
        first = r02_events(engine, 'r02_expansion')[0]
        self.assertEqual(first['candidate']['source'], 'primitive')

    def test_expansion_budget_abstains_without_fabricated_proof(self):
        config = replace(AdaptiveConfig(), max_expansions=1)
        d = AdaptiveEngine(config).infer(chain('budget', (True, True, True)).observation)
        self.assertIsNone(d.value)
        self.assertEqual(d.convergence.status, Status.BUDGET_EXHAUSTED)
        self.assertFalse(d.proof.nodes)
        self.assertFalse(d.graph_complete)

    def test_unknown_observations_do_not_turn_structural_bias_into_answer(self):
        d = AdaptiveEngine().infer(chain('unknown', (True, True, True), (None, None, None)).observation)
        self.assertIsNone(d.value)
        self.assertFalse(d.proof.nodes)

    def test_negative_answer_requires_all_dependencies(self):
        world = diamond('negative-coverage', (False, True, False, True))
        d = AdaptiveEngine().infer(world.observation)
        a = assess(d, world.observation, dict(world.hidden))
        self.assertIs(d.value, False)
        self.assertTrue(d.graph_complete)
        self.assertEqual(set(d.expanded_paths), {(0, 1), (2, 3)})
        self.assertTrue(a.proof_valid)
        self.assertTrue(a.correct)

    def test_first_negative_route_does_not_hide_positive_other_route(self):
        world = diamond('alternate', (False, True, True, True))
        engine = AdaptiveEngine()
        d = engine.infer(world.observation)
        self.assertIs(d.value, True)
        self.assertEqual(set(d.expanded_paths), {(0, 1), (2, 3)})
        self.assertTrue(assess(d, world.observation, dict(world.hidden)).correct)

    def test_positive_can_stop_before_unrelated_branch_is_expanded(self):
        world = diamond('early', (True, True, True, True))
        d = AdaptiveEngine().infer(world.observation)
        self.assertIs(d.value, True)
        self.assertFalse(d.graph_complete)
        self.assertTrue(assess(d, world.observation, dict(world.hidden)).proof_valid)

    def test_frozen_inference_never_mutates_memory(self):
        engine = AdaptiveEngine(memory=deepcopy(self.learned.memory))
        before = engine.memory.digest
        d = engine.infer(chain('frozen', (True, True, True)).observation)
        self.assertEqual(engine.memory.digest, before)
        with self.assertRaises(ContractError):
            engine.feedback(Feedback('bad-frozen-feedback', d.id, d.observation_digest, True, True))
        self.assertEqual(engine.memory.digest, before)

    def test_strong_counterfactual_is_not_an_answer_cache_hit(self):
        world = chain('closed', (False, True, True))
        d = AdaptiveEngine(memory=deepcopy(self.learned.memory)).infer(world.observation)
        self.assertIs(d.value, False)
        self.assertTrue(assess(d, world.observation, dict(world.hidden)).correct)

    def test_error_feedback_weakens_routing_without_editing_first_decision(self):
        engine = AdaptiveEngine(memory=deepcopy(self.learned.memory))
        world = chain('error-feedback', (True, True, True))
        d = engine.infer(world.observation, Mode.ADAPT)
        self.assertTrue(d.circuit_ids)
        saved = codec.dumps(d)
        before = {c.id: c.strength for c in engine.memory.circuits}
        # 외부 오류 통보의 상태 전이만 시험한다. 이것을 오수렴 실측으로 세지 않는다.
        engine.feedback(Feedback('synthetic-error', d.id, d.observation_digest, False, False, 'test_external_feedback'))
        for c in engine.memory.circuits:
            self.assertAlmostEqual(c.strength, before[c.id] * engine.config.kernel.weakening if c.id in d.circuit_ids else before[c.id])
        self.assertEqual(codec.dumps(d), saved)
        self.assertEqual(codec.dumps(r02_events(engine, 'r02_decision')[0]), saved)

    def test_revision_recomputes_from_requested_measurements(self):
        engine = AdaptiveEngine(memory=deepcopy(self.learned.memory))
        # 공개 관측에 측정 오류를 주고, 외부 평가는 실제 truth에 근거한다.
        world = chain('reopen', (False, True, True), (.6, .92, .92))
        initial = engine.infer(world.observation, Mode.ADAPT)
        self.assertIs(initial.value, True)
        a = report_feedback(engine, world, initial)
        self.assertIs(a.correct, False)
        request = engine.request_revision(initial.id)
        self.assertIsNotNone(request)
        observed = world.measure(request)
        later = engine.infer(observed, Mode.ADAPT, revision_of=initial.id)
        self.assertIs(later.value, False)
        self.assertEqual(later.attempt, 2)
        self.assertEqual(later.observation_revision, 1)
        self.assertFalse(later.circuit_ids)
        self.assertEqual(later.cost['observation_requests'], 1)
        self.assertTrue(assess(later, observed, dict(world.hidden)).correct)

    def test_no_reexpansion_ablation_does_not_revise(self):
        engine = AdaptiveEngine(allow_reexpansion=False)
        world = chain('no-reopen', (False, True), (.7, .92))
        d = engine.infer(world.observation, Mode.ADAPT)
        report_feedback(engine, world, d)
        self.assertIsNone(engine.request_revision(d.id))

    def test_unrequested_revision_is_rejected(self):
        engine = AdaptiveEngine()
        obs = chain('invalid-reopen').observation
        with self.assertRaises(ContractError):
            engine.infer(replace(obs, revision=1), Mode.ADAPT, revision_of='not-issued')

    def test_adaptive_decision_codec_roundtrip(self):
        d = AdaptiveEngine().infer(chain('codec', (True, True, True)).observation)
        self.assertEqual(codec.adaptive_decision_from(codec.plain(d)), d)


class WorkspaceSideBranchTests(unittest.TestCase):
    def make_workspace(self, config=None):
        # A→B→C→G 외에 macro 내부 B에서 D→G로 가는 별도 경로를 둔다.
        obs = Observation('side', 0, 'A', 'G', tuple(EdgeObservation('e' + str(i), a, b, .92)
            for i, (a, b) in enumerate((('A','B'), ('B','C'), ('C','G'), ('B','D'), ('D','G')))))
        return AdaptiveWorkspace(obs, config or AdaptiveConfig(), AdaptiveCost(), Trace(), 'test-side')

    def test_macro_keeps_side_branch_at_internal_role(self):
        workspace = self.make_workspace()
        b = bind_path(workspace.observation, 'motif', (0, 1, 2))
        workspace.apply(ExpansionCandidate((0, 1, 2), 'circuit', .9, 0., 'motif', b, .1, 1))
        self.assertEqual([p.path for p in workspace.routes], [(0, 1, 2)])
        self.assertEqual([p.path for p in workspace.frontier], [(0, 3)])
        self.assertFalse(workspace.complete)
        workspace.apply(ExpansionCandidate((4,)))
        self.assertEqual({p.path for p in workspace.routes}, {(0, 1, 2), (0, 3, 4)})
        self.assertTrue(workspace.complete)

    def test_invalid_macro_binding_leaves_graph_unmodified(self):
        workspace = self.make_workspace()
        b = bind_path(workspace.observation, 'motif', (0, 1))
        before = codec.dumps(workspace.frontier)
        with self.assertRaises(ContractError):
            workspace.apply(ExpansionCandidate((0, 3), 'circuit', .9, 0., 'motif', b, .1, 1))
        self.assertEqual(codec.dumps(workspace.frontier), before)
        self.assertEqual(workspace.cost.expansions, 0)

    def test_frontier_limit_does_not_silently_remove_alternative(self):
        world = diamond('branch-limit', (True, True, True, True))
        workspace = AdaptiveWorkspace(world.observation, replace(AdaptiveConfig(), max_frontier=1), AdaptiveCost(), Trace(), 'limit')
        before = codec.dumps(workspace.frontier)
        with self.assertRaises(ExpansionLimit):
            workspace.apply(ExpansionCandidate((0,)))
        self.assertEqual(codec.dumps(workspace.frontier), before)
        self.assertEqual(workspace.cost.expansions, 0)
