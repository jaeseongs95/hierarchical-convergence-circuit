"""Typed two-variable tuples; field equality and correlation erasure are native."""
from hcr.model import Config,fingerprint
from tools.r32_semantic_join.runtime import lower,export,require
from tools.r33_typed_feedback.runtime import kernel
from tools.r34_feasible_state.runtime import onehot
from tools.r35_compositional_slot import compiler
from tools.r35_compositional_slot.runtime import encode_role

def projection(layout,cfg):
    b=compiler.Builder(['f'+str(i) for i in range(4)],cfg)
    for axis in range(2):
        for value in range(2):b.node('p'+str(axis)+str(value),'or',[('f'+str(i),1) for i,xy in enumerate(layout) if xy[axis]==value])
    for i,xy in enumerate(layout):b.node('e'+str(i),'and',[('p0'+str(xy[0]),1),('p1'+str(xy[1]),1)])
    b.node('goal','or',[('e'+str(i),1) for i in range(4)]);return b.document()

def documents(cfg):
    layout=[[0,0],[0,1],[1,0],[1,1]];docs=dict(role=compiler.equality(cfg),pair=compiler.expression(['and',0,1],cfg),feasible=compiler.feasible(4,cfg),query=compiler.query(4,cfg),projection0=projection(layout,cfg),projection1=projection(layout[::-1],cfg))
    for n in range(5):
        b=compiler.Builder(['m'+str(i) for i in range(n)],cfg);b.node('goal','or',[('m'+str(i),1) for i in range(n)]);docs['or'+str(n)]=b.document()
    return docs

def validate(domains,alternatives,facts,predicate):
    require(set(domains)=={'X','Y'} and all(len(v)==len(set(v))==2 for v in domains.values()) and len(set(domains['X']+domains['Y']))==4,'two disjoint typed domains')
    product=[dict(X=x,Y=y) for x in domains['X'] for y in domains['Y']]
    require(alternatives in [product,product[::-1]],'public Cartesian assignment layout')
    require(len(facts)<=4 and len({p['origin_sha256'] for p in facts})==len(facts),'bounded distinct source references')
    require(all(f['predicate']==predicate and f['subject'] in domains['X'] and f['object'] in domains['Y'] and f['revision']==0 and f['value'] is True for f in facts),'typed relation metadata')

def membership(alternatives,facts,vocabulary,cfg,docs,initial):
    values=[];networks=[];gain=cfg.evidence_gain
    for assignment in alternatives:
        matches=[]
        for fact in facts:
            fields=[kernel(docs['role'],encode_role({'object':assignment[variable]},{'subject':fact[field]},vocabulary,cfg),cfg,initial) for variable,field in [('X','subject'),('Y','object')]]
            pair=kernel(docs['pair'],dict(m0=gain*(2*fields[0]['state']['goal']-1),m1=gain*(2*fields[1]['state']['goal']-1),m2=-gain),cfg,initial)
            networks.extend([*fields,pair]);matches.append(pair['state']['goal'])
        k=kernel(docs['or'+str(len(facts))],{'m'+str(i):gain*(2*v-1) for i,v in enumerate(matches)},cfg,initial);networks.append(k);values.append(k['state']['goal'])
    return values,networks

def promote(domains,alternatives,facts,k,cfg,representation):
    kind=onehot(k,['none','unique','many','incomplete'],cfg.margin_threshold);eligibility=[k['state']['e'+str(i)] for i in range(4)];hi=(1+cfg.margin_threshold)/2;lo=(1-cfg.margin_threshold)/2
    indices=[i for i,v in enumerate(eligibility) if v>=hi];index=indices[0] if kind=='unique' and len(indices)==1 and all(v<=lo for i,v in enumerate(eligibility) if i!=indices[0]) else None
    return dict(schema='hcr-r37-joint-tuple-v1',revision=1,variables=['X','Y'],domains=domains,alternatives=alternatives,eligibility=eligibility,coverage_activation=k['state']['complete'],kind=kind,selected_index=index,representation=representation,constraint_origin_refs=[f['origin_sha256'] for f in facts],state_sha256=fingerprint(k),posterior_is_probability=False,contract='explicit_complete_domains_and_closed_relation_tables')

def consume_t(binding,t,vocabulary,cfg,docs,initial):
    """No first C, case/mask, source registry, or exact solver inputs."""
    require(binding['schema']=='hcr-r37-joint-tuple-v1' and binding['revision']==1 and binding['variables']==['X','Y'] and len(binding['eligibility'])==4 and all(0<=v<=1 for v in binding['eligibility']) and 0<=binding['coverage_activation']<=1,'typed joint binding metadata')
    validate(binding['domains'],binding['alternatives'],t,'T')
    values,networks=membership(binding['alternatives'],t,vocabulary,cfg,docs,initial)
    drives={prefix+str(i):cfg.evidence_gain*(2*v-1) for prefix,vs in [('e',binding['eligibility']),('t',values)] for i,v in enumerate(vs)};drives['complete']=cfg.evidence_gain*(2*binding['coverage_activation']-1)
    k=kernel(docs['query'],drives,cfg,initial);networks.append(k);tag=onehot(k,['qtrue','qfalse','empty','mixed','incomplete'],cfg.margin_threshold)
    value=True if tag=='qtrue' else False if tag=='qfalse' else None;reason='decided' if value is not None else 'abstain_inconsistent' if tag=='empty' else 'abstain_ambiguous' if tag=='mixed' else 'abstain_incomplete' if tag=='incomplete' else 'abstain_dynamic'
    return dict(tag=tag,value=value,reason=reason,binding_sha256=fingerprint(binding),T_sha256=fingerprint(t)),networks

def exact(alternatives,context,t):
    feasible=[i for i,a in enumerate(alternatives) if any(a['X']==f['subject'] and a['Y']==f['object'] for f in context)]
    vals=[any(alternatives[i]['X']==f['subject'] and alternatives[i]['Y']==f['object'] for f in t) for i in feasible]
    value=None if not vals or len(set(vals))>1 else vals[0]
    return dict(kind='none' if not feasible else 'unique' if len(feasible)==1 else 'many',selected_index=feasible[0] if len(feasible)==1 else None,value=value,reason='abstain_inconsistent' if not vals else 'abstain_ambiguous' if value is None else 'decided',feasible=feasible,native_calls=0)

def execute(domains,alternatives,context,t,vocabulary,arm,configuration,initial):
    validate(domains,alternatives,context,'C');validate(domains,alternatives,t,'T')
    require(len(vocabulary)==len(set(vocabulary))==8 and set(domains['X']+domains['Y'])<=set(vocabulary),'public three-bit vocabulary')
    if arm=='exact_joint':return dict(arm=arm,**exact(alternatives,context,t))
    require(arm in ['native_joint','native_marginal'],'numeric arm');cfg=Config(**configuration);docs=documents(cfg)
    messages,networks=membership(alternatives,context,vocabulary,cfg,docs,initial);applied=messages
    if arm=='native_marginal':
        layout=[[domains['X'].index(a['X']),domains['Y'].index(a['Y'])] for a in alternatives]
        k=kernel(projection(layout,cfg),{'f'+str(i):cfg.evidence_gain*(2*v-1) for i,v in enumerate(messages)},cfg,initial);networks.append(k);applied=[k['state']['e'+str(i)] for i in range(4)]
    drives={'e'+str(i):cfg.evidence_gain*(2*v-1) for i,v in enumerate(applied)};drives['complete']=cfg.evidence_gain
    k=kernel(docs['feasible'],drives,cfg,initial);networks.append(k);binding=promote(domains,alternatives,context,k,cfg,arm)
    final,later=consume_t(binding,t,vocabulary,cfg,docs,initial);networks.extend(later)
    return dict(arm=arm,messages=messages,applied=applied,binding=binding,final=final,kind=binding['kind'],selected_index=binding['selected_index'],value=final['value'],reason=final['reason'],networks=networks,native_calls=12*(len(context)+len(t))+10+int(arm=='native_marginal'),independent_evidence_added=0)
