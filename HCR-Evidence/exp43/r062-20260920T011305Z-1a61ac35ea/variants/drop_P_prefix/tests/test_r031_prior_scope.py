"""R0.3.1 prior 조작의 국소성·상태 보존·검산·조건 동결 검사."""
from __future__ import annotations
import ast
from contextlib import redirect_stdout, redirect_stderr
from copy import deepcopy
from dataclasses import replace
import io
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from hcr import codec
from hcr.model import AdaptiveConfig, ContractError, Mode, fingerprint, Feedback
from hcr.prior_policy import PriorPolicy, policy_fields, read_scope
from hcr.runtime import AdaptiveEngine
from hcr.sessions import AdaptiveSession, verify_packet
from hcr.evaluation.prior_spec import fixtures, cells, TRAINING_COUNTS, ARMS, arm_options, condition_plan
from hcr.evaluation.prior_protocol import run_task, run_fixed, run_demo, verify_run
from hcr.evaluation.prior_audit import verify_task, verify_fixed, audit_packet
from hcr.evaluation.prior_analysis import record_metrics, structural_universe
from hcr.evaluation.reference import reachable
from r02_helpers import train_r02


def clean(d):
    d=deepcopy(codec.plain(d));d['cost'].pop('wall_seconds');return d


class PolicyContracts(unittest.TestCase):
    def test_bad_scopes_rejected(self):
        for s in ('graph_only','',None,True,1,{'judgment_scope':'legacy'}):
            with self.subTest(scope=s),self.assertRaises(ContractError):PriorPolicy(s)
    def test_policy_checksum(self):
        p=policy_fields('route_only');p['prior_policy']['sha256']='f'*64
        with self.assertRaises(ContractError):read_scope(p)
    def test_unknown_policy_fields(self):
        p=policy_fields('route_only');p['prior_policy']['truth']=True
        with self.assertRaises(ContractError):read_scope(p)
    def test_legacy_historical_omission(self):
        self.assertEqual(policy_fields('legacy'),{});self.assertEqual(read_scope({}),'legacy')
    def test_no_fake_explicit_legacy_policy(self):
        with self.assertRaises(ContractError):read_scope({'prior_policy':PriorPolicy('legacy').document()})
    def test_policy_signature_separate_from_memory(self):
        self.assertNotEqual(PriorPolicy('legacy').document(),PriorPolicy('route_only').document())
        a=AdaptiveEngine();b=AdaptiveEngine(judgment_prior='route_only')
        self.assertEqual(a.config.signature,b.config.signature);self.assertEqual(a.memory.document(),b.memory.document())
    def test_policy_is_read_only(self):
        e=AdaptiveEngine()
        with self.assertRaises(AttributeError):e.judgment_prior='route_only'
    def test_engine_rejects_bad_scope(self):
        with self.assertRaises(ContractError):AdaptiveEngine(judgment_prior='foo')
    def test_direct_default_trace_unchanged(self):
        obs=codec.observation_from(fixtures()[0]['observation'])
        a=AdaptiveEngine();b=AdaptiveEngine(judgment_prior='legacy')
        self.assertEqual(a.trace.records,b.trace.records);self.assertEqual(clean(a.infer(obs)),clean(b.infer(obs)))
    def test_hidden_truth_not_public_observation(self):
        raw=deepcopy(fixtures()[0]['observation']);raw['truth']=False
        with self.assertRaises(ContractError):codec.observation_from(raw)


class ScopedBehavior(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg=AdaptiveConfig();cls.memory=train_r02(6).memory
        cls.case=next(c for c in fixtures() if c['name']=='sweep_weak_negative')
        cls.raw={a:run_task(cls.cfg,cls.memory,6,cls.case,a) for a in ARMS}
    def test_scope_audits(self):
        for a,r in self.raw.items():
            with self.subTest(arm=a):self.assertTrue(verify_task(r,self.case,6,a,self.memory.document(),self.cfg)[0]['verified'])
    def test_initial_pool_macro_unchanged(self):
        a,b=[record_metrics(self.raw[k]) for k in ('legacy','route_only')]
        self.assertEqual(a['first_routing'],b['first_routing']);self.assertGreater(b['circuit_reuses'],0)
        self.assertEqual(a['pool_candidates'],b['pool_candidates'])
    def test_only_judgment_drive_disabled(self):
        a,b=[record_metrics(self.raw[k]) for k in ('legacy','route_only')]
        self.assertEqual(a['judgment_networks'][0]['observation_drive'],b['judgment_networks'][0]['observation_drive'])
        self.assertTrue(any(a['judgment_networks'][0]['judgment_drive'].values()))
        self.assertFalse(any(b['judgment_networks'][0]['judgment_drive'].values()))
    def test_counterexample_not_fixed_by_host(self):
        self.assertIs(self.raw['legacy']['decision']['value'],True)
        self.assertIs(self.raw['route_only']['decision']['value'],False)
        self.assertIs(self.raw['graph_only']['decision']['value'],False)
    def test_memory_frozen(self):
        for r in self.raw.values():self.assertEqual(r['packet']['document']['engine']['memory'],self.memory.document())
    def test_primitive_d_not_macro_hops(self):
        for a in ARMS:
            r=self.raw[a];self.assertEqual(r['decision']['proof']['primitive_depth'],3 if a=='legacy' else 2)
    def test_graph_only_does_not_use_pool(self):
        m=record_metrics(self.raw['graph_only']);self.assertEqual(m['pool_ticks'],0);self.assertEqual(m['circuit_reuses'],0)
    def test_disabled_is_not_suppression(self):
        m=record_metrics(self.raw['graph_only']);cs=[c for q in m['funnel'] for c in q.get('candidates',[])]
        self.assertTrue(cs);self.assertTrue(all(c['reasons']==['circuit_policy_disabled'] for c in cs))
    def test_memory_strength_and_balance_are_recorded(self):
        m=record_metrics(self.raw['legacy'])
        self.assertTrue(all(c['evidence_count']==6 and c['balance']==6/7 for c in m['memory_circuits']))
    def test_trace_cost_split(self):
        for r in self.raw.values():
            m=record_metrics(r);self.assertEqual(m['pool_ticks']+m['decision_ticks'],r['decision']['cost']['kernel_ticks'])
    def test_raw_policy_cannot_be_changed(self):
        r=deepcopy(self.raw['route_only']);r['judgment_prior']='legacy'
        with self.assertRaises(ContractError):verify_task(r,self.case,6,'route_only',self.memory.document(),self.cfg)
    def test_integer_switch_cannot_impersonate_bool(self):
        r=deepcopy(self.raw['legacy']);r['use_circuits']=1
        with self.assertRaises(ContractError):verify_task(r,self.case,6,'legacy',self.memory.document(),self.cfg)
    def test_decision_substitution_rejected(self):
        r=deepcopy(self.raw['route_only']);r['decision']['value']=True
        with self.assertRaises(ContractError):verify_task(r,self.case,6,'route_only',self.memory.document(),self.cfg)
    def test_same_public_input_two_hidden_worlds(self):
        c=next(c for c in fixtures() if c['name']=='all_missing')
        r=run_task(self.cfg,self.memory,6,c,'legacy');_,a=verify_task(r,c,6,'legacy',self.memory.document(),self.cfg)
        self.assertEqual(len(a),2);self.assertEqual({v['correct'] for v in a.values()},{True,False})
    def test_all_missing_route_only_guard(self):
        c=next(c for c in fixtures() if c['name']=='all_missing')
        r=run_task(self.cfg,self.memory,6,c,'route_only')
        self.assertIsNone(r['decision']['value']);self.assertTrue(record_metrics(r)['readout_support_guard'])
        self.assertTrue(verify_task(r,c,6,'route_only',self.memory.document(),self.cfg)[0]['verified'])
    def test_all_zero_separate_from_missing(self):
        cs={c['name']:c for c in fixtures()}
        a,b=cs['all_zero'],cs['all_missing']
        self.assertNotEqual(a['observation'],b['observation'])
        r=run_task(self.cfg,self.memory,6,a,'route_only');m=record_metrics(r)
        self.assertEqual(m['zero_slots'],[0,1,2]);self.assertEqual(m['missing_slots'],[]);self.assertIsNone(m['value'])
    def test_positive_preservation(self):
        for name in ('familiar','longer','diamond','renamed_reordered'):
            c=next(c for c in fixtures() if c['name']==name)
            r=run_task(self.cfg,self.memory,6,c,'route_only')
            with self.subTest(case=name):self.assertTrue(verify_task(r,c,6,'route_only',self.memory.document(),self.cfg)[1]['declared']['correct'])


class ScopeState(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.memory=train_r02(6).memory
    def session(self):
        s=AdaptiveSession(memory=self.memory,session_id='scope-state',judgment_prior='route_only')
        s.begin(codec.observation_from(next(c for c in fixtures() if c['name']=='longer')['observation']));s.advance();return s
    def test_new_policy_schema(self):self.assertEqual(self.session().packet()['schema'],'hcr-session-checkpoint-r031-v1')
    def test_restore_pending_policy(self):
        s=self.session();r=AdaptiveSession.from_packet(s.packet(),expected_judgment_prior='route_only')
        self.assertEqual(clean(s.complete()),clean(r.complete()));self.assertTrue(verify_packet(r.packet())['verified'])
    def test_expected_scope_rejected(self):
        with self.assertRaises(ContractError):AdaptiveSession.from_packet(self.session().packet(),expected_judgment_prior='legacy')
    def test_old_schema_cannot_hide_policy(self):
        p=self.session().packet();p['schema']='hcr-session-checkpoint-r021-v1'
        with self.assertRaises(ContractError):verify_packet(p)
    def test_missing_policy_rejected(self):
        p=self.session().packet();p['document']['engine'].pop('prior_policy');p['sha256']=fingerprint(p['document'])
        with self.assertRaises(ContractError):verify_packet(p)
    def test_missing_pending_policy_rejected(self):
        p=self.session().packet();p['document']['engine']['pending'].pop('prior_policy');p['sha256']=fingerprint(p['document'])
        with self.assertRaises(ContractError):verify_packet(p)
    def test_source_guard_not_bypassed(self):
        p=self.session().packet();p['document']['source_hashes']['src/hcr/prior_policy.py']='f'*64;p['sha256']=fingerprint(p['document'])
        with self.assertRaises(ContractError):AdaptiveSession.from_packet(p)
    def test_source_guard_cannot_disable_on_load(self):
        with self.assertRaises(ContractError):AdaptiveSession.from_packet(self.session().packet(),check_source=False)
    def test_policy_mutation_mid_attempt_rejected(self):
        s=self.session();s._engine._judgment_prior='legacy'
        with self.assertRaises(ContractError):s.advance()
    def test_byte_snapshot_roundtrip(self):
        s=self.session()
        with tempfile.TemporaryDirectory(prefix='한글 공백 ') as td:
            p=Path(td)/'packet.json';s.save(p);r=AdaptiveSession.load(p)
            self.assertEqual(s.current,r.current);self.assertEqual(clean(s.complete()),clean(r.complete()))
    def test_freeze_learning_rejected(self):
        s=self.session();d=s.complete()
        with self.assertRaises(ContractError):s.feedback(Feedback('f',d.id,d.observation_digest,True,True))
    def test_priority_and_policy_survive_together(self):
        s=AdaptiveSession(memory=self.memory,judgment_prior='route_only');c=next(c for c in fixtures() if c['name']=='diamond')
        s.begin(codec.observation_from(c['observation']));s.prioritize_frontier([])
        p=s.packet();self.assertEqual(p['schema'],'hcr-session-checkpoint-r031-v1')
        self.assertTrue(verify_packet(p)['verified']);self.assertEqual(clean(s.complete()),clean(AdaptiveSession.from_packet(p).complete()))


class FixedDiagnostic(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cfg=AdaptiveConfig();memory=train_r02(6).memory
        case=next(c for c in fixtures() if c['name']=='sweep_weak_negative')
        cls.legacy=run_task(cfg,memory,6,case,'legacy');cls.a=run_fixed(cls.legacy,'legacy');cls.b=run_fixed(cls.legacy,'route_only')
    def test_fixed_pair_audit(self):
        self.assertTrue(verify_fixed(self.a,self.legacy)['verified']);self.assertTrue(verify_fixed(self.b,self.legacy)['verified'])
    def test_fixed_program_and_initial_state(self):
        self.assertEqual(self.a['program'],self.b['program']);self.assertEqual(self.a['initial'],self.b['initial'])
    def test_fixed_state_differs(self):self.assertGreater(self.a['state']['goal'],.5);self.assertLess(self.b['state']['goal'],.5)
    def test_drive_tamper(self):
        r=deepcopy(self.b);r['drives']['goal']=1
        with self.assertRaises(ContractError):verify_fixed(r,self.legacy)
    def test_initial_tamper(self):
        r=deepcopy(self.b);r['initial']['goal']=.9
        with self.assertRaises(ContractError):verify_fixed(r,self.legacy)
    def test_missing_tick(self):
        r=deepcopy(self.b);r['events'].pop(1)
        with self.assertRaises(ContractError):verify_fixed(r,self.legacy)
    def test_wrong_source_reference(self):
        r=deepcopy(self.b);r['source_ref']['event_seq']+=1
        with self.assertRaises(ContractError):verify_fixed(r,self.legacy)
    def test_fake_endpoint(self):
        r=deepcopy(self.b);r['state']['goal']=.8
        with self.assertRaises(ContractError):verify_fixed(r,self.legacy)
    def test_rehashed_tick_tamper(self):
        r=deepcopy(self.b);r['events'][1]['payload']['state']['goal']=.9;head='0'*64
        for e in r['events']:
            e['previous']=head;e['sha256']=fingerprint({k:v for k,v in e.items() if k!='sha256'});head=e['sha256']
        with self.assertRaises(ContractError):verify_fixed(r,self.legacy)


class ExperimentContracts(unittest.TestCase):
    def test_matrix(self):self.assertEqual(len(list(cells())),117);self.assertEqual(len(fixtures()),13)
    def test_no_duplicate_cells(self):self.assertEqual(len({(n,c['name'],a) for n,c,a in cells()}),117)
    def test_sweep_topology_constant(self):
        xs=[c for c in fixtures() if c['family']=='score_sweep'];a=xs[0]['observation']
        for c in xs:
            b=c['observation'];self.assertEqual(a['edges'][1:],b['edges'][1:])
            self.assertEqual({k:v for k,v in a.items() if k!='edges'},{k:v for k,v in b.items() if k!='edges'})
    def test_twins_have_different_truth(self):
        for c in fixtures():
            if c['paired_hidden_worlds']:
                obs=codec.observation_from(c['observation'])
                self.assertEqual({reachable(obs,t) for t in c['worlds'].values()},{False,True})
    def test_unknown_arm(self):
        with self.assertRaises(ValueError):arm_options('secret')
    def test_output_existing_rejected(self):
        with tempfile.TemporaryDirectory() as d,self.assertRaises(FileExistsError):run_demo(Path(d))
    def test_output_sealed_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'manifest.json').write_bytes(b'{}')
            with self.assertRaises(ContractError):run_demo(p/'child')
    def test_auditor_has_no_production_calls(self):
        p=ROOT/'src/hcr/evaluation/prior_audit.py';tree=ast.parse(p.read_text(encoding='utf-8'))
        imports=[n.module for n in ast.walk(tree) if isinstance(n,ast.ImportFrom)]
        self.assertFalse(any(m and m.endswith(('runtime','dynamics','learning','workspace','sessions')) for m in imports))
    def test_cli_help(self):
        from hcr.cli import main
        out=io.StringIO();err=io.StringIO()
        with redirect_stdout(out),redirect_stderr(err),self.assertRaises(SystemExit) as c:main(['priors','--help'])
        self.assertEqual(c.exception.code,0);self.assertIn('demo',out.getvalue());self.assertFalse(err.getvalue())
    def test_cli_plan_no_inference(self):
        from hcr.cli import main
        out=io.StringIO()
        with patch('hcr.runtime.AdaptiveEngine.infer',side_effect=AssertionError('inference')),redirect_stdout(out):self.assertEqual(main(['priors','plan']),0)
        self.assertFalse(codec.loads(out.getvalue())['inference_executed'])
    def test_session_cli_policy_option(self):
        from hcr.session_cli import main
        out=io.StringIO()
        with redirect_stdout(out),self.assertRaises(SystemExit):main(['start','--help'])
        self.assertIn('--judgment-prior',out.getvalue())


class FullProtocol(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='hcr-r031-audit-')
        cls.root=Path(cls.temp.name)/'run'
        cls.receipt=run_demo(cls.root)
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()
    def copy_run(self):
        p=Path(self.temp.name)/self._testMethodName;shutil.copytree(self.root,p);return p
    def rehash(self,p):
        import hashlib
        manifest=codec.loads((p/'manifest.json').read_bytes())
        for name in manifest['files']:manifest['files'][name]=hashlib.sha256((p/name).read_bytes()).hexdigest()
        (p/'manifest.json').write_bytes((codec.dumps(manifest)+'\n').encode())
    def test_complete_counts(self):
        self.assertEqual(self.receipt['new_task_inferences'],117)
        self.assertEqual(self.receipt['new_training_inferences'],9)
        self.assertEqual(self.receipt['new_fixed_network_replays'],78)
        self.assertEqual(self.receipt['audit_new_inferences'],0)
    def test_same_run_reaudit(self):self.assertTrue(verify_run(self.root)['verified'])
    def test_extra_file_rejected(self):
        p=self.copy_run();(p/'unexpected.txt').write_bytes(b'x')
        with self.assertRaises(ContractError):verify_run(p)
    def test_failed_run_rejected(self):
        p=self.copy_run();(p/'FAILED.json').write_bytes(b'{}')
        with self.assertRaises(ContractError):verify_run(p)
    def test_summary_rehashed_still_rejected(self):
        p=self.copy_run();s=codec.loads((p/'summary.json').read_bytes());s['task_inferences']=1
        (p/'summary.json').write_bytes((codec.dumps(s)+'\n').encode());self.rehash(p)
        with self.assertRaises(ContractError):verify_run(p)
    def test_external_truth_rehashed_rejected(self):
        p=self.copy_run();file=p/'records/3/sweep_strong_negative/legacy.json';s=codec.loads(file.read_bytes())
        s['assessments']['declared']['correct']=not s['assessments']['declared']['correct']
        file.write_bytes((codec.dumps(s)+'\n').encode());self.rehash(p)
        with self.assertRaises(ContractError):verify_run(p)
    def test_csv_rehashed_rejected(self):
        p=self.copy_run();file=p/'costs.csv';file.write_bytes(file.read_bytes().replace(b'legacy',b'forged',1));self.rehash(p)
        with self.assertRaises(ContractError):verify_run(p)
    def test_location_independent(self):
        p=self.copy_run();self.assertTrue(verify_run(p)['verified'])


class PythonLauncher(unittest.TestCase):
    def load(self):
        import importlib.util
        spec=importlib.util.spec_from_file_location('r031_launcher',ROOT/'scripts/legacy/Run-HCR-R031.py')
        m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
    def test_discovery_import_environment(self):
        commands=self.load().commands(Path('new-run'))
        self.assertIn(['hcr.py','check'],commands)
        self.assertFalse(any('tests.test_' in ' '.join(c) for c in commands))
    def test_check_only_no_demo(self):
        commands=self.load().commands(None)
        self.assertFalse(any('demo' in c or 'priors' in c for c in commands))
    def test_native_failure_stops_next_command(self):
        import subprocess
        m=self.load();error=subprocess.CalledProcessError(2,['python'])
        with patch.object(m.subprocess,'run',side_effect=error) as call,redirect_stdout(io.StringIO()),redirect_stderr(io.StringIO()):
            self.assertEqual(m.main(['--check-only']),2);self.assertEqual(call.call_count,1)
    def test_existing_output_stops_before_tests(self):
        m=self.load()
        with tempfile.TemporaryDirectory() as d,patch.object(m.subprocess,'run') as call,redirect_stderr(io.StringIO()):
            self.assertEqual(m.main(['--out',d]),2);call.assert_not_called()
