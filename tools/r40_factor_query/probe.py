"""Fresh producer matched factor/joint query workloads."""
import argparse,ast,itertools,json,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from hcr.model import Config,fingerprint
from tools.r19_cross_level.probe import read,put,sha,require
SPEC=ROOT/'experiments/exp-86-factor-query/frozen_spec.json';OUT=ROOT/'runs/technical'
def inputs():
    p=read(SPEC);require(all(sha(ROOT/n)==h for n,h in read(SPEC.with_name('input_manifest.json')).items()),'input SHA pins');return p
def preparation():
    import tools.r40_factor_query.runtime as rt
    import tools.r37_joint_tuple.runtime as prior
    from tools.r40_factor_query.verify import oracle
    from tools.r33_typed_feedback.runtime import program
    import tools.r39_z_query.runtime as gates
    p=inputs();cfg=Config(**p['kernel']);require(rt.documents(cfg)==p['programs'],'syntax-only generator');checks=0
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
    for name in ['pair','triple']+['or'+str(n) for n in range(5)]:
        n=3 if name in ['pair','triple'] else int(name[2:])
        for bits in itertools.product([False,True],repeat=n):require(boolean(p['programs'][name],{'m'+str(i):v for i,v in enumerate(bits)})['goal']==(bits[0] and bits[1] if name=='pair' else all(bits) if name=='triple' else any(bits)),'gate Boolean');checks+=1
    for bits in itertools.product([False,True],repeat=3):
        state=boolean(p['programs']['feasible'],dict(zip(['e0','e1','complete'],bits)));n=sum(bits[:2]);require([state[k] for k in ['none','unique','many','incomplete']]==[bits[-1] and n==0,bits[-1] and n==1,bits[-1] and n>1,not bits[-1]],'classifier Boolean');checks+=1
    require(len(p['cases'])==32 and p['repetitions']==3 and [w['key'] for w in p['workloads']]==['q1','q2','q4','q8','u1'],'frozen workload matrix')
    sources={s['key']:dict(predicate=s['predicate'],subject=s['observation']['start'],object=s['observation']['goal'],revision=0,value=True,origin_sha256=s['key']) for s in p['sources']};calls=0;original=rt.kernel;old_gate=gates.kernel;old_prior=prior.kernel
    def stub(doc,drives,cfg,initial):
        nonlocal calls
        calls+=1;state={k:float(v) for k,v in boolean(doc,{k:v>0 for k,v in drives.items()}).items()};return dict(state=state,adopted=state['goal']>.5,convergence=dict(status='stable_decision'))
    rt.kernel=gates.kernel=prior.kernel=stub
    try:
        for rep in range(3):
            for c in p['cases']:
                relations={n:[sources[k] for k in keys] for n,keys in c['relations'].items()}
                for w in p['workloads']:
                    truth=oracle(c['domains'],relations,0,w['queries'])
                    for arm in p['arms']:
                        r=rt.execute(c['domains'],relations,c['vocabulary'],c['order'],w['queries'],arm,p['kernel'],c['initial'])
                        for i,q in enumerate(r['queries']):
                            answer={k:q[k] for k in ['kind','selected_index']};answer['eligible']=q['eligible'] if arm=='exact_joint' else [v>.5 for v in q['eligibility']];require(answer==truth['answers'][i],'Boolean full query route');checks+=1
    finally:rt.kernel=original;gates.kernel=old_gate;prior.kernel=old_prior
    require(calls==85824,'simulated physical count');tree=ast.parse((ROOT/'tools/r40_factor_query/runtime.py').read_text());fns={x.name:x for x in tree.body if isinstance(x,ast.FunctionDef)};require([x.arg for x in fns['consume'].args.args]==['payload','query','representation','cfg','docs','initial'],'consumer isolation signature');require('queries' not in [x.arg for x in fns['produce'].args.args] and 'query' not in [x.arg for x in fns['produce'].args.args],'query-free producer')
    put(OUT/'preparation.json',dict(status='PASS',checks=checks,native_calls=0,boolean_stub_not_numeric_validation=True,simulated_numeric_invocations=calls,contexts=32,repetitions=3,workloads=5,arm_records=1440,query_outputs=4608,program_groups={k:len(v['groups']) for k,v in p['programs'].items()}))

def work():
    from tools.r40_factor_query.runtime import lower,export,execute
    from tools.r38_shared_witness.recording import Recorder,work_writer
    import tools.r34_feasible_state.probe as storage
    p=inputs();write=work_writer(OUT,p);storage.OUT=OUT;storage.put=write;started=time.process_time();sources={s['key']:lower(s['observation'],s['predicate'],p['kernel']) for s in p['sources']};write(OUT/'sources.json',sources);source_cpu=time.process_time()-started
    recorder=Recorder(p);metrics=[];batch=[];part=0;computed=completed=0;success=False;inflight=None
    try:
        for rep in range(3):
            for ci,c in enumerate(p['cases']):
                for wi,w in enumerate(p['workloads']):
                    start_arm=(ci+wi+rep)%3;arms=p['arms'][start_arm:]+p['arms'][:start_arm]
                    for arm in arms:
                        inflight=dict(case=c['key'],repetition=rep,workload=w['key'],arm=arm);start=time.process_time();wall=time.perf_counter();needed=sum(c['relations'].values(),[]);packets={k:export(sources[k]) for k in needed};require(all(packets[k]['origin_sha256']==fingerprint(sources[k]) for k in packets),'source export guard')
                        r=execute(c['domains'],{n:[packets[k] for k in keys] for n,keys in c['relations'].items()},c['vocabulary'],c['order'],w['queries'],arm,p['kernel'],c['initial']);computed+=r['native_calls'];core=time.process_time()-start;storage_start=time.process_time();r.update(case=c['key'],repetition=rep,workload=w['key']);r['network_ids']=[] if arm=='exact_joint' else [recorder.add(k) for k in r.pop('networks')]
                        batch.append(r);metrics.append(dict(case=c['key'],repetition=rep,workload=w['key'],arm=arm,core_cpu_seconds=core,prefix_core_cpu_seconds=r['prefix_core_cpu_seconds'],query_core_cpu_seconds=r['query_core_cpu_seconds'],storage_cpu_seconds=time.process_time()-storage_start,wall_seconds=time.perf_counter()-wall));completed+=1;inflight=None
                    if len(batch)==96:write(OUT/('batch%02d.json'%part),batch);write(OUT/('metrics%02d.json'%part),metrics);part+=1;batch=[];metrics=[]
        require(not batch and part==15 and recorder.calls==computed==85824 and completed==1440,'complete actual calls/scenarios');success=True
    finally:
        write(OUT/'work-ledger.json',dict(completed=success,physical_numeric_calls=computed,recorded_references=recorder.calls,storage_references=recorder.calls,source_calls=24,unique_trace_records=len(recorder.cache),computation_reused=False,trace_storage_only_shared=True,source_cpu_seconds=source_cpu,metric_parts=part,completed_evaluations=completed,canonical_cache_bytes=recorder.cached_bytes,maximum_canonical_record_bytes=recorder.peak_record_bytes,inflight=inflight,inflight_native_call_count_unknown=inflight is not None),metadata=True)
        if not success and batch:write(OUT/'partial-completed.json',dict(records=batch,metrics=metrics),metadata=True)

def audit_all():
    from tools.r40_factor_query.verify import SavedNetworks,audit,mutations,summarize
    from tools.r32_semantic_join.runtime import export
    from tools.r32_semantic_join.verify import audit_lower
    p=inputs();networks=SavedNetworks(OUT,p);error=networks.verify_all();sources=read(OUT/'sources.json');packets={k:export(v) for k,v in sources.items()};low=[audit_lower(sources[s['key']],s,p) for s in p['sources']];records=[r for i in range(15) for r in read(OUT/('batch%02d.json'%i))];cases={c['key']:c for c in p['cases']};rows=[];timing=[]
    for r in records:
        started=time.process_time();rows.append(audit(r,cases[r['case']],packets,p,networks));timing.append(dict(case=r['case'],repetition=r['repetition'],workload=r['workload'],arm=r['arm'],audit_cpu_seconds=time.process_time()-started))
    representative=next(r for r in records if r['arm']=='native_factor' and r['workload']=='q4' and cases[r['case']]['r_mask']==cases[r['case']]['u_mask']==6 and cases[r['case']]['s_mask']==9);rejected=mutations(representative,cases[representative['case']],packets,p,networks);calls=24+sum(r['physical_native_calls'] for r in rows);ticks=sum(r['ticks'] for r in rows)+sum(x['ticks'] for x in low);require(calls==85848 and ticks<=13735680,'physical calls/ticks')
    put(OUT/'audit-metrics.json',timing);put(OUT/'summary.json',dict(status='AUDITED',**summarize(rows),sources=low,unique_traces=len(networks),physical_calls=calls,ticks=ticks,max_scalar_error=max(error,max(x['numeric_replay_max_absolute_error'] for x in low)),mutation_rejections=rejected,saved_trace_cache=networks._get.cache_info()._asdict(),learning=0,world_measurement=0,production_adoption=False))

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
        put(ROOT/'completion.json',dict(parent_process_cpu_seconds=time.process_time(),completed=failure is None,seconds_including_seal=time.monotonic()-started,within_wall_limit=time.monotonic()-started<limits['total_seconds'],evidence_sha256=sha(ROOT/'evidence.zip'),evidence_bytes=(ROOT/'evidence.zip').stat().st_size))
    if failure:raise SystemExit(1)

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--phase',required=True,choices=['run','preparation','work','audit']);a.add_argument('--started',type=float);args=a.parse_args()
    from hcr.tasks.toy_world import World
    def forbidden(*a,**k):raise ValueError('R40 world measurement forbidden')
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
