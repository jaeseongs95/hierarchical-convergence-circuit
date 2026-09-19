"""Synthetic control-flow tests; no new research outcomes are generated."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch
from tools.r050_review_boundary.common import IntegrityError, dump, load, seal
from tools.r055_allocation.pipeline import kernel_and_audit, stage, validate_spec
from tools.r055_allocation.worker import masked_program, produce


def spec():
    return load(Path(__file__).resolve().parents[3]/'experiments/exp-36-drive-allocation/frozen_spec.json')


def fixture():
    links = spec()['feedback_links']
    program = dict(groups=[dict(id=name,level=0 if name.startswith('e:') else 1,bias=0.0)
        for name in ('e:0','e:1','p:0:0','p:0:1','goal')],
        links=[dict(source=item['source'],target=item['target'],weight=.35,kind='top_down')
               for item in links] + [dict(source='e:0',target='p:0:0',weight=2.0,kind='support')],
        paths=[[0,1]],edge_count=2)
    return program,links


class WorkerPipeline(unittest.TestCase):
    def test_exact_drive_mapping_and_fixed_total(self):
        pairs = [(1.0,.02),(.755,.265),(.51,.51),(.265,.755),(.02,1.0)]
        drives = [(4.0,.08),(3.02,1.06),(2.04,2.04),(1.06,3.02),(.08,4.0)]
        for condition, pair, drive in zip(spec()['conditions'], pairs, drives, strict=True):
            self.assertEqual(condition['input_pair'], list(pair))
            self.assertEqual(condition['drives'], {'e:0':drive[0],'e:1':drive[1],'goal':0.0})
            self.assertEqual(condition['drives']['e:0'], 4*pair[0])
            self.assertEqual(condition['drives']['e:1'], 4*pair[1])
            self.assertAlmostEqual(sum(pair), 1.02)
            self.assertAlmostEqual(sum(drive), 4.08)

    def test_exact_single_link_removal_preserves_everything_else(self):
        program,links = fixture()
        before = deepcopy(program)
        for mask in spec()['masks']:
            masked,active,removed = masked_program(program,mask,links)
            self.assertEqual(len(removed),len(mask['remove']))
            self.assertEqual(len(active),4-len(removed))
            self.assertEqual(masked['groups'],program['groups'])
            self.assertEqual(masked['links'][-1],program['links'][-1])
            expected = {(link['source'],link['target']) for link in links if link['id'] in mask['remove']}
            self.assertEqual({(link['source'],link['target']) for link in removed},expected)
        self.assertEqual(program,before)

    def test_unknown_duplicate_extra_or_missing_link_rejected(self):
        program,links = fixture()
        for remove in (['unknown'],['E_start','E_start']):
            with self.assertRaises(IntegrityError):
                masked_program(program,dict(id='bad',remove=remove),links)
        for variant in (program['links'][1:],program['links']+[program['links'][0]]):
            with self.assertRaises(IntegrityError):
                masked_program({**program,'links':variant},dict(id='full',remove=[]),links)

    def test_fixed_contract_tampering_rejected(self):
        original = spec()
        validate_spec(original)
        for key in ('masks','conditions','anchor_files','parent_files','endpoint_rule','drive_mapping','mirrored_contrasts'):
            changed = deepcopy(original)
            changed[key] = []
            with self.assertRaises(IntegrityError):
                validate_spec(changed)

    def test_four_smoke_branches_fresh_start_and_null_claims(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            plan = dict(schema='hcc-r055-plan-v1',purpose='implementation_validation',spec=spec(),config={})
            dump(root/'plan.json',seal(plan))
            dump(root/'parents/study/raw/r052-c001/start_edge.json',{'fixture':True})
            original,_ = fixture()
            calls = []
            def fake_execute(program,drives,config,initial):
                calls.append(deepcopy(initial))
                self.assertIn(drives, [c['drives'] for c in spec()['conditions']])
                initial['goal'] = .1
                return dict(ticks=[],final_state={},convergence={},cost={})
            with patch('tools.r055_allocation.worker.read_network',return_value=(original,{})), \
                    patch('tools.r055_allocation.worker.execute',side_effect=fake_execute):
                produce(root)
            self.assertEqual(len(calls),4)
            self.assertTrue(all(set(item.values()) == {.5} for item in calls))
            paths = list((root/'smoke').rglob('*.json'))
            self.assertEqual(len(paths),4)
            for path in paths:
                row = load(path)
                self.assertTrue(row['counterfactual'])
                self.assertTrue(all(row[key] is None for key in spec()['unmeasured']))

    def test_parent_or_anchor_change_stops_before_worker(self):
        for key in ('parent_files','anchor_files'):
            with self.subTest(key=key), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                manifests = dict(parent_files={},anchor_files={})
                manifests[key] = {'missing.json':'a'*64}
                dump(root/'plan.json',dict(spec=manifests))
                with patch('tools.r055_allocation.pipeline.stage') as launch:
                    with self.assertRaisesRegex(IntegrityError,'Evidence bytes changed'):
                        kernel_and_audit(root,root,'test')
                    launch.assert_not_called()

    def test_research_matrix_metadata_and_overrides(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            frozen = spec()
            dump(root/'plan.json', seal(dict(schema='hcc-r055-plan-v1', purpose='research',
                                           spec=frozen, config={})))
            dump(root/'parents'/frozen['program_parent'], {'fixture':True})
            original, _ = fixture()
            original_drives = {'e:0':4.0, 'e:1':.08, 'goal':0.0}
            with patch('tools.r055_allocation.worker.read_network', return_value=(original, original_drives)), \
                    patch('tools.r055_allocation.worker.execute', return_value=dict(
                        ticks=[], final_state={}, convergence={}, cost={})) as launch:
                produce(root)
            self.assertEqual(launch.call_count, 10)
            self.assertEqual(len(list((root/'study').rglob('*.json'))), 10)
            for condition in frozen['conditions']:
                for mask in frozen['masks']:
                    row = load(root/'study'/condition['id']/(mask['id']+'.json'))
                    self.assertEqual(row['condition'], condition['id'])
                    self.assertEqual(row['input_pair'], condition['input_pair'])
                    self.assertEqual(row['drives'], condition['drives'])
                    self.assertEqual(row['original_drives'], original_drives)
                    self.assertEqual(set(row['initial_state'].values()), {.5})

    def test_stage_preserves_first_failure_without_retry(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with patch('tools.r055_allocation.pipeline.subprocess.run',return_value=SimpleNamespace(returncode=7)) as launch:
                with self.assertRaisesRegex(IntegrityError,'first failure retained'):
                    stage(root,root,'failed','tools.r055_allocation.worker',[])
                self.assertEqual(launch.call_count,1)
            self.assertEqual(load(root/'validation/failed.receipt.json')['returncode'],7)
            with self.assertRaises(FileExistsError):
                stage(root,root,'failed','tools.r055_allocation.worker',[])


if __name__ == '__main__':
    unittest.main()
