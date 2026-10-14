"""정책 결과 확정 뒤에만 world/anchor를 읽는 별도 평가 프로세스."""
from fractions import Fraction as Q
import hashlib
from pathlib import Path
import time
import termination_compare_core as core


def file_bound(ref):
    raw=Path(ref['path']).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=ref['sha256']:raise ValueError('evaluation artifact hash')
    return core.decode(raw)


def distance(current,anchor,epsilon=core.EPSILON):
    B=core.parse_box(current)
    if len(anchor)!=7 or any(len(p)!=2 for p in anchor):raise ValueError('whole7 anchor')
    A=[tuple(map(Q,p)) for p in anchor]
    if any(not -1<=lo<=hi<=1 for lo,hi in A):raise ValueError('anchor order/domain')
    lower=max(max(Q(0),lo-ah,al-hi) for (lo,hi),(al,ah) in zip(B,A))/2
    upper=max(max(abs(lo-ah),abs(hi-al)) for (lo,hi),(al,ah) in zip(B,A))/2
    return {'lower_p_exact':str(lower),'upper_p_exact':str(upper),
            'status':'INSIDE' if upper<=epsilon else 'OUTSIDE' if lower>epsilon else 'AMBIGUOUS'}


def reachability(observation,truth,allowed_edges=None):
    edges=observation['edges'];ids=[e['id'] for e in edges]
    if len(ids)!=len(set(ids)) or set(truth)!=set(ids) or any(type(v)is not bool for v in truth.values()):
        raise ValueError('world must cover exactly public edge identities with booleans')
    if allowed_edges is not None and not set(allowed_edges)<=set(ids):raise ValueError('processed edges')
    seen={observation['start']};frontier=[observation['start']]
    while frontier:
        node=frontier.pop()
        for edge in edges:
            if (edge['source']==node and truth[edge['id']]
                    and (allowed_edges is None or edge['id'] in allowed_edges)
                    and edge['target'] not in seen):
                seen.add(edge['target']);frontier.append(edge['target'])
    return observation['goal'] in seen


def independent_model(public):
    order=core.ORDER;program=public['program'];kernel=public['kernel']
    if [g['id'] for g in program['groups']]!=order:raise ValueError('evaluator order')
    def lifted(v):return Q.from_float(float(v))
    if lifted(kernel['temperature'])!=1:raise ValueError('temperature')
    biases={g['id']:lifted(g['bias']) for g in program['groups']}
    b=[biases[key]+Q(public['drives'].get(key,'0')) for key in order]
    G=[[Q(0)]*7 for _ in order]
    for edge in program['links']:
        if edge['kind'] not in ('support','top_down'):raise ValueError('link kind')
        G[order.index(edge['target'])][order.index(edge['source'])]+=lifted(edge['weight'])
    diagonal=(lifted(kernel['self_excitation'])+lifted(kernel['inhibition']))/2
    for i in range(7):G[i][i]+=diagonal
    return {'b':list(map(str,b)),'G':[list(map(str,row)) for row in G],
            'd':str(lifted(kernel['damping']))}


def evaluate_worker(input_path,input_sha,release):
    # Policy seal is authenticated before any truth or future-reference loader is called.
    start=release['start'];meter=core.Meter(release['deadline']);meter.guard()
    raw=Path(input_path).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=input_sha:raise ValueError('evaluation input hash')
    request=core.decode(raw)
    if (set(request)!= {'schema','repo','policy_seal','public_input','world','distance_reference'}
            or request['schema']!='HCCTerminationEvaluationInput.v1'):
        raise ValueError('evaluation input fields')
    seal=file_bound(request['policy_seal'])
    if seal.get('schema')!='HCCTerminationSealedCell.v1':raise ValueError('policy not sealed')
    data=file_bound(request['public_input'])
    if seal['input_sha256']!=request['public_input']['sha256']:raise ValueError('seal input binding')
    model=independent_model(data['public']);model_digest=core.digest(model)
    if (model_digest!=data['model_digest'] or model_digest!=seal['model_digest']
            or core.digest(data['public']['observation'])!=seal['observation_digest']
            or core.digest(data['public']['processed'])!=seal['processed_digest']):
        raise ValueError('model/observation/processed seal binding')
    world=file_bound(request['world'])
    if (world.get('schema')!='HCCTerminationWorld.v1'
            or world['observation_digest']!=data['observation_digest']
            or world['authored_synthetic_world'] is not True):raise ValueError('independent world binding')
    observation=data['public']['observation']
    truth=reachability(observation,world['truth'])
    processed_edges={e for path in data['public']['processed']['paths'] for e in path}
    first_truth=reachability(observation,world['truth'],processed_edges)
    meter.guard()
    last=seal['last_complete']
    result={'schema':'HCCTerminationEvaluation.v1','candidate':None,'candidate_correct':None,
            'full_public_truth':truth,'processed_path_truth':first_truth,'distance':{'status':'NOT_EVALUATED'},
            'adopted_value':'NOT_MEASURED','full_engine_accuracy':'NOT_ESTABLISHED',
            'proof_validity':None,'support_gap':None,'D_DAG':None,'proof_status':'NOT_MEASURED',
            'processed_graph_complete':data['public']['processed']['complete'],
            'remaining_public_paths':[data['public']['processed']['remaining_public_path']],
            'actual_controller_frontier':'NOT_MEASURED',
            'candidate_evidence':'source-bound sequential supplier output; not full prefix replay',
            'reference_evidence':'trusted pinned accepted old anchor; no old physics rerun'}
    if last is not None:
        snapshot=last['snapshot'];ack=last['ack'];B=snapshot['current_x_box']
        name=ack['path']
        if (not isinstance(name,str) or len(name)!=17 or not name.startswith('state-')
                or not name[6:12].isdigit() or name[12:]!='.json'):
            raise ValueError('state file name')
        state_bytes=(Path(request['policy_seal']['path']).parent/name).read_bytes()
        if hashlib.sha256(state_bytes).hexdigest()!=ack['sha256'] or core.decode(state_bytes)!=snapshot:
            raise ValueError('sealed snapshot source binding')
        if (snapshot['tick']!=ack['tick'] or snapshot['model_digest']!=model_digest
                or snapshot['observation_digest']!=data['observation_digest']
                or snapshot['processed_digest']!=data['processed_digest']
                or ack['completed_monotonic']>seal['supervision']['deadline_monotonic']):
            raise ValueError('last complete context/time')
        # Recheck diagnostic semantics in the evaluator, never fill a policy readout after timeout.
        diagnostic=core.diagnostic(B,partial=not data['public']['processed']['complete'])
        if diagnostic!=snapshot['diagnostic']:raise ValueError('diagnostic mismatch')
        candidate=diagnostic['candidate']
        result.update(tick=snapshot['tick'],candidate=candidate,
                      candidate_correct=None if candidate is None else candidate==truth,
                      coverage_required=diagnostic['coverage_required'])
        repo=Path(request['repo']).resolve();ref=request['distance_reference']
        relative=Path(ref['path'])
        if relative.is_absolute() or '..' in relative.parts:raise ValueError('reference traversal')
        anchor_path=(repo/relative).resolve()
        if not anchor_path.is_relative_to(repo):raise ValueError('reference outside repo')
        anchor_bytes=anchor_path.read_bytes()
        if len(anchor_bytes)!=ref['bytes'] or hashlib.sha256(anchor_bytes).hexdigest()!=ref['sha256']:
            raise ValueError('trusted anchor source pin')
        record=core.decode(anchor_bytes);checked=record['independent_verification']
        if (checked['accepted'] is not True or checked['model_digest']!=model_digest
                or checked['state_order']!=core.ORDER or checked['sample_id']!='above_near'
                or checked['all7'] is not True or checked['anchor']['tick']!=6144):
            raise ValueError('anchor context/accepted proof')
        result['distance']=distance(B,checked['anchor']['x_box_exact'])
        final=seal['final']
        result['gate_state']=snapshot['gate_state']
        if final is not None:
            if final['input_sha256']!=seal['input_sha256'] or final['last_complete']!=ack:
                raise ValueError('final seal context')
            if final['stop_reason']=='CERTIFIED':
                if seal['supervision']['status']!='COMPLETE' or snapshot['policy']!='C':
                    raise ValueError('unsealed/pending certificate')
                arithmetic=core.Arithmetic(data['math_sources'],meter)
                certificate=arithmetic.certificate(model,B)
                if (certificate!=final['certificate']
                        or certificate['bounds']['component_vector'][0]['status']!='CERTIFIED_WITHIN_EPS'):
                    raise ValueError('local certificate recheck mismatch')
                result['local_certificate_recheck']='PASS_shared_pinned_numeric_helpers'
            elif final['certificate'] is not None:raise ValueError('certificate on noncertified stop')
            result['gate_state']=final.get('last_gate_status','INCONCLUSIVE')
    meter.guard()
    result.update(evaluator_wall_seconds=time.monotonic()-start,
                  evaluator_cpu_seconds=time.process_time(),evaluation_counts=dict(meter.counts),
                  world_kind='authored_synthetic_not_real_world_observation')
    import termination_compare_runner as runner
    runner.write_new(Path(release['out'])/'result.json',result);meter.guard()


def aggregate(rows):
    expected=['180/L','180/F','180/C','1800/C','1800/F','1800/L']
    seen={}
    for row in rows:
        if row['cell'] not in expected or row['cell'] in seen:raise ValueError('cell inventory')
        seen[row['cell']]=row
    complete=[seen.get(label,{'cell':label,'status':'NOT_RUN','evaluation':None}) for label in expected]
    by_budget={}
    for budget in (180,1800):
        group=[r for r in complete if r['cell'].startswith(str(budget)+'/')]
        assessed=[r for r in group if r.get('evaluation') is not None
                  and r.get('status') not in ('MEASUREMENT_FAILURE','CLEANUP_NOT_CONFIRMED','NOT_RUN','INCONCLUSIVE')]
        answered=[r for r in assessed if r['evaluation']['candidate'] is not None]
        correct=sum(r['evaluation']['candidate_correct'] is True for r in answered)
        by_budget[str(budget)]={'planned_denominator':3,'evaluable':len(assessed),
            'answered':len(answered),'correct':correct,
            'conditional_accuracy':correct/len(answered) if answered else None,
            'answer_coverage_over_planned':len(answered)/3,
            'status_counts':{s:sum(r['status']==s for r in group) for s in {r['status'] for r in group}}}
    return {'schema':'HCCTerminationComparisonSummary.v1','planned_denominator':6,
            'independent_discovery_samples':0,'by_budget':by_budget,'rows':complete,
            'full_engine_accuracy':'NOT_ESTABLISHED','cost_units_combined':False,
            'energy':None,'rss_peak_bytes':None}
