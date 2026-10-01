"""Independent formula replay and external-world assessment; no producer imports."""
import argparse
from copy import deepcopy
from pathlib import Path
import sys
from hcr import codec
from hcr.model import Feedback
from hcr.evaluation.reference import assess, reachable
from hcr.evaluation.review_audit import packet_states
from tools.r050_review_boundary.audit import candidate_measures, counter_values, FORBIDDEN
from tools.r050_review_boundary.candidate_audit import verify_candidate
from tools.r050_review_boundary.common import dump, files, fingerprint, load, require, seal, sha, unseal
from tools.r063_formation.audit import verify_execution, verify_training, mutation_checks
from .contract import SPEC, SPEC_FINGERPRINT, WORLD


def execution(run, path, plan):
    r=unseal(load(run/path/'inference.json'),'hcc-r064-inference-v1')
    require(r['plan_sha256']==fingerprint(plan),'Inference plan binding')
    return r['execution']


def reference(e, observation, truth):
    if e is None or e['candidate'] is None:
        return dict(feedback=None,assessment=None,truth=truth,reason='no_completed_candidate')
    obs=codec.observation_from(observation);d=codec.adaptive_decision_from(e['candidate']['decision'])
    a=assess(d,obs,truth)
    f=Feedback('external-'+d.id,d.id,obs.digest,a.correct,a.proof_valid and a.assumption_correct is True)
    return dict(feedback=codec.plain(f),assessment=codec.plain(a),truth=truth,reason='independent_authored_world')


def check_reference(run,path,e,obs,truth):
    expected=dict(schema='hcc-r064-reference-v1',**reference(e,obs,truth),inference_sha256=load(run/path/'inference.json')['sha256'])
    require(unseal(load(run/path/'reference.json'),'hcc-r064-reference-v1')==expected,'External truth/feedback binding')
    return expected


def check_learning(e,ref,learn,before,after):
    require(learn['feedback']==ref['feedback'] and learn['memory_after']==after,'Published feedback/memory')
    if ref['feedback'] is None:
        require(learn==dict(schema='hcc-r064-learning-v1',status='not_applied_no_candidate',feedback=None,packet=None,patch=None,memory_after=before),'No-candidate boundary')
        return
    require(learn['status']=='applied','Feedback status')
    _,r=packet_states(learn['packet']);require(r['verified'],'Independent learning replay')
    old=e['candidate']['packet']['document'];doc=learn['packet']['document']
    require(doc['transitions'][:-1]==old['transitions'] and doc['events'][:-2]==old['events'],'Exact assessed finish branch')
    require(doc['transitions'][-1]['operation']=='feedback' and doc['engine']['memory']==after,'Feedback operation/memory')
    require(doc['events'][-2]['payload']==ref['feedback'] and doc['events'][-1]['payload']['patch']==learn['patch'],'Feedback/patch event binding')


def check_request(base,learn,ref):
    eligible=ref['feedback'] is not None and ref['feedback']['correct'] is False
    if not eligible:
        require(base==dict(schema='hcc-r064-request-v1',request=None,request_packet=None,status='not_requested_no_error'),'No-error request boundary')
        return
    _,r=packet_states(base['request_packet']);require(r['verified'],'Independent request replay')
    before=learn['packet']['document'];doc=base['request_packet']['document'];n=len(before['events'])
    require(doc['transitions'][:-1]==before['transitions'] and doc['events'][:n]==before['events'],'Request exact feedback prefix')
    require(doc['transitions'][-1]['operation']=='request_revision','Request operation')
    did=ref['feedback']['decision_id'];requests=doc['engine']['requests']
    # Native replay validates request eligibility, selected edges and no-op transitions.
    expected=requests.get(did)
    require(base['request']==expected and base['status']==('requested' if expected is not None else 'native_no_request'),'Native request publication')
    require(doc['engine']['memory']==learn['memory_after'],'Request changed memory')


def measurements(plan,base,truth):
    if base['request'] is None: return {}
    result={}
    for arm in plan['spec']['revision_arms']:
        obs=deepcopy(plan['initial']['observation']);obs['revision']=base['request']['revision']
        if arm=='corrected_observation':
            for edge in obs['edges']:
                if edge['id'] in base['request']['edge_ids']:edge['score']=1.0 if truth[edge['id']] else -1.0
        result[arm]=obs
    return result


def check_revision(plan,e,obs,base,memory):
    if base['request'] is None:
        require(e is None,'Revision without native request');return
    require(e is not None and set(e)=={'packet','candidate','advances','ready','stop'},'Revision execution schema')
    states,r=packet_states(e['packet']);require(r['verified'],'Independent revision replay')
    old=base['request_packet']['document'];doc=e['packet']['document'];n=len(old['transitions'])
    require(doc['transitions'][:n]==old['transitions'] and doc['events'][:len(old['events'])]==old['events'],'Exact shared revision prefix')
    require(doc['transitions'][n:][0]['operation']=='begin' and [t['operation'] for t in doc['transitions'][n+1:]]==['advance']*e['advances'],'Revision operations/count')
    p=doc['engine']['pending'];bound=plan['config']['kernel']['max_ticks'];limits=plan['limits']
    require(p['observation']==obs and p['mode']=='adapt' and p['revision_of']==base['request']['decision_id'],'Requested observation/mode/decision')
    require(doc['engine']['memory']==memory,'Frozen revision memory')
    require(type(e['advances']) is int and 0<=e['advances']<=limits['max_advances_per_session'],'Revision advance budget')
    for ordinal in range(e['advances']):
        before=states[n+ordinal]['pending'];after=states[n+ordinal+1]['pending']
        a=before['cost']['kernel_ticks'];b=after['cost']['kernel_ticks']
        require(not before['ready'] and a+bound<=limits['max_kernel_ticks_per_session'] and 0<=b-a<=bound,'Revision reserved ticks')
    require(e['ready'] is p['ready'],'Revision ready flag')
    if e['ready']:
        require(e['stop']=='readout_ready' and e['candidate'] is not None,'Revision readout')
        verify_candidate(e['candidate'],e['packet'],states)
    else:
        require(e['candidate'] is None and e['stop']=='external_compute_budget','Revision partial status')
        require(e['advances']==limits['max_advances_per_session'] or p['cost']['kernel_ticks']+bound>limits['max_kernel_ticks_per_session'],'Revision premature stop')


def parent_audit(run,plan):
    parent=run/'parent';require(files(parent)==plan['spec']['parent_files'],'Exact pinned R063 evidence')
    pp=unseal(load(parent/'plan.json'),'hcc-r063-plan-v1')
    for i in range(1,4):
        r,ref=verify_training(pp,parent,i)
        stored=unseal(load(parent/f'training/{i:02d}/reference.json'),'hcc-r063-reference-v1')
        require(stored==dict(schema='hcc-r063-reference-v1',**ref,inference_sha256=load(parent/f'training/{i:02d}/inference.json')['sha256']),'Parent reference recomputation')
        learn=unseal(load(parent/f'training/{i:02d}/learning.json'),'hcc-r063-learning-v1')
        learn['schema']='hcc-r064-learning-v1'
        check_learning(r['execution'],ref,learn,load(parent/f'memory/{i-1}.json'),load(parent/f'memory/{i}.json'))
    require(load(run/'memory/before.json')==load(parent/'memory/3.json'),'Exact native R063 seed')


def metrics(e,obs,truth):
    m=candidate_measures(e,reachable(codec.observation_from(obs),truth))
    return dict(measures=m,cost=None if e is None else counter_values(e),external_assessment=reference(e,obs,truth)['assessment'])


def final_audit(run,plan,truth):
    parent_audit(run,plan)
    before=load(run/'memory/before.json');after=load(run/'memory/after_feedback.json');last=load(run/'memory/after_correction.json')
    initial=execution(run,Path('initial'),plan)
    verify_execution(plan,initial,plan['initial'],before,True,'adapt','r064-initial')
    ref=check_reference(run,Path('initial'),initial,plan['initial']['observation'],truth)
    learn=unseal(load(run/'initial/learning.json'),'hcc-r064-learning-v1');check_learning(initial,ref,learn,before,after)
    base=unseal(load(run/'request.json'),'hcc-r064-request-v1');check_request(base,learn,ref)
    observed=unseal(load(run/'measurements.json'),'hcc-r064-measurements-v1')
    expected=measurements(plan,base,truth)
    require(observed==dict(schema='hcc-r064-measurements-v1',request_sha256=load(run/'request.json')['sha256'],observations=expected),'Exact requested external measurements')
    arms={};arm_executions={}
    for arm in plan['spec']['revision_arms']:
        path=Path('revision')/arm;e=execution(run,path,plan);obs=expected.get(arm,plan['initial']['observation'])
        check_revision(plan,e,obs,base,after);r=check_reference(run,path,e,obs,truth)
        arms[arm]=metrics(e,obs,truth);arm_executions[arm]=e
        if arm=='corrected_observation':
            final=unseal(load(run/path/'learning.json'),'hcc-r064-learning-v1');check_learning(e,r,final,after,last)
    require(not (run/'revision/same_observation/learning.json').exists(),'Unplanned control feedback')
    rows=[]
    for snapshot in plan['spec']['memory_snapshots']:
        memory=load(run/'memory'/f'{snapshot}.json')
        for gate in (False,True):
            for case in plan['cases']:
                identity=f"{snapshot}-{'on' if gate else 'off'}-{case['id']}";e=execution(run,Path('evaluation')/identity,plan)
                verify_execution(plan,e,case,memory,gate,'frozen_eval','r064-eval-'+identity)
                row=dict(identity=identity,snapshot=snapshot,use_circuits=gate,case=case['id'],**metrics(e,case['observation'],truth))
                if plan['purpose']!='research':row['rejected_mutations']=mutation_checks(plan,e,case,memory,gate,'frozen_eval','r064-eval-'+identity)
                rows.append(row)
    require(len(list((run/'evaluation').glob('*/inference.json')))==len(rows),'Exact frozen coverage')
    mutations=[]
    if plan['purpose']!='research':
        def reject(name,fn):
            try:fn()
            except (ValueError,AssertionError,RuntimeError,KeyError):mutations.append(name)
            else:raise AssertionError('Undetected mutation: '+name)
        bad=deepcopy(learn);bad['memory_after']['version']+=1
        reject('feedback_memory_publication',lambda:check_learning(initial,ref,bad,before,after))
        bad_request=deepcopy(base);bad_request['status']='invented'
        reject('request_status',lambda:check_request(bad_request,learn,ref))
        if base['request'] is not None:
            bad_e=deepcopy(arm_executions['same_observation']);bad_e['advances']+=1
            reject('revision_advance_count',lambda:check_revision(plan,bad_e,expected['same_observation'],base,after))
            bad_obs=deepcopy(expected['same_observation']);bad_obs['edges'][0]['score']=-0.5
            reject('revision_observation',lambda:check_revision(plan,arm_executions['same_observation'],bad_obs,base,after))
        require((base['request'] is not None)==(plan['matrix']=='smoke_request'),'Synthetic request/no-request coverage')
    initial_m=metrics(initial,plan['initial']['observation'],truth)
    cells={(r['snapshot'],r['use_circuits'],r['case']):r for r in rows}
    repeat=[cells[(s,True,'misleading-repeat')] for s in plan['spec']['memory_snapshots']]
    eligible=initial_m['measures']['adopted_correct'] is False and base['request'] is not None
    def verdict(value,applicable=True):return 'not_evaluable' if not applicable else 'supported' if value else 'falsified'
    predictions=dict(
        memory_changes_after_error=verdict(before!=after,ref['feedback'] is not None and ref['feedback']['correct'] is False),
        same_observation_revision_corrects=verdict(arms['same_observation']['measures']['adopted_correct'] is True,eligible and arm_executions['same_observation'] is not None),
        corrected_observation_revision_corrects=verdict(arms['corrected_observation']['measures']['adopted_correct'] is True,eligible and arm_executions['corrected_observation'] is not None),
        corrected_behavior_retained=verdict(repeat[-1]['measures']['adopted_correct'] is True,eligible and arms['corrected_observation']['measures']['adopted_correct'] is True))
    return dict(verified=True,initial=initial_m,request=base['request'],revision=arms,rows=rows,predictions=predictions,
        memory_changes=dict(after_feedback=before!=after,after_correction=after!=last),
        circuit_snapshots={s:load(run/'memory'/f'{s}.json')['circuits'] for s in plan['spec']['memory_snapshots']},
        adapt_executions=1+sum(e is not None for e in arm_executions.values()),frozen_executions=len(rows),
        synthetic_rejected_mutations=mutations,research=plan['purpose']=='research',
        independent_samples=False,independent_formula_replay=True,independent_process=True,independent_researcher=False,
        actual_energy_joules=None,peak_memory_bytes=None)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--run',type=Path,required=True)
    parser.add_argument('--phase',choices=['initial','measurements','revision','final'],default='final')
    args=parser.parse_args();run=args.run;plan=unseal(load(run/'plan.json'),'hcc-r064-plan-v1');spec=plan['spec']
    require(fingerprint(spec)==SPEC_FINGERPRINT and load(run/'source'/SPEC)==spec,'Frozen public spec')
    require(plan['initial']==spec[plan['matrix']]['initial'] and plan['cases']==spec[plan['matrix']]['cases'],'Frozen matrix')
    require(plan['config']==spec['config'] and plan['limits']==spec['limits'],'Frozen config/budget')
    require((plan['purpose']=='research')==(plan['matrix']=='research'),'Purpose/matrix')
    require(sha((run/'source_manifest.json').read_bytes())==plan['source_manifest_sha256'],'Source manifest binding')
    require(files(run/'source')==load(run/'source_manifest.json')['files'],'Frozen source hashes')
    worlds=load(run/'source'/WORLD);require(sha((run/'source'/WORLD).read_bytes())==spec['reference_worlds_sha256'],'Private world hash')
    truth=worlds[plan['matrix']]
    if args.phase=='initial':
        parent_audit(run,plan);e=execution(run,Path('initial'),plan)
        verify_execution(plan,e,plan['initial'],load(run/'memory/before.json'),True,'adapt','r064-initial')
        dump(run/'initial/reference.json',seal(dict(schema='hcc-r064-reference-v1',**reference(e,plan['initial']['observation'],truth),inference_sha256=load(run/'initial/inference.json')['sha256'])))
    elif args.phase=='measurements':
        base=unseal(load(run/'request.json'),'hcc-r064-request-v1');learn=unseal(load(run/'initial/learning.json'),'hcc-r064-learning-v1')
        ref=unseal(load(run/'initial/reference.json'),'hcc-r064-reference-v1');check_request(base,learn,ref)
        dump(run/'measurements.json',seal(dict(schema='hcc-r064-measurements-v1',request_sha256=load(run/'request.json')['sha256'],observations=measurements(plan,base,truth))))
    elif args.phase=='revision':
        base=unseal(load(run/'request.json'),'hcc-r064-request-v1');observations=measurements(plan,base,truth)
        for arm in spec['revision_arms']:
            path=Path('revision')/arm;e=execution(run,path,plan);obs=observations.get(arm,plan['initial']['observation'])
            check_revision(plan,e,obs,base,load(run/'memory/after_feedback.json'))
            dump(run/path/'reference.json',seal(dict(schema='hcc-r064-reference-v1',**reference(e,obs,truth),inference_sha256=load(run/path/'inference.json')['sha256'])))
    else:dump(run/'summary.json',final_audit(run,plan,truth))
    require(not (FORBIDDEN|{'hcr.learning','hcr.compiler','tools.r064_retention.worker'}) & set(sys.modules),'Auditor imported producer')
    print('independent audit passed',args.phase,flush=True)


if __name__=='__main__':main()
