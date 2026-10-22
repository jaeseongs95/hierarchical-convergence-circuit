"""Frozen 8-token full-space codebook intervention and stage-transfer probes around unchanged R35/R36 inference."""
import argparse,itertools,json,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from tools.r19_cross_level.probe import read,put,sha,require
SPEC=ROOT/'experiments/exp-91-codebook-transfer-coverage/frozen_spec.json';OUT=ROOT/'runs/technical'

def inputs():
    p=read(SPEC);require(all(sha(ROOT/n)==h for n,h in read(SPEC.with_name('input_manifest.json')).items()),'input SHA pins');return p

def preparation():
    from copy import deepcopy
    from hcr.model import Config
    from tools.r35_compositional_slot.compiler import documents
    from tools.r33_typed_feedback.runtime import program
    from tools.r36_overlap_composition.runtime import validate_inputs
    from tools.r45_codebook_transfer_coverage.verify import validate_map,check_matrix_coverage
    p=inputs();require(p['programs']==documents(p['expressions'],Config(**p['kernel'])),'syntax/count generator preserved')
    for doc in p['programs'].values():program(doc).validate(Config(**p['kernel']))
    require(len(p['sources'])==56 and len(p['cases'])==1024 and len({c['base_key'] for c in p['cases']})==128,'matrix/source count')
    desc={s['key']:dict(predicate=s['predicate'],subject=s['observation']['start'],object=s['observation']['goal']) for s in p['sources']}
    coverage={name:set() for name in ['C','T']};by_base={};checks=0
    for c in p['cases']:
        validate_map(c,p)
        base=by_base.setdefault(c['base_key'],c)
        require({k:v for k,v in c.items() if k not in ['key','map_name','code_map','vocabulary','arms']}=={k:v for k,v in base.items() if k not in ['key','map_name','code_map','vocabulary','arms']},'only map metadata/vocabulary changed')
        candidates=[desc[k] for k in c['candidates']];context=[desc[k] for k in c['context']];t=[desc[k] for k in c['T']];validate_inputs(candidates,context,t,c['contract'])
        require(all(desc[k][field] in c['vocabulary'] for k,field in [(k,'object') for k in c['candidates']]+[(k,'subject') for k in c['context']+c['T']]),'encoder complete token domain')
        for phase,facts in [('C',context),('T',t)]:coverage[phase].add(tuple(candidates[0]['object']==f['subject'] for f in facts))
        checks+=1
    require(all(len(v)==8 for v in coverage.values()),'actual source eight leaf patterns')
    cov_summary=check_matrix_coverage(p,desc)
    rejected=[];c=p['cases'][0]
    for name,mp in [('duplicate',[0]*8),('short',list(range(7))),('bool',[False]+list(range(1,8))),('range',list(range(7))+[8])]:
        bad=deepcopy(c);bad['code_map']=mp
        try:validate_map(bad,p)
        except ValueError:rejected.append(name)
        else:raise ValueError('accepted invalidmap '+name)
    allmaps=0;pairchecks=0
    for mp in itertools.permutations(range(8)):
        require(len(set(mp))==8,'bijection enumeration');allmaps+=1
        for x,y in itertools.product(range(8),repeat=2):require((mp[x]==mp[y])==(x==y),'symbolicbijection equality');pairchecks+=1
    require(allmaps==40320 and pairchecks==2580480,'finite role domain')
    put(OUT/'preparation.json',dict(status='PASS',checks=checks,native_calls=0,actual_source_leaf_patterns={k:[list(x) for x in sorted(v)] for k,v in coverage.items()},matrix_coverage=cov_summary,symbolic_maps=allmaps,symbolic_pairchecks=pairchecks,invalid_map_rejections=rejected,not_native_semantic_evidence=True))

def work():
    from hcr.model import Config,fingerprint
    from tools.r33_typed_feedback.runtime import kernel
    from tools.r35_compositional_slot.runtime import truth
    from tools.r34_feasible_state.runtime import onehot
    from tools.r36_overlap_composition.runtime import lower,export,execute
    from tools.r36_overlap_composition.recording import Recorder,work_writer
    import tools.r34_feasible_state.probe as storage
    p=inputs();write=work_writer(OUT,p);storage.OUT=OUT;storage.put=write;cfg=Config(**p['kernel']);start=time.process_time();sources={s['key']:lower(s['observation'],s['predicate'],p['kernel']) for s in p['sources']};write(OUT/'sources.json',sources);source_cpu=time.process_time()-start;rec=Recorder(p)
    def add(k):
        n=rec.add(k);require(rec.cached_bytes<=p['budget']['canonical_cache_bytes'],'aggregate canonical cache stop');return n
    role=[];start=time.process_time();rep_pairs={0:(0,0),1:(0,1),2:(0,3),3:(0,7)};role_goals={}
    for x,y in itertools.product(range(8),repeat=2):
        drives={s+str(i):cfg.evidence_gain*(1 if v>>i&1 else -1) for s,v in [('x',x),('y',y)] for i in range(3)};k=kernel(p['programs']['role'],drives,cfg,.5);nid=add(k);d=(x^y).bit_count();role.append(dict(left=x,right=y,hamming=d,network_id=nid))
        if rep_pairs[d]==(x,y):role_goals[d]=k['state']['goal']
    role_cpu=time.process_time()-start;write(OUT/'roles.json',role)
    require(set(role_goals)=={0,1,2,3},'four Hamming representative role outputs')
    transfer_start=time.process_time();expr_transfer=[];true_vals=[];false_vals=[]
    for expr_idx,tree in enumerate(p['expressions']):
        doc=p['programs']['expr'+str(expr_idx)]
        for d0,d1,d2 in itertools.product(range(4),repeat=3):
            drives={'m'+str(j):cfg.evidence_gain*(2*role_goals[dj]-1) for j,dj in enumerate((d0,d1,d2))}
            k=kernel(doc,drives,cfg,.5);nid=add(k);gv=k['state']['goal'];expected=truth(tree,[d0==0,d1==0,d2==0])
            if expected:true_vals.append(gv)
            else:false_vals.append(gv)
            expr_transfer.append(dict(expr=expr_idx,hamming_triple=[d0,d1,d2],expected=expected,goal=gv,adopted=k['adopted'],ticks=k['cost']['kernel_ticks'],network_id=nid))
    require(len(expr_transfer)==384 and true_vals and false_vals,'exhaustive 384 expr Hamming-triple settles')
    env_points=[
        ('false_min',False,min(false_vals)),
        ('false_max',False,max(false_vals)),
        ('true_min',True,min(true_vals)),
        ('true_max',True,max(true_vals)),
    ]
    feasible_envelope=[];elig_true=[];elig_false=[];cov_vals=[]
    f_doc=p['programs']['feasible2']
    for (n0,b0,v0),(n1,b1,v1) in itertools.product(env_points,repeat=2):
        drives={'e0':cfg.evidence_gain*(2*v0-1),'e1':cfg.evidence_gain*(2*v1-1),'complete':cfg.evidence_gain}
        k=kernel(f_doc,drives,cfg,.5);nid=add(k);kind=onehot(k,['none','unique','many','incomplete'],cfg.margin_threshold)
        el=[k['state']['e0'],k['state']['e1']];cov_vals.append(k['state']['complete'])
        for b_flag,ev in [(b0,el[0]),(b1,el[1])]:
            if b_flag:elig_true.append(ev)
            else:elig_false.append(ev)
        feasible_envelope.append(dict(left_tag=n0,right_tag=n1,left_bool=b0,right_bool=b1,left_in=v0,right_in=v1,kind=kind,eligibility=el,coverage_activation=k['state']['complete'],ticks=k['cost']['kernel_ticks'],network_id=nid))
    require(len(feasible_envelope)==16 and elig_true and elig_false,'16 feasible2 extremal settles')
    elig_points=[
        ('efalse_min',False,min(elig_false)),
        ('efalse_max',False,max(elig_false)),
        ('etrue_min',True,min(elig_true)),
        ('etrue_max',True,max(elig_true)),
    ]
    t_Patterns=[
        ('ff',(False,False),(env_points[1][2],env_points[1][2])),
        ('ft',(False,True),(env_points[1][2],env_points[2][2])),
        ('tf',(True,False),(env_points[2][2],env_points[1][2])),
        ('tt',(True,True),(env_points[2][2],env_points[2][2])),
    ]
    cov_min=min(cov_vals);q_doc=p['programs']['query2'];query_envelope=[]
    for (en0,eb0,ev0),(en1,eb1,ev1) in itertools.product(elig_points,repeat=2):
        for t_tag,(tb0,tb1),(tv0,tv1) in t_Patterns:
            drives={'e0':cfg.evidence_gain*(2*ev0-1),'e1':cfg.evidence_gain*(2*ev1-1),'t0':cfg.evidence_gain*(2*tv0-1),'t1':cfg.evidence_gain*(2*tv1-1),'complete':cfg.evidence_gain*(2*cov_min-1)}
            k=kernel(q_doc,drives,cfg,.5);nid=add(k);qtag=onehot(k,['qtrue','qfalse','empty','mixed','incomplete'],cfg.margin_threshold)
            query_envelope.append(dict(e0_tag=en0,e1_tag=en1,t_tag=t_tag,e_bool=[eb0,eb1],t_bool=[tb0,tb1],e_in=[ev0,ev1],t_in=[tv0,tv1],complete_in=cov_min,tag=qtag,ticks=k['cost']['kernel_ticks'],network_id=nid))
    require(len(query_envelope)==64,'64 query2 extremal settles')
    transfer_cpu=time.process_time()-transfer_start
    write(OUT/'transfer.json',dict(role_representatives=role_goals,expr_transfer=expr_transfer,expr_bounds=dict(false_min=min(false_vals),false_max=max(false_vals),true_min=min(true_vals),true_max=max(true_vals)),feasible_envelope=feasible_envelope,eligibility_bounds=dict(false_min=min(elig_false),false_max=max(elig_false),true_min=min(elig_true),true_max=max(elig_true),coverage_min=cov_min,coverage_max=max(cov_vals)),query_envelope=query_envelope))
    batch=[];metrics=[];part=0;computed=64+384+16+64;completed=0;success=False;inflight=None
    try:
        for c in p['cases']:
            for arm in c['arms']:
                inflight=dict(case=c['key'],arm=arm);cpu=time.process_time();wall=time.perf_counter();packets={k:export(sources[k]) for k in c['candidates']+c['context']+c['T']};require(all(packets[k]['origin_sha256']==fingerprint(sources[k]) for k in packets),'source export guard')
                r=execute([packets[k] for k in c['candidates']],[packets[k] for k in c['context']],p['expressions'][c['c_expr']],[packets[k] for k in c['T']],p['expressions'][c['t_expr']],c['contract'],c['vocabulary'],arm,p['kernel'],c['initial']);computed+=r['native_calls'];core=time.process_time()-cpu;store=time.process_time();r.update(inflight,map_name=c['map_name'],base_key=c['base_key']);r['network_ids']=[] if arm=='exact' else [add(k) for k in r.pop('networks')]
                if arm=='native':del r['binding']['alternatives'];r['binding']['alternative_keys']=c['candidates']
                batch.append(r);metrics.append(dict(inflight,core_cpu_seconds=core,storage_cpu_seconds=time.process_time()-store,wall_seconds=time.perf_counter()-wall));completed+=1;inflight=None
                if len(batch)==64:write(OUT/('batch%02d.json'%part),batch);write(OUT/('metrics%02d.json'%part),metrics);part+=1;batch=[];metrics=[]
        require(not batch and part==18 and computed==rec.calls==18960 and completed==1152,'complete frozen work');success=True
    finally:
        write(OUT/'work-ledger.json',dict(completed=success,physical_recorded_calls=computed,source_calls=56,role_calls=64,expr_transfer_calls=384,extremal_envelope_calls=80,upper_calls=computed-528,completed_evaluations=completed,unique_trace_records=len(rec.cache),aggregate_cache_bytes=rec.cached_bytes,maximum_canonical_record_bytes=rec.peak_record_bytes,source_cpu_seconds=source_cpu,role_cpu_seconds=role_cpu,transfer_cpu_seconds=transfer_cpu,metric_parts=part,computation_reused=False,trace_storage_only_shared=True,inflight=inflight),metadata=True)
        if not success and batch:write(OUT/'partial-completed.json',dict(records=batch,metrics=metrics),metadata=True)

def audit_all():
    from tools.r45_codebook_transfer_coverage.verify import bundle
    result,_=bundle(OUT,inputs());put(OUT/'summary.json',result)

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
    def forbidden(*a,**k):raise ValueError('R45 world measurement forbidden')
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
