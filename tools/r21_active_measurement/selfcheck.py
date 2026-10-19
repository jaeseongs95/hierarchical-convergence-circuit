"""Pure request/budget/response checks and saved trace replay; no new kernel or sensor calls."""
from copy import deepcopy
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from hcr import dynamics
from hcr.model import Cost
from hcr.tasks.toy_world import World
from tools.r21_active_measurement import probe,sensor
from tools.r21_active_measurement.policy import choose,request_for,accept_response,validate_public,require


def check(portable):
    p=probe.spec();fixtures=probe.read(probe.SPEC.with_name('sensor-fixtures.json'));golden=probe.read(probe.SPEC.with_name('fixture.json'))
    tolerance=p['numeric_replay_absolute_tolerance_portable'] if portable else p['numeric_replay_absolute_tolerance_server'];count=0
    def assertion(ok,message):
        nonlocal count
        require(ok,message);count+=1
    assertion(len(p['cases'])==10 and len({c['key'] for c in p['cases']})==10,'matrix')
    for cell in p['cases']:
        validate_public(cell['public']);fixture=fixtures[cell['key']]
        assertion(len(fixture['hidden_features'])==2 and all(type(v) is bool for v in fixture['hidden_features']),'feature fixture')
        assertion(fixture['mode'] in ['valid','stale','no_information','flipped'],'fault fixture')
    original=(dynamics.tick,dynamics.settle,World.measure,probe.base.execute)
    def forbidden(*args,**kwargs):raise AssertionError('native kernel/sensor call in pure preparation')
    dynamics.tick=dynamics.settle=World.measure=forbidden
    maximum=0.0
    try:
        for e in golden.values():
            maximum=max(maximum,probe.base.audit_execution(e,e['public'],'gated',p['base'],tolerance))
            assertion(maximum<=tolerance,'saved base trace replay')
        clear_pub=next(c['public'] for c in p['cases'] if c['key']=='clear_A');saved=deepcopy(golden['clear'])
        outer=dict(public=clear_pub,arm='no_query',initial=saved,request_gate=choose(clear_pub,saved,'no_query',p),
            request=None,response=None,response_error=None,measurement_changed=None,revised=None,
            final=dict(category=saved['category'],relation=saved['relation']),final_source='initial',
            measurement_wall_seconds=0.0,provider_calls=0,ledger=probe.ledger(None,None,p),cost=probe.costs(saved,None),
            training_calls=0,native_revision_controller=False,native_measurement_contract=True)
        assertion(probe.audit_execution(outer,clear_pub,'no_query',p,fixtures['clear_A'],tolerance)<=tolerance,'saved outer auditor replay')
        pub=next(c['public'] for c in p['cases'] if c['key']=='missing_aux_A')
        initial=dict(category=None,kernels=[dict(convergence=dict(status='stable_ambiguous'))])
        renamed=deepcopy(pub);renamed['observation']['id']='renamed'
        assertion(choose(renamed,initial,'primary_uncertainty',p)['action']==choose(pub,initial,'primary_uncertainty',p)['action'],'identity does not choose request')
        for field,value,reason in [('requests',0,'request_budget'),('feature_units',1,'feature_budget'),('revision_settles',3,'revision_compute_budget')]:
            bad=deepcopy(pub);bad['budget'][field]=value
            assertion(choose(bad,initial,'primary_uncertainty',p)['reason']==reason,'budget before provider')
        request=request_for(pub,initial,'primary_uncertainty',p)
        response=sensor.expected(pub,request,fixtures['missing_aux_A'],p)
        updated=accept_response(pub,request,response,p)
        assertion(updated['revision']==1 and updated['measurements']==[.98,.98],'typed response adapter')
        for mutation,message in [('revision','response revision'),('source','response source'),('request_hash','response request binding'),('targets','response measurement targets')]:
            bad=deepcopy(response)
            if mutation=='revision':bad['observation']['revision']=0
            elif mutation=='source':bad['source_id']='unknown'
            elif mutation=='request_hash':bad['request_sha256']='0'*64
            else:bad['observation']['edges'][0]['id']='other'
            try:accept_response(pub,request,bad,p)
            except ValueError as exc:assertion(str(exc)==message,'response rejection cause')
            else:raise ValueError('invalid response accepted')
        polluted=dict(pub,hidden_truth=True)
        try:validate_public(polluted)
        except ValueError:count+=1
        else:raise ValueError('hidden truth field accepted')
        try:probe.handle_terminate(15,None)
        except TimeoutError:count+=1
        else:raise ValueError('termination handler did not raise')
        def fake_execute(case,arm,base_spec):
            # Deliberately synthetic orchestration stub, not an experiment or auditor result.
            decided=any(case['measurements']);status='stable_decision' if decided else 'stable_ambiguous'
            low=dict(convergence=dict(status=status),state=dict(goal=.9 if sum(case['measurements'])>0 else .5),cost=Cost().snapshot())
            gate=probe.base.decide(case,low,base_spec)
            category=sum(case['measurements'])>0 if decided else (case['context']>0 if gate['action']=='feedback' else None)
            calls=1 if gate['action']=='abstain' else (4 if gate['action']=='feedback' else 2)
            kernels=[dict(kind='lower_initial',**low)]+[dict(kind='stub',cost=Cost().snapshot()) for _ in range(calls-1)]
            return dict(public=case,category=category,relation=None if category is None else category==(case['context']>0),kernels=kernels)
        probe.base.execute=fake_execute
        requests=0
        for cell in p['cases']:
            for arm in p['arms']:
                calls=[]
                def deliver(req):
                    calls.append(req);return sensor.expected(cell['public'],req,fixtures[cell['key']],p)
                e=probe.execute(cell['public'],arm,p,deliver)
                assertion(len(calls)==e['provider_calls']==e['ledger']['requests_used']<=1,'one-shot callback')
                assertion(e['ledger']['feature_units_charged']==2*len(calls),'failed calls are charged too')
                assertion(e['ledger']['additional_settles_used']<=e['ledger']['additional_settles_reserved']<=cell['public']['budget']['revision_settles'],'compute budget')
                if arm=='no_query':assertion(len(calls)==0,'no provider in control')
                if cell['key'] in ['feature_budget_A','compute_budget_A']:assertion(len(calls)==0,'no provider after budget refusal')
                if cell['key']=='stale_reply_A' and calls:assertion(e['response_error']=='response revision' and e['revised'] is None and e['final']['category'] is None,'stale reply withholding')
                if cell['key']=='no_information_A' and calls:assertion(e['measurement_changed'] is False,'revision alone is not new information')
                requests+=len(calls)
        assertion(requests<=p['maximum_measurement_requests'],'global stub request cap')
    finally:
        dynamics.tick,dynamics.settle,World.measure,probe.base.execute=original
    return dict(status='PURE_PREPARATION_PASSED',assertions=count,stub_cells=30,new_native_settle_calls=0,new_world_measure_calls=0,
        saved_record_max_absolute_error=maximum,numeric_tolerance=tolerance,
        notice='Stub cells/adapter formulas are preparation checks, not experimental observations.')


if __name__=='__main__':
    import json
    print(json.dumps(check(portable=True),sort_keys=True))
