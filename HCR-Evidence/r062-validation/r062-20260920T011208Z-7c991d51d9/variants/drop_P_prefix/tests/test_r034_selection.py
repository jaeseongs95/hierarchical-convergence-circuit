"""R0.3.4 순수 모듈 시험. 합성 계약 fixture이며 실제 엔진 실험 결과가 아니다."""
from __future__ import annotations
from copy import deepcopy
from dataclasses import asdict
import json
from pathlib import Path
import random
import tempfile
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from hcr.selection import (SelectionLimits, SelectionContractError, digest,
    empty_usage, project_candidate, select_supported, validate_view)
from hcr.evaluation.selection_audit import SelectionAuditError, verify_selection
from hcr.evaluation.selection_spec import conditions, cells, baseline_specs
from hcr.evaluation.selection_protocol import identifiable, reachable
from hcr import selection_io


def synthetic_view(*, alternative=True, raw=True, missing=None):
    """EXP-14의 역할 배치와 같은 작은 합성 view. raw packet을 사칭하지 않는다."""
    obs=dict(episode_id='synthetic-r034-contract',revision=0,start='s',goal='g',edges=[
        dict(id='e0',source='s',target='a',score=.92),dict(id='e1',source='a',target='g',score=.92),
        dict(id='e2',source='s',target='b',score=missing),dict(id='e3',source='b',target='g',score=.92)])
    paths=[[2,3]]+([[0,1]] if alternative else [])
    state={'e:0':.999,'e:1':.999,'e:2':.707,'e:3':.999,'p:0:1':.9996}
    if alternative:state['p:1:1']=.9939
    ref=dict(segment=0,generation=4,ready_sha256='a'*64,finished_sha256='b'*64)
    return dict(schema='hcr-selection-view-r034-v1',source_candidate_id='review-candidate-'+digest(ref),
        source_reference=ref,source_decision_sha256='c'*64,source_packet_sha256='b'*64,
        observation=obs,observation_digest=digest(obs),raw_value=raw,state=state,
        completed_paths=paths,graph_complete=alternative,original_proof={'synthetic_fixture':True},min_abs_score=0.0)


def reseal(output):
    output['candidate_id']='selection-candidate-'+digest({k:v for k,v in output.items() if k not in ('candidate_id','wall_seconds')})
    return output


class SelectionSemantics(unittest.TestCase):
    def verify(self,v,lim=None,used=None):
        before=deepcopy(v);r=select_supported(v,lim,used)
        self.assertEqual(v,before);self.assertTrue(verify_selection(v,r)['verified']);return r

    def test_alternative_is_selected(self):
        r=self.verify(synthetic_view());self.assertEqual(r['selected_path_index'],1)
        self.assertEqual(r['proof']['assumed_edges'],[['e0',True],['e1',True]])

    def test_before_alternative_generation_abstains(self):
        r=self.verify(synthetic_view(alternative=False));self.assertIsNone(r['value'])
        self.assertEqual(r['reason'],'no_supported_existing_path')

    def test_neutral_is_not_positive_support(self):
        self.assertEqual(self.verify(synthetic_view(missing=0.0))['selected_path_index'],1)

    def test_negative_observation_rejects_active_path(self):
        self.assertEqual(self.verify(synthetic_view(missing=-.06))['selected_path_index'],1)

    def test_fully_supported_familiar_path_retains_rank(self):
        self.assertEqual(self.verify(synthetic_view(missing=.98))['selected_path_index'],0)

    def test_does_not_flip_false_to_true(self):
        r=self.verify(synthetic_view(raw=False));self.assertIsNone(r['value']);self.assertEqual(r['usage_delta'],empty_usage())

    def test_does_not_turn_none_into_true(self):
        self.assertIsNone(self.verify(synthetic_view(raw=None))['value'])

    def test_preserves_activation_constraint(self):
        v=synthetic_view();v['state']['e:0']=.49
        self.assertIsNone(self.verify(v)['value'])

    def test_activation_boundary_point_five(self):
        v=synthetic_view();v['state']['e:0']=.5
        self.assertIs(self.verify(v)['value'],True)

    def test_terminal_activation_rank_is_not_truth(self):
        v=synthetic_view();v['state']['p:1:1']=.4
        self.assertIs(self.verify(v)['value'],True)

    def test_positive_threshold_is_strict(self):
        v=synthetic_view(missing=.92);v['min_abs_score']=.92
        self.assertIsNone(self.verify(v)['value'])

    def test_threshold_can_retain_weak_positive(self):
        v=synthetic_view(missing=.01)
        self.assertEqual(self.verify(v)['selected_path_index'],0)

    def test_tie_break_is_stable_index(self):
        v=synthetic_view(missing=.92);v['state']['p:1:1']=v['state']['p:0:1']
        self.assertEqual(self.verify(v)['selected_path_index'],0)

    def test_fewer_than_all_paths_may_be_scanned(self):
        r=self.verify(synthetic_view(missing=.92));self.assertEqual(r['usage_delta']['path_checks'],1)
        self.assertEqual(r['usage_delta']['ranked_paths'],2)

    def test_same_request_deterministic_except_timing(self):
        a=select_supported(synthetic_view());b=select_supported(synthetic_view())
        a.pop('wall_seconds');b.pop('wall_seconds');self.assertEqual(a,b)

    def test_json_round_trip(self):
        v=synthetic_view();r=self.verify(v)
        self.assertTrue(verify_selection(json.loads(json.dumps(v)),json.loads(json.dumps(r)))['verified'])

    def test_proof_depth_is_dependency_not_inspection_count(self):
        r=self.verify(synthetic_view());self.assertEqual(r['proof']['primitive_depth'],2)
        self.assertEqual(r['usage_delta']['edge_checks'],4)

    def test_receipt_preserves_original_source(self):
        v=synthetic_view();r=self.verify(v)
        self.assertEqual(r['source_reference'],v['source_reference'])
        self.assertFalse(r['boundaries']['original_decision_modified'])

    def test_ranking_budget(self):
        r=self.verify(synthetic_view(),SelectionLimits(max_ranked_paths=1))
        self.assertEqual(r['reason'],'selection_ranking_budget')

    def test_path_budget(self):
        r=self.verify(synthetic_view(),SelectionLimits(max_path_checks=1))
        self.assertEqual(r['reason'],'selection_scan_budget');self.assertIsNone(r['value'])

    def test_edge_budget(self):
        r=self.verify(synthetic_view(),SelectionLimits(max_edge_checks=3))
        self.assertEqual(r['usage_delta']['edge_checks'],2);self.assertIsNone(r['value'])

    def test_proof_budget(self):
        r=self.verify(synthetic_view(),SelectionLimits(max_proof_nodes=3))
        self.assertEqual(r['reason'],'selection_proof_budget');self.assertIsNone(r['proof'])

    def test_cumulative_scan_budget(self):
        v=synthetic_view();limits=SelectionLimits(max_path_checks=3)
        first=self.verify(v,limits);second=self.verify(v,limits,first['usage_after'])
        self.assertTrue(first['accepted']);self.assertFalse(second['accepted'])
        self.assertEqual(second['usage_after']['path_checks'],3)

    def test_cumulative_proof_budget(self):
        limits=SelectionLimits(max_proof_nodes=4);first=self.verify(synthetic_view(),limits)
        second=self.verify(synthetic_view(),limits,first['usage_after'])
        self.assertEqual(second['reason'],'selection_proof_budget')

    def test_reused_budget_not_mutated(self):
        u=empty_usage();before=deepcopy(u);self.verify(synthetic_view(),used=u);self.assertEqual(u,before)

    def test_zero_all_budgets(self):
        r=self.verify(synthetic_view(),SelectionLimits(0,0,0,0));self.assertIsNone(r['value'])

    def test_limits_reject_bool(self):
        with self.assertRaises(SelectionContractError):SelectionLimits(max_edge_checks=True)

    def test_limits_reject_negative(self):
        with self.assertRaises(SelectionContractError):SelectionLimits(max_path_checks=-1)

    def test_limits_reject_float(self):
        with self.assertRaises(SelectionContractError):SelectionLimits(max_proof_nodes=1.0)

    def test_exhausted_previous_usage_is_rejected(self):
        u=empty_usage();u['proof_nodes']=129
        with self.assertRaises(SelectionContractError):select_supported(synthetic_view(),used=u)

    def test_no_path_is_no_support(self):
        v=synthetic_view();v['completed_paths']=[];v['state']={}
        r=self.verify(v);self.assertEqual(r['reason'],'no_supported_existing_path')

    def test_edge_identity_renaming_preserves_result(self):
        v=synthetic_view()
        for e in v['observation']['edges']:e['id']='renamed-'+e['id']
        v['observation_digest']=digest(v['observation'])
        r=self.verify(v);self.assertIs(r['value'],True)
        self.assertEqual(r['proof']['assumed_edges'],[['renamed-e0',True],['renamed-e1',True]])

    def test_three_step_proof_DAG(self):
        v=synthetic_view();v['observation']['edges']=[dict(id='a',source='s',target='u',score=.9),dict(id='b',source='u',target='v',score=.9),dict(id='c',source='v',target='g',score=.9)]
        v['observation_digest']=digest(v['observation']);v['completed_paths']=[[0,1,2]]
        v['state']={'e:0':.9,'e:1':.9,'e:2':.9,'p:0:2':.9}
        r=self.verify(v);self.assertEqual(r['proof']['primitive_depth'],3)

    def test_randomized_small_sign_states(self):
        rng=random.Random(15034)
        for _ in range(80):
            v=synthetic_view(missing=rng.choice([None,0.0,-.1,.1,.9]));v['state']['e:0']=rng.choice([.1,.5,.9])
            v['state']['e:2']=rng.choice([.1,.5,.9]);v['state']['p:0:1']=rng.random();v['state']['p:1:1']=rng.random()
            self.verify(v)


class SchemaRejection(unittest.TestCase):
    def reject(self,change):
        v=synthetic_view();change(v)
        with self.assertRaises((SelectionContractError,TypeError,KeyError)):select_supported(v)

    def test_hidden_world_field(self):self.reject(lambda v:v.update(world={'e0':True}))
    def test_wrong_observation_digest(self):self.reject(lambda v:v.update(observation_digest='0'*64))
    def test_wrong_candidate_id(self):self.reject(lambda v:v.update(source_candidate_id='forged'))
    def test_wrong_generation_type(self):self.reject(lambda v:v['source_reference'].update(generation=True))
    def test_missing_activation(self):self.reject(lambda v:v['state'].pop('e:0'))
    def test_boolean_activation(self):self.reject(lambda v:v['state'].update({'e:0':True}))
    def test_nan_activation(self):self.reject(lambda v:v['state'].update({'e:0':float('nan')}))
    def test_boolean_raw_value(self):self.reject(lambda v:v.update(raw_value=1))
    def test_boolean_slot(self):self.reject(lambda v:v['completed_paths'][1].__setitem__(0,False))
    def test_path_not_generated_end(self):self.reject(lambda v:v['completed_paths'].__setitem__(1,[0]))
    def test_path_discontinuity(self):self.reject(lambda v:v['completed_paths'].__setitem__(1,[1,0]))
    def test_duplicate_path(self):self.reject(lambda v:v['completed_paths'].append([2,3]))
    def test_nan_threshold(self):self.reject(lambda v:v.update(min_abs_score=float('nan')))
    def test_missing_schema_field(self):self.reject(lambda v:v.pop('state'))

    def test_invalid_scores(self):
        for score in (True,float('nan'),float('inf'),1.1,'0.9'):
            v=synthetic_view();v['observation']['edges'][0]['score']=score
            if isinstance(score,float) and not (-1<=score<=1):
                with self.assertRaises((SelectionContractError,ValueError)):select_supported(v)
            else:
                v['observation_digest']=digest(v['observation'])
                with self.assertRaises(SelectionContractError):select_supported(v)


class IndependentAuditTampering(unittest.TestCase):
    def reject(self,change):
        v=synthetic_view();r=select_supported(v);change(r);reseal(r)
        with self.assertRaises(SelectionAuditError):verify_selection(v,r)

    def test_wrong_output(self):self.reject(lambda r:r.update(value=False))
    def test_host_flip_flag(self):self.reject(lambda r:r['boundaries'].update(value_flip_allowed=True))
    def test_forged_support(self):self.reject(lambda r:r['path_checks'][0].update(observation_supported=True))
    def test_hidden_new_path(self):self.reject(lambda r:r['proof']['paths'].append(['e0','e3']))
    def test_wrong_selected_index(self):self.reject(lambda r:r.update(selected_path_index=0))
    def test_wrong_selected_index_type(self):self.reject(lambda r:r.update(selected_path_index=True))
    def test_wrong_dependency_depth(self):self.reject(lambda r:r['proof'].update(primitive_depth=9))
    def test_bad_parent(self):self.reject(lambda r:r['proof']['nodes'][-1].update(parents=['nonexistent']))
    def test_self_cycle(self):self.reject(lambda r:r['proof']['nodes'][-1].update(parents=[r['proof']['final']]))
    def test_duplicate_node(self):self.reject(lambda r:r['proof']['nodes'][1].update(id=r['proof']['nodes'][0]['id']))
    def test_extra_fact(self):self.reject(lambda r:r['proof']['assumed_edges'].append(['e2',True]))
    def test_false_assumption(self):self.reject(lambda r:r['proof']['assumed_edges'][0].__setitem__(1,False))
    def test_integer_assumption(self):self.reject(lambda r:r['proof']['assumed_edges'][0].__setitem__(1,1))
    def test_wrong_source_hash(self):self.reject(lambda r:r.update(source_packet_sha256='0'*64))
    def test_unlisted_cost(self):self.reject(lambda r:r['usage_delta'].update(proof_nodes=0))
    def test_cost_type(self):self.reject(lambda r:r['usage_after'].update(proof_nodes=4.0))
    def test_wrong_final(self):self.reject(lambda r:r['proof'].update(final='f:0:1'))
    def test_unregistered_primitive(self):self.reject(lambda r:r['proof']['nodes'][1].update(rule='oracle_true'))
    def test_wrong_path_index(self):self.reject(lambda r:r['proof']['nodes'][1].update(path_index=0))
    def test_missing_selection_fields(self):self.reject(lambda r:r.pop('accepted'))
    def test_fake_reason(self):self.reject(lambda r:r.update(reason='converged'))
    def test_unaccounted_path_scan(self):self.reject(lambda r:r['path_checks'].pop(0))
    def test_claimed_zero_cost(self):self.reject(lambda r:r.update(usage_after=empty_usage(),usage_delta=empty_usage()))
    def test_negative_timing(self):self.reject(lambda r:r.update(wall_seconds=-1))


class ProtocolAndIO(unittest.TestCase):
    def test_matrix_counts(self):
        cp=conditions();r=cells(cp)
        self.assertEqual(len(r),194);self.assertEqual(sum(x['group']=='main' for x in r),182)
        self.assertEqual(len(list(baseline_specs(cp))),18)
        self.assertEqual(len({x['id'] for x in r}),194)

    def test_conditions_are_fresh_objects(self):
        cp=conditions();cp['work_limits']['max_extra_advances']=0
        self.assertEqual(conditions()['work_limits']['max_extra_advances'],8)

    def test_computation_controls_separate(self):
        r=[x for x in cells(conditions()) if x['group'].startswith('running_')]
        self.assertEqual(len(r),8);self.assertTrue(all(x['scope']=='route_only' for x in r))
        self.assertFalse(any(x['arm']=='select_only' for x in r))

    def test_missing_critical_information(self):
        c=next(c for c in conditions()['cases'] if c['name']=='critical_missing')
        self.assertEqual(identifiable(c['observation']),dict(identifiable=False,value=None))
        self.assertFalse(reachable(c['observation'],c['worlds']['first_closed']))
        self.assertTrue(reachable(c['observation'],c['worlds']['first_open']))

    def test_irrelevant_gap_is_identifiable(self):
        c=next(c for c in conditions()['cases'] if c['name']=='irrelevant_missing')
        self.assertEqual(identifiable(c['observation']),dict(identifiable=True,value=True))

    def test_known_cuts_are_identifiable(self):
        for name in ('known_cut_missing','two_branch_cut'):
            c=next(c for c in conditions()['cases'] if c['name']==name)
            self.assertEqual(identifiable(c['observation']),dict(identifiable=True,value=False))

    def test_support_is_not_truth(self):
        c=next(c for c in conditions()['cases'] if c['name']=='misleading_direction')
        self.assertTrue(identifiable(c['observation'])['value'])
        self.assertFalse(reachable(c['observation'],c['worlds']['declared']))

    def test_exclusive_evidence_write(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'raw.json';selection_io.put(p,{'a':1})
            with self.assertRaises(FileExistsError):selection_io.put(p,{'a':2})
            self.assertEqual(selection_io.load(p),{'a':1})

    def test_duplicate_json_key_rejected(self):
        with self.assertRaises(ValueError):selection_io.loads('{"a":1,"a":2}')

    def test_json_nan_rejected(self):
        with self.assertRaises(ValueError):selection_io.loads('{"a":NaN}')

    def test_path_traversal_rejected(self):
        for name in ('../x','/tmp/x','C:/x','foo\\bar'):
            with self.assertRaises(ValueError):selection_io.child(Path('/tmp'),name)

    def test_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'file').write_text('x')
            try:(root/'link').symlink_to(root/'file')
            except OSError:self.skipTest('local symlink creation not supported')
            with self.assertRaises(ValueError):selection_io.read(root/'link')

    def test_bounded_read(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'x';p.write_bytes(b'12345')
            with self.assertRaises(ValueError):selection_io.read(p,limit=4)


class CandidateProjectionTests(unittest.TestCase):
    def candidate(self):
        v=synthetic_view();program={'paths':v['completed_paths']}
        d=dict(id='synthetic-decision',observation_digest=v['observation_digest'],observation_revision=0,
            episode_id=v['observation']['episode_id'],program_digest=digest(program),
            expanded_paths=deepcopy(v['completed_paths']),value=True,state=list(v['state'].items()),
            graph_complete=True,proof={'synthetic_fixture':True})
        events=[dict(event='r02_attempt_started',payload=dict(decision_id=d['id'],observation=v['observation'])),
            dict(event='r02_network',payload=dict(decision_id=d['id'],kind='decision',program=program,
                program_digest=digest(program),metadata=dict(routes=[dict(path=p) for p in v['completed_paths']]))),
            dict(event='r02_decision',payload=d)]
        doc=dict(events=events);packet=dict(document=doc,sha256=digest(doc))
        ref=dict(segment=0,generation=4,ready_sha256='a'*64,finished_sha256=packet['sha256'])
        return dict(decision=d,packet=packet,reference=ref,candidate_id='review-candidate-'+digest(ref),
            diagnostic=dict(source=dict(decision_sha256=digest(d)),contract=dict(min_abs_score=0.0)))

    def seal(self,c):
        c['packet']['sha256']=digest(c['packet']['document'])
        c['reference']['finished_sha256']=c['packet']['sha256']
        c['candidate_id']='review-candidate-'+digest(c['reference'])
        c['diagnostic']['source']['decision_sha256']=digest(c['decision'])
        return c

    def test_projection_agrees_with_independent_extractor(self):
        from hcr.evaluation.selection_audit import source_view
        c=self.candidate();before=deepcopy(c);v=project_candidate(c)
        self.assertEqual(v,source_view(c));self.assertEqual(c,before)
        self.assertTrue(verify_selection(v,select_supported(v))['verified'])

    def test_projection_detects_packet_changes(self):
        c=self.candidate();c['packet']['document']['injected']=1
        with self.assertRaises(SelectionContractError):project_candidate(c)

    def test_projection_detects_program_changes(self):
        c=self.candidate();c['decision']['program_digest']='0'*64;self.seal(c)
        with self.assertRaises(SelectionContractError):project_candidate(c)

    def test_projection_detects_route_provenance(self):
        c=self.candidate();c['packet']['document']['events'][1]['payload']['metadata']['routes'].pop();self.seal(c)
        with self.assertRaises(SelectionContractError):project_candidate(c)

    def test_projection_detects_stale_revision(self):
        c=self.candidate();c['decision']['observation_revision']=1;self.seal(c)
        with self.assertRaises(SelectionContractError):project_candidate(c)

    def test_projection_detects_duplicate_begin(self):
        c=self.candidate();c['packet']['document']['events'].insert(1,deepcopy(c['packet']['document']['events'][0]));self.seal(c)
        with self.assertRaises(SelectionContractError):project_candidate(c)

    def test_projection_detects_wrong_diagnostic_source(self):
        c=self.candidate();c['diagnostic']['source']['decision_sha256']='0'*64
        with self.assertRaises(SelectionContractError):project_candidate(c)

    def test_projection_rejects_duplicate_state_identity(self):
        c=self.candidate();c['decision']['state'].append(['e:0',.1]);self.seal(c)
        with self.assertRaises(SelectionContractError):project_candidate(c)

    def test_projection_detects_wrong_finished_reference(self):
        c=self.candidate();c['reference']['finished_sha256']='0'*64
        with self.assertRaises(SelectionContractError):project_candidate(c)


if __name__=='__main__':unittest.main(verbosity=2)
