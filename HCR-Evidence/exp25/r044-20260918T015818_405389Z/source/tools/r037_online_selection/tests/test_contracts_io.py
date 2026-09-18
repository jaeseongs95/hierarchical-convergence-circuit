from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from r037_online_selection import io,spec
from r037_online_selection.contracts import Budget, ContractError, digest, validate_public_observation
from helpers import OBS


class ContractTests(unittest.TestCase):
    def test_budget_rejects_boolean(self):
        with self.assertRaises(ContractError):Budget(max_initial_advances=True)
    def test_budget_rejects_negative(self):
        with self.assertRaises(ContractError):Budget(max_extra_kernel_ticks=-1)
    def test_budget_rejects_nan(self):
        with self.assertRaises(ContractError):Budget(max_extra_kernel_ticks=float('nan'))
    def test_valid_observation(self):
        validate_public_observation(OBS)
    def test_truth_injection(self):
        obs=deepcopy(OBS);obs['worlds']={}
        with self.assertRaises(ContractError):validate_public_observation(obs)
    def test_boolean_score(self):
        obs=deepcopy(OBS);obs['edges'][0]['score']=True
        with self.assertRaises(ContractError):validate_public_observation(obs)
    def test_nonfinite_score(self):
        obs=deepcopy(OBS);obs['edges'][0]['score']=float('inf')
        with self.assertRaises(ContractError):validate_public_observation(obs)
    def test_missing_and_zero_are_distinct_inputs(self):
        a=deepcopy(OBS);b=deepcopy(OBS);a['edges'][0]['score']=None;b['edges'][0]['score']=0
        validate_public_observation(a);validate_public_observation(b);self.assertNotEqual(digest(a),digest(b))
    def test_duplicate_edge(self):
        obs=deepcopy(OBS);obs['edges'].append(deepcopy(obs['edges'][0]))
        with self.assertRaises(ContractError):validate_public_observation(obs)
    def test_design_population(self):
        cases=[{'name':n} for n in spec.CASE_NAMES];trials=spec.trials(cases)
        self.assertEqual(len(trials),32);self.assertEqual(len({t['id'] for t in trials}),32)
        self.assertEqual(len({t['case'] for t in trials}),8)
    def test_public_producer_not_given_worlds(self):
        self.assertFalse(spec.conditions()['correctness_required_for_audit'])
        self.assertTrue(spec.conditions()['selector_controls_stop'])
        self.assertFalse(spec.conditions()['selector_changes_native_kernel'])


class IOTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
    def tearDown(self):
        self.tmp.cleanup()
    def test_no_overwrite(self):
        p=self.root/'x.json';io.put(p,{'a':1})
        with self.assertRaises(FileExistsError):io.put(p,{'a':2})
        self.assertEqual(io.load(p),{'a':1})
    def test_duplicate_json_key(self):
        with self.assertRaises(ContractError):io.loads('{"a":1,"a":2}')
    def test_nan_json(self):
        with self.assertRaises(ValueError):io.loads('{"a":NaN}')
    def test_traversal(self):
        for name in ('../x','/etc/passwd','C:/x','x\\y','a/../x','./x','a//x'):
            with self.subTest(name=name):
                with self.assertRaises(ContractError):io.child(self.root,name)
    def test_symlink(self):
        target=self.root/'target';target.write_text('x');link=self.root/'link'
        try:link.symlink_to(target)
        except (OSError,NotImplementedError):return  # Windows 일반 권한에서는 생성 자체가 금지될 수 있다.
        with self.assertRaises(ContractError):io.read(link)
    def test_disjoint(self):
        with self.assertRaises(ContractError):io.disjoint(self.root,self.root/'child')
        with self.assertRaises(ContractError):io.disjoint(self.root,self.root)
    def test_crlf_only_normalized_for_source_hash(self):
        a=self.root/'a';b=self.root/'b';a.write_bytes(b'x\n');b.write_bytes(b'x\r\n')
        self.assertEqual(io.text_hash(a),io.text_hash(b));self.assertNotEqual(io.file_hash(a),io.file_hash(b))
    def test_inventory(self):
        io.put(self.root/'nested'/'a.json',{'a':1});self.assertEqual(io.inventory(self.root),{'nested/a.json'})
