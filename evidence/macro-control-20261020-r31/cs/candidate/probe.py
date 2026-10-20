"""Fixed3 training then12 evaluation stages; same-experience control, no adaptive tuning."""
import argparse,json,time,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from hcr import codec
from hcr.circuits import AdaptiveMemory
from tools.r19_cross_level.probe import read,put,sha
from tools.r31_macro_control.verify import require,audit,mutations
SPEC=ROOT/'experiments/exp-77-macro-control/frozen_spec.json'
OUT=ROOT/'runs/technical'
def spec():return read(SPEC)
def inputs():
    p=spec();old=read(ROOT/'experiments/exp-64-pre-reuse-gate/frozen_spec.json')
    require(p['config']==old['config'] and p['training']==old['training'] and [c['observation'] for c in p['cases']]==[c['observation'] for c in old['cases']],'R18 fixed source inputs')
    require(all(sha(ROOT/n)==h for n,h in read(SPEC.with_name('input_manifest.json')).items()),'source inputs');return p
def emit_record(path,r,engine):
    r.update(records=engine.trace.records,event_count=engine.trace.count,event_head=engine.trace.head);put(path,r)
def init():
    p=inputs();m=AdaptiveMemory.empty(codec.adaptive_config_from(p['config']));put(OUT/'memory0.json',m.document())
def train(index):
    from tools.r31_macro_control.runtime import infer,learn
    p=inputs();public=p['training'][index]['observation'];r,e=infer(public,read(OUT/f'memory{index}.json'),p,'hcr',True)
    # Reference file is opened only after the native decision has finished.
    truth=read(SPEC.with_name('reference.json'))['training'][str(index)];learn(r,e,truth,index)
    emit_record(OUT/f'train{index}.json',r,e);put(OUT/f'memory{index+1}.json',e.memory.document())
def case(item):
    from tools.r31_macro_control.runtime import infer
    key,arm=item.rsplit('__',1);p=inputs();c=next(c for c in p['cases'] if c['key']==key)
    require(arm in p['arms'],'arm');m=read(OUT/('memory0.json' if arm=='primitive' else 'memory3.json'))
    r,e=infer(c['observation'],m,p,arm);emit_record(OUT/(item+'.json'),r,e)
def audit_all():
    p=inputs();truth=read(SPEC.with_name('reference.json'));memory=read(OUT/'memory0.json');training=[]
    require(memory==AdaptiveMemory.empty(codec.adaptive_config_from(p['config'])).document(),'empty initial memory')
    for i,c in enumerate(p['training']):
        r=read(OUT/f'train{i}.json');training.append(audit(r,c['observation'],memory,p,'hcr',truth['training'][str(i)],True));memory=r['memory_after_learning'];require(memory==read(OUT/f'memory{i+1}.json'),'persisted learned memory')
    require(len(memory['circuits'])==1 and len(memory['circuits'][0]['evidence_episodes'])==3,'actual three-episode circuit formation')
    rows=[]
    for c in p['cases']:
        for arm in p['arms']:
            m=read(OUT/'memory0.json') if arm=='primitive' else memory;r=read(OUT/(c['key']+'__'+arm+'.json'))
            rows.append(dict(key=c['key'],**audit(r,c['observation'],m,p,arm,truth['cases'][c['key']])))
    target=p['cases'][0];mutants=mutations(read(OUT/(target['key']+'__macro.json')),target['observation'],memory,p,'macro',truth['cases'][target['key']])
    require(sum(r['settles'] for r in training+rows)<=p['maximum_native_settle_calls'] and sum(r['cost']['kernel_ticks'] for r in training+rows)<=p['maximum_logical_ticks'],'global numerical caps')
    comparison=[]
    for c in p['cases']:
        rs={r['arm']:r for r in rows if r['key']==c['key']}
        comparison.append(dict(key=c['key'],all_strict_correct=all(r['strict_correct'] for r in rs.values()),hcr_macro_same_expansions=rs['hcr']['expansions']==rs['macro']['expansions'],hcr_macro_same_value=rs['hcr']['value'] is rs['macro']['value']))
    put(OUT/'summary.json',dict(status='TECHNICAL_PROBE_AUDITED',rows=rows,training=training,comparisons=comparison,targeted_rejections=mutants,
        training_calls=3,evaluation_calls=12,world_measure_calls=0,learned_circuit_count=len(memory['circuits']),native_settle_calls=sum(r['settles'] for r in training+rows),kernel_ticks=sum(r['cost']['kernel_ticks'] for r in training+rows),
        numeric_replay_max_absolute_error=max(r['numeric_replay_max_absolute_error'] for r in training+rows),statistical_speed_verdict=None,production_adoption=False))

# Bounded parent is copied from R22 at preparation, with only fixed stage schedule changed.
from tools.r22_measurement_adoption.policy import stage_violations
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
        require(all(source_check().values()),'source preflight');stage('preparation');stage('init')
        for i in range(3):stage('train',str(i))
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
    a=argparse.ArgumentParser();a.add_argument('--phase',required=True,choices=['run','preparation','init','train','case','audit']);a.add_argument('--item',default='');a.add_argument('--started',type=float);args=a.parse_args()
    from hcr.tasks.toy_world import World
    def forbidden(*a,**k):raise ValueError('R31 world measurement forbidden')
    World.measure=forbidden
    if args.phase=='run':run(args.started if args.started is not None else time.monotonic())
    elif args.phase=='init':init()
    elif args.phase=='train':train(int(args.item))
    elif args.phase=='case':case(args.item)
    elif args.phase=='audit':audit_all()
    else:
        import resource
        from tools.r31_macro_control.selfcheck import check
        p=inputs();r=check(p);r['child_limits']=dict(address_space=resource.getrlimit(resource.RLIMIT_AS),file_size=resource.getrlimit(resource.RLIMIT_FSIZE))
        require(r['child_limits']['address_space']==(p['limits']['child_address_space_bytes'],)*2 and r['child_limits']['file_size']==(p['limits']['child_file_bytes'],)*2,'child resource limits');put(OUT/'preparation.json',r)
