"""Saved-data 8-token 2-variable joint-tuple codebook coverage, 6-stage continuous transfer probe (809 settles), and sealed-binding invariance audit."""
import itertools,json,math
from collections import Counter
from copy import deepcopy
from hcr.model import fingerprint
from tools.r32_semantic_join.runtime import require,export
from tools.r32_semantic_join.verify import audit_lower
from tools.r34_feasible_state.verify import tag
from tools.r36_overlap_composition.verify import SavedNetworks
from tools.r37_joint_tuple.verify import audit as r37_audit,oracle

FIELDS=['kind',' normalized_selected','value','reason','tag','normalized_eligible','strict_correct','intervention_strict_correct','unnecessary_abstention','incorrect_assertion']
FIELDS=[f.strip() for f in FIELDS]
STAGE_TICK_KEYS=['role_ticks','pair_ticks','membership_ticks','projection_ticks','feasible_ticks','query_ticks']
ISOMETRIC_MAPS={'identity','bit_reverse','xor7'}

def validate_map(c,p):
    mp=c['code_map'];v=c['canonical_vocabulary']
    require(len(mp)==len(v)==len(set(v))==8 and all(type(x) is int for x in mp) and sorted(mp)==list(range(8)),'3bit bijective map')
    require(mp==p['codebooks'][c['map_name']] and len(c['vocabulary'])==8 and len(set(c['vocabulary']))==8,'frozen codebook')
    require(all(c['vocabulary'][mp[i]]==token for i,token in enumerate(v)),'inverse vocabulary encoder contract')

def check_matrix_coverage(p,desc):
    restricted={};active_tokens_global=set();token_base_counts=Counter()
    code_pairs_by_map={m:set() for m in p['codebooks']}
    hamming_classes_by_map={m:set() for m in p['codebooks']}
    hamming_pairs_by_map={m:set() for m in p['codebooks']}
    cross_facts_by_map={m:set() for m in p['codebooks']}
    parts_seen=Counter();orders_seen=Counter()
    for c in p['cases']:
        validate_map(c,p)
        d=c['domains']
        require(set(d)=={'X','Y'} and all(len(v)==len(set(v))==2 for v in d.values()) and len(set(d['X']+d['Y']))==4,'two disjoint 2-token domains')
        code={token:i for i,token in enumerate(c['vocabulary'])}
        tokens=sorted(set(d['X']+d['Y']))
        require(all(t in code for t in tokens),'active domain tokens in vocabulary')
        active_tokens_global.update(tokens)
        if c['map_name']=='identity':
            parts_seen[c['part']]+=1
            orders_seen[c['order']]+=1
            for t in tokens:token_base_counts[t]+=1
        sig=tuple((t,code[t]) for t in tokens)
        restricted.setdefault(c['base_key'],{})[c['map_name']]=sig
        for pred,fkeys in [('C',c['context']),('T',c['T'])]:
            for fk in fkeys:
                require(fk in desc,'relation source key in desc')
                fact=desc[fk]
                require(fact['predicate']==pred and fact['subject'] in d['X'] and fact['object'] in d['Y'] and fact['subject'] in code and fact['object'] in code,'fact endpoints in domain and vocabulary')
                cross_facts_by_map[c['map_name']].add((code[fact['subject']],code[fact['object']]))
                for a in c['alternatives']:
                    cx,fx=code[a['X']],code[fact['subject']]
                    cy,fy=code[a['Y']],code[fact['object']]
                    dx,dy=(cx^fx).bit_count(),(cy^fy).bit_count()
                    code_pairs_by_map[c['map_name']].update([(cx,fx),(cy,fy)])
                    hamming_classes_by_map[c['map_name']].update([dx,dy])
                    hamming_pairs_by_map[c['map_name']].add((dx,dy))
    require(dict(sorted(parts_seen.items()))=={'I':16,'II':8,'III':8} and dict(sorted(orders_seen.items()))=={0:16,1:16},'32 base cases (16 Part I, 8 Part II, 8 Part III; 16 order=0, 16 order=1)')
    require(len(active_tokens_global)==8 and set(active_tokens_global)==set(p['canonical_vocabulary']),'all 8 canonical tokens active in joint-tuple pipeline')
    classes_per_base=sorted({len(set(m.values())) for m in restricted.values()})
    unchanged_cases=changed_cases=0
    for maps in restricted.values():
        for name,sig in maps.items():
            if name=='identity':continue
            if sig==maps['identity']:unchanged_cases+=1
            else:changed_cases+=1
    require(classes_per_base==[8] and unchanged_cases==0 and changed_cases==224,'every base context 8 distinct restricted maps and 0 unchanged pairs')
    for m in p['codebooks']:
        require(len(code_pairs_by_map[m])==64 and hamming_classes_by_map[m]=={0,1,2,3} and len(hamming_pairs_by_map[m])==16 and len(cross_facts_by_map[m])==56,'all 64 ordered code pairs, 16 ordered Hamming pairs, and 56 cross-domain fact pairs per codebook '+m)
    return dict(
        base_cases_by_part=dict(sorted(parts_seen.items())),
        base_cases_by_order={str(k):v for k,v in sorted(orders_seen.items())},
        restricted_map_classes_per_base=classes_per_base,
        mapped_case_pairs_unchanged=unchanged_cases,
        mapped_case_pairs_changed=changed_cases,
        mapped_native_arm_pairs_unchanged=2*unchanged_cases,
        mapped_native_arm_pairs_changed=2*changed_cases,
        active_tokens_count=len(active_tokens_global),
        token_base_participation=dict(sorted(token_base_counts.items())),
        ordered_code_pairs_per_map={m:len(v) for m,v in sorted(code_pairs_by_map.items())},
        hamming_classes_per_map={m:sorted(v) for m,v in sorted(hamming_classes_by_map.items())},
        ordered_hamming_pairs_per_map={m:len(v) for m,v in sorted(hamming_pairs_by_map.items())},
        cross_domain_fact_pairs_per_map={m:len(v) for m,v in sorted(cross_facts_by_map.items())}
    )

def audit(r,c,packets,p,networks):
    validate_map(c,p)
    require(r['case']==c['key'] and r['base_key']==c['base_key'] and r['map_name']==c['map_name'] and r['part']==c['part'] and r['order']==c['order'] and r['namespace']==c['namespace'],'record case/base/map/part/order/namespace identity')
    row=r37_audit(r,c,packets,p,networks)
    arm=r['arm'];target=row['closure'] if arm=='native_marginal' else row['truth']
    expected_tag='empty' if not target['feasible'] else 'qtrue' if target['value'] is True else 'qfalse' if target['value'] is False else 'mixed'
    stage_ticks={k:0 for k in STAGE_TICK_KEYS}
    if arm=='exact_joint':
        row.update(
            base_key=c['base_key'],map_name=c['map_name'],part=c['part'],
            tag=expected_tag,state_sha256=None,binding_sha256=None,binding_floats=[],
            **stage_ticks
        )
    else:
        require(r['final']['tag']==expected_tag,'final query4 tag matches intervention oracle')
        ks=[networks[n] for n in r['network_ids']];cursor=0
        C_len=len(c['context']);T_len=len(c['T'])
        for _ in range(4):
            for _ in range(C_len):
                stage_ticks['role_ticks']+=ks[cursor]['cost']['kernel_ticks']+ks[cursor+1]['cost']['kernel_ticks']
                stage_ticks['pair_ticks']+=ks[cursor+2]['cost']['kernel_ticks']
                cursor+=3
            stage_ticks['membership_ticks']+=ks[cursor]['cost']['kernel_ticks'];cursor+=1
        hi=(1+p['kernel']['margin_threshold'])/2;lo=(1-p['kernel']['margin_threshold'])/2
        if arm=='native_marginal':
            proj_k=ks[cursor];stage_ticks['projection_ticks']+=proj_k['cost']['kernel_ticks'];cursor+=1
            layout=[[0,0],[0,1],[1,0],[1,1]] if not c['order'] else [[1,1],[1,0],[0,1],[0,0]]
            act={tuple(layout[i]) for i,b in enumerate(row['truth']['eligible']) if b}
            xs={x for x,y in act};ys={y for x,y in act}
            exp_p={'p00':0 in xs,'p01':1 in xs,'p10':0 in ys,'p11':1 in ys}
            for pk,b_flag in exp_p.items():
                pv=proj_k['state'][pk]
                require(pv>=hi if b_flag else pv<=lo,'projection internal marginal state margin '+pk)
            for i,b_flag in enumerate(row['closure']['eligible']):
                ev=proj_k['state']['e'+str(i)]
                require(ev>=hi if b_flag else ev<=lo,'projection output e margin '+str(i))
        feas_k=ks[cursor];stage_ticks['feasible_ticks']+=feas_k['cost']['kernel_ticks'];cursor+=1
        for i,b_flag in enumerate(target['eligible']):
            ev=r['binding']['eligibility'][i]
            require(ev>=hi if b_flag else ev<=lo,'strict feasible4 eligibility margin separation')
        require(r['binding']['coverage_activation']>=hi,'strict feasible4 coverage margin separation')
        for _ in range(4):
            for _ in range(T_len):
                stage_ticks['role_ticks']+=ks[cursor]['cost']['kernel_ticks']+ks[cursor+1]['cost']['kernel_ticks']
                stage_ticks['pair_ticks']+=ks[cursor+2]['cost']['kernel_ticks']
                cursor+=3
            stage_ticks['membership_ticks']+=ks[cursor]['cost']['kernel_ticks'];cursor+=1
        query_k=ks[cursor];stage_ticks['query_ticks']+=query_k['cost']['kernel_ticks'];cursor+=1
        require(cursor==len(ks) and sum(stage_ticks.values())==row['ticks'],'exact 6-stage tick partition')
        row.update(
            base_key=c['base_key'],map_name=c['map_name'],part=c['part'],
            tag=r['final']['tag'],
            state_sha256=r['binding']['state_sha256'],
            binding_sha256=r['final']['binding_sha256'],
            binding_floats=list(r['binding']['eligibility'])+[r['binding']['coverage_activation']],
            **stage_ticks
        )
    return row

def role_audit(role,networks,p):
    require(len(role)==64 and {(x['left'],x['right']) for x in role}==set(itertools.product(range(8),repeat=2)),'all numeric role inputs')
    table={};cfg=p['kernel'];gain=cfg['evidence_gain'];by_d={d:[] for d in range(4)};ticks_by_d={d:set() for d in range(4)};error=0
    for r in role:
        k=networks[r['network_id']];drives={s+str(i):gain*(1 if (v>>i)&1 else -1) for s,v in [('x',r['left']),('y',r['right'])] for i in range(3)}
        d=(r['left']^r['right']).bit_count()
        require(r['hamming']==d and k['program']==p['programs']['role'] and k['drives']==drives and all(v==.5 for v in k['initial'].values()),'role Program/Config/drive/initial/Hamming coverage')
        table[(r['left'],r['right'])]=k['adopted'];by_d[d].append(k['state']['goal']);ticks_by_d[d].add(k['cost']['kernel_ticks'])
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
        scope='all 8-token bijections role stage (4 Hamming equivalence classes), fixed Program/Config/initial'
    ),rep_goals

def transfer_audit(transfer,rep_goals,networks,p):
    cfg=p['kernel'];gain=cfg['evidence_gain'];tol=p['scalar_tolerance']
    hi=(1+cfg['margin_threshold'])/2;lo=(1-cfg['margin_threshold'])/2
    # 1. pair_transfer (16 exhaustive Hamming-pair settles)
    pair_rows=transfer['pair_transfer'];require(len(pair_rows)==16,'16 exhaustive pair Hamming-pair rows')
    seen_pair=set();pair_true=[];pair_false=[];pair_ticks=set();pair_table={}
    for row in pair_rows:
        d0,d1=row['hamming_pair']
        require(d0 in [0,1,2,3] and d1 in [0,1,2,3],'valid Hamming pair')
        seen_pair.add((d0,d1))
        k=networks[row['network_id']]
        expected_drives={'m0':gain*(2*rep_goals[d0]-1),'m1':gain*(2*rep_goals[d1]-1),'m2':-gain}
        require(k['program']==p['programs']['pair'] and all(abs(k['drives'][m]-expected_drives[m])<=tol for m in expected_drives) and all(v==.5 for v in k['initial'].values()),'pair transfer Program/drives/initial')
        expected_bool=(d0==0 and d1==0)
        require(row['expected'] is expected_bool and k['adopted'] is expected_bool and row['adopted'] is expected_bool and abs(row['goal']-k['state']['goal'])<=tol and row['ticks']==k['cost']['kernel_ticks'],'pair transfer semantic and scalar consistency')
        if expected_bool:pair_true.append(k['state']['goal'])
        else:pair_false.append(k['state']['goal'])
        pair_ticks.add(k['cost']['kernel_ticks']);pair_table[(d0,d1)]=k['adopted']
    require(len(seen_pair)==16 and len(pair_true)==1 and len(pair_false)==15,'all 16 pair Hamming pairs covered')
    pair_lookup_checks=0;pair_lookup_wrong=0
    for d0,d1 in itertools.product(range(4),repeat=2):
        pair_lookup_checks+=40320
        if pair_table[(d0,d1)] is not (d0==0 and d1==0):pair_lookup_wrong+=40320
    require(pair_lookup_checks==16*40320 and pair_lookup_wrong==0,'exhaustive role->pair 40320 bijection class transfer')
    # 2. or_transfer (1 + 3 + 9 + 27 + 81 = 121 settles across or0..4)
    or_rows=transfer['or_transfer'];require(len(or_rows)==121,'121 or0..4 extremal rows')
    or_seen=set();m_true=[];m_false=[];or_ticks_by_arity={L:set() for L in range(5)}
    for row in or_rows:
        L=row['arity'];tags=tuple(row['input_tags']);bools=row['input_bools'];vals=row['input_vals']
        require(0<=L<=4 and len(tags)==len(bools)==len(vals)==L,'valid or0..4 row')
        or_seen.add((L,tags))
        k=networks[row['network_id']]
        expected_drives={'m'+str(i):gain*(2*vals[i]-1) for i in range(L)}
        require(k['program']==p['programs']['or'+str(L)] and set(k['drives'])==set(expected_drives) and all(abs(k['drives'][m]-expected_drives[m])<=tol for m in expected_drives),'or0..4 Program/drives')
        expected_bool=any(bools)
        require(row['expected'] is expected_bool and k['adopted'] is expected_bool and row['adopted'] is expected_bool and abs(row['goal']-k['state']['goal'])<=tol and row['ticks']==k['cost']['kernel_ticks'],'or0..4 semantic and scalar consistency')
        if expected_bool:m_true.append(k['state']['goal'])
        else:m_false.append(k['state']['goal'])
        or_ticks_by_arity[L].add(k['cost']['kernel_ticks'])
    require(len(or_seen)==121 and m_true and m_false,'all 121 or0..4 extremal combinations covered')
    mf_max=max(m_false);mt_min=min(m_true)
    # 3. projection_envelope (16 + 16 = 32 settles across projection0 and projection1)
    proj_rows=transfer['projection_envelope'];require(len(proj_rows)==32,'32 projection0/1 extremal rows')
    proj_seen=set();proj_true=[];proj_false=[];proj_ticks={0:set(),1:set()};closure_sigs={0:set(),1:set()}
    for row in proj_rows:
        order=row['order'];f_bool=row['f_bool']
        require(order in [0,1] and len(f_bool)==4 and all(type(b) is bool for b in f_bool),'valid projection row')
        proj_seen.add((order,tuple(f_bool)))
        k=networks[row['network_id']]
        expected_f_in=[mt_min if b else mf_max for b in f_bool]
        expected_drives={'f'+str(i):gain*(2*expected_f_in[i]-1) for i in range(4)}
        require(k['program']==p['programs']['projection'+str(order)] and all(abs(k['drives'][m]-expected_drives[m])<=tol for m in expected_drives),'projection Program/drives')
        layout=[[0,0],[0,1],[1,0],[1,1]] if order==0 else [[1,1],[1,0],[0,1],[0,0]]
        act={tuple(layout[i]) for i,b in enumerate(f_bool) if b}
        xs={x for x,y in act};ys={y for x,y in act}
        exp_p={'p00':0 in xs,'p01':1 in xs,'p10':0 in ys,'p11':1 in ys}
        exp_e=[(layout[i][0] in xs and layout[i][1] in ys) for i in range(4)]
        exp_goal=any(exp_e)
        require(row['expected_e']==exp_e and row['adopted'] is exp_goal and k['adopted'] is exp_goal and row['ticks']==k['cost']['kernel_ticks'],'projection semantic and tick consistency')
        for pk,b_flag in exp_p.items():
            pv=k['state'][pk]
            require(abs(row['p_state'][pk]-pv)<=tol and (pv>=hi if b_flag else pv<=lo),'projection internal p_state margin '+pk)
        for i,b_flag in enumerate(exp_e):
            ev=k['state']['e'+str(i)]
            require(abs(row['e_out'][i]-ev)<=tol and (ev>=hi if b_flag else ev<=lo),'projection e_out margin '+str(i))
            if b_flag:proj_true.append(ev)
            else:proj_false.append(ev)
        norm_sig=tuple(i for i,b in enumerate(exp_e if order==0 else exp_e[::-1]) if b)
        closure_sigs[order].add(norm_sig)
        proj_ticks[order].add(k['cost']['kernel_ticks'])
    require(len(proj_seen)==32 and len(closure_sigs[0])==10 and len(closure_sigs[1])==10,'all 32 projection0/1 corners and 10/16 marginal-closure signatures verified')
    pf_max=max(proj_false);pt_min=min(proj_true)
    # 4. feasible_envelope (32 direct_or + 32 via_projection = 64 settles on feasible4)
    f_rows=transfer['feasible_envelope'];require(len(f_rows)==64,'64 feasible4 extremal rows')
    f_seen=set();ef_all=[];et_all=[];cf_all=[];ct_all=[];f_ticks_by_src={'direct_or':set(),'via_projection':set()}
    for row in f_rows:
        src=row['source_kind'];e_bool=row['e_bool'];comp_bool=row['complete_bool']
        require(src in ['direct_or','via_projection'] and len(e_bool)==4 and type(comp_bool) is bool,'feasible4 envelope shape')
        f_seen.add((src,tuple(e_bool),comp_bool))
        f_hi,t_lo=(mf_max,mt_min) if src=='direct_or' else (pf_max,pt_min)
        expected_e_in=[t_lo if b else f_hi for b in e_bool]
        expected_drives={'e'+str(i):gain*(2*expected_e_in[i]-1) for i in range(4)}
        expected_drives['complete']=gain*(1 if comp_bool else -1)
        k=networks[row['network_id']]
        require(k['program']==p['programs']['feasible'] and all(abs(k['drives'][m]-expected_drives[m])<=tol for m in expected_drives),'feasible4 envelope Program/drives')
        kind=tag(k,['none','unique','many','incomplete'],cfg)
        cnt=sum(e_bool)
        expected_kind='incomplete' if not comp_bool else 'none' if cnt==0 else 'unique' if cnt==1 else 'many'
        el=[k['state']['e'+str(i)] for i in range(4)];cov=k['state']['complete']
        require(kind==expected_kind and row['kind']==expected_kind,'feasible4 extremal semantic kind')
        require(all((el[i]>=hi if e_bool[i] else el[i]<=lo) for i in range(4)),'feasible4 extremal eligibility margins')
        require((cov>=hi if comp_bool else cov<=lo),'feasible4 extremal coverage margin')
        for b_flag,ev in zip(e_bool,el,strict=True):
            if b_flag:et_all.append(ev)
            else:ef_all.append(ev)
        if comp_bool:ct_all.append(cov)
        else:cf_all.append(cov)
        f_ticks_by_src[src].add(k['cost']['kernel_ticks'])
    require(len(f_seen)==64,'all 64 feasible4 extremal corners covered')
    ef_max=max(ef_all);et_min=min(et_all);cf_max=max(cf_all);ct_min=min(ct_all)
    # 5. query_envelope (2^9 = 512 settles on query4)
    q_rows=transfer['query_envelope'];require(len(q_rows)==512,'512 query4 extremal rows')
    q_seen=set();q_tags=Counter();q_ticks=set()
    for row in q_rows:
        e_bool=row['e_bool'];t_bool=row['t_bool'];comp_bool=row['complete_bool']
        require(len(e_bool)==len(t_bool)==4 and type(comp_bool) is bool,'query4 envelope shape')
        q_seen.add((tuple(e_bool),tuple(t_bool),comp_bool))
        expected_e_in=[et_min if b else ef_max for b in e_bool]
        expected_t_in=[mt_min if b else mf_max for b in t_bool]
        expected_c_in=ct_min if comp_bool else cf_max
        expected_drives={'e'+str(i):gain*(2*expected_e_in[i]-1) for i in range(4)}
        expected_drives.update({'t'+str(i):gain*(2*expected_t_in[i]-1) for i in range(4)})
        expected_drives['complete']=gain*(2*expected_c_in-1)
        k=networks[row['network_id']]
        require(k['program']==p['programs']['query'] and all(abs(k['drives'][m]-expected_drives[m])<=tol for m in expected_drives),'query4 envelope Program/drives')
        qtag=tag(k,['qtrue','qfalse','empty','mixed','incomplete'],cfg)
        vals=[tb for eb_f,tb in zip(e_bool,t_bool,strict=True) if eb_f]
        expected_tag='incomplete' if not comp_bool else 'empty' if not vals else 'qtrue' if all(vals) else 'qfalse' if not any(vals) else 'mixed'
        require(qtag==expected_tag and row['tag']==expected_tag,'query4 extremal semantic tag')
        q_tags[qtag]+=1;q_ticks.add(k['cost']['kernel_ticks'])
    require(len(q_seen)==512 and set(q_tags)=={'qtrue','qfalse','empty','mixed','incomplete'},'all 512 query4 extremal corners and 5 tags covered')
    return dict(
        pair_exhaustive_pairs=16,
        pair_correct=16,
        pair_bijection_class_checks=pair_lookup_checks,
        pair_bijection_class_wrong=pair_lookup_wrong,
        pair_false_goal_range=[min(pair_false),max(pair_false)],
        pair_true_goal=pair_true[0],
        pair_ticks=sorted(pair_ticks),
        or_extremal_combinations=121,
        or_correct=121,
        membership_false_goal_range=[min(m_false),max(m_false)],
        membership_true_goal_range=[min(m_true),max(m_true)],
        or_ticks_by_arity={str(L):sorted(or_ticks_by_arity[L]) for L in range(5)},
        projection_extremal_corners=32,
        projection_correct=32,
        projection_closure_signatures_order0=len(closure_sigs[0]),
        projection_closure_signatures_order1=len(closure_sigs[1]),
        projection_false_e_range=[min(proj_false),max(proj_false)],
        projection_true_e_range=[min(proj_true),max(proj_true)],
        projection_ticks_by_order={str(o):sorted(proj_ticks[o]) for o in [0,1]},
        feasible4_extremal_corners=64,
        feasible4_correct=64,
        feasible4_eligibility_false_range=[min(ef_all),max(ef_all)],
        feasible4_eligibility_true_range=[min(et_all),max(et_all)],
        feasible4_coverage_false_range=[min(cf_all),max(cf_all)],
        feasible4_coverage_true_range=[min(ct_all),max(ct_all)],
        feasible4_ticks_by_source={k:sorted(v) for k,v in f_ticks_by_src.items()},
        query4_extremal_corners=512,
        query4_correct=512,
        query4_tag_counts=dict(sorted(q_tags.items())),
        query4_ticks=sorted(q_ticks),
        total_stage_transfer_settles=809,
        scope='role(64)->pair(16) is exhaustive across all 4^2 Hamming-distance pairs for all 40320 3-bit bijections; or0..4(121), projection0/1(32), feasible4(64), and query4(512) are extremal inner-margin [false_max, true_min] boundary checks across the 6-stage joint-tuple chain, not 64^n full product enumeration'
    )

def verify_regime_and_signature_coverage(rows):
    by_arm={}
    for arm in ['exact_joint','native_joint','native_marginal']:
        sub=[r for r in rows if r['arm']==arm]
        p1=[r for r in sub if r['part']=='I']
        p2=[r for r in sub if r['part']=='II']
        p3=[r for r in sub if r['part']=='III']
        require(len(sub)==256 and len(p1)==128 and len(p2)==64 and len(p3)==64,'256 evaluations (128 Part I, 64 Part II, 64 Part III) per arm')
        sigs_p1={tuple(r['normalized_eligible']) for r in p1 if r['map_name']=='identity'}
        require(len(sigs_p1)==(10 if arm=='native_marginal' else 16),'Part I 16/16 joint vs 10/16 marginal-closure distinct eligibility signatures')
        require(all(r['intervention_strict_correct'] and r['intervention_eligibility_correct']==4 and not r['incorrect_assertion'] for r in sub),'100% intervention accuracy and 0 false assertions across all 256 evaluations of '+arm)
        if arm in ['exact_joint','native_joint']:
            require(all(r['strict_correct'] and r['tuple_eligibility_correct']==4 and not r['unnecessary_abstention'] for r in sub),'100% full-truth accuracy for '+arm)
            require(set(r['tag'] for r in sub)=={'empty','qtrue','qfalse','mixed'},'all 4 complete query4 tags realized in upper pipeline by '+arm)
            require(Counter(r['tag'] for r in p2)=={'qtrue':32,'qfalse':32} and Counter(r['tag'] for r in p3)=={'qtrue':32,'qfalse':32},'balanced qtrue/qfalse truth on Part II and Part III counterexamples')
        else:
            require(all(r['strict_correct'] and not r['unnecessary_abstention'] for r in p1),'100% full-truth agreement on Part I for native_marginal')
            require(all(not r['strict_correct'] and r['unnecessary_abstention'] and r['tag']=='mixed' and r['value'] is None and r['reason']=='abstain_ambiguous' for r in p2+p3),'100% correlation-loss mixed abstention on Part II (64) and Part III (64) for native_marginal')
        by_arm[arm]=dict(
            distinct_part1_signatures=len(sigs_p1),
            part1_strict_correct=sum(r['strict_correct'] for r in p1),
            part2_strict_correct=sum(r['strict_correct'] for r in p2),
            part3_strict_correct=sum(r['strict_correct'] for r in p3),
            part2_abstentions=sum(r['unnecessary_abstention'] for r in p2),
            part3_abstentions=sum(r['unnecessary_abstention'] for r in p3),
            incorrect_assertions=sum(r['incorrect_assertion'] for r in sub),
            tags=dict(Counter(r['tag'] for r in sub)),
            kinds=dict(Counter(r['kind'] for r in sub))
        )
    return by_arm

def run_mutation_suite(records,cases,packets,p,networks,desc,role,transfer,rep_goals):
    r_joint=next(r for r in records if r['arm']=='native_joint' and cases[r['case']]['c_mask']==6 and cases[r['case']]['t_mask']==6)
    c_joint=cases[r_joint['case']]
    r_marg=next(r for r in records if r['arm']=='native_marginal' and cases[r['case']]['c_mask']==6 and cases[r['case']]['t_mask']==6)
    c_marg=cases[r_marg['case']]
    rejected=[]
    single_mutations=[
        ('revision',lambda x:x['binding'].update(revision=2)),
        ('source',lambda x:x['binding']['constraint_origin_refs'].__setitem__(0,'wrong')),
        ('variables',lambda x:x['binding'].update(variables=['Y','X'])),
        ('tuple',lambda x:x['binding']['alternatives'][0].update(Y='wrong')),
        ('eligibility',lambda x:x['binding']['eligibility'].__setitem__(0,.5)),
        ('messages',lambda x:x['messages'].__setitem__(0,.5)),
        ('applied',lambda x:x['applied'].__setitem__(0,.5)),
        ('state_hash',lambda x:x['binding'].update(state_sha256='wrong')),
        ('T_hash',lambda x:x['final'].update(T_sha256='wrong')),
        ('value',lambda x:x.update(value=not x['value'])),
        ('selected',lambda x:x.update(selected_index=99)),
        ('network_ref',lambda x:x['network_ids'].__setitem__(0,x['network_ids'][-1])),
        ('binding_hash',lambda x:x['final'].update(binding_sha256='wrong')),
        ('coverage_activation',lambda x:x['binding'].update(coverage_activation=.5)),
        ('final_tag_tamper',lambda x:x['final'].update(tag='empty')),
    ]
    for name,change in single_mutations:
        bad=deepcopy(r_joint);change(bad)
        try:audit(bad,c_joint,packets,p,networks)
        except ValueError:rejected.append(name)
        else:raise ValueError('accepted mutation '+name)
    bad_m=deepcopy(r_marg);bad_m['applied']=list(bad_m['messages'])
    try:audit(bad_m,c_marg,packets,p,networks)
    except ValueError:rejected.append('marginal_projection_bypass')
    else:raise ValueError('accepted mutation marginal_projection_bypass')
    bad_c1=deepcopy(c_joint);bad_c1['code_map']=[0]*8
    try:audit(r_joint,bad_c1,packets,p,networks)
    except ValueError:rejected.append('nonbijective_map')
    else:raise ValueError('accepted mutation nonbijective_map')
    bad_c2=deepcopy(c_joint);bad_c2['vocabulary']=list(reversed(bad_c2['vocabulary']))
    try:audit(r_joint,bad_c2,packets,p,networks)
    except ValueError:rejected.append('inverse_vocab_mismatch')
    else:raise ValueError('accepted mutation inverse_vocab_mismatch')
    bad_role=deepcopy(role);bad_role[0]['left']=1
    try:role_audit(bad_role,networks,p)
    except ValueError:rejected.append('numeric_role_coverage')
    else:raise ValueError('accepted mutation numeric_role_coverage')
    bad_p1=deepcopy(p)
    b00_by_map={cc['map_name']:cc for cc in bad_p1['cases'] if cc['base_key']=='b00'}
    for cc in bad_p1['cases']:
        ref=b00_by_map[cc['map_name']]
        cc['domains']=deepcopy(ref['domains'])
        cc['alternatives']=deepcopy(ref['alternatives'])
        cc['context']=list(ref['context'])
        cc['T']=list(ref['T'])
    try:check_matrix_coverage(bad_p1,desc)
    except ValueError:rejected.append('incomplete_codepair_coverage')
    else:raise ValueError('accepted mutation incomplete_codepair_coverage')
    bad_p2=deepcopy(p)
    for cc in bad_p2['cases']:
        if cc['base_key']=='b00':
            cc['domains']=dict(X=['amber','cobalt'],Y=['jade','violet'])
            cc['alternatives']=[dict(X=x,Y=y) for x in ['amber','cobalt'] for y in ['jade','violet']]
            cc['context']=['C_0_2']
            cc['T']=['T_1_3']
    try:check_matrix_coverage(bad_p2,desc)
    except ValueError:rejected.append('collapsed_restricted_codebook')
    else:raise ValueError('accepted mutation collapsed_restricted_codebook')
    bad_tr1=deepcopy(transfer);bad_tr1['pair_transfer'][0]['adopted']=not bad_tr1['pair_transfer'][0]['adopted']
    try:transfer_audit(bad_tr1,rep_goals,networks,p)
    except ValueError:rejected.append('pair_transfer_tamper')
    else:raise ValueError('accepted mutation pair_transfer_tamper')
    bad_tr2=deepcopy(transfer);bad_tr2['projection_envelope'][0]['e_out'][0]=.5
    try:transfer_audit(bad_tr2,rep_goals,networks,p)
    except ValueError:rejected.append('projection_envelope_tamper')
    else:raise ValueError('accepted mutation projection_envelope_tamper')
    bad_tr3=deepcopy(transfer);bad_tr3['feasible_envelope'][0]['kind']='many'
    try:transfer_audit(bad_tr3,rep_goals,networks,p)
    except ValueError:rejected.append('feasible4_envelope_tamper')
    else:raise ValueError('accepted mutation feasible4_envelope_tamper')
    bad_tr4=deepcopy(transfer);bad_tr4['query_envelope'][-1]['tag']='empty'
    try:transfer_audit(bad_tr4,rep_goals,networks,p)
    except ValueError:rejected.append('query4_envelope_tamper')
    else:raise ValueError('accepted mutation query4_envelope_tamper')
    require(len(rejected)==25,'25 mutations rejected')
    return rejected

def bundle(folder,p):
    read=lambda n:json.loads((folder/n).read_text(encoding='utf-8'))
    networks=SavedNetworks(folder,p);scalar=networks.verify_all();sources=read('sources.json');packets={k:export(v) for k,v in sources.items()};low=[audit_lower(sources[s['key']],s,p) for s in p['sources']]
    desc={s['key']:dict(predicate=s['predicate'],subject=s['observation']['start'],object=s['observation']['goal']) for s in p['sources']}
    cov_summary=check_matrix_coverage(p,desc)
    records=[r for i in range(12) for r in read('batch%02d.json'%i)];metrics=[r for i in range(12) for r in read('metrics%02d.json'%i)];cases={c['key']:c for c in p['cases']};expected={(c['key'],arm) for c in p['cases'] for arm in c['arms']}
    require(len(records)==len(metrics)==len(expected)==768 and {(r['case'],r['arm']) for r in records}=={(r['case'],r['arm']) for r in metrics}==expected,'full frozen 768 evaluations')
    require(all(math.isfinite(v) and v>=0 for m in metrics for k,v in m.items() if k.endswith('_seconds')),'finite measurement')
    rows=[audit(r,cases[r['case']],packets,p,networks) for r in records]
    role=read('roles.json');coverage,rep_goals=role_audit(role,networks,p)
    transfer=read('transfer.json');transfer_summary=transfer_audit(transfer,rep_goals,networks,p)
    regime_summary=verify_regime_and_signature_coverage(rows)
    native_arms=['native_joint','native_marginal']
    by_base_arm_map={(r['base_key'],r['arm'],r['map_name']):r for r in rows if r['arm'] in native_arms}
    paired=[];iso_total=iso_state_same=iso_bind_same=noniso_total=noniso_state_changed=noniso_bind_changed=0
    iso_max_diff=0.0;noniso_max_diff=0.0
    for (base,arm,name),r in sorted(by_base_arm_map.items()):
        if name=='identity':continue
        b=by_base_arm_map[(base,arm,'identity')]
        sem_eq=all(r[k]==b[k] for k in FIELDS) and r['first_failed_intermediate']==b['first_failed_intermediate']==None
        b_diff=max(abs(x-y) for x,y in zip(r['binding_floats'],b['binding_floats'],strict=True))
        st_same=(r['state_sha256']==b['state_sha256'])
        bd_same=(r['binding_sha256']==b['binding_sha256'])
        if name in ISOMETRIC_MAPS:
            iso_total+=1;iso_state_same+=int(st_same);iso_bind_same+=int(bd_same);iso_max_diff=max(iso_max_diff,b_diff)
        else:
            noniso_total+=1;noniso_state_changed+=int(not st_same);noniso_bind_changed+=int(not bd_same);noniso_max_diff=max(noniso_max_diff,b_diff)
        paired.append(dict(base_key=base,arm=arm,map_name=name,part=r['part'],semantic_equal=sem_eq,binding_max_abs_diff=b_diff,state_sha256_equal=st_same,binding_sha256_equal=bd_same))
    require(len(paired)==448 and all(x['semantic_equal'] for x in paired),'all 448 paired non-identity vs identity evaluations semantically invariant')
    require(iso_total==128 and iso_state_same==128 and iso_bind_same==128 and iso_max_diff<=p['scalar_tolerance'] and noniso_total==320 and noniso_state_changed>0 and noniso_bind_changed>0,'isometric state invariance and non-isometric continuous binding perturbation')
    counts={};counts_by_arm={}
    sums=['strict_correct','intervention_strict_correct','tuple_eligibility_correct','intervention_eligibility_correct','tuple_total','pre_membership_correct','unnecessary_abstention','incorrect_assertion','role_total','role_correct','pair_total','pair_correct','membership_total','membership_correct','projection_total','projection_correct','physical_native_calls','ticks',*STAGE_TICK_KEYS,'groups','links']
    for arm in ['exact_joint','native_joint','native_marginal']:
        rr=[r for r in rows if r['arm']==arm]
        counts_by_arm[arm]=dict(
            cases=len(rr),
            **{k:sum(r[k] for r in rr) for k in sums},
            kinds=dict(Counter(str(r['kind']) for r in rr)),
            tags=dict(Counter(str(r['tag']) for r in rr)),
            reasons=dict(Counter(r['reason'] for r in rr)),
            first_failed_intermediates=dict(Counter(str(r['first_failed_intermediate']) for r in rr))
        )
    require(counts_by_arm['native_joint']['strict_correct']==256 and counts_by_arm['native_joint']['intervention_strict_correct']==256 and counts_by_arm['native_joint']['tuple_eligibility_correct']==1024,'native_joint 256/256 full truth and 1024/1024 tuple eligibility')
    require(counts_by_arm['native_marginal']['intervention_strict_correct']==256 and counts_by_arm['native_marginal']['intervention_eligibility_correct']==1024 and counts_by_arm['native_marginal']['strict_correct']==128 and counts_by_arm['native_marginal']['unnecessary_abstention']==128 and counts_by_arm['native_marginal']['incorrect_assertion']==0,'native_marginal 256/256 closure accuracy, 128/256 truth split, 128 abstentions, and 0 false assertions')
    for name in p['codebooks']:
        rr=[r for r in rows if r['arm'] in native_arms and r['map_name']==name]
        counts[name]=dict(
            evaluations=len(rr),
            strict_correct=sum(r['strict_correct'] for r in rr),
            intervention_strict_correct=sum(r['intervention_strict_correct'] for r in rr),
            tuple_eligibility_correct=sum(r['tuple_eligibility_correct'] for r in rr),
            intervention_eligibility_correct=sum(r['intervention_eligibility_correct'] for r in rr),
            unnecessary_abstention=sum(r['unnecessary_abstention'] for r in rr),
            incorrect_assertion=sum(r['incorrect_assertion'] for r in rr),
            roles_total=sum(r['role_total'] for r in rr),roles_correct=sum(r['role_correct'] for r in rr),
            pairs_total=sum(r['pair_total'] for r in rr),pairs_correct=sum(r['pair_correct'] for r in rr),
            memberships_total=sum(r['membership_total'] for r in rr),memberships_correct=sum(r['membership_correct'] for r in rr),
            projections_total=sum(r['projection_total'] for r in rr),projections_correct=sum(r['projection_correct'] for r in rr),
            ticks=sum(r['ticks'] for r in rr),
            **{k:sum(r[k] for r in rr) for k in STAGE_TICK_KEYS},
            groups=sum(r['groups'] for r in rr),links=sum(r['links'] for r in rr)
        )
    id_counts=counts['identity']
    nonrole_tick_invariant=all(
        all(counts[name][k]==id_counts[k] for k in STAGE_TICK_KEYS if k!='role_ticks')
        for name in p['codebooks']
    )
    require(nonrole_tick_invariant,'100% of upper tick variation across codebooks is confined to role_ticks across all 5 non-role stages')
    work=read('work-ledger.json');refs=Counter(n for r in records for n in r['network_ids'])
    refs.update(r['network_id'] for r in role)
    for tbl_key in ['pair_transfer','or_transfer','projection_envelope','feasible_envelope','query_envelope']:
        refs.update(r['network_id'] for r in transfer[tbl_key])
    require(sum(refs.values())==work['physical_recorded_calls']==33641 and set(refs)==set(networks),'all actual numerical references')
    probe_ticks=(
        sum(networks[x['network_id']]['cost']['kernel_ticks'] for x in role)+
        sum(networks[x['network_id']]['cost']['kernel_ticks'] for tbl_key in ['pair_transfer','or_transfer','projection_envelope','feasible_envelope','query_envelope'] for x in transfer[tbl_key])
    )
    calls=112+sum(r['physical_native_calls'] for r in rows)+809
    ticks=sum(r['ticks'] for r in rows)+sum(x['ticks'] for x in low)+probe_ticks
    require(calls==33753 and ticks<=5400480 and work['completed'] and work['aggregate_cache_bytes']<=p['budget']['canonical_cache_bytes'],'physical ledger/resource cap')
    rejected=run_mutation_suite(records,cases,packets,p,networks,desc,role,transfer,rep_goals)
    quality=(
        counts_by_arm['native_joint']['strict_correct']==256 and
        counts_by_arm['native_joint']['intervention_strict_correct']==256 and
        counts_by_arm['native_marginal']['intervention_strict_correct']==256 and
        counts_by_arm['native_marginal']['strict_correct']==128 and
        counts_by_arm['native_marginal']['unnecessary_abstention']==128 and
        counts_by_arm['native_marginal']['incorrect_assertion']==0 and
        all(r['first_failed_intermediate'] is None for r in rows if r['arm'] in native_arms) and
        all(r['semantic_equal'] for r in paired) and
        coverage['wrong']==0 and
        transfer_summary['pair_bijection_class_wrong']==0 and
        transfer_summary['or_correct']==121 and
        transfer_summary['projection_correct']==32 and
        transfer_summary['feasible4_correct']==64 and
        transfer_summary['query4_correct']==512 and
        nonrole_tick_invariant
    )
    exposure={}
    for name in p['codebooks']:
        hist=Counter();code_pairs=set();hamming_pairs=set();cross_pairs=set();hetero=0;pair_calls=0
        for c in p['cases']:
            if c['map_name']!=name:continue
            code={token:i for i,token in enumerate(c['vocabulary'])}
            for fkeys in [c['context'],c['T']]:
                for fk in fkeys:
                    fact=desc[fk]
                    cross_pairs.add((code[fact['subject']],code[fact['object']]))
                    for a in c['alternatives']:
                        x0,y0=code[a['X']],code[fact['subject']]
                        x1,y1=code[a['Y']],code[fact['object']]
                        d0,d1=(x0^y0).bit_count(),(x1^y1).bit_count()
                        code_pairs.update([(x0,y0),(x1,y1)])
                        hist[d0]+=1;hist[d1]+=1
                        hamming_pairs.add((d0,d1));pair_calls+=1
                        if d0>0 and d1>0 and d0!=d1:hetero+=1
        exposure[name]=dict(
            actual_role_comparisons_per_arm=sum(hist.values()),
            actual_role_comparisons_across_2arms=2*sum(hist.values()),
            ordered_code_pairs_count=len(code_pairs),
            ordered_code_pairs=sorted(code_pairs),
            hamming_distance_histogram_per_arm={str(k):v for k,v in sorted(hist.items())},
            ordered_hamming_pairs_count=len(hamming_pairs),
            ordered_hamming_pairs=sorted(list(x) for x in hamming_pairs),
            cross_domain_fact_pairs_count=len(cross_pairs),
            heterogeneous_nonzero_hamming_pairs_per_arm=hetero,
            total_pair_gate_calls_per_arm=pair_calls
        )
    return dict(
        status='AUDITED',
        quality_pass=quality,
        finite_semantic_adoption=quality,
        counts=counts,
        counts_by_arm=counts_by_arm,
        regime_and_signature_coverage=regime_summary,
        nonrole_stage_ticks_invariant_across_codebooks=nonrole_tick_invariant,
        state_perturbation=dict(
            isometric_pairs=iso_total,
            isometric_state_sha256_equal=iso_state_same,
            isometric_binding_sha256_equal=iso_bind_same,
            isometric_binding_max_abs_diff=iso_max_diff,
            nonisometric_pairs=noniso_total,
            nonisometric_state_sha256_changed=noniso_state_changed,
            nonisometric_binding_sha256_changed=noniso_bind_changed,
            nonisometric_binding_max_abs_diff=noniso_max_diff
        ),
        role_coverage=coverage,
        stage_transfer=transfer_summary,
        matrix_coverage=cov_summary,
        paired_conditions=448,
        paired_invariant=sum(r['semantic_equal'] for r in paired),
        pairs=paired,
        physical_calls=calls,
        ticks=ticks,
        unique_traces=len(networks),
        max_scalar_error=max(scalar,max(x['numeric_replay_max_absolute_error'] for x in low)),
        mutation_rejections=rejected,
        actual_pipeline_coverage=exposure,
        source_calls=112,
        role_calls=64,
        pair_transfer_calls=16,
        or_transfer_calls=121,
        projection_envelope_calls=32,
        feasible4_envelope_calls=64,
        query4_envelope_calls=512,
        stage_transfer_calls=809,
        upper_pipeline_calls=32832,
        learning=0,
        world_measurement=0,
        production_adoption=False,
        statistical_speed_verdict=None
    ),rows
