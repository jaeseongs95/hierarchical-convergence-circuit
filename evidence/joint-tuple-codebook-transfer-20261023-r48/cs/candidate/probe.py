"""Frozen 8-token 2-variable joint-tuple codebook intervention and 809-settle 6-stage continuous transfer probe around unchanged R37 inference."""
import argparse,ast,itertools,json,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from tools.r19_cross_level.probe import read,put,sha,require
SPEC=ROOT/'experiments/exp-94-joint-tuple-codebook-transfer/frozen_spec.json';OUT=ROOT/'runs/technical'

def inputs():
    p=read(SPEC);require(all(sha(ROOT/n)==h for n,h in read(SPEC.with_name('input_manifest.json')).items()),'input SHA pins');return p

def run_stage_transfer(p,cfg,kernel_fn,onehot_fn,add_fn):
    role=[];rep_pairs={0:(0,0),1:(0,1),2:(0,3),3:(0,7)};role_goals={}
    for x,y in itertools.product(range(8),repeat=2):
        drives={s+str(i):cfg.evidence_gain*(1 if (v>>i)&1 else -1) for s,v in [('x',x),('y',y)] for i in range(3)}
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
    mf_min=min(m_false);mf_max=max(m_false);mt_min=min(m_true);mt_max=max(m_true)
    projection_envelope=[];proj_true=[];proj_false=[]
    for order in [0,1]:
        doc=p['programs']['projection'+str(order)]
        layout=[[0,0],[0,1],[1,0],[1,1]] if order==0 else [[1,1],[1,0],[0,1],[0,0]]
        for bits in itertools.product([False,True],repeat=4):
            f_bool=list(bits)
            f_in=[mt_min if b else mf_max for b in f_bool]
            drives={'f'+str(i):cfg.evidence_gain*(2*f_in[i]-1) for i in range(4)}
            k=kernel_fn(doc,drives,cfg,.5);nid=add_fn(k)
            act={tuple(layout[i]) for i,b in enumerate(f_bool) if b}
            xs={x for x,y in act};ys={y for x,y in act}
            exp_e=[(layout[i][0] in xs and layout[i][1] in ys) for i in range(4)]
            p_state={pk:k['state'][pk] for pk in ['p00','p01','p10','p11']}
            e_out=[k['state']['e'+str(i)] for i in range(4)]
            for b_flag,ev in zip(exp_e,e_out,strict=True):
                if b_flag:proj_true.append(ev)
                else:proj_false.append(ev)
            projection_envelope.append(dict(order=order,f_bool=f_bool,f_in=f_in,expected_e=exp_e,p_state=p_state,e_out=e_out,goal=k['state']['goal'],adopted=k['adopted'],ticks=k['cost']['kernel_ticks'],network_id=nid))
    require(len(projection_envelope)==32 and proj_true and proj_false,'32 projection0/1 extremal settles')
    pf_min=min(proj_false);pf_max=max(proj_false);pt_min=min(proj_true);pt_max=max(proj_true)
    feasible_envelope=[];ef_all=[];et_all=[];cf_all=[];ct_all=[]
    for src,(f_hi,t_lo) in [('direct_or',(mf_max,mt_min)),('via_projection',(pf_max,pt_min))]:
        for bits in itertools.product([False,True],repeat=5):
            e_bool=list(bits[:4]);comp_bool=bits[4]
            e_in=[t_lo if b else f_hi for b in e_bool]
            drives={'e'+str(i):cfg.evidence_gain*(2*e_in[i]-1) for i in range(4)}
            drives['complete']=cfg.evidence_gain*(1 if comp_bool else -1)
            k=kernel_fn(p['programs']['feasible'],drives,cfg,.5);nid=add_fn(k)
            kind=onehot_fn(k,['none','unique','many','incomplete'],cfg.margin_threshold)
            el=[k['state']['e'+str(i)] for i in range(4)];cov=k['state']['complete']
            for b_flag,ev in zip(e_bool,el,strict=True):
                if b_flag:et_all.append(ev)
                else:ef_all.append(ev)
            if comp_bool:ct_all.append(cov)
            else:cf_all.append(cov)
            feasible_envelope.append(dict(source_kind=src,e_bool=e_bool,complete_bool=comp_bool,e_in=e_in,complete_in=1.0 if comp_bool else 0.0,kind=kind,eligibility=el,coverage_activation=cov,ticks=k['cost']['kernel_ticks'],network_id=nid))
    require(len(feasible_envelope)==64,'64 feasible4 extremal settles')
    ef_min=min(ef_all);ef_max=max(ef_all);et_min=min(et_all);et_max=max(et_all)
    cf_min=min(cf_all);cf_max=max(cf_all);ct_min=min(ct_all);ct_max=max(ct_all)
    query_envelope=[]
    for bits in itertools.product([False,True],repeat=9):
        e_bool=list(bits[:4]);t_bool=list(bits[4:8]);comp_bool=bits[8]
        e_in=[et_min if b else ef_max for b in e_bool]
        t_in=[mt_min if b else mf_max for b in t_bool]
        c_in=ct_min if comp_bool else cf_max
        drives={'e'+str(i):cfg.evidence_gain*(2*e_in[i]-1) for i in range(4)}
        drives.update({'t'+str(i):cfg.evidence_gain*(2*t_in[i]-1) for i in range(4)})
        drives['complete']=cfg.evidence_gain*(2*c_in-1)
        k=kernel_fn(p['programs']['query'],drives,cfg,.5);nid=add_fn(k)
        qtag=onehot_fn(k,['qtrue','qfalse','empty','mixed','incomplete'],cfg.margin_threshold)
        query_envelope.append(dict(e_bool=e_bool,t_bool=t_bool,complete_bool=comp_bool,e_in=e_in,t_in=t_in,complete_in=c_in,tag=qtag,ticks=k['cost']['kernel_ticks'],network_id=nid))
    require(len(query_envelope)==512,'512 query4 extremal settles')
    transfer=dict(
        role_representatives=role_goals,
        pair_transfer=pair_transfer,
        pair_bounds=dict(false_min=min(pair_false),false_max=max(pair_false),true_val=pair_true[0]),
        or_transfer=or_transfer,
        membership_bounds=dict(false_min=mf_min,false_max=mf_max,true_min=mt_min,true_max=mt_max),
        projection_envelope=projection_envelope,
        projection_bounds=dict(false_min=pf_min,false_max=pf_max,true_min=pt_min,true_max=pt_max),
        feasible_envelope=feasible_envelope,
        eligibility_bounds=dict(false_min=ef_min,false_max=ef_max,true_min=et_min,true_max=et_max,cov_false_min=cf_min,cov_false_max=cf_max,cov_true_min=ct_min,cov_true_max=ct_max),
        query_envelope=query_envelope
    )
    return role,transfer

def preparation():
    from hcr.model import Config
    from tools.r33_typed_feedback.runtime import program
    from tools.r34_feasible_state.runtime import onehot
    import tools.r37_joint_tuple.runtime as r37_rt
    from tools.r37_joint_tuple.verify import oracle
    from tools.r48_joint_tuple_codebook_transfer.verify import validate_map,check_matrix_coverage,audit,role_audit,transfer_audit,verify_regime_and_signature_coverage,run_mutation_suite
    p=inputs();cfg=Config(**p['kernel']);require(p['programs']==r37_rt.documents(cfg),'syntax/count generator preserved');checks=0
    for doc in p['programs'].values():program(doc).validate(cfg)
    require(len(p['sources'])==112 and len(p['cases'])==256 and len({c['base_key'] for c in p['cases']})==32,'matrix/source/base count')
    tree=ast.parse((ROOT/'tools/r37_joint_tuple/runtime.py').read_text(encoding='utf-8'));fns={x.name:x for x in tree.body if isinstance(x,ast.FunctionDef)}
    require([x.arg for x in fns['consume_t'].args.args]==['binding','t','vocabulary','cfg','docs','initial'],'isolated consumer signature r37_joint_tuple')
    require([x.arg for x in fns['promote'].args.args]==['domains','alternatives','facts','k','cfg','representation'],'target-independent producer promotion signature')
    desc={s['key']:dict(predicate=s['predicate'],subject=s['observation']['start'],object=s['observation']['goal']) for s in p['sources']}
    cov_summary=check_matrix_coverage(p,desc)
    by_base={}
    for c in p['cases']:
        validate_map(c,p)
        base=by_base.setdefault(c['base_key'],c)
        require({k:v for k,v in c.items() if k not in ['key','map_name','code_map','vocabulary']}=={k:v for k,v in base.items() if k not in ['key','map_name','code_map','vocabulary']},'only map metadata/vocabulary changed')
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
    stub_nets={};calls=0;orig_kernel=r37_rt.kernel
    def stub(doc,drives,cfg_obj,initial):
        nonlocal calls
        calls+=1
        bstate=boolean(doc,{k:v>0 for k,v in drives.items()})
        state={k:(0.99 if v else 0.01) for k,v in bstate.items()}
        if doc==p['programs']['role']:
            d=sum((drives['x'+str(i)]>0)!=(drives['y'+str(i)]>0) for i in range(3))
            state['goal']={0:0.992,1:0.008,2:0.0004,3:0.00002}[d]
        elif drives:
            eps=1e-6*sum(drives[k] for k in sorted(drives))
            for k in state:
                state[k]=(0.99+eps) if bstate[k] else (0.01+eps)
        return dict(program=doc,drives=dict(drives),initial={g['id']:initial for g in doc['groups']},state=state,adopted=state['goal']>.5,convergence=dict(status='stable_decision'),cost=dict(kernel_ticks=30,group_updates=120,signal_transmissions=240))
    def add_stub(k):
        nid='s%05d'%len(stub_nets);stub_nets[nid]=k;return nid
    r37_rt.kernel=stub
    mock_records=[];marg_strict=marg_closure=0
    try:
        role_mock,transfer_mock=run_stage_transfer(p,cfg,stub,onehot,add_stub)
        require(calls==809,'809 stage-transfer settles in Boolean stub')
        for c in p['cases']:
            ctx=[stub_packets[k] for k in c['context']];t=[stub_packets[k] for k in c['T']]
            truth=oracle(c['alternatives'],ctx,t,False);closure=oracle(c['alternatives'],ctx,t,True)
            for arm in c['arms']:
                r=r37_rt.execute(c['domains'],c['alternatives'],ctx,t,c['vocabulary'],arm,p['kernel'],c['initial'])
                r.update(case=c['key'],base_key=c['base_key'],map_name=c['map_name'],part=c['part'],order=c['order'],namespace=c['namespace'],arm=arm)
                r['network_ids']=[] if arm=='exact_joint' else [add_stub(k) for k in r.pop('networks')]
                mock_records.append(r)
                target=closure if arm=='native_marginal' else truth
                require(all(r[k]==target[k] for k in ['kind','selected_index','value','reason']),'Boolean stub oracle match '+arm)
                if arm=='native_marginal':
                    marg_strict+=int(all(r[k]==truth[k] for k in ['kind','selected_index','value','reason']))
                    marg_closure+=int(all(r[k]==closure[k] for k in ['kind','selected_index','value','reason']))
    finally:
        r37_rt.kernel=orig_kernel
    require(calls==33641 and len(mock_records)==768 and marg_strict==128 and marg_closure==256,'declared 33641 recorded settles, 768 evaluations, and 128/256 marginal split')
    cases_map={c['key']:c for c in p['cases']}
    # R47 mandatory guard: run full unmutated audit, role_audit, transfer_audit, and regime check BEFORE mutation suite
    rows_mock=[audit(r,cases_map[r['case']],stub_packets,p,stub_nets) for r in mock_records]
    cov_mock,rep_goals_mock=role_audit(role_mock,stub_nets,p)
    tr_summary_mock=transfer_audit(transfer_mock,rep_goals_mock,stub_nets,p)
    regime_mock=verify_regime_and_signature_coverage(rows_mock)
    require(len(rows_mock)==768 and cov_mock['wrong']==0 and tr_summary_mock['total_stage_transfer_settles']==809,'unmutated full audit precheck passed')
    pre_rejected=run_mutation_suite(mock_records,cases_map,stub_packets,p,stub_nets,desc,role_mock,transfer_mock,rep_goals_mock)
    require(len(pre_rejected)==25,'all 25 mutations pre-verified in preparation')
    allmaps=pairchecks=0
    for mp in itertools.permutations(range(8)):
        require(len(set(mp))==8,'bijection enumeration');allmaps+=1
        for x,y in itertools.product(range(8),repeat=2):require((mp[x]==mp[y])==(x==y),'symbolic bijection equality');pairchecks+=1
    require(allmaps==40320 and pairchecks==2580480,'finite role domain')
    put(OUT/'preparation.json',dict(status='PASS',checks=checks,native_calls=0,simulated_recorded_invocations=calls,expected_marginal_full_strict=marg_strict,expected_marginal_closure_strict=marg_closure,matrix_coverage=cov_summary,regime_precheck=regime_mock,symbolic_maps=allmaps,symbolic_pairchecks=pairchecks,preverified_mutation_rejections=pre_rejected,not_native_semantic_evidence=True))

def work():
    from hcr.model import Config,fingerprint
    from tools.r32_semantic_join.runtime import lower,export
    from tools.r33_typed_feedback.runtime import kernel
    from tools.r34_feasible_state.runtime import onehot
    from tools.r38_shared_witness.recording import Recorder,work_writer
    import tools.r34_feasible_state.probe as storage
    import tools.r37_joint_tuple.runtime as r37_rt
    p=inputs();write=work_writer(OUT,p);storage.OUT=OUT;storage.put=write;cfg=Config(**p['kernel']);start=time.process_time();sources={s['key']:lower(s['observation'],s['predicate'],p['kernel']) for s in p['sources']};write(OUT/'sources.json',sources);source_cpu=time.process_time()-start;rec=Recorder(p)
    def add(k):
        n=rec.add(k);require(rec.cached_bytes<=p['budget']['canonical_cache_bytes'],'aggregate canonical cache stop');return n
    t0=time.process_time();role,transfer=run_stage_transfer(p,cfg,kernel,onehot,add);transfer_cpu=time.process_time()-t0
    write(OUT/'roles.json',role);write(OUT/'transfer.json',transfer)
    require(rec.calls==809,'809 stage-transfer settles recorded')
    batch=[];metrics=[];part=0;computed=809;completed=0;success=False;inflight=None
    try:
        for c in p['cases']:
            needed=c['context']+c['T'];packets={k:export(sources[k]) for k in needed};require(all(packets[k]['origin_sha256']==fingerprint(sources[k]) for k in packets),'source export guard')
            ctx=[packets[k] for k in c['context']];t=[packets[k] for k in c['T']]
            for arm in c['arms']:
                inflight=dict(case=c['key'],arm=arm);cpu=time.process_time();wall=time.perf_counter()
                r=r37_rt.execute(c['domains'],c['alternatives'],ctx,t,c['vocabulary'],arm,p['kernel'],c['initial'])
                computed+=r['native_calls'];core=time.process_time()-cpu;store=time.process_time()
                r.update(inflight,map_name=c['map_name'],base_key=c['base_key'],part=c['part'],order=c['order'],namespace=c['namespace'])
                r['network_ids']=[] if arm=='exact_joint' else [add(k) for k in r.pop('networks')]
                batch.append(r);metrics.append(dict(inflight,core_cpu_seconds=core,storage_cpu_seconds=time.process_time()-store,wall_seconds=time.perf_counter()-wall));completed+=1;inflight=None
                if len(batch)==64:write(OUT/('batch%02d.json'%part),batch);write(OUT/('metrics%02d.json'%part),metrics);part+=1;batch=[];metrics=[]
        require(not batch and part==12 and computed==rec.calls==33641 and completed==768,'complete frozen work');success=True
    finally:
        if batch:write(OUT/('batch%02d.partial.json'%part),batch,metadata=True);write(OUT/('metrics%02d.partial.json'%part),metrics,metadata=True)
        write(OUT/'work-ledger.json',dict(completed=success,completed_evaluations=completed,planned_evaluations=768,inflight=inflight,physical_recorded_calls=rec.calls,upper_calls=computed-809,role_calls=64,pair_transfer_calls=16,or_transfer_calls=121,projection_envelope_calls=32,feasible4_envelope_calls=64,query4_envelope_calls=512,stage_transfer_calls=809,source_calls=112,total_physical_calls=rec.calls+112,unique_traces=len(rec.cache),aggregate_cache_bytes=rec.cached_bytes,max_record_bytes=rec.peak_record_bytes,computation_reused=False,trace_storage_only_shared=True,source_cpu_seconds=source_cpu,stage_transfer_cpu_seconds=transfer_cpu),metadata=True)

def audit_all():
    from tools.r48_joint_tuple_codebook_transfer.verify import bundle
    summary,_=bundle(OUT,inputs());put(OUT/'summary.json',summary)

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
            v=resource.getrusage(resource.RUSAGE_CHILDREN);raw=sum(f.stat().st_size for f in OUT.iterdir() if f.is_file())
            stages.append(dict(phase=phase,returncode=rc,wall_seconds=time.monotonic()-before,cpu_seconds=v.ru_utime+v.ru_stime-u.ru_utime-u.ru_stime,user_cpu_seconds=v.ru_utime-u.ru_utime,system_cpu_seconds=v.ru_stime-u.ru_stime,ru_maxrss_raw=v.ru_maxrss,raw_bytes=raw))
            require(rc==0 and raw<=limits['raw_bytes'],'stage/cap failure '+phase)
    except BaseException:failure=traceback.format_exc()
    finally:
        post=source_check();put(OUT/'source-postcheck.json',dict(unchanged=all(post.values()),files=post))
        if not all(post.values()):failure=(failure or '')+'\nsource postcheck failed'
        if failure:put(OUT/'failure.json',dict(traceback=failure,retry=False))
        parent=resource.getrusage(resource.RUSAGE_SELF);children=resource.getrusage(resource.RUSAGE_CHILDREN)
        put(OUT/'result.json',dict(status='FAILED' if failure else 'COMPLETED',stages=stages,source_unchanged=all(post.values()),source_manifest_sha256=sha(ROOT/'source_manifest.json'),seconds_before_seal=time.monotonic()-started,parent_cpu_seconds=parent.ru_utime+parent.ru_stime,children_cpu_seconds=children.ru_utime+children.ru_stime,parent_ru_maxrss_raw=parent.ru_maxrss,children_ru_maxrss_raw=children.ru_maxrss,python=sys.version.split()[0],platform=sys.platform,retry=False))
        put(OUT/'manifest.json',{f.name:dict(sha256=sha(f),bytes=f.stat().st_size) for f in sorted(OUT.iterdir()) if f.is_file()})
        with zipfile.ZipFile(ROOT/'evidence.zip','x',compression=zipfile.ZIP_DEFLATED) as z:
            for f in sorted(OUT.iterdir()):
                if f.is_file():z.write(f,'technical/'+f.name)
        after=resource.getrusage(resource.RUSAGE_SELF)
        put(ROOT/'completion.json',dict(completed=failure is None,seconds_including_seal=time.monotonic()-started,within_wall_limit=time.monotonic()-started<limits['total_seconds'],parent_cpu_seconds_including_seal=after.ru_utime+after.ru_stime,evidence_sha256=sha(ROOT/'evidence.zip'),evidence_bytes=(ROOT/'evidence.zip').stat().st_size))
    if failure:raise SystemExit(1)

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--phase',required=True,choices=['run','preparation','work','audit']);a.add_argument('--started',type=float);args=a.parse_args()
    from hcr.tasks.toy_world import World
    def forbidden(*a,**k):raise ValueError('R48 world measurement forbidden')
    World.measure=forbidden
    if args.phase=='run':run(args.started or time.monotonic())
    elif args.phase=='preparation':preparation()
    elif args.phase=='work':work()
    else:audit_all()
