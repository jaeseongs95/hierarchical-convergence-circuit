"""Frozen joint tuple versus native marginal-product intervention."""
import argparse,ast,itertools,json,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from hcr.model import Config,fingerprint
from tools.r19_cross_level.probe import read,put,sha,require
SPEC=ROOT/'experiments/exp-83-joint-tuple/frozen_spec.json';OUT=ROOT/'runs/technical'
def inputs():
    p=read(SPEC);require(all(sha(ROOT/n)==h for n,h in read(SPEC.with_name('input_manifest.json')).items()),'input SHA pins');return p
def preparation():
    from tools.r37_joint_tuple.runtime import documents,validate
    from tools.r37_joint_tuple.verify import oracle
    from tools.r33_typed_feedback.runtime import program
    p=inputs();cfg=Config(**p['kernel']);require(documents(cfg)==p['programs'],'syntax/layout-only generator');checks=0
    for doc in p['programs'].values():program(doc).validate(cfg)
    def boolean(doc,features):
        state=dict(features)
        for g in doc['groups']:
            name=g['id']
            if name in state:continue
            terms=[state[e['source']] if e['weight']>0 else not state[e['source']] for e in doc['links'] if e['kind']=='support' and e['target']==name]
            state[name]=(all(terms) if g['bias']<0 else any(terms)) if terms else g['bias']>0
        return state
    for x in range(8):
        for y in range(8):
            state=boolean(p['programs']['role'],{prefix+str(i):bool((v>>i)&1) for prefix,v in [('x',x),('y',y)] for i in range(3)});require(state['goal']==(x==y),'3bit role equality');checks+=1
    for bits in itertools.product([False,True],repeat=3):require(boolean(p['programs']['pair'],dict(zip(['m0','m1','m2'],bits)))['goal']==(bits[0] and bits[1]),'pair conjunction');checks+=1
    for n in range(5):
        for bits in itertools.product([False,True],repeat=n):require(boolean(p['programs']['or'+str(n)],dict(zip(['m'+str(i) for i in range(n)],bits)))['goal']==any(bits),'relation disjunction');checks+=1
    for order in range(2):
        layout=[[0,0],[0,1],[1,0],[1,1]][::1 if order==0 else -1]
        for bits in itertools.product([False,True],repeat=4):
            state=boolean(p['programs']['projection'+str(order)],dict(zip(['f'+str(i) for i in range(4)],bits)));allowed=[xy for xy,v in zip(layout,bits) if v];xs={x for x,y in allowed};ys={y for x,y in allowed};require([state['e'+str(i)] for i in range(4)]==[x in xs and y in ys for x,y in layout],'marginal-only re-cross');checks+=1
    for bits in itertools.product([False,True],repeat=5):
        state=boolean(p['programs']['feasible'],dict(zip(['e'+str(i) for i in range(4)]+['complete'],bits)));n=sum(bits[:4]);require([state[k] for k in ['none','unique','many','incomplete']]==[bits[-1] and n==0,bits[-1] and n==1,bits[-1] and n>1,not bits[-1]],'feasible cardinality');checks+=1
    for bits in itertools.product([False,True],repeat=9):
        state=boolean(p['programs']['query'],dict(zip([prefix+str(i) for prefix in ['e','t'] for i in range(4)]+['complete'],bits)));vals=[bits[i+4] for i in range(4) if bits[i]];complete=bits[-1];require([state[k] for k in ['qtrue','qfalse','empty','mixed','incomplete']]==[complete and bool(vals) and all(vals),complete and bool(vals) and not any(vals),complete and not vals,complete and bool(vals) and any(vals) and not all(vals),not complete],'universal tuple query');checks+=1
    sources={s['key']:dict(predicate=s['predicate'],subject=s['observation']['start'],object=s['observation']['goal'],revision=0,value=True,origin_sha256=s['key']) for s in p['sources']}
    require({(c['c_mask'],c['t_mask'],c['namespace'],c['order']) for c in p['cases']}==set(itertools.product(range(16),range(16),range(2),range(2))) and len(p['cases'])==1024,'complete table and variants')
    strict=eligibility=0;signatures=set();closure_signatures=set()
    for c in p['cases']:
        C=[sources[k] for k in c['context']];T=[sources[k] for k in c['T']];validate(c['domains'],c['alternatives'],C,'C');validate(c['domains'],c['alternatives'],T,'T');exact=oracle(c['alternatives'],C,T);marginal=oracle(c['alternatives'],C,T,True);strict+=all(exact[k]==marginal[k] for k in ['kind','selected_index','value','reason']);eligibility+=sum(x==y for x,y in zip(exact['eligible'],marginal['eligible']))
        if c['namespace']==c['order']==0 and c['t_mask']==0:signatures.add(tuple(exact['eligible']));closure_signatures.add(tuple(marginal['eligible']))
        checks+=1
    require(strict==944 and eligibility==3584 and len(signatures)==16 and len(closure_signatures)==10,'declared information-loss oracle')
    tree=ast.parse((ROOT/'tools/r37_joint_tuple/runtime.py').read_text());fn=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='consume_t');require([x.arg for x in fn.args.args]==['binding','t','vocabulary','cfg','docs','initial'],'no first C/oracle/source registry T signature')
    put(OUT/'preparation.json',dict(status='PASS',checks=checks,native_calls=0,expected_marginal_full_strict=944,expected_marginal_eligible_correct=3584,expected_joint_signatures=16,expected_closure_signatures=10,full_table_cases=1024,program_groups={k:len(v['groups']) for k,v in p['programs'].items()}))
def work():
    from tools.r37_joint_tuple.runtime import lower,export,execute
    from tools.r36_overlap_composition.recording import Recorder,work_writer
    import tools.r34_feasible_state.probe as storage
    p=inputs();write=work_writer(OUT,p);storage.OUT=OUT;storage.put=write;started=time.process_time();sources={s['key']:lower(s['observation'],s['predicate'],p['kernel']) for s in p['sources']};write(OUT/'sources.json',sources);source_cpu=time.process_time()-started
    recorder=Recorder(p);metrics=[];batch=[];part=0;computed=completed=0;success=False;inflight=None
    try:
        for c in p['cases']:
            for arm in c['arms']:
                inflight=dict(case=c['key'],arm=arm);start=time.process_time();wall=time.perf_counter();needed=c['context']+c['T'];packets={k:export(sources[k]) for k in needed};require(all(packets[k]['origin_sha256']==fingerprint(sources[k]) for k in packets),'source export guard')
                r=execute(c['domains'],c['alternatives'],[packets[k] for k in c['context']],[packets[k] for k in c['T']],c['vocabulary'],arm,p['kernel'],c['initial']);computed+=r['native_calls'];core=time.process_time()-start;storage_start=time.process_time();r['case']=c['key'];r['network_ids']=[] if arm=='exact_joint' else [recorder.add(k) for k in r.pop('networks')]
                batch.append(r);metrics.append(dict(case=c['key'],arm=arm,core_cpu_seconds=core,storage_cpu_seconds=time.process_time()-storage_start,wall_seconds=time.perf_counter()-wall));completed+=1;inflight=None
            if len(batch)==96:write(OUT/('batch%02d.json'%part),batch);write(OUT/('metrics%02d.json'%part),metrics);part+=1;batch=[];metrics=[]
        require(not batch and part==32 and recorder.calls==computed==119808 and completed==3072,'all physical calls and outputs');success=True
    finally:
        write(OUT/'work-ledger.json',dict(completed=success,physical_numeric_calls=computed,recorded_references=recorder.calls,source_calls=16,unique_trace_records=len(recorder.cache),storage_references=recorder.calls,computation_reused=False,trace_storage_only_shared=True,source_cpu_seconds=source_cpu,metric_parts=part,completed_evaluations=completed,canonical_cache_bytes=recorder.cached_bytes,maximum_canonical_record_bytes=recorder.peak_record_bytes,unique_trace_bound=p['budget']['maximum_unique_trace_records'],record_bound=p['budget']['record_encoded_cache_max_bytes'],inflight=inflight,inflight_native_call_count_unknown=inflight is not None),metadata=True)
        if not success and batch:write(OUT/'partial-completed.json',dict(records=batch,metrics=metrics),metadata=True)
def audit_all():
    from tools.r37_joint_tuple.verify import SavedNetworks,audit,mutations,summarize
    from tools.r32_semantic_join.runtime import export
    from tools.r32_semantic_join.verify import audit_lower
    p=inputs();networks=SavedNetworks(OUT,p);error=networks.verify_all();sources=read(OUT/'sources.json');packets={k:export(v) for k,v in sources.items()};lower=[audit_lower(sources[s['key']],s,p) for s in p['sources']];records=[r for i in range(32) for r in read(OUT/('batch%02d.json'%i))];cases={c['key']:c for c in p['cases']};rows=[audit(r,cases[r['case']],packets,p,networks) for r in records];r=next(r for r in records if r['arm']=='native_joint' and cases[r['case']]['c_mask']==cases[r['case']]['t_mask']==9);rejected=mutations(r,cases[r['case']],packets,p,networks)
    calls=16+sum(r['physical_native_calls'] for r in rows);ticks=sum(r['ticks'] for r in rows)+sum(x['ticks'] for x in lower);require(calls==119824 and ticks<=19171840,'derived physical counts')
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
    def forbidden(*a,**k):raise ValueError('R37 world measurement forbidden')
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
