"""Bounded one-shot active measurement around the unchanged R20 inference policy."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from hcr.codec import plain
from hcr.model import fingerprint
from tools.r20_evidence_feedback import probe as base
from tools.r21_active_measurement.policy import choose,request_for,accept_response,require,validate_public
from tools.r21_active_measurement import sensor

SPEC=ROOT/'experiments/exp-67-active-measurement/frozen_spec.json'
read,put,sha=base.read,base.put,base.sha
def spec():return read(SPEC)


def costs(initial,revised):
    names=['kernel_ticks','group_updates','signal_transmissions','normalization_ops']
    phases=[]
    for phase in [initial,revised]:
        kernels=[] if phase is None else phase['kernels']
        phases.append(dict({name:sum(k['cost'][name] for k in kernels) for name in names},native_settle_calls=len(kernels)))
    return dict(initial=phases[0],revision=phases[1],total={name:phases[0][name]+phases[1][name] for name in phases[0]})


def ledger(request,revised,p):
    charged=request is not None;used=0 if revised is None else len(revised['kernels'])
    reserved=p['request_quote']['revision_settle_reservation'] if charged else 0
    return dict(requests_used=int(charged),feature_units_charged=p['request_quote']['feature_units'] if charged else 0,
        additional_settles_reserved=reserved,additional_settles_used=used,reservation_released=reserved-used)


def execute(public,arm,p,deliver):
    validate_public(public)
    initial=base.execute(public['observation'],'gated',p['base']);gate=choose(public,initial,arm,p)
    request=None;response=None;revised=None;error=None;changed=None;measurement_wall=0.0;provider_calls=0
    final=dict(category=initial['category'],relation=initial['relation']);source='initial'
    if gate['action']=='request':
        request=request_for(public,initial,arm,p);before=time.perf_counter();provider_calls+=1
        response=deliver(request);measurement_wall=time.perf_counter()-before
        try:updated=accept_response(public,request,response,p)
        except ValueError as exc:
            error=str(exc);final=dict(category=None,relation=None);source='invalid_response_abstention'
        else:
            changed=updated['measurements']!=public['observation']['measurements']
            revised=base.execute(updated,'gated',p['base'])
            final=dict(category=revised['category'],relation=revised['relation']);source='revised'
    book=ledger(request,revised,p)
    require(book['additional_settles_used']<=book['additional_settles_reserved'],'revision compute reservation exceeded')
    return dict(public=public,arm=arm,initial=initial,request_gate=gate,request=None if request is None else plain(request),
        response=response,response_error=error,measurement_changed=changed,revised=revised,final=final,final_source=source,
        measurement_wall_seconds=measurement_wall,provider_calls=provider_calls,ledger=book,cost=costs(initial,revised),
        training_calls=0,native_revision_controller=False,native_measurement_contract=True)


def audit_execution(e,public,arm,p,fixture,tolerance):
    require(e['public']==public and e['arm']==arm,'frozen public binding')
    maximum=base.audit_execution(e['initial'],public['observation'],'gated',p['base'],tolerance)
    gate=choose(public,e['initial'],arm,p);require(e['request_gate']==gate,'request gate binding')
    request=None;revised=None;error=None;changed=None
    final=dict(category=e['initial']['category'],relation=e['initial']['relation']);source='initial'
    if gate['action']=='request':
        request=request_for(public,e['initial'],arm,p)
        require(e['request']==plain(request),'request binding')
        require(e['response']==sensor.expected(public,request,fixture,p),'provider response binding')
        try:updated=accept_response(public,request,e['response'],p)
        except ValueError as exc:
            error=str(exc);final=dict(category=None,relation=None);source='invalid_response_abstention'
            require(e['revised'] is None,'invalid response cannot run revised inference')
        else:
            revised=e['revised'];require(revised is not None,'missing revised inference')
            maximum=max(maximum,base.audit_execution(revised,updated,'gated',p['base'],tolerance))
            changed=updated['measurements']!=public['observation']['measurements']
            final=dict(category=revised['category'],relation=revised['relation']);source='revised'
    else:require(e['request'] is None and e['response'] is None and e['revised'] is None,'unrequested provider access')
    require(e['response_error']==error and e['measurement_changed']==changed,'response validation status')
    require(e['final']==final and e['final_source']==source,'final readout source')
    require(e['ledger']==ledger(request,revised,p),'measurement charge ledger')
    book=e['ledger'];budget=public['budget'];quote=p['request_quote']
    require(book['requests_used']<=budget['requests'] and book['requests_used']<=1,'request cap')
    require(book['feature_units_charged']<=budget['feature_units'],'measurement unit cap')
    require(book['additional_settles_used']<=book['additional_settles_reserved']<=budget['revision_settles'],'revision reservation')
    require(e['provider_calls']==int(request is not None),'actual provider call count')
    require(e['measurement_wall_seconds']>=0 and (request is not None or e['measurement_wall_seconds']==0),'provider timing')
    require(e['cost']==costs(e['initial'],revised),'initial plus revised cost')
    require(e['training_calls']==0 and not e['native_revision_controller'] and e['native_measurement_contract'],'scope flags')
    return maximum


def audit(out):
    p=spec();truth=read(SPEC.with_name('reference.json'));fixtures=read(SPEC.with_name('sensor-fixtures.json'));rows=[];rejected={}
    mutations={('missing_aux_A','primary_uncertainty'):[('request_gate','request gate binding'),('request_revision','request binding'),
        ('charge_units','measurement charge ledger'),('response_score','provider response binding')],
        ('clear_A','no_query'):[('upper_tick','scalar replay tick mismatch'),('upper_program_bias','fixed program')]}
    for cell in p['cases']:
        key,public=cell['key'],cell['public']
        for arm in p['arms']:
            path=out/(key+'__'+arm+'.json');e=read(path)
            maximum=audit_execution(e,public,arm,p,fixtures[key],p['numeric_replay_absolute_tolerance_server'])
            for mutation,expected in mutations.get((key,arm),[]):
                bad=deepcopy(e)
                if mutation=='request_gate':bad['request_gate']['action']='retain'
                elif mutation=='request_revision':bad['request']['revision']+=1
                elif mutation=='charge_units':bad['ledger']['feature_units_charged']=0
                elif mutation=='response_score':bad['response']['observation']['edges'][0]['score']-=.01
                elif mutation=='upper_tick':bad['initial']['kernels'][1]['ticks'][0]['state']['goal']+=.01
                else:bad['initial']['kernels'][1]['program']['groups'][0]['bias']+=.1
                try:audit_execution(bad,public,arm,p,fixtures[key],p['numeric_replay_absolute_tolerance_server'])
                except ValueError as exc:
                    require(str(exc)==expected,'unexpected mutation rejection: '+str(exc));rejected[mutation]=str(exc)
                else:raise ValueError('mutation accepted '+mutation)
            row=dict(key=key,arm=arm,category=e['final']['category'],relation=e['final']['relation'],
                initial_category=e['initial']['category'],initial_primary_status=e['initial']['kernels'][0]['convergence']['status'],
                request_reason=e['request_gate']['reason'],response_error=e['response_error'],measurement_changed=e['measurement_changed'],
                final_source=e['final_source'],requests=e['ledger']['requests_used'],feature_units=e['ledger']['feature_units_charged'],
                additional_settles_reserved=e['ledger']['additional_settles_reserved'],additional_settles_used=e['ledger']['additional_settles_used'],
                cost=e['cost'],measurement_wall_seconds=e['measurement_wall_seconds'],execution_bytes=path.stat().st_size,
                numeric_replay_max_absolute_error=maximum)
            for name in ['category','relation']:
                value=e['final'][name];row[name+'_correct']=value is not None and value==truth[key][name]
                row[name+'_wrong']=value is not None and value!=truth[key][name];row[name+'_abstained']=value is None
            rows.append(row)
    require(len(rows)==30 and len(rejected)==6,'frozen matrix and targeted mutations')
    totals={}
    for arm in p['arms']:
        group=[row for row in rows if row['arm']==arm]
        totals[arm]={name:sum(row[name] for row in group) for name in ['requests','feature_units','additional_settles_used',
            'category_correct','category_wrong','category_abstained','relation_correct','relation_wrong','relation_abstained','measurement_wall_seconds','execution_bytes']}
        totals[arm]['cost']={phase:{name:sum(row['cost'][phase][name] for row in group) for name in group[0]['cost'][phase]} for phase in ['initial','revision','total']}
    require(sum(t['requests'] for t in totals.values())<=p['maximum_measurement_requests'],'global measurement cap')
    require(sum(t['cost']['total']['native_settle_calls'] for t in totals.values())<=p['maximum_native_settle_calls'],'global settle cap')
    put(out/'summary.json',dict(status='TECHNICAL_PROBE_REPLAYED',rows=rows,totals=totals,targeted_rejections=rejected,
        numeric_replay_absolute_tolerance=p['numeric_replay_absolute_tolerance_server'],training_calls=0,
        synthetic_measurement_provider=True,physical_sensor_reliability_established=False,memory_correction_retention=False))


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
            except BaseException:child.kill();child.wait();raise
        after=resource.getrusage(resource.RUSAGE_CHILDREN)
        stages.append(dict(phase=phase,item=item,returncode=rc,wall_seconds=time.monotonic()-before,
            child_cpu_seconds=after.ru_utime+after.ru_stime-usage.ru_utime-usage.ru_stime))
        require(rc==0,'stage failure '+phase+' '+item)
        require(sum(f.stat().st_size for f in out.rglob('*') if f.is_file())<limits['raw_bytes'],'raw stage-end size')
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
            python_version=sys.version.split()[0],platform=sys.platform,total_wall_limit_seconds=limits['total_seconds'],automatic_retry=False))
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
        from tools.r21_active_measurement.selfcheck import check
        put(out/'preparation.json',check(portable=False))
    elif args.phase=='audit':audit(out)
    else:
        key,arm=args.item.split('__');p=spec();cell=next(c for c in p['cases'] if c['key']==key)
        def deliver(request):
            fixture=read(SPEC.with_name('sensor-fixtures.json'))[key]
            return sensor.deliver(cell['public'],request,fixture,p)
        put(out/(args.item+'.json'),execute(cell['public'],arm,p,deliver))
