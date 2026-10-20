"""Frozen compositional matrix with actual calls and lossless storage-only sharing."""
import argparse,ast,itertools,json,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from hcr.model import Config,fingerprint
from tools.r19_cross_level.probe import read,put,sha,require
SPEC=ROOT/'experiments/exp-82-overlap-composition/frozen_spec.json';OUT=ROOT/'runs/technical'

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
    for n in [2]:
        for bits in itertools.product([False,True],repeat=n+1):
            features=dict(zip(['e'+str(i) for i in range(n)]+['complete'],bits));state=boolean(p['programs']['feasible'+str(n)],features);count=sum(bits[:n]);complete=bits[-1]
            expected=[complete and count==0,complete and count==1,complete and count>1,not complete];require([state[k] for k in ['none','unique','many','incomplete']]==expected,'cardinality Boolean semantics');checks+=1
        for bits in itertools.product([False,True],repeat=2*n+1):
            features=dict(zip([prefix+str(i) for prefix in ['e','t'] for i in range(n)]+['complete'],bits));state=boolean(p['programs']['query'+str(n)],features);values=[bits[n+i] for i in range(n) if bits[i]];complete=bits[-1]
            expected=[complete and bool(values) and all(values),complete and bool(values) and not any(values),complete and not values,complete and bool(values) and any(values) and not all(values),not complete]
            require([state[k] for k in ['qtrue','qfalse','empty','mixed','incomplete']]==expected,'universal Boolean query');checks+=1
    from tools.r36_overlap_composition.runtime import validate_inputs
    sources={s['key']:s for s in p['sources']}
    def packet(key):
        s=sources[key];return dict(predicate=s['predicate'],subject=s['observation']['start'],object=s['observation']['goal'])
    canonical=[c for c in p['cases'] if c['cohort']=='canonical'];sentinels=[c for c in p['cases'] if c['cohort']=='sentinel']
    require(len(canonical)==2304 and {(c['c_pattern'],c['t_pattern'],c['c_expr'],c['t_expr']) for c in canonical}==set(itertools.product(range(8),range(8),range(6),range(6))),'full semantic table')
    require(len(sentinels)==192 and len({(c['c_pattern'],c['t_pattern'],c['namespace'],c['order']) for c in sentinels})==192,'sentinel coverage')
    patterns={'C':set(),'T':set()}
    for c in p['cases']:
        candidates=[packet(k) for k in c['candidates']];context=[packet(k) for k in c['context']];t=[packet(k) for k in c['T']];validate_inputs(candidates,context,t,c['contract'])
        require(len(c['candidates'])==2 and c['complete'] and c['initial']==.5,'two complete fixed-initial alternatives')
        if c['cohort']=='canonical':
            for phase,facts,mask in [('C',context,c['c_pattern']),('T',t,c['t_pattern'])]:
                bits=tuple(candidates[0]['object']==f['subject'] for f in facts);require(bits==tuple(bool((mask>>i)&1) for i in range(3)),'actual typed source pattern');patterns[phase].add(bits)
        checks+=1
    require(all(v==set(itertools.product([False,True],repeat=3)) for v in patterns.values()),'all actual Boolean patterns')
    vectors=[tuple(truth(tree,bits) for bits in itertools.product([False,True],repeat=3)) for tree in p['expressions']];require(len(set(vectors))==6,'six distinct Boolean functions')
    require(28+sum(8*len(c['candidates'])+2 for c in p['cases'])==44956,'derived physical call cap')
    c=p['cases'][0];candidates=[packet(k) for k in c['candidates']];context=[packet(k) for k in c['context']];t=[packet(k) for k in c['T']]
    from copy import deepcopy
    rejected=[]
    for name,field,slot in [('C_predicate','predicate',0),('C_target','object',0),('T_predicate','predicate',1),('R_subject','subject',2)]:
        cc,tt,rr=deepcopy(context),deepcopy(t),deepcopy(candidates);target=cc if slot==0 else tt if slot==1 else rr;target[0][field]='wrong'
        try:validate_inputs(rr,cc,tt,c['contract'])
        except ValueError:rejected.append(name)
        else:raise ValueError('accepted type-slot mutation '+name)
    tree=ast.parse((ROOT/'tools/r35_compositional_slot/runtime.py').read_text());fn=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='consume_t')
    require([x.arg for x in fn.args.args]==['binding','t','t_tree','vocabulary','cfg','role_doc','expr_doc','query_doc','initial'],'unchanged independent consumer boundary')
    put(OUT/'preparation.json',dict(status='PASS',checks=checks,native_calls=0,actual_source_leaf_patterns={k:[list(x) for x in sorted(v)] for k,v in patterns.items()},six_distinct_symbolic_functions=True,slot_guard_mutations_rejected=rejected,program_groups={k:len(v['groups']) for k,v in p['programs'].items()}))

def work():
    from tools.r36_overlap_composition.runtime import lower,export,execute
    from tools.r36_overlap_composition.recording import Recorder,work_writer
    import tools.r34_feasible_state.probe as storage
    p=inputs();write=work_writer(OUT,p);storage.OUT=OUT;storage.put=write;started=time.process_time();sources={s['key']:lower(s['observation'],s['predicate'],p['kernel']) for s in p['sources']};write(OUT/'sources.json',sources);source_cpu=time.process_time()-started
    recorder=Recorder(p);metrics=[];batch=[];part=0;computed_calls=0;completed=0;success=False;inflight=None
    try:
        for c in p['cases']:
            for arm in c['arms']:
                inflight=dict(case=c['key'],arm=arm);start=time.process_time();wall=time.perf_counter();needed=c['candidates']+c['context']+c['T'];packets={key:export(sources[key]) for key in needed};require(all(packets[k]['origin_sha256']==fingerprint(sources[k]) for k in packets),'source export guard')
                r=execute([packets[k] for k in c['candidates']],[packets[k] for k in c['context']],p['expressions'][c['c_expr']],[packets[k] for k in c['T']],p['expressions'][c['t_expr']],c['contract'],c['vocabulary'],arm,p['kernel'],c['initial']);computed_calls+=r['native_calls'];core=time.process_time()-start;storage_start=time.process_time();r['case']=c['key']
                r['network_ids']=[] if arm=='exact' else [recorder.add(k) for k in r.pop('networks')]
                if arm=='native':del r['binding']['alternatives'];r['binding']['alternative_keys']=c['candidates']
                batch.append(r);metrics.append(dict(case=c['key'],arm=arm,core_cpu_seconds=core,storage_cpu_seconds=time.process_time()-storage_start,wall_seconds=time.perf_counter()-wall));completed+=1;inflight=None
            if len(batch)==128:
                write(OUT/('batch%02d.json'%part),batch);write(OUT/('metrics%02d.json'%part),metrics);part+=1;batch=[];metrics=[]
        require(not batch and part==39 and recorder.calls==computed_calls==44928 and completed==4992,'all actual native calls and batches')
        success=True
    finally:
        write(OUT/'work-ledger.json',dict(completed=success,physical_numeric_calls=computed_calls,recorded_references=recorder.calls,source_calls=28,unique_trace_records=len(recorder.cache),storage_references=recorder.calls,computation_reused=False,trace_storage_only_shared=True,source_cpu_seconds=source_cpu,metric_parts=part,completed_evaluations=completed,canonical_cache_bytes=recorder.cached_bytes,maximum_canonical_record_bytes=recorder.peak_record_bytes,unique_trace_bound=p['budget']['maximum_unique_trace_records'],record_bound=p['budget']['record_encoded_cache_max_bytes'],inflight=inflight,inflight_native_call_count_unknown=inflight is not None),metadata=True)
        if not success and batch:write(OUT/'partial-completed.json',dict(records=batch,metrics=metrics),metadata=True)

def audit_all():
    from tools.r36_overlap_composition.verify import SavedNetworks,audit,mutations,distinctions
    from tools.r32_semantic_join.runtime import export
    from tools.r32_semantic_join.verify import audit_lower
    p=inputs();networks=SavedNetworks(OUT,p);error=networks.verify_all();sources=read(OUT/'sources.json');packets={k:export(v) for k,v in sources.items()};lower=[audit_lower(sources[s['key']],s,p) for s in p['sources']];records=[r for i in range(39) for r in read(OUT/('batch%02d.json'%i))];by_case={c['key']:c for c in p['cases']};rows=[audit(r,by_case[r['case']],packets,p,networks) for r in records];r=next(r for r in records if r['arm']=='native');rejected=mutations(r,by_case[r['case']],packets,p,networks)
    calls=28+sum(r['physical_native_calls'] for r in rows);ticks=sum(r['ticks'] for r in rows)+sum(r['ticks'] for r in lower);require(calls==44956 and ticks<=7192960,'derived physical call/tick caps')
    counts={}
    for arm in p['arms']:
        subset=[r for r in rows if r['arm']==arm];counts[arm]=dict(cases=len(subset),strict=sum(r['strict_correct'] for r in subset),value=sum(r['value_correct'] for r in subset),kind=sum(r['kind_correct'] for r in subset),reason=sum(r['reason_correct'] for r in subset),calls=sum(r['physical_native_calls'] for r in subset),ticks=sum(r['ticks'] for r in subset),groups=sum(r['groups'] for r in subset),links=sum(r['links'] for r in subset),role_total=sum(r.get('role_total',0) for r in subset),role_correct=sum(r.get('role_correct',0) for r in subset),AST_total=sum(r.get('AST_total',0) for r in subset),AST_correct=sum(r.get('AST_correct',0) for r in subset))
    put(OUT/'summary.json',dict(status='AUDITED',counts=counts,sources=lower,unique_traces=len(networks),physical_calls=calls,ticks=ticks,max_scalar_error=max(error,max(x['numeric_replay_max_absolute_error'] for x in lower)),mutation_rejections=rejected,semantic_distinctions=distinctions(rows,by_case,p),saved_trace_cache=networks._get.cache_info()._asdict(),learning=0,world_measurement=0,production_adoption=False))

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
    def forbidden(*a,**k):raise ValueError('R36 world measurement forbidden')
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
