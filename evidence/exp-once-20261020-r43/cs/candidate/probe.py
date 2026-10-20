"""Matched observation of producer and original kernel CPU phases."""
import argparse,ast,itertools,json,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from hcr.model import Config,fingerprint
from tools.r19_cross_level.probe import read,put,sha,require
SPEC=ROOT/'experiments/exp-89-exp-once/frozen_spec.json';OUT=ROOT/'runs/technical'
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
    require(len(p['cases'])==32 and p['repetitions']==3 and len(p['workloads'])==1 and p['workloads'][0]['key']=='q4' and p['modes']==['baseline','exp_once'],'frozen matrix')
    sources={s['key']:dict(predicate=s['predicate'],subject=s['observation']['start'],object=s['observation']['goal'],revision=0,value=True,origin_sha256=s['key']) for s in p['sources']};calls=0;original=rt.kernel;old_gate=gates.kernel;old_prior=prior.kernel
    def stub(doc,drives,cfg,initial):
        nonlocal calls
        calls+=1;state={k:float(v) for k,v in boolean(doc,{k:v>0 for k,v in drives.items()}).items()};return dict(state=state,adopted=state['goal']>.5,convergence=dict(status='stable_decision'))
    rt.kernel=gates.kernel=prior.kernel=stub
    try:
        for c in p['cases']:
            relations={n:[sources[k] for k in keys] for n,keys in c['relations'].items()};w=p['workloads'][0];truth=oracle(c['domains'],relations,0,w['queries'])
            for arm in p['arms']:
                r=rt.execute(c['domains'],relations,c['vocabulary'],c['order'],w['queries'],arm,p['kernel'],c['initial'])
                for i,q in enumerate(r['queries']):
                    answer={k:q[k] for k in ['kind','selected_index']};answer['eligible']=q['eligible'] if arm=='exact_joint' else [v>.5 for v in q['eligibility']];require(answer==truth['answers'][i],'Boolean original q4 route');checks+=1
    finally:rt.kernel=original;gates.kernel=old_gate;prior.kernel=old_prior
    require(calls==5760,'Boolean physical plan per repeat/mode')
    from tools.r43_exp_once.runtime import SOURCE,OLD,NEW,CANDIDATE_SOURCE
    require(SOURCE.count(OLD)==1 and CANDIDATE_SOURCE==SOURCE.replace(OLD,NEW),'single source substitution');ast.parse(CANDIDATE_SOURCE)
    require(len(p['correctness_inputs'])==65 and len(p['direct_tests'])==18 and sum(2 for _ in p['direct_tests'])==36,'correctness matrix')
    put(OUT/'preparation.json',dict(status='PASS',checks=checks,native_calls=0,boolean_stub_not_numeric_validation=True,simulated_numeric_invocations=calls,contexts=32,repetitions=3,arm_records=480,query_outputs=1920,prior_unique_inputs=65,direct_tick_invocations=36,single_source_substitution=True))

def correctness():
    from hcr import codec,dynamics
    from hcr.model import Cost,Config,ContractError
    from tools.r34_feasible_state.verify import expand_network
    from tools.r43_exp_once import runtime as rt
    from tools.r43_exp_once.verify import counted_pair,direct_checks
    p=inputs();prior=read(ROOT/'experiments/exp-88-coarse-profile/frozen_spec.json');rows=[];parts=0;totals=[]
    for entry in p['correctness_inputs']:
        require(sha(ROOT/entry['path'])==entry['sha256'],'prior input SHA');expected=expand_network(read(ROOT/entry['path']),prior);cfg=p['kernel'];items={m:rt.counted_kernel(expected['program'],expected['drives'],cfg,next(iter(expected['initial'].values())),m) for m in p['modes']}
        ref=__import__('hashlib').sha256(rt.canonical(expected,cfg)).hexdigest();row=dict(kind='prior',key=entry['key'],config=cfg,reference_sha256=ref,opportunity=rt.opportunity(expected,cfg),**items);totals.append(counted_pair(row,p));rows.append(row)
        if len(rows)==5:put(OUT/('correct%02d.json'%parts),rows);rows=[];parts+=1
    require(not rows and parts==13,'counted input coverage');controls=[]
    for control in p['control_tests']:
        cfg=dict(p['kernel'],self_excitation=0.,inhibition=0.,max_ticks=1,patience=1);doc=dict(groups=[dict(id='goal',level=1,bias=0.)],links=[],paths=[[0]],edge_count=1);items={m:rt.counted_kernel(doc,{'goal':control['drive']},cfg,.5,m) for m in p['modes']};row=dict(kind='control',key=control['name'],config=cfg,expected_status=control['status'],opportunity=rt.opportunity(items['baseline']['kernel'],cfg),**items);totals.append(counted_pair(row,p));controls.append(row)
    put(OUT/'correct-controls.json',controls);direct=[]
    for test in p['direct_tests']:
        outputs={}
        for mode in p['modes']:
            doc,current,drives,cfg,top=rt.direct_input(test,p);pr=rt.program(doc);pr.validate(cfg);cost=Cost();info=None
            try:
                with rt.installed(mode,True) as info:nxt=dynamics.tick(pr,current,drives,cfg,cost,top_down=top)
                output=dict(next=nxt,next_order=list(nxt),cost=cost.snapshot(),error_type=None)
            except ContractError as e:output=dict(error_type=type(e).__name__,error_message=str(e),cost=cost.snapshot())
            output.update(exp_calls=info['exp_calls'],restored=info['restored']);outputs[mode]=output
        direct.append(dict(test=test['name'],zero_cost=Cost().snapshot(),**outputs))
    dd=direct_checks(direct,p);put(OUT/'direct-ticks.json',direct)
    try:
        with rt.installed('exp_once') as exceptional:raise ValueError('synthetic controlled exception')
    except ValueError:require(exceptional['restored'],'exception restore')
    with rt.installed('baseline') as outer:
        try:
            with rt.installed('exp_once'):raise AssertionError('nested accepted')
        except ValueError:pass
    require(outer['restored'] and dynamics.tick is rt.NATIVE_TICK,'normal/nested restore')
    put(OUT/'correct-summary.json',dict(status='PASS',prior_pairs=65,control_pairs=2,physical_settles=134,direct_tick_invocations=36,settle_ticks=sum(x['ticks'] for x in totals),exp_baseline=sum(x['baseline_exp_calls'] for x in totals),exp_once=sum(x['exp_once_exp_calls'] for x in totals),negative_updates=sum(x['negative_updates'] for x in totals),max_scalar_error=max(x['max_scalar_error'] for x in totals),direct=dd,normal_exception_nested_restoration=True,parts=parts,local_native_calls=0))

def work():
    from tools.r32_semantic_join.runtime import lower
    from tools.r43_exp_once.runtime import run
    from tools.r38_shared_witness.recording import Recorder,work_writer
    import tools.r34_feasible_state.probe as storage
    p=inputs();write=work_writer(OUT,p);storage.OUT=OUT;started=time.process_time();sources={x['key']:lower(x['observation'],x['predicate'],p['kernel']) for x in p['sources']};write(OUT/'sources.json',sources);source_cpu=time.process_time()-started
    stores={key:Recorder(p) for key in p['store_offsets']};batch=[];metrics=[];part=0;computed=completed=0;success=False;inflight=None;w=p['workloads'][0];cells=[('native_joint','baseline'),('native_joint','exp_once'),('native_factor','baseline'),('native_factor','exp_once'),('exact_joint','baseline')]
    try:
        for rep in range(3):
            for ci,c in enumerate(p['cases']):
                first=(ci+rep)%5
                for arm,mode in cells[first:]+cells[:first]:
                    inflight=dict(case=c['key'],repetition=rep,workload='q4',arm=arm,mode=mode);r,metric=run(c,w,arm,mode,p,sources);computed+=r['native_calls'];cpu=time.process_time();wall=time.perf_counter();r.update(inflight);refs=[]
                    if arm!='exact_joint':
                        key=arm+'/'+mode;rec=stores[key];offset=p['store_offsets'][key]
                        def writer(path,data,metadata=False):write(OUT/('n%04d.json'%(offset+int(path.stem[1:]))),data,metadata)
                        storage.put=writer
                        for k in r.pop('networks'):
                            local=rec.add(k);refs.append('n%04d'%(offset+int(local[1:])));require(sum(x.cached_bytes for x in stores.values())<=p['budget']['canonical_cache_bytes'],'aggregate four-store byte stop')
                    r['network_ids']=refs;scpu=time.process_time()-cpu;swall=time.perf_counter()-wall;batch.append(r);metrics.append(dict(inflight,**metric,storage_cpu_seconds=scpu,storage_wall_seconds=swall));completed+=1;inflight=None
                    if len(batch)==80:write(OUT/('batch%02d.json'%part),batch);write(OUT/('metrics%02d.json'%part),metrics);batch=[];metrics=[];part+=1
        require(not batch and part==6 and computed==sum(x.calls for x in stores.values())==34560 and completed==480,'complete physical workload');success=True
    finally:
        write(OUT/'work-ledger.json',dict(completed=success,physical_numeric_calls=computed,source_calls=24,source_cpu_seconds=source_cpu,metric_parts=part,completed_evaluations=completed,per_store={key:dict(calls=x.calls,unique_trace_records=len(x.cache),canonical_cache_bytes=x.cached_bytes,maximum_canonical_record_bytes=x.peak_record_bytes,offset=p['store_offsets'][key]) for key,x in stores.items()},aggregate_cache_bytes=sum(x.cached_bytes for x in stores.values()),computation_reused=False,trace_storage_only_shared=True,timing_exp_probes=0,inflight=inflight),metadata=True)
        if not success and batch:write(OUT/'partial-completed.json',dict(records=batch,metrics=metrics),metadata=True)

def audit_all():
    from tools.r43_exp_once.verify import SavedNetworks,audit,pairs,summarize,mutations,counted_pair,direct_checks
    from tools.r43_exp_once.runtime import opportunity,canonical
    from tools.r32_semantic_join.runtime import export
    from tools.r32_semantic_join.verify import audit_lower
    p=inputs();networks=SavedNetworks(OUT,p);error=networks.verify_all();sources=read(OUT/'sources.json');packets={k:export(v) for k,v in sources.items()};low=[audit_lower(sources[x['key']],x,p) for x in p['sources']];records=[r for i in range(6) for r in read(OUT/('batch%02d.json'%i))];metrics=[m for i in range(6) for m in read(OUT/('metrics%02d.json'%i))];cases={c['key']:c for c in p['cases']};rows=[];timing=[]
    for r,m in zip(records,metrics,strict=True):
        require(all(r[k]==m[k] for k in ['case','workload','repetition','arm','mode']) and m['restored'] is True and m['exp_probe'] is False and m['builtin_exp_unprobed'] is True and m['tick_variant_verified'] is True,'unprobed timing identity/restore');cpu=time.process_time();wall=time.perf_counter();rows.append(audit(r,cases[r['case']],packets,p,networks));timing.append(dict(case=r['case'],workload='q4',repetition=r['repetition'],arm=r['arm'],mode=r['mode'],audit_cpu_seconds=time.process_time()-cpu,audit_wall_seconds=time.perf_counter()-wall))
    counted=[r for i in range(13) for r in read(OUT/('correct%02d.json'%i))];controls=read(OUT/'correct-controls.json');correct=[counted_pair(r,p) for r in counted+controls];dd=direct_checks(read(OUT/'direct-ticks.json'),p)
    hashes={__import__('hashlib').sha256(canonical(r['baseline']['kernel'],p['kernel'])).hexdigest() for r in counted};require(all(__import__('hashlib').sha256(canonical(networks[n],p['kernel'])).hexdigest() in hashes for n in networks),'all timing kernels covered by directly counted inputs')
    paired=pairs(records,networks,p);rr=next(r for r in records if r['arm']=='native_factor' and r['mode']=='exp_once' and cases[r['case']]['r_mask']==cases[r['case']]['u_mask']==6 and cases[r['case']]['s_mask']==9);rejected=mutations(rr,cases[rr['case']],packets,p,networks,records,counted[0]);calls=24+sum(r['physical_native_calls'] for r in rows)+134;ticks=sum(r['ticks'] for r in rows)+sum(x['ticks'] for x in low)+sum(x['ticks'] for x in correct)+36
    require(calls==34718 and ticks<=5554916 and len(records)==480 and len(paired)==192,'total physical caps')
    op={n:opportunity(networks[n],p['kernel']) for n in networks}
    put(OUT/'audit-metrics.json',timing);put(OUT/'summary.json',dict(status='AUDITED',**summarize(rows),paired_records=paired,sources=low,unique_traces=len(networks),physical_calls=calls,ticks=ticks,settle_ticks=ticks-36,direct_tick_invocations=36,max_scalar_error=max(error,max(x['numeric_replay_max_absolute_error'] for x in low),max(x['max_scalar_error'] for x in correct)),mutation_rejections=rejected,correctness=dict(pairs=65,control_pairs=2,settles=134,direct=dd,exp_baseline=sum(x['baseline_exp_calls'] for x in correct),exp_once=sum(x['exp_once_exp_calls'] for x in correct)),timing_exp_calls_derived_from_directly_counted_unique_kernels={key:dict(baseline=sum(op[n]['baseline_exp_calls'] for r in records if r['arm']+'/'+r['mode']==key for n in r['network_ids']),exp_once=sum(op[n]['exp_once_exp_calls'] for r in records if r['arm']+'/'+r['mode']==key for n in r['network_ids'])) for key in p['store_offsets']},learning=0,world_measurement=0,production_adoption=False,clock=vars(time.get_clock_info('process_time'))))

def run(started):
    import resource,signal,subprocess,traceback,zipfile
    p=inputs();limits=p['limits'];OUT.mkdir(parents=True,exist_ok=False);deadline=started+limits['total_seconds']-30;stages=[];failure=None;manifest=read(ROOT/'source_manifest.json')
    def terminate(signum,frame):raise TimeoutError('termination signal '+str(signum))
    signal.signal(signal.SIGTERM,terminate)
    def source_check():return {n:(ROOT/n).is_file() and sha(ROOT/n)==h for n,h in manifest.items()}
    def limit():resource.setrlimit(resource.RLIMIT_AS,(limits['child_address_space_bytes'],)*2);resource.setrlimit(resource.RLIMIT_FSIZE,(limits['child_file_bytes'],)*2)
    try:
        require(all(source_check().values()),'source preflight')
        for phase in ['preparation','correctness','work','audit']:
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
    a=argparse.ArgumentParser();a.add_argument('--phase',required=True,choices=['run','preparation','correctness','work','audit']);a.add_argument('--started',type=float);args=a.parse_args()
    from hcr.tasks.toy_world import World
    def forbidden(*a,**k):raise ValueError('R43 world measurement forbidden')
    World.measure=forbidden
    if args.phase=='run':run(args.started or time.monotonic())
    else:
        import resource
        try:
            if args.phase=='preparation':preparation()
            elif args.phase=='correctness':correctness()
            elif args.phase=='work':work()
            else:audit_all()
        finally:
            u=resource.getrusage(resource.RUSAGE_SELF)
            put(OUT/(args.phase+'-resources.json'),dict(platform=sys.platform,ru_maxrss_raw=u.ru_maxrss,ru_maxrss_units='platform-native getrusage; no conversion asserted',user_cpu_seconds=u.ru_utime,system_cpu_seconds=u.ru_stime))
