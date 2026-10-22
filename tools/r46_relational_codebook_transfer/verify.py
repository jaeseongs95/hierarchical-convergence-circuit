"""Saved-data 8-token 4-cohort relational codebook coverage, 6-stage continuous transfer probe (569 settles), and sealed-payload invariance audit."""
import itertools,json,math
from collections import Counter
from copy import deepcopy
from hcr.model import fingerprint
from tools.r32_semantic_join.runtime import require,export
from tools.r32_semantic_join.verify import audit_lower
from tools.r34_feasible_state.verify import tag
from tools.r36_overlap_composition.verify import SavedNetworks
from tools.r39_z_query.verify import oracle

AXES=[('R',('X','Y')),('S',('Y','Z')),('U',('X','Z'))]
LAYERS=['role','pair','membership','triple','projection','query_input']
STAGE_TICK_KEYS=['role_ticks','pair_ticks','membership_ticks','triple_ticks','projection_ticks','query_input_ticks','feasible_ticks']

def validate_map(c,p):
    mp=c['code_map'];v=c['canonical_vocabulary']
    require(len(mp)==len(v)==len(set(v))==8 and all(type(x) is int for x in mp) and sorted(mp)==list(range(8)),'3bit bijective map')
    require(mp==p['codebooks'][c['map_name']] and len(c['vocabulary'])==8 and len(set(c['vocabulary']))==8,'frozen codebook')
    require(all(c['vocabulary'][mp[i]]==token for i,token in enumerate(v)),'inverse vocabulary encoder contract')

def check_matrix_coverage(p,desc):
    restricted={};active_tokens_global=set();token_cohort_counts=Counter();hamming_classes_by_map={m:set() for m in p['codebooks']};hamming_pairs_by_map={m:set() for m in p['codebooks']};hamming_pairs_global=set()
    for c in p['cases']:
        validate_map(c,p)
        d=c['domains']
        require(set(d)=={'X','Y','Z'} and all(len(v)==len(set(v))==2 for v in d.values()) and len(set(sum(d.values(),[])))==6,'three disjoint 2-token domains')
        code={token:i for i,token in enumerate(c['vocabulary'])}
        tokens=sorted(set(sum(d.values(),[])))
        require(all(t in code for t in tokens),'active domain tokens in vocabulary')
        active_tokens_global.update(tokens)
        if c['map_name']=='identity' and c['r_mask']==9 and c['s_mask']==9 and c['u_mask']==9 and c['order']==0:
            for coh in p['cohorts']:
                for dom_tokens in coh['domains'].values():
                    for t in dom_tokens:token_cohort_counts[t]+=1
        sig=tuple((t,code[t]) for t in tokens)
        restricted.setdefault(c['base_key'],{})[c['map_name']]=sig
        for name,(a,b) in AXES:
            assignments=[(x,y) for x in d[a] for y in d[b]][::1 if not c['order'] else -1]
            for fk in c['relations'][name]:
                require(fk in desc,'relation source key in desc')
                fact=desc[fk]
                require(fact['subject'] in d[a] and fact['object'] in d[b] and fact['subject'] in code and fact['object'] in code,'fact endpoints in domain and vocabulary')
                for ax,ay in assignments:
                    dx=(code[ax]^code[fact['subject']]).bit_count()
                    dy=(code[ay]^code[fact['object']]).bit_count()
                    hamming_classes_by_map[c['map_name']].update([dx,dy])
                    hamming_pairs_by_map[c['map_name']].add((dx,dy))
                    hamming_pairs_global.add((dx,dy))
    require(len(active_tokens_global)==8 and set(active_tokens_global)==set(p['canonical_vocabulary']),'all 8 canonical tokens active in relational pipeline')
    require(all(token_cohort_counts[t]==3 for t in p['canonical_vocabulary']),'balanced 3/4 cohort participation per token')
    classes_per_base=sorted({len(set(m.values())) for m in restricted.values()})
    unchanged_cases=changed_cases=0
    for maps in restricted.values():
        for name,sig in maps.items():
            if name=='identity':continue
            if sig==maps['identity']:unchanged_cases+=1
            else:changed_cases+=1
    require(classes_per_base==[8] and unchanged_cases==0 and changed_cases==112,'every base context 8 distinct restricted maps and 0 unchanged pairs')
    require(all(hamming_classes_by_map[m]=={0,1,2,3} for m in p['codebooks']),'all 4 Hamming distance classes realized per codebook')
    require(len(hamming_pairs_by_map['identity'])==16 and len(hamming_pairs_by_map['bit_reverse'])==16 and len(hamming_pairs_by_map['xor7'])==16 and len(hamming_pairs_global)==16,'all 16 ordered Hamming pairs realized in upper pipeline')
    return dict(
        restricted_map_classes_per_base=classes_per_base,
        mapped_case_pairs_unchanged=unchanged_cases,
        mapped_case_pairs_changed=changed_cases,
        mapped_native_arm_pairs_unchanged=3*unchanged_cases,
        mapped_native_arm_pairs_changed=3*changed_cases,
        active_tokens_count=len(active_tokens_global),
        token_cohort_participation=dict(sorted(token_cohort_counts.items())),
        hamming_classes_per_map={m:sorted(v) for m,v in sorted(hamming_classes_by_map.items())},
        upper_pair_hamming_pairs_per_map={m:len(v) for m,v in sorted(hamming_pairs_by_map.items())},
        upper_pair_hamming_pairs_global=len(hamming_pairs_global)
    )

def audit(r,c,packets,p,networks):
    validate_map(c,p)
    require(r['case']==c['key'] and r['base_key']==c['base_key'] and r['map_name']==c['map_name'] and r['cohort']==c['cohort'],'record case/base/map/cohort identity')
    d=c['domains'];order=c['order'];relations={n:[packets[k] for k in keys] for n,keys in c['relations'].items()}
    truth=oracle(d,relations,0,c['queries_canonical']);closure=oracle(d,relations,0,c['queries_canonical'],True)
    arm=r['arm'];scores={n+'_'+s:0 for n in LAYERS for s in ['total','correct']};stage_ticks={k:0 for k in STAGE_TICK_KEYS};ks=[];answers=[]
    def bits(vs):return [None if abs(2*v-1)<p['kernel']['margin_threshold'] else v>.5 for v in vs]
    if arm=='exact_joint':
        require(r['network_ids']==[] and r['native_calls']==0 and sorted(map(tuple,r['triples']))==truth['triples'],'exact full native zero and independent triple oracle')
        require(len(r['queries'])==5,'exact query count')
        for q in r['queries']:
            require(q['native_calls']==0 and set(q)=={'eligible','kind','selected_index','native_calls'},'exact query fields')
            answers.append(dict(eligible=q['eligible'],kind=q['kind'],selected_index=q['selected_index']))
        require(answers==truth['answers'],'exact independent set oracle')
        signature=tuple(int(v) for row in truth['slices'] for v in row)
        payload_sha=None;payload_floats=[]
    else:
        require(arm in ['native_joint','native_factor','native_compact'],'native relational arm')
        L=sum(map(len,relations.values()))
        expected_prefix=12*L+(20 if arm=='native_joint' else 12 if arm=='native_factor' else 26)
        expected_calls=12*L+(27 if arm=='native_joint' else 35 if arm=='native_factor' else 39)
        require(len(r['network_ids'])==r['native_calls']==expected_calls and r['prefix_calls']==expected_prefix,'physical native and prefix call counts')
        ks=[networks[n] for n in r['network_ids']];cursor=0;gain=p['kernel']['evidence_gain'];codes={v:i for i,v in enumerate(c['vocabulary'])};messages={}
        def check(k,name,drives,tick_bucket):
            require(k['program']==p['programs'][name] and k['drives']==drives,'native Program/drives '+name)
            stage_ticks[tick_bucket]+=k['cost']['kernel_ticks']
        for name,axes in AXES:
            assignments=[(x,y) for x in d[axes[0]] for y in d[axes[1]]][::1 if not order else -1];facts=relations[name];values=[]
            for assignment in assignments:
                matches=[]
                for fact in facts:
                    fields=ks[cursor:cursor+2];pair=ks[cursor+2];cursor+=3;expected=[]
                    for k,token,field in zip(fields,assignment,['subject','object'],strict=True):
                        require(token in codes and fact[field] in codes,'role tokens in vocabulary')
                        drives={prefix+str(i):gain*(1 if (codes[t]>>i)&1 else -1) for prefix,t in [('x',token),('y',fact[field])] for i in range(3)}
                        check(k,'role',drives,'role_ticks');expected.append(token==fact[field]);scores['role_total']+=1;scores['role_correct']+=k['adopted'] is expected[-1]
                    check(pair,'pair',dict(m0=gain*(2*fields[0]['state']['goal']-1),m1=gain*(2*fields[1]['state']['goal']-1),m2=-gain),'pair_ticks')
                    matches.append(pair['state']['goal']);scores['pair_total']+=1;scores['pair_correct']+=pair['adopted'] is all(expected)
                k=ks[cursor];cursor+=1;check(k,'or'+str(len(facts)),{'m'+str(i):gain*(2*v-1) for i,v in enumerate(matches)},'membership_ticks')
                values.append(k['state']['goal']);scores['membership_total']+=1;scores['membership_correct']+=k['adopted'] is (assignment in {(f['subject'],f['object']) for f in facts})
            messages[name]=values
        require(r['messages']==messages,'membership numeric messages')
        def gate(name,values,logical,layer,tick_bucket):
            nonlocal cursor
            k=ks[cursor];cursor+=1;drives={'m'+str(i):gain*(2*v-1) for i,v in enumerate(values)}
            if name=='pair':drives['m2']=-gain
            check(k,name,drives,tick_bucket);scores[layer+'_total']+=1;scores[layer+'_correct']+=k['adopted'] is logical;return k['state']['goal']
        if arm in ['native_joint','native_compact']:
            truth_ord=oracle(d,relations,order,c['queries']);closure_ord=oracle(d,relations,order,c['queries'],True)
            ij=[(i,j) for i in range(2) for j in range(2)][::1 if not order else -1];position={xy:i for i,xy in enumerate(ij)}
            slices=[[gate('triple',[messages['R'][position[x,y]],messages['S'][position[y,z]],messages['U'][position[x,z]]],truth_ord['slices'][z][i],'triple','triple_ticks') for i,(x,y) in enumerate(ij)] for z in range(2)]
            require(r['triple_slices']==slices,'triple slices')
            payload=dict(slices=slices)
            if arm=='native_compact':
                xy=[gate('or2',[slices[0][i],slices[1][i]],truth_ord['xy'][i],'projection','projection_ticks') for i in range(4)]
                zs=[gate('or4',slices[z],truth_ord['z'][z],'projection','projection_ticks') for z in range(2)]
                payload=dict(xy=xy,z=zs)
            expected_binding=dict(schema='hcr-r39-z-query-v1',revision=1,representation=arm,domains=d,alternatives=[dict(X=d['X'][x],Y=d['Y'][y]) for x,y in ij],payload=payload,payload_sha256=fingerprint(payload),source_refs={n:[f['origin_sha256'] for f in fs] for n,fs in relations.items()},posterior_is_probability=False,contract='complete_typed_domains_and_closed_relation_tables')
            require(r['binding']==expected_binding and r['producer_seal_sha256']==fingerprint(expected_binding) and cursor==expected_prefix,'r39 sealed producer binding')
            intervention_ord=closure_ord if arm=='native_compact' else truth_ord
            require(len(r['queries'])==5,'5 queries')
            for qi,q in enumerate(c['queries']):
                start_c=cursor;values=[]
                for z in range(2):
                    logical=intervention_ord['answers'][qi]['eligible'][z]
                    if arm=='native_joint':v=payload['slices'][z][q['slot']] if q['kind']=='conditional' else gate('or4',payload['slices'][z],logical,'query_input','query_input_ticks')
                    elif q['kind']=='unary':v=payload['z'][z]
                    else:v=gate('pair',[payload['xy'][q['slot']],payload['z'][z]],logical,'query_input','query_input_ticks')
                    values.append(v)
                scores['query_input_total']+=2;scores['query_input_correct']+=sum(a is b for a,b in zip(bits(values),intervention_ord['answers'][qi]['eligible'],strict=True))
                k=ks[cursor];cursor+=1;check(k,'feasible',dict(e0=gain*(2*values[0]-1),e1=gain*(2*values[1]-1),complete=gain),'feasible_ticks')
                eligible=[k['state']['e0'],k['state']['e1']];kind=tag(k,['none','unique','many','incomplete'],p['kernel']);hi=(1+p['kernel']['margin_threshold'])/2;lo=(1-p['kernel']['margin_threshold'])/2;ids=[i for i,v in enumerate(eligible) if v>=hi];index=ids[0] if kind=='unique' and len(ids)==1 and all(v<=lo for i,v in enumerate(eligible) if i!=ids[0]) else None
                require(r['queries'][qi]==dict(messages=values,eligibility=eligible,kind=kind,selected_index=index,native_calls=cursor-start_c),'r39 query output')
                answers.append(dict(eligible=bits(eligible),kind=kind,selected_index=index))
            if arm=='native_compact':
                xy_can=payload['xy'][::1 if not order else -1]
                signature=tuple(int(v) if v is not None else None for row in (bits(xy_can),bits(payload['z'])) for v in row)
                payload_floats=list(xy_can)+list(payload['z'])
            else:
                slices_can=[row[::1 if not order else -1] for row in payload['slices']]
                signature=tuple(int(v) if v is not None else None for row in slices_can for v in bits(row))
                payload_floats=[v for row in slices_can for v in row]
            payload_sha=expected_binding['payload_sha256']
        else:
            factors={n:v[::1 if not order else -1] for n,v in messages.items()};payload=dict(factors=factors)
            expected_binding=dict(schema='hcr-r40-factor-query-v1',revision=1,representation='native_factor',domains=d,alternatives=[dict(X=x,Y=y) for x in d['X'] for y in d['Y']],payload=payload,payload_sha256=fingerprint(payload),source_refs={n:[f['origin_sha256'] for f in fs] for n,fs in relations.items()},posterior_is_probability=False,contract='complete_typed_domains_and_closed_relation_tables')
            require(r['binding']==expected_binding and r['producer_seal_sha256']==fingerprint(expected_binding) and cursor==expected_prefix,'r40 sealed producer binding')
            require(r['payload_numeric_values']==12 and r['payload_bytes']==len(json.dumps(payload,sort_keys=True,separators=(',',':')).encode()),'r40 payload size')
            require(len(r['queries'])==5,'5 queries')
            for qi,q in enumerate(c['queries_canonical']):
                start_c=cursor;values=[]
                for z in range(2):
                    row=[]
                    for slot in (range(4) if q['kind']=='unary' else [q['slot']]):
                        x,y=divmod(slot,2);row.append(gate('triple',[factors['R'][2*x+y],factors['S'][2*y+z],factors['U'][2*x+z]],truth['slices'][z][slot],'triple','triple_ticks'))
                    v=gate('or4',row,truth['answers'][qi]['eligible'][z],'query_input','query_input_ticks') if q['kind']=='unary' else row[0]
                    values.append(v)
                scores['query_input_total']+=2;scores['query_input_correct']+=sum(a is b for a,b in zip(bits(values),truth['answers'][qi]['eligible'],strict=True))
                k=ks[cursor];cursor+=1;check(k,'feasible',dict(e0=gain*(2*values[0]-1),e1=gain*(2*values[1]-1),complete=gain),'feasible_ticks')
                eligible=[k['state']['e0'],k['state']['e1']];kind=tag(k,['none','unique','many','incomplete'],p['kernel']);hi=(1+p['kernel']['margin_threshold'])/2;lo=(1-p['kernel']['margin_threshold'])/2;ids=[i for i,v in enumerate(eligible) if v>=hi];index=ids[0] if kind=='unique' and len(ids)==1 and all(v<=lo for i,v in enumerate(eligible) if i!=ids[0]) else None
                require(r['queries'][qi]==dict(messages=values,eligibility=eligible,kind=kind,selected_index=index,native_calls=cursor-start_c),'r40 query output')
                answers.append(dict(eligible=bits(eligible),kind=kind,selected_index=index))
            signature=tuple(int(v) if v is not None else None for n in ['R','S','U'] for v in bits(factors[n]))
            payload_floats=[v for n in ['R','S','U'] for v in factors[n]]
            payload_sha=expected_binding['payload_sha256']
        require(cursor==len(ks) and r['independent_evidence_added']==0 and all(all(v==c['initial'] for v in k['initial'].values()) for k in ks),'complete refs/initial/no added evidence')
    total_ticks=sum(k['cost']['kernel_ticks'] for k in ks)
    require(sum(stage_ticks.values())==total_ticks,'exact 7-stage tick partition')
    intervention=closure if arm=='native_compact' else truth;out=[]
    for qi,answer in enumerate(answers):
        tr=truth['answers'][qi];cl=intervention['answers'][qi]
        out.append(dict(query_index=qi,kind=c['queries_canonical'][qi]['kind'],observed=answer,truth=tr,intervention=cl,strict_correct=answer==tr,intervention_strict_correct=answer==cl,eligible_correct=sum(a is b for a,b in zip(answer['eligible'],tr['eligible'],strict=True)),intervention_eligible_correct=sum(a is b for a,b in zip(answer['eligible'],cl['eligible'],strict=True)),extra_z=sum(a is True and b is False for a,b in zip(answer['eligible'],tr['eligible'],strict=True)),missing_z=sum(a is False and b is True for a,b in zip(answer['eligible'],tr['eligible'],strict=True))))
    return dict(
        case=c['key'],base_key=c['base_key'],map_name=c['map_name'],cohort=c['cohort'],arm=arm,order=order,r_mask=c['r_mask'],s_mask=c['s_mask'],u_mask=c['u_mask'],
        queries=out,all_queries_correct=all(q['strict_correct'] for q in out),all_intervention_correct=all(q['intervention_strict_correct'] for q in out),
        semantic_payload_signature=signature,payload_sha256=payload_sha,payload_floats=payload_floats,
        first_failed_intermediate=next((n for n in LAYERS if scores[n+'_total']!=scores[n+'_correct']),None),
        **scores,**stage_ticks,physical_native_calls=len(ks),prefix_calls=r.get('prefix_calls',0),ticks=total_ticks,
        groups=sum(k['cost']['group_updates'] for k in ks),links=sum(k['cost']['signal_transmissions'] for k in ks)
    )

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
    return dict(actual_numeric_inputs=64,numeric_correct=64-error,codebooks_role_only=40320,saved_lookup_checks=checked,wrong=wrong,first_counterexamples=first,hamming_class_goals={str(k):v for k,v in rep_goals.items()},hamming_class_ticks={str(k):v for k,v in rep_ticks.items()},max_within_class_goal_spread=max_class_spread,full_pipeline_codebooks=8,scope='all 8-token bijections role stage (4 Hamming equivalence classes), fixed Program/Config/initial'),rep_goals

def transfer_audit(transfer,rep_goals,networks,p):
    cfg=p['kernel'];gain=cfg['evidence_gain'];tol=p['scalar_tolerance']
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
    # 3. triple_transfer (4^3 = 64 settles)
    tr_rows=transfer['triple_transfer'];require(len(tr_rows)==64,'64 triple extremal rows')
    tr_seen=set();s_true=[];s_false=[];tr_ticks=set()
    for row in tr_rows:
        tags=tuple(row['input_tags']);bools=row['input_bools'];vals=row['input_vals']
        require(len(tags)==len(bools)==len(vals)==3,'valid triple row')
        tr_seen.add(tags)
        k=networks[row['network_id']]
        expected_drives={'m'+str(i):gain*(2*vals[i]-1) for i in range(3)}
        require(k['program']==p['programs']['triple'] and all(abs(k['drives'][m]-expected_drives[m])<=tol for m in expected_drives),'triple Program/drives')
        expected_bool=all(bools)
        require(row['expected'] is expected_bool and k['adopted'] is expected_bool and row['adopted'] is expected_bool and abs(row['goal']-k['state']['goal'])<=tol and row['ticks']==k['cost']['kernel_ticks'],'triple semantic and scalar consistency')
        if expected_bool:s_true.append(k['state']['goal'])
        else:s_false.append(k['state']['goal'])
        tr_ticks.add(k['cost']['kernel_ticks'])
    require(len(tr_seen)==64 and s_true and s_false,'all 64 triple extremal combinations covered')
    # 4. projection_or2 (4^2 = 16 settles) and projection_or4 (4^4 = 256 settles)
    or2_rows=transfer['projection_or2'];require(len(or2_rows)==16,'16 projection or2 extremal rows')
    or2_seen=set();xy_true=[];xy_false=[];or2_ticks=set()
    for row in or2_rows:
        tags=tuple(row['input_tags']);bools=row['input_bools'];vals=row['input_vals']
        or2_seen.add(tags);k=networks[row['network_id']]
        expected_drives={'m'+str(i):gain*(2*vals[i]-1) for i in range(2)}
        require(k['program']==p['programs']['or2'] and all(abs(k['drives'][m]-expected_drives[m])<=tol for m in expected_drives),'projection or2 Program/drives')
        expected_bool=any(bools)
        require(row['expected'] is expected_bool and k['adopted'] is expected_bool and row['adopted'] is expected_bool and abs(row['goal']-k['state']['goal'])<=tol and row['ticks']==k['cost']['kernel_ticks'],'projection or2 consistency')
        if expected_bool:xy_true.append(k['state']['goal'])
        else:xy_false.append(k['state']['goal'])
        or2_ticks.add(k['cost']['kernel_ticks'])
    require(len(or2_seen)==16 and xy_true and xy_false,'all 16 projection or2 combinations covered')
    or4_rows=transfer['projection_or4'];require(len(or4_rows)==256,'256 projection or4 extremal rows')
    or4_seen=set();z_true=[];z_false=[];or4_ticks=set()
    for row in or4_rows:
        tags=tuple(row['input_tags']);bools=row['input_bools'];vals=row['input_vals']
        or4_seen.add(tags);k=networks[row['network_id']]
        expected_drives={'m'+str(i):gain*(2*vals[i]-1) for i in range(4)}
        require(k['program']==p['programs']['or4'] and all(abs(k['drives'][m]-expected_drives[m])<=tol for m in expected_drives),'projection or4 Program/drives')
        expected_bool=any(bools)
        require(row['expected'] is expected_bool and k['adopted'] is expected_bool and row['adopted'] is expected_bool and abs(row['goal']-k['state']['goal'])<=tol and row['ticks']==k['cost']['kernel_ticks'],'projection or4 consistency')
        if expected_bool:z_true.append(k['state']['goal'])
        else:z_false.append(k['state']['goal'])
        or4_ticks.add(k['cost']['kernel_ticks'])
    require(len(or4_seen)==256 and z_true and z_false,'all 256 projection or4 combinations covered')
    # 5. consumer_pair (4^2 = 16 settles) and feasible_envelope (4^2 = 16 settles)
    cp_rows=transfer['consumer_pair'];require(len(cp_rows)==16,'16 consumer pair extremal rows')
    cp_seen=set();cp_true=[];cp_false=[];cp_ticks=set()
    for row in cp_rows:
        tags=tuple(row['input_tags']);bools=row['input_bools'];vals=row['input_vals']
        cp_seen.add(tags);k=networks[row['network_id']]
        expected_drives={'m0':gain*(2*vals[0]-1),'m1':gain*(2*vals[1]-1),'m2':-gain}
        require(k['program']==p['programs']['pair'] and all(abs(k['drives'][m]-expected_drives[m])<=tol for m in expected_drives),'consumer pair Program/drives')
        expected_bool=all(bools)
        require(row['expected'] is expected_bool and k['adopted'] is expected_bool and row['adopted'] is expected_bool and abs(row['goal']-k['state']['goal'])<=tol and row['ticks']==k['cost']['kernel_ticks'],'consumer pair consistency')
        if expected_bool:cp_true.append(k['state']['goal'])
        else:cp_false.append(k['state']['goal'])
        cp_ticks.add(k['cost']['kernel_ticks'])
    require(len(cp_seen)==16 and cp_true and cp_false,'all 16 consumer pair combinations covered')
    f_rows=transfer['feasible_envelope'];require(len(f_rows)==16,'16 feasible2 extremal rows')
    f_seen=set();elig_true=[];elig_false=[];cov_vals=[];f_ticks=set()
    for row in f_rows:
        f_seen.add((row['left_tag'],row['right_tag']))
        k=networks[row['network_id']]
        expected_drives={'e0':gain*(2*row['left_in']-1),'e1':gain*(2*row['right_in']-1),'complete':gain}
        require(k['program']==p['programs']['feasible'] and all(abs(k['drives'][m]-expected_drives[m])<=tol for m in expected_drives),'feasible2 envelope Program/drives')
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
        cov_vals.append(k['state']['complete']);f_ticks.add(k['cost']['kernel_ticks'])
    require(len(f_seen)==16,'all 16 feasible2 extremal corners')
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
        triple_extremal_combinations=64,
        triple_correct=64,
        slice_false_goal_range=[min(s_false),max(s_false)],
        slice_true_goal_range=[min(s_true),max(s_true)],
        triple_ticks=sorted(tr_ticks),
        projection_or2_combinations=16,
        projection_or2_correct=16,
        xy_false_goal_range=[min(xy_false),max(xy_false)],
        xy_true_goal_range=[min(xy_true),max(xy_true)],
        projection_or4_combinations=256,
        projection_or4_correct=256,
        z_false_goal_range=[min(z_false),max(z_false)],
        z_true_goal_range=[min(z_true),max(z_true)],
        consumer_pair_combinations=16,
        consumer_pair_correct=16,
        consumer_pair_false_goal_range=[min(cp_false),max(cp_false)],
        consumer_pair_true_goal_range=[min(cp_true),max(cp_true)],
        feasible2_extremal_corners=16,
        feasible2_extremal_correct=16,
        feasible2_eligibility_false_range=[min(elig_false),max(elig_false)],
        feasible2_eligibility_true_range=[min(elig_true),max(elig_true)],
        feasible2_coverage_range=[min(cov_vals),max(cov_vals)],
        feasible2_ticks=sorted(f_ticks),
        total_stage_transfer_settles=569,
        scope='role(64)->pair(16) is exhaustive across all 4^2 Hamming-distance pairs for all 40320 3-bit bijections; or0..4(121), triple(64), projection(272), and consume(32) are extremal [min,max] interval-boundary checks across the 6-stage relational chain, not 64^n full product enumeration'
    )

def run_mutation_suite(records,cases,packets,p,networks,desc,role,transfer,rep_goals):
    def pick(arm):return next(r for r in records if r['arm']==arm and cases[r['case']]['r_mask']==6 and cases[r['case']]['s_mask']==9 and cases[r['case']]['u_mask']==6)
    r_joint=pick('native_joint');c_joint=cases[r_joint['case']]
    r_factor=pick('native_factor');c_factor=cases[r_factor['case']]
    r_compact=pick('native_compact');c_compact=cases[r_compact['case']]
    rejected=[]
    joint_mutations=[
        ('revision',lambda x:x['binding'].update(revision=2)),
        ('source_ref',lambda x:x['binding']['source_refs']['R'].__setitem__(0,'wrong')),
        ('joint_payload_slice',lambda x:x['binding']['payload']['slices'][0].__setitem__(0,.5)),
        ('payload_hash',lambda x:x['binding'].update(payload_sha256='wrong')),
        ('producer_seal',lambda x:x.update(producer_seal_sha256='wrong')),
        ('triple_slice',lambda x:x['triple_slices'][0].__setitem__(0,.5)),
        ('membership_message',lambda x:x['messages']['R'].__setitem__(0,.5)),
        ('query_slot_swap',lambda x:x['queries'].__setitem__(slice(1,3),x['queries'][1:3][::-1])),
        ('query_messages',lambda x:x['queries'][0]['messages'].__setitem__(0,.5)),
        ('query_eligibility',lambda x:x['queries'][0]['eligibility'].__setitem__(0,.5)),
        ('selected_index',lambda x:x['queries'][0].update(selected_index=99)),
        ('prefix_count',lambda x:x.update(prefix_calls=0)),
        ('network_ref',lambda x:x['network_ids'].__setitem__(0,x['network_ids'][-1])),
    ]
    for name,change in joint_mutations:
        bad=deepcopy(r_joint);change(bad)
        try:audit(bad,c_joint,packets,p,networks)
        except ValueError:rejected.append(name)
        else:raise ValueError('accepted mutation '+name)
    bad_f=deepcopy(r_factor);bad_f['binding']['payload']['factors']['S'][0]=.5
    try:audit(bad_f,c_factor,packets,p,networks)
    except ValueError:rejected.append('factor_payload')
    else:raise ValueError('accepted mutation factor_payload')
    bad_comp=deepcopy(r_compact);bad_comp['binding']['payload']['z'][0]=.5
    try:audit(bad_comp,c_compact,packets,p,networks)
    except ValueError:rejected.append('compact_projection')
    else:raise ValueError('accepted mutation compact_projection')
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
    c0_dom=bad_p1['cohorts'][0]['domains']
    c0_rels={n:[f'c0_{n}_{i}' for i in range(4)] for n in ['R','S','U']}
    for cc in bad_p1['cases']:
        cc['domains']=deepcopy(c0_dom)
        cc['relations']={n:[c0_rels[n][i] for i in range(4) if (cc[n.lower()+'_mask']>>i)&1] for n in ['R','S','U']}
    try:check_matrix_coverage(bad_p1,desc)
    except ValueError:rejected.append('incomplete_8token_coverage')
    else:raise ValueError('accepted mutation incomplete_8token_coverage')
    bad_p2=deepcopy(p)
    for cc in bad_p2['cases']:
        if cc['base_key']=='b00':
            cc['domains']=dict(X=['jade','violet'],Y=['wheat','umber'],Z=['teal','coral'])
            cc['relations']=dict(R=[],S=[],U=[])
    try:check_matrix_coverage(bad_p2,desc)
    except ValueError:rejected.append('collapsed_restricted_codebook')
    else:raise ValueError('accepted mutation collapsed_restricted_codebook')
    bad_p3=deepcopy(p)
    for cc in bad_p3['cases']:
        cc['relations']=dict(R=[],S=[],U=[])
    try:check_matrix_coverage(bad_p3,desc)
    except ValueError:rejected.append('incomplete_16hamming_pair_coverage')
    else:raise ValueError('accepted mutation incomplete_16hamming_pair_coverage')
    bad_tr=deepcopy(transfer);bad_tr['pair_transfer'][0]['adopted']=not bad_tr['pair_transfer'][0]['adopted']
    try:transfer_audit(bad_tr,rep_goals,networks,p)
    except ValueError:rejected.append('downstream_transfer_table_tamper')
    else:raise ValueError('accepted mutation downstream_transfer_table_tamper')
    require(len(rejected)==22,'22 mutations rejected')
    return rejected

def bundle(folder,p):
    read=lambda n:json.loads((folder/n).read_text(encoding='utf-8'))
    networks=SavedNetworks(folder,p);scalar=networks.verify_all();sources=read('sources.json');packets={k:export(v) for k,v in sources.items()};low=[audit_lower(sources[s['key']],s,p) for s in p['sources']]
    desc={s['key']:dict(predicate=s['predicate'],subject=s['observation']['start'],object=s['observation']['goal']) for s in p['sources']}
    cov_summary=check_matrix_coverage(p,desc)
    records=[r for i in range(8) for r in read('batch%02d.json'%i)];metrics=[r for i in range(8) for r in read('metrics%02d.json'%i)];cases={c['key']:c for c in p['cases']};expected={(c['key'],arm) for c in p['cases'] for arm in c['arms']}
    require(len(records)==len(metrics)==len(expected)==512 and {(r['case'],r['arm']) for r in records}=={(r['case'],r['arm']) for r in metrics}==expected,'full frozen 512 evaluations')
    require(all(math.isfinite(v) and v>=0 for m in metrics for k,v in m.items() if k.endswith('_seconds')),'finite measurement')
    rows=[audit(r,cases[r['case']],packets,p,networks) for r in records]
    role=read('roles.json');coverage,rep_goals=role_audit(role,networks,p)
    transfer=read('transfer.json');transfer_summary=transfer_audit(transfer,rep_goals,networks,p)
    native_arms=['native_joint','native_factor','native_compact']
    by_base_arm_map={(r['base_key'],r['arm'],r['map_name']):r for r in rows if r['arm'] in native_arms}
    paired=[];isometric_sha_equal=0;nonisometric_sha_changed=0;isometric_max_diff=0.0;nonisometric_max_diff=0.0
    for (base,arm,name),r in sorted(by_base_arm_map.items()):
        if name=='identity':continue
        b=by_base_arm_map[(base,arm,'identity')]
        q_eq=all(rq['observed']==bq['observed'] and rq['strict_correct']==bq['strict_correct'] and rq['intervention_strict_correct']==bq['intervention_strict_correct'] for rq,bq in zip(r['queries'],b['queries'],strict=True))
        sig_eq=(r['semantic_payload_signature']==b['semantic_payload_signature'])
        inter_eq=(r['first_failed_intermediate']==b['first_failed_intermediate']==None)
        sha_eq=(r['payload_sha256']==b['payload_sha256'])
        p_diff=max((abs(x-y) for x,y in zip(r['payload_floats'],b['payload_floats'],strict=True)),default=0.0)
        if name in ['bit_reverse','xor7']:
            isometric_sha_equal+=int(sha_eq);isometric_max_diff=max(isometric_max_diff,p_diff)
        else:
            nonisometric_sha_changed+=int(not sha_eq);nonisometric_max_diff=max(nonisometric_max_diff,p_diff)
        paired.append(dict(base_key=base,arm=arm,map_name=name,semantic_equal=q_eq and sig_eq and inter_eq,payload_sha256_equal=sha_eq,payload_max_abs_diff=p_diff))
    require(len(paired)==336 and all(x['semantic_equal'] for x in paired),'all 336 paired non-identity vs identity evaluations semantically invariant')
    require(isometric_max_diff<=p['scalar_tolerance'] and nonisometric_sha_changed>0,'isometric codebooks preserve payload within scalar tolerance while non-isometric codebooks perturb continuous payload')
    counts={};counts_by_arm={}
    for arm in native_arms+['exact_joint']:
        rr=[r for r in rows if r['arm']==arm];qq=[q for r in rr for q in r['queries']]
        counts_by_arm[arm]=dict(
            evaluations=len(rr),queries=len(qq),
            all_truth_correct=sum(r['all_queries_correct'] for r in rr),
            all_intervention_correct=sum(r['all_intervention_correct'] for r in rr),
            strict_correct=sum(q['strict_correct'] for q in qq),
            intervention_strict_correct=sum(q['intervention_strict_correct'] for q in qq),
            eligible_correct=sum(q['eligible_correct'] for q in qq),
            intervention_eligible_correct=sum(q['intervention_eligible_correct'] for q in qq),
            extra_z=sum(q['extra_z'] for q in qq),
            missing_z=sum(q['missing_z'] for q in qq),
            kinds=dict(Counter(q['observed']['kind'] for q in qq)),
            physical_native_calls=sum(r['physical_native_calls'] for r in rr),
            ticks=sum(r['ticks'] for r in rr),
            **{k:sum(r[k] for r in rr) for k in STAGE_TICK_KEYS},
            groups=sum(r['groups'] for r in rr),
            links=sum(r['links'] for r in rr)
        )
    require(counts_by_arm['native_joint']['strict_correct']==640 and counts_by_arm['native_factor']['strict_correct']==640,'native_joint and native_factor 640/640 full truth accuracy')
    require(counts_by_arm['native_compact']['intervention_strict_correct']==640 and counts_by_arm['native_compact']['strict_correct']==544 and counts_by_arm['native_compact']['extra_z']==96 and counts_by_arm['native_compact']['missing_z']==0,'native_compact 640/640 closure accuracy and exact 96/640 conditional abstention boundary')
    for name in p['codebooks']:
        rr=[r for r in rows if r['arm'] in native_arms and r['map_name']==name];qq=[q for r in rr for q in r['queries']]
        counts[name]=dict(
            evaluations=len(rr),queries=len(qq),
            strict_correct=sum(q['strict_correct'] for q in qq),
            intervention_strict_correct=sum(q['intervention_strict_correct'] for q in qq),
            roles_total=sum(r['role_total'] for r in rr),roles_correct=sum(r['role_correct'] for r in rr),
            pairs_total=sum(r['pair_total'] for r in rr),pairs_correct=sum(r['pair_correct'] for r in rr),
            memberships_total=sum(r['membership_total'] for r in rr),memberships_correct=sum(r['membership_correct'] for r in rr),
            triples_total=sum(r['triple_total'] for r in rr),triples_correct=sum(r['triple_correct'] for r in rr),
            projections_total=sum(r['projection_total'] for r in rr),projections_correct=sum(r['projection_correct'] for r in rr),
            query_inputs_total=sum(r['query_input_total'] for r in rr),query_inputs_correct=sum(r['query_input_correct'] for r in rr),
            ticks=sum(r['ticks'] for r in rr),
            **{k:sum(r[k] for r in rr) for k in STAGE_TICK_KEYS},
            groups=sum(r['groups'] for r in rr),links=sum(r['links'] for r in rr)
        )
    id_counts=counts['identity']
    nonrole_tick_invariant=all(
        all(counts[name][k]==id_counts[k] for k in STAGE_TICK_KEYS if k!='role_ticks')
        for name in p['codebooks']
    )
    require(nonrole_tick_invariant,'100% of upper tick variation across codebooks is confined to role_ticks')
    work=read('work-ledger.json');refs=Counter(n for r in records for n in r['network_ids'])
    refs.update(r['network_id'] for r in role)
    for tbl_key in ['pair_transfer','or_transfer','triple_transfer','projection_or2','projection_or4','consumer_pair','feasible_envelope']:
        refs.update(r['network_id'] for r in transfer[tbl_key])
    require(sum(refs.values())==work['physical_recorded_calls']==38841 and set(refs)==set(networks),'all actual numerical references')
    probe_ticks=(
        sum(networks[x['network_id']]['cost']['kernel_ticks'] for x in role)+
        sum(networks[x['network_id']]['cost']['kernel_ticks'] for tbl_key in ['pair_transfer','or_transfer','triple_transfer','projection_or2','projection_or4','consumer_pair','feasible_envelope'] for x in transfer[tbl_key])
    )
    calls=48+sum(r['physical_native_calls'] for r in rows)+569
    ticks=sum(r['ticks'] for r in rows)+sum(x['ticks'] for x in low)+probe_ticks
    require(calls==38889 and ticks<=6222240 and work['completed'] and work['aggregate_cache_bytes']<=p['budget']['canonical_cache_bytes'],'physical ledger/resource cap')
    rejected=run_mutation_suite(records,cases,packets,p,networks,desc,role,transfer,rep_goals)
    quality=(
        counts_by_arm['native_joint']['strict_correct']==640 and
        counts_by_arm['native_factor']['strict_correct']==640 and
        counts_by_arm['native_compact']['intervention_strict_correct']==640 and
        counts_by_arm['native_compact']['strict_correct']==544 and
        all(r['first_failed_intermediate'] is None for r in rows if r['arm'] in native_arms) and
        all(r['semantic_equal'] for r in paired) and
        coverage['wrong']==0 and
        transfer_summary['pair_bijection_class_wrong']==0 and
        transfer_summary['or_correct']==121 and
        transfer_summary['triple_correct']==64 and
        transfer_summary['projection_or2_correct']==16 and
        transfer_summary['projection_or4_correct']==256 and
        transfer_summary['consumer_pair_correct']==16 and
        transfer_summary['feasible2_extremal_correct']==16 and
        nonrole_tick_invariant
    )
    exposure={}
    for name in p['codebooks']:
        hist=Counter();code_pairs=set();hamming_pairs=set();hetero=0;pair_calls=0
        for c in p['cases']:
            if c['map_name']!=name:continue
            code={token:i for i,token in enumerate(c['vocabulary'])}
            d=c['domains']
            for rel_name,(a,b) in AXES:
                assignments=[(x,y) for x in d[a] for y in d[b]][::1 if not c['order'] else -1]
                for fk in c['relations'][rel_name]:
                    fact=desc[fk]
                    for ax,ay in assignments:
                        x0,y0=code[ax],code[fact['subject']]
                        x1,y1=code[ay],code[fact['object']]
                        d0,d1=(x0^y0).bit_count(),(x1^y1).bit_count()
                        code_pairs.update([(x0,y0),(x1,y1)])
                        hist[d0]+=1;hist[d1]+=1
                        hamming_pairs.add((d0,d1));pair_calls+=1
                        if d0>0 and d1>0 and d0!=d1:hetero+=1
        exposure[name]=dict(
            actual_role_comparisons_per_arm=sum(hist.values()),
            actual_role_comparisons_across_3arms=3*sum(hist.values()),
            ordered_code_pairs_count=len(code_pairs),
            ordered_code_pairs=sorted(code_pairs),
            hamming_distance_histogram_per_arm={str(k):v for k,v in sorted(hist.items())},
            ordered_hamming_pairs_count=len(hamming_pairs),
            ordered_hamming_pairs=sorted(list(x) for x in hamming_pairs),
            heterogeneous_nonzero_hamming_pairs_per_arm=hetero,
            total_pair_gate_calls_per_arm=pair_calls
        )
    return dict(
        status='AUDITED',
        quality_pass=quality,
        finite_semantic_adoption=quality,
        counts=counts,
        counts_by_arm=counts_by_arm,
        nonrole_stage_ticks_invariant_across_codebooks=nonrole_tick_invariant,
        isometric_payload_sha256_equal_pairs=isometric_sha_equal,
        isometric_payload_max_abs_diff=isometric_max_diff,
        nonisometric_payload_sha256_changed_pairs=nonisometric_sha_changed,
        nonisometric_payload_max_abs_diff=nonisometric_max_diff,
        role_coverage=coverage,
        stage_transfer=transfer_summary,
        matrix_coverage=cov_summary,
        paired_conditions=336,
        paired_queries=1680,
        paired_invariant=sum(r['semantic_equal'] for r in paired),
        pairs=paired,
        physical_calls=calls,
        ticks=ticks,
        unique_traces=len(networks),
        max_scalar_error=max(scalar,max(x['numeric_replay_max_absolute_error'] for x in low)),
        mutation_rejections=rejected,
        actual_pipeline_coverage=exposure,
        source_calls=48,
        role_calls=64,
        stage_transfer_calls=569,
        upper_pipeline_calls=38272,
        learning=0,
        world_measurement=0,
        production_adoption=False,
        statistical_speed_verdict=None
    ),rows
