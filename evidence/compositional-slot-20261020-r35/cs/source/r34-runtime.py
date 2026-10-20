"""Native feasible-set channels and universal T consumer, no symbolic repair."""
from hcr.model import Config,fingerprint
from tools.r32_semantic_join.runtime import require,export,lower
from tools.r33_typed_feedback.runtime import kernel,compatibility

def onehot(k,labels,margin):
    if k['convergence']['status'] not in ['stable_decision','stable_ambiguous']:return None
    low=(1-margin)/2;high=(1+margin)/2
    selected=[label for label in labels if k['state'][label]>=high]
    if len(selected)!=1 or any(k['state'][x]>low for x in labels if x!=selected[0]):return None
    return selected[0]

def feasible(messages,arm,cfg,doc,initial):
    require(arm in ['full','delta'],'numeric arm')
    pair=list(messages)
    if arm=='delta':
        delta=messages[1]-messages[0];pair=[.5-delta/2,.5+delta/2]
    drives={'f0':cfg.evidence_gain*(2*pair[0]-1),'f1':cfg.evidence_gain*(2*pair[1]-1)}
    k=kernel(doc,drives,cfg,initial);tag=onehot(k,['none','u0','u1','many'],cfg.margin_threshold)
    return k,tag,pair

def promote(candidates,k,tag):
    return dict(schema='hcr-r34-feasible-slot-v1',revision=1,alternatives=candidates,eligibility=[k['state']['f0'],k['state']['f1']],kind=tag,
        selected_index=0 if tag=='u0' else 1 if tag=='u1' else None,source_refs=[c['origin_sha256'] for c in candidates],state_sha256=fingerprint(k),posterior_is_probability=False)

def consume_t(binding,t,t_mode,vocabulary,cfg,docs,initial):
    """No C, role-compatibility messages, case ID, softprior or oracle arguments."""
    matches=[compatibility(c,t,t_mode,vocabulary,cfg,docs,initial) for c in binding['alternatives']]
    gain=cfg.evidence_gain;values=[*binding['eligibility'],*(m['state']['goal'] for m in matches)]
    drives={name:gain*(2*v-1) for name,v in zip(['f0','f1','t0','t1'],values,strict=True)}
    k=kernel(docs['query'],drives,cfg,initial);tag=onehot(k,['qtrue','qfalse','empty','mixed'],cfg.margin_threshold)
    value=True if tag=='qtrue' else False if tag=='qfalse' else None
    reason='decided' if value is not None else 'abstain_inconsistent' if tag=='empty' else 'abstain_ambiguous' if tag=='mixed' else 'abstain_dynamic'
    return dict(matches=matches,kernel=k,tag=tag,value=value,reason=reason,binding_sha256=fingerprint(binding),T_sha256=fingerprint(dict(packets=t,mode=t_mode)))

def exact(candidates,context,mode,t,t_mode):
    def allowed(c,facts,operator):
        m=[c['object']==s['subject'] for s in facts]
        return m[0] if operator=='one0' else m[1] if operator=='one1' else any(m) if operator=='either' else all(m)
    indices=[i for i,c in enumerate(candidates) if allowed(c,context,mode)];v=[allowed(candidates[i],t,t_mode) for i in indices]
    kind='none' if not indices else 'many' if len(indices)==2 else 'u'+str(indices[0]);value=None if not v or len(set(v))>1 else v[0]
    return dict(kind=kind,selected_index=indices[0] if len(indices)==1 else None,value=value,reason='abstain_inconsistent' if not v else 'abstain_ambiguous' if value is None else 'decided',feasible=indices,native_calls=0)

def execute(candidates,context,mode,t,t_mode,vocabulary,soft_evidence,arm,configuration,docs,initial):
    cfg=Config(**configuration)
    if arm=='exact':return dict(arm=arm,**exact(candidates,context,mode,t,t_mode))
    # soft_evidence is preference metadata, deliberately excluded from hard feasibility.
    upper=[compatibility(c,context,mode,vocabulary,cfg,docs,initial) for c in candidates];messages=[k['state']['goal'] for k in upper]
    k,tag,pair=feasible(messages,arm,cfg,docs['feasible'],initial);binding=promote(candidates,k,tag);final=consume_t(binding,t,t_mode,vocabulary,cfg,docs,initial)
    return dict(arm=arm,kind=tag,selected_index=binding['selected_index'],value=final['value'],reason=final['reason'],context_kernels=upper,messages=messages,applied=pair,
        feasible_kernel=k,binding=binding,final=final,native_calls=6,soft_preference_applied_to_hard_state=False,independent_evidence_added=0)
