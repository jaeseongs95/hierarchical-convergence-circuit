"""수집/짝지음 도구의 계약 시험. 사용자가 명시적으로 실행한다. HCR 엔진은 import하지 않는다."""
from copy import deepcopy
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from collect import (ALIASES, BaselineError, canonical, canonical_cost, check_chain,
                     loads, pattern_id, relative, sha, verify_bundle, write_json)
from probe import semantic_decision


class BaselineTools(unittest.TestCase):
    def cost(self):
        return {**{k: 2 for k in ALIASES}, **{k: 2 for k in ALIASES.values()}, "wall_seconds": .2}

    def test_json_duplicate_rejected(self):
        with self.assertRaises(BaselineError):
            loads('{"a":1,"a":2}')

    def test_json_nonfinite_rejected(self):
        for raw in ('{"x":NaN}', '{"x":1e999}'):
            with self.subTest(raw=raw), self.assertRaises(BaselineError):
                loads(raw)

    def test_unsafe_paths_rejected(self):
        for path in ('../x', '/x', 'C:/x', 'a\\b', '.git/config', 'a//b', '', '.'):
            with self.subTest(path=path), self.assertRaises(BaselineError):
                relative(path)

    def test_safe_path_retained(self):
        self.assertEqual(relative('src/hcr/runtime.py').as_posix(), 'src/hcr/runtime.py')

    def test_alias_not_double_counted(self):
        self.assertTrue(set(canonical_cost(self.cost())).isdisjoint(ALIASES))

    def test_mismatched_alias_rejected(self):
        c = self.cost()
        c['signal_events'] += 1
        with self.assertRaises(BaselineError):
            canonical_cost(c)

    def test_negative_cost_rejected(self):
        c = self.cost()
        c['wall_seconds'] = -1
        with self.assertRaises(BaselineError):
            canonical_cost(c)

    def test_pattern_id_is_computed_not_stored(self):
        circuit = {'pattern': {'relations': [1, 2]}}
        self.assertEqual(pattern_id(circuit), 'pattern-' + sha(canonical(circuit['pattern']))[:24])

    def test_empty_trace_contract(self):
        check_chain([], {'event_count': 0, 'event_head': '0' * 64})

    def test_tampered_trace_rejected(self):
        body = dict(seq=0, previous='0'*64, event='x', payload={'v': 1})
        event = dict(body, sha256=sha(canonical(body)))
        event['payload']['v'] = 2
        with self.assertRaises(BaselineError):
            check_chain([event], {'event_count': 1, 'event_head': event['sha256']})

    def test_decision_comparison_excludes_only_id_time(self):
        a = {'id': 'a', 'cost': {'wall_seconds': .1, 'expansions': 2}, 'proof': {'primitive_depth': 3}, 'state': [['goal', .7]]}
        b = deepcopy(a)
        b['id'], b['cost']['wall_seconds'] = 'b', .2
        self.assertEqual(semantic_decision(a), semantic_decision(b))
        self.assertIn('id', a)
        b['proof']['primitive_depth'] = 2
        self.assertNotEqual(semantic_decision(a), semantic_decision(b))

    def test_operation_difference_not_hidden(self):
        a = {'id': 'a', 'cost': {'wall_seconds': .1, 'expansions': 2}}
        b = deepcopy(a)
        b['cost']['expansions'] = 1
        self.assertNotEqual(semantic_decision(a), semantic_decision(b))

    def test_exclusive_json_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'x.json'
            write_json(p, {'a': 1})
            with self.assertRaises(FileExistsError):
                write_json(p, {'a': 2})
            self.assertEqual(loads(p.read_bytes()), {'a': 1})

    def test_bundle_extra_file_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_json(root/'bundle_manifest.json', dict(schema='hcr-r02-baseline-bundle-v1', state='complete', files={}))
            (root/'unexpected').write_text('x')
            with self.assertRaises(BaselineError):
                verify_bundle(root)

    def test_bundle_wrong_hash_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'data').write_bytes(b'x')
            write_json(root/'bundle_manifest.json', dict(schema='hcr-r02-baseline-bundle-v1', state='complete', files={'data':'0'*64}))
            with self.assertRaises(BaselineError):
                verify_bundle(root)

    def test_bundle_valid_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'data').write_bytes(b'x')
            write_json(root/'bundle_manifest.json', dict(schema='hcr-r02-baseline-bundle-v1', state='complete', files={'data':sha(b'x')}))
            self.assertEqual(verify_bundle(root)['state'], 'complete')


if __name__ == '__main__':
    unittest.main()
