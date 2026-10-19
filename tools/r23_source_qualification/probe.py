"""R23: separate labelled qualification, frozen held-out evaluation, total cost accounting."""
import argparse
from copy import deepcopy
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from hcr.codec import plain
from hcr.model import fingerprint
from tools.r22_measurement_adoption import probe as old,sensor
from tools.r22_measurement_adoption.policy import cell_caps,global_caps
from tools.r23_source_qualification.policy import require,validate_public,qualify,choose,request_for,adoption
base=old.base
read,put,sha,costs=old.read,old.put,old.sha,old.costs
SPEC=ROOT/'experiments/exp-69-source-qualification/frozen_spec.json'
def spec():return read(SPEC)

def calibration_request(public,source,p):
    return request_for(public,dict(calibration='known_feature_panel'),source,p)

def calibration_records(p,native):
    fixtures=read(SPEC.with_name('calibration-fixtures.json'));truth=read(SPEC.with_name('calibration-reference.json'));rows=[]
    for cell in p['calibration']:
        for source in p['sources']:
            request=calibration_request(cell['public'],source,p)
            response=(sensor.deliver if native else sensor.expected)(cell['public'],request,source,fixtures[cell['key']][source],p)
            rows.append(dict(key=cell['key'],source=source,public=cell['public'],request=request,response=response,
                known_feature_signs=truth[cell['key']]['feature_signs']))
    return rows

def calibration_saved(p,native):
    before=time.perf_counter();rows=calibration_records(p,native)
    certificate=qualify(rows,p)
    return dict(records=[dict(r,request=plain(r['request'])) for r in rows],certificate=certificate,
        requests=len(rows),feature_units=len(rows)*p['feature_units_per_request'],known_feature_labels=len(p['calibration'])*2,
        native_settle_calls=0,training_calls=0,wall_seconds=time.perf_counter()-before)

def verify_calibration(saved,p):
    expected=calibration_saved(p,False)
    for name in ['records','certificate','requests','feature_units','known_feature_labels','native_settle_calls','training_calls']:
        require(saved[name]==expected[name],'calibration '+name+' binding')
    require(saved['wall_seconds']>=0,'calibration wall')
    return expected['certificate']

def execute(public,arm,p,certificate,deliver):
    validate_public(public);initial=base.execute(public['observation'],'gated',p['base']);gate=choose(public,initial,arm,p,certificate)
    requests=[];responses=[];revised=None;accept=None;elapsed=0.
    final=dict(category=initial['category'],relation=initial['relation']);source='initial'
    if gate['action']=='request':
        for origin in gate['sources']:
            req=request_for(public,initial,origin,p);requests.append((origin,req));before=time.perf_counter()
            responses.append(deliver(origin,req));elapsed+=time.perf_counter()-before
        accept,updated=adoption(public,arm,requests,responses,p)
        if accept['action']=='adopt':
            revised=base.execute(updated,'gated',p['base']);final=dict(category=revised['category'],relation=revised['relation']);source='revised'
        else:final=dict(category=None,relation=None);source='unsupported_measurement_abstention'
    book=old.ledger(requests,revised,p);cell_caps(book,public['budget'])
    return dict(public=public,arm=arm,initial=initial,request_gate=gate,requests=[dict(source_id=s,request=plain(r)) for s,r in requests],responses=responses,
        adoption=accept,revised=revised,final=final,final_source=source,ledger=book,cost=costs(initial,revised),measurement_wall_seconds=elapsed,
        provider_calls=len(responses),training_calls=0,native_revision_controller=False)

def audit_execution(e,public,arm,p,certificate,fixtures,tolerance):
    require(e['public']==public and e['arm']==arm,'frozen public binding');cell_caps(e['ledger'],public['budget'])
    maximum=base.audit_execution(e['initial'],public['observation'],'gated',p['base'],tolerance)
    gate=choose(public,e['initial'],arm,p,certificate);require(e['request_gate']==gate,'request gate binding')
    requests=[(s,request_for(public,e['initial'],s,p)) for s in gate['sources']]
    require(e['requests']==[dict(source_id=s,request=plain(r)) for s,r in requests],'request binding')
    require(e['responses']==[sensor.expected(public,r,s,fixtures[s],p) for s,r in requests],'provider response binding')
    revised=None;accept=None;final=dict(category=e['initial']['category'],relation=e['initial']['relation']);source='initial'
    if requests:
        accept,updated=adoption(public,arm,requests,e['responses'],p)
        if accept['action']=='adopt':
            revised=e['revised'];require(revised is not None,'missing revised inference')
            maximum=max(maximum,base.audit_execution(revised,updated,'gated',p['base'],tolerance))
            final=dict(category=revised['category'],relation=revised['relation']);source='revised'
        else:require(e['revised'] is None,'rejected revised inference');final=dict(category=None,relation=None);source='unsupported_measurement_abstention'
    else:require(e['revised'] is None,'unrequested revision')
    require(e['adoption']==accept,'adoption binding');require(e['final']==final and e['final_source']==source,'final readout source')
    require(e['ledger']==old.ledger(requests,revised,p),'measurement charge ledger');require(e['cost']==costs(e['initial'],revised),'initial plus revised cost')
    require(e['provider_calls']==len(requests),'provider count');require(e['measurement_wall_seconds']>=0 and (requests or e['measurement_wall_seconds']==0),'provider timing')
    require(e['training_calls']==0 and not e['native_revision_controller'],'scope flags')
    return maximum

def audit(out):
    p=spec();saved=read(out/'calibration.json');certificate=verify_calibration(saved,p)
    truth=read(SPEC.with_name('reference.json'));fixtures=read(SPEC.with_name('sensor-fixtures.json'));rows=[];rejected={}
    for cell in p['cases']:
        for arm in p['arms']:
            key=cell['key'];path=out/(key+'__'+arm+'.json');e=read(path)
            maximum=audit_execution(e,cell['public'],arm,p,certificate,fixtures[key],p['numeric_replay_absolute_tolerance_server'])
            # Upper-trace mutations bypass unchanged lower-hash guard; each expected cause is checked.
            if (key,arm)==('eval_08','no_query'):
                for name in ['upper_tick','upper_program_bias']:
                    try:audit_execution(old.mutate(e,name),cell['public'],arm,p,certificate,fixtures[key],0.)
                    except ValueError as exc:require(str(exc)==old.MUTATIONS[name],'mutation cause');rejected[name]=str(exc)
                    else:raise ValueError('accepted mutation '+name)
            if (key,arm)==('eval_00','qualified_single'):
                for name in ['request_gate','request_revision','charge_units','response_score','adoption_action','request_cap','unit_cap','revision_cap']:
                    try:audit_execution(old.mutate(e,name),cell['public'],arm,p,certificate,fixtures[key],0.)
                    except ValueError as exc:require(str(exc)==old.MUTATIONS[name],'mutation cause '+str(exc));rejected[name]=str(exc)
                    else:raise ValueError('accepted mutation '+name)
            row=dict(key=key,arm=arm,final=e['final'],request_reason=e['request_gate']['reason'],sources=[r['source_id'] for r in e['requests']],
                requests=e['ledger']['requests_used'],feature_units=e['ledger']['feature_units_charged'],cost=e['cost'],measurement_wall_seconds=e['measurement_wall_seconds'],
                execution_bytes=path.stat().st_size,numeric_replay_max_absolute_error=maximum)
            for name in ['category','relation']:
                value=e['final'][name];row[name+'_correct']=value is not None and value==truth[key][name];row[name+'_wrong']=value is not None and value!=truth[key][name];row[name+'_abstained']=value is None
            rows.append(row)
    totals={}
    for arm in p['arms']:
        group=[r for r in rows if r['arm']==arm];totals[arm]={n:sum(r[n] for r in group) for n in ['requests','feature_units','category_correct','category_wrong','category_abstained','relation_correct','relation_wrong','relation_abstained','measurement_wall_seconds','execution_bytes']}
        totals[arm]['cost']={phase:{n:sum(r['cost'][phase][n] for r in group) for n in group[0]['cost'][phase]} for phase in ['initial','revision','total']}
        totals[arm]['calibration_requests_attributed']=saved['requests'] if arm=='qualified_single' else 0
        totals[arm]['calibration_feature_units_attributed']=saved['feature_units'] if arm=='qualified_single' else 0
        totals[arm]['requests_including_calibration']=totals[arm]['requests']+totals[arm]['calibration_requests_attributed']
        totals[arm]['feature_units_including_calibration']=totals[arm]['feature_units']+totals[arm]['calibration_feature_units_attributed']
    global_caps(saved['requests']+sum(t['requests'] for t in totals.values()),sum(t['cost']['total']['native_settle_calls'] for t in totals.values()),p)
    # This is an empirical promotion filter for this matrix, not a product tolerance or a general guarantee.
    baseline={r['key']:r for r in rows if r['arm']=='single_contract'};qualified=[r for r in rows if r['arm']=='qualified_single']
    new_wrongs=[r['key'] for r in qualified if r['category_wrong'] and baseline[r['key']]['category_correct']]
    require(len(rows)==40 and len(rejected)==10,'matrix and targeted mutations')
    put(out/'summary.json',dict(status='TECHNICAL_PROBE_REPLAYED',rows=rows,totals=totals,certificate=certificate,calibration_requests=saved['requests'],
        calibration_feature_units=saved['feature_units'],known_feature_labels=saved['known_feature_labels'],calibration_wall_seconds=saved['wall_seconds'],
        new_wrongs_on_single_correct_inputs=new_wrongs,individual_quality_preserved=not new_wrongs,targeted_rejections=rejected,training_calls=0,
        probability_calibration_established=False,stationarity_established=False,source_authenticated=False))

def run(started):
    # ponytail: reuse the existing bounded process/seal runner; only its spec and child entry point differ.
    old.spec=spec;old.__file__=__file__
    old.run(started)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--phase',required=True,choices=['run','preparation','case','audit']);parser.add_argument('--item',default='');parser.add_argument('--started',type=float);args=parser.parse_args();out=ROOT/'runs/technical'
    if args.phase=='run':run(args.started if args.started is not None else time.monotonic())
    elif args.phase=='preparation':
        from tools.r23_source_qualification.selfcheck import check
        result=check(portable=False)
        import resource
        p=spec();result['child_limits']=dict(address_space=resource.getrlimit(resource.RLIMIT_AS),file_size=resource.getrlimit(resource.RLIMIT_FSIZE))
        require(result['child_limits']['address_space']==(p['limits']['child_address_space_bytes'],)*2 and result['child_limits']['file_size']==(p['limits']['child_file_bytes'],)*2,'child resource limits')
        # Calibration is actual paid provider work after pure preparation, before held-out cases.
        put(out/'preparation.json',result);put(out/'calibration.json',calibration_saved(p,True))
    elif args.phase=='audit':audit(out)
    else:
        key,arm=args.item.split('__');p=spec();cell=next(c for c in p['cases'] if c['key']==key)
        certificate=verify_calibration(read(out/'calibration.json'),p)
        def deliver(source,request):
            fixture=read(SPEC.with_name('sensor-fixtures.json'))[key][source]
            return sensor.deliver(cell['public'],request,source,fixture,p)
        put(out/(args.item+'.json'),execute(cell['public'],arm,p,certificate,deliver))
