"""Saved-data codebook coverage; role exhaustiveness is separate from pipeline coverage."""
import itertools,json,math
from collections import Counter
from copy import deepcopy
from hcr.model import fingerprint
from tools.r32_semantic_join.runtime import require,export
from tools.r32_semantic_join.verify import audit_lower
from tools.r36_overlap_composition.verify import SavedNetworks,audit as prior_audit,mutations as prior_mutations

FIELDS=['kind','selected_index','value','reason','C_AST_values','T_AST_values','C_leaf_patterns','T_leaf_patterns']

def validate_map(c,p):
    mp=c['code_map'];v=c['canonical_vocabulary']
    require(len(mp)==len(v)==len(set(v))==8 and all(type(x) is int for x in mp) and sorted(mp)==list(range(8)),'3bit bijective map')
    require(mp==p['codebooks'][c['map_name']] and len(c['vocabulary'])==8,'frozen codebook')
    require(all(c['vocabulary'][mp[i]]==token for i,token in enumerate(v)),'inverse vocabulary encoder contract')

def audit(r,c,packets,p,networks):
    validate_map(c,p);require(r['map_name']==c['map_name'] and r['base_key']==c['base_key'],'record codebook identity')
    row=prior_audit(r,c,packets,p,networks);row.update(map_name=c['map_name'],base_key=c['base_key']);return row

def role_audit(role,networks,p):
    require(len(role)==64 and {(x['left'],x['right']) for x in role}==set(itertools.product(range(8),repeat=2)),'all numeric role inputs')
    table={};error=0;cfg=p['kernel'];gain=cfg['evidence_gain']
    for r in role:
        k=networks[r['network_id']];drives={s+str(i):gain*(1 if (v>>i)&1 else -1) for s,v in [('x',r['left']),('y',r['right'])] for i in range(3)}
        require(k['program']==p['programs']['role'] and k['drives']==drives and all(v==.5 for v in k['initial'].values()),'role Program/Config/drive/initial coverage')
        table[(r['left'],r['right'])]=k['adopted'];error+=k['adopted'] is not (r['left']==r['right'])
    checked=wrong=0;first=[]
    for perm in itertools.permutations(range(8)):
        for x,y in itertools.product(range(8),repeat=2):
            checked+=1
            if table[(perm[x],perm[y])] is not (x==y):
                wrong+=1
                if len(first)<8:first.append(dict(codebook=list(perm),left=x,right=y,value=table[(perm[x],perm[y])]))
    require(checked==2580480,'all40320mapping role checks')
    return dict(actual_numeric_inputs=64,numeric_correct=64-error,codebooks_role_only=40320,saved_lookup_checks=checked,wrong=wrong,first_counterexamples=first,full_pipeline_codebooks=8,scope='all8token bijections role stage only, fixedProgramConfiginitial;not all fullpipeline executions')

def bundle(folder,p):
    read=lambda n:json.loads((folder/n).read_text(encoding='utf-8'))
    networks=SavedNetworks(folder,p);scalar=networks.verify_all();sources=read('sources.json');packets={k:export(v) for k,v in sources.items()};low=[audit_lower(sources[s['key']],s,p) for s in p['sources']]
    records=[r for i in range(18) for r in read('batch%02d.json'%i)];metrics=[r for i in range(18) for r in read('metrics%02d.json'%i)];cases={c['key']:c for c in p['cases']};expected={(c['key'],arm) for c in p['cases'] for arm in c['arms']}
    require(len(records)==len(metrics)==len(expected)==1152 and {(r['case'],r['arm']) for r in records}=={(r['case'],r['arm']) for r in metrics}==expected,'full frozen evaluations')
    require(all(math.isfinite(v) and v>=0 for m in metrics for k,v in m.items() if k.endswith('_seconds')),'finite measurement')
    rows=[audit(r,cases[r['case']],packets,p,networks) for r in records];role=read('roles.json');coverage=role_audit(role,networks,p)
    native={(r['base_key'],r['map_name']):r for r in rows if r['arm']=='native'};paired=[]
    for (base,name),r in native.items():
        if name=='identity':continue
        b=native[(base,'identity')];paired.append(dict(base_key=base,map_name=name,semantic_equal=all(r[k]==b[k] for k in FIELDS)))
    require(len(paired)==896,'mapped-baseline pair coverage')
    counts={name:dict(cases=len(rr:=[r for r in rows if r['arm']=='native' and r['map_name']==name]),strict=sum(r['strict_correct'] for r in rr),roles_total=sum(r['role_total'] for r in rr),roles_correct=sum(r['role_correct'] for r in rr),AST_total=sum(r['AST_total'] for r in rr),AST_correct=sum(r['AST_correct'] for r in rr),ticks=sum(r['ticks'] for r in rr),groups=sum(r['groups'] for r in rr),links=sum(r['links'] for r in rr)) for name in p['codebooks']}
    exact=[r for r in rows if r['arm']=='exact'];work=read('work-ledger.json');refs=Counter(n for r in records for n in r['network_ids']);refs.update(r['network_id'] for r in role)
    require(sum(refs.values())==work['physical_recorded_calls']==18496 and set(refs)==set(networks),'all actual numerical references')
    calls=28+sum(r['physical_native_calls'] for r in rows)+64;ticks=sum(r['ticks'] for r in rows)+sum(x['ticks'] for x in low)+sum(networks[x['network_id']]['cost']['kernel_ticks'] for x in role)
    require(calls==18524 and ticks<=2963840 and work['completed'] and work['aggregate_cache_bytes']<=p['budget']['canonical_cache_bytes'],'physical ledger/resource cap')
    target=next(r for r in records if r['arm']=='native');c=cases[target['case']];rejected=prior_mutations(target,c,packets,p,networks)
    bad=deepcopy(c);bad['code_map']=[0]*8
    try:audit(target,bad,packets,p,networks)
    except ValueError:rejected.append('nonbijective_map')
    else:raise ValueError('accepted map mutation')
    bad=deepcopy(role);bad[0]['left']=1
    try:role_audit(bad,networks,p)
    except ValueError:rejected.append('numeric_role_coverage')
    else:raise ValueError('accepted role coverage mutation')
    quality=all(r['strict_correct'] and r.get('intermediate_correct',True) for r in rows) and all(r['semantic_equal'] for r in paired) and coverage['wrong']==0
    exposure={}
    source_descriptors={s['key']:s for s in p['sources']}
    for name in p['codebooks']:
        hist=Counter();pairs_seen=set();bits_seen=set()
        for c in p['cases']:
            if c['map_name']!=name:continue
            code={token:i for i,token in enumerate(c['vocabulary'])}
            for ck in c['candidates']:
                a=source_descriptors[ck]['observation']['goal']
                for fk in c['context']+c['T']:
                    b=source_descriptors[fk]['observation']['start'];x,y=code[a],code[b];pairs_seen.add((x,y));hist[(x^y).bit_count()]+=1;bits_seen.add(tuple((x>>i&1,y>>i&1) for i in range(3)))
        exposure[name]=dict(actual_role_comparisons=sum(hist.values()),ordered_code_pairs=sorted(pairs_seen),hamming_distance_histogram=dict(hist),bit_pair_patterns=len(bits_seen),changed_ordered_tokenpair_hamming=sum((i^j).bit_count()!=(p['codebooks'][name][i]^p['codebooks'][name][j]).bit_count() for i,j in itertools.product(range(8),repeat=2)))
    return dict(status='AUDITED',quality_pass=quality,finite_semantic_adoption=quality,counts=counts,exact=dict(cases=len(exact),strict=sum(r['strict_correct'] for r in exact)),role_coverage=coverage,paired_conditions=896,paired_invariant=sum(r['semantic_equal'] for r in paired),pairs=paired,physical_calls=calls,ticks=ticks,unique_traces=len(networks),max_scalar_error=max(scalar,max(x['numeric_replay_max_absolute_error'] for x in low)),mutation_rejections=rejected,actual_pipeline_coverage=exposure,source_calls=28,learning=0,world_measurement=0,production_adoption=False,statistical_speed_verdict=None),rows
