"""R0.2 신규 계약·역할 동일성·구조 컴파일러 회귀 시험."""
import ast
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
from hcr import codec
from hcr.model import AdaptiveConfig, AdaptiveCost, Config, ContractError, Mode, Feedback, ExpansionBudget, MismatchSignal
from hcr.identity import bind_path, binding_from, NodeRef
from hcr.patterns import make_pattern, pattern_from
from hcr.circuits import AdaptiveMemory, Memory
from hcr.runtime import AdaptiveEngine
from hcr.cli import adaptive_config_from
from hcr.tasks.toy_world import chain
from r02_helpers import train_r02, report_feedback


class AdaptiveContracts(unittest.TestCase):
    def test_bad_adaptive_budget_rejected(self):
        for raw in ({'max_expansions': 0}, {'max_binding_checks': True}, {'max_frontier': -1},
                    {'max_pool_candidates': 5}, {'pattern_lengths': (3, 2)},
                    {'pattern_lengths': (1,)}, {'activation_threshold': 1}, {'mismatch_threshold': float('nan')}):
            with self.subTest(raw=raw), self.assertRaises(ContractError):
                AdaptiveConfig(**raw)

    def test_adaptive_config_codec_roundtrip(self):
        config = AdaptiveConfig()
        self.assertEqual(codec.adaptive_config_from(codec.plain(config)), config)

    def test_toml_defaults_match_contract(self):
        root = Path(__file__).resolve().parents[1]
        self.assertEqual(adaptive_config_from(root / 'configs/r02.toml'), AdaptiveConfig())

    def test_configuration_unknown_field_rejected(self):
        raw = codec.plain(AdaptiveConfig())
        raw['ground_truth'] = True
        with self.assertRaises(ContractError):
            codec.adaptive_config_from(raw)

    def test_public_observation_rejects_labels(self):
        raw = codec.plain(chain('a').observation)
        for key in ('truth', 'novelty', 'holdout', 'expected_goal'):
            with self.subTest(key=key), self.assertRaises(ContractError):
                codec.observation_from(dict(raw, **{key: True}))

    def test_budget_and_mismatch_ranges(self):
        for factory in (lambda: ExpansionBudget(-1, 2, 3), lambda: MismatchSignal('x', float('nan'))):
            with self.assertRaises(ContractError):
                factory()

    def test_engine_requires_typed_configuration(self):
        with self.assertRaises(ContractError):
            AdaptiveEngine(Config())

    def test_cost_aliases_preserve_primitive_counters(self):
        cost = AdaptiveCost(signal_transmissions=7, kernel_ticks=3, proof_nodes_reconstructed=5, storage_bytes=20)
        result = cost.snapshot()
        self.assertEqual((result['signal_events'], result['convergence_ticks'], result['proof_reconstruction_cost'], result['storage_cost']), (7, 3, 5, 20))
        self.assertEqual(result['signal_events'], result['signal_transmissions'])

    def test_r01_and_r02_memory_schemas_not_mixed(self):
        config = AdaptiveConfig()
        with self.assertRaises(ContractError):
            AdaptiveMemory.from_document(Memory().document(), config)
        with self.assertRaises(ContractError):
            Memory.from_document(AdaptiveMemory.empty(config).document(), config.kernel)

    def test_memory_configuration_mismatch_rejected(self):
        first = AdaptiveConfig()
        with self.assertRaises(ContractError):
            AdaptiveMemory.from_document(AdaptiveMemory.empty(first).document(), replace(first, max_expansions=7))

    def test_new_engine_modules_do_not_import_external_truth(self):
        root = Path(__file__).resolve().parents[1] / 'src/hcr'
        for name in ('activation', 'expansion', 'identity', 'patterns', 'runtime', 'compiler', 'learning', 'workspace'):
            tree = ast.parse((root / (name + '.py')).read_text(encoding='utf-8'))
            imports = [node.module or '' for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
            self.assertFalse(any('evaluation' in n or 'toy_world' in n for n in imports), name)

    def test_auditor_does_not_call_production_algorithm(self):
        root = Path(__file__).resolve().parents[1] / 'src/hcr/evaluation'
        forbidden = {'runtime', 'dynamics', 'expansion', 'activation', 'learning', 'workspace', 'adaptive_protocol'}
        for name in ('adaptive_audit.py', 'adaptive_audit_support.py'):
            tree = ast.parse((root / name).read_text(encoding='utf-8'))
            modules = [node.module or '' for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
            self.assertFalse(forbidden.intersection(modules))


class RoleIdentityContracts(unittest.TestCase):
    def test_binding_roundtrip(self):
        obs = chain('a', (True, True, True)).observation
        binding = bind_path(obs, 'p', (0, 1))
        self.assertEqual(binding_from(codec.plain(binding)), binding)
        binding.check(obs, 2)

    def test_revision_cannot_reuse_old_binding(self):
        obs = chain('a').observation
        binding = bind_path(obs, 'p', (0, 1))
        with self.assertRaises(ContractError):
            binding.check(replace(obs, revision=1), 2)

    def test_same_semantic_can_have_different_node_id(self):
        obs = chain('a', (True, True, True)).observation
        a, b = bind_path(obs, 'p2', (0, 1)), bind_path(obs, 'p3', (0, 1, 2))
        self.assertEqual(a.roles[0][1].semantic_id, b.roles[0][1].semantic_id)
        self.assertNotEqual(a.roles[0][1].node_id, b.roles[0][1].node_id)

    def test_observation_change_invalidates_binding(self):
        obs = chain('a').observation
        binding = bind_path(obs, 'p', (0, 1))
        changed = replace(obs, edges=(replace(obs.edges[0], score=-.92), obs.edges[1]))
        with self.assertRaises(ContractError):
            binding.check(changed, 2)

    def test_noncontiguous_binding_rejected(self):
        obs = chain('a', (True, True, True)).observation
        with self.assertRaises(ContractError):
            bind_path(obs, 'p', (0, 2))

    def test_role_names_cannot_be_reordered(self):
        obs = chain('a').observation
        binding = bind_path(obs, 'p', (0, 1))
        with self.assertRaises(ContractError):
            replace(binding, roles=tuple(reversed(binding.roles))).check(obs, 2)

    def test_node_revision_contract(self):
        with self.assertRaises(ContractError):
            NodeRef('node', 'semantic', -1)


class SubgraphMemoryContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.trained = train_r02()

    def test_partial_patterns_compiled_after_distinct_episodes(self):
        self.assertEqual({c.pattern.length for c in self.trained.memory.circuits}, {2, 3})
        self.assertTrue(all(len(set(c.evidence_episodes)) >= 3 for c in self.trained.memory.circuits))

    def test_pattern_contains_roles_not_previous_instance_names_or_answers(self):
        for c in self.trained.memory.circuits:
            text = codec.dumps(c.pattern)
            self.assertNotIn('r02-obj-', text)
            self.assertNotIn('r02-train-', text)
            self.assertNotIn('answer', codec.plain(c.pattern))
            self.assertEqual(c.pattern.output_role, 'R' + str(c.pattern.length))

    def test_untrained_pattern_has_no_memory_presence(self):
        engine = train_r02(2)
        self.assertFalse(engine.memory.circuits)
        self.assertEqual(len(engine.memory.pending), 2)

    def test_structural_certificate_rejects_modified_link(self):
        config = AdaptiveConfig()
        raw = codec.plain(make_pattern(2, config.kernel))
        raw['program']['links'][0]['weight'] += .1
        with self.assertRaises(ContractError):
            pattern_from(raw, config.kernel)

    def test_memory_roundtrip_persistence(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'memory.json'
            self.trained.memory.save(p)
            self.assertEqual(AdaptiveMemory.load(p, self.trained.config).digest, self.trained.memory.digest)

    def test_same_episode_not_counted_twice(self):
        from copy import deepcopy
        memory = deepcopy(self.trained.memory)
        existing = memory.circuits[0].evidence_episodes[0]
        engine = AdaptiveEngine(self.trained.config, memory)
        world = chain(existing, (True, True, True), prefix='different-objects')
        lengths = {c.id: len(c.evidence_episodes) for c in memory.circuits}
        d = engine.infer(world.observation, Mode.TRAIN)
        report_feedback(engine, world, d)
        self.assertEqual(lengths, {c.id: len(c.evidence_episodes) for c in memory.circuits})

    def test_duplicate_feedback_and_inference_do_not_double_learn(self):
        engine = AdaptiveEngine()
        world = chain('duplicate', (True, True, True))
        d = engine.infer(world.observation, Mode.TRAIN)
        report_feedback(engine, world, d, identity='feedback-once')
        before = engine.memory.digest
        with self.assertRaises(ContractError):
            engine.feedback(Feedback('feedback-once', d.id, d.observation_digest, True, True))
        with self.assertRaises(ContractError):
            engine.infer(world.observation, Mode.TRAIN)
        self.assertEqual(engine.memory.digest, before)

    def test_mutated_evidence_is_rejected_even_after_rehash(self):
        doc = self.trained.memory.document()
        doc['circuits'][0]['evidence_episodes'].append(doc['circuits'][0]['evidence_episodes'][0])
        with self.assertRaises(ContractError):
            AdaptiveMemory.from_document(doc, self.trained.config)
