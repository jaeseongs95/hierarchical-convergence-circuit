"""Lossless trace expansion and separate semantic/controller/count verification."""
from copy import deepcopy
from hcr.model import fingerprint
from tools.r32_semantic_join.runtime import require
from tools.r33_typed_feedback.verify import replay

def expand_network(doc,p):
    require(doc['config_sha256']==fingerprint(p['kernel']),'network config binding')
    pr=p['programs'][doc['program_key']];ids=[g['id'] for g in pr['groups']]
    ticks=[dict(tick=i,state=dict(zip(ids,row[2:],strict=True)),residual=row[0],stable_steps=row[1]) for i,row in enumerate(doc['tick_vectors'],1)]
    k=dict(program=pr,program_sha256=doc['program_sha256'],drives=doc['drives'],initial={x:doc['initial_scalar'] for x in ids},ticks=ticks,state=dict(zip(ids,doc['final_vector'],strict=True)),convergence=doc['convergence'],cost=doc['cost'],adopted=doc['adopted'])
    require(fingerprint(dict(kernel=k,config=p['kernel']))==doc['content_sha256'],'lossless native record digest');return k

def oracle(candidates,context,mode,t,tmode):
    def subset(facts,op):
        a={i for i,c in enumerate(candidates) if c['object']==facts[0]['subject']};b={i for i,c in enumerate(candidates) if c['object']==facts[1]['subject']}
        return a if op=='one0' else b if op=='one1' else a|b if op=='either' else a&b
    feasible=subset(context,mode);positive=subset(t,tmode);values={i in positive for i in feasible}
    return dict(kind='none' if not feasible else 'many' if len(feasible)==2 else 'u'+str(next(iter(feasible))),selected_index=next(iter(feasible)) if len(feasible)==1 else None,value=next(iter(values)) if len(values)==1 else None,
        reason='abstain_inconsistent' if not feasible else 'abstain_ambiguous' if len(values)>1 else 'decided',feasible=sorted(feasible))

def tag(k,labels,cfg):
    if k['convergence']['status'] not in ['stable_decision','stable_ambiguous']:return None
    positive={x for x in labels if 2*k['state'][x]-1>=cfg['margin_threshold']};negative={x for x in labels if 1-2*k['state'][x]>=cfg['margin_threshold']}
    return next(iter(positive)) if len(positive)==1 and len(negative)==len(labels)-1 else None

def audit(r,c,packets,p,networks):
    candidates=[packets[k] for k in c['candidates']];context=[packets[k] for k in c['context']];t=[packets[k] for k in c['T']];truth=oracle(candidates,context,c['mode'],t,c['t_mode']);arm=r['arm'];require(r['case']==c['key'],'case binding')
    if arm=='exact':
        for k,v in truth.items():require(r[k]==v,'exact semantic '+k)
        require(r['native_calls']==0 and r['network_ids']==[],'exact no native');ks=[]
    else:
        require(arm in ['full','delta'] and len(r['network_ids'])==r['native_calls']==6,'physical call refs');ks=[networks[x] for x in r['network_ids']];upper=ks[:2];lower=ks[2];Tmatches=ks[3:5];query=ks[5]
        gain=p['kernel']['evidence_gain'];code={c['vocabulary'][0]:-gain,c['vocabulary'][1]:gain}
        for candidate,k in zip(candidates,upper,strict=True):
            used=[context[0]] if c['mode']=='one0' else [context[1]] if c['mode']=='one1' else context;drives={'x':code[candidate['object']]};drives.update({'y'+str(i):code[s['subject']] for i,s in enumerate(used)})
            require(k['program']==p['programs']['one' if len(used)==1 else c['mode']] and k['drives']==drives,'C field-only native compatibility')
        messages=[k['state']['goal'] for k in upper];pair=messages if arm=='full' else [.5-(messages[1]-messages[0])/2,.5+(messages[1]-messages[0])/2]
        require(r['messages']==messages and r['applied']==pair,'common-mode-only intervention');require(lower['program']==p['programs']['feasible'] and lower['drives']=={'f0':gain*(2*pair[0]-1),'f1':gain*(2*pair[1]-1)},'lower preserves pair')
        kind=tag(lower,['none','u0','u1','many'],p['kernel']);index=0 if kind=='u0' else 1 if kind=='u1' else None;b=r['binding']
        expected=dict(schema='hcr-r34-feasible-slot-v1',revision=1,alternative_keys=c['candidates'],eligibility=[lower['state']['f0'],lower['state']['f1']],kind=kind,selected_index=index,source_refs=[x['origin_sha256'] for x in candidates],state_sha256=fingerprint(lower),posterior_is_probability=False)
        require(b==expected and r['kind']==kind and r['selected_index']==index,'slot source/roles/revision/native classification')
        full_binding=dict(b);del full_binding['alternative_keys'];full_binding['alternatives']=candidates
        for candidate,k in zip(candidates,Tmatches,strict=True):
            used=[t[0]] if c['t_mode']=='one0' else [t[1]] if c['t_mode']=='one1' else t;drives={'x':code[candidate['object']]};drives.update({'y'+str(i):code[s['subject']] for i,s in enumerate(used)})
            require(k['program']==p['programs']['one' if len(used)==1 else c['t_mode']] and k['drives']==drives,'independent T compatibility')
        values=[*b['eligibility'],*(k['state']['goal'] for k in Tmatches)];drives={name:gain*(2*v-1) for name,v in zip(['f0','f1','t0','t1'],values,strict=True)};require(query['program']==p['programs']['query'] and query['drives']==drives,'native universal query graph input')
        label=tag(query,['qtrue','qfalse','empty','mixed'],p['kernel']);value=True if label=='qtrue' else False if label=='qfalse' else None;reason='decided' if value is not None else 'abstain_inconsistent' if label=='empty' else 'abstain_ambiguous' if label=='mixed' else 'abstain_dynamic'
        require(r['final']==dict(tag=label,value=value,reason=reason,binding_sha256=fingerprint(full_binding),T_sha256=fingerprint(dict(packets=t,mode=c['t_mode']))),'T packet/source/native readout binding')
        require(r['value']==value and r['reason']==reason and r['soft_preference_applied_to_hard_state'] is False and r['independent_evidence_added']==0,'unrepaired readout/evidence gate')
        for k in ks:require(all(v==c['initial'] for v in k['initial'].values()),'initial source binding')
    return dict(case=c['key'],arm=arm,mode=c['mode'],T=c['t_mode'],namespace=c['namespace'],order=c['order'],initial=c['initial'],prior=c['prior'],truth=truth,kind=r['kind'],selected_index=r['selected_index'],value=r['value'],reason=r['reason'],
        strict_correct=all(r[k]==truth[k] for k in ['kind','selected_index','value','reason']),value_correct=r['value']==truth['value'],kind_correct=r['kind']==truth['kind'],query_reason_correct=r['reason']==truth['reason'],
        physical_native_calls=len(ks),ticks=sum(k['cost']['kernel_ticks'] for k in ks),groups=sum(k['cost']['group_updates'] for k in ks),links=sum(k['cost']['signal_transmissions'] for k in ks))

def mutations(r,c,packets,p,networks):
    rejected=[]
    for name,change in [('revision',lambda x:x['binding'].update(revision=3)),('source',lambda x:x['binding']['source_refs'].__setitem__(0,'wrong')),('eligibility',lambda x:x['binding']['eligibility'].__setitem__(0,0.5)),('selected',lambda x:x.update(selected_index=9)),('message',lambda x:x['messages'].__setitem__(0,0.5)),('T_hash',lambda x:x['final'].update(T_sha256='wrong')),('value',lambda x:x.update(value=not x['value'])),('network_ref',lambda x:x['network_ids'].__setitem__(2,x['network_ids'][0]))]:
        v=deepcopy(r);change(v)
        try:audit(v,c,packets,p,networks)
        except (ValueError,KeyError):rejected.append(name)
        else:raise ValueError('accepted mutation '+name)
    return rejected

def verify_networks(documents,p):
    networks={};error=0.
    for key,doc in documents.items():
        k=expand_network(doc,p);error=max(error,replay(k,p['kernel'],p['scalar_tolerance']));require(k['cost']['dynamic_groups_created']==len(k['program']['groups']) and k['cost']['dynamic_links_created']==len(k['program']['links']),'native construction counts');networks[key]=k
    return networks,error
