"""Saved-data 8-token codebook coverage, 4-class Hamming role partition, 384 expr exhaustive transfer, and 80 extremal envelope audit."""
import itertools,json,math
from collections import Counter
from copy import deepcopy
from hcr.model import fingerprint
from tools.r32_semantic_join.runtime import require,export
from tools.r32_semantic_join.verify import audit_lower
from tools.r34_feasible_state.verify import tag
from tools.r35_compositional_slot.runtime import truth
from tools.r36_overlap_composition.verify import SavedNetworks,audit as prior_audit,mutations as prior_mutations

FIELDS=['kind','selected_index','value','reason','C_AST_values','T_AST_values','C_leaf_patterns','T_leaf_patterns']

def validate_map(c,p):
    mp=c['code_map'];v=c['canonical_vocabulary']
    require(len(mp)==len(v)==len(set(v))==8 and all(type(x) is int for x in mp) and sorted(mp)==list(range(8)),'3bit bijective map')
    require(mp==p['codebooks'][c['map_name']] and len(c['vocabulary'])==8,'frozen codebook')
    require(all(c['vocabulary'][mp[i]]==token for i,token in enumerate(v)),'inverse vocabulary encoder contract')

def check_matrix_coverage(p,desc):
    restricted={}
    for c in p['cases']:
        tokens=sorted({desc[k]['object'] for k in c['candidates']}|{desc[k]['subject'] for k in c['context']+c['T']})
        code={token:i for i,token in enumerate(c['vocabulary'])}
        sig=tuple((t,code[t]) for t in tokens)
        restricted.setdefault(c['base_key'],{})[c['map_name']]=sig
    classes_per_base=sorted({len(set(m.values())) for m in restricted.values()})
    unchanged=changed=0
    for maps in restricted.values():
        for name,sig in maps.items():
            if name=='identity':continue
            if sig==maps['identity']:unchanged+=1
            else:changed+=1
    require(classes_per_base==[8] and unchanged==0 and changed==896,'every base case 8 distinct restricted maps and 0 unchanged pairs')
    pairs_by_map={}
    for name in p['codebooks']:
        pairs_seen=set()
        for c in p['cases']:
            if c['map_name']!=name:continue
            code={token:i for i,token in enumerate(c['vocabulary'])}
            for ck in c['candidates']:
                a=desc[ck]['object']
                for fk in c['context']+c['T']:
                    b=desc[fk]['subject']
                    pairs_seen.add((code[a],code[b]))
        require(len(pairs_seen)==64,'all 64 ordered code pairs per codebook')
        pairs_by_map[name]=len(pairs_seen)
    return dict(restricted_map_classes_per_base=classes_per_base,mapped_pairs_actual_code_unchanged=unchanged,mapped_pairs_actual_code_changed=changed,ordered_code_pairs_per_map=pairs_by_map)

def audit(r,c,packets,p,networks):
    validate_map(c,p);require(r['map_name']==c['map_name'] and r['base_key']==c['base_key'],'record codebook identity')
    row=prior_audit(r,c,packets,p,networks);row.update(map_name=c['map_name'],base_key=c['base_key'])
    if r['arm']=='native':
        ks=[networks[name] for name in r['network_ids']]
        role_ks=[*ks[0:3],*ks[4:7],*ks[9:12],*ks[13:16]]
        expr_ks=[ks[3],ks[7],ks[12],ks[16]]
        feas_k=ks[8];query_k=ks[17]
        rt=sum(k['cost']['kernel_ticks'] for k in role_ks)
        et=sum(k['cost']['kernel_ticks'] for k in expr_ks)
        ft=feas_k['cost']['kernel_ticks']
        qt=query_k['cost']['kernel_ticks']
        require(rt+et+ft+qt==row['ticks'],'stage tick partition')
        row.update(role_ticks=rt,expr_ticks=et,feasible_ticks=ft,query_ticks=qt)
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
    require(checked==2580480 and wrong==0,'all40320mapping role checks')
    return dict(actual_numeric_inputs=64,numeric_correct=64-error,codebooks_role_only=40320,saved_lookup_checks=checked,wrong=wrong,first_counterexamples=first,hamming_class_goals={str(k):v for k,v in rep_goals.items()},hamming_class_ticks={str(k):v for k,v in rep_ticks.items()},max_within_class_goal_spread=max_class_spread,full_pipeline_codebooks=8,scope='all8token bijections role stage (4 Hamming equivalence classes), fixedProgramConfiginitial;not all fullpipeline executions'),rep_goals

def transfer_audit(transfer,rep_goals,networks,p):
    cfg=p['kernel'];gain=cfg['evidence_gain'];tol=p['scalar_tolerance']
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
    # Verify saved-lookup transfer for all 6 ASTs across all 8^3 = 512 boolean/Hamming patterns under all 40320 bijections
    # Since every bijection preserves (d==0) <=> (x==y) and maps each leaf comparison into d in {0,1,2,3}, any triple of leaf comparisons maps into {0,1,2,3}^3!
    expr_lookup_checks=0;expr_lookup_wrong=0
    for ei in range(6):
        for d0,d1,d2 in itertools.product(range(4),repeat=3):
            expr_lookup_checks+=40320
            if expr_table[(ei,d0,d1,d2)] is not truth(p['expressions'][ei],[d0==0,d1==0,d2==0]):
                expr_lookup_wrong+=40320
    require(expr_lookup_checks==384*40320 and expr_lookup_wrong==0,'exhaustive role->expr 40320 bijection class transfer')
    f_rows=transfer['feasible_envelope'];require(len(f_rows)==16,'16 feasible2 extremal rows')
    f_seen=set();elig_true=[];elig_false=[];cov_vals=[]
    for row in f_rows:
        f_seen.add((row['left_tag'],row['right_tag']))
        k=networks[row['network_id']]
        expected_drives={'e0':gain*(2*row['left_in']-1),'e1':gain*(2*row['right_in']-1),'complete':gain}
        require(k['program']==p['programs']['feasible2'] and all(abs(k['drives'][m]-expected_drives[m])<=tol for m in expected_drives),'feasible2 envelope Program/drives')
        kind=tag(k,['none','unique','many','incomplete'],cfg)
        b0,b1=row['left_bool'],row['right_bool']
        expected_kind='none' if not b0 and not b1 else 'unique' if b0!=b1 else 'many'
        el=[k['state']['e0'],k['state']['e1']]
        hi=(1+cfg['margin_threshold'])/2;lo=(1-cfg['margin_threshold'])/2
        require(kind==expected_kind and row['kind']==expected_kind,'feasible2 extremal semantic kind')
        require((el[0]>=hi if b0 else el[0]<=lo) and (el[1]>=hi if b1 else el[1]<=lo),'feasible2 extremal eligibility margins')
        for b_flag,ev in [(b0,el[0]),(b1,el[1])]:
            if b_flag:elig_true.append(ev)
            else:elig_false.append(ev)
        cov_vals.append(k['state']['complete'])
    require(len(f_seen)==16,'all 16 feasible2 extremal corners')
    q_rows=transfer['query_envelope'];require(len(q_rows)==64,'64 query2 extremal rows')
    q_seen=set()
    for row in q_rows:
        q_seen.add((row['e0_tag'],row['e1_tag'],row['t_tag']))
        k=networks[row['network_id']]
        ev0,ev1=row['e_in'];tv0,tv1=row['t_in'];cin=row['complete_in']
        expected_drives={'e0':gain*(2*ev0-1),'e1':gain*(2*ev1-1),'t0':gain*(2*tv0-1),'t1':gain*(2*tv1-1),'complete':gain*(2*cin-1)}
        require(k['program']==p['programs']['query2'] and all(abs(k['drives'][m]-expected_drives[m])<=tol for m in expected_drives),'query2 envelope Program/drives')
        qtag=tag(k,['qtrue','qfalse','empty','mixed','incomplete'],cfg)
        eb0,eb1=row['e_bool'];tb0,tb1=row['t_bool']
        vals=[tb for eb,tb in [(eb0,tb0),(eb1,tb1)] if eb]
        expected_tag='empty' if not vals else 'qtrue' if all(vals) else 'qfalse' if not any(vals) else 'mixed'
        require(qtag==expected_tag and row['tag']==expected_tag,'query2 extremal semantic tag')
    require(len(q_seen)==64,'all 64 query2 extremal corners')
    return dict(
        expr_exhaustive_triples=384,
        expr_correct=384,
        expr_bijection_class_checks=expr_lookup_checks,
        expr_bijection_class_wrong=expr_lookup_wrong,
        expr_false_goal_range=[min(false_vals),max(false_vals)],
        expr_true_goal_range=[min(true_vals),max(true_vals)],
        expr_ticks_by_ast={str(i):sorted(expr_ticks_by_ast[i]) for i in range(6)},
        feasible2_extremal_corners=16,
        feasible2_extremal_correct=16,
        feasible2_eligibility_false_range=[min(elig_false),max(elig_false)],
        feasible2_eligibility_true_range=[min(elig_true),max(elig_true)],
        feasible2_coverage_range=[min(cov_vals),max(cov_vals)],
        query2_extremal_corners=64,
        query2_extremal_correct=64,
        scope='role(64)->expr(384) is exhaustive across all 4^3 Hamming-distance triples for all 40320 3-bit bijections; feasible2(16) and query2(64) are extremal [min,max] interval-boundary checks, not 64^2 or 64^4 full product enumeration'
    )

def bundle(folder,p):
    read=lambda n:json.loads((folder/n).read_text(encoding='utf-8'))
    networks=SavedNetworks(folder,p);scalar=networks.verify_all();sources=read('sources.json');packets={k:export(v) for k,v in sources.items()};low=[audit_lower(sources[s['key']],s,p) for s in p['sources']]
    desc={s['key']:dict(predicate=s['predicate'],subject=s['observation']['start'],object=s['observation']['goal']) for s in p['sources']}
    cov_summary=check_matrix_coverage(p,desc)
    records=[r for i in range(18) for r in read('batch%02d.json'%i)];metrics=[r for i in range(18) for r in read('metrics%02d.json'%i)];cases={c['key']:c for c in p['cases']};expected={(c['key'],arm) for c in p['cases'] for arm in c['arms']}
    require(len(records)==len(metrics)==len(expected)==1152 and {(r['case'],r['arm']) for r in records}=={(r['case'],r['arm']) for r in metrics}==expected,'full frozen evaluations')
    require(all(math.isfinite(v) and v>=0 for m in metrics for k,v in m.items() if k.endswith('_seconds')),'finite measurement')
    rows=[audit(r,cases[r['case']],packets,p,networks) for r in records]
    role=read('roles.json');coverage,rep_goals=role_audit(role,networks,p)
    transfer=read('transfer.json');transfer_summary=transfer_audit(transfer,rep_goals,networks,p)
    native={(r['base_key'],r['map_name']):r for r in rows if r['arm']=='native'};paired=[]
    for (base,name),r in native.items():
        if name=='identity':continue
        b=native[(base,'identity')];paired.append(dict(base_key=base,map_name=name,semantic_equal=all(r[k]==b[k] for k in FIELDS)))
    require(len(paired)==896,'mapped-baseline pair coverage')
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
    # Check that non-role ticks (expr_ticks, feasible_ticks, query_ticks) are invariant across all 8 codebooks!
    id_counts=counts['identity']
    nonrole_tick_invariant=all(
        counts[name]['expr_ticks']==id_counts['expr_ticks'] and
        counts[name]['feasible_ticks']==id_counts['feasible_ticks'] and
        counts[name]['query_ticks']==id_counts['query_ticks']
        for name in p['codebooks']
    )
    require(nonrole_tick_invariant,'100% of upper tick variation across codebooks is confined to role_ticks')
    exact=[r for r in rows if r['arm']=='exact'];work=read('work-ledger.json');refs=Counter(n for r in records for n in r['network_ids'])
    refs.update(r['network_id'] for r in role)
    refs.update(r['network_id'] for r in transfer['expr_transfer'])
    refs.update(r['network_id'] for r in transfer['feasible_envelope'])
    refs.update(r['network_id'] for r in transfer['query_envelope'])
    require(sum(refs.values())==work['physical_recorded_calls']==18960 and set(refs)==set(networks),'all actual numerical references')
    probe_ticks=(
        sum(networks[x['network_id']]['cost']['kernel_ticks'] for x in role)+
        sum(networks[x['network_id']]['cost']['kernel_ticks'] for x in transfer['expr_transfer'])+
        sum(networks[x['network_id']]['cost']['kernel_ticks'] for x in transfer['feasible_envelope'])+
        sum(networks[x['network_id']]['cost']['kernel_ticks'] for x in transfer['query_envelope'])
    )
    calls=56+sum(r['physical_native_calls'] for r in rows)+64+384+80
    ticks=sum(r['ticks'] for r in rows)+sum(x['ticks'] for x in low)+probe_ticks
    require(calls==19016 and ticks<=3042560 and work['completed'] and work['aggregate_cache_bytes']<=p['budget']['canonical_cache_bytes'],'physical ledger/resource cap')
    target=next(r for r in records if r['arm']=='native');c=cases[target['case']];rejected=prior_mutations(target,c,packets,p,networks)
    bad=deepcopy(c);bad['code_map']=[0]*8
    try:audit(target,bad,packets,p,networks)
    except ValueError:rejected.append('nonbijective_map')
    else:raise ValueError('accepted map mutation')
    bad=deepcopy(role);bad[0]['left']=1
    try:role_audit(bad,networks,p)
    except ValueError:rejected.append('numeric_role_coverage')
    else:raise ValueError('accepted role coverage mutation')
    bad_p=deepcopy(p);bad_p['cases'][0]['context']=[bad_p['cases'][0]['candidates'][0]]*3
    try:check_matrix_coverage(bad_p,desc)
    except ValueError:rejected.append('incomplete_tokenpair_coverage')
    else:raise ValueError('accepted incomplete tokenpair coverage mutation')
    bad_p2=deepcopy(p)
    for cc in bad_p2['cases'][:8]:
        cc['candidates']=['n0_R_0','n0_R_1']
        cc['context']=['n0_P0_0','n0_P1_1','n0_P2_0']
        cc['T']=['n0_Q0_0','n0_Q1_1','n0_Q2_0']
    try:check_matrix_coverage(bad_p2,desc)
    except ValueError:rejected.append('collapsed_restricted_codebook')
    else:raise ValueError('accepted collapsed restricted codebook mutation')
    bad_tr=deepcopy(transfer);bad_tr['expr_transfer'][0]['adopted']=not bad_tr['expr_transfer'][0]['adopted']
    try:transfer_audit(bad_tr,rep_goals,networks,p)
    except ValueError:rejected.append('downstream_transfer_table_tamper')
    else:raise ValueError('accepted downstream transfer tamper')
    require(len(rejected)==21,'21 mutations rejected')
    quality=(
        all(r['strict_correct'] and r.get('intermediate_correct',True) for r in rows) and
        all(r['semantic_equal'] for r in paired) and
        coverage['wrong']==0 and
        transfer_summary['expr_bijection_class_wrong']==0 and
        transfer_summary['feasible2_extremal_correct']==16 and
        transfer_summary['query2_extremal_correct']==64 and
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
        paired_conditions=896,
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
        extremal_envelope_calls=80,
        upper_pipeline_calls=18432,
        learning=0,
        world_measurement=0,
        production_adoption=False,
        statistical_speed_verdict=None
    ),rows
