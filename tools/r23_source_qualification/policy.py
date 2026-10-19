"""Finite source qualification, not a reliability probability or source authentication."""
from tools.r22_measurement_adoption.policy import (require,validate_public,choose as old_choose,request_for,adoption as old_adoption,response_spec)
from tools.r21_active_measurement.policy import accept_response
from hcr.model import fingerprint
from hcr.codec import plain

def qualify(records,p):
    require(len(records)==len(p['calibration'])*len(p['sources']),'calibration record count')
    expected={(c['key'],s) for c in p['calibration'] for s in p['sources']}
    require({(r['key'],r['source']) for r in records}==expected,'calibration matrix')
    summary=[]
    for source in p['sources']:
        rows=[r for r in records if r['source']==source];passed=0
        for r in rows:
            ok=False
            try:
                updated=accept_response(r['public'],r['request'],r['response']['measurement'],response_spec(source,p))
                scores=updated['measurements'];signs=r['known_feature_signs']
                require(len(signs)==2 and all(type(v) is bool for v in signs),'known calibration signs')
                ok=all(abs(v)>=p['qualification']['feature_min_abs_score'] and (v>0)==truth for v,truth in zip(scores,signs,strict=True))
            except ValueError:pass
            passed+=int(ok)
        n=len(rows);failures=n-passed
        summary.append(dict(source_id=source,examples=n,passed=passed,failures=failures,
            qualified=n==p['qualification']['required_examples_per_source'] and failures<=p['qualification']['maximum_failures']))
    # Only these aggregate counters reach the evaluation policy. No evaluation labels or fault modes.
    return dict(sources=summary,calibration_sha256=fingerprint(plain(records)),rule_sha256=fingerprint(p['qualification']))

def choose(public,initial,arm,p,certificate):
    require(arm in p['arms'],'arm')
    if arm!='qualified_single':return old_choose(public,initial,arm,p)
    require(certificate['rule_sha256']==fingerprint(p['qualification']),'qualification rule binding')
    require([s['source_id'] for s in certificate['sources']]==p['sources'],'qualification source binding')
    for s in certificate['sources']:
        require(type(s['examples']) is int and type(s['passed']) is int and type(s['failures']) is int and 0<=s['passed']<=s['examples'], 'qualification counters')
        require(s['failures']==s['examples']-s['passed'],'qualification failures')
        require(s['qualified']==(s['examples']==p['qualification']['required_examples_per_source'] and s['failures']<=p['qualification']['maximum_failures']),'qualification decision')
    gate=old_choose(public,initial,'single_contract',p)
    selected=next((s['source_id'] for s in certificate['sources'] if s['qualified']),None)
    if gate['action']=='request':
        if selected is None:gate.update(action='retain',reason='no_qualified_source',sources=[])
        else:gate.update(reason='public_condition_budget_and_qualification',sources=[selected])
    gate.update(qualification_sha256=fingerprint(certificate))
    return gate

def adoption(public,arm,requests,responses,p):
    # Identical single-response contract: the new independent variable is pre-query source selection.
    return old_adoption(public,'single_contract' if arm=='qualified_single' else arm,requests,responses,p)
