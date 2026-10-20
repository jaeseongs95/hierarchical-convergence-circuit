"""Fixed eight lower sources and twelve queries xthree arms; no training or retries."""
import argparse,json,time,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from hcr import codec
from tools.r19_cross_level.probe import read,put,sha
from tools.r32_semantic_join.verify import require,logic,audit_lower,audit_upper,collision_check,mutations,structural_check
SPEC=ROOT/'experiments/exp-78-semantic-join/frozen_spec.json';OUT=ROOT/'runs/technical'
def spec():return read(SPEC)
def inputs():
    p=spec();logic(p);require(all(sha(ROOT/n)==h for n,h in read(SPEC.with_name('input_manifest.json')).items()),'input source pins');return p
def source(key):
    from tools.r32_semantic_join.runtime import lower
    p=inputs();s=next(s for s in p['sources'] if s['key']==key);put(OUT/(key+'.json'),lower(s['observation'],s['predicate'],p['kernel']))
def case(item):
    from tools.r32_semantic_join.runtime import export,guard,execute
    key,arm=item.rsplit('__',1);p=inputs();c=next(c for c in p['cases'] if c['key']==key);require(arm in p['arms'],'arm')
    sources=[read(OUT/(n+'.json')) for n in c['source_keys']];packets=[export(s) for s in sources]
    for packet,s,predicate in zip(packets,sources,['R','S'],strict=True):guard(packet,s,predicate,c['query']['vocabulary'])
    # Only compact packets/query/config/Program cross this consumer boundary.
    r=execute(c['query'],packets,arm,p['kernel'],p['upper_program'])
    r['bridge_cost']=dict(source_records_loaded=2,source_serialized_bytes=sum(len(codec.dumps(s).encode()) for s in sources),origin_sha256_calls=4,packet_digest_calls=16,packet_validations=2,packet_serialized_bytes=sum(len(codec.dumps(f).encode()) for f in packets))
    put(OUT/(item+'.json'),r)
def audit_all():
    p=inputs();truth=read(SPEC.with_name('reference.json'));sources={s['key']:read(OUT/(s['key']+'.json')) for s in p['sources']};lower_rows=[audit_lower(sources[s['key']],s,p) for s in p['sources']]
    require(len({r['confidence'].hex() for r in lower_rows})==1,'same actual binary64 confidence across all role sources')
    records={};rows=[]
    for c in p['cases']:
        for arm in p['arms']:
            r=read(OUT/(c['key']+'__'+arm+'.json'));records[(c['key'],arm)]=r;rows.append(audit_upper(r,c,arm,p,sources,truth[c['key']]))
    groups=collision_check(records,p['cases']);require(any(len({truth[k] for k in g['cases']})==2 for g in groups),'role-erasure conflicting truth collision')
    c=p['cases'][0];rejected=mutations(records[(c['key'],'typed')],c,p,sources,truth[c['key']])
    ticks=sum(r['ticks'] for r in lower_rows)+sum(r['cost']['kernel_ticks'] for r in rows);require(ticks<=5120 and sum(r['upper_native_settles'] for r in rows)+8==32,'fixed native call/tick cap')
    put(OUT/'summary.json',dict(status='TECHNICAL_PROBE_AUDITED',lower=lower_rows,rows=rows,scalar_collision_groups=groups,targeted_rejections=rejected,
        native_settle_calls=32,kernel_ticks=ticks,lower_sources=8,upper_evaluations=36,training_calls=0,world_measure_calls=0,
        numeric_replay_max_absolute_error=max([r['numeric_replay_max_absolute_error'] for r in lower_rows+rows]),statistical_speed_verdict=None,production_adoption=False,native_adaptive_session=False,native_upper_primitive_route_proof=False))

def stage_violations(returncode,raw_bytes,limit):
    out=[]
    if returncode!=0:out.append('stage process failed')
    if raw_bytes>limit:out.append('raw byte cap')
    return out

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
        for s in p['sources']:stage('source',s['key'])
        for item in p['execution_order']:stage('case',item)
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
    a=argparse.ArgumentParser();a.add_argument('--phase',required=True,choices=['run','preparation','source','case','audit']);a.add_argument('--item',default='');a.add_argument('--started',type=float);args=a.parse_args()
    from hcr.tasks.toy_world import World
    def forbidden(*a,**k):raise ValueError('R32 world measurement forbidden')
    World.measure=forbidden
    if args.phase=='run':run(args.started if args.started is not None else time.monotonic())
    elif args.phase=='source':source(args.item)
    elif args.phase=='case':case(args.item)
    elif args.phase=='audit':audit_all()
    else:
        import resource
        p=inputs();r=structural_check(p);r['child_limits']=dict(address_space=resource.getrlimit(resource.RLIMIT_AS),file_size=resource.getrlimit(resource.RLIMIT_FSIZE))
        require(r['child_limits']['address_space']==(p['limits']['child_address_space_bytes'],)*2 and r['child_limits']['file_size']==(p['limits']['child_file_bytes'],)*2,'child resource limits');put(OUT/'preparation.json',r)
