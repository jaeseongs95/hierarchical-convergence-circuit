"""Frozen 8-token variable-capacity (n=1..4) overlapping-AST codebook intervention and 1,188-settle stage-transfer probe around unchanged R35 inference."""
import argparse,ast,itertools,json,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from tools.r19_cross_level.probe import read,put,sha,require
SPEC=ROOT/'experiments/exp-93-capacity-codebook-transfer/frozen_spec.json';OUT=ROOT/'runs/technical'

def inputs():
    p=read(SPEC);require(all(sha(ROOT/n)==h for n,h in read(SPEC.with_name('input_manifest.json')).items()),'input SHA pins');return p

def validate_inputs(candidates,context,t,contract):
    require(1<=len(candidates)<=4 and len(context)==len(t)==3,'variable candidate (1..4) and three leaf contract')
    require(len({c['object'] for c in candidates})==len(candidates),'distinct candidate tokens')
    require(all(c['predicate']=='R' and c['subject']==contract['candidate_subject'] for c in candidates),'candidate slot metadata')
    for facts,name in [(context,'C'),(t,'T')]:
        require(len(contract[name])==3,'three declared slots')
        for fact,slot in zip(facts,contract[name],strict=True):
            require(fact['predicate']==slot['predicate'] and fact['object']==slot['object'],'predicate/target slot metadata')

def execute_case(candidates,context,c_tree,t,t_tree,complete,contract,vocabulary,arm,configuration,initial):
    from hcr.model import fingerprint
    from tools.r35_compositional_slot.runtime import execute as prior_execute
    validate_inputs(candidates,context,t,contract)
    r=prior_execute(candidates,context,c_tree,t,t_tree,complete,vocabulary,arm,configuration,initial)
    r['leaf_contract_sha256']=fingerprint(contract)
    return r

def run_stage_transfer(p,cfg,kernel_fn,onehot_fn,add_fn):
    from tools.r35_compositional_slot.runtime import truth
    role=[];rep_pairs={0:(0,0),1:(0,1),2:(0,3),3:(0,7)};role_goals={}
    for x,y in itertools.product(range(8),repeat=2):
        drives={s+str(i):cfg.evidence_gain*(1 if (v>>i)&1 else -1) for s,v in [('x',x),('y',y)] for i in range(3)}
        k=kernel_fn(p['programs']['role'],drives,cfg,.5);nid=add_fn(k);d=(x^y).bit_count();role.append(dict(left=x,right=y,hamming=d,network_id=nid))
        if rep_pairs[d]==(x,y):role_goals[d]=k['state']['goal']
    require(set(role_goals)=={0,1,2,3},'four Hamming representative role outputs')
    expr_transfer=[];true_vals=[];false_vals=[]
    for expr_idx,tree in enumerate(p['expressions']):
        doc=p['programs']['expr'+str(expr_idx)]
        for d0,d1,d2 in itertools.product(range(4),repeat=3):
            drives={'m'+str(j):cfg.evidence_gain*(2*role_goals[dj]-1) for j,dj in enumerate((d0,d1,d2))}
            k=kernel_fn(doc,drives,cfg,.5);nid=add_fn(k);gv=k['state']['goal'];expected=truth(tree,[d0==0,d1==0,d2==0])
            if expected:true_vals.append(gv)
            else:false_vals.append(gv)
            expr_transfer.append(dict(expr=expr_idx,hamming_triple=[d0,d1,d2],expected=expected,goal=gv,adopted=k['adopted'],ticks=k['cost']['kernel_ticks'],network_id=nid))
    require(len(expr_transfer)==384 and true_vals and false_vals,'exhaustive 384 expr Hamming-triple settles')
    expr_false_min=min(false_vals);expr_false_max=max(false_vals)
    expr_true_min=min(true_vals);expr_true_max=max(true_vals)
    feasible_envelope=[];elig_bounds_by_n={};all_elig_false=[];all_elig_true=[];all_cov_false=[];all_cov_true=[]
    for n in range(1,5):
        f_doc=p['programs']['feasible'+str(n)]
        ef=[];et=[];cf=[];ct=[]
        for bits in itertools.product([False,True],repeat=n+1):
            e_bool=list(bits[:n]);comp_bool=bits[n]
            e_in=[expr_true_min if b else expr_false_max for b in e_bool]
            drives={'e'+str(i):cfg.evidence_gain*(2*e_in[i]-1) for i in range(n)}
            drives['complete']=cfg.evidence_gain*(1 if comp_bool else -1)
            k=kernel_fn(f_doc,drives,cfg,.5);nid=add_fn(k)
            kind=onehot_fn(k,['none','unique','many','incomplete'],cfg.margin_threshold)
            el=[k['state']['e'+str(i)] for i in range(n)];cov=k['state']['complete']
            for b_flag,ev in zip(e_bool,el,strict=True):
                if b_flag:et.append(ev);all_elig_true.append(ev)
                else:ef.append(ev);all_elig_false.append(ev)
            if comp_bool:ct.append(cov);all_cov_true.append(cov)
            else:cf.append(cov);all_cov_false.append(cov)
            feasible_envelope.append(dict(capacity=n,e_bool=e_bool,complete_bool=comp_bool,e_in=e_in,complete_in=1.0 if comp_bool else 0.0,kind=kind,eligibility=el,coverage_activation=cov,ticks=k['cost']['kernel_ticks'],network_id=nid))
        elig_bounds_by_n[str(n)]=dict(false_min=min(ef),false_max=max(ef),true_min=min(et),true_max=max(et),cov_false_min=min(cf),cov_false_max=max(cf),cov_true_min=min(ct),cov_true_max=max(ct))
    require(len(feasible_envelope)==60,'60 feasible1..4 extremal settles')
    query_envelope=[]
    for n in range(1,5):
        q_doc=p['programs']['query'+str(n)];eb=elig_bounds_by_n[str(n)]
        ef_max=eb['false_max'];et_min=eb['true_min'];cf_max=eb['cov_false_max'];ct_min=eb['cov_true_min']
        for bits in itertools.product([False,True],repeat=2*n+1):
            e_bool=list(bits[:n]);t_bool=list(bits[n:2*n]);comp_bool=bits[2*n]
            e_in=[et_min if b else ef_max for b in e_bool]
            t_in=[expr_true_min if b else expr_false_max for b in t_bool]
            c_in=ct_min if comp_bool else cf_max
            drives={'e'+str(i):cfg.evidence_gain*(2*e_in[i]-1) for i in range(n)}
            drives.update({'t'+str(i):cfg.evidence_gain*(2*t_in[i]-1) for i in range(n)})
            drives['complete']=cfg.evidence_gain*(2*c_in-1)
            k=kernel_fn(q_doc,drives,cfg,.5);nid=add_fn(k)
            qtag=onehot_fn(k,['qtrue','qfalse','empty','mixed','incomplete'],cfg.margin_threshold)
            query_envelope.append(dict(capacity=n,e_bool=e_bool,t_bool=t_bool,complete_bool=comp_bool,e_in=e_in,t_in=t_in,complete_in=c_in,tag=qtag,ticks=k['cost']['kernel_ticks'],network_id=nid))
    require(len(query_envelope)==680,'680 query1..4 extremal settles')
    transfer=dict(
        role_representatives=role_goals,
        expr_transfer=expr_transfer,
        expr_bounds=dict(false_min=expr_false_min,false_max=expr_false_max,true_min=expr_true_min,true_max=expr_true_max),
        feasible_envelope=feasible_envelope,
        eligibility_bounds_by_capacity=elig_bounds_by_n,
        eligibility_bounds_global=dict(false_min=min(all_elig_false),false_max=max(all_elig_false),true_min=min(all_elig_true),true_max=max(all_elig_true),cov_false_max=max(all_cov_false),cov_true_min=min(all_cov_true)),
        query_envelope=query_envelope
    )
    return role,transfer

def preparation():
    from hcr.model import Config
    from tools.r33_typed_feedback.runtime import program
    from tools.r34_feasible_state.runtime import onehot
    from tools.r35_compositional_slot.compiler import documents
    import tools.r35_compositional_slot.runtime as r35_rt
    from tools.r35_compositional_slot.runtime import truth
    from tools.r35_compositional_slot.verify import oracle
    from tools.r47_capacity_codebook_transfer.verify import validate_map,check_matrix_coverage,run_mutation_suite
    p=inputs();cfg=Config(**p['kernel']);require(documents(p['expressions'],cfg)==p['programs'],'single syntax/count generator');checks=0
    for doc in p['programs'].values():program(doc).validate(cfg)
    require(len(p['sources'])==56 and len(p['cases'])==1280 and len({c['base_key'] for c in p['cases']})==160,'matrix/source/base count')
    tree=ast.parse((ROOT/'tools/r35_compositional_slot/runtime.py').read_text(encoding='utf-8'));fn=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='consume_t')
    require([x.arg for x in fn.args.args]==['binding','t','t_tree','vocabulary','cfg','role_doc','expr_doc','query_doc','initial'],'independent final consumer boundary')
    def boolean(doc,features):
        state=dict(features)
        for g in doc['groups']:
            name=g['id']
            if name in state:continue
            terms=[state[e['source']] if e['weight']>0 else not state[e['source']] for e in doc['links'] if e['kind']=='support' and e['target']==name]
            state[name]=(all(terms) if g['bias']<0 else any(terms)) if terms else g['bias']>0
        return state
    for x,y in itertools.product(range(8),repeat=2):
        st=boolean(p['programs']['role'],{prefix+str(i):bool((v>>i)&1) for prefix,v in [('x',x),('y',y)] for i in range(3)})
        require(st['goal']==(x==y),'3bit Boolean equality');checks+=1
    for i,tr in enumerate(p['expressions']):
        for bits in itertools.product([False,True],repeat=3):
            require(boolean(p['programs']['expr'+str(i)],dict(zip(['m0','m1','m2'],bits)))['goal']==truth(tr,bits),'AST Boolean semantics');checks+=1
    for n in range(1,5):
        for bits in itertools.product([False,True],repeat=n+1):
            features=dict(zip(['e'+str(i) for i in range(n)]+['complete'],bits));st=boolean(p['programs']['feasible'+str(n)],features);cnt=sum(bits[:n]);comp=bits[-1]
            expected=[comp and cnt==0,comp and cnt==1,comp and cnt>1,not comp]
            require([st[k] for k in ['none','unique','many','incomplete']]==expected,'cardinality Boolean semantics');checks+=1
        for bits in itertools.product([False,True],repeat=2*n+1):
            features=dict(zip([prefix+str(i) for prefix in ['e','t'] for i in range(n)]+['complete'],bits));st=boolean(p['programs']['query'+str(n)],features)
            vals=[bits[n+i] for i in range(n) if bits[i]];comp=bits[-1]
            expected=[comp and bool(vals) and all(vals),comp and bool(vals) and not any(vals),comp and not vals,comp and bool(vals) and any(vals) and not all(vals),not comp]
            require([st[k] for k in ['qtrue','qfalse','empty','mixed','incomplete']]==expected,'universal Boolean query');checks+=1
    desc={s['key']:dict(predicate=s['predicate'],subject=s['observation']['start'],object=s['observation']['goal']) for s in p['sources']}
    cov_summary=check_matrix_coverage(p,desc)
    by_base={}
    for c in p['cases']:
        validate_map(c,p)
        base=by_base.setdefault(c['base_key'],c)
        require({k:v for k,v in c.items() if k not in ['key','map_name','code_map','vocabulary','arms']}=={k:v for k,v in base.items() if k not in ['key','map_name','code_map','vocabulary','arms']},'only map metadata/vocabulary changed')
        checks+=1
    stub_packets={s['key']:dict(schema='hcr-r32-relation-v1',predicate=s['predicate'],subject=s['observation']['start'],object=s['observation']['goal'],revision=0,confidence=.99,value=True,origin_sha256=s['key'],observation_sha256=s['key'],proof_sha256=s['key'],config_sha256=s['key']) for s in p['sources']}
    stub_nets={};calls=0;orig_kernel=r35_rt.kernel
    def stub(doc,drives,cfg_obj,initial):
        nonlocal calls
        calls+=1
        bstate=boolean(doc,{k:v>0 for k,v in drives.items()})
        state={k:(0.99 if v else 0.01) for k,v in bstate.items()}
        if doc==p['programs']['role']:
            d=sum((drives['x'+str(i)]>0)!=(drives['y'+str(i)]>0) for i in range(3))
            state['goal']={0:0.986,1:0.008,2:0.0004,3:0.00002}[d]
        elif 'goal' in state and drives:
            eps=1e-6*sum(drives[k] for k in sorted(drives))
            for k in state:
                state[k]=(0.99+eps) if bstate[k] else (0.01+eps)
        return dict(program=doc,drives=dict(drives),initial={g['id']:initial for g in doc['groups']},state=state,adopted=state['goal']>.5,convergence=dict(status='stable_decision'),cost=dict(kernel_ticks=30,group_updates=120,signal_transmissions=240))
    def add_stub(k):
        nid='s%05d'%len(stub_nets);stub_nets[nid]=k;return nid
    r35_rt.kernel=stub
    mock_records=[]
    try:
        role_mock,transfer_mock=run_stage_transfer(p,cfg,stub,onehot,add_stub)
        require(calls==1188,'1188 stage-transfer settles in Boolean stub')
        for c in p['cases']:
            cands=[stub_packets[k] for k in c['candidates']];ctx=[stub_packets[k] for k in c['context']];t=[stub_packets[k] for k in c['T']]
            expected=oracle(cands,ctx,p['expressions'][c['c_expr']],t,p['expressions'][c['t_expr']],c['complete'])
            for arm in c['arms']:
                r=execute_case(cands,ctx,p['expressions'][c['c_expr']],t,p['expressions'][c['t_expr']],c['complete'],c['contract'],c['vocabulary'],arm,p['kernel'],c['initial'])
                r.update(case=c['key'],base_key=c['base_key'],map_name=c['map_name'],capacity=c['capacity'],part=c['part'],arm=arm)
                r['network_ids']=[] if arm=='exact' else [add_stub(k) for k in r.pop('networks')]
                if arm=='native':del r['binding']['alternatives'];r['binding']['alternative_keys']=c['candidates']
                require(all(r[k]==expected[k] for k in ['kind','selected_index','value','reason']),'Boolean stub oracle match '+arm)
                mock_records.append(r)
    finally:
        r35_rt.kernel=orig_kernel
    require(calls==29348 and len(mock_records)==1440,'declared 29348 recorded settles and 1440 evaluations')
    cases_map={c['key']:c for c in p['cases']}
    pre_rejected=run_mutation_suite(mock_records,cases_map,stub_packets,p,stub_nets,desc,role_mock,transfer_mock,transfer_mock['role_representatives'])
    require(len(pre_rejected)==25,'all 25 mutations pre-verified in preparation')
    allmaps=pairchecks=0
    for mp in itertools.permutations(range(8)):
        require(len(set(mp))==8,'bijection enumeration');allmaps+=1
        for x,y in itertools.product(range(8),repeat=2):require((mp[x]==mp[y])==(x==y),'symbolic bijection equality');pairchecks+=1
    require(allmaps==40320 and pairchecks==2580480,'finite role domain')
    put(OUT/'preparation.json',dict(status='PASS',checks=checks,role_bijections_checked=allmaps,role_pair_checks=pairchecks,pre_verified_mutations=len(pre_rejected),matrix_coverage=cov_summary,native_calls=0))

def work():
    from hcr.model import Config,fingerprint
    from tools.r32_semantic_join.runtime import lower,export
    from tools.r33_typed_feedback.runtime import kernel
    from tools.r34_feasible_state.runtime import onehot
    from tools.r36_overlap_composition.recording import Recorder,work_writer
    import tools.r34_feasible_state.probe as storage
    p=inputs();write=work_writer(OUT,p);storage.OUT=OUT;storage.put=write;cfg=Config(**p['kernel']);start=time.process_time();sources={s['key']:lower(s['observation'],s['predicate'],p['kernel']) for s in p['sources']};write(OUT/'sources.json',sources);source_cpu=time.process_time()-start;rec=Recorder(p)
    def add(k):
        n=rec.add(k);require(rec.cached_bytes<=p['budget']['canonical_cache_bytes'],'aggregate canonical cache stop');return n
    transfer_start=time.process_time()
    role,transfer=run_stage_transfer(p,cfg,kernel,onehot,add)
    stage_transfer_cpu=time.process_time()-transfer_start
    write(OUT/'roles.json',role);write(OUT/'transfer.json',transfer)
    require(rec.calls==1188,'1188 stage-transfer settles recorded')
    batch=[];metrics=[];part=0;computed=1188;completed=0;success=False;inflight=None
    try:
        for c in p['cases']:
            for arm in c['arms']:
                inflight=dict(case=c['key'],arm=arm);cpu=time.process_time();wall=time.perf_counter();packets={k:export(sources[k]) for k in c['candidates']+c['context']+c['T']};require(all(packets[k]['origin_sha256']==fingerprint(sources[k]) for k in packets),'source export guard')
                r=execute_case([packets[k] for k in c['candidates']],[packets[k] for k in c['context']],p['expressions'][c['c_expr']],[packets[k] for k in c['T']],p['expressions'][c['t_expr']],c['complete'],c['contract'],c['vocabulary'],arm,p['kernel'],c['initial'])
                computed+=r['native_calls'];core=time.process_time()-cpu;store=time.process_time()
                r.update(inflight,map_name=c['map_name'],base_key=c['base_key'],capacity=c['capacity'],part=c['part'])
                r['network_ids']=[] if arm=='exact' else [add(k) for k in r.pop('networks')]
                if arm=='native':del r['binding']['alternatives'];r['binding']['alternative_keys']=c['candidates']
                batch.append(r);metrics.append(dict(inflight,core_cpu_seconds=core,storage_cpu_seconds=time.process_time()-store,wall_seconds=time.perf_counter()-wall));completed+=1;inflight=None
                if len(batch)==80:write(OUT/('batch%02d.json'%part),batch);write(OUT/('metrics%02d.json'%part),metrics);part+=1;batch=[];metrics=[]
        require(not batch and part==18 and computed==rec.calls==29348 and completed==1440,'complete frozen work');success=True
    finally:
        if batch:write(OUT/('batch%02d.partial.json'%part),batch,metadata=True);write(OUT/('metrics%02d.partial.json'%part),metrics,metadata=True)
        write(OUT/'work-ledger.json',dict(completed=success,completed_evaluations=completed,planned_evaluations=1440,inflight=inflight,physical_recorded_calls=rec.calls,upper_calls=computed-1188,role_calls=64,expr_transfer_calls=384,feasible_envelope_calls=60,query_envelope_calls=680,stage_transfer_calls=1188,source_calls=56,total_physical_calls=rec.calls+56,unique_traces=len(rec.cache),aggregate_cache_bytes=rec.cached_bytes,max_record_bytes=rec.peak_record_bytes,computation_reused=False,trace_storage_only_shared=True,source_cpu_seconds=source_cpu,stage_transfer_cpu_seconds=stage_transfer_cpu),metadata=True)

def audit_all():
    from tools.r47_capacity_codebook_transfer.verify import bundle
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
    def forbidden(*a,**k):raise ValueError('R47 world measurement forbidden')
    World.measure=forbidden
    if args.phase=='run':run(args.started or time.monotonic())
    elif args.phase=='preparation':preparation()
    elif args.phase=='work':work()
    else:audit_all()
