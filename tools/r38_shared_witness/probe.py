"""Frozen same-Z triangle versus independent witness relaxation."""
import argparse,ast,itertools,json,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from hcr.model import Config,fingerprint
from tools.r19_cross_level.probe import read,put,sha,require
SPEC=ROOT/'experiments/exp-84-shared-witness/frozen_spec.json';OUT=ROOT/'runs/technical'
def inputs():
    p=read(SPEC);require(all(sha(ROOT/n)==h for n,h in read(SPEC.with_name('input_manifest.json')).items()),'input SHA pins');return p
def preparation():
    import tools.r38_shared_witness.runtime as rt
    from tools.r38_shared_witness.verify import oracle
    from tools.r33_typed_feedback.runtime import program
    p=inputs();cfg=Config(**p['kernel']);require(rt.documents(cfg)==p['programs'],'unchanged syntax-only generator');checks=0
    for doc in p['programs'].values():program(doc).validate(cfg)
    def boolean(doc,features):
        state=dict(features)
        for g in doc['groups']:
            name=g['id']
            if name in state:continue
            terms=[state[e['source']] if e['weight']>0 else not state[e['source']] for e in doc['links'] if e['kind']=='support' and e['target']==name]
            state[name]=(all(terms) if g['bias']<0 else any(terms)) if terms else g['bias']>0
        return state
    for x,y in itertools.product(range(8),repeat=2):
        f={a+str(i):bool((v>>i)&1) for a,v in [('x',x),('y',y)] for i in range(3)};require(boolean(p['programs']['role'],f)['goal']==(x==y),'role Boolean');checks+=1
    for name in ['pair']+['or'+str(n) for n in range(5)]:
        n=3 if name=='pair' else int(name[2:])
        for bits in itertools.product([False,True],repeat=n):require(boolean(p['programs'][name],{'m'+str(i):v for i,v in enumerate(bits)})['goal']==(bits[0] and bits[1] if name=='pair' else any(bits)),'gate Boolean');checks+=1
    for bits in itertools.product([False,True],repeat=5):
        state=boolean(p['programs']['feasible'],dict(zip(['e'+str(i) for i in range(4)]+['complete'],bits)));n=sum(bits[:4]);require([state[k] for k in ['none','unique','many','incomplete']]==[bits[-1] and n==0,bits[-1] and n==1,bits[-1] and n>1,not bits[-1]],'classifier Boolean');checks+=1
    sources={s['key']:dict(predicate=s['predicate'],subject=s['observation']['start'],object=s['observation']['goal'],revision=0,value=True,origin_sha256=s['key']) for s in p['sources']}
    expected={(r,s,u,0,0) for r,s,u in itertools.product([6,9],range(16),range(16))}|{(r,s,u,ns,o) for r,s,u in itertools.product([6,9],[0,6,9,15],[0,6,9,15]) for ns,o in [(0,1),(1,0),(1,1)]};require(len(p['cases'])==608 and {(c['r_mask'],c['s_mask'],c['u_mask'],c['namespace'],c['order']) for c in p['cases']}==expected,'frozen608matrix');full=relaxed=0;elig=0;false=0
    original=rt.kernel
    def stub(doc,drives,cfg,initial):return dict(state={k:float(v) for k,v in boolean(doc,{k:v>0 for k,v in drives.items()}).items()})
    rt.kernel=stub
    try:
        for c in p['cases']:
            rels={n:[sources[k] for k in keys] for n,keys in c['relations'].items()};rt.validate(c['domains'],rels,c['vocabulary'],c['order']);truth=oracle(c['domains'],rels,c['order']);split=oracle(c['domains'],rels,c['order'],True)
            require(rt.exact(c['domains'],rels,c['order'])['eligible']==truth['eligible'],'separate exact set oracle')
            messages={n:[float(any(a['X']==f['subject'] and a['Y']==f['object'] for f in rels[n])) for a in rt.layout(c['domains'],axes,c['order'])] for n,axes in rt.AXES.items()}
            for arm,target in [('native_shared',truth),('native_split',split)]:
                values,inter,ks=rt.combine(messages,c['order'],cfg,p['programs'],c['initial'],arm);require([v>.5 for v in values]==target['eligible'],'Boolean combine same/split witness');checks+=1
            full+=truth['eligible']==split['eligible'];elig+=sum(x==y for x,y in zip(truth['eligible'],split['eligible']));false+=split['consistent'] and not truth['consistent'];checks+=1
    finally:rt.kernel=original
    fn=next(x for x in ast.parse((ROOT/'tools/r38_shared_witness/runtime.py').read_text()).body if isinstance(x,ast.FunctionDef) and x.name=='combine');require([x.arg for x in fn.args.args]==['messages','order','cfg','docs','initial','arm'],'no facts/case/mask/oracle in numeric combiner')
    put(OUT/'preparation.json',dict(status='PASS',checks=checks,native_calls=0,boolean_stub_not_numeric_validation=True,full_table_cases=608,expected_split_full_strict=full,expected_split_eligibility_correct=elig,expected_split_false_consistency=false,program_groups={k:len(v['groups']) for k,v in p['programs'].items()}))
def work():
    from tools.r38_shared_witness.runtime import lower,export,execute
    from tools.r38_shared_witness.recording import Recorder,work_writer
    import tools.r34_feasible_state.probe as storage
    p=inputs();write=work_writer(OUT,p);storage.OUT=OUT;storage.put=write;started=time.process_time();sources={s['key']:lower(s['observation'],s['predicate'],p['kernel']) for s in p['sources']};write(OUT/'sources.json',sources);source_cpu=time.process_time()-started
    recorder=Recorder(p);metrics=[];batch=[];part=0;computed=completed=0;success=False;inflight=None
    try:
        for c in p['cases']:
            for arm in c['arms']:
                inflight=dict(case=c['key'],arm=arm);start=time.process_time();wall=time.perf_counter();needed=sum(c['relations'].values(),[]);packets={k:export(sources[k]) for k in needed};require(all(packets[k]['origin_sha256']==fingerprint(sources[k]) for k in packets),'source export guard')
                r=execute(c['domains'],{n:[packets[k] for k in keys] for n,keys in c['relations'].items()},c['vocabulary'],c['order'],arm,p['kernel'],c['initial']);computed+=r['native_calls'];core=time.process_time()-start;storage_start=time.process_time();r['case']=c['key'];r['network_ids']=[] if arm=='exact_joint' else [recorder.add(k) for k in r.pop('networks')]
                batch.append(r);metrics.append(dict(case=c['key'],arm=arm,core_cpu_seconds=core,storage_cpu_seconds=time.process_time()-storage_start,wall_seconds=time.perf_counter()-wall));completed+=1;inflight=None
            if len(batch)==96:write(OUT/('batch%02d.json'%part),batch);write(OUT/('metrics%02d.json'%part),metrics);part+=1;batch=[];metrics=[]
        require(not batch and part==19 and recorder.calls==computed==120384 and completed==1824,'all physical calls and outputs');success=True
    finally:
        write(OUT/'work-ledger.json',dict(completed=success,physical_numeric_calls=computed,recorded_references=recorder.calls,source_calls=24,unique_trace_records=len(recorder.cache),storage_references=recorder.calls,computation_reused=False,trace_storage_only_shared=True,source_cpu_seconds=source_cpu,metric_parts=part,completed_evaluations=completed,canonical_cache_bytes=recorder.cached_bytes,maximum_canonical_record_bytes=recorder.peak_record_bytes,unique_trace_bound=p['budget']['maximum_unique_trace_records'],record_bound=p['budget']['record_encoded_cache_max_bytes'],inflight=inflight,inflight_native_call_count_unknown=inflight is not None),metadata=True)
        if not success and batch:write(OUT/'partial-completed.json',dict(records=batch,metrics=metrics),metadata=True)
def audit_all():
    from tools.r38_shared_witness.verify import SavedNetworks,audit,mutations,summarize
    from tools.r32_semantic_join.runtime import export
    from tools.r32_semantic_join.verify import audit_lower
    p=inputs();networks=SavedNetworks(OUT,p);error=networks.verify_all();sources=read(OUT/'sources.json');packets={k:export(v) for k,v in sources.items()};lower=[audit_lower(sources[s['key']],s,p) for s in p['sources']];records=[r for i in range(19) for r in read(OUT/('batch%02d.json'%i))];cases={c['key']:c for c in p['cases']};rows=[audit(r,cases[r['case']],packets,p,networks) for r in records];r=next(r for r in records if r['arm']=='native_shared' and cases[r['case']]['r_mask']==cases[r['case']]['s_mask']==9 and cases[r['case']]['u_mask']==6);rejected=mutations(r,cases[r['case']],packets,p,networks)
    calls=24+sum(r['physical_native_calls'] for r in rows);ticks=sum(r['ticks'] for r in rows)+sum(x['ticks'] for x in lower);require(calls==120408 and ticks<=19265280,'derived physical counts')
    put(OUT/'summary.json',dict(status='AUDITED',**summarize(rows),sources=lower,unique_traces=len(networks),physical_calls=calls,ticks=ticks,max_scalar_error=max(error,max(x['numeric_replay_max_absolute_error'] for x in lower)),mutation_rejections=rejected,saved_trace_cache=networks._get.cache_info()._asdict(),learning=0,world_measurement=0,production_adoption=False))
def run(started):
    import resource,signal,subprocess,traceback,zipfile
    p=inputs();limits=p['limits'];OUT.mkdir(parents=True,exist_ok=False);deadline=started+limits['total_seconds']-30;stages=[];failure=None;manifest=read(ROOT/'source_manifest.json')
    def terminate(signum,frame):raise TimeoutError('termination signal '+str(signum))
    signal.signal(signal.SIGTERM,terminate)
    def source_check():return {n:(ROOT/n).is_file() and sha(ROOT/n)==h for n,h in manifest.items()}
    def limit():resource.setrlimit(resource.RLIMIT_AS,(limits['child_address_space_bytes'],)*2);resource.setrlimit(resource.RLIMIT_FSIZE,(limits['child_file_bytes'],)*2)
    try:
        require(all(source_check().values()),'source preflight')
        for phase in ['preparation','work','audit']:
            before=time.monotonic();u=resource.getrusage(resource.RUSAGE_CHILDREN);require(deadline-before>30,'deadline reserve')
            with (OUT/(phase+'.stdout')).open('xb') as stdout,(OUT/(phase+'.stderr')).open('xb') as stderr:
                child=subprocess.Popen([sys.executable,'-B',str(Path(__file__)),'--phase',phase],stdout=stdout,stderr=stderr,preexec_fn=limit)
                try:rc=child.wait(timeout=min(limits['stage_seconds'],deadline-time.monotonic()-20))
                except BaseException:child.kill();child.wait();raise
            v=resource.getrusage(resource.RUSAGE_CHILDREN);raw=sum(f.stat().st_size for f in OUT.iterdir() if f.is_file());stages.append(dict(phase=phase,returncode=rc,wall_seconds=time.monotonic()-before,cpu_seconds=v.ru_utime+v.ru_stime-u.ru_utime-u.ru_stime,raw_bytes=raw));require(rc==0 and raw<=limits['raw_bytes'],'stage/cap failure '+phase)
    except BaseException:failure=traceback.format_exc()
    finally:
        post=source_check();put(OUT/'source-postcheck.json',dict(unchanged=all(post.values()),files=post))
        if not all(post.values()):failure=(failure or '')+'\nsource postcheck failed'
        if failure:put(OUT/'failure.json',dict(traceback=failure,retry=False))
        put(OUT/'result.json',dict(status='FAILED' if failure else 'COMPLETED',stages=stages,source_unchanged=all(post.values()),source_manifest_sha256=sha(ROOT/'source_manifest.json'),seconds_before_seal=time.monotonic()-started,python=sys.version.split()[0],platform=sys.platform,retry=False))
        put(OUT/'manifest.json',{f.name:dict(sha256=sha(f),bytes=f.stat().st_size) for f in sorted(OUT.iterdir()) if f.is_file()})
        with zipfile.ZipFile(ROOT/'evidence.zip','x',compression=zipfile.ZIP_DEFLATED) as z:
            for f in sorted(OUT.iterdir()):
                if f.is_file():z.write(f,'technical/'+f.name)
        put(ROOT/'completion.json',dict(completed=failure is None,seconds_including_seal=time.monotonic()-started,within_wall_limit=time.monotonic()-started<limits['total_seconds'],evidence_sha256=sha(ROOT/'evidence.zip'),evidence_bytes=(ROOT/'evidence.zip').stat().st_size))
    if failure:raise SystemExit(1)

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--phase',required=True,choices=['run','preparation','work','audit']);a.add_argument('--started',type=float);args=a.parse_args()
    from hcr.tasks.toy_world import World
    def forbidden(*a,**k):raise ValueError('R38 world measurement forbidden')
    World.measure=forbidden
    if args.phase=='run':run(args.started or time.monotonic())
    else:
        import resource
        try:
            if args.phase=='preparation':preparation()
            elif args.phase=='work':work()
            else:audit_all()
        finally:
            u=resource.getrusage(resource.RUSAGE_SELF)
            put(OUT/(args.phase+'-resources.json'),dict(platform=sys.platform,ru_maxrss_raw=u.ru_maxrss,ru_maxrss_units='platform-native getrusage; no conversion asserted',user_cpu_seconds=u.ru_utime,system_cpu_seconds=u.ru_stime))
