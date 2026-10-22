"""Seal joint Z slices or erase correlations before public conditional queries."""
from hcr.model import Config,fingerprint
from tools.r32_semantic_join.runtime import lower,export,require
from tools.r33_typed_feedback.runtime import kernel
from tools.r34_feasible_state.runtime import onehot
from tools.r35_compositional_slot import compiler
from tools.r37_joint_tuple.runtime import membership
from tools.r38_shared_witness.runtime import AXES,layout,validate

def documents(cfg):
    from tools.r38_shared_witness.runtime import documents as prior
    docs=prior(cfg);docs['feasible']=compiler.feasible(2,cfg);docs['triple']=compiler.expression(['and',0,['and',1,2]],cfg);return docs

def gate(name,values,cfg,docs,initial):
    drives={'m'+str(i):cfg.evidence_gain*(2*v-1) for i,v in enumerate(values)}
    if name=='pair':drives['m2']=-cfg.evidence_gain
    return kernel(docs[name],drives,cfg,initial)

def produce(domains,relations,vocabulary,order,representation,configuration,initial):
    """No query is accepted by the producer."""
    validate(domains,relations,vocabulary,order);require(representation in ['native_joint','native_compact'],'representation');cfg=Config(**configuration);docs=documents(cfg);messages={};ks=[]
    for name,axes in AXES.items():
        values,networks=membership(layout(domains,axes,order),relations[name],vocabulary,cfg,docs,initial);messages[name]=values;ks.extend(networks)
    ij=[(x,y) for x in range(2) for y in range(2)][::1 if not order else -1];position={xy:i for i,xy in enumerate(ij)};slices=[]
    for z in range(2):
        row=[]
        for x,y in ij:
            k=gate('triple',[messages['R'][position[x,y]],messages['S'][position[y,z]],messages['U'][position[x,z]]],cfg,docs,initial);ks.append(k);row.append(k['state']['goal'])
        slices.append(row)
    payload=dict(slices=slices)
    if representation=='native_compact':
        xy=[];zs=[]
        for i in range(4):
            k=gate('or2',[slices[0][i],slices[1][i]],cfg,docs,initial);ks.append(k);xy.append(k['state']['goal'])
        for z in range(2):
            k=gate('or4',slices[z],cfg,docs,initial);ks.append(k);zs.append(k['state']['goal'])
        payload=dict(xy=xy,z=zs)
    binding=dict(schema='hcr-r39-z-query-v1',revision=1,representation=representation,domains=domains,alternatives=layout(domains,('X','Y'),order),payload=payload,payload_sha256=fingerprint(payload),source_refs={n:[f['origin_sha256'] for f in fs] for n,fs in relations.items()},posterior_is_probability=False,contract='complete_typed_domains_and_closed_relation_tables')
    return dict(messages=messages,triple_slices=slices,binding=binding,networks=ks,native_calls=len(ks))

def consume(payload,query,representation,cfg,docs,initial):
    """Only numeric payload and public routing; no binding/facts/hash registry."""
    require(set(query)=={'kind','slot'} and (query['kind']=='unary' and query['slot'] is None or query['kind']=='conditional' and type(query['slot']) is int and 0<=query['slot']<4),'public query routing')
    expected={'slices'} if representation=='native_joint' else {'xy','z'} if representation=='native_compact' else None;require(set(payload)==expected,'numeric payload keys only')
    require((representation=='native_joint' and len(payload['slices'])==2 and all(len(row)==4 for row in payload['slices'])) or (representation=='native_compact' and len(payload['xy'])==4 and len(payload['z'])==2),'payload shape')
    require(all(type(v) in [int,float] and 0<=v<=1 for vs in (payload['slices'] if representation=='native_joint' else [payload['xy'],payload['z']]) for v in vs),'bounded numeric values');values=[];ks=[]
    for z in range(2):
        if representation=='native_joint':
            if query['kind']=='conditional':v=payload['slices'][z][query['slot']]
            else:k=gate('or4',payload['slices'][z],cfg,docs,initial);ks.append(k);v=k['state']['goal']
        elif query['kind']=='unary':v=payload['z'][z]
        else:k=gate('pair',[payload['xy'][query['slot']],payload['z'][z]],cfg,docs,initial);ks.append(k);v=k['state']['goal']
        values.append(v)
    k=kernel(docs['feasible'],dict(e0=cfg.evidence_gain*(2*values[0]-1),e1=cfg.evidence_gain*(2*values[1]-1),complete=cfg.evidence_gain),cfg,initial);ks.append(k);kind=onehot(k,['none','unique','many','incomplete'],cfg.margin_threshold);eligible=[k['state']['e0'],k['state']['e1']];hi=(1+cfg.margin_threshold)/2;lo=(1-cfg.margin_threshold)/2;ids=[i for i,v in enumerate(eligible) if v>=hi];index=ids[0] if kind=='unique' and len(ids)==1 and all(v<=lo for i,v in enumerate(eligible) if i!=ids[0]) else None
    return dict(messages=values,eligibility=eligible,kind=kind,selected_index=index,native_calls=len(ks)),ks

def exact(domains,relations,order,queries):
    triples={(x,y,z) for x in domains['X'] for y in domains['Y'] for z in domains['Z'] if all(any(f['subject']==a and f['object']==b for f in relations[n]) for n,a,b in [('R',x,y),('S',y,z),('U',x,z)])};alternatives=layout(domains,('X','Y'),order);out=[]
    for q in queries:
        zs={z for x,y,z in triples if q['kind']=='unary' or (x,y)==(alternatives[q['slot']]['X'],alternatives[q['slot']]['Y'])};eligible=[z in zs for z in domains['Z']];ids=[i for i,v in enumerate(eligible) if v];out.append(dict(eligible=eligible,kind='none' if not ids else 'unique' if len(ids)==1 else 'many',selected_index=ids[0] if len(ids)==1 else None,native_calls=0))
    return dict(arm='exact_joint',queries=out,triples=sorted(triples),native_calls=0)

def execute(domains,relations,vocabulary,order,queries,arm,configuration,initial):
    validate(domains,relations,vocabulary,order)
    if arm=='exact_joint':return exact(domains,relations,order,queries)
    r=produce(domains,relations,vocabulary,order,arm,configuration,initial);binding=r['binding'];before=fingerprint(binding);cfg=Config(**configuration);docs=documents(cfg);answers=[];r['prefix_calls']=r['native_calls']
    for q in queries:
        require(fingerprint(binding)==before and fingerprint(binding['payload'])==binding['payload_sha256'],'sealed producer before query')
        answer,ks=consume(binding['payload'],q,arm,cfg,docs,initial);answers.append(answer);r['networks'].extend(ks);require(fingerprint(binding)==before,'producer immutable after query')
    r.update(arm=arm,queries=answers,native_calls=len(r['networks']),producer_seal_sha256=before,independent_evidence_added=0);return r
