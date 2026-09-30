"""Separate authored-world evaluator and independent formula replay; no producer imports."""
import argparse
from copy import deepcopy
from pathlib import Path
import sys
from hcr import codec
from hcr.evaluation.reference import reachable
from hcr.evaluation.review_audit import packet_states
from tools.r050_review_boundary.audit import candidate_measures, counter_values, FORBIDDEN
from tools.r050_review_boundary.common import dump, files, fingerprint, load, require, sha
from tools.r063_formation.audit import verify_execution, mutation_checks
from tools.r064_retention.audit import reference, check_learning, check_request, check_revision


def prediction(observed, expected, executed=True):
    return 'not_evaluable' if not executed or observed is None else (
        'supported' if observed is expected else 'falsified')


def payloads(plan, base, truth):
    request = base['request']; observations = {}
    if request is not None:
        require(request['edge_ids']==['e1'] and request['revision']==1, 'Single native requested edge')
        stale = deepcopy(plan['observation']); stale['revision']=1
        fresh = deepcopy(stale)
        fresh['edges'][1]['score'] = 1.0 if truth['e1'] else -1.0
        observations = dict(stale=stale,fresh=fresh)
    return dict(request_sha256=fingerprint(base), observations=observations,
        acquisition=dict(id='r069-shared-e1' if observations else None,
            source='frozen_ideal_toy_world',edge_ids=['e1'] if observations else [],
            scores=dict(e1=-1.0) if observations else {},calls=int(bool(observations)),
            measured_edges=int(bool(observations)),physical_sensor=False),
        cached_acquisition_calls=0)


def check_cell(plan, cell, row, base, measured, before, after):
    require(row['cell']==cell, 'Cell definition')
    obs = measured['observations'].get(cell['payload'])
    expected = dict(branch=cell['id'],payload=cell['payload'],observation=obs,
        request_sha256=fingerprint(base),measurement_sha256=fingerprint(measured),
        acquisition_id=measured['acquisition']['id'] if cell['payload']=='fresh' and obs else None)
    require(row['delivery']==expected, 'Branch payload/request/acquisition binding')
    e = row['execution']
    if obs is None:
        require(row['status']=='not_run_no_authorized_payload' and e is None, 'Missing payload boundary')
        return
    require(row['status']=='executed' and e is not None, 'Execution present')
    if cell['path']=='revision':
        check_revision(plan,e,obs,base,after)
    else:
        memory = before if cell['memory']=='M0' else after
        verify_execution(plan,e,dict(observation=obs),memory,True,'adapt','r069-'+cell['id'])
    doc=e['candidate']['packet']['document'] if e['candidate'] else e['packet']['document']
    feedback=[x for x in doc['events'] if x['event']=='r02_feedback']
    require(len(feedback)==int(cell['path']=='revision'), 'No followup feedback')
    require(doc['engine']['switches']['use_circuits'] is True, 'Configured ON gate')


def main(out, phase):
    plan=load(out/'plan.json');truth=load(out/'source'/plan['world_file'])
    require(plan==load(out/'source/experiments/exp-50-revision-factorization/frozen_spec.json'),'Frozen spec')
    require(sha((out/'source'/plan['world_file']).read_bytes())==plan['world_sha256'],'World binding')
    before=load(out/'memory/M0.json');initial=load(out/'initial/inference.json')
    require(before==load(out/'parent/memory/after_correction.json'),'Pinned M0')
    verify_execution(plan,initial,dict(observation=plan['observation']),before,True,'adapt','r069-donor')
    ref=reference(initial,plan['observation'],truth)
    if phase=='reference':
        dump(out/'initial/reference.json',ref);return
    require(load(out/'initial/reference.json')==ref,'Reference recomputation')
    after=load(out/'memory/M1.json');learn=load(out/'initial/learning.json');base=load(out/'request.json')
    check_learning(initial,ref,learn,before,after);check_request(base,learn,ref)
    measured=payloads(plan,base,truth)
    if phase=='measurements':
        dump(out/'measurements.json',measured);return
    require(load(out/'measurements.json')==measured,'Requested shared payloads')
    for folder,manifest in [('source','source_manifest.json'),('parent','input_manifest.json'),
                            ('evaluation','raw_manifest.json')]:
        require(files(out/folder)==load(out/manifest)['files'],'Coverage '+folder)
    require(files(out/'parent')==plan['parent_files'],'Parent input coverage')
    rows=[]
    for cell in plan['cells']:
        row=load(out/'evaluation'/cell['id']/'inference.json')
        check_cell(plan,cell,row,base,measured,before,after)
        e=row['execution'];obs=row['delivery']['observation']
        m=candidate_measures(e,False)
        rows.append(dict(**cell,status=row['status'],measures=m,cost=counter_values(e) if e else None,
            external_assessment=reference(e,obs,truth)['assessment'] if obs else None,
            configured_gate=True,effective_circuit_eligibility=cell['path']=='new',
            sensor_acquisition_calls_at_branch=0,payload_deliveries=int(obs is not None)))
    require({p.name for p in (out/'evaluation').iterdir()}=={c['id'] for c in plan['cells']},'Exact cell coverage')
    changes=learn['patch']['changes'] if learn['patch'] else []
    engaged=any(c['kind']=='weaken' for c in changes)
    initial_m=candidate_measures(initial,False)
    eligible=ref['feedback'] is not None and ref['feedback']['correct'] is False
    predictions=dict(donor_raw_wrong=prediction(initial_m['raw_correct'],False),
        donor_adopted_true=prediction(initial_m['adopted_value'],True),
        error_weakens_reused_circuit='not_evaluable' if not eligible else
        ('supported' if engaged else 'learning_construct_not_engaged'),
        request_single_e1='not_evaluable' if not eligible else
        ('supported' if base['request'] is not None and base['request']['edge_ids']==['e1'] else 'falsified'))
    for row in rows:
        expected_correct=row['payload']=='fresh'
        observed=row['measures']['adopted_correct']
        predictions[row['id']+'_prediction']=prediction(observed,expected_correct,row['status']=='executed')
    rejected=mutation_checks(plan,initial,dict(observation=plan['observation']),before,True,'adapt','r069-donor') if initial['candidate'] else []
    def reject(name,call):
        try:call()
        except (ValueError,AssertionError,RuntimeError,KeyError):rejected.append(name)
        else:raise AssertionError('Undetected mutation '+name)
    if initial['candidate'] is None:
        bad=deepcopy(initial);bad['advances']+=1
        reject('partial_donor_count',lambda:verify_execution(plan,bad,dict(observation=plan['observation']),before,True,'adapt','r069-donor'))
    for cell in plan['cells']:
        original=load(out/'evaluation'/cell['id']/'inference.json')
        bad=deepcopy(original);bad['delivery']['measurement_sha256']='0'*64
        reject(cell['id']+'_delivery',lambda:check_cell(plan,cell,bad,base,measured,before,after))
    if base['request'] is not None:
        bad=deepcopy(base);bad['request']['edge_ids']=['e0']
        reject('request_edge',lambda:check_request(bad,learn,ref))
        cell=next(c for c in plan['cells'] if c['path']=='revision')
        bad=deepcopy(load(out/'evaluation'/cell['id']/'inference.json'))
        bad['execution']['advances']+=1
        reject('revision_count',lambda:check_cell(plan,cell,bad,base,measured,before,after))
    bad=deepcopy(learn);bad['memory_after']['version']+=1
    reject('learning_checkpoint',lambda:check_learning(initial,ref,bad,before,after))
    require(not (FORBIDDEN|{'hcr.learning','hcr.compiler','tools.r069_revision.worker',
        'tools.r063_formation.worker','tools.r064_retention.worker'}) & set(sys.modules),'Evaluator producer import boundary')
    cells={r['id']:r for r in rows}
    pairs={}
    for payload in ('stale','fresh'):
        pairs['memory_'+payload]=dict(first='new-M0-'+payload,second='new-M1-'+payload,
            first_value=cells['new-M0-'+payload]['measures']['adopted_value'],
            second_value=cells['new-M1-'+payload]['measures']['adopted_value'],
            interpretation='checkpoint intervention; not feedback-information-only')
        pairs['path_'+payload]=dict(first='new-M1-'+payload,second='revision-M1-'+payload,
            first_value=cells['new-M1-'+payload]['measures']['adopted_value'],
            second_value=cells['revision-M1-'+payload]['measures']['adopted_value'],
            interpretation='revision API path bundle; not pure session persistence')
    dump(out/'summary.json',dict(initial=dict(measures=initial_m,cost=counter_values(initial)),
        feedback=ref['feedback'],patch=learn['patch'],learning_construct='engaged' if engaged else 'not_engaged',
        request=base['request'],rows=rows,pairs=pairs,predictions=predictions,
        donor_executions=1,followup_executions=sum(r['status']=='executed' for r in rows),
        feedback_applications=int(learn['status']=='applied'),independent_samples=False,
        sensor_acquisition_calls=measured['acquisition']['calls'],
        measured_edges=measured['acquisition']['measured_edges'],
        fresh_deliveries=sum(r['payload']=='fresh' and r['status']=='executed' for r in rows),
        cached_deliveries=sum(r['payload']=='stale' and r['status']=='executed' for r in rows),
        cost_accounting='donor, feedback and acquisition recorded once; branch costs exclude copied history',
        actual_energy_joules=None,peak_memory_bytes=None,physical_sensor=False,
        claim_boundary='Authored binary toy world. Feedback already discloses the target label. No autonomous sensing, pure feedback or persistence effect.'))
    dump(out/'verification.json',dict(verified=True,formula_replays=1+sum(r['status']=='executed' for r in rows),
        rejected_mutations=rejected,independent_process=True,independent_researcher=False))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True)
    p.add_argument('--phase',choices=['reference','measurements','final'],required=True)
    a=p.parse_args();main(a.out,a.phase)
