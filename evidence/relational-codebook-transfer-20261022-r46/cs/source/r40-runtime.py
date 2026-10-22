"""Fresh sealed producers for matched joint-slice/factor query workloads."""
import json,time
from hcr.model import Config,fingerprint
from tools.r32_semantic_join.runtime import lower,export,require
from tools.r33_typed_feedback.runtime import kernel
from tools.r34_feasible_state.runtime import onehot
from tools.r37_joint_tuple.runtime import membership
from tools.r38_shared_witness.runtime import AXES,layout,validate
from tools.r39_z_query.runtime import documents,gate

def produce(domains,relations,vocabulary,order,representation,configuration,initial):
    validate(domains,relations,vocabulary,order);require(representation in ['native_joint','native_factor'],'representation');cfg=Config(**configuration);docs=documents(cfg);messages={};ks=[]
    for name,axes in AXES.items():
        values,nets=membership(layout(domains,axes,order),relations[name],vocabulary,cfg,docs,initial);ks.extend(nets);messages[name]=values
    factors={n:vs[::1 if not order else -1] for n,vs in messages.items()};payload=dict(factors=factors)
    if representation=='native_joint':
        slices=[]
        for z in range(2):
            row=[]
            for x in range(2):
                for y in range(2):
                    k=gate('triple',[factors['R'][2*x+y],factors['S'][2*y+z],factors['U'][2*x+z]],cfg,docs,initial);ks.append(k);row.append(k['state']['goal'])
            slices.append(row)
        payload=dict(slices=slices)
    binding=dict(schema='hcr-r40-factor-query-v1',revision=1,representation=representation,domains=domains,alternatives=layout(domains,('X','Y'),0),payload=payload,payload_sha256=fingerprint(payload),source_refs={n:[f['origin_sha256'] for f in fs] for n,fs in relations.items()},posterior_is_probability=False,contract='complete_typed_domains_and_closed_relation_tables')
    return dict(messages=messages,binding=binding,networks=ks,prefix_calls=len(ks))

def consume(payload,query,representation,cfg,docs,initial):
    """Canonical public integer slot only; no facts/binding/query registry."""
    require(set(query)=={'kind','slot'} and (query['kind']=='unary' and query['slot'] is None or query['kind']=='conditional' and type(query['slot']) is int and 0<=query['slot']<4),'public query')
    require(representation in ['native_joint','native_factor'],'representation');require(set(payload)==({'slices'} if representation=='native_joint' else {'factors'}),'payload keys')
    if representation=='native_joint':require(len(payload['slices'])==2 and all(len(v)==4 for v in payload['slices']),'joint shape');arrays=payload['slices']
    else:require(set(payload['factors'])=={'R','S','U'} and all(len(v)==4 for v in payload['factors'].values()),'factor shape');arrays=payload['factors'].values()
    require(all(type(v) in [int,float] and 0<=v<=1 for row in arrays for v in row),'numeric bounded payload');ks=[];values=[]
    for z in range(2):
        if representation=='native_joint':
            if query['kind']=='conditional':v=payload['slices'][z][query['slot']]
            else:k=gate('or4',payload['slices'][z],cfg,docs,initial);ks.append(k);v=k['state']['goal']
        else:
            f=payload['factors'];slots=range(4) if query['kind']=='unary' else [query['slot']];row=[]
            for slot in slots:
                x,y=divmod(slot,2);k=gate('triple',[f['R'][2*x+y],f['S'][2*y+z],f['U'][2*x+z]],cfg,docs,initial);ks.append(k);row.append(k['state']['goal'])
            if query['kind']=='unary':k=gate('or4',row,cfg,docs,initial);ks.append(k);v=k['state']['goal']
            else:v=row[0]
        values.append(v)
    k=kernel(docs['feasible'],dict(e0=cfg.evidence_gain*(2*values[0]-1),e1=cfg.evidence_gain*(2*values[1]-1),complete=cfg.evidence_gain),cfg,initial);ks.append(k);kind=onehot(k,['none','unique','many','incomplete'],cfg.margin_threshold);eligible=[k['state']['e0'],k['state']['e1']];hi=(1+cfg.margin_threshold)/2;lo=(1-cfg.margin_threshold)/2;ids=[i for i,v in enumerate(eligible) if v>=hi];index=ids[0] if kind=='unique' and len(ids)==1 and all(v<=lo for i,v in enumerate(eligible) if i!=ids[0]) else None
    return dict(messages=values,eligibility=eligible,kind=kind,selected_index=index,native_calls=len(ks)),ks

def execute(domains,relations,vocabulary,order,queries,arm,configuration,initial):
    start=time.process_time();validate(domains,relations,vocabulary,order);answers=[]
    if arm=='exact_joint':
        pairs={n:{(f['subject'],f['object']) for f in fs} for n,fs in relations.items()};triples=sorted((x,y,z) for x in domains['X'] for y in domains['Y'] for z in domains['Z'] if (x,y) in pairs['R'] and (y,z) in pairs['S'] and (x,z) in pairs['U']);prefix=time.process_time()-start;query_start=time.process_time();xy=layout(domains,('X','Y'),0)
        for q in queries:
            zs={z for x,y,z in triples if q['kind']=='unary' or (x,y)==(xy[q['slot']]['X'],xy[q['slot']]['Y'])};eligible=[z in zs for z in domains['Z']];ids=[i for i,v in enumerate(eligible) if v];answers.append(dict(eligible=eligible,kind='none' if not ids else 'unique' if len(ids)==1 else 'many',selected_index=ids[0] if len(ids)==1 else None,native_calls=0))
        return dict(arm=arm,triples=triples,queries=answers,prefix_calls=0,native_calls=0,payload_numeric_values=0,payload_bytes=len(json.dumps(triples,separators=(',',':')).encode()),prefix_core_cpu_seconds=prefix,query_core_cpu_seconds=time.process_time()-query_start)
    r=produce(domains,relations,vocabulary,order,arm,configuration,initial);binding=r['binding'];before=fingerprint(binding);cfg=Config(**configuration);docs=documents(cfg);r.update(payload_numeric_values=8 if arm=='native_joint' else 12,payload_bytes=len(json.dumps(binding['payload'],sort_keys=True,separators=(',',':')).encode()),prefix_core_cpu_seconds=time.process_time()-start);query_start=time.process_time()
    for q in queries:
        require(fingerprint(binding)==before and fingerprint(binding['payload'])==binding['payload_sha256'],'sealed before query');answer,ks=consume(binding['payload'],q,arm,cfg,docs,initial);answers.append(answer);r['networks'].extend(ks);require(fingerprint(binding)==before,'sealed after query')
    r.update(arm=arm,queries=answers,native_calls=len(r['networks']),producer_seal_sha256=before,independent_evidence_added=0,query_core_cpu_seconds=time.process_time()-query_start);return r
