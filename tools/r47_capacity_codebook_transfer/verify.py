"""Saved-data 8-token variable-capacity (n=1..4) codebook coverage, 6/6 AST distinction, and 1,188-settle stage-transfer audit."""
import itertools,json,math
from collections import Counter
from copy import deepcopy
from hcr.model import fingerprint
from tools.r32_semantic_join.runtime import require,export
from tools.r32_semantic_join.verify import audit_lower
from tools.r34_feasible_state.verify import tag
from tools.r35_compositional_slot.runtime import truth
from tools.r35_compositional_slot.verify import audit as r35_audit,oracle,mutations as r35_mutations
from tools.r36_overlap_composition.verify import SavedNetworks

FIELDS=['kind','selected_index','value','reason','tag','C_AST_values','T_AST_values','C_leaf_patterns','T_leaf_patterns']
ISOMETRIC_MAPS={'identity','bit_reverse','xor7'}

def validate_map(c,p):
    mp=c['code_map'];v=c['canonical_vocabulary']
    require(len(mp)==len(v)==len(set(v))==8 and all(type(x) is int for x in mp) and sorted(mp)==list(range(8)),'3bit bijective map')
    require(mp==p['codebooks'][c['map_name']] and len(c['vocabulary'])==8,'frozen codebook')
    require(all(c['vocabulary'][mp[i]]==token for i,token in enumerate(v)),'inverse vocabulary encoder contract')

def check_matrix_coverage(p,desc):
    restricted={};capacities_seen=Counter()
    for c in p['cases']:
        require(1<=c['capacity']<=4 and len(c['candidates'])==c['capacity'],'case capacity contract')
        require(len({desc[k]['object'] for k in c['candidates']})==c['capacity'],'distinct candidate tokens')
        tokens=sorted({desc[k]['object'] for k in c['candidates']}|{desc[k]['subject'] for k in c['context']+c['T']})
        code={token:i for i,token in enumerate(c['vocabulary'])}
        require(all(t in code for t in tokens),'active tokens in vocabulary')
        sig=tuple((t,code[t]) for t in tokens)
        restricted.setdefault(c['base_key'],{})[c['map_name']]=sig
        if c['map_name']=='identity':capacities_seen[c['capacity']]+=1
    require(dict(sorted(capacities_seen.items()))=={1:40,2:40,3:40,4:40},'40 base cases per capacity n=1..4')
    classes_per_base=sorted({len(set(m.values())) for m in restricted.values()})
    unchanged=changed=0
    for maps in restricted.values():
        for name,sig in maps.items():
            if name=='identity':continue
            if sig==maps['identity']:unchanged+=1
            else:changed+=1
    require(classes_per_base==[8] and unchanged==0 and changed==1120,'every base case 8 distinct restricted maps and 0 unchanged pairs')
    pairs_by_map={};hamming_by_map={}
    for name in p['codebooks']:
        pairs_seen=set();d_seen=set()
        for c in p['cases']:
            if c['map_name']!=name:continue
            code={token:i for i,token in enumerate(c['vocabulary'])}
            for ck in c['candidates']:
                a=desc[ck]['object']
                require(a in code,'candidate object in vocabulary')
                for fk in c['context']+c['T']:
                    b=desc[fk]['subject']
                    require(b in code,'leaf subject in vocabulary')
                    pair=(code[a],code[b]);pairs_seen.add(pair);d_seen.add((pair[0]^pair[1]).bit_count())
        require(len(pairs_seen)==64 and d_seen=={0,1,2,3},'all 64 ordered code pairs and d in 0..3 per codebook')
        pairs_by_map[name]=len(pairs_seen);hamming_by_map[name]=sorted(d_seen)
    return dict(
        base_cases_by_capacity={str(k):v for k,v in sorted(capacities_seen.items())},
        restricted_map_classes_per_base=classes_per_base,
        mapped_pairs_actual_code_unchanged=unchanged,
        mapped_pairs_actual_code_changed=changed,
        ordered_code_pairs_per_map=pairs_by_map,
        hamming_classes_per_map=hamming_by_map
    )

def audit(r,c,packets,p,networks):
    validate_map(c,p)
    require(r['map_name']==c['map_name'] and r['base_key']==c['base_key'] and r['capacity']==c['capacity'] and r['part']==c['part'],'record codebook/capacity identity')
    candidates=[packets[k] for k in c['candidates']];context=[packets[k] for k in c['context']];t=[packets[k] for k in c['T']];contract=c['contract'];n=len(candidates)
    require(n==c['capacity'] and 1<=n<=4,'candidate count matches capacity')
    require(r['leaf_contract_sha256']==fingerprint(contract),'typed leaf contract binding')
    require(all(x['predicate']=='R' and x['subject']==contract['candidate_subject'] for x in candidates),'candidate metadata slot')
    for facts,name in [(context,'C'),(t,'T')]:
        for fact,slot in zip(facts,contract[name],strict=True):
            require(fact['predicate']==slot['predicate'] and fact['object']==slot['object'],'leaf predicate/target slot binding')
    row=r35_audit(r,c,packets,p,networks)
    expected_tag='incomplete' if not c['complete'] else 'empty' if not row['truth']['feasible'] else 'qtrue' if row['truth']['value'] is True else 'qfalse' if row['truth']['value'] is False else 'mixed'
    row.update(
        map_name=c['map_name'],
        base_key=c['base_key'],
        capacity=n,
        part=c['part'],
        c_masks=c['c_masks'],
        t_masks=c['t_masks'],
        tag=expected_tag if r['arm']=='exact' else r['final']['tag'],
        selected_code=None if r['selected_index'] is None else c['canonical_vocabulary'].index(candidates[r['selected_index']]['object'])
    )
    if r['arm']=='native':
        require(r['final']['tag']==expected_tag,'final tag matches oracle')
        ks=[networks[name] for name in r['network_ids']];require(len(ks)==8*n+2,'8n+2 native networks')
        c_seg=ks[:4*n];feas_k=ks[4*n];t_seg=ks[4*n+1:8*n+1];query_k=ks[8*n+1]
        role_total=role_correct=ast_total=ast_correct=0;role_ks=[];expr_ks=[]
        for name,facts,expr,segment in [('C',context,c['c_expr'],c_seg),('T',t,c['t_expr'],t_seg)]:
            feasible=oracle(candidates,facts,p['expressions'][expr],facts,p['expressions'][expr],True)['feasible'];values=[];patterns=[]
            for i,candidate in enumerate(candidates):
                block=segment[4*i:4*i+4];role_ks.extend(block[:3]);expr_ks.append(block[3])
                bits=[candidate['object']==fact['subject'] for fact in facts];patterns.append(bits)
                role_total+=3;role_correct+=sum(k['adopted'] is expected for k,expected in zip(block[:3],bits,strict=True))
                ast_total+=1;ast_correct+=block[3]['adopted'] is (i in feasible);values.append(block[3]['adopted'])
            row[name+'_AST_values']=values;row[name+'_leaf_patterns']=patterns
        rt=sum(k['cost']['kernel_ticks'] for k in role_ks)
        et=sum(k['cost']['kernel_ticks'] for k in expr_ks)
        ft=feas_k['cost']['kernel_ticks']
        qt=query_k['cost']['kernel_ticks']
        require(rt+et+ft+qt==row['ticks'],'stage tick partition')
        hi=(1+p['kernel']['margin_threshold'])/2;lo=(1-p['kernel']['margin_threshold'])/2
        c_feas=set(oracle(candidates,context,p['expressions'][c['c_expr']],context,p['expressions'][c['c_expr']],True)['feasible'])
        for i,ev in enumerate(r['binding']['eligibility']):
            require(ev>=hi if (i in c_feas) else ev<=lo,'strict eligibility margin separation at capacity n')
        row.update(
            role_total=role_total,role_correct=role_correct,
            AST_total=ast_total,AST_correct=ast_correct,
            intermediate_correct=role_total==role_correct and ast_total==ast_correct,
            role_ticks=rt,expr_ticks=et,feasible_ticks=ft,query_ticks=qt,
            eligibility=list(r['binding']['eligibility']),
            coverage_activation=r['binding']['coverage_activation'],
            state_sha256=r['binding']['state_sha256']
        )
    return row

def role_audit(role,networks,p):
    require(len(role)==64 and {(x['left'],x['right']) for x in role}==set(itertools.product(range(8),repeat=2)),'all numeric role inputs')
    table={};goal_table={};tick_table={};error=0;cfg=p['kernel'];gain=cfg['evidence_gain'];by_d={d:[] for d in range(4)};ticks_by_d={d:set() for d in range(4)}
    for r in role:
        k=networks[r['network_id']];drives={s+str(i):gain*(1 if (v>>i)&1 else -1) for s,v in [('x',r['left']),('y',r['right'])] for i in range(3)}
        d=(r['left']^r['right']).bit_count()
        require(r['hamming']==d and k['program']==p['programs']['role'] and k['drives']==drives and all(v==.5 for v in k['initial'].values()),'role Program/Config/drive/initial/Hamming coverage')
        table[(r['left'],r['right'])]=k['adopted'];goal_table[(r['left'],r['right'])]=k['state']['goal'];tick_table[(r['left'],r['right'])]=k['cost']['kernel_ticks']
        by_d[d].append(k['state']['goal']);ticks_by_d[d].add(k['cost']['kernel_ticks'])
        error+=k['adopted'] is not (r['left']==r['right'])
    rep_goals={};rep_ticks={};max_class_spread=0.0
    for d in range(4):
        vals=by_d[d];require(len(vals)==[8,24,24,8][d] and len(ticks_by_d[d])==1,'Hamming class cardinality and exact tick invariance')
        spread=max(vals)-min(vals);max_class_spread=max(max_class_spread,spread)
        require(spread<=p['scalar_tolerance'],'4-class Hamming terminal goal equivalence')
        rep_goals[d]=vals[0];rep_ticks[d]=next(iter(ticks_by_d[d]))
    require(rep_goals[0]>0.9 and all(rep_goals[d]<0.02 for d in [1,2,3]),'Hamming class separation')
    checked=wrong=0;first=[]
    for perm in itertools.permutations(range(8)):
        for x,y in itertools.product(range(8),repeat=2):
            checked+=1
            if table[(perm[x],perm[y])] is not (x==y) or ((perm[x]^perm[y]).bit_count()==0) is not (x==y):
                wrong+=1
                if len(first)<8:first.append(dict(codebook=list(perm),left=x,right=y,value=table[(perm[x],perm[y])]))
    require(checked==2580480 and wrong==0,'all 40320 mapping role checks')
    return dict(
        actual_numeric_inputs=64,
        numeric_correct=64-error,
        codebooks_role_only=40320,
        saved_lookup_checks=checked,
        wrong=wrong,
        first_counterexamples=first,
        hamming_class_goals={str(k):v for k,v in rep_goals.items()},
        hamming_class_ticks={str(k):v for k,v in rep_ticks.items()},
        max_within_class_goal_spread=max_class_spread,
        full_pipeline_codebooks=8,
        scope='all 8-token bijections role stage (4 Hamming equivalence classes), fixed Program/Config/initial; not all full-pipeline executions'
    ),rep_goals

def transfer_audit(transfer,rep_goals,networks,p):
    cfg=p['kernel'];gain=cfg['evidence_gain'];tol=p['scalar_tolerance']
    hi=(1+cfg['margin_threshold'])/2;lo=(1-cfg['margin_threshold'])/2
    expr_rows=transfer['expr_transfer']
    require(len(expr_rows)==384,'384 exhaustive expr Hamming-triple rows')
    seen_expr=set();true_vals=[];false_vals=[];expr_ticks_by_ast={i:set() for i in range(6)};expr_table={}
    for row in expr_rows:
        ei=row['expr'];d0,d1,d2=row['hamming_triple']
        require(0<=ei<6 and all(dj in [0,1,2,3] for dj in (d0,d1,d2)),'valid expr/Hamming triple')
        seen_expr.add((ei,d0,d1,d2))
        k=networks[row['network_id']]
        expected_drives={'m'+str(j):gain*(2*rep_goals[dj]-1) for j,dj in enumerate((d0,d1,d2))}
        require(k['program']==p['programs']['expr'+str(ei)] and all(abs(k['drives'][m]-expected_drives[m])<=tol for m in expected_drives) and all(v==.5 for v in k['initial'].values()),'expr transfer Program/drives/initial')
        expected_bool=truth(p['expressions'][ei],[d0==0,d1==0,d2==0])
        require(row['expected'] is expected_bool and k['adopted'] is expected_bool and row['adopted'] is expected_bool and abs(row['goal']-k['state']['goal'])<=tol and row['ticks']==k['cost']['kernel_ticks'],'expr transfer semantic and scalar consistency')
        if expected_bool:true_vals.append(k['state']['goal'])
        else:false_vals.append(k['state']['goal'])
        expr_ticks_by_ast[ei].add(k['cost']['kernel_ticks'])
        expr_table[(ei,d0,d1,d2)]=k['adopted']
    require(len(seen_expr)==384,'all 6x4^3 expr triples covered')
    expr_lookup_checks=0;expr_lookup_wrong=0
    for ei in range(6):
        for d0,d1,d2 in itertools.product(range(4),repeat=3):
            expr_lookup_checks+=40320
            if expr_table[(ei,d0,d1,d2)] is not truth(p['expressions'][ei],[d0==0,d1==0,d2==0]):
                expr_lookup_wrong+=40320
    require(expr_lookup_checks==384*40320 and expr_lookup_wrong==0,'exhaustive role->expr 40320 bijection class transfer')
    expr_false_max=max(false_vals);expr_true_min=min(true_vals)
    f_rows=transfer['feasible_envelope'];require(len(f_rows)==60,'60 feasible1..4 extremal rows')
    f_seen=set();f_by_n={n:0 for n in range(1,5)};elig_bounds_by_n={}
    ef_by_n={n:[] for n in range(1,5)};et_by_n={n:[] for n in range(1,5)};cf_by_n={n:[] for n in range(1,5)};ct_by_n={n:[] for n in range(1,5)}
    for row in f_rows:
        n=row['capacity'];e_bool=row['e_bool'];comp_bool=row['complete_bool']
        require(1<=n<=4 and len(e_bool)==n and type(comp_bool) is bool,'feasible envelope capacity/bool shape')
        f_seen.add((n,tuple(e_bool),comp_bool));f_by_n[n]+=1
        k=networks[row['network_id']]
        expected_e_in=[expr_true_min if b else expr_false_max for b in e_bool]
        expected_drives={'e'+str(i):gain*(2*expected_e_in[i]-1) for i in range(n)}
        expected_drives['complete']=gain*(1 if comp_bool else -1)
        require(k['program']==p['programs']['feasible'+str(n)] and all(abs(k['drives'][m]-expected_drives[m])<=tol for m in expected_drives),'feasible_n envelope Program/drives')
        kind=tag(k,['none','unique','many','incomplete'],cfg)
        cnt=sum(e_bool)
        expected_kind='incomplete' if not comp_bool else 'none' if cnt==0 else 'unique' if cnt==1 else 'many'
        el=[k['state']['e'+str(i)] for i in range(n)];cov=k['state']['complete']
        require(kind==expected_kind and row['kind']==expected_kind,'feasible_n extremal semantic kind')
        require(all((el[i]>=hi if e_bool[i] else el[i]<=lo) for i in range(n)),'feasible_n extremal eligibility margins')
        require((cov>=hi if comp_bool else cov<=lo),'feasible_n extremal coverage margin')
        for b_flag,ev in zip(e_bool,el,strict=True):
            if b_flag:et_by_n[n].append(ev)
            else:ef_by_n[n].append(ev)
        if comp_bool:ct_by_n[n].append(cov)
        else:cf_by_n[n].append(cov)
    require(len(f_seen)==60 and f_by_n=={1:4,2:8,3:16,4:32},'all 60 feasible1..4 extremal corners')
    for n in range(1,5):
        elig_bounds_by_n[str(n)]=dict(
            false_min=min(ef_by_n[n]),false_max=max(ef_by_n[n]),
            true_min=min(et_by_n[n]),true_max=max(et_by_n[n]),
            cov_false_min=min(cf_by_n[n]),cov_false_max=max(cf_by_n[n]),
            cov_true_min=min(ct_by_n[n]),cov_true_max=max(ct_by_n[n])
        )
    q_rows=transfer['query_envelope'];require(len(q_rows)==680,'680 query1..4 extremal rows')
    q_seen=set();q_by_n={n:0 for n in range(1,5)}
    for row in q_rows:
        n=row['capacity'];e_bool=row['e_bool'];t_bool=row['t_bool'];comp_bool=row['complete_bool']
        require(1<=n<=4 and len(e_bool)==len(t_bool)==n and type(comp_bool) is bool,'query envelope capacity/bool shape')
        q_seen.add((n,tuple(e_bool),tuple(t_bool),comp_bool));q_by_n[n]+=1
        eb=elig_bounds_by_n[str(n)]
        expected_e_in=[eb['true_min'] if b else eb['false_max'] for b in e_bool]
        expected_t_in=[expr_true_min if b else expr_false_max for b in t_bool]
        expected_c_in=eb['cov_true_min'] if comp_bool else eb['cov_false_max']
        expected_drives={'e'+str(i):gain*(2*expected_e_in[i]-1) for i in range(n)}
        expected_drives.update({'t'+str(i):gain*(2*expected_t_in[i]-1) for i in range(n)})
        expected_drives['complete']=gain*(2*expected_c_in-1)
        k=networks[row['network_id']]
        require(k['program']==p['programs']['query'+str(n)] and all(abs(k['drives'][m]-expected_drives[m])<=tol for m in expected_drives),'query_n envelope Program/drives')
        qtag=tag(k,['qtrue','qfalse','empty','mixed','incomplete'],cfg)
        vals=[tb for eb_f,tb in zip(e_bool,t_bool,strict=True) if eb_f]
        expected_tag='incomplete' if not comp_bool else 'empty' if not vals else 'qtrue' if all(vals) else 'qfalse' if not any(vals) else 'mixed'
        require(qtag==expected_tag and row['tag']==expected_tag,'query_n extremal semantic tag')
    require(len(q_seen)==680 and q_by_n=={1:8,2:32,3:128,4:512},'all 680 query1..4 extremal corners')
    return dict(
        expr_exhaustive_triples=384,
        expr_correct=384,
        expr_bijection_class_checks=expr_lookup_checks,
        expr_bijection_class_wrong=expr_lookup_wrong,
        expr_false_goal_range=[min(false_vals),max(false_vals)],
        expr_true_goal_range=[min(true_vals),max(true_vals)],
        expr_ticks_by_ast={str(i):sorted(expr_ticks_by_ast[i]) for i in range(6)},
        feasible_extremal_corners=60,
        feasible_extremal_correct=60,
        feasible_corners_by_capacity={str(k):v for k,v in sorted(f_by_n.items())},
        eligibility_bounds_by_capacity=elig_bounds_by_n,
        query_extremal_corners=680,
        query_extremal_correct=680,
        query_corners_by_capacity={str(k):v for k,v in sorted(q_by_n.items())},
        scope='role(64)->expr(384) is exhaustive across all 4^3 Hamming-distance triples for all 40320 3-bit bijections; feasible1..4(60) and query1..4(680) are exhaustive Boolean corners at worst-case inner-margin [false_max, true_min] bounds across capacities n=1..4, not 64^n full product enumeration'
    )

def verify_ast_and_regime_coverage(rows,p):
    native_id=[r for r in rows if r['arm']=='native' and r['map_name']=='identity']
    expected_8bit=[[truth(tree,[bool((mask>>i)&1) for i in range(3)]) for mask in range(8)] for tree in p['expressions']]
    expected_m4a=[[truth(tree,[bool((mask>>i)&1) for i in range(3)]) for mask in [1,2,5,7]] for tree in p['expressions']]
    by_cap={}
    for n in range(1,5):
        sub=[r for r in native_id if r['capacity']==n]
        comp_true=[r for r in sub if r['complete']];comp_false=[r for r in sub if not r['complete']]
        require(len(sub)==40 and len(comp_true)==32 and len(comp_false)==8,'40 base cases (32 complete=True, 8 complete=False) per capacity')
        c_obs={i:{} for i in range(6)};t_obs={i:{} for i in range(6)}
        for r in comp_true:
            for m,v in zip(r['c_masks'],r['C_AST_values'],strict=True):
                if m in c_obs[r['c_expr']]:require(c_obs[r['c_expr']][m]==v,'consistent C AST value')
                c_obs[r['c_expr']][m]=v
            for m,v in zip(r['t_masks'],r['T_AST_values'],strict=True):
                if m in t_obs[r['t_expr']]:require(t_obs[r['t_expr']][m]==v,'consistent T AST value')
                t_obs[r['t_expr']][m]=v
        if n>=2:
            c_vecs=[[c_obs[i][m] for m in range(8)] for i in range(6)]
            t_vecs=[[t_obs[i][m] for m in range(8)] for i in range(6)]
            require(c_vecs==expected_8bit and t_vecs==expected_8bit and len({tuple(v) for v in c_vecs})==6 and len({tuple(v) for v in t_vecs})==6,'all 48/48 (AST,mask) cells and 6/6 distinct 8-bit truth vectors at capacity n>=2')
            ast_info=dict(c_distinct_ast=6,t_distinct_ast=6,c_cells_covered=48,t_cells_covered=48,full_8bit_per_phase=True)
        else:
            c_m4=[[c_obs[i][m] for m in [1,2,5,7]] for i in range(6)]
            union_vecs=[[c_obs[i].get(m,t_obs[i].get(m)) for m in range(8)] for i in range(6)]
            require(c_m4==expected_m4a and len({tuple(v) for v in c_m4})==6 and union_vecs==expected_8bit and len({tuple(v) for v in union_vecs})==6,'6/6 distinct AST functions and 48/48 combined (AST,mask) cells at n=1')
            ast_info=dict(c_distinct_ast=6,t_distinct_ast=6,combined_cells_covered=48,full_8bit_combined=True)
        regimes=Counter()
        for r in sub:
            f_cnt=len(r['truth']['feasible'])
            t_pos=sum(r['T_AST_values'][i] for i in r['truth']['feasible'])
            t_neg=f_cnt-t_pos
            regimes[f"{r['kind']}:{r['tag']}:|F|={f_cnt}:{t_pos}:{t_neg}"]+=1
        require(all(r['kind']=='incomplete' and r['tag']=='incomplete' and r['value'] is None and r['reason']=='abstain_incomplete' for r in comp_false),'100% incomplete abstention when complete=False')
        by_cap[str(n)]=dict(ast_distinction=ast_info,regime_counts=dict(sorted(regimes.items())))
    return by_cap

def single_record_mutations(r,c,packets,p,networks):
    rejected=r35_mutations(r,c,packets,p,networks)
    bad=deepcopy(r);bad['leaf_contract_sha256']='wrong'
    try:audit(bad,c,packets,p,networks)
    except ValueError:rejected.append('leaf_contract')
    else:raise ValueError('accepted wrong leaf contract')
    for name,key,field,value in [('C_predicate',c['context'][0],'predicate','wrong'),('C_target',c['context'][0],'object','wrong'),('T_predicate',c['T'][0],'predicate','wrong'),('T_target',c['T'][0],'object','wrong'),('candidate_subject',c['candidates'][0],'subject','wrong')]:
        altered=deepcopy(packets);altered[key][field]=value
        try:audit(r,c,altered,p,networks)
        except ValueError:rejected.append(name)
        else:raise ValueError('accepted slot mutation '+name)
    return rejected

def run_mutation_suite(records,cases,packets,p,networks,desc,role,transfer,rep_goals):
    target_n4=next(r for r in records if r['arm']=='native' and r['capacity']==4 and cases[r['case']]['complete'])
    c_n4=cases[target_n4['case']]
    rejected=single_record_mutations(target_n4,c_n4,packets,p,networks)
    bad_c=deepcopy(c_n4);bad_c['code_map']=[0]*8
    try:audit(target_n4,bad_c,packets,p,networks)
    except ValueError:rejected.append('nonbijective_map')
    else:raise ValueError('accepted nonbijective_map')
    bad_c2=deepcopy(c_n4);bad_c2['vocabulary']=list(reversed(bad_c2['vocabulary']))
    try:audit(target_n4,bad_c2,packets,p,networks)
    except ValueError:rejected.append('inverse_vocab_mismatch')
    else:raise ValueError('accepted inverse_vocab_mismatch')
    bad_r_cap=deepcopy(target_n4);bad_r_cap['binding']['eligibility']=bad_r_cap['binding']['eligibility'][:3]
    try:audit(bad_r_cap,c_n4,packets,p,networks)
    except ValueError:rejected.append('capacity_mismatch')
    else:raise ValueError('accepted capacity_mismatch')
    target_inc=next(r for r in records if r['arm']=='native' and r['capacity']==4 and not cases[r['case']]['complete'])
    c_inc=cases[target_inc['case']]
    bad_inc=deepcopy(target_inc);bad_inc['kind']='unique';bad_inc['binding']['kind']='unique'
    try:audit(bad_inc,c_inc,packets,p,networks)
    except ValueError:rejected.append('incomplete_policy_bypass')
    else:raise ValueError('accepted incomplete_policy_bypass')
    bad_role=deepcopy(role);bad_role[0]['left']=1
    try:role_audit(bad_role,networks,p)
    except ValueError:rejected.append('numeric_role_coverage')
    else:raise ValueError('accepted numeric_role_coverage')
    bad_p=deepcopy(p)
    for cc in bad_p['cases']:
        if cc['map_name']=='identity':
            cc['context']=['n0_P0_0','n0_P1_0','n0_P2_0']
            cc['T']=['n0_Q0_0','n0_Q1_0','n0_Q2_0']
    try:check_matrix_coverage(bad_p,desc)
    except ValueError:rejected.append('incomplete_tokenpair_coverage')
    else:raise ValueError('accepted incomplete_tokenpair_coverage')
    bad_p2=deepcopy(p)
    for cc in bad_p2['cases']:
        if cc['base_key']=='b000':
            cc['candidates']=['n0_R_0']
            cc['context']=['n0_P0_0','n0_P1_2','n0_P2_0']
            cc['T']=['n0_Q0_0','n0_Q1_2','n0_Q2_0']
    try:check_matrix_coverage(bad_p2,desc)
    except ValueError:rejected.append('collapsed_restricted_codebook')
    else:raise ValueError('accepted collapsed_restricted_codebook')
    bad_tr1=deepcopy(transfer);bad_tr1['expr_transfer'][0]['adopted']=not bad_tr1['expr_transfer'][0]['adopted']
    try:transfer_audit(bad_tr1,rep_goals,networks,p)
    except ValueError:rejected.append('expr_transfer_table_tamper')
    else:raise ValueError('accepted expr_transfer_table_tamper')
    bad_tr2=deepcopy(transfer);bad_tr2['query_envelope'][-1]['tag']='empty'
    try:transfer_audit(bad_tr2,rep_goals,networks,p)
    except ValueError:rejected.append('capacity_envelope_tamper')
    else:raise ValueError('accepted capacity_envelope_tamper')
    require(len(rejected)==25,'25 mutations rejected')
    return rejected

def bundle(folder,p):
    read=lambda n:json.loads((folder/n).read_text(encoding='utf-8'))
    networks=SavedNetworks(folder,p);scalar=networks.verify_all();sources=read('sources.json');packets={k:export(v) for k,v in sources.items()};low=[audit_lower(sources[s['key']],s,p) for s in p['sources']]
    desc={s['key']:dict(predicate=s['predicate'],subject=s['observation']['start'],object=s['observation']['goal']) for s in p['sources']}
    cov_summary=check_matrix_coverage(p,desc)
    records=[r for i in range(18) for r in read('batch%02d.json'%i)];metrics=[r for i in range(18) for r in read('metrics%02d.json'%i)];cases={c['key']:c for c in p['cases']};expected={(c['key'],arm) for c in p['cases'] for arm in c['arms']}
    require(len(records)==len(metrics)==len(expected)==1440 and {(r['case'],r['arm']) for r in records}=={(r['case'],r['arm']) for r in metrics}==expected,'full frozen evaluations')
    require(all(math.isfinite(v) and v>=0 for m in metrics for k,v in m.items() if k.endswith('_seconds')),'finite measurement')
    rows=[audit(r,cases[r['case']],packets,p,networks) for r in records]
    role=read('roles.json');coverage,rep_goals=role_audit(role,networks,p)
    transfer=read('transfer.json');transfer_summary=transfer_audit(transfer,rep_goals,networks,p)
    capacity_summary=verify_ast_and_regime_coverage(rows,p)
    native={(r['base_key'],r['map_name']):r for r in rows if r['arm']=='native'};paired=[]
    iso_total=iso_sha_same=noniso_total=noniso_sha_changed=0
    iso_max_diff=0.0;noniso_max_diff=0.0;noniso_max_diff_by_n={str(n):0.0 for n in range(1,5)}
    for (base,name),r in sorted(native.items()):
        if name=='identity':continue
        b=native[(base,'identity')]
        sem_eq=all(r[k]==b[k] for k in FIELDS) and r['selected_code']==b['selected_code']
        el_diff=max([abs(x-y) for x,y in zip(r['eligibility'],b['eligibility'],strict=True)]+[abs(r['coverage_activation']-b['coverage_activation'])])
        sha_same=(r['state_sha256']==b['state_sha256'])
        if name in ISOMETRIC_MAPS:
            iso_total+=1;iso_sha_same+=int(sha_same);iso_max_diff=max(iso_max_diff,el_diff)
        else:
            noniso_total+=1;noniso_sha_changed+=int(not sha_same);noniso_max_diff=max(noniso_max_diff,el_diff)
            noniso_max_diff_by_n[str(r['capacity'])]=max(noniso_max_diff_by_n[str(r['capacity'])],el_diff)
        paired.append(dict(base_key=base,map_name=name,capacity=r['capacity'],semantic_equal=sem_eq,eligibility_max_abs_diff=el_diff,state_sha256_equal=sha_same))
    require(len(paired)==1120 and iso_total==320 and iso_sha_same==320 and iso_max_diff<=p['scalar_tolerance'] and noniso_total==800 and noniso_sha_changed>0,'isometric state invariance and non-isometric continuous perturbation')
    counts={name:dict(
        cases=len(rr:=[r for r in rows if r['arm']=='native' and r['map_name']==name]),
        strict=sum(r['strict_correct'] for r in rr),
        roles_total=sum(r['role_total'] for r in rr),
        roles_correct=sum(r['role_correct'] for r in rr),
        AST_total=sum(r['AST_total'] for r in rr),
        AST_correct=sum(r['AST_correct'] for r in rr),
        ticks=sum(r['ticks'] for r in rr),
        role_ticks=sum(r['role_ticks'] for r in rr),
        expr_ticks=sum(r['expr_ticks'] for r in rr),
        feasible_ticks=sum(r['feasible_ticks'] for r in rr),
        query_ticks=sum(r['query_ticks'] for r in rr),
        groups=sum(r['groups'] for r in rr),
        links=sum(r['links'] for r in rr)
    ) for name in p['codebooks']}
    id_counts=counts['identity']
    nonrole_tick_invariant=all(
        counts[name]['expr_ticks']==id_counts['expr_ticks'] and
        counts[name]['feasible_ticks']==id_counts['feasible_ticks'] and
        counts[name]['query_ticks']==id_counts['query_ticks']
        for name in p['codebooks']
    )
    require(nonrole_tick_invariant,'100% of upper tick variation across codebooks is confined to role_ticks across all capacities n=1..4')
    exact=[r for r in rows if r['arm']=='exact'];work=read('work-ledger.json');refs=Counter(n for r in records for n in r['network_ids'])
    refs.update(r['network_id'] for r in role)
    refs.update(r['network_id'] for r in transfer['expr_transfer'])
    refs.update(r['network_id'] for r in transfer['feasible_envelope'])
    refs.update(r['network_id'] for r in transfer['query_envelope'])
    require(sum(refs.values())==work['physical_recorded_calls']==29348 and set(refs)==set(networks),'all actual numerical references')
    probe_ticks=(
        sum(networks[x['network_id']]['cost']['kernel_ticks'] for x in role)+
        sum(networks[x['network_id']]['cost']['kernel_ticks'] for x in transfer['expr_transfer'])+
        sum(networks[x['network_id']]['cost']['kernel_ticks'] for x in transfer['feasible_envelope'])+
        sum(networks[x['network_id']]['cost']['kernel_ticks'] for x in transfer['query_envelope'])
    )
    calls=56+sum(r['physical_native_calls'] for r in rows)+1188
    ticks=sum(r['ticks'] for r in rows)+sum(x['ticks'] for x in low)+probe_ticks
    require(calls==29404 and ticks<=4704640 and work['completed'] and work['aggregate_cache_bytes']<=p['budget']['canonical_cache_bytes'],'physical ledger/resource cap')
    rejected=run_mutation_suite(records,cases,packets,p,networks,desc,role,transfer,rep_goals)
    quality=(
        all(r['strict_correct'] and r.get('intermediate_correct',True) for r in rows) and
        all(r['semantic_equal'] for r in paired) and
        coverage['wrong']==0 and
        transfer_summary['expr_bijection_class_wrong']==0 and
        transfer_summary['feasible_extremal_correct']==60 and
        transfer_summary['query_extremal_correct']==680 and
        nonrole_tick_invariant
    )
    exposure={}
    source_descriptors={s['key']:s for s in p['sources']}
    for name in p['codebooks']:
        hist=Counter();pairs_seen=set();bits_seen=set();hetero=0;triples_total=0
        for c in p['cases']:
            if c['map_name']!=name:continue
            code={token:i for i,token in enumerate(c['vocabulary'])}
            for ck in c['candidates']:
                a=source_descriptors[ck]['observation']['goal']
                for phase_facts in [c['context'],c['T']]:
                    triples_total+=1
                    ds=[]
                    for fk in phase_facts:
                        b=source_descriptors[fk]['observation']['start'];x,y=code[a],code[b];d=(x^y).bit_count();ds.append(d)
                        pairs_seen.add((x,y));hist[d]+=1;bits_seen.add(tuple((x>>i&1,y>>i&1) for i in range(3)))
                    if len({d for d in ds if d>0})>=2:hetero+=1
        exposure[name]=dict(
            actual_role_comparisons=sum(hist.values()),
            ordered_code_pairs_count=len(pairs_seen),
            ordered_code_pairs=sorted(pairs_seen),
            hamming_distance_histogram={str(k):v for k,v in sorted(hist.items())},
            bit_pair_patterns=len(bits_seen),
            heterogeneous_nonzero_hamming_triples=hetero,
            total_ast_input_triples=triples_total,
            changed_ordered_tokenpair_hamming=sum((i^j).bit_count()!=(p['codebooks'][name][i]^p['codebooks'][name][j]).bit_count() for i,j in itertools.product(range(8),repeat=2))
        )
    return dict(
        status='AUDITED',
        quality_pass=quality,
        finite_semantic_adoption=quality,
        counts=counts,
        nonrole_stage_ticks_invariant_across_codebooks=nonrole_tick_invariant,
        exact=dict(cases=len(exact),strict=sum(r['strict_correct'] for r in exact)),
        role_coverage=coverage,
        stage_transfer=transfer_summary,
        matrix_coverage=cov_summary,
        capacity_coverage=capacity_summary,
        state_perturbation=dict(
            isometric_pairs=iso_total,
            isometric_state_sha256_equal=iso_sha_same,
            isometric_eligibility_max_abs_diff=iso_max_diff,
            nonisometric_pairs=noniso_total,
            nonisometric_state_sha256_changed=noniso_sha_changed,
            nonisometric_eligibility_max_abs_diff=noniso_max_diff,
            nonisometric_eligibility_max_abs_diff_by_capacity=noniso_max_diff_by_n
        ),
        paired_conditions=1120,
        paired_invariant=sum(r['semantic_equal'] for r in paired),
        pairs=paired,
        physical_calls=calls,
        ticks=ticks,
        unique_traces=len(networks),
        max_scalar_error=max(scalar,max(x['numeric_replay_max_absolute_error'] for x in low)),
        mutation_rejections=rejected,
        actual_pipeline_coverage=exposure,
        source_calls=56,
        role_calls=64,
        expr_transfer_calls=384,
        feasible_envelope_calls=60,
        query_envelope_calls=680,
        stage_transfer_calls=1188,
        upper_pipeline_calls=28160,
        learning=0,
        world_measurement=0,
        production_adoption=False,
        statistical_speed_verdict=None
    ),rows
