"""Pure preparation and counterexamples. Stub results are not experimental data."""
from copy import deepcopy
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from hcr import dynamics
from hcr.model import Cost
from hcr.tasks.toy_world import World
from tools.r23_source_qualification import probe
from tools.r23_source_qualification.policy import choose,qualify,require
from tools.r22_measurement_adoption.policy import global_caps,stage_violations,cell_caps

def check(portable):
    p=probe.spec();count=0
    def assertion(ok,message):
        nonlocal count
        require(ok,message);count+=1
    def rejects(call,message):
        try:call()
        except ValueError as exc:assertion(str(exc)==message,'expected '+message+', observed '+str(exc))
        else:raise ValueError('guard not exercised '+message)
    assertion(len(p['cases'])==10 and len(p['calibration'])==8 and len(p['arms'])==4,'matrix')
    calids={c['public']['observation']['id'] for c in p['calibration']};evalids={c['public']['observation']['id'] for c in p['cases']}
    assertion(calids.isdisjoint(evalids) and len(calids)==8 and len(evalids)==10,'calibration evaluation identity separation')
    fixtures=probe.read(probe.SPEC.with_name('sensor-fixtures.json'))
    original=(dynamics.tick,dynamics.settle,World.measure,probe.base.execute)
    def forbidden(*args,**kwargs):raise AssertionError('new native work during preparation')
    dynamics.tick=dynamics.settle=World.measure=forbidden
    maximum=0.
    try:
        saved=probe.calibration_saved(p,False);certificate=probe.verify_calibration(saved,p)
        assertion(saved['requests']==16 and saved['feature_units']==32 and saved['known_feature_labels']==16,'calibration accounting')
        assertion([s['passed'] for s in certificate['sources']]==[6,8],'qualification known-feature comparison')
        assertion([s['qualified'] for s in certificate['sources']]==[False,True],'qualification zero failures rule')
        # Saved native evidence only; scalar recurrence does not invoke new ticks/settles.
        golden=probe.read(ROOT/'experiments/exp-68-measurement-adoption/fixture.json')
        for e in golden.values():
            maximum=max(maximum,probe.base.audit_execution(e,e['public'],'gated',p['base'],1e-15 if portable else 0.))
            assertion(maximum<=(1e-15 if portable else 0.),'saved recurrence')
        for field,expected in [('certificate','calibration certificate binding'),('requests','calibration requests binding'),('feature_units','calibration feature_units binding'),('records','calibration records binding')]:
            bad=deepcopy(saved)
            if field=='certificate':bad[field]['sources'][0]['qualified']=True
            elif field=='records':bad[field][0]['response']['measurement']['observation']['edges'][0]['score']=-.98
            else:bad[field]+=1
            rejects(lambda b=bad:probe.verify_calibration(b,p),expected)
        pub=p['cases'][0]['public'];initial=dict(kernels=[dict(convergence=dict(status='stable_ambiguous'))])
        gate=choose(pub,initial,'qualified_single',p,certificate)
        assertion(gate['sources']==[p['sources'][1]],'qualified source selected before querying')
        empty=deepcopy(certificate)
        for source in empty['sources']:source.update(passed=0,failures=8,qualified=False)
        assertion(choose(pub,initial,'qualified_single',p,empty)['reason']=='no_qualified_source','no certificate pass refuses before provider')
        forged=deepcopy(certificate);forged['sources'][0]['qualified']=True
        rejects(lambda:choose(pub,initial,'qualified_single',p,forged),'qualification decision')
        forged=deepcopy(certificate);forged['rule_sha256']='0'*64
        rejects(lambda:choose(pub,initial,'qualified_single',p,forged),'qualification rule binding')
        rejects(lambda:qualify(probe.calibration_records(p,False)[:-1],p),'calibration record count')
        duplicate=probe.calibration_records(p,False);duplicate[-1]=duplicate[0]
        rejects(lambda:qualify(duplicate,p),'calibration matrix')
        book=dict(requests_used=2,feature_units_charged=4,additional_settles_reserved=4,additional_settles_used=2,reservation_released=2)
        for field,value,reason in [('requests_used',3,'request cap'),('feature_units_charged',5,'measurement unit cap'),('additional_settles_used',5,'revision reservation')]:
            bad=dict(book);bad[field]=value;rejects(lambda b=bad:cell_caps(b,pub['budget']),reason)
        global_caps(64,240,p);count+=1
        rejects(lambda:global_caps(65,240,p),'global measurement cap');rejects(lambda:global_caps(64,241,p),'global settle cap')
        assertion(stage_violations(1,128,128)==['stage failure','raw stage-end size'],'failed stage sizes retained')
        def fake_execute(case,arm,base_spec):
            decided=any(case['measurements']);category=sum(case['measurements'])>0 if decided else None
            low=dict(convergence=dict(status='stable_decision' if decided else 'stable_ambiguous'),cost=Cost().snapshot())
            return dict(category=category,relation=None if category is None else category==(case['context']>0),kernels=[dict(kind='lower_initial',**low)]+([dict(kind='upper_initial',cost=Cost().snapshot())] if decided else []))
        probe.base.execute=fake_execute;requests=16;settles=0
        for cell in p['cases']:
            for arm in p['arms']:
                called=[]
                def deliver(source,request):
                    called.append(source);return probe.sensor.expected(cell['public'],request,source,fixtures[cell['key']][source],p)
                e=probe.execute(cell['public'],arm,p,certificate,deliver)
                assertion(len(called)==e['provider_calls']==e['ledger']['requests_used'],'provider charge count')
                assertion(e['ledger']['feature_units_charged']==2*len(called),'charge attempted measurements')
                assertion(e['ledger']['additional_settles_used']<=e['ledger']['additional_settles_reserved']<=4,'revision bounds')
                if arm=='qualified_single' and called:assertion(called==[p['sources'][1]],'one qualified source only')
                if cell['key'] in ['eval_08','eval_09']:assertion(not called,'fixed trigger misses stable wrong')
                if (cell['key'],arm)==('eval_07','corroborated'):assertion(not called,'dual budget refused before callback')
                requests+=len(called);settles+=e['cost']['total']['native_settle_calls']
        global_caps(requests,settles,p);count+=1
    finally:dynamics.tick,dynamics.settle,World.measure,probe.base.execute=original
    return dict(status='PURE_PREPARATION_PASSED',assertions=count,stub_cells=40,new_native_settle_calls=0,new_world_measure_calls=0,
        saved_record_max_absolute_error=maximum,numeric_tolerance=1e-15 if portable else 0.,notice='Stub and expected provider records are preparation checks only.')

if __name__=='__main__':
    import json
    print(json.dumps(check(portable=True),sort_keys=True))
