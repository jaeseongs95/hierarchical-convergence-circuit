"""R0.3.2: 근거 진단, 명시적 gate, 원본 보존, 평가기 분리, 파일 재검산."""
from __future__ import annotations
import ast
from contextlib import redirect_stdout,redirect_stderr
from copy import deepcopy
from dataclasses import replace
import io
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from hcr import codec
from hcr.model import AdaptiveConfig,ContractError,Feedback,Mode,fingerprint
from hcr.grounding import SupportContract,classify,diagnose,apply_readout,compare_diagnostics,POLICIES
from hcr.sessions import AdaptiveSession
from hcr.circuits import AdaptiveMemory
from hcr.evaluation.prior_protocol import run_task
from hcr.evaluation.prior_spec import training_world
from hcr.evaluation.reference import assess
from hcr.evaluation.grounding_spec import fixtures,cells,condition_plan,SUPPORT
from hcr.evaluation.grounding_protocol import make_record,make_conflicts,run_demo,verify_run,expected_files,load,file_hash
from hcr.evaluation.grounding_audit import verify_record,verify_diagnostic,verify_readout,verify_conflicts,compatible_worlds


def reseal(d):
    d['sha256']=fingerprint({k:v for k,v in d.items() if k!='sha256'});return d


class SupportContracts(unittest.TestCase):
    def test_contract_does_not_claim_truth(self):
        self.assertEqual(SupportContract().document(),SUPPORT)
        self.assertFalse(SupportContract().document()['support_is_truth'])
    def test_bad_thresholds(self):
        for v in (-.1,1,True,float('inf'),float('nan'),'0'):
            with self.subTest(v=v),self.assertRaises(ContractError):SupportContract(v)
    def test_none_is_not_false_observation(self):self.assertEqual(classify(None,False,SupportContract()),'missing')
    def test_zero_is_neutral(self):
        for v in (0,0.0,-0.0):self.assertEqual(classify(v,False,SupportContract()),'neutral')
    def test_sign_conflict(self):self.assertEqual(classify(-.06,True,SupportContract()),'sign_conflict')
    def test_weak_evidence_is_direction_not_probability(self):self.assertEqual(classify(-.06,False,SupportContract()),'directional_support')
    def test_threshold_is_explicit(self):self.assertEqual(classify(-.06,False,SupportContract(.1)),'below_threshold')
    def test_integer_assumption_rejected(self):
        with self.assertRaises(ContractError):classify(.92,1,SupportContract())
    def test_invalid_scores(self):
        for v in (True,'0',2,float('nan'),float('inf')):
            with self.subTest(v=v),self.assertRaises(ContractError):classify(v,True,SupportContract())
    def test_condition_matrix(self):
        cs=list(cells());self.assertEqual(len(cs),126);self.assertEqual(len({(n,c['name'],a) for n,c,a in cs}),126)
        self.assertEqual(len(fixtures()),14)
    def test_plan_no_hidden_runtime_access(self):
        self.assertFalse(condition_plan()['hidden_truth_passed_to_diagnostic'])
        self.assertEqual(condition_plan()['measurement_requests_executed'],0)
    def test_critical_edge_is_identifiable_only_after_information(self):
        c=next(c for c in fixtures() if c['name']=='critical_missing');r=compatible_worlds(c['observation'])
        self.assertEqual(r['possible_values'],[False,True]);self.assertEqual(r['influential_unknown_edges'],['e0'])
    def test_unknown_off_supported_path_not_influential(self):
        c=next(c for c in fixtures() if c['name']=='irrelevant_missing');r=compatible_worlds(c['observation'])
        self.assertEqual(r['possible_values'],[True]);self.assertEqual(r['influential_unknown_edges'],[])
    def test_known_cut_all_unknown_completions_false(self):
        c=next(c for c in fixtures() if c['name']=='known_cut_missing');r=compatible_worlds(c['observation'])
        self.assertEqual(r['possible_values'],[False]);self.assertEqual(r['worlds_enumerated'],4)


class GroundingBehavior(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg=AdaptiveConfig();s=AdaptiveSession(cls.cfg)
        for i in range(6):
            w=training_world(i);s.begin(w.observation,Mode.TRAIN);d=s.complete();a=assess(d,w.observation,dict(w.hidden))
            s.feedback(Feedback('f-'+d.id,d.id,w.observation.digest,a.correct,a.proof_valid and a.assumption_correct is True))
        cls.memory=s.memory_document;cls.cases={c['name']:c for c in fixtures()};cls.cache={}
    def item(self,name='critical_missing',arm='route_only'):
        key=(name,arm)
        if key not in self.cache:
            c=self.cases[name];raw=run_task(self.cfg,AdaptiveMemory.from_document(self.memory,self.cfg),6,c,arm)
            self.cache[key]=(raw,make_record(raw,c))
        return deepcopy(self.cache[key])
    def test_original_and_memory_preserved(self):
        raw,_=self.item();before=deepcopy(raw);r=make_record(raw,self.cases['critical_missing'])
        self.assertEqual(raw,before);self.assertEqual(raw['initial_memory'],raw['packet']['document']['engine']['memory'])
        self.assertEqual(r['readouts']['diagnostic_only']['value'],raw['decision']['value'])
    def test_returned_diagnostic_cannot_alias_source_binding(self):
        raw,_=self.item('weak_negative');before=deepcopy(raw)
        d=diagnose(codec.observation_from(raw['observation']),codec.adaptive_decision_from(raw['decision']),raw['packet']['document']['events'])
        d['assumptions'][0]['routing_uses'][0]['edge_order'][0]=99
        self.assertEqual(raw,before)
    def test_critical_missing_blocks_only_separate_readout(self):
        raw,r=self.item();self.assertIs(raw['decision']['value'],False)
        self.assertFalse(r['diagnostic']['evidence_support_sufficient']);self.assertIsNone(r['readouts']['dependency_gate']['value'])
    def test_critical_zero_preserved_as_neutral(self):
        _,r=self.item('critical_zero');self.assertEqual(r['diagnostic']['assumptions'][0]['support'],'neutral')
    def test_unknown_elsewhere_not_blanket_abstained(self):
        _,r=self.item('irrelevant_missing');self.assertIs(r['readouts']['dependency_gate']['value'],True)
        self.assertIsNone(r['readouts']['blanket_unknown_gate']['value']);self.assertIn('e2',r['diagnostic']['unknown_outside_selected_proof'])
    def test_known_cut_missing_allowed(self):
        _,r=self.item('known_cut_missing');self.assertIs(r['readouts']['dependency_gate']['value'],False)
        self.assertIsNone(r['readouts']['blanket_unknown_gate']['value'])
    def test_known_cut_zero_allowed(self):
        _,r=self.item('known_cut_zero');self.assertIs(r['readouts']['dependency_gate']['value'],False)
    def test_two_branch_cut_allowed(self):
        _,r=self.item('two_branch_cut');self.assertIs(r['readouts']['dependency_gate']['value'],False)
        self.assertTrue(r['diagnostic']['graph_complete'])
    def test_prior_not_promoted_to_observation(self):
        _,r=self.item('weak_negative','legacy');a=r['diagnostic']['assumptions'][0]
        self.assertEqual(a['support'],'sign_conflict');self.assertGreater(a['goal_learned_drive'],0)
        self.assertIsNone(r['readouts']['dependency_gate']['value'])
    def test_route_only_prior_provenance_separated(self):
        _,r=self.item('weak_negative');a=r['diagnostic']['assumptions'][0]
        self.assertEqual(a['goal_learned_drive'],0);self.assertGreater(a['routing_uses'][0]['routing_prior'],0)
    def test_directional_support_not_external_truth(self):
        _,r=self.item('misleading_direction');self.assertTrue(r['diagnostic']['evidence_support_sufficient'])
        self.assertIs(r['readouts']['dependency_gate']['value'],True)
        self.assertFalse(r['assessment']['policies']['dependency_gate']['external_correct']['declared'])
    def test_no_new_measurement_executed(self):
        _,r=self.item();self.assertEqual(r['diagnostic']['suggestion']['edge_ids'],['e0']);self.assertFalse(r['diagnostic']['suggestion']['executed'])
    def test_all_unknown_keeps_original_abstention(self):
        raw,r=self.item('all_missing');self.assertIsNone(raw['decision']['value']);self.assertIsNone(r['diagnostic']['evidence_support_sufficient'])
        self.assertTrue(all(v['value'] is None for v in r['readouts'].values()))
    def test_no_flipped_answer(self):
        for name in self.cases:
            raw,r=self.item(name)
            self.assertTrue(all(v['value'] is None or v['value'] is raw['decision']['value'] for v in r['readouts'].values()))
    def test_no_new_path_or_proof(self):
        raw,r=self.item('irrelevant_missing','legacy');self.assertFalse(r['diagnostic']['boundaries']['new_paths_generated'])
        self.assertIsNone(r['readouts']['dependency_gate']['value'])
        self.assertEqual(len(r['diagnostic']['explored_path_checks']),len(raw['decision']['expanded_paths']))
    def test_stale_observation_rejected(self):
        raw,_=self.item();obs=codec.observation_from(raw['observation']);d=codec.adaptive_decision_from(raw['decision'])
        with self.assertRaises(ContractError):diagnose(replace(obs,revision=obs.revision+1),d,raw['packet']['document']['events'])
    def test_different_decision_rejected(self):
        raw,_=self.item();d=codec.adaptive_decision_from(raw['decision'])
        with self.assertRaises(ContractError):diagnose(codec.observation_from(raw['observation']),replace(d,id='wrong'),raw['packet']['document']['events'])
    def test_event_mutation_rejected(self):
        raw,_=self.item();events=raw['packet']['document']['events'];events[1]['payload']['attempt']=99
        with self.assertRaises(ContractError):diagnose(codec.observation_from(raw['observation']),codec.adaptive_decision_from(raw['decision']),events)
    def test_empty_source_rejected(self):
        raw,_=self.item()
        with self.assertRaises(ContractError):diagnose(codec.observation_from(raw['observation']),codec.adaptive_decision_from(raw['decision']),[])
    def test_diagnostic_hash_required(self):
        raw,r=self.item();r['diagnostic']['evidence_support_sufficient']=True
        with self.assertRaises(ContractError):apply_readout(codec.adaptive_decision_from(raw['decision']),r['diagnostic'],'dependency_gate')
    def test_unknown_policy_rejected(self):
        raw,r=self.item()
        with self.assertRaises(ContractError):apply_readout(codec.adaptive_decision_from(raw['decision']),r['diagnostic'],'repair')
    def test_different_contracts_not_compared(self):
        raw,r=self.item();other=deepcopy(r['diagnostic']);other['contract']['min_abs_score']=.5;reseal(other)
        with self.assertRaises(ContractError):compare_diagnostics({'a':r['diagnostic'],'b':other})
    def test_different_memories_not_compared(self):
        _,r=self.item();other=deepcopy(r['diagnostic']);other['source']['memory_digest']='f'*64;reseal(other)
        with self.assertRaises(ContractError):compare_diagnostics({'a':r['diagnostic'],'b':other})
    def test_agreement_can_have_support_gap(self):
        _,a=self.item();_,b=self.item(arm='graph_only');c=compare_diagnostics({'r':a['diagnostic'],'g':b['diagnostic']})
        self.assertEqual(c['status'],'agreement_with_support_gap');self.assertEqual(c['assumption_conflicts'],[])
    def test_conflicting_assumption_localized(self):
        _,a=self.item('weak_negative','legacy');_,b=self.item('weak_negative','route_only')
        c=compare_diagnostics({'l':a['diagnostic'],'r':b['diagnostic']});self.assertEqual(c['status'],'decision_conflict')
        self.assertEqual([x['edge_id'] for x in c['assumption_conflicts']],['e0']);verify_conflicts({'l':a['diagnostic'],'r':b['diagnostic']},c)
    def test_formal_proof_and_support_are_separate(self):
        raw,r=self.item();report=verify_record(raw,r,self.cases['critical_missing'],6,'route_only',self.memory,self.cfg)
        self.assertTrue(report['proof']['logical_proof_valid']);self.assertFalse(r['diagnostic']['evidence_support_sufficient'])
    def test_rehashed_false_support_rejected(self):
        raw,r=self.item();r['diagnostic']['evidence_support_sufficient']=True;reseal(r['diagnostic'])
        with self.assertRaises(ContractError):verify_diagnostic(raw,r['diagnostic'])
    def test_rehashed_provenance_rejected(self):
        raw,r=self.item();r['diagnostic']['source']['memory_digest']='f'*64;reseal(r['diagnostic'])
        with self.assertRaises(ContractError):verify_diagnostic(raw,r['diagnostic'])
    def test_rehashed_drive_rejected(self):
        raw,r=self.item();r['diagnostic']['assumptions'][0]['goal_learned_drive']=9;reseal(r['diagnostic'])
        with self.assertRaises(ContractError):verify_diagnostic(raw,r['diagnostic'])
    def test_rehashed_proposed_action_execution_rejected(self):
        raw,r=self.item();r['diagnostic']['suggestion']['executed']=True;reseal(r['diagnostic'])
        with self.assertRaises(ContractError):verify_diagnostic(raw,r['diagnostic'])
    def test_rehashed_answer_flip_rejected(self):
        raw,r=self.item();v=r['readouts']['dependency_gate'];v['value']=True;reseal(v)
        with self.assertRaises(ContractError):verify_readout(raw,r['diagnostic'],v,'dependency_gate')
    def test_integer_for_boolean_rejected_by_readout_audit(self):
        raw,r=self.item('strong_positive');v=r['readouts']['dependency_gate'];v['accepted']=1;reseal(v)
        with self.assertRaises(ContractError):verify_readout(raw,r['diagnostic'],v,'dependency_gate')
    def test_rehashed_world_assessment_rejected(self):
        raw,r=self.item();r['assessment']['policies']['dependency_gate']['external_correct']['first_open']=True
        with self.assertRaises(ContractError):verify_record(raw,r,self.cases['critical_missing'],6,'route_only',self.memory,self.cfg)
    def test_diagnostic_repeats_do_not_change_packet(self):
        raw,r=self.item();before=deepcopy(raw);r2=make_record(raw,self.cases['critical_missing'])
        self.assertEqual(raw,before);self.assertEqual(r2['diagnostic'],r['diagnostic']);self.assertEqual(r2['readouts'],r['readouts'])
    def test_production_has_no_evaluator_dependency(self):
        tree=ast.parse((ROOT/'src/hcr/grounding.py').read_text(encoding='utf-8'))
        self.assertFalse(any(isinstance(n,ast.ImportFrom) and 'evaluation' in (n.module or '') for n in ast.walk(tree)))
    def test_auditor_does_not_import_production_diagnostic(self):
        tree=ast.parse((ROOT/'src/hcr/evaluation/grounding_audit.py').read_text(encoding='utf-8'))
        self.assertFalse(any(isinstance(n,ast.ImportFrom) and n.module in ('grounding','runtime','dynamics') for n in ast.walk(tree)))


class GroundingCLI(unittest.TestCase):
    def test_help_in_process(self):
        from hcr.cli import main
        stdout=io.StringIO();stderr=io.StringIO()
        with redirect_stdout(stdout),redirect_stderr(stderr),self.assertRaises(SystemExit) as caught:main(['grounding','--help'])
        self.assertEqual(caught.exception.code,0);self.assertIn('demo',stdout.getvalue())
    def test_plan_does_not_infer(self):
        from hcr.grounding_cli import main
        stdout=io.StringIO()
        with redirect_stdout(stdout),patch('hcr.evaluation.grounding_protocol.run_demo',side_effect=AssertionError('not allowed')):
            self.assertEqual(main(['plan']),0)
        self.assertFalse(json.loads(stdout.getvalue())['inference_executed'])
    def test_launcher_python_not_powershell(self):
        import importlib.util
        spec=importlib.util.spec_from_file_location('grounding_launcher',ROOT/'scripts/legacy/Run-HCR-R032.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
        steps=m.commands(Path('output'));self.assertIn(['hcr.py','grounding','demo','--out','output'],steps)
        self.assertFalse(any('powershell' in str(s).lower() for s in steps))
    def test_existing_output_does_not_start(self):
        with tempfile.TemporaryDirectory() as td, self.assertRaises(FileExistsError):run_demo(Path(td))


class GroundingBundle(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.root=Path(cls.temp.name)/'run'
        cls.receipt=run_demo(cls.root)
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()
    def test_end_to_end_counts(self):
        self.assertTrue(self.receipt['verified']);self.assertEqual(self.receipt['task_inferences'],126)
        self.assertEqual(self.receipt['readout_policy_evaluations'],378);self.assertTrue(self.receipt['original_decisions_preserved'])
    def test_relocated_bundle(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'이동 결과';shutil.copytree(self.root,p);self.assertTrue(verify_run(p)['verified'])
    def test_extra_file_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'run';shutil.copytree(self.root,p);(p/'extra').write_bytes(b'x')
            with self.assertRaises(ContractError):verify_run(p)
    def test_summary_rehash_does_not_bypass_reaggregation(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'run';shutil.copytree(self.root,p);s=load(p/'summary.json');s['task_inferences']=999
            (p/'summary.json').write_bytes((codec.dumps(s)+'\n').encode());manifest=load(p/'manifest.json')
            manifest['files']['summary.json']=file_hash(p/'summary.json');(p/'manifest.json').write_bytes((codec.dumps(manifest)+'\n').encode())
            with self.assertRaises(ContractError):verify_run(p)
    def test_raw_always_separate(self):
        raw=load(self.root/'raw/6/critical_missing/route_only.json');record=load(self.root/'records/6/critical_missing/route_only.json')
        self.assertIs(raw['decision']['value'],False);self.assertIsNone(record['readouts']['dependency_gate']['value'])
    def test_failed_original_cannot_pass_as_complete(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'run';shutil.copytree(self.root,p);m=load(p/'manifest.json');m['state']='failed';(p/'manifest.json').write_bytes((codec.dumps(m)+'\n').encode())
            with self.assertRaises(ContractError):verify_run(p)
    def test_failure_keeps_first_raw_evidence(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'failure'
            with patch('hcr.evaluation.grounding_protocol.make_record',side_effect=RuntimeError('injected diagnostic failure')):
                with self.assertRaises(RuntimeError):run_demo(p)
            f=load(p/'FAILED.json');self.assertEqual(f['task_inferences_recorded'],1)
            self.assertEqual(len(list((p/'raw').rglob('*.json'))),1);self.assertFalse((p/'manifest.json').exists())
