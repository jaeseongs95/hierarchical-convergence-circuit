"""R0.3 실제 교대·메시지·총예산·독립 감사의 계약 시험."""
from __future__ import annotations
import ast
from contextlib import redirect_stderr, redirect_stdout
import io
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from hcr import codec
from hcr.cli import main as hcr_main
from hcr.model import ContractError, fingerprint, Mode
from hcr.integration import RouteHint, integrate
from hcr.methods import MethodEngine, MethodConfig, ARMS, prefix_choice
from hcr.sessions import AdaptiveSession, verify_packet
from hcr.evaluation.method_audit import verify_result
from hcr.evaluation.method_protocol import cases, external_assessment
from hcr.tasks.toy_world import chain
from r02_helpers import train_r02


def rehash_controller(result):
    head='0'*64
    for i,e in enumerate(result['controller']):
        body=dict(seq=i,previous=head,event=e['event'],payload=e['payload'])
        e.update(body,sha256=fingerprint(body));head=e['sha256']


class PriorityContracts(unittest.TestCase):
    def fresh(self):
        s=AdaptiveSession(use_circuits=False,session_id='priority')
        s.begin(cases()['fork'].observation);s.advance()
        return s
    def test_priority_preserves_nodes(self):
        s=self.fresh();before=s.current['pending']['workspace'];p=before['frontier'][1]['path']
        s.prioritize_frontier(p);after=s.current['pending']['workspace']
        self.assertEqual(after['known'],before['known']);self.assertEqual(after['routes'],before['routes'])
        self.assertEqual(sorted(after['frontier'],key=lambda x:x['path']),sorted(before['frontier'],key=lambda x:x['path']))
        self.assertEqual(after['frontier'][0]['path'],p)
    def test_nonexistent_path_rejected_atomically(self):
        s=self.fresh();before=s.packet()
        with self.assertRaises(ContractError):s.prioritize_frontier([7,7])
        self.assertEqual(s.packet(),before)
    def test_bool_slot_rejected(self):
        s=self.fresh()
        with self.assertRaises(ContractError):s.prioritize_frontier([True])
    def test_priority_snapshot_schema(self):
        s=self.fresh();self.assertEqual(s.packet()['schema'],'hcr-session-checkpoint-r021-v1')
        s.prioritize_frontier([1]);self.assertEqual(s.packet()['schema'],'hcr-session-checkpoint-r03-v1')
        self.assertTrue(verify_packet(s.packet())['verified'])
    def test_wrong_schema_rejected(self):
        s=self.fresh();s.prioritize_frontier([1]);p=s.packet();p['schema']='hcr-session-checkpoint-r021-v1'
        with self.assertRaises(ContractError):AdaptiveSession.from_packet(p)
    def test_priority_resume(self):
        s=self.fresh();s.prioritize_frontier([1]);p=s.packet();r=AdaptiveSession.from_packet(p)
        a=codec.plain(s.complete());b=codec.plain(r.complete())
        a['cost'].pop('wall_seconds');b['cost'].pop('wall_seconds');self.assertEqual(a,b)
    def test_finished_priority_refused(self):
        s=self.fresh();s.complete()
        with self.assertRaises(ContractError):s.prioritize_frontier([1])


class MethodBehavior(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.memory=train_r02().memory
        cls.world=cases()
        cls.results={a:MethodEngine(memory=cls.memory).infer(cls.world['fork'].observation,arm=a) for a in ARMS}
    def test_all_arms_independent_audit(self):
        for a,r in self.results.items():
            with self.subTest(arm=a):self.assertTrue(verify_result(r)['verified'])
    def test_memory_unchanged(self):
        for r in self.results.values():self.assertEqual(r['initial_memory'],self.memory.document())
    def test_different_profiles_not_just_name(self):
        a=self.results['sequential'];b=self.results['associative']
        self.assertGreater(a['budget']['used_advances'],b['budget']['used_advances'])
        self.assertEqual(a['cost']['circuit_reuses'],0);self.assertGreater(b['cost']['circuit_reuses'],0)
    def test_message_changes_actual_frontier(self):
        a=self.results['fixed'];b=self.results['fixed_no_messages']
        self.assertGreater(verify_result(a)['priority_changes'],0)
        self.assertLess(a['budget']['used_advances'],b['budget']['used_advances'])
    def test_no_messages_ablation(self):
        for a in ('fixed_no_messages','adaptive_no_messages'):
            self.assertEqual(self.results[a]['budget']['messages_sent'],0)
            self.assertFalse(any(e['event']=='r03_message' for e in self.results[a]['controller']))
    def test_scheduler_changes_sequence(self):
        seq=lambda a:[e['payload']['worker'] for e in self.results[a]['controller'] if e['event']=='r03_scheduled']
        self.assertNotEqual(seq('fixed_no_messages'),seq('adaptive_no_messages'))
    def test_no_disk_during_interleaving(self):
        with patch.object(AdaptiveSession,'save',side_effect=AssertionError('unexpected disk checkpoint')),patch.object(AdaptiveSession,'load',side_effect=AssertionError('unexpected disk load')):
            MethodEngine(memory=self.memory).infer(self.world['familiar'].observation)
    def test_conflict_is_not_a_fabricated_correction(self):
        r=MethodEngine(memory=self.memory).infer(self.world['weak_conflict'].observation)
        self.assertIsNone(r['result']['value']);self.assertEqual(r['result']['status'],'conflict_abstention')
        self.assertTrue(r['decisions']['associative']['value']);self.assertFalse(r['decisions']['sequential']['value'])
        self.assertTrue(verify_result(r)['verified'])
    def test_no_double_count_of_public_evidence(self):
        r=self.results['fixed'];refs=r['result']['unique_evidence_refs']
        self.assertEqual(len(refs),len(set(refs)))
        self.assertFalse(r['result']['evidence_count_is_confidence'])
    def test_total_cost_is_all_workers_not_winner(self):
        r=self.results['fixed'];total=sum(v['cost']['kernel_ticks'] for v in r['decisions'].values())
        self.assertEqual(total,r['cost']['kernel_ticks'])
    def test_budget_is_shared(self):
        r=MethodEngine(memory=self.memory,method_config=MethodConfig(max_advances=2)).infer(self.world['fork'].observation)
        self.assertEqual(r['budget']['used_advances'],2);self.assertTrue(verify_result(r)['verified'])
    def test_tick_reservation_no_preview(self):
        with patch.object(AdaptiveSession,'advance',side_effect=AssertionError('preview is inference')):
            r=MethodEngine(memory=self.memory,method_config=MethodConfig(max_kernel_ticks=1)).infer(self.world['fork'].observation)
        self.assertEqual(r['budget']['used_kernel_ticks'],0);self.assertIsNone(r['result']['value'])
        self.assertTrue(verify_result(r)['verified'])
    def test_zero_advance_budget(self):
        r=MethodEngine(memory=self.memory,method_config=MethodConfig(max_advances=0)).infer(self.world['familiar'].observation)
        self.assertEqual(r['budget']['used_advances'],0);self.assertEqual(r['decisions'],{})
        self.assertTrue(verify_result(r)['verified'])
    def test_message_budget_is_explicit(self):
        r=MethodEngine(memory=self.memory,method_config=MethodConfig(max_messages=0)).infer(self.world['fork'].observation)
        self.assertEqual(r['budget']['messages_sent'],0)
        self.assertTrue(any(e['event']=='r03_message_dropped' for e in r['controller']))
        self.assertTrue(verify_result(r)['verified'])
    def test_invalid_arm(self):
        with self.assertRaises(ContractError):MethodEngine().infer(self.world['fork'].observation,arm='oracle')
    def test_typed_observation(self):
        with self.assertRaises(ContractError):MethodEngine().infer(dict(truth=True))
    def test_budget_bool_is_not_int(self):
        with self.assertRaises(ContractError):MethodConfig(max_advances=True)
    def test_negative_budget(self):
        with self.assertRaises(ContractError):MethodConfig(max_kernel_ticks=-1)
    def test_unknown_first_method(self):
        with self.assertRaises(ContractError):MethodConfig(first_method='truth')
    def test_reverse_first_method(self):
        r=MethodEngine(memory=self.memory,method_config=MethodConfig(first_method='sequential')).infer(self.world['fork'].observation,arm='fixed')
        first=next(e for e in r['controller'] if e['event']=='r03_scheduled')
        self.assertEqual(first['payload']['worker'],'sequential');self.assertTrue(verify_result(r)['verified'])
    def test_unknown_input_is_not_correct(self):
        r=MethodEngine(memory=None).infer(self.world['unknown'].observation,arm='sequential')
        self.assertIsNone(external_assessment(r,self.world['unknown'])['correct'])
    def test_results_are_detached(self):
        r=MethodEngine(memory=self.memory).infer(self.world['familiar'].observation)
        r['initial_memory']['circuits'].clear();self.assertTrue(self.memory.circuits)
    def test_no_hidden_truth_imports_in_production(self):
        for name in ('methods.py','integration.py'):
            tree=ast.parse((ROOT/'src/hcr'/name).read_text())
            imports=[n.module for n in ast.walk(tree) if isinstance(n,ast.ImportFrom)]
            self.assertFalse(any(x and ('evaluation' in x or 'tasks' in x) for x in imports))


class MessageContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.memory=train_r02().memory;cls.obs=cases()['fork'].observation
        cls.result=MethodEngine(memory=cls.memory).infer(cls.obs)
        cls.packet=next(e['payload'] for e in cls.result['controller'] if e['event']=='r03_message')
        cls.hint=RouteHint.from_packet(cls.packet)
        cls.events=cls.result['workers'][cls.hint.sender]['document']['events']
    def test_valid_message(self):self.hint.validate(self.obs,self.memory.digest,self.events)
    def test_packet_roundtrip(self):self.assertEqual(self.hint.packet(),self.packet)
    def test_stale_memory(self):
        with self.assertRaises(ContractError):self.hint.validate(self.obs,'f'*64,self.events)
    def test_stale_revision(self):
        with self.assertRaises(ContractError):replace(self.hint,observation_revision=99).validate(self.obs,self.memory.digest,self.events)
    def test_wrong_roles(self):
        with self.assertRaises(ContractError):replace(self.hint,roles=(('R0','ghost'),)).validate(self.obs,self.memory.digest,self.events)
    def test_wrong_evidence(self):
        with self.assertRaises(ContractError):replace(self.hint,evidence_refs=('ghost',)).validate(self.obs,self.memory.digest,self.events)
    def test_unseen_edge(self):
        with self.assertRaises(ContractError):replace(self.hint,path=(99,)).validate(self.obs,self.memory.digest,self.events)
    def test_bool_slot(self):
        with self.assertRaises(ContractError):replace(self.hint,path=(False,)).validate(self.obs,self.memory.digest,self.events)
    def test_wrong_source_event(self):
        with self.assertRaises(ContractError):replace(self.hint,source_event_sha256='0'*64).validate(self.obs,self.memory.digest,self.events)
    def test_no_self_echo(self):
        with self.assertRaises(ContractError):replace(self.hint,receiver=self.hint.sender).validate(self.obs,self.memory.digest,self.events)
    def test_hash_detects_mutation(self):
        p=deepcopy(self.packet);p['memory_digest']='0'*64
        with self.assertRaises(ContractError):RouteHint.from_packet(p)
    def test_extra_payload_field(self):
        p=deepcopy(self.packet);p['truth']=True
        with self.assertRaises(ContractError):RouteHint.from_packet(p)


class AuditContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r=MethodEngine(memory=train_r02().memory).infer(cases()['fork'].observation)
    def reject(self,mutate):
        r=deepcopy(self.r);mutate(r);rehash_controller(r)
        with self.assertRaises(ContractError):verify_result(r)
    def test_total_cost_tamper(self):self.reject(lambda r:r['cost'].__setitem__('kernel_ticks',0))
    def test_budget_tamper(self):self.reject(lambda r:r['budget'].__setitem__('max_advances',999))
    def test_seed_tamper(self):self.reject(lambda r:r['initial_memory'].__setitem__('version',900))
    def test_hidden_worker_work(self):self.reject(lambda r:r['workers'].__setitem__('third',deepcopy(r['workers']['sequential'])))
    def test_false_confidence(self):self.reject(lambda r:r['result'].__setitem__('evidence_count_is_confidence',True))
    def test_result_substitution(self):self.reject(lambda r:r['result'].__setitem__('value',False))
    def test_counter_delta_tamper(self):
        self.reject(lambda r:next(e for e in r['controller'] if e['event']=='r03_advanced')['payload']['cost_delta'].__setitem__('kernel_ticks',0))
    def test_routing_instruction_tamper(self):
        self.reject(lambda r:next(e for e in r['controller'] if e['event']=='r03_scheduled')['payload'].__setitem__('selected_path',[7]))
    def test_message_content_tamper_after_rehash(self):
        self.reject(lambda r:next(e for e in r['controller'] if e['event']=='r03_message')['payload'].__setitem__('roles',[['R0','ghost']]))
    def test_consumed_message_not_fabricated(self):
        self.reject(lambda r:next(e for e in r['controller'] if e['event']=='r03_scheduled')['payload'].__setitem__('consumed_hint_ids',['ghost']))
    def test_no_production_auditor_imports(self):
        tree=ast.parse((ROOT/'src/hcr/evaluation/method_audit.py').read_text())
        imports=[n.module or '' for n in ast.walk(tree) if isinstance(n,ast.ImportFrom)]
        self.assertFalse(any(x.endswith(('methods','integration','runtime','sessions')) for x in imports))


class MethodCLI(unittest.TestCase):
    def test_help(self):
        stdout,stderr=io.StringIO(),io.StringIO()
        with redirect_stdout(stdout),redirect_stderr(stderr):
            with self.assertRaises(SystemExit) as raised:
                hcr_main(['methods','--help'])
        self.assertEqual(raised.exception.code,0,stderr.getvalue())
        self.assertIn('demo',stdout.getvalue())
    def test_unknown_arguments_fail(self):
        stdout,stderr=io.StringIO(),io.StringIO()
        with redirect_stdout(stdout),redirect_stderr(stderr):
            with self.assertRaises(SystemExit) as raised:
                hcr_main(['methods','demo'])
        self.assertNotEqual(raised.exception.code,0)
        self.assertIn('--out',stderr.getvalue())
    def test_windows_launcher_native_parser_when_available(self):
        import shutil
        executable=shutil.which('pwsh') or shutil.which('powershell.exe')
        if not executable:self.skipTest('PowerShell native parser unavailable in this environment')
        path=str(ROOT/'Run-HCR-R03.ps1').replace("'","''")
        command="$t=$null;$e=$null;[System.Management.Automation.Language.Parser]::ParseFile('"+path+"',[ref]$t,[ref]$e)|Out-Null;if($e.Count -gt 0){$e|Out-String|Write-Error;exit 1}"
        p=subprocess.run([executable,'-NoProfile','-Command',command],capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stdout+p.stderr)
    def test_output_existing_refused(self):
        from hcr.evaluation.method_protocol import run_demo
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(FileExistsError):run_demo(Path(d))


if __name__=='__main__':unittest.main()
