"""Frozen 8-token 4-cohort relational codebook intervention and 6-stage continuous transfer probe around unchanged R39/R40 inference."""
import argparse,ast,itertools,json,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from tools.r19_cross_level.probe import read,put,sha,require
SPEC=ROOT/'experiments/exp-92-relational-codebook-transfer/frozen_spec.json';OUT=ROOT/'runs/technical'

def inputs():
    p=read(SPEC);require(all(sha(ROOT/n)==h for n,h in read(SPEC.with_name('input_manifest.json')).items()),'input SHA pins');return p

def run_stage_transfer(p,cfg,kernel_fn,onehot_fn,add_fn):
    role=[];rep_pairs={0:(0,0),1:(0,1),2:(0,3),3:(0,7)};role_goals={}
    for x,y in itertools.product(range(8),repeat=2):
        drives={s+str(i):cfg.evidence_gain*(1 if v>>i&1 else -1) for s,v in [('x',x),('y',y)] for i in range(3)}
        k=kernel_fn(p['programs']['role'],drives,cfg,.5);nid=add_fn(k);d=(x^y).bit_count();role.append(dict(left=x,right=y,hamming=d,network_id=nid))
        if rep_pairs[d]==(x,y):role_goals[d]=k['state']['goal']
    require(set(role_goals)=={0,1,2,3},'four Hamming representative role outputs')
    pair_transfer=[];pair_true=[];pair_false=[]
    for d0,d1 in itertools.product(range(4),repeat=2):
        drives={'m0':cfg.evidence_gain*(2*role_goals[d0]-1),'m1':cfg.evidence_gain*(2*role_goals[d1]-1),'m2':-cfg.evidence_gain}
        k=kernel_fn(p['programs']['pair'],drives,cfg,.5);nid=add_fn(k);gv=k['state']['goal'];expected=(d0==0 and d1==0)
        if expected:pair_true.append(gv)
        else:pair_false.append(gv)
        pair_transfer.append(dict(hamming_pair=[d0,d1],expected=expected,goal=gv,adopted=k['adopted'],ticks=k['cost']['kernel_ticks'],network_id=nid))
    require(len(pair_transfer)==16 and len(pair_true)==1 and len(pair_false)==15,'16 exhaustive pair settles')
    p_env=[('pfalse_min',False,min(pair_false)),('pfalse_max',False,max(pair_false)),('ptrue',True,pair_true[0])]
    or_transfer=[];m_true=[];m_false=[]
    for L in range(5):
        doc=p['programs']['or'+str(L)]
        for pts in itertools.product(p_env,repeat=L):
            tags=[pt[0] for pt in pts];bools=[pt[1] for pt in pts];vals=[pt[2] for pt in pts]
            drives={'m'+str(i):cfg.evidence_gain*(2*vals[i]-1) for i in range(L)}
            k=kernel_fn(doc,drives,cfg,.5);nid=add_fn(k);gv=k['state']['goal'];expected=any(bools)
            if expected:m_true.append(gv)
            else:m_false.append(gv)
            or_transfer.append(dict(arity=L,input_tags=tags,input_bools=bools,input_vals=vals,expected=expected,goal=gv,adopted=k['adopted'],ticks=k['cost']['kernel_ticks'],network_id=nid))
    require(len(or_transfer)==121 and m_true and m_false,'121 or0..4 extremal settles')
    m_env=[('mfalse_min',False,min(m_false)),('mfalse_max',False,max(m_false)),('mtrue_min',True,min(m_true)),('mtrue_max',True,max(m_true))]
    triple_transfer=[];s_true=[];s_false=[]
    for pts in itertools.product(m_env,repeat=3):
        tags=[pt[0] for pt in pts];bools=[pt[1] for pt in pts];vals=[pt[2] for pt in pts]
        drives={'m'+str(i):cfg.evidence_gain*(2*vals[i]-1) for i in range(3)}
        k=kernel_fn(p['programs']['triple'],drives,cfg,.5);nid=add_fn(k);gv=k['state']['goal'];expected=all(bools)
        if expected:s_true.append(gv)
        else:s_false.append(gv)
        triple_transfer.append(dict(input_tags=tags,input_bools=bools,input_vals=vals,expected=expected,goal=gv,adopted=k['adopted'],ticks=k['cost']['kernel_ticks'],network_id=nid))
    require(len(triple_transfer)==64 and s_true and s_false,'64 triple extremal settles')
    s_env=[('sfalse_min',False,min(s_false)),('sfalse_max',False,max(s_false)),('strue_min',True,min(s_true)),('strue_max',True,max(s_true))]
    projection_or2=[];xy_true=[];xy_false=[]
    for pts in itertools.product(s_env,repeat=2):
        tags=[pt[0] for pt in pts];bools=[pt[1] for pt in pts];vals=[pt[2] for pt in pts]
        drives={'m'+str(i):cfg.evidence_gain*(2*vals[i]-1) for i in range(2)}
        k=kernel_fn(p['programs']['or2'],drives,cfg,.5);nid=add_fn(k);gv=k['state']['goal'];expected=any(bools)
        if expected:xy_true.append(gv)
        else:xy_false.append(gv)
        projection_or2.append(dict(input_tags=tags,input_bools=bools,input_vals=vals,expected=expected,goal=gv,adopted=k['adopted'],ticks=k['cost']['kernel_ticks'],network_id=nid))
    projection_or4=[];z_true=[];z_false=[]
    for pts in itertools.product(s_env,repeat=4):
        tags=[pt[0] for pt in pts];bools=[pt[1] for pt in pts];vals=[pt[2] for pt in pts]
        drives={'m'+str(i):cfg.evidence_gain*(2*vals[i]-1) for i in range(4)}
        k=kernel_fn(p['programs']['or4'],drives,cfg,.5);nid=add_fn(k);gv=k['state']['goal'];expected=any(bools)
        if expected:z_true.append(gv)
        else:z_false.append(gv)
        projection_or4.append(dict(input_tags=tags,input_bools=bools,input_vals=vals,expected=expected,goal=gv,adopted=k['adopted'],ticks=k['cost']['kernel_ticks'],network_id=nid))
    require(len(projection_or2)==16 and len(projection_or4)==256,'272 projection extremal settles')
    xy_env=[('xyfalse_min',False,min(xy_false)),('xyfalse_max',False,max(xy_false)),('xytrue_min',True,min(xy_true)),('xytrue_max',True,max(xy_true))]
    z_env=[('zfalse_min',False,min(z_false)),('zfalse_max',False,max(z_false)),('ztrue_min',True,min(z_true)),('ztrue_max',True,max(z_true))]
    consumer_pair=[];cp_true=[];cp_false=[]
    for pxy,pz in itertools.product(xy_env,z_env):
        tags=[pxy[0],pz[0]];bools=[pxy[1],pz[1]];vals=[pxy[2],pz[2]]
        drives={'m0':cfg.evidence_gain*(2*vals[0]-1),'m1':cfg.evidence_gain*(2*vals[1]-1),'m2':-cfg.evidence_gain}
        k=kernel_fn(p['programs']['pair'],drives,cfg,.5);nid=add_fn(k);gv=k['state']['goal'];expected=all(bools)
        if expected:cp_true.append(gv)
        else:cp_false.append(gv)
        consumer_pair.append(dict(input_tags=tags,input_bools=bools,input_vals=vals,expected=expected,goal=gv,adopted=k['adopted'],ticks=k['cost']['kernel_ticks'],network_id=nid))
    q_false_all=s_false+z_false+cp_false;q_true_all=s_true+z_true+cp_true
    q_env=[('qfalse_min',False,min(q_false_all)),('qfalse_max',False,max(q_false_all)),('qtrue_min',True,min(q_true_all)),('qtrue_max',True,max(q_true_all))]
    feasible_envelope=[];elig_true=[];elig_false=[];cov_vals=[]
    for (n0,b0,v0),(n1,b1,v1) in itertools.product(q_env,repeat=2):
        drives={'e0':cfg.evidence_gain*(2*v0-1),'e1':cfg.evidence_gain*(2*v1-1),'complete':cfg.evidence_gain}
        k=kernel_fn(p['programs']['feasible'],drives,cfg,.5);nid=add_fn(k);kind=onehot_fn(k,['none','unique','many','incomplete'],cfg.margin_threshold)
        el=[k['state']['e0'],k['state']['e1']];cov_vals.append(k['state']['complete'])
        for b_flag,ev in [(b0,el[0]),(b1,el[1])]:
            if b_flag:elig_true.append(ev)
            else:elig_false.append(ev)
        feasible_envelope.append(dict(left_tag=n0,right_tag=n1,left_bool=b0,right_bool=b1,left_in=v0,right_in=v1,kind=kind,eligibility=el,coverage_activation=k['state']['complete'],ticks=k['cost']['kernel_ticks'],network_id=nid))
    require(len(consumer_pair)==16 and len(feasible_envelope)==16,'32 consume extremal settles')
    transfer=dict(
        role_representatives=role_goals,
        pair_transfer=pair_transfer,
        pair_bounds=dict(false_min=min(pair_false),false_max=max(pair_false),true_val=pair_true[0]),
        or_transfer=or_transfer,
        membership_bounds=dict(false_min=min(m_false),false_max=max(m_false),true_min=min(m_true),true_max=max(m_true)),
        triple_transfer=triple_transfer,
        slice_bounds=dict(false_min=min(s_false),false_max=max(s_false),true_min=min(s_true),true_max=max(s_true)),
        projection_or2=projection_or2,
        xy_bounds=dict(false_min=min(xy_false),false_max=max(xy_false),true_min=min(xy_true),true_max=max(xy_true)),
        projection_or4=projection_or4,
        z_bounds=dict(false_min=min(z_false),false_max=max(z_false),true_min=min(z_true),true_max=max(z_true)),
        consumer_pair=consumer_pair,
        query_input_bounds=dict(false_min=min(q_false_all),false_max=max(q_false_all),true_min=min(q_true_all),true_max=max(q_true_all)),
        feasible_envelope=feasible_envelope,
        eligibility_bounds=dict(false_min=min(elig_false),false_max=max(elig_false),true_min=min(elig_true),true_max=max(elig_true),coverage_min=min(cov_vals),coverage_max=max(cov_vals))
    )
    return role,transfer

def preparation():
    from copy import deepcopy
    from hcr.model import Config,fingerprint
    from tools.r33_typed_feedback.runtime import program
    from tools.r34_feasible_state.runtime import onehot
    import tools.r37_joint_tuple.runtime as r37_rt
    import tools.r39_z_query.runtime as r39_rt
    import tools.r40_factor_query.runtime as r40_rt
    from tools.r39_z_query.verify import oracle
    from tools.r46_relational_codebook_transfer.verify import validate_map,check_matrix_coverage,run_mutation_suite
    p=inputs();cfg=Config(**p['kernel']);require(p['programs']==r39_rt.documents(cfg),'syntax/count generator preserved')
    for doc in p['programs'].values():program(doc).validate(cfg)
    require(len(p['sources'])==48 and len(p['cohorts'])==4 and len(p['cases'])==128 and len({c['base_key'] for c in p['cases']})==16,'matrix/source/cohort count')
    for name in ['r39_z_query','r40_factor_query']:
        tree=ast.parse((ROOT/'tools'/name/'runtime.py').read_text(encoding='utf-8'));fns={x.name:x for x in tree.body if isinstance(x,ast.FunctionDef)}
        require([x.arg for x in fns['consume'].args.args]==['payload','query','representation','cfg','docs','initial'],'isolated numeric consumer signature '+name)
        require('queries' not in [x.arg for x in fns['produce'].args.args] and 'query' not in [x.arg for x in fns['produce'].args.args],'query-independent producer '+name)
    desc={s['key']:dict(predicate=s['predicate'],subject=s['observation']['start'],object=s['observation']['goal']) for s in p['sources']}
    cov_summary=check_matrix_coverage(p,desc)
    by_base={};checks=0
    for c in p['cases']:
        validate_map(c,p)
        base=by_base.setdefault(c['base_key'],c)
        require({k:v for k,v in c.items() if k not in ['key','map_name','code_map','vocabulary']}=={k:v for k,v in base.items() if k not in ['key','map_name','code_map','vocabulary']},'only map metadata/vocabulary changed')
        require(c['queries']==[dict(kind='conditional',slot=i if not c['order'] else 3-i) for i in range(4)]+[dict(kind='unary',slot=None)],'r39 query normalization')
        require(c['queries_canonical']==[dict(kind='conditional',slot=i) for i in range(4)]+[dict(kind='unary',slot=None)],'r40 canonical query list')
        checks+=1
    def boolean(doc,features):
        state=dict(features)
        for g in doc['groups']:
            name=g['id']
            if name in state:continue
            terms=[state[e['source']] if e['weight']>0 else not state[e['source']] for e in doc['links'] if e['kind']=='support' and e['target']==name]
            state[name]=(all(terms) if g['bias']<0 else any(terms)) if terms else g['bias']>0
        return state
    stub_packets={s['key']:dict(schema='hcr-r32-relation-v1',predicate=s['predicate'],subject=s['observation']['start'],object=s['observation']['goal'],revision=0,confidence=.99,value=True,origin_sha256=s['key'],observation_sha256=s['key'],proof_sha256=s['key'],config_sha256=s['key']) for s in p['sources']}
    stub_nets={};calls=0
    orig_37=r37_rt.kernel;orig_39=r39_rt.kernel;orig_40=r40_rt.kernel
    def stub(doc,drives,cfg_obj,initial):
        nonlocal calls
        calls+=1
        bstate=boolean(doc,{k:v>0 for k,v in drives.items()})
        state={k:(0.99 if v else 0.01) for k,v in bstate.items()}
        if doc==p['programs']['role']:
            d=sum((drives['x'+str(i)]>0)!=(drives['y'+str(i)]>0) for i in range(3))
            state['goal']={0:0.992,1:0.008,2:0.0004,3:0.00002}[d]
        elif 'goal' in state and drives:
            eps=1e-6*sum(drives[k] for k in sorted(drives))
            state['goal']=(0.99+eps) if bstate['goal'] else (0.01+eps)
        return dict(program=doc,drives=dict(drives),initial={g['id']:initial for g in doc['groups']},state=state,adopted=state['goal']>.5,convergence=dict(status='stable_decision'),cost=dict(kernel_ticks=30,group_updates=120,signal_transmissions=240))
    def add_stub(k):
        nid='s%05d'%len(stub_nets);stub_nets[nid]=k;return nid
    r37_rt.kernel=r39_rt.kernel=r40_rt.kernel=stub
    mock_records=[];compact_strict=compact_closure=0
    try:
        role_mock,transfer_mock=run_stage_transfer(p,cfg,stub,onehot,add_stub)
        require(calls==569,'569 stage-transfer settles in Boolean stub')
        for c in p['cases']:
            rel={n:[stub_packets[k] for k in keys] for n,keys in c['relations'].items()}
            truth=oracle(c['domains'],rel,0,c['queries_canonical']);closure=oracle(c['domains'],rel,0,c['queries_canonical'],True)
            for arm in c['arms']:
                if arm=='native_factor':r=r40_rt.execute(c['domains'],rel,c['vocabulary'],c['order'],c['queries_canonical'],arm,p['kernel'],c['initial'])
                else:r=r39_rt.execute(c['domains'],rel,c['vocabulary'],c['order'],c['queries'],arm,p['kernel'],c['initial'])
                r.update(case=c['key'],base_key=c['base_key'],map_name=c['map_name'],cohort=c['cohort'],arm=arm)
                r['network_ids']=[] if arm=='exact_joint' else [add_stub(k) for k in r.pop('networks')]
                mock_records.append(r)
                target=closure if arm=='native_compact' else truth
                for i,q in enumerate(r['queries']):
                    ans=dict(kind=q['kind'],selected_index=q['selected_index'],eligible=q['eligible'] if arm=='exact_joint' else [v>.5 for v in q['eligibility']])
                    require(ans==target['answers'][i],'Boolean stub oracle match '+arm)
                    if arm=='native_compact':
                        compact_strict+=int(ans==truth['answers'][i])
                        compact_closure+=int(ans==closure['answers'][i])
    finally:
        r37_rt.kernel=orig_37;r39_rt.kernel=orig_39;r40_rt.kernel=orig_40
    require(calls==38841 and compact_strict==544 and compact_closure==640,'declared 38841 recorded settles and exact 544/640 compact split')
    cases_map={c['key']:c for c in p['cases']}
    pre_rejected=run_mutation_suite(mock_records,cases_map,stub_packets,p,stub_nets,desc,role_mock,transfer_mock,transfer_mock['role_representatives'])
    require(len(pre_rejected)==22,'all 22 mutations pre-verified in preparation')
    allmaps=pairchecks=0
    for mp in itertools.permutations(range(8)):
        require(len(set(mp))==8,'bijection enumeration');allmaps+=1
        for x,y in itertools.product(range(8),repeat=2):require((mp[x]==mp[y])==(x==y),'symbolic bijection equality');pairchecks+=1
    require(allmaps==40320 and pairchecks==2580480,'finite role domain')
    put(OUT/'preparation.json',dict(status='PASS',checks=checks,native_calls=0,simulated_recorded_invocations=calls,expected_compact_full_strict=compact_strict,expected_compact_closure_strict=compact_closure,matrix_coverage=cov_summary,symbolic_maps=allmaps,symbolic_pairchecks=pairchecks,preverified_mutation_rejections=pre_rejected,not_native_semantic_evidence=True))

def work():
    from hcr.model import Config,fingerprint
    from tools.r32_semantic_join.runtime import lower,export
    from tools.r33_typed_feedback.runtime import kernel
    from tools.r34_feasible_state.runtime import onehot
    from tools.r38_shared_witness.recording import Recorder,work_writer
    import tools.r34_feasible_state.probe as storage
    import tools.r39_z_query.runtime as r39_rt
    import tools.r40_factor_query.runtime as r40_rt
    p=inputs();write=work_writer(OUT,p);storage.OUT=OUT;storage.put=write;cfg=Config(**p['kernel']);start=time.process_time();sources={s['key']:lower(s['observation'],s['predicate'],p['kernel']) for s in p['sources']};write(OUT/'sources.json',sources);source_cpu=time.process_time()-start;rec=Recorder(p)
    def add(k):
        n=rec.add(k);require(rec.cached_bytes<=p['budget']['canonical_cache_bytes'],'aggregate canonical cache stop');return n
    t0=time.process_time();role,transfer=run_stage_transfer(p,cfg,kernel,onehot,add);transfer_cpu=time.process_time()-t0
    write(OUT/'roles.json',role);write(OUT/'transfer.json',transfer)
    batch=[];metrics=[];part=0;computed=569;completed=0;success=False;inflight=None
    try:
        for c in p['cases']:
            needed=sum(c['relations'].values(),[]);packets={k:export(sources[k]) for k in needed};require(all(packets[k]['origin_sha256']==fingerprint(sources[k]) for k in packets),'source export guard')
            rel={n:[packets[k] for k in keys] for n,keys in c['relations'].items()}
            for arm in c['arms']:
                inflight=dict(case=c['key'],arm=arm);cpu=time.process_time();wall=time.perf_counter()
                if arm=='native_factor':r=r40_rt.execute(c['domains'],rel,c['vocabulary'],c['order'],c['queries_canonical'],arm,p['kernel'],c['initial'])
                else:r=r39_rt.execute(c['domains'],rel,c['vocabulary'],c['order'],c['queries'],arm,p['kernel'],c['initial'])
                computed+=r['native_calls'];core=time.process_time()-cpu;store=time.process_time()
                r.update(inflight,map_name=c['map_name'],base_key=c['base_key'],cohort=c['cohort'])
                r['network_ids']=[] if arm=='exact_joint' else [add(k) for k in r.pop('networks')]
                batch.append(r);metrics.append(dict(inflight,core_cpu_seconds=core,storage_cpu_seconds=time.process_time()-store,wall_seconds=time.perf_counter()-wall));completed+=1;inflight=None
                if len(batch)==64:write(OUT/('batch%02d.json'%part),batch);write(OUT/('metrics%02d.json'%part),metrics);part+=1;batch=[];metrics=[]
        require(not batch and part==8 and computed==rec.calls==38841 and completed==512,'complete frozen work');success=True
    finally:
        write(OUT/'work-ledger.json',dict(completed=success,physical_recorded_calls=computed,source_calls=48,role_calls=64,stage_transfer_calls=569,upper_calls=computed-569,completed_evaluations=completed,unique_trace_records=len(rec.cache),aggregate_cache_bytes=rec.cached_bytes,maximum_canonical_record_bytes=rec.peak_record_bytes,source_cpu_seconds=source_cpu,stage_transfer_cpu_seconds=transfer_cpu,metric_parts=part,computation_reused=False,trace_storage_only_shared=True,inflight=inflight),metadata=True)
        if not success and batch:write(OUT/'partial-completed.json',dict(records=batch,metrics=metrics),metadata=True)

def audit_all():
    from tools.r46_relational_codebook_transfer.verify import bundle
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
    def forbidden(*a,**k):raise ValueError('R46 world measurement forbidden')
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
