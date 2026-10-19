"""Pure orchestration, cap rejection and saved-record replay; no new measurements."""
from copy import deepcopy
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from hcr import dynamics
from hcr.model import Cost
from hcr.tasks.toy_world import World
from tools.r22_measurement_adoption import probe,sensor
from tools.r22_measurement_adoption.policy import (choose,request_for,adoption,validate_public,require,cell_caps,global_caps,stage_violations)


def check(portable):
    p=probe.spec();fixtures=probe.read(probe.SPEC.with_name('sensor-fixtures.json'));golden=probe.read(probe.SPEC.with_name('fixture.json'));count=0
    tolerance=p['numeric_replay_absolute_tolerance_portable'] if portable else p['numeric_replay_absolute_tolerance_server']
    def assertion(ok,message):
        nonlocal count
        require(ok,message);count+=1
    def rejected(call,message):
        try:call()
        except ValueError as exc:assertion(str(exc)==message,'exact rejection cause '+str(exc))
        else:raise ValueError('guard not exercised '+message)
    assertion(len(p['cases'])==13 and len(p['arms'])==3,'matrix')
    limits=p['limits']
    assertion(0<limits['child_address_space_bytes']<=limits['parent_address_space_bytes']<=512*1024**2 and
        0<limits['child_file_bytes']<=limits['parent_file_bytes']<=32*1024**2,'parent and worker cap contract')
    for cell in p['cases']:
        validate_public(cell['public'])
        for fixture in fixtures[cell['key']].values():
            assertion(len(fixture['hidden_features'])==2 and all(type(v) is bool for v in fixture['hidden_features']),'private feature fixture')
            assertion(fixture['mode'] in ['valid','flipped','no_information','stale','weak'],'private fault mode')
    original=(dynamics.tick,dynamics.settle,World.measure,probe.base.execute)
    def forbidden(*args,**kwargs):raise AssertionError('new native kernel or measurement in pure preparation')
    dynamics.tick=dynamics.settle=World.measure=forbidden;maximum=0.
    try:
        for saved in golden.values():
            maximum=max(maximum,probe.base.audit_execution(saved,saved['public'],'gated',p['base'],tolerance))
            assertion(maximum<=tolerance,'saved R20 record replay')
        cell=next(c for c in p['cases'] if c['key']=='clear_A');saved=deepcopy(golden['clear']);public=cell['public']
        outer=dict(public=public,arm='no_query',initial=saved,request_gate=choose(public,saved,'no_query',p),requests=[],responses=[],adoption=None,revised=None,
            final=dict(category=saved['category'],relation=saved['relation']),final_source='initial',ledger=probe.ledger([],None,p),cost=probe.costs(saved,None),
            measurement_wall_seconds=0.,provider_calls=0,training_calls=0,native_revision_controller=False)
        assertion(probe.audit_execution(outer,public,'no_query',p,fixtures['clear_A'],tolerance)<=tolerance,'saved outer record replay')
        for name in ['upper_tick','upper_program_bias']:
            rejected(lambda n=name:probe.audit_execution(probe.mutate(outer,n),public,'no_query',p,fixtures['clear_A'],tolerance),probe.MUTATIONS[name])
        book=dict(requests_used=2,feature_units_charged=4,additional_settles_reserved=4,additional_settles_used=2,reservation_released=2)
        budget=dict(requests=2,feature_units=4,revision_settles=4)
        for field,value,message in [('requests_used',3,'request cap'),('feature_units_charged',5,'measurement unit cap'),('additional_settles_used',5,'revision reservation')]:
            bad=dict(book);bad[field]=value;rejected(lambda b=bad:cell_caps(b,budget),message)
        global_caps(39,260,p);count+=1
        rejected(lambda:global_caps(40,260,p),'global measurement cap')
        rejected(lambda:global_caps(39,261,p),'global settle cap')
        assertion(stage_violations(0,127,128)==[],'normal stage')
        assertion(stage_violations(1,127,128)==['stage failure'],'failed stage still sized')
        assertion(stage_violations(1,128,128)==['stage failure','raw stage-end size'],'both failures retained')
        try:probe.handle_terminate(15,None)
        except TimeoutError:count+=1
        else:raise ValueError('termination not propagated')
        pub=next(c['public'] for c in p['cases'] if c['key']=='missing_aux_A');initial=dict(kernels=[dict(convergence=dict(status='stable_ambiguous'))])
        reqs=[(s,request_for(pub,initial,s,p)) for s in p['sources']]
        responses=[sensor.expected(pub,r,s,fixtures['missing_aux_A'][s],p) for s,r in reqs]
        gate,updated=adoption(pub,'corroborated',reqs,responses,p)
        assertion(gate['action']=='adopt' and updated['measurements']==[.98,.98],'feature agreement adopts primary without averaging')
        for mutation,reason in [('same_acquisition','same_acquisition'),('overlap','declared_root_overlap'),('weak','insufficient_strength'),('disagree','feature_disagreement'),('stale','contract:response revision')]:
            bad=deepcopy(responses)
            if mutation=='same_acquisition':bad[1]['acquisition_id']=bad[0]['acquisition_id']
            elif mutation=='overlap':bad[1]['root_measurement_ids']=bad[0]['root_measurement_ids']
            elif mutation=='weak':bad[1]['measurement']['observation']['edges'][0]['score']=.2
            elif mutation=='disagree':bad[1]['measurement']['observation']['edges'][0]['score']=-.98
            else:bad[1]['measurement']['observation']['revision']=0
            g,u=adoption(pub,'corroborated',reqs,bad,p);assertion(g['action']=='abstain' and g['reason']==reason and u is None,'adoption rejection '+mutation)
        def fake_execute(case,arm,base_spec):
            decided=any(case['measurements']);status='stable_decision' if decided else 'stable_ambiguous'
            low=dict(convergence=dict(status=status),state=dict(goal=.9 if sum(case['measurements'])>0 else .5),cost=Cost().snapshot())
            gate=probe.base.decide(case,low,base_spec)
            category=sum(case['measurements'])>0 if decided else (case['context']>0 if gate['action']=='feedback' else None)
            calls=1 if gate['action']=='abstain' else (4 if gate['action']=='feedback' else 2)
            return dict(category=category,relation=None if category is None else category==(case['context']>0),
                kernels=[dict(kind='lower_initial',**low)]+[dict(kind='stub',cost=Cost().snapshot()) for _ in range(calls-1)])
        probe.base.execute=fake_execute;requests=0;settles=0
        reasons={'primary_flipped_A':'feature_disagreement','witness_flipped_A':'feature_disagreement','declared_overlap_A':'declared_root_overlap',
            'stale_witness_A':'contract:response revision','no_information_A':'insufficient_strength','weak_witness_A':'insufficient_strength'}
        for cell in p['cases']:
            for arm in p['arms']:
                calls=[]
                def deliver(source,req):calls.append(source);return sensor.expected(cell['public'],req,source,fixtures[cell['key']][source],p)
                e=probe.execute(cell['public'],arm,p,deliver)
                assertion(e['provider_calls']==len(calls)==e['ledger']['requests_used']<=2,'callback counts')
                assertion(e['ledger']['feature_units_charged']==2*len(calls),'all attempted measurements charged')
                assertion(e['ledger']['additional_settles_used']<=e['ledger']['additional_settles_reserved']<=cell['public']['budget']['revision_settles'],'additional compute caps')
                if arm=='corroborated' and cell['key'] in reasons:assertion(e['adoption']['reason']==reasons[cell['key']] and e['revised'] is None,'gate case '+cell['key'])
                if arm=='corroborated' and cell['key']=='both_wrong_A':assertion(e['adoption']['action']=='adopt' and e['final']['category'] is False,'agreement cannot prove truth')
                if arm=='corroborated' and cell['key'] in ['request_budget_A','feature_budget_A']:assertion(not calls,'refuse before provider')
                if cell['key'] in ['clear_A','strong_primary_wrong_B']:assertion(not calls,'fixed request predicate preserves coverage limitation')
                requests+=len(calls);settles+=e['cost']['total']['native_settle_calls']
        global_caps(requests,settles,p);count+=1
    finally:dynamics.tick,dynamics.settle,World.measure,probe.base.execute=original
    return dict(status='PURE_PREPARATION_PASSED',assertions=count,stub_cells=39,new_native_settle_calls=0,new_world_measure_calls=0,
        saved_record_max_absolute_error=maximum,numeric_tolerance=tolerance,global_cap_rejection_functions_exercised=2,
        cell_cap_rejection_functions_exercised=3,notice='Stub cells/response formulas are preparation checks, not experimental observations.')


if __name__=='__main__':
    import json
    print(json.dumps(check(portable=True),sort_keys=True))
