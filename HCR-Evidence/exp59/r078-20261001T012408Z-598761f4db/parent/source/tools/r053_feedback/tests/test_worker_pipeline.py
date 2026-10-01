"""Synthetic implementation checks; never run the research matrix here."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch
from hcr.codec import plain
from hcr.model import Config
from tools.r050_review_boundary.common import IntegrityError, dump, load
from tools.r053_feedback.worker import execute, masked_program, parent_path, read_network
from tools.r053_feedback.pipeline import kernel_and_audit, stage, validate_spec


class WorkerPipeline(unittest.TestCase):
    def test_four_masks_partition_without_mutating_source(self):
        program = dict(groups=[dict(id='e',level=0),dict(id='p',level=1),dict(id='goal',level=1)],
            links=[dict(source='e',target='p',kind='support',weight=2.0),
                   dict(source='p',target='e',kind='top_down',weight=.35),
                   dict(source='goal',target='p',kind='top_down',weight=.35)])
        original = deepcopy(program)
        partition = dict(edge_local=[['p','e']],path_internal=[['goal','p']])
        for local, internal, count in ((False,False,0),(True,False,1),(False,True,1),(True,True,2)):
            result, active, removed = masked_program(program, dict(edge_local=local,path_internal=internal),partition)
            self.assertEqual(len(active),count)
            self.assertEqual(len(removed),2-count)
            self.assertEqual(result['links'][0],program['links'][0])
        self.assertEqual(program,original)
        program['links'].append(dict(source='p',target='goal',kind='top_down',weight=.35))
        with self.assertRaisesRegex(IntegrityError,'directed feedback partition'):
            masked_program(program,dict(edge_local=True,path_internal=True),partition)

    def test_frozen_matrix_preflight_rejects_resealed_changes(self):
        root = Path(__file__).resolve().parents[3]
        spec = load(root/'experiments/exp-34-feedback-factorial/frozen_spec.json')
        validate_spec(spec)
        for key in ('masks','conditions','parent_files','unmeasured'):
            changed = deepcopy(spec)
            changed[key] = []
            with self.assertRaises(IntegrityError):
                validate_spec(changed)

    def test_network_extraction_does_not_use_native_outcomes(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'raw.json'
            dump(path, dict(execution=dict(candidate='deliberately unusable',packet=dict(document=dict(
                events=[dict(event='r02_tick',payload='deliberately unusable'),dict(event='r02_network',
                    payload=dict(kind='decision',program={'sentinel':1},drives={'goal':0.0}))])))))
            self.assertEqual(read_network(path),({'sentinel':1},{'goal':0.0}))

    def test_duplicate_network_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'raw.json'
            event = dict(event='r02_network',payload=dict(kind='decision',program={},drives={}))
            dump(path,dict(execution=dict(packet=dict(document=dict(events=[event,event])))))
            with self.assertRaises(IntegrityError):
                read_network(path)

    def test_parent_paths_are_fixed(self):
        self.assertEqual(parent_path('baseline'),'study/baselines/r052-c001.json')
        self.assertEqual(parent_path('start_edge'),'study/raw/r052-c001/start_edge.json')

    def test_synthetic_kernel_only(self):
        program = dict(groups=[dict(id='goal',level=1,bias=0.0)],links=[],paths=[[0]],edge_count=1)
        result = execute(program,{},plain(Config()),{'goal':.5})
        self.assertEqual(result['final_state'],{'goal':.5})
        self.assertEqual(result['convergence']['status'],'stable_ambiguous')
        self.assertEqual(result['cost'],dict(kernel_ticks=4,group_updates=4,
            normalization_ops=4,signal_transmissions=0))

    def test_stage_failure_is_retained_without_retry(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with patch('tools.r053_feedback.pipeline.subprocess.run',return_value=SimpleNamespace(returncode=7)) as run:
                with self.assertRaisesRegex(IntegrityError,'first failure retained'):
                    stage(root,root,'failed','tools.r053_feedback.worker',[])
                self.assertEqual(run.call_count,1)
            self.assertEqual(load(root/'validation/failed.receipt.json')['returncode'],7)
            with self.assertRaises(FileExistsError):
                stage(root,root,'failed','tools.r053_feedback.worker',[])

    def test_parent_change_stops_before_worker(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            dump(root/'plan.json',dict(spec=dict(parent_files={'missing.json':'a'*64})))
            with patch('tools.r053_feedback.pipeline.stage') as launch:
                with self.assertRaisesRegex(IntegrityError,'Parent bytes changed'):
                    kernel_and_audit(root,root,'test')
                launch.assert_not_called()


if __name__ == '__main__':
    unittest.main()
