"""One-shot measurement requests based only on recorded inference and public budget."""
from copy import deepcopy
from hcr.codec import observation_from,plain
from hcr.model import Observation,EdgeObservation,ObservationRequest,fingerprint
from tools.r20_evidence_feedback.policy import require,validate


def validate_public(public):
    require(set(public)=={'observation','budget'},'public outer fields')
    validate(public['observation']);budget=public['budget']
    require(set(budget)=={'requests','feature_units','revision_settles'},'budget fields')
    require(all(type(v) is int and v>=0 for v in budget.values()),'nonnegative budget')
    require(budget['requests']<=1 and budget['feature_units']<=2 and budget['revision_settles']<=4,'bounded experiment budget')


def panel(case):
    return Observation(case['id'],case['revision'],'s','t',(
        EdgeObservation('f0','s','m',case['measurements'][0]),EdgeObservation('f1','m','t',case['measurements'][1])))


def choose(public,initial,arm,p):
    validate_public(public);require(arm in p['arms'],'arm');quote=p['request_quote'];budget=public['budget']
    def result(action,reason,trigger):
        return dict(action=action,reason=reason,trigger=trigger,public_sha256=fingerprint(public),
            initial_sha256=fingerprint(initial),quote_sha256=fingerprint(quote))
    if arm=='no_query':return result('retain','no_query_control',False)
    trigger=(initial['category'] is None if arm=='after_abstention' else
        initial['kernels'][0]['convergence']['status']=='stable_ambiguous')
    if not trigger:return result('retain','condition_not_met',False)
    if budget['requests']<1:return result('retain','request_budget',True)
    if budget['feature_units']<quote['feature_units']:return result('retain','feature_budget',True)
    if budget['revision_settles']<quote['revision_settle_reservation']:return result('retain','revision_compute_budget',True)
    return result('request','public_condition_and_budget',True)


def request_for(public,initial,arm,p):
    case=public['observation']
    return ObservationRequest(fingerprint(initial),case['id'],case['revision']+1,
        tuple(p['request_quote']['feature_ids']),'final_abstention' if arm=='after_abstention' else 'primary_uncertainty')


def accept_response(public,request,response,p):
    require(isinstance(response,dict) and set(response)=={'source_id','request_sha256','observation'},'response fields')
    require(response['source_id']==p['request_quote']['source_id'],'response source')
    require(response['request_sha256']==fingerprint(plain(request)),'response request binding')
    observed=observation_from(response['observation']);old=panel(public['observation'])
    require(observed.episode_id==old.episode_id,'response episode')
    require(observed.revision==request.revision and request.revision==old.revision+1,'response revision')
    require(observed.start==old.start and observed.goal==old.goal,'response topology')
    require([(e.id,e.source,e.target) for e in observed.edges]==[(e.id,e.source,e.target) for e in old.edges],'response measurement targets')
    require(list(request.edge_ids)==p['request_quote']['feature_ids'],'request measurement targets')
    updated=deepcopy(public['observation']);updated['revision']=observed.revision
    updated['measurements']=[edge.score for edge in observed.edges]
    validate(updated)
    return updated
