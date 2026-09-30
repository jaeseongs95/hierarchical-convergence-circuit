"""Independent input reconstruction, ideal measurement checking and native formula replay."""
import argparse
from copy import deepcopy
from itertools import product
from pathlib import Path
import sys
from tools.r050_review_boundary.audit import candidate_measures, counter_values, FORBIDDEN
from tools.r050_review_boundary.common import dump, files, fingerprint, load, require, sha, unseal
from tools.r063_formation.audit import verify_execution, mutation_checks
from tools.r066_facts.verify import expected_facts


def expected_input(plan, arm, truth):
    observation=deepcopy(plan['observation']);old=plan['old_fact'];request=None;response=None
    status='history';valid_at=-1;score=-1.0;stored=[old]
    if arm!='history':
        request=dict(controller='explicit_baseline',edge_id='e1',source='v1',target='v2',
            scope=plan['fact_scope'],requested_at=1,budget=1,channel={'stale':'cached','fresh':'current'}[arm])
        score=0.8 if arm=='stale' else {False:-1.0,True:1.0}[truth['e1']]
        valid_at={'stale':0,'fresh':1}[arm];status='measured'
        response=dict(request=request,delivered_at=1,valid_at=valid_at,
            source={'stale':'cached_original','fresh':'ideal_current_sensor'}[arm],status=status,score=score)
        if arm=='fresh':
            stored=[dict(context=old['context'],epoch=old['epoch'],edge_id='e1',source='v1',target='v2',
                value=truth['e1'],valid_at=1,provenance=dict(response_sha256=fingerprint(response)))]
    observation['edges'][1]['score']=score
    return dict(arm=arm,controller='explicit_baseline',request=request,response=response,
        original_input=plan['observation'],actual_input=observation,status=status,valid_at=valid_at,
        prior_conflict=True,stored_before=[old],stored_after=stored,persistence_used_in_this_decision=False,
        input_changed=observation!=plan['observation'],
        cost=dict(additional_observation_budget=1,observation_calls=int(arm!='history'),
            current_measurement_calls=int(arm=='fresh'),stale_presentations=int(arm=='stale'),
            fact_reads=1,fact_value_writes=int(arm=='fresh'),conflict_comparisons=1,information_gain_bits=None))


def check_input(row, plan, arm, truth):
    require(row==expected_input(plan,arm,truth),'Independent observation/input reconstruction')


def main(out):
    plan=load(out/'plan.json');spec=load(out/'source/experiments/exp-48-observation-refresh/frozen_spec.json')
    require(plan==spec,'Frozen plan')
    require(files(out/'source')==load(out/'source_manifest.json')['files'],'Source coverage')
    require(files(out/'parent')==plan['parent_files']==load(out/'input_manifest.json')['files'],'Parent coverage')
    require(files(out/'evaluation')==load(out/'raw_manifest.json')['files'],'Raw coverage')
    require(files(out/'measurements')==load(out/'measurement_manifest.json')['files'],'Measurement coverage')
    wp=out/'source/experiments/exp-48-observation-refresh/reference_worlds.json'
    require(sha(wp.read_bytes().replace(b'\r\n',b'\n'))==plan['worlds_sha256'],'Private-world hash')
    worlds=load(wp);require(set(worlds)==set(plan['slots']),'World coverage')
    historical=next(x for x in expected_facts(out,plan) if x['edge_id']=='e1')
    require(plan['old_fact']==dict(historical,valid_at=-1) and historical['value'] is False,'Historical provenance')
    require(plan['arms']==['history','stale','fresh'] and plan['observation']['edges']==[
        dict(id='e0',source='v0',target='v1',score=0.8),dict(id='e1',source='v1',target='v2',score=0.8)],'Frozen contrast')
    memory=load(out/'parent/memory/after_correction.json');rows=[];identities=set();measurement_ids=set();sample=None
    for slot,arm,gate in product(plan['slots'],plan['arms'],(False,True)):
        identity=f"{slot}-{arm}-{'on' if gate else 'off'}";identities.add(identity);where=out/'evaluation'/identity
        truth=worlds[slot];require(set(truth)=={'e0','e1'} and truth['e0'] is True
            and type(truth['e1']) is bool,'Fixed two-edge Boolean world')
        target=truth['e0'] and truth['e1'];inp=load(where/'input.json');check_input(inp,plan,arm,truth)
        require(load(where/'request.json')==dict(request=inp['request'],after_initial_inference=True),'Request record')
        if arm!='history':
            measurement_ids.add(identity+'.json')
            response=unseal(load(out/'measurements'/f'{identity}.json'),'hcc-r067-response-v1')
            require(response==dict(schema='hcc-r067-response-v1',identity=identity,
                plan_sha256=fingerprint(plan),response=inp['response']),'Measurement binding')
        stage_results={}
        for phase in ('before','after'):
            record=unseal(load(where/phase/'inference.json'),'hcc-r067-inference-v1');execution=record['execution']
            expected=dict(schema='hcc-r067-inference-v1',execution=execution,identity=identity,phase=phase,plan_sha256=fingerprint(plan))
            if phase=='after':expected['input_sha256']=fingerprint(inp)
            require(record==expected,'Inference record binding')
            obs=plan['observation'] if phase=='before' else inp['actual_input']
            session_id='r067-'+identity+'-'+phase
            verify_execution(plan,execution,dict(observation=obs),memory,gate,'frozen_eval',session_id)
            m=candidate_measures(execution,target)
            # Same visible edge scores; this simple chain baseline receives no private world truth.
            positive=sum(e['score']>0 for e in obs['edges']);negative=sum(e['score']<0 for e in obs['edges'])
            direct=False if negative else True if positive==2 else None
            stage_results[phase]=dict(measures=m,native_cost=counter_values(execution),
                direct_baseline_value=direct,direct_baseline_correct=None if direct is None else direct==target,
                direct_baseline_edge_checks=2)
            if sample is None and execution['candidate'] is not None:
                sample=(execution,obs,gate,session_id)
        rows.append(dict(identity=identity,slot=slot,arm=arm,use_circuits=gate,truth=truth,target=target,
            memory_sha256=fingerprint(memory),prior_conflict=inp['prior_conflict'],input_cost=inp['cost'],**stage_results))
    require({x.name for x in (out/'evaluation').iterdir()}==identities and len(rows)==12,'Complete matrix')
    require({x.name for x in (out/'measurements').iterdir()}==measurement_ids and len(measurement_ids)==8,'Exact response count')
    paired=[]
    for arm,gate in product(plan['arms'],(False,True)):
        a,b=[next(r for r in rows if r['slot']==s and r['arm']==arm and r['use_circuits']==gate) for s in plan['slots']]
        def value(r,phase):return r[phase]['measures']['adopted_value']
        paired.append(dict(arm=arm,use_circuits=gate,before_values_equal=value(a,'before')==value(b,'before'),
            after_values_equal=value(a,'after')==value(b,'after'),
            both_after_correct=all(r['after']['measures']['adopted_correct'] is True for r in (a,b))))
    predictions=dict(
        old_information_cannot_discriminate=all(p['after_values_equal'] and not p['both_after_correct'] for p in paired if p['arm']!='fresh'),
        fresh_e1_discriminates=all(not p['after_values_equal'] and p['both_after_correct'] for p in paired if p['arm']=='fresh'),
        initial_conflict_is_world_ambiguous=all(r['prior_conflict'] for r in rows) and all(p['before_values_equal'] for p in paired),
        same_information_baseline_suffices=all(r['after']['direct_baseline_correct'] is True for r in rows if r['arm']=='fresh'),
        recording_not_used_for_current_correction=all(not load(out/'evaluation'/r['identity']/'input.json')['persistence_used_in_this_decision'] for r in rows))
    rejected=[];base=expected_input(plan,'fresh',worlds[plan['slots'][0]])
    changes=[('e0_confounded',lambda x:x['actual_input']['edges'][0].update(score=1.0)),
        ('measurement_value',lambda x:x['response'].update(score=1.0)),
        ('freshness',lambda x:x['response'].update(valid_at=0)),
        ('request_edge',lambda x:x['request'].update(edge_id='e0')),
        ('source',lambda x:x['response'].update(source='cached_original')),
        ('stored_value',lambda x:x['stored_after'][0].update(value=True)),
        ('hidden_write',lambda x:x.update(persistence_used_in_this_decision=True)),
        ('calls',lambda x:x['cost'].update(observation_calls=0)),
        ('conflict',lambda x:x.update(prior_conflict=False))]
    for name,mutate in changes:
        bad=deepcopy(base);mutate(bad)
        try:check_input(bad,plan,'fresh',worlds[plan['slots'][0]])
        except ValueError:rejected.append(name)
        else:raise AssertionError('Undetected mutation: '+name)
    if sample:
        e,obs,gate,identity=sample
        rejected+=['native_'+x for x in mutation_checks(plan,e,dict(observation=obs),memory,gate,'frozen_eval',identity)]
    require(not (FORBIDDEN|{'hcr.learning','hcr.compiler','tools.r067_refresh.worker','tools.r067_refresh.measure',
        'tools.r063_formation.worker'}) & set(sys.modules),'Verifier imported producer')
    dump(out/'summary.json',dict(rows=rows,paired_worlds=paired,predictions=predictions,native_evaluations=24,
        new_learning_executions=0,independent_samples=False,baseline_controller=True,ideal_toy_sensor=True,
        subsequent_retention_measured=False,actual_energy_joules=None,peak_memory_bytes=None,information_gain_bits=None))
    dump(out/'verification.json',dict(verified=True,native_formula_replays=24,rejected_mutations=rejected,
        independent_logic=True,independent_process=True,independent_researcher=False))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);main(p.parse_args().out)
