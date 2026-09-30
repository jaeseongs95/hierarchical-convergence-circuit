from pathlib import Path
from copy import deepcopy
from contextlib import redirect_stdout,redirect_stderr
from dataclasses import asdict
import hashlib
import io
import json
import shutil
import tempfile
import unittest
from helpers import rewrite_manifest
from hcr import codec
from hcr.model import Config,ContractError,fingerprint
from hcr.trace import Trace,check_chain
from hcr.cli import main,config_from
from hcr.evaluation.protocol import run_demo
from hcr.evaluation.audit import verify_run


class TraceContracts(unittest.TestCase):
    def test_returned_record_mutation_does_not_rewrite_trace(self):
        t=Trace();p={'a':[1,2]};t.emit('hello',p);p['a'].append(3)
        view=t.records;view[0]['payload']['a'].append(4)
        self.assertEqual(t.records[0]['payload']['a'],[1,2])
    def test_truncation_rejected(self):
        t=Trace();t.emit('one',{});t.emit('two',{})
        with self.assertRaises(ContractError):check_chain(t.records[:-1],t.count,t.head)
    def test_closed_trace_cannot_silently_continue_only_in_memory(self):
        t=Trace();t.close()
        with self.assertRaises(ContractError):t.emit('bad',{})
    def test_existing_file_not_overwritten(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'result.json';p.write_text('keep')
            with self.assertRaises(FileExistsError):codec.save(p,{'changed':True})
            self.assertEqual(p.read_text(),'keep')


class RunAudit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.root=Path(cls.tmp.name)/'run';cls.summary=run_demo(cls.root)
    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()
    def copy(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);p=Path(temp.name)/'copy';shutil.copytree(self.root,p);return p
    def test_entire_integrated_loop_has_independent_replay(self):
        result=verify_run(self.root)
        self.assertTrue(result['verified']);self.assertEqual(result['decisions_reassessed'],43)
        self.assertGreater(result['scalar_ticks_replayed'],1000);self.assertEqual(result['memory_updates_checked'],9)
    def test_final_summary_reports_failures_and_abstention(self):
        s=self.summary
        self.assertEqual(s['frozen_eval']['full']['wrong_stable'],1)
        self.assertEqual(s['frozen_eval']['graph_only']['unresolved'],1)
        self.assertFalse(s['adaptation']['full']['initial']['correct']);self.assertTrue(s['adaptation']['full']['final']['correct'])
        self.assertFalse(s['adaptation']['no_reexpansion']['final']['correct']);self.assertEqual(s['retention']['strict_correct'],2)
    def test_tampered_file_rejected(self):
        root=self.copy();(root/'summary.json').write_text('{}')
        with self.assertRaises(ContractError):verify_run(root)
    def test_forged_summary_rejected_even_when_manifest_rehashed(self):
        root=self.copy();x=codec.loads((root/'summary.json').read_bytes());x['frozen_eval']['full']['correct']=8
        codec.save(root/'summary.json',x,replace=True);rewrite_manifest(root)
        with self.assertRaisesRegex(ContractError,'group summary'):verify_run(root)
    def test_tampered_tick_rejected_even_with_new_event_chain(self):
        root=self.copy();events=[codec.loads(x) for x in (root/'events.jsonl').read_text().splitlines()]
        first=next(e for e in events if e['event']=='tick');first['payload']['state']['goal']=.91
        head='0'*64
        for e in events:
            e['previous']=head;body={k:e[k] for k in ('seq','previous','event','payload')};e['sha256']=fingerprint(body);head=e['sha256']
        (root/'events.jsonl').write_text('\n'.join(codec.dumps(e) for e in events)+'\n',encoding='utf-8')
        status=codec.loads((root/'status.json').read_bytes());status['event_head']=head;codec.save(root/'status.json',status,replace=True);rewrite_manifest(root)
        with self.assertRaisesRegex(ContractError,'recurrence mismatch'):verify_run(root)
    def test_extra_file_rejected(self):
        root=self.copy();(root/'extra.txt').write_text('unexpected')
        with self.assertRaises(ContractError):verify_run(root)
    def test_run_directory_cannot_be_reused(self):
        before=(self.root/'manifest.json').read_bytes()
        with self.assertRaises(FileExistsError):run_demo(self.root)
        self.assertEqual(before,(self.root/'manifest.json').read_bytes())
    def test_deterministic_semantics_excluding_measured_timing(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);root=Path(temp.name)/'second';run_demo(root)
        left=[codec.loads(x) for x in (self.root/'episodes.jsonl').read_text().splitlines()]
        right=[codec.loads(x) for x in (root/'episodes.jsonl').read_text().splitlines()]
        for a,b in zip(left,right):
            a['decision']['cost'].pop('wall_seconds');b['decision']['cost'].pop('wall_seconds')
            self.assertEqual(a,b)
        self.assertEqual(len(left),len(right))
    def test_failed_run_is_not_accepted_as_complete(self):
        root=self.copy();x=codec.loads((root/'status.json').read_bytes());x['state']='failed';codec.save(root/'status.json',x,replace=True);rewrite_manifest(root)
        with self.assertRaises(ContractError):verify_run(root)


class CommandLine(unittest.TestCase):
    def test_config_matches_source_defaults(self):
        path=Path(__file__).resolve().parents[1]/'configs/r01.toml'
        self.assertEqual(config_from(path),Config())
    def test_infer_uses_only_public_input(self):
        with tempfile.TemporaryDirectory() as td,redirect_stdout(io.StringIO()):
            root=Path(td);obs=Path(__file__).resolve().parents[1]/'configs/example_observation.json'
            rc=main(['infer','--input',str(obs),'--out',str(root/'new')])
            self.assertEqual(rc,0);state=codec.loads((root/'new/state.json').read_bytes());self.assertFalse(state['correctness_evaluated'])
    def test_infer_rejects_hidden_label_file(self):
        with tempfile.TemporaryDirectory() as td,redirect_stderr(io.StringIO()):
            root=Path(td);p=root/'obs.json';p.write_text('{"truth":true}')
            self.assertEqual(main(['infer','--input',str(p),'--out',str(root/'new')]),2)
            self.assertFalse((root/'new').exists())
    def test_cli_demo_and_verify(self):
        with tempfile.TemporaryDirectory() as td,redirect_stdout(io.StringIO()):
            root=Path(td)/'한글 공백';self.assertEqual(main(['demo','--out',str(root)]),0)
            self.assertEqual(main(['verify','--run',str(root)]),0)
    def test_verify_receipt_cannot_pollute_original_run(self):
        with tempfile.TemporaryDirectory() as td,redirect_stderr(io.StringIO()):
            root=Path(td)/'run';run_demo(root)
            self.assertEqual(main(['verify','--run',str(root),'--out',str(root/'receipt.json')]),2)
            self.assertTrue(verify_run(root)['verified'])

    def test_finite_boolean_calibration_all_cases(self):
        import importlib.util
        path=Path(__file__).resolve().parents[1]/'scripts/calibrate.py'
        spec=importlib.util.spec_from_file_location('hcr_calibration',path)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        result=module.calibration()
        self.assertEqual(result['checks'],184);self.assertEqual(result['failures'],0)
