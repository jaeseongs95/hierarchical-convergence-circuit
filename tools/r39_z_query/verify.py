"""Independent full/product set oracles and every saved native causal edge."""
from collections import Counter
from copy import deepcopy
from hcr.model import fingerprint
from tools.r32_semantic_join.runtime import require
from tools.r34_feasible_state.verify import tag
from tools.r36_overlap_composition.verify import SavedNetworks

def oracle(domains,relations,order,queries,product=False):
    pairs={n:{(f['subject'],f['object']) for f in fs} for n,fs in relations.items()};triples={(x,y,z) for x in domains['X'] for y in domains['Y'] for z in domains['Z'] if (x,y) in pairs['R'] and (y,z) in pairs['S'] and (x,z) in pairs['U']}
    if product:triples={(x,y,z) for x,y in {(a,b) for a,b,c in triples} for z in {c for a,b,c in triples}}
    xy=[(x,y) for x in domains['X'] for y in domains['Y']][::1 if not order else -1];slices=[[(x,y,z) in triples for x,y in xy] for z in domains['Z']];answers=[]
    for q in queries:
        values={z for x,y,z in triples if q['kind']=='unary' or (x,y)==xy[q['slot']]};eligible=[z in values for z in domains['Z']];ids=[i for i,v in enumerate(eligible) if v];answers.append(dict(eligible=eligible,kind='none' if not ids else 'unique' if len(ids)==1 else 'many',selected_index=ids[0] if len(ids)==1 else None))
    return dict(slices=slices,xy=[any(row[i] for row in slices) for i in range(4)],z=[any(row) for row in slices],triples=sorted(triples),answers=answers)

def audit(r,c,packets,p,networks):
    d=c['domains'];order=c['order'];relations={n:[packets[k] for k in keys] for n,keys in c['relations'].items()};truth=oracle(d,relations,order,c['queries']);closure=oracle(d,relations,order,c['queries'],True);arm=r['arm'];require(r['case']==c['key'],'case');scores={n+'_'+s:0 for n in ['role','pair','membership','triple','projection','query_input'] for s in ['total','correct']};ks=[];answers=[]
    def bits(values):return [None if abs(2*v-1)<p['kernel']['margin_threshold'] else v>.5 for v in values]
    if arm=='exact_joint':
        require(r['network_ids']==[] and r['native_calls']==0 and sorted(map(tuple,r['triples']))==truth['triples'],'exact fullnativezero/independenttripleoracle')
        require(len(r['queries'])==5,'exact query count')
        for q in r['queries']:
            require(q['native_calls']==0 and set(q)=={'eligible','kind','selected_index','native_calls'},'exact query fields');answers.append(dict(eligible=q['eligible'],kind=q['kind'],selected_index=q['selected_index']))
        require(answers==truth['answers'],'exact independent set oracle')
        signature=tuple(int(v) for row in truth['slices'] for v in row)
    else:
        require(arm in ['native_joint','native_compact'],'native arm');L=sum(map(len,relations.values()));require(len(r['network_ids'])==r['native_calls']==12*L+(27 if arm=='native_joint' else 39),'physical calls');ks=[networks[n] for n in r['network_ids']];cursor=0;gain=p['kernel']['evidence_gain'];codes={v:i for i,v in enumerate(c['vocabulary'])};messages={}
        def check(k,name,drives):require(k['program']==p['programs'][name] and k['drives']==drives,'native Program/drives '+name)
        for name,axes in [('R',('X','Y')),('S',('Y','Z')),('U',('X','Z'))]:
            assignments=[(x,y) for x in d[axes[0]] for y in d[axes[1]]][::1 if not order else -1];facts=relations[name];values=[]
            for assignment in assignments:
                matches=[]
                for fact in facts:
                    fields=ks[cursor:cursor+2];pair=ks[cursor+2];cursor+=3;expected=[]
                    for k,token,field in zip(fields,assignment,['subject','object'],strict=True):
                        drives={prefix+str(i):gain*(1 if (codes[t]>>i)&1 else -1) for prefix,t in [('x',token),('y',fact[field])] for i in range(3)};check(k,'role',drives);expected.append(token==fact[field]);scores['role_total']+=1;scores['role_correct']+=k['adopted'] is expected[-1]
                    check(pair,'pair',dict(m0=gain*(2*fields[0]['state']['goal']-1),m1=gain*(2*fields[1]['state']['goal']-1),m2=-gain));matches.append(pair['state']['goal']);scores['pair_total']+=1;scores['pair_correct']+=pair['adopted'] is all(expected)
                k=ks[cursor];cursor+=1;check(k,'or'+str(len(facts)),{'m'+str(i):gain*(2*v-1) for i,v in enumerate(matches)});values.append(k['state']['goal']);scores['membership_total']+=1;scores['membership_correct']+=k['adopted'] is (assignment in {(f['subject'],f['object']) for f in facts})
            messages[name]=values
        require(r['messages']==messages,'membership numeric messages');ij=[(i,j) for i in range(2) for j in range(2)][::1 if not order else -1];position={xy:i for i,xy in enumerate(ij)}
        def gate(name,values,logical,layer):
            nonlocal cursor
            k=ks[cursor];cursor+=1;drives={'m'+str(i):gain*(2*v-1) for i,v in enumerate(values)}
            if name=='pair':drives['m2']=-gain
            check(k,name,drives);scores[layer+'_total']+=1;scores[layer+'_correct']+=k['adopted'] is logical;return k['state']['goal']
        slices=[[gate('triple',[messages['R'][position[x,y]],messages['S'][position[y,z]],messages['U'][position[x,z]]],truth['slices'][z][i],'triple') for i,(x,y) in enumerate(ij)] for z in range(2)];require(r['triple_slices']==slices,'R-applied triple states');payload=dict(slices=slices)
        if arm=='native_compact':
            xy=[gate('or2',[slices[0][i],slices[1][i]],truth['xy'][i],'projection') for i in range(4)];zs=[gate('or4',slices[z],truth['z'][z],'projection') for z in range(2)];payload=dict(xy=xy,z=zs)
        expected=dict(schema='hcr-r39-z-query-v1',revision=1,representation=arm,domains=d,alternatives=[dict(X=d['X'][x],Y=d['Y'][y]) for x,y in ij],payload=payload,payload_sha256=fingerprint(payload),source_refs={n:[f['origin_sha256'] for f in fs] for n,fs in relations.items()},posterior_is_probability=False,contract='complete_typed_domains_and_closed_relation_tables');require(r['binding']==expected and r['producer_seal_sha256']==fingerprint(expected),'query-independent sealed producer/provenance/payload')
        require(r['prefix_calls']==cursor==12*L+(20 if arm=='native_joint' else 26),'producer count before query');intervention=closure if arm=='native_compact' else truth;require(len(r['queries'])==5,'all queries retained')
        for qi,q in enumerate(c['queries']):
            start=cursor;values=[]
            for z in range(2):
                logical=intervention['answers'][qi]['eligible'][z]
                if arm=='native_joint':v=payload['slices'][z][q['slot']] if q['kind']=='conditional' else gate('or4',payload['slices'][z],logical,'query_input')
                elif q['kind']=='unary':v=payload['z'][z]
                else:v=gate('pair',[payload['xy'][q['slot']],payload['z'][z]],logical,'query_input')
                values.append(v)
            scores['query_input_total']+=2;scores['query_input_correct']+=sum(a is b for a,b in zip(bits(values),intervention['answers'][qi]['eligible'],strict=True));k=ks[cursor];cursor+=1;check(k,'feasible',dict(e0=gain*(2*values[0]-1),e1=gain*(2*values[1]-1),complete=gain));eligible=[k['state']['e0'],k['state']['e1']];kind=tag(k,['none','unique','many','incomplete'],p['kernel']);hi=(1+p['kernel']['margin_threshold'])/2;lo=(1-p['kernel']['margin_threshold'])/2;ids=[i for i,v in enumerate(eligible) if v>=hi];index=ids[0] if kind=='unique' and len(ids)==1 and all(v<=lo for i,v in enumerate(eligible) if i!=ids[0]) else None
            require(r['queries'][qi]==dict(messages=values,eligibility=eligible,kind=kind,selected_index=index,native_calls=cursor-start),'public routing/actualquerymessages/classifier output');answers.append(dict(eligible=bits(eligible),kind=kind,selected_index=index))
        require(cursor==len(ks) and r['independent_evidence_added']==0 and all(all(v==c['initial'] for v in k['initial'].values()) for k in ks),'complete refs/initial/noindependent evidence')
        signature=tuple(int(v) if v is not None else None for row in (bits(payload['xy']),bits(payload['z'])) for v in row) if arm=='native_compact' else tuple(int(v) if v is not None else None for row in payload['slices'] for v in bits(row))
    intervention=closure if arm=='native_compact' else truth;out=[]
    for qi,answer in enumerate(answers):
        tr=truth['answers'][qi];cl=intervention['answers'][qi];out.append(dict(query_index=qi,kind=c['queries'][qi]['kind'],observed=answer,truth=tr,intervention=cl,strict_correct=answer==tr,intervention_strict_correct=answer==cl,eligible_correct=sum(a is b for a,b in zip(answer['eligible'],tr['eligible'],strict=True)),intervention_eligible_correct=sum(a is b for a,b in zip(answer['eligible'],cl['eligible'],strict=True)),extra_z=sum(a is True and b is False for a,b in zip(answer['eligible'],tr['eligible'],strict=True)),missing_z=sum(a is False and b is True for a,b in zip(answer['eligible'],tr['eligible'],strict=True))))
    return dict(case=c['key'],arm=arm,r_mask=c['r_mask'],s_mask=c['s_mask'],u_mask=c['u_mask'],namespace=c['namespace'],order=order,queries=out,all_queries_correct=all(q['strict_correct'] for q in out),semantic_payload_signature=signature,first_failed_intermediate=next((n for n in ['role','pair','membership','triple','projection','query_input'] if scores[n+'_total']!=scores[n+'_correct']),None),**scores,physical_native_calls=len(ks),ticks=sum(k['cost']['kernel_ticks'] for k in ks),groups=sum(k['cost']['group_updates'] for k in ks),links=sum(k['cost']['signal_transmissions'] for k in ks))

def mutations(r,c,packets,p,networks):
    changes=[('revision',lambda x:x['binding'].update(revision=2)),('source',lambda x:x['binding']['source_refs']['R'].__setitem__(0,'wrong')),('payload',lambda x:x['binding']['payload']['slices'][0].__setitem__(0,.5)),('payload_hash',lambda x:x['binding'].update(payload_sha256='wrong')),('seal_hash',lambda x:x.update(producer_seal_sha256='wrong')),('triple',lambda x:x['triple_slices'][0].__setitem__(0,.5)),('R_message',lambda x:x['messages']['R'].__setitem__(0,.5)),('query_slot_swap',lambda x:x['queries'].__setitem__(slice(1,3),x['queries'][1:3][::-1])),('query_eligibility',lambda x:x['queries'][0]['eligibility'].__setitem__(0,.5)),('selected',lambda x:x['queries'][0].update(selected_index=99)),('prefix_count',lambda x:x.update(prefix_calls=0)),('network_ref',lambda x:x['network_ids'].__setitem__(0,x['network_ids'][-1]))];out=[]
    for name,change in changes:
        bad=deepcopy(r);change(bad)
        try:audit(bad,c,packets,p,networks)
        except (ValueError,KeyError):out.append(name)
        else:raise ValueError('accepted mutation '+name)
    return out

def summarize(rows):
    arms=sorted({r['arm'] for r in rows});counts={};base={(r['arm'],r['r_mask'],r['s_mask'],r['u_mask']):r for r in rows if r['namespace']==r['order']==0};meta={}
    for arm in arms:
        rr=[r for r in rows if r['arm']==arm];qq=[q for r in rr for q in r['queries']];sums=['physical_native_calls','ticks','groups','links']+[n+'_'+s for n in ['role','pair','membership','triple','projection','query_input'] for s in ['total','correct']];counts[arm]=dict(contexts=len(rr),queries=len(qq),all_contexts_correct=sum(r['all_queries_correct'] for r in rr),**{k:sum(r[k] for r in rr) for k in sums},**{k:sum(q[k] for q in qq) for k in ['strict_correct','intervention_strict_correct','eligible_correct','intervention_eligible_correct','extra_z','missing_z']},kinds=dict(Counter(q['observed']['kind'] for q in qq)),query_families={kind:dict(total=len(v),strict_correct=sum(q['strict_correct'] for q in v),intervention_strict_correct=sum(q['intervention_strict_correct'] for q in v)) for kind in ['unary','conditional'] for v in [[q for q in qq if q['kind']==kind]]},first_failed_intermediates=dict(Counter(str(r['first_failed_intermediate']) for r in rr)))
        variants=[r for r in rr if r['namespace'] or r['order']];meta[arm]=dict(context_pairs=len(variants),question_pairs=5*len(variants),invariant=sum(all(r['queries'][i]['observed']==base[(arm,r['r_mask'],r['s_mask'],r['u_mask'])]['queries'][i]['observed'] for i in range(5)) for r in variants))
    collision=[{k:r[k] for k in ['case','arm','r_mask','s_mask','u_mask','namespace','order','semantic_payload_signature','queries']} for r in rows if r['r_mask']==9 and r['s_mask']==r['u_mask'] and r['s_mask'] in [6,9]]
    return dict(counts=counts,metamorphic=meta,conditional_collision=collision)
