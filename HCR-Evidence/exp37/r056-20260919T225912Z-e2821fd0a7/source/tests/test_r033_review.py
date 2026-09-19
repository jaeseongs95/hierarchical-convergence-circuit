"""R0.3.3 실제 경계 계속 실행, 관측 계약, 독립 검산의 회귀시험."""
from __future__ import annotations
from contextlib import redirect_stdout,redirect_stderr
from copy import deepcopy
from dataclasses import replace
import io
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from hcr import codec
from hcr.model import AdaptiveConfig,ContractError,Mode,fingerprint
from hcr.review import (ReviewLimits,ReviewFlow,POLICIES,prepare_baseline,verify_baseline,
    measurement_request,consume_measurement,sealed)
from hcr.sessions import AdaptiveSession,verify_packet
from hcr.evaluation.grounding_spec import fixtures
from hcr.evaluation.review_spec import condition_plan,cells,provider_for
from hcr.evaluation.review_audit import audit_rollout,assess_rollout
from r02_helpers import train_r02


def rechain(records):
    previous='0'*64
    for i,r in enumerate(records):
        body=dict(seq=i,previous=previous,event=r['event'],payload=r['payload'])
        previous=fingerprint(body);r.clear();r.update(body,sha256=previous)


class ReviewFixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg=AdaptiveConfig();cls.memory=train_r02(6,cls.cfg).memory
        cls.cases={c['name']:c for c in fixtures()}
        cls.base={}
        for name in ('irrelevant_missing','critical_missing','weak_negative','known_cut_missing','two_branch_cut','strong_positive','misleading_direction'):
            for scope in ('legacy','route_only'):
                cls.base[name,scope]=prepare_baseline(codec.observation_from(cls.cases[name]['observation']),cls.cfg,cls.memory,judgment_prior=scope)

    def flow(self,name,policy,scope='legacy',mode='perfect',limits=None,world=None):
        c=self.cases[name];world=world or next(iter(c['worlds']))
        b=self.base[name,scope];r=ReviewFlow(b,policy,limits).run(provider_for(c['observation'],c['worlds'][world],mode))
        audit_rollout(b,r,world=c['worlds'][world],provider_mode=mode)
        return r


class ContinueContracts(ReviewFixture):
    def session(self,name='irrelevant_missing'):
        return AdaptiveSession.from_packet(self.base[name,'legacy']['ready'])

    def test_fork_preserves_live_state(self):
        s=self.session();p=s.packet();d,f=s.fork_readout()
        self.assertEqual(s.packet(),p);self.assertEqual(f['document']['events'][-1]['payload'],codec.plain(d));verify_packet(f)

    def test_continue_preserves_frontier_bindings_and_cost(self):
        s=self.session();before=s.current;s.continue_dependency();after=s.current
        p=after['pending'];expected=deepcopy(before);expected['pending']['ready']=False;expected['pending']['value']=None
        self.assertEqual(after,expected);self.assertEqual(p['cost'],before['pending']['cost']);verify_packet(s.packet())

    def test_extra_step_not_initial_replay(self):
        s=self.session();before=s.current['pending'];s.continue_dependency();s.advance()
        after=s.current['pending'];self.assertEqual(after['cost']['expansions'],before['cost']['expansions']+1)
        self.assertEqual(after['workspace']['routes'][:len(before['workspace']['routes'])],before['workspace']['routes'])
        verify_packet(s.packet())

    def test_continuation_snapshot_load(self):
        s=self.session();s.continue_dependency();p=s.packet();restored=AdaptiveSession.from_packet(p)
        self.assertEqual(restored.current,s.current);restored.advance();verify_packet(restored.packet())

    def test_continuation_json_file(self):
        s=self.session();s.continue_dependency()
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'state.json';s.save(path);s2=AdaptiveSession.load(path);self.assertEqual(s2.current,s.current)

    def test_no_remaining_frontier_rejected(self):
        s=self.session('critical_missing');p=s.packet()
        with self.assertRaises(ContractError):s.continue_dependency()
        self.assertEqual(s.packet(),p)

    def test_running_continue_rejected(self):
        s=self.session();s.continue_dependency();p=s.packet()
        with self.assertRaises(ContractError):s.continue_dependency()
        self.assertEqual(s.packet(),p)

    def test_idle_continue_rejected(self):
        s=self.session();s.finish()
        with self.assertRaises(ContractError):s.continue_dependency()

    def test_fork_requires_ready(self):
        s=self.session();s.continue_dependency()
        with self.assertRaises(ContractError):s.fork_readout()

    def test_training_continue_rejected(self):
        s=AdaptiveSession(self.cfg,self.memory);s.begin(codec.observation_from(self.cases['irrelevant_missing']['observation']),Mode.TRAIN)
        while s.phase=='running':s.advance()
        with self.assertRaises(ContractError):s.continue_dependency()

    def test_schema_cannot_hide_continue(self):
        s=self.session();s.continue_dependency();p=s.packet();p['schema']='hcr-session-checkpoint-r021-v1'
        with self.assertRaises(ContractError):verify_packet(p)

    def test_forged_pending_cost_rejected(self):
        s=self.session();s.continue_dependency();p=s.packet();p['document']['engine']['pending']['cost']['kernel_ticks']=0
        p['sha256']=fingerprint(p['document'])
        with self.assertRaises(ContractError):verify_packet(p)

    def test_first_readout_matches_normal_infer(self):
        from hcr.runtime import AdaptiveEngine
        c=self.cases['critical_missing'];d=AdaptiveEngine(self.cfg,deepcopy(self.memory)).infer(codec.observation_from(c['observation']))
        a=codec.plain(d);b=deepcopy(self.base['critical_missing','legacy']['first']['decision'])
        a['cost'].pop('wall_seconds');b['cost'].pop('wall_seconds');self.assertEqual(a,b)


class FlowContracts(ReviewFixture):
    def test_hold_preserves_first_and_does_no_extra_work(self):
        r=self.flow('critical_missing','hold');self.assertEqual(r['candidates'][0],self.base['critical_missing','legacy']['first'])
        self.assertEqual(r['usage'],dict(extra_advances=0,extra_kernel_ticks=0,measurements=0,restarts=0));self.assertIsNone(r['result']['value'])

    def test_extra_expansion_can_fail_without_answer_repair(self):
        r=self.flow('irrelevant_missing','expand_only');self.assertEqual(r['usage']['extra_advances'],1)
        self.assertEqual(r['usage']['measurements'],0);self.assertIsNone(r['result']['value'])
        self.assertGreater(len(r['candidates'][-1]['decision']['expanded_paths']),len(r['candidates'][0]['decision']['expanded_paths']))

    def test_route_review_is_real_paid_computation(self):
        r=self.flow('irrelevant_missing','route_review');self.assertIs(r['result']['value'],True)
        self.assertEqual(r['usage']['restarts'],1);self.assertEqual(r['usage']['measurements'],0)
        self.assertGreater(r['usage']['extra_kernel_ticks'],0)

    def test_weak_conflict_review_changes_value_not_original(self):
        r=self.flow('weak_negative','route_review');self.assertIs(r['candidates'][0]['decision']['value'],True)
        self.assertIs(r['result']['value'],False)

    def test_critical_missing_needs_information(self):
        r=self.flow('critical_missing','route_review');self.assertIsNone(r['result']['value']);self.assertEqual(r['usage']['measurements'],0)
        r=self.flow('critical_missing','expand_then_observe');self.assertIs(r['result']['value'],True);self.assertEqual(r['usage']['measurements'],1)

    def test_same_initial_input_opposite_worlds_separate_after_query(self):
        a=self.flow('critical_missing','observe_first',world='first_open')
        b=self.flow('critical_missing','observe_first',world='first_closed')
        self.assertEqual(a['candidates'][0],b['candidates'][0]);self.assertIs(a['result']['value'],True);self.assertIs(b['result']['value'],False)

    def test_supported_negative_no_queries(self):
        for name in ('known_cut_missing','two_branch_cut'):
            for policy in POLICIES:
                r=self.flow(name,policy);self.assertIs(r['result']['value'],False);self.assertEqual(r['usage']['extra_advances'],0);self.assertEqual(r['usage']['measurements'],0)

    def test_irrelevant_missing_supported_initial_no_work(self):
        r=self.flow('irrelevant_missing','expand_then_observe',scope='route_only');self.assertIs(r['result']['value'],True);self.assertEqual(r['usage']['restarts'],0)

    def test_observation_error_not_hidden(self):
        r=self.flow('misleading_direction','expand_then_observe');a=assess_rollout(self.base['misleading_direction','legacy'],r,self.cases['misleading_direction']['worlds']['declared'])
        self.assertIs(a['external_correct'],False);self.assertIs(r['result']['value'],True);self.assertEqual(r['usage']['measurements'],0)

    def test_no_change_does_not_retry(self):
        r=self.flow('critical_missing','expand_then_observe',mode='unchanged');self.assertEqual(r['result']['reason'],'measurement_no_new_information')
        self.assertEqual(r['usage']['measurements'],1);self.assertEqual(r['usage']['restarts'],0)

    def test_unavailable_does_not_retry(self):
        r=self.flow('critical_missing','observe_first',mode='unavailable');self.assertEqual(r['result']['reason'],'measurement_unavailable');self.assertEqual(r['usage']['restarts'],0)

    def test_zero_work_does_not_query(self):
        r=self.flow('critical_missing','expand_then_observe',limits=ReviewLimits(max_extra_advances=0))
        self.assertEqual(r['usage']['measurements'],0);self.assertIsNone(r['result']['value'])

    def test_zero_ticks_does_not_query(self):
        r=self.flow('critical_missing','observe_first',limits=ReviewLimits(max_extra_kernel_ticks=0));self.assertEqual(r['usage']['measurements'],0)

    def test_zero_measurement_budget(self):
        r=self.flow('critical_missing','observe_first',limits=ReviewLimits(max_measurements=0));self.assertEqual(r['result']['reason'],'stop_measurement_budget')

    def test_restart_does_not_reset_work_limit(self):
        r=self.flow('critical_missing','observe_first',limits=ReviewLimits(max_extra_advances=1))
        self.assertLessEqual(r['usage']['extra_advances'],1);self.assertIsNone(r['result']['value'])

    def test_cumulative_cost_not_repeated_per_readout(self):
        r=self.flow('irrelevant_missing','expand_only');self.assertEqual(r['cost']['engine']['kernel_ticks'],r['cost']['initial_kernel_ticks']+r['usage']['extra_kernel_ticks'])
        self.assertGreater(sum(c['decision']['cost']['kernel_ticks'] for c in r['candidates']),r['cost']['engine']['kernel_ticks'])

    def test_candidate_global_ids_unique(self):
        r=self.flow('irrelevant_missing','expand_only');ids=[c['candidate_id'] for c in r['candidates']]
        self.assertEqual(len(ids),len(set(ids)));self.assertEqual(r['candidates'][0]['decision']['id'],r['candidates'][1]['decision']['id'])

    def test_caller_baseline_not_modified(self):
        b=self.base['critical_missing','legacy'];before=deepcopy(b);ReviewFlow(b,'hold').run();self.assertEqual(b,before)

    def test_single_use_controller(self):
        flow=ReviewFlow(self.base['critical_missing','legacy'],'hold');flow.run()
        with self.assertRaises(ContractError):flow.run()

    def test_negative_bool_and_excess_limits_rejected(self):
        for args in [dict(max_extra_advances=True),dict(max_measurements=-1),dict(max_extra_kernel_ticks=100001)]:
            with self.subTest(args=args),self.assertRaises(ContractError):ReviewLimits(**args)

    def test_unknown_policy_rejected(self):
        with self.assertRaises(ContractError):ReviewFlow(self.base['critical_missing','legacy'],'always_correct')

    def test_tampered_baseline_gate_rejected(self):
        b=deepcopy(self.base['critical_missing','legacy']);b['first']['readout']['accepted']=True
        b=sealed({k:v for k,v in b.items() if k!='sha256'})
        with self.assertRaises(ContractError):verify_baseline(b)


class MeasurementContracts(unittest.TestCase):
    def setUp(self):
        self.obs=codec.observation_from(next(c['observation'] for c in fixtures() if c['name']=='critical_missing'))
        self.req=measurement_request(self.obs,dict(candidate_id='candidate'),1,'e0')
        self.reply=dict(request_sha256=self.req['sha256'],status='measured',scores={'e0':.98},source='test_sensor')

    def test_revision_and_topology_scope(self):
        obs,status=consume_measurement(self.obs,self.req,self.reply)
        self.assertEqual(obs.revision,1);self.assertEqual(obs.edges[1:],self.obs.edges[1:]);self.assertEqual(status,'measurement_applied')

    def test_wrong_request_rejected(self):
        self.reply['request_sha256']='0'*64
        with self.assertRaises(ContractError):consume_measurement(self.obs,self.req,self.reply)

    def test_extra_edge_rejected(self):
        self.reply['scores']['e1']=-.98
        with self.assertRaises(ContractError):consume_measurement(self.obs,self.req,self.reply)

    def test_missing_edge_rejected(self):
        self.reply['scores']={}
        with self.assertRaises(ContractError):consume_measurement(self.obs,self.req,self.reply)

    def test_nonfinite_and_bool_score_rejected(self):
        for v in (float('nan'),float('inf'),True,1.1):
            self.reply['scores']['e0']=v
            with self.subTest(v=v),self.assertRaises(ContractError):consume_measurement(self.obs,self.req,self.reply)

    def test_unavailable_must_be_empty(self):
        self.reply['status']='unavailable'
        with self.assertRaises(ContractError):consume_measurement(self.obs,self.req,self.reply)

    def test_source_required(self):
        self.reply['source']=''
        with self.assertRaises(ContractError):consume_measurement(self.obs,self.req,self.reply)

    def test_unknown_response_field_rejected(self):
        self.reply['hidden_truth']={'e0':True}
        with self.assertRaises(ContractError):consume_measurement(self.obs,self.req,self.reply)

    def test_no_information_keeps_revision(self):
        self.reply['scores']['e0']=None;new,status=consume_measurement(self.obs,self.req,self.reply)
        self.assertIsNone(new);self.assertEqual(status,'measurement_no_new_information');self.assertEqual(self.obs.revision,0)


class AuditContracts(ReviewFixture):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        c=cls.cases['irrelevant_missing'];b=cls.base['irrelevant_missing','legacy']
        cls.raw=ReviewFlow(b,'expand_then_observe').run(provider_for(c['observation'],next(iter(c['worlds'].values())),'perfect'))

    def reject(self,mutation,rechain_trace=False):
        r=deepcopy(self.raw);mutation(r)
        if rechain_trace:rechain(r['controller'])
        with self.assertRaises(ContractError):audit_rollout(self.base['irrelevant_missing','legacy'],r)

    def test_rehashed_controller_action_rejected(self):
        self.reject(lambda r:r['controller'][1]['payload'].__setitem__('action','stop_supported'),True)

    def test_cost_reset_rejected(self):
        self.reject(lambda r:r['cost']['engine'].__setitem__('kernel_ticks',0))

    def test_unexecuted_answer_rejected(self):
        self.reject(lambda r:r['result'].__setitem__('value',False))

    def test_duplicate_candidate_rejected(self):
        self.reject(lambda r:r['candidates'].append(deepcopy(r['candidates'][0])))

    def test_original_replacement_rejected(self):
        self.reject(lambda r:r['candidates'][0]['decision'].__setitem__('value',False))

    def test_extra_segment_rejected(self):
        self.reject(lambda r:r['segments'].append(deepcopy(r['segments'][0])))

    def test_policy_label_replacement_rejected(self):
        self.reject(lambda r:r.__setitem__('policy','hold'))

    def test_request_target_rehashed_rejected(self):
        def change(r):
            e=next(e for e in r['controller'] if e['event']=='review_measurement_request');e['payload']['edge_ids']=['e0'];e['payload']=sealed({k:v for k,v in e['payload'].items() if k!='sha256'})
        self.reject(change,True)

    def test_negative_timing_rejected(self):
        self.reject(lambda r:r['timing'].__setitem__('review_wall_seconds',-1))

    def test_auditor_no_review_engine_import(self):
        import ast
        t=ast.parse((ROOT/'src/hcr/evaluation/review_audit.py').read_text(encoding='utf-8'))
        imports=[n.module for n in ast.walk(t) if isinstance(n,ast.ImportFrom)]
        self.assertFalse(set(imports)&{'review','runtime','dynamics'})


class PlanCLI(unittest.TestCase):
    def test_default_condition_counts(self):
        p=condition_plan();self.assertEqual(len(cells(p)),142);self.assertEqual(len(p['cases']),8)

    def test_condition_order_survives_json_key_sort(self):
        p=condition_plan()
        self.assertEqual(cells(p),cells(codec.loads(codec.dumps(p))))

    def test_training_extension_is_explicit(self):
        self.assertEqual(len(cells(condition_plan((3,6,9)))),426)
        for values in [(6,3),(True,),(),(6,6),(4,)]:
            with self.subTest(values=values),self.assertRaises(ContractError):condition_plan(values)

    def test_cli_help(self):
        from hcr.cli import main
        out=io.StringIO();err=io.StringIO()
        with redirect_stdout(out),redirect_stderr(err),self.assertRaises(SystemExit) as exc:main(['review','--help'])
        self.assertEqual(exc.exception.code,0);self.assertIn('execute',out.getvalue())

    def test_plan_only_no_inferences(self):
        from hcr.review_cli import main
        with tempfile.TemporaryDirectory() as tmp,redirect_stdout(io.StringIO()):
            path=Path(tmp)/'plan.json';self.assertEqual(main(['plan','--out',str(path)]),0)
            self.assertTrue(path.is_file());self.assertEqual(len(list(Path(tmp).iterdir())),1)

    def test_plan_source_tamper_rejected(self):
        from hcr.evaluation.review_protocol import make_plan,validate_plan
        p=make_plan();p['source_hashes']={}
        with self.assertRaises(ContractError):validate_plan(p)

    def test_launcher_python_discovery(self):
        spec=importlib.util.spec_from_file_location('review_launcher',ROOT/'scripts/legacy/Run-HCR-R033.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        steps=module.commands(Path('HCR-Evidence/exp14/test'))
        self.assertIn(['hcr.py','review','demo','--out',str(Path('HCR-Evidence/exp14/test'))],steps)
        self.assertFalse(any('.ps1' in str(s) for s in steps))


if __name__=='__main__':unittest.main()
