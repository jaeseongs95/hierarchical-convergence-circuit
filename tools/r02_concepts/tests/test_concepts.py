"""개념 추적/관측 보조 도구 계약 시험. HCR 실행이나 실제 연구 표본을 만들지 않는다."""
from __future__ import annotations
import ast
from copy import deepcopy
import importlib.util
from pathlib import Path
import tempfile
import unittest

HERE = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location('concept_tool_' + name, HERE / (name + '.py'))
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


check = load('check')
review = load('review')


class CoverageContracts(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / 'x.py').write_text('class X:\n    def step(self):\n        return 1\n', encoding='utf-8')
        (self.root / 'design.md').write_text('# Plan\nnot executed\n', encoding='utf-8')
        self.catalog = dict(schema='hcr-concept-coverage-v1', assessment_basis='source_review_not_research_proof',
            sources=[dict(id='S01', title='원문', sha256='a' * 64)], required_concepts=['K1'],
            concepts=[dict(id='K1', title='sample', status='implemented_scoped', scope='sample',
                remaining='future', stages=['R0.2'], sources=['S01'],
                anchors=[dict(path='x.py', kind='code', symbol='X.step')])])

    def run_check(self):
        return check.check_registry(self.root, self.catalog)

    def test_valid_catalog(self):
        self.assertTrue(self.run_check()['anchor_consistency_checked'])

    def test_does_not_claim_execution_or_semantics(self):
        r = self.run_check()
        self.assertFalse(r['tests_executed'])
        self.assertFalse(r['inference_executed'])
        self.assertFalse(r['semantics_proved'])

    def test_missing_symbol_rejected(self):
        self.catalog['concepts'][0]['anchors'][0]['symbol'] = 'X.unknown'
        with self.assertRaises(check.CoverageError): self.run_check()

    def test_changed_source_hash_rejected(self):
        self.catalog['concepts'][0]['anchors'][0]['normalized_sha256'] = 'f' * 64
        with self.assertRaises(check.CoverageError): self.run_check()

    def test_crlf_normalized_for_source_anchor(self):
        path = self.root / 'x.py'

        # 현재 플랫폼의 줄바꿈을 먼저 canonical LF로 만든다.
        lf = path.read_bytes().replace(b'\r\n', b'\n')

        a = self.catalog['concepts'][0]['anchors'][0]
        a['normalized_sha256'] = check.normalized_sha(lf)

        # canonical LF에서 정확히 CRLF를 만든다.
        path.write_bytes(lf.replace(b'\n', b'\r\n'))

        self.assertEqual(self.run_check()['concepts'], 1)

    def test_missing_required_concept_rejected(self):
        self.catalog['required_concepts'].append('K2')
        with self.assertRaises(check.CoverageError): self.run_check()

    def test_duplicate_concept_rejected(self):
        self.catalog['concepts'].append(deepcopy(self.catalog['concepts'][0]))
        with self.assertRaises(check.CoverageError): self.run_check()

    def test_unknown_source_rejected(self):
        self.catalog['concepts'][0]['sources'] = ['not-here']
        with self.assertRaises(check.CoverageError): self.run_check()

    def test_unknown_status_rejected(self):
        self.catalog['concepts'][0]['status'] = 'proved'
        with self.assertRaises(check.CoverageError): self.run_check()

    def test_implemented_needs_code_anchor(self):
        self.catalog['concepts'][0]['anchors'] = [dict(path='design.md', kind='design', contains='Plan')]
        with self.assertRaises(check.CoverageError): self.run_check()

    def test_planned_accepts_design(self):
        self.catalog['concepts'][0]['status'] = 'planned'
        self.catalog['concepts'][0]['anchors'] = [dict(path='design.md', kind='design', contains='Plan')]
        self.assertEqual(self.run_check()['status_counts'], {'planned': 1})

    def test_missing_design_anchor_rejected(self):
        self.catalog['concepts'][0]['anchors'].append(dict(path='design.md', kind='design', contains='missing'))
        with self.assertRaises(check.CoverageError): self.run_check()

    def test_path_traversal_rejected(self):
        with self.assertRaises(check.CoverageError): check.safe_path(self.root, '../bad.py')

    def test_windows_path_rejected(self):
        with self.assertRaises(check.CoverageError): check.safe_path(self.root, 'C:\\bad.py')

    def test_git_and_runs_not_anchors(self):
        for name in ('.git/config', 'runs/test.json'):
            with self.subTest(name=name), self.assertRaises(check.CoverageError):
                check.safe_path(self.root, name)

    def test_duplicate_json_rejected(self):
        p = self.root / 'bad.json'; p.write_text('{"a":1,"a":2}', encoding='utf-8')
        with self.assertRaises(check.CoverageError): check.load_json(p)

    def test_nonfinite_json_rejected(self):
        p = self.root / 'bad.json'
        for raw in ('{"a":NaN}', '{"a":1e9999}'):
            p.write_text(raw, encoding='utf-8')
            with self.subTest(raw=raw), self.assertRaises(check.CoverageError): check.load_json(p)

    def test_registry_checks_do_not_write(self):
        before = {p.name: p.read_bytes() for p in self.root.iterdir()}
        self.run_check()
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.root.iterdir()})


def fixture():
    obs = dict(episode_id='e', revision=0, start='a', goal='b',
               edges=[dict(id='edge0', source='a', target='b', score=.9)])
    decision = dict(id='d1', attempt=1, value=True, program_digest='p1',
        convergence=dict(status='stable_decision'),
        proof=dict(nodes=[dict(id='fact')], primitive_depth=1,
                   assumed_edges=[['edge0', True]], paths=[['edge0']]),
        cost=dict(proof_nodes_reconstructed=1, wall_seconds=.001))
    row = dict(phase='familiarity', arm='warm', case='fixture', observation=obs, decision=decision,
               assessment=dict(correct=True, wrong_stable=False, proof_valid=True, assumption_correct=True))
    events = [
        dict(seq=0, event='r02_attempt_started', payload=dict(decision_id='d1', observation=obs)),
        dict(seq=1, event='r02_network', payload=dict(decision_id='d1', network_id='n1',
             kind='decision', program_digest='p1', program=dict(paths=[[0]]))),
        dict(seq=2, event='r02_settled', payload=dict(decision_id='d1', network_id='n1')),
        dict(seq=3, event='r02_decision', payload=deepcopy(decision))]
    return row, events


class ReviewContracts(unittest.TestCase):
    def test_stable_wrong_observed_not_cause(self):
        row, _ = fixture(); row['assessment'].update(correct=False, wrong_stable=True)
        r = review.label_outcome(row['decision'], row['assessment'])
        self.assertIn('misconvergence', r['observed_labels'])
        self.assertIn('over_compression', r['causes_not_diagnosed'])

    def test_correct_value_is_not_a_failure(self):
        row, _ = fixture()
        self.assertEqual(review.label_outcome(row['decision'], row['assessment'])['observed_labels'], [])

    def test_no_candidate_is_not_activation_failure(self):
        row, _ = fixture(); row['decision']['value'] = None
        row['decision']['convergence']['status'] = 'no_candidate'
        row['assessment'].update(correct=None, proof_valid=False)
        r = review.label_outcome(row['decision'], row['assessment'])
        self.assertIn('no_candidate_observed', r['observed_labels'])
        self.assertNotIn('activation_failure', r['observed_labels'])
        self.assertNotIn('invalid_proof_reported', r['observed_labels'])

    def test_budget_is_not_proven_nonconvergence(self):
        row, _ = fixture(); row['decision']['value'] = None
        row['decision']['convergence']['status'] = 'budget_exhausted'
        row['assessment']['correct'] = None
        r = review.label_outcome(row['decision'], row['assessment'])
        self.assertIn('budget_boundary', r['observed_labels'])
        self.assertNotIn('non_convergence', r['observed_labels'])

    def test_oscillation_is_separate_observation(self):
        row, _ = fixture(); row['decision']['value'] = None
        row['decision']['convergence']['status'] = 'oscillating'; row['assessment']['correct'] = None
        self.assertIn('oscillation_observed', review.label_outcome(row['decision'], row['assessment'])['observed_labels'])

    def test_wrong_stable_inconsistency_rejected(self):
        row, _ = fixture(); row['assessment']['wrong_stable'] = True
        with self.assertRaises(review.baseline.BaselineError): review.label_outcome(row['decision'], row['assessment'])

    def test_boolean_contract_not_integer(self):
        row, _ = fixture(); row['assessment']['correct'] = 1
        with self.assertRaises(review.baseline.BaselineError): review.label_outcome(row['decision'], row['assessment'])

    def test_assumption_mismatch_kept_separate(self):
        row, _ = fixture(); row['assessment']['assumption_correct'] = False
        r = review.label_outcome(row['decision'], row['assessment'])
        self.assertIn('assumption_reality_mismatch', r['observed_labels'])

    def test_explanation_is_containment_not_causal_audit(self):
        row, events = fixture(); r = review.explanation_observation(row, events)
        self.assertEqual(r['assumption_ids_outside_public_observation'], [])
        self.assertFalse(r['actual_causal_path_reconstructed'])
        self.assertFalse(r['primitive_proof_revalidated'])

    def test_missing_time_is_not_fabricated(self):
        row, events = fixture(); r = review.explanation_observation(row, events)
        self.assertFalse(r['separate_readout_event_recorded'])
        self.assertFalse(r['separate_latencies_measured'])

    def test_extra_explored_branch_not_missing_proof(self):
        row, events = fixture()
        row['observation']['edges'].append(dict(id='edge1', source='a', target='b', score=-.9))
        events[1]['payload']['program']['paths'].append([1])
        r = review.explanation_observation(row, events)
        self.assertFalse(r['omitted_dependencies_diagnosed'])
        self.assertEqual(r['proof_paths_outside_last_program'], [])

    def test_assumption_outside_input_reported(self):
        row, events = fixture(); row['decision']['proof']['assumed_edges'].append(['ghost', True])
        r = review.explanation_observation(row, events)
        self.assertEqual(r['assumption_ids_outside_public_observation'], ['ghost'])

    def test_proof_path_outside_program_reported(self):
        row, events = fixture(); row['decision']['proof']['paths'].append(['ghost'])
        self.assertEqual(review.explanation_observation(row, events)['proof_paths_outside_last_program'], [('ghost',)])

    def test_program_digest_mismatch_rejected(self):
        row, events = fixture(); events[1]['payload']['program_digest'] = 'bad'
        with self.assertRaises(review.baseline.BaselineError): review.explanation_observation(row, events)

    def test_missing_settled_event_rejected(self):
        row, events = fixture(); events.pop(2)
        with self.assertRaises(review.baseline.BaselineError): review.explanation_observation(row, events)

    def test_duplicated_decision_rejected(self):
        row, events = fixture(); events.append(events[-1])
        with self.assertRaises(review.baseline.BaselineError): review.explanation_observation(row, events)

    def test_row_observation_mismatch_rejected(self):
        row, events = fixture(); events[0]['payload']['observation'] = dict(row['observation'], revision=1)
        with self.assertRaises(review.baseline.BaselineError): review.explanation_observation(row, events)

    def test_multirow_aggregation_does_not_count_new_samples(self):
        row, events = fixture(); r = review.analyze_records([row], events)
        self.assertEqual(len(r['records']), 1)
        self.assertEqual(r['boundaries']['new_research_samples'], 0)

    def test_duplicate_rows_rejected(self):
        row, events = fixture()
        with self.assertRaises(review.baseline.BaselineError): review.analyze_records([row, row], events)

    def test_existing_output_rejected_before_reading_capture(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            with self.assertRaises(review.baseline.BaselineError): review.review(p / 'capture', p)

    def test_tools_have_no_hcr_imports(self):
        for file in ('check.py', 'review.py'):
            tree = ast.parse((HERE / file).read_text(encoding='utf-8'))
            imports = [node.module or '' for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
            imports += [alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names]
            self.assertFalse(any(name == 'hcr' or name.startswith('hcr.') for name in imports))


if __name__ == '__main__':
    unittest.main()
