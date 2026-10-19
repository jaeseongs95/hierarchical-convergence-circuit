"""Fixed R22 adoption comparison using unchanged R20 kernels and R21 measurement helpers."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from hcr.codec import plain
from tools.r21_active_measurement import probe as old
from tools.r22_measurement_adoption import sensor
from tools.r22_measurement_adoption.policy import (require,validate_public,choose,request_for,adoption,cell_caps,global_caps,stage_violations)

base=old.base
read,put,sha,costs=old.read,old.put,old.sha,old.costs
SPEC=ROOT/'experiments/exp-68-measurement-adoption/frozen_spec.json'
def spec():return read(SPEC)


def ledger(requests,revised,p):
    used=0 if revised is None else len(revised['kernels']);count=len(requests)
    reserved=p['revision_settle_reservation'] if count else 0
    return dict(requests_used=count,feature_units_charged=count*p['feature_units_per_request'],
        additional_settles_reserved=reserved,additional_settles_used=used,reservation_released=reserved-used)


def execute(public,arm,p,deliver):
    validate_public(public);initial=base.execute(public['observation'],'gated',p['base']);gate=choose(public,initial,arm,p)
    requests=[];responses=[];revised=None;accept=None;elapsed=0.
    final=dict(category=initial['category'],relation=initial['relation']);source='initial'
    if gate['action']=='request':
        for origin in gate['sources']:
            req=request_for(public,initial,origin,p);requests.append((origin,req))
            before=time.perf_counter();responses.append(deliver(origin,req));elapsed+=time.perf_counter()-before
        accept,updated=adoption(public,arm,requests,responses,p)
        if accept['action']=='adopt':
            revised=base.execute(updated,'gated',p['base']);final=dict(category=revised['category'],relation=revised['relation']);source='revised'
        else:final=dict(category=None,relation=None);source='unsupported_measurement_abstention'
    book=ledger(requests,revised,p);cell_caps(book,public['budget'])
    return dict(public=public,arm=arm,initial=initial,request_gate=gate,requests=[dict(source_id=s,request=plain(r)) for s,r in requests],
        responses=responses,adoption=accept,revised=revised,final=final,final_source=source,ledger=book,cost=costs(initial,revised),
        measurement_wall_seconds=elapsed,provider_calls=len(responses),training_calls=0,native_revision_controller=False)


def audit_execution(e,public,arm,p,fixtures,tolerance):
    require(e['public']==public and e['arm']==arm,'frozen public binding');cell_caps(e['ledger'],public['budget'])
    maximum=base.audit_execution(e['initial'],public['observation'],'gated',p['base'],tolerance)
    gate=choose(public,e['initial'],arm,p);require(e['request_gate']==gate,'request gate binding')
    requests=[(s,request_for(public,e['initial'],s,p)) for s in gate['sources']]
    require(e['requests']==[dict(source_id=s,request=plain(r)) for s,r in requests],'request binding')
    expected=[sensor.expected(public,r,s,fixtures[s],p) for s,r in requests]
    require(e['responses']==expected,'provider response binding')
    revised=None;accept=None;final=dict(category=e['initial']['category'],relation=e['initial']['relation']);source='initial'
    if requests:
        accept,updated=adoption(public,arm,requests,e['responses'],p)
        if accept['action']=='adopt':
            revised=e['revised'];require(revised is not None,'missing revised inference')
            maximum=max(maximum,base.audit_execution(revised,updated,'gated',p['base'],tolerance))
            final=dict(category=revised['category'],relation=revised['relation']);source='revised'
        else:require(e['revised'] is None,'rejected response cannot run revised inference');final=dict(category=None,relation=None);source='unsupported_measurement_abstention'
    else:require(e['revised'] is None,'unrequested revision')
    require(e['adoption']==accept,'adoption binding')
    require(e['final']==final and e['final_source']==source,'final readout source')
    require(e['ledger']==ledger(requests,revised,p),'measurement charge ledger')
    require(e['cost']==costs(e['initial'],revised),'initial plus revised cost')
    require(e['provider_calls']==len(requests),'provider count')
    require(e['measurement_wall_seconds']>=0 and (requests or e['measurement_wall_seconds']==0),'provider timing')
    require(e['training_calls']==0 and not e['native_revision_controller'],'scope flags')
    return maximum


MUTATIONS={'request_gate':'request gate binding','request_revision':'request binding','charge_units':'measurement charge ledger',
    'response_score':'provider response binding','adoption_action':'adoption binding','request_cap':'request cap',
    'unit_cap':'measurement unit cap','revision_cap':'revision reservation','upper_tick':'scalar replay tick mismatch','upper_program_bias':'fixed program'}
def mutate(e,name):
    bad=deepcopy(e)
    if name=='request_gate':bad['request_gate']['action']='retain'
    elif name=='request_revision':bad['requests'][0]['request']['revision']+=1
    elif name=='charge_units':bad['ledger']['feature_units_charged']=0
    elif name=='response_score':bad['responses'][0]['measurement']['observation']['edges'][0]['score']-=.01
    elif name=='adoption_action':bad['adoption']['action']='abstain'
    elif name=='request_cap':bad['ledger']['requests_used']=3
    elif name=='unit_cap':bad['ledger']['feature_units_charged']=5
    elif name=='revision_cap':bad['ledger']['additional_settles_used']=5
    elif name=='upper_tick':bad['initial']['kernels'][1]['ticks'][0]['state']['goal']+=.01
    else:bad['initial']['kernels'][1]['program']['groups'][0]['bias']+=.1
    return bad


def audit(out):
    p=spec();truth=read(SPEC.with_name('reference.json'));fixtures=read(SPEC.with_name('sensor-fixtures.json'));rows=[];rejected={}
    for cell in p['cases']:
        key,public=cell['key'],cell['public']
        for arm in p['arms']:
            path=out/(key+'__'+arm+'.json');e=read(path)
            maximum=audit_execution(e,public,arm,p,fixtures[key],p['numeric_replay_absolute_tolerance_server'])
            for name,expected in MUTATIONS.items():
                target=('clear_A','no_query') if name.startswith('upper_') else ('missing_aux_A','corroborated')
                if (key,arm)!=target:continue
                try:audit_execution(mutate(e,name),public,arm,p,fixtures[key],p['numeric_replay_absolute_tolerance_server'])
                except ValueError as exc:require(str(exc)==expected,'mutation rejection cause '+str(exc));rejected[name]=str(exc)
                else:raise ValueError('mutation accepted '+name)
            row=dict(key=key,arm=arm,category=e['final']['category'],relation=e['final']['relation'],initial_category=e['initial']['category'],
                request_reason=e['request_gate']['reason'],adoption_reason=None if e['adoption'] is None else e['adoption']['reason'],
                final_source=e['final_source'],requests=e['ledger']['requests_used'],feature_units=e['ledger']['feature_units_charged'],
                additional_settles_reserved=e['ledger']['additional_settles_reserved'],additional_settles_used=e['ledger']['additional_settles_used'],
                cost=e['cost'],measurement_wall_seconds=e['measurement_wall_seconds'],execution_bytes=path.stat().st_size,
                numeric_replay_max_absolute_error=maximum)
            for name in ['category','relation']:
                v=e['final'][name];row[name+'_correct']=v is not None and v==truth[key][name];row[name+'_wrong']=v is not None and v!=truth[key][name];row[name+'_abstained']=v is None
            rows.append(row)
    require(len(rows)==39 and len(rejected)==10,'frozen matrix and mutations')
    totals={}
    for arm in p['arms']:
        group=[r for r in rows if r['arm']==arm]
        totals[arm]={n:sum(r[n] for r in group) for n in ['requests','feature_units','additional_settles_used','category_correct','category_wrong','category_abstained',
            'relation_correct','relation_wrong','relation_abstained','measurement_wall_seconds','execution_bytes']}
        totals[arm]['cost']={phase:{n:sum(r['cost'][phase][n] for r in group) for n in group[0]['cost'][phase]} for phase in ['initial','revision','total']}
    global_caps(sum(t['requests'] for t in totals.values()),sum(t['cost']['total']['native_settle_calls'] for t in totals.values()),p)
    put(out/'summary.json',dict(status='TECHNICAL_PROBE_REPLAYED',rows=rows,totals=totals,targeted_rejections=rejected,
        numeric_replay_absolute_tolerance=p['numeric_replay_absolute_tolerance_server'],training_calls=0,synthetic_measurement_provider=True,
        physical_sensor_reliability_established=False,declared_provenance_proves_independence=False))
def handle_terminate(signum,frame):raise TimeoutError('termination signal '+str(signum))


def run(started):
    import resource
    import signal
    import subprocess
    import traceback
    import zipfile
    p=spec();limits=p['limits'];out=ROOT/'runs/technical';out.mkdir(parents=True,exist_ok=False)
    require(0<limits['total_seconds']<=600 and 0<limits['stage_seconds']<=60,'time caps')
    signal.signal(signal.SIGTERM,handle_terminate)
    parent_limits=dict(address_space=resource.getrlimit(resource.RLIMIT_AS),file_size=resource.getrlimit(resource.RLIMIT_FSIZE));
    require(parent_limits['address_space']==(limits['parent_address_space_bytes'],)*2 and parent_limits['file_size']==(limits['parent_file_bytes'],)*2,'parent resource limits');
    stages=[];failure=None;deadline=started+limits['total_seconds']-20;manifest=read(ROOT/'source_manifest.json')
    def source_check():return {name:(ROOT/name).is_file() and sha(ROOT/name)==digest for name,digest in manifest.items()}
    def stage(phase,item=''):
        require(deadline-time.monotonic()>30,'budget reserve')
        before=time.monotonic();usage=resource.getrusage(resource.RUSAGE_CHILDREN)
        def limit():
            resource.setrlimit(resource.RLIMIT_AS,(limits['child_address_space_bytes'],limits['child_address_space_bytes']))
            resource.setrlimit(resource.RLIMIT_FSIZE,(limits['child_file_bytes'],limits['child_file_bytes']))
        with (out/(phase+'-'+item+'.stdout')).open('xb') as stdout,(out/(phase+'-'+item+'.stderr')).open('xb') as stderr:
            child=subprocess.Popen([sys.executable,'-B',str(Path(__file__)),'--phase',phase,'--item',item],stdout=stdout,stderr=stderr,preexec_fn=limit)
            try:rc=child.wait(timeout=min(limits['stage_seconds'],deadline-time.monotonic()-20))
            except BaseException:
                child.kill();child.wait()
                raw_bytes=sum(f.stat().st_size for f in out.rglob('*') if f.is_file())
                stages.append(dict(phase=phase,item=item,returncode=child.returncode,terminated=True,raw_bytes=raw_bytes,
                    violations=stage_violations(child.returncode,raw_bytes,limits['raw_bytes'])))
                raise
        after=resource.getrusage(resource.RUSAGE_CHILDREN)
        raw_bytes=sum(f.stat().st_size for f in out.rglob('*') if f.is_file())
        stages.append(dict(phase=phase,item=item,returncode=rc,raw_bytes=raw_bytes,wall_seconds=time.monotonic()-before,
            child_cpu_seconds=after.ru_utime+after.ru_stime-usage.ru_utime-usage.ru_stime))
        violations=stage_violations(rc,raw_bytes,limits['raw_bytes'])
        require(not violations,'; '.join(violations)+' '+phase+' '+item)
    try:
        require(all(source_check().values()),'source preflight');stage('preparation')
        for cell in p['cases']:
            for arm in p['arms']:stage('case',cell['key']+'__'+arm)
        stage('audit')
    except BaseException:failure=traceback.format_exc()
    finally:
        post=source_check();put(out/'source-postcheck.json',dict(unchanged=all(post.values()),files=post))
        if not all(post.values()):failure=(failure or '')+'\nsource postcheck failed'
        if failure:put(out/'failure.json',dict(traceback=failure,stages=stages,automatic_retry=False))
        put(out/'result.json',dict(status='FAILED' if failure else 'COMPLETED',stages=stages,source_unchanged=all(post.values()),
            source_manifest_sha256=sha(ROOT/'source_manifest.json'),seconds_before_seal=time.monotonic()-started,
            python_version=sys.version.split()[0],platform=sys.platform,parent_limits=parent_limits,total_wall_limit_seconds=limits['total_seconds'],automatic_retry=False))
        put(out/'manifest.json',{f.relative_to(out).as_posix():sha(f) for f in sorted(out.rglob('*')) if f.is_file()})
        with zipfile.ZipFile(ROOT/'evidence.zip','x',compression=zipfile.ZIP_DEFLATED) as z:
            for f in sorted(out.rglob('*')):
                if f.is_file():z.write(f,'technical/'+f.relative_to(out).as_posix())
        put(ROOT/'completion.json',dict(completed=failure is None,seconds_including_seal=time.monotonic()-started,
            within_600_seconds=time.monotonic()-started<limits['total_seconds'],evidence_sha256=sha(ROOT/'evidence.zip'),evidence_bytes=(ROOT/'evidence.zip').stat().st_size))
    if failure:raise SystemExit(1)


if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--phase',required=True,choices=['run','preparation','case','audit']);a.add_argument('--item',default='');a.add_argument('--started',type=float);args=a.parse_args();out=ROOT/'runs/technical'
    if args.phase=='run':run(args.started if args.started is not None else time.monotonic())
    elif args.phase=='preparation':
        from tools.r22_measurement_adoption.selfcheck import check
        result=check(portable=False)
        import resource
        p=spec();result['child_limits']=dict(address_space=resource.getrlimit(resource.RLIMIT_AS),file_size=resource.getrlimit(resource.RLIMIT_FSIZE))
        require(result['child_limits']['address_space']==(p['limits']['child_address_space_bytes'],)*2 and result['child_limits']['file_size']==(p['limits']['child_file_bytes'],)*2,'child resource limits')
        put(out/'preparation.json',result)
    elif args.phase=='audit':audit(out)
    else:
        key,arm=args.item.split('__');p=spec();cell=next(c for c in p['cases'] if c['key']==key)
        def deliver(source,request):
            fixture=read(SPEC.with_name('sensor-fixtures.json'))[key][source]
            return sensor.deliver(cell['public'],request,source,fixture,p)
        put(out/(args.item+'.json'),execute(cell['public'],arm,p,deliver))
