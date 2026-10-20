"""Independent set oracle, every numeric causal edge, and paired workload counts."""
import json
from collections import Counter
from copy import deepcopy
from hcr.model import fingerprint
from tools.r32_semantic_join.runtime import require
from tools.r34_feasible_state.verify import tag
from tools.r36_overlap_composition.verify import SavedNetworks
from tools.r39_z_query.verify import oracle

LAYERS=['role','pair','membership','triple','query_input']
def audit(r,c,packets,p,networks):
    w=next(w for w in p['workloads'] if w['key']==r['workload']);queries=w['queries'];d=c['domains'];order=c['order'];relations={n:[packets[k] for k in keys] for n,keys in c['relations'].items()};truth=oracle(d,relations,0,queries);arm=r['arm'];require(r['case']==c['key'] and type(r['repetition']) is int and 0<=r['repetition']<3,'record identity');scores={n+'_'+s:0 for n in LAYERS for s in ['total','correct']};ks=[];answers=[]
    def bits(vs):return [None if abs(2*v-1)<p['kernel']['margin_threshold'] else v>.5 for v in vs]
    require(len(r['queries'])==len(queries) and r['prefix_core_cpu_seconds']>=0 and r['query_core_cpu_seconds']>=0,'queries/timing fields')
    if arm=='exact_joint':
        require(r['network_ids']==[] and r['native_calls']==r['prefix_calls']==0 and sorted(map(tuple,r['triples']))==truth['triples'],'explicit exact full solver');require(r['payload_numeric_values']==0 and r['payload_bytes']==len(json.dumps(r['triples'],separators=(',',':')).encode()),'exact serialized payload')
        for q in r['queries']:require(q['native_calls']==0 and set(q)=={'eligible','kind','selected_index','native_calls'},'exact fields');answers.append({k:q[k] for k in ['eligible','kind','selected_index']})
        require(answers==truth['answers'],'independent full oracle')
    else:
        require(arm in ['native_joint','native_factor'],'native arm');L=sum(map(len,relations.values()));expected_prefix=12*L+12+(8 if arm=='native_joint' else 0);expected_calls=expected_prefix+sum((1 if q['kind']=='conditional' else 3) if arm=='native_joint' else (3 if q['kind']=='conditional' else 11) for q in queries);require(r['native_calls']==len(r['network_ids'])==expected_calls,'physical count');ks=[networks[n] for n in r['network_ids']];cursor=0;gain=p['kernel']['evidence_gain'];codes={v:i for i,v in enumerate(c['vocabulary'])};messages={}
        def check(k,name,drives):require(k['program']==p['programs'][name] and k['drives']==drives,'Program/drives '+name)
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
        require(r['messages']==messages,'raw membership messages');factors={n:v[::1 if not order else -1] for n,v in messages.items()}
        def gate(name,values,logical,layer):
            nonlocal cursor
            k=ks[cursor];cursor+=1;check(k,name,{'m'+str(i):gain*(2*v-1) for i,v in enumerate(values)});scores[layer+'_total']+=1;scores[layer+'_correct']+=k['adopted'] is logical;return k['state']['goal']
        payload=dict(factors=factors)
        if arm=='native_joint':payload=dict(slices=[[gate('triple',[factors['R'][2*x+y],factors['S'][2*y+z],factors['U'][2*x+z]],truth['slices'][z][2*x+y],'triple') for x in range(2) for y in range(2)] for z in range(2)])
        expected=dict(schema='hcr-r40-factor-query-v1',revision=1,representation=arm,domains=d,alternatives=[dict(X=x,Y=y) for x in d['X'] for y in d['Y']],payload=payload,payload_sha256=fingerprint(payload),source_refs={n:[f['origin_sha256'] for f in fs] for n,fs in relations.items()},posterior_is_probability=False,contract='complete_typed_domains_and_closed_relation_tables');require(r['binding']==expected and r['producer_seal_sha256']==fingerprint(expected),'producer seal/roles/provenance');require(r['prefix_calls']==cursor==expected_prefix,'prefix physical boundary');require(r['payload_numeric_values']==(8 if arm=='native_joint' else 12) and r['payload_bytes']==len(json.dumps(payload,sort_keys=True,separators=(',',':')).encode()),'declared payload size')
        for qi,q in enumerate(queries):
            start=cursor;values=[]
            for z in range(2):
                if arm=='native_joint':v=payload['slices'][z][q['slot']] if q['kind']=='conditional' else gate('or4',payload['slices'][z],truth['answers'][qi]['eligible'][z],'query_input')
                else:
                    row=[]
                    for slot in (range(4) if q['kind']=='unary' else [q['slot']]):
                        x,y=divmod(slot,2);row.append(gate('triple',[factors['R'][2*x+y],factors['S'][2*y+z],factors['U'][2*x+z]],truth['slices'][z][slot],'triple'))
                    v=gate('or4',row,truth['answers'][qi]['eligible'][z],'query_input') if q['kind']=='unary' else row[0]
                values.append(v)
            scores['query_input_total']+=2;scores['query_input_correct']+=sum(a is b for a,b in zip(bits(values),truth['answers'][qi]['eligible'],strict=True));k=ks[cursor];cursor+=1;check(k,'feasible',dict(e0=gain*(2*values[0]-1),e1=gain*(2*values[1]-1),complete=gain));eligible=[k['state']['e0'],k['state']['e1']];kind=tag(k,['none','unique','many','incomplete'],p['kernel']);hi=(1+p['kernel']['margin_threshold'])/2;lo=(1-p['kernel']['margin_threshold'])/2;ids=[i for i,v in enumerate(eligible) if v>=hi];index=ids[0] if kind=='unique' and len(ids)==1 and all(v<=lo for i,v in enumerate(eligible) if i!=ids[0]) else None
            require(r['queries'][qi]==dict(messages=values,eligibility=eligible,kind=kind,selected_index=index,native_calls=cursor-start),'native query/classifier actual output');answers.append(dict(eligible=bits(eligible),kind=kind,selected_index=index))
        require(cursor==len(ks) and r['independent_evidence_added']==0 and all(all(v==c['initial'] for v in k['initial'].values()) for k in ks),'all refs/initial/no added evidence')
    qq=[dict(observed=answer,truth=tr,strict_correct=answer==tr,eligible_correct=sum(a is b for a,b in zip(answer['eligible'],tr['eligible'],strict=True))) for answer,tr in zip(answers,truth['answers'],strict=True)]
    return dict(case=c['key'],arm=arm,workload=w['key'],repetition=r['repetition'],namespace=c['namespace'],order=order,r_mask=c['r_mask'],s_mask=c['s_mask'],u_mask=c['u_mask'],queries=qq,strict_correct=sum(q['strict_correct'] for q in qq),eligible_correct=sum(q['eligible_correct'] for q in qq),all_correct=all(q['strict_correct'] for q in qq),**scores,prefix_calls=r['prefix_calls'],physical_native_calls=len(ks),ticks=sum(k['cost']['kernel_ticks'] for k in ks),groups=sum(k['cost']['group_updates'] for k in ks),links=sum(k['cost']['signal_transmissions'] for k in ks),payload_bytes=r['payload_bytes'],payload_numeric_values=r['payload_numeric_values'])

def mutations(r,c,packets,p,networks):
    changes=[('revision',lambda x:x['binding'].update(revision=2)),('source',lambda x:x['binding']['source_refs']['R'].__setitem__(0,'wrong')),('payload',lambda x:x['binding']['payload']['factors']['S'].__setitem__(0,.5)),('payload_hash',lambda x:x['binding'].update(payload_sha256='wrong')),('seal',lambda x:x.update(producer_seal_sha256='wrong')),('Rmessage',lambda x:x['messages']['R'].__setitem__(0,.5)),('query_swap',lambda x:x['queries'].__setitem__(slice(1,3),x['queries'][1:3][::-1])),('eligibility',lambda x:x['queries'][0]['eligibility'].__setitem__(0,.5)),('selected',lambda x:x['queries'][0].update(selected_index=99)),('prefix_count',lambda x:x.update(prefix_calls=0)),('network_ref',lambda x:x['network_ids'].__setitem__(0,x['network_ids'][-1])),('workload',lambda x:x.update(workload='q1'))];out=[]
    for name,change in changes:
        bad=deepcopy(r);change(bad)
        try:audit(bad,c,packets,p,networks)
        except (ValueError,KeyError):out.append(name)
        else:raise ValueError('accepted mutation '+name)
    return out

def summarize(rows):
    counts={};meta={};repeat={};keys=['physical_native_calls','prefix_calls','ticks','groups','links','strict_correct','eligible_correct']+[n+'_'+s for n in LAYERS for s in ['total','correct']]
    for arm in sorted({r['arm'] for r in rows}):
        rr=[r for r in rows if r['arm']==arm];counts[arm]=dict(records=len(rr),queries=sum(len(r['queries']) for r in rr),all_records_correct=sum(r['all_correct'] for r in rr),**{k:sum(r[k] for r in rr) for k in keys},workloads={w:dict(records=len(v),queries=sum(len(r['queries']) for r in v),**{k:sum(r[k] for r in v) for k in keys}) for w in sorted({r['workload'] for r in rr}) for v in [[r for r in rr if r['workload']==w]]})
        base={(r['r_mask'],r['s_mask'],r['u_mask'],r['workload'],r['repetition']):r for r in rr if r['namespace']==r['order']==0};variants=[r for r in rr if r['namespace'] or r['order']];meta[arm]=dict(record_pairs=len(variants),question_pairs=sum(len(r['queries']) for r in variants),invariant=sum(r['queries']==base[r['r_mask'],r['s_mask'],r['u_mask'],r['workload'],r['repetition']]['queries'] for r in variants));first={(r['case'],r['workload']):r for r in rr if r['repetition']==0};later=[r for r in rr if r['repetition']];repeat[arm]=dict(record_pairs=len(later),invariant=sum(r['queries']==first[r['case'],r['workload']]['queries'] for r in later))
    return dict(counts=counts,metamorphic=meta,repetition=repeat)
