"""EXP-09 r2 순수 도구 계약 시험. HCR import나 추론 없이 실행한다."""
from __future__ import annotations
from copy import deepcopy
import ast
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from collect import ALIASES,BaselineError,canonical,sha,write_json
import probe
from probe_analysis import (comparison,benchmark_report,decompose,memory_changes,memory_content,
                            semantic_decision,input_content)
from audit_probe import verify_files,audit_pairs,SCHEMA


def row(arm='graph_only',rep=0):
    cost={**{k:0 for k in ALIASES},**{k:0 for k in ALIASES.values()},'group_updates':0,
          'wall_seconds':.003,'expansions':3}
    return dict(phase='cost_pairs',arm=arm,case='case',replicate=rep,
        order_in_pair=(0 if arm=='graph_only' else 1) if rep%2==0 else (1 if arm=='graph_only' else 0),
        observation={'episode_id':'e','revision':0,'edges':[]},external_truth={},
        decision=dict(id=arm+str(rep),cost=cost,proof={'primitive_depth':3},value=True,circuit_ids=[]),
        assessment={'correct':True})


class AnalysisR2(unittest.TestCase):
    def test_strict_pair_rejects_different_observation(self):
        a,b=row(),row('circuits');b['observation']['revision']=1
        with self.assertRaises(BaselineError):comparison(a,b,'x')

    def test_pair_rejects_truth_change(self):
        a,b=row(),row('circuits');b['external_truth']={'e':False}
        with self.assertRaises(BaselineError):comparison(a,b,'x',strict_input=False)

    def test_delta_direction_right_minus_left(self):
        a,b=row(),row('circuits');b['decision']['cost']['expansions']=1
        self.assertEqual(comparison(a,b,'x')['cost_delta']['expansions'],-2)

    def test_aliases_not_summed_in_delta(self):
        self.assertTrue(set(comparison(row(),row('circuits'),'x')['cost_delta']).isdisjoint(ALIASES))

    def test_same_score_comparison_is_not_strict_identity(self):
        a,b=row(),row('circuits');b['observation']['episode_id']='other';b['observation']['revision']=1
        r=comparison(a,b,'x',strict_input=False)
        self.assertFalse(r['same_public_input']);self.assertTrue(r['same_input_except_episode_revision'])

    def test_cost_pair_missing_arm_rejected(self):
        with self.assertRaises(BaselineError):benchmark_report([row()])

    def test_cost_pair_duplicate_arm_rejected(self):
        with self.assertRaises(BaselineError):benchmark_report([row(),row()])

    def test_cost_report_balanced_order(self):
        rows=[row(arm,i) for i in range(2) for arm in ('graph_only','circuits')]
        r=benchmark_report(rows)
        self.assertEqual(r['cases'][0]['first_arm_counts'],{'graph_only':1,'circuits':1})
        self.assertFalse(r['independent_task_samples'])

    def test_cost_report_tracks_timing_without_forcing_gain(self):
        rows=[row(),row('circuits')];rows[1]['decision']['cost']['wall_seconds']=.010
        self.assertAlmostEqual(benchmark_report(rows)['cases'][0]['median_paired_delta_ms'],7.)

    def test_semantic_compare_preserves_source(self):
        a=row()['decision'];b=deepcopy(a);semantic_decision(a);self.assertEqual(a,b)

    def test_memory_history_only_is_not_structure_learning(self):
        a=dict(circuits=[],pending=[],version=1);b=dict(a,version=2)
        self.assertEqual(memory_content(a),memory_content(b));self.assertNotEqual(a,b)

    def test_memory_delta_no_invented_circuits(self):
        self.assertEqual(memory_changes({'circuits':[]},{'circuits':[]}),[])

    def test_memory_delta_tracks_weaken(self):
        c=dict(pattern={'relations':[0,1]},strength=.8,failures=0,active=True,evidence_episodes=['a','b','c'])
        d=dict(c,strength=.16,failures=1)
        r=memory_changes({'circuits':[c]},{'circuits':[d]})[0]
        self.assertEqual((r['before_strength'],r['after_strength']),(.8,.16))
        self.assertTrue(r['after_active'])

    def test_decompose_empty_records(self):
        self.assertEqual(decompose([],[]),dict(costs=[],candidates=[],feedback=[]))

    def test_decompose_detects_counter_tamper(self):
        r=row();r['decision']['cost']['kernel_ticks']=r['decision']['cost']['convergence_ticks']=1
        with self.assertRaises(BaselineError):decompose([r],[])

    def test_input_content_keeps_scores(self):
        a=dict(episode_id='x',revision=1,edges=[{'score':.1}])
        self.assertEqual(input_content(a),{'edges':[{'score':.1}]})


class PlanAndBundleR2(unittest.TestCase):
    def test_repeat_bound_and_evenness_checked_before_read(self):
        for n in (0,1,3,21,22,True):
            with self.subTest(n=n),self.assertRaises(BaselineError):probe.make_plan(Path('missing'),n)

    def test_roots_reject_existing_output(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)
            with self.assertRaises(BaselineError):probe.roots(p,p)

    def test_roots_reject_nested_output(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)
            with self.assertRaises(BaselineError):probe.roots(p,p/'result')

    def make_bundle(self,p):
        (p/'x').write_bytes(b'content\n')
        write_json(p/'manifest.json',dict(schema=SCHEMA,state='complete',files={'x':sha(b'content\n')}))

    def test_verify_files_valid(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);self.make_bundle(p);self.assertEqual(verify_files(p)['state'],'complete')

    def test_verify_files_byte_mutation(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);self.make_bundle(p);(p/'x').write_bytes(b'changed\n')
            with self.assertRaises(BaselineError):verify_files(p)

    def test_verify_files_extra_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);self.make_bundle(p);(p/'extra').write_bytes(b'')
            with self.assertRaises(BaselineError):verify_files(p)

    def test_failed_bundle_not_complete(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);self.make_bundle(p);write_json(p/'FAILED.json',{'state':'failed'})
            with self.assertRaises(BaselineError):verify_files(p)

    def test_registry_accepts_lf_bytes_not_platform_newline(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);self.make_bundle(p)
            self.assertEqual((p/'x').read_bytes(),b'content\n')

    def test_read_only_manifest_check(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);self.make_bundle(p);before={x.name:x.read_bytes() for x in p.iterdir()}
            verify_files(p);self.assertEqual(before,{x.name:x.read_bytes() for x in p.iterdir()})

    def test_no_top_level_hcr_import(self):
        root=Path(__file__).resolve().parents[1]
        for name in ('probe.py','probe_analysis.py','audit_probe.py'):
            tree=ast.parse((root/name).read_text(encoding='utf-8'))
            for node in tree.body:
                if isinstance(node,ast.ImportFrom):self.assertFalse((node.module or '').startswith('hcr'))
                if isinstance(node,ast.Import):self.assertFalse(any(x.name.startswith('hcr') for x in node.names))

    def test_auditor_no_production_inference_import(self):
        root=Path(__file__).resolve().parents[1]
        tree=ast.parse((root/'audit_probe.py').read_text(encoding='utf-8'))
        prohibited={'hcr.runtime','hcr.learning','hcr.dynamics','hcr.expansion','hcr.activation'}
        self.assertFalse(any(isinstance(n,ast.ImportFrom) and n.module in prohibited for n in ast.walk(tree)))


def matrix_fixture():
    weak={'episode_id':'e900001','revision':0,'edges':[{'score':-.06}]}
    measured={'episode_id':'e900001','revision':0,'edges':[{'score':-.98}]}
    seeds={'before':'b','after':'a','training_3':'t3','training_9':'t9','live':'l'}
    cases={'conflict_truth':{'e':False}}
    rows=[]
    def add(phase,arm,obs,seed,enabled,**extra):
        d={'mode':'adapt' if phase=='adaptation' else 'frozen_eval','attempt':1}
        rows.append(dict(phase=phase,arm=arm,observation=deepcopy(obs),external_truth={'e':False},
            memory_before=seed,memory_after_inference=seed,decision=d,engine_use_circuits=enabled,**extra))
    for mem in ('before','after'):
        for profile,obs in (('weak',weak),('measured',measured)):
            obs=dict(obs,episode_id='e900002')
            for route in ('circuits','graph_only'):add('factorial',f'{mem}/{profile}/{route}',obs,seeds[mem],route=='circuits')
    for arm in ('direct','reload'):add('persistence',arm,dict(weak,episode_id='e900002'),'l',True)
    for arm in ('measured_replay','same_score_control','training_3','training_6','training_9'):
        seed='before' if arm in ('measured_replay','same_score_control','training_6') else arm
        add('adaptation',arm,weak,seeds[seed],True)
    for case in ('c1','c2','c3','c4','c5'):
        cases[case]={'observation':deepcopy(weak),'external_truth':{'e':False}}
        for rep in range(2):
            for arm in ('graph_only','circuits'):
                order=(0 if arm=='graph_only' else 1) if rep%2==0 else (1 if arm=='graph_only' else 0)
                add('cost_pairs',arm,weak,'b',arm=='circuits',case=case,replicate=rep,order_in_pair=order)
    plan={'repeats':2,'max_inferences':45}
    return rows,plan,seeds,weak,measured,cases


class PairAuditorR2(unittest.TestCase):
    def test_complete_matrix(self):
        self.assertEqual(audit_pairs(*matrix_fixture())['cost_pairs'],10)

    def test_memory_intervention_mismatch(self):
        data=list(matrix_fixture());data[0][0]['memory_before']='wrong'
        with self.assertRaises(BaselineError):audit_pairs(*data)

    def test_profile_intervention_mismatch(self):
        data=list(matrix_fixture());data[0][0]['observation']['edges'][0]['score']=-.98
        with self.assertRaises(BaselineError):audit_pairs(*data)

    def test_route_intervention_mismatch(self):
        data=list(matrix_fixture());data[0][0]['engine_use_circuits']=False
        with self.assertRaises(BaselineError):audit_pairs(*data)

    def test_case_order_intervention_mismatch(self):
        data=list(matrix_fixture());data[0][-1]['order_in_pair']=1-data[0][-1]['order_in_pair']
        with self.assertRaises(BaselineError):audit_pairs(*data)

    def test_missing_cell(self):
        data=list(matrix_fixture());data[0].pop(0)
        with self.assertRaises(BaselineError):audit_pairs(*data)

    def test_extra_cell(self):
        data=list(matrix_fixture());data[0].append(deepcopy(data[0][0]))
        with self.assertRaises(BaselineError):audit_pairs(*data)

    def test_frozen_cell_cannot_train(self):
        data=list(matrix_fixture());data[0][0]['decision']['mode']='train'
        with self.assertRaises(BaselineError):audit_pairs(*data)


if __name__=='__main__':unittest.main()
