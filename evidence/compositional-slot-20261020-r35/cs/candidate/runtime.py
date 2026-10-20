"""Compositional native route; same-information exact is explicitly symbolic."""
from hcr.model import Config,fingerprint
from tools.r32_semantic_join.runtime import lower,export,require
from tools.r33_typed_feedback.runtime import kernel
from tools.r34_feasible_state.runtime import onehot
from tools.r35_compositional_slot import compiler

def encode_role(candidate,fact,vocabulary,cfg):
    codes={token:i for i,token in enumerate(vocabulary)};require(len(codes)==len(vocabulary)==8,'three-bit vocabulary')
    return {p+str(i):cfg.evidence_gain*(1 if (codes[token]>>i)&1 else -1) for p,token in [('x',candidate['object']),('y',fact['subject'])] for i in range(3)}

def evaluate(candidates,facts,tree,vocabulary,cfg,role_doc,expr_doc,initial):
    values=[];networks=[]
    for candidate in candidates:
        matches=[kernel(role_doc,encode_role(candidate,f,vocabulary,cfg),cfg,initial) for f in facts]
        drives={'m'+str(i):cfg.evidence_gain*(2*k['state']['goal']-1) for i,k in enumerate(matches)}
        k=kernel(expr_doc,drives,cfg,initial);networks.extend([*matches,k]);values.append(k['state']['goal'])
    return values,networks

def promote(candidates,k,cfg):
    kind=onehot(k,['none','unique','many','incomplete'],cfg.margin_threshold);n=len(candidates)
    eligibility=[k['state']['e'+str(i)] for i in range(n)];hi=(1+cfg.margin_threshold)/2;lo=(1-cfg.margin_threshold)/2
    indices=[i for i,v in enumerate(eligibility) if v>=hi]
    index=indices[0] if kind=='unique' and len(indices)==1 and all(v<=lo for i,v in enumerate(eligibility) if i!=indices[0]) else None
    return dict(schema='hcr-r35-compositional-slot-v1',revision=1,alternatives=candidates,eligibility=eligibility,coverage_activation=k['state']['complete'],kind=kind,selected_index=index,source_refs=[c['origin_sha256'] for c in candidates],state_sha256=fingerprint(k),posterior_is_probability=False)

def consume_t(binding,t,t_tree,vocabulary,cfg,role_doc,expr_doc,query_doc,initial):
    values,networks=evaluate(binding['alternatives'],t,t_tree,vocabulary,cfg,role_doc,expr_doc,initial)
    drives={p+str(i):cfg.evidence_gain*(2*v-1) for p,vs in [('e',binding['eligibility']),('t',values)] for i,v in enumerate(vs)}
    drives['complete']=cfg.evidence_gain*(2*binding['coverage_activation']-1)
    k=kernel(query_doc,drives,cfg,initial);networks.append(k)
    tag=onehot(k,['qtrue','qfalse','empty','mixed','incomplete'],cfg.margin_threshold)
    value=True if tag=='qtrue' else False if tag=='qfalse' else None
    reason='decided' if value is not None else 'abstain_inconsistent' if tag=='empty' else 'abstain_ambiguous' if tag=='mixed' else 'abstain_incomplete' if tag=='incomplete' else 'abstain_dynamic'
    return dict(tag=tag,value=value,reason=reason,binding_sha256=fingerprint(binding),T_sha256=fingerprint(dict(packets=t,expression=t_tree))),networks

def truth(tree,matches):
    if type(tree) is int:return matches[tree]
    op=tree[0];a=truth(tree[1],matches)
    if op=='not':return not a
    b=truth(tree[2],matches);return a and b if op=='and' else a or b

def exact(candidates,context,c_tree,t,t_tree,complete):
    indices=[i for i,c in enumerate(candidates) if truth(c_tree,[c['object']==s['subject'] for s in context])]
    values=[truth(t_tree,[candidates[i]['object']==s['subject'] for s in t]) for i in indices]
    kind='incomplete' if not complete else 'none' if not indices else 'unique' if len(indices)==1 else 'many'
    value=None if not complete or not values or len(set(values))>1 else values[0]
    reason='abstain_incomplete' if not complete else 'abstain_inconsistent' if not values else 'abstain_ambiguous' if value is None else 'decided'
    return dict(kind=kind,selected_index=indices[0] if complete and len(indices)==1 else None,value=value,reason=reason,feasible=indices,native_calls=0)

def execute(candidates,context,c_tree,t,t_tree,complete,vocabulary,arm,configuration,initial):
    if arm=='exact':return dict(arm=arm,**exact(candidates,context,c_tree,t,t_tree,complete))
    require(arm=='native','native or exact');cfg=Config(**configuration);n=len(candidates)
    role=compiler.equality(cfg);c_doc=compiler.expression(c_tree,cfg);t_doc=compiler.expression(t_tree,cfg)
    f_doc=compiler.feasible(n,cfg);q_doc=compiler.query(n,cfg)
    messages,networks=evaluate(candidates,context,c_tree,vocabulary,cfg,role,c_doc,initial)
    drives={'e'+str(i):cfg.evidence_gain*(2*v-1) for i,v in enumerate(messages)};drives['complete']=cfg.evidence_gain*(1 if complete else -1)
    k=kernel(f_doc,drives,cfg,initial);networks.append(k);binding=promote(candidates,k,cfg)
    final,later=consume_t(binding,t,t_tree,vocabulary,cfg,role,t_doc,q_doc,initial);networks.extend(later)
    return dict(arm=arm,messages=messages,binding=binding,final=final,kind=binding['kind'],selected_index=binding['selected_index'],value=final['value'],reason=final['reason'],networks=networks,native_calls=8*n+2,independent_evidence_added=0)
