"""Public measurement-contract and corroboration gates; no reference labels."""
from hcr.model import ObservationRequest,fingerprint
from hcr.codec import plain
from tools.r20_evidence_feedback.policy import require,validate
from tools.r21_active_measurement.policy import accept_response


def validate_public(public):
    require(set(public)=={'observation','budget'},'public fields');validate(public['observation'])
    budget=public['budget'];require(set(budget)=={'requests','feature_units','revision_settles'},'budget fields')
    require(all(type(v) is int and v>=0 for v in budget.values()),'nonnegative budget')
    require(budget['requests']<=2 and budget['feature_units']<=4 and budget['revision_settles']<=4,'experiment budget range')


def choose(public,initial,arm,p):
    validate_public(public);require(arm in p['arms'],'arm')
    sources=[] if arm=='no_query' else p['sources'][:1 if arm=='single_contract' else 2]
    trigger=arm!='no_query' and initial['kernels'][0]['convergence']['status']=='stable_ambiguous'
    count=len(sources);budget=public['budget'];reason='condition_not_met';action='retain'
    if trigger:
        if budget['requests']<count:reason='request_budget'
        elif budget['feature_units']<count*p['feature_units_per_request']:reason='feature_budget'
        elif budget['revision_settles']<p['revision_settle_reservation']:reason='revision_compute_budget'
        else:action='request';reason='public_condition_and_budget'
    return dict(action=action,reason=reason,trigger=trigger,sources=sources if action=='request' else [],
        public_sha256=fingerprint(public),initial_sha256=fingerprint(initial))


def request_for(public,initial,source,p):
    case=public['observation']
    return ObservationRequest(fingerprint(initial),case['id'],case['revision']+1,tuple(p['feature_ids']),'adoption_probe:'+source)


def response_spec(source,p):return dict(request_quote=dict(source_id=source,feature_ids=p['feature_ids']))


def adoption(public,arm,requests,responses,p):
    def result(action,reason,updated=None):return dict(action=action,reason=reason,responses_sha256=fingerprint(responses)),updated
    updated=[]
    for (source,request),bundle in zip(requests,responses,strict=True):
        try:
            require(set(bundle)=={'measurement','acquisition_id','root_measurement_ids'},'bundle fields')
            updated.append(accept_response(public,request,bundle['measurement'],response_spec(source,p)))
            if arm=='corroborated':
                roots=bundle['root_measurement_ids'];acquisition=bundle['acquisition_id']
                require(isinstance(roots,list) and 1<=len(roots)<=4 and all(isinstance(v,str) and 0<len(v)<=80 for v in roots),'declared roots')
                require(len(set(roots))==len(roots) and isinstance(acquisition,str) and 0<len(acquisition)<=160,'declared acquisition')
        except ValueError as exc:return result('abstain','contract:'+str(exc))
    if arm=='corroborated':
        require(len(updated)==2,'two responses')
        if responses[0]['acquisition_id']==responses[1]['acquisition_id']:return result('abstain','same_acquisition')
        if not set(responses[0]['root_measurement_ids']).isdisjoint(responses[1]['root_measurement_ids']):return result('abstain','declared_root_overlap')
        scores=[u['measurements'] for u in updated]
        if any(abs(v)<p['acceptance_min_abs_score'] for row in scores for v in row):return result('abstain','insufficient_strength')
        if any((a>0)!=(b>0) for a,b in zip(*scores,strict=True)):return result('abstain','feature_disagreement')
    # Witness gates acceptance only; it is never averaged or added to the first score.
    return result('adopt','single_contract' if arm=='single_contract' else 'declared_separation_and_feature_agreement',updated[0])


def cell_caps(book,budget):
    require(0<=book['requests_used']<=budget['requests'] and book['requests_used']<=2,'request cap')
    require(0<=book['feature_units_charged']<=budget['feature_units'],'measurement unit cap')
    require(0<=book['additional_settles_used']<=book['additional_settles_reserved']<=budget['revision_settles'],'revision reservation')


def global_caps(requests,settles,p):
    require(0<=requests<=p['maximum_measurement_requests'],'global measurement cap')
    require(0<=settles<=p['maximum_native_settle_calls'],'global settle cap')


def stage_violations(rc,raw_bytes,limit):
    return (['stage failure'] if rc!=0 else [])+(['raw stage-end size'] if raw_bytes>=limit else [])
