"""Frozen compositional matrix with actual calls and lossless storage-only sharing."""
import argparse,ast,itertools,json,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from hcr.model import Config,fingerprint
from tools.r19_cross_level.probe import read,put,sha,require
SPEC=ROOT/'experiments/exp-81-compositional-slot/frozen_spec.json';OUT=ROOT/'runs/technical'

def inputs():
    p=read(SPEC);require(all(sha(ROOT/n)==h for n,h in read(SPEC.with_name('input_manifest.json')).items()),'input SHA pins');return p

def preparation():
    from tools.r35_compositional_slot.compiler import documents
    from tools.r35_compositional_slot.runtime import truth
    from tools.r33_typed_feedback.runtime import program
    p=inputs();cfg=Config(**p['kernel']);require(documents(p['expressions'],cfg)==p['programs'],'single syntax/count generator');checks=0
    for doc in p['programs'].values():program(doc).validate(cfg)
    def boolean(doc,features):
        state=dict(features)
        for group in doc['groups']:
            name=group['id']
            if name in state:continue
            terms=[state[e['source']] if e['weight']>0 else not state[e['source']] for e in doc['links'] if e['kind']=='support' and e['target']==name]
            state[name]=(all(terms) if group['bias']<0 else any(terms)) if terms else group['bias']>0
        return state
    for x in range(8):
        for y in range(8):
            state=boolean(p['programs']['role'],{prefix+str(i):bool((v>>i)&1) for prefix,v in [('x',x),('y',y)] for i in range(3)});require(state['goal']==(x==y),'3bit Boolean equality');checks+=1
    for i,tree in enumerate(p['expressions']):
        for bits in itertools.product([False,True],repeat=3):require(boolean(p['programs']['expr'+str(i)],dict(zip(['m0','m1','m2'],bits)))['goal']==truth(tree,bits),'AST Boolean semantics');checks+=1
    for n in range(1,5):
        for bits in itertools.product([False,True],repeat=n+1):
            features=dict(zip(['e'+str(i) for i in range(n)]+['complete'],bits));state=boolean(p['programs']['feasible'+str(n)],features);count=sum(bits[:n]);complete=bits[-1]
            expected=[complete and count==0,complete and count==1,complete and count>1,not complete];require([state[k] for k in ['none','unique','many','incomplete']]==expected,'cardinality Boolean semantics');checks+=1
        for bits in itertools.product([False,True],repeat=2*n+1):
            features=dict(zip([prefix+str(i) for prefix in ['e','t'] for i in range(n)]+['complete'],bits));state=boolean(p['programs']['query'+str(n)],features);values=[bits[n+i] for i in range(n) if bits[i]];complete=bits[-1]
            expected=[complete and bool(values) and all(values),complete and bool(values) and not any(values),complete and not values,complete and bool(values) and any(values) and not all(values),not complete]
            require([state[k] for k in ['qtrue','qfalse','empty','mixed','incomplete']]==expected,'universal Boolean query');checks+=1
    factors={(c['base_n'],c['c_expr'],c['t_expr'],c['namespace'],c['order'],c['complete']) for c in p['cases']};require(len(factors)==len(p['cases'])==864,'frozen matrix completeness');checks+=864
    require(24+sum(8*len(c['candidates'])+2 for c in p['cases'])==19032,'native planned call cap')
    tree=ast.parse((ROOT/'tools/r35_compositional_slot/runtime.py').read_text());fn=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='consume_t')
    require([x.arg for x in fn.args.args]==['binding','t','t_tree','vocabulary','cfg','role_doc','expr_doc','query_doc','initial'],'independent final consumer boundary')
    put(OUT/'preparation.json',dict(status='PASS',checks=checks,native_calls=0,program_groups={k:len(v['groups']) for k,v in p['programs'].items()}))

def work():
    from tools.r35_compositional_slot.runtime import lower,export,execute
    import tools.r34_feasible_state.probe as storage
    p=inputs();storage.OUT=OUT;started=time.process_time();sources={s['key']:lower(s['observation'],s['predicate'],p['kernel']) for s in p['sources']};put(OUT/'sources.json',sources);source_cpu=time.process_time()-started
    recorder=storage.Recorder(p);metrics=[];batch=[];part=0
    for c in p['cases']:
        for arm in c['arms']:
            start=time.process_time();wall=time.perf_counter();needed=c['candidates']+c['context']+c['T'];packets={key:export(sources[key]) for key in needed};require(all(packets[k]['origin_sha256']==fingerprint(sources[k]) for k in packets),'source export guard')
            r=execute([packets[k] for k in c['candidates']],[packets[k] for k in c['context']],p['expressions'][c['c_expr']],[packets[k] for k in c['T']],p['expressions'][c['t_expr']],c['complete'],c['vocabulary'],arm,p['kernel'],c['initial']);core=time.process_time()-start;storage_start=time.process_time();r['case']=c['key']
            r['network_ids']=[] if arm=='exact' else [recorder.add(k) for k in r.pop('networks')]
            if arm=='native':del r['binding']['alternatives'];r['binding']['alternative_keys']=c['candidates']
            batch.append(r);metrics.append(dict(case=c['key'],arm=arm,core_cpu_seconds=core,storage_cpu_seconds=time.process_time()-storage_start,wall_seconds=time.perf_counter()-wall))
        if len(batch)==144:put(OUT/('batch%02d.json'%part),batch);part+=1;batch=[]
    require(not batch and part==12 and recorder.calls==19008,'all actual native calls recorded')
    put(OUT/'work-ledger.json',dict(physical_numeric_calls=recorder.calls,source_calls=24,unique_trace_records=len(recorder.items),storage_references=recorder.calls,computation_reused=False,trace_storage_only_shared=True,source_cpu_seconds=source_cpu,metrics=metrics))

def audit_all():
    from tools.r35_compositional_slot.verify import verify_networks,audit,mutations
    from tools.r32_semantic_join.runtime import export
    from tools.r32_semantic_join.verify import audit_lower
    p=inputs();documents={f.stem:read(f) for f in OUT.glob('n[0-9]*.json')};networks,error=verify_networks(documents,p);sources=read(OUT/'sources.json');packets={k:export(v) for k,v in sources.items()};lower=[audit_lower(sources[s['key']],s,p) for s in p['sources']];records=[r for i in range(12) for r in read(OUT/('batch%02d.json'%i))];by_case={c['key']:c for c in p['cases']};rows=[audit(r,by_case[r['case']],packets,p,networks) for r in records];r=next(r for r in records if r['arm']=='native');rejected=mutations(r,by_case[r['case']],packets,p,networks)
    calls=24+sum(r['physical_native_calls'] for r in rows);ticks=sum(r['ticks'] for r in rows)+sum(r['ticks'] for r in lower);require(calls==19032 and ticks<=3045120,'native caps')
    counts={}
    for arm in p['arms']:
        subset=[r for r in rows if r['arm']==arm];counts[arm]=dict(cases=len(subset),strict=sum(r['strict_correct'] for r in subset),value=sum(r['value_correct'] for r in subset),kind=sum(r['kind_correct'] for r in subset),reason=sum(r['reason_correct'] for r in subset),calls=sum(r['physical_native_calls'] for r in subset),ticks=sum(r['ticks'] for r in subset),groups=sum(r['groups'] for r in subset),links=sum(r['links'] for r in subset))
    put(OUT/'summary.json',dict(status='AUDITED',counts=counts,sources=lower,unique_traces=len(networks),physical_calls=calls,ticks=ticks,max_scalar_error=max(error,max(x['numeric_replay_max_absolute_error'] for x in lower)),mutation_rejections=rejected,learning=0,world_measurement=0,production_adoption=False))

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
    def forbidden(*a,**k):raise ValueError('R35 world measurement forbidden')
    World.measure=forbidden
    if args.phase=='run':run(args.started or time.monotonic())
    elif args.phase=='preparation':preparation()
    elif args.phase=='work':work()
    else:audit_all()
