"""One typed, replacement-feedback roundtrip. No oracle/file access in consumers."""
from hcr import codec
from hcr.model import Config,Cost,Group,Link,Program,fingerprint
from tools.r32_semantic_join.runtime import lower,export,require

def program(doc):return Program(tuple(Group(**g) for g in doc['groups']),tuple(Link(**e) for e in doc['links']),tuple(tuple(p) for p in doc['paths']),doc['edge_count'])

def kernel(doc,drives,cfg,initial):
    from hcr.dynamics import settle
    pr=program(doc);cost=Cost(dynamic_groups_created=len(pr.groups),dynamic_links_created=len(pr.links));ticks=[];start={g.id:initial for g in pr.groups}
    state,conv=settle(pr,drives,cfg,cost,initial=start,observe=lambda i,s,r,k:ticks.append(dict(tick=i,state=dict(s),residual=r,stable_steps=k)))
    return dict(program=codec.plain(pr),program_sha256=pr.digest,drives=drives,initial=start,ticks=ticks,state=state,convergence=codec.plain(conv),cost=cost.snapshot(),adopted=state['goal']>=.5 if conv.status.value=='stable_decision' else None)

def compatibility(candidate,context,mode,vocabulary,cfg,docs,initial):
    """Per-field coding; equality and AND/OR are native graph operations."""
    code={vocabulary[0]:-cfg.evidence_gain,vocabulary[1]:cfg.evidence_gain}
    used=[context[0]] if mode=='one0' else [context[1]] if mode=='one1' else context
    drives={'x':code[candidate['object']]};drives.update({'y'+str(i):code[s['subject']] for i,s in enumerate(used)})
    return kernel(docs['one'] if len(used)==1 else docs[mode],drives,cfg,initial)

def selector(evidence,candidates,feedback,cfg,doc,initial):
    # Numeric message difference only. No host role equality, filtering or argmax.
    local=evidence[candidates[1]['object']]-evidence[candidates[0]['object']]
    return kernel(doc,{'local':cfg.evidence_gain*local,'context':cfg.evidence_gain*(feedback[1]-feedback[0])},cfg,initial)

def promote(candidates,selection,revision):
    index=None if selection['adopted'] is None else int(selection['adopted'])
    return dict(schema='hcr-r33-conditional-slot-v1',revision=revision,alternatives=candidates,selected_index=index,
        selected=None if index is None else candidates[index],selection_sha256=fingerprint(selection),uncertainty_kind='unresolved_dynamic' if index is None else 'native_decision',
        source_refs=[c['origin_sha256'] for c in candidates],posterior_is_probability=False)

def consume_t(binding,t,vocabulary,cfg,doc,initial):
    """Receives only the revised slot packet and T. No first context C or messages."""
    code={vocabulary[0]:-cfg.evidence_gain,vocabulary[1]:cfg.evidence_gain};selected=binding['selected']
    drives={'x':0.0 if selected is None else code[selected['object']],'y0':code[t['subject']]}
    k=kernel(doc,drives,cfg,initial);value=None if selected is None else k['adopted']
    return dict(kernel=k,value=value,reason='abstain_dynamic' if value is None else 'decided',
        argument=None if selected is None or value is None else dict(rule='typed_join' if value else 'typed_join_counterexample',role_terms=[selected['object'],t['subject']],source_refs=[selected['origin_sha256'],t['origin_sha256']]),
        binding_sha256=fingerprint(binding),t_sha256=fingerprint(t))

def exact(candidates,context,mode,t):
    """Declared ordinary full-information exact constraint solver, not a numeric adapter."""
    feasible=[]
    for i,c in enumerate(candidates):
        matches=[c['object']==s['subject'] for s in context]
        permitted=matches[0] if mode=='one0' else matches[1] if mode=='one1' else any(matches) if mode=='either' else all(matches)
        if permitted:feasible.append(i)
    truths=[candidates[i]['object']==t['subject'] for i in feasible]
    index=feasible[0] if len(feasible)==1 else None
    value=None if not truths or len(set(truths))>1 else truths[0]
    return dict(feasible=feasible,selected_index=index,value=value,reason='abstain_inconsistent' if not truths else 'abstain_ambiguous' if value is None else 'decided',role_equality_operations=4+len(feasible),kernels=[])

def execute(candidates,context,t,vocabulary,evidence,mode,arm,configuration,docs,initial):
    cfg=Config(**configuration)
    if arm=='exact':return dict(arm=arm,**exact(candidates,context,mode,t))
    require(arm in ('full','frozen'),'numeric arm')
    first=selector(evidence,candidates,[0.,0.],cfg,docs['selector'],initial)
    upper=[compatibility(c,context,mode,vocabulary,cfg,docs,initial) for c in candidates]
    returned=[k['state']['goal'] for k in upper];applied=returned if arm=='full' else [0.,0.]
    revised=selector(evidence,candidates,applied,cfg,docs['selector'],initial)
    initial_packet=promote(candidates,first,0);packet=promote(candidates,revised,1)
    final=consume_t(packet,t,vocabulary,cfg,docs['one'],initial)
    return dict(arm=arm,initial_packet=initial_packet,packet=packet,compatibility=upper,returned=returned,applied=applied,
        initial_selection=first,revised_selection=revised,final=final,value=final['value'],reason=final['reason'],selected_index=packet['selected_index'],
        feedback_is_replacement=True,independent_evidence_added=0,native_settles=5)
