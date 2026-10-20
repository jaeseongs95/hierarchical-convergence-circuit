"""Saved-data role/grammar/packet audit and separately set-based semantic oracle."""
from copy import deepcopy
from hcr.model import fingerprint
from tools.r32_semantic_join.runtime import require
from tools.r34_feasible_state.verify import verify_networks,tag

def oracle(candidates,context,c_tree,t,t_tree,complete):
    universe=set(range(len(candidates)))
    def evaluate(tree,facts):
        if type(tree) is int:return {i for i,c in enumerate(candidates) if c['object']==facts[tree]['subject']}
        op=tree[0];a=evaluate(tree[1],facts)
        if op=='not':return universe-a
        b=evaluate(tree[2],facts);return a&b if op=='and' else a|b
    feasible=evaluate(c_tree,context);positive=evaluate(t_tree,t);answers={i in positive for i in feasible}
    kind='incomplete' if not complete else 'none' if not feasible else 'unique' if len(feasible)==1 else 'many'
    value=next(iter(answers)) if complete and len(answers)==1 else None
    reason='abstain_incomplete' if not complete else 'abstain_inconsistent' if not feasible else 'abstain_ambiguous' if len(answers)>1 else 'decided'
    return dict(kind=kind,selected_index=next(iter(feasible)) if complete and len(feasible)==1 else None,value=value,reason=reason,feasible=sorted(feasible))

def audit(r,c,packets,p,networks):
    candidates=[packets[k] for k in c['candidates']];context=[packets[k] for k in c['context']];t=[packets[k] for k in c['T']];n=len(candidates)
    truth=oracle(candidates,context,p['expressions'][c['c_expr']],t,p['expressions'][c['t_expr']],c['complete']);require(r['case']==c['key'],'case binding');arm=r['arm']
    if arm=='exact':
        require(all(r[k]==v for k,v in truth.items()),'exact independent set oracle');require(r['native_calls']==0 and r['network_ids']==[],'exact native bypass');ks=[]
    else:
        require(arm=='native' and r['native_calls']==len(r['network_ids'])==8*n+2,'physical call count');ks=[networks[k] for k in r['network_ids']];class_k=ks[4*n];query_k=ks[-1];gain=p['kernel']['evidence_gain'];code={token:i for i,token in enumerate(c['vocabulary'])}
        def validate_stage(segment,facts,expr):
            values=[]
            for i,candidate in enumerate(candidates):
                block=segment[4*i:4*i+4]
                for fact,k in zip(facts,block[:3],strict=True):
                    drives={prefix+str(bit):gain*(1 if (code[token]>>bit)&1 else -1) for prefix,token in [('x',candidate['object']),('y',fact['subject'])] for bit in range(3)}
                    require(k['program']==p['programs']['role'] and k['drives']==drives,'native 3bit per-field role match')
                k=block[3];require(k['program']==p['programs']['expr'+str(expr)] and k['drives']=={'m'+str(j):gain*(2*x['state']['goal']-1) for j,x in enumerate(block[:3])},'syntax-only constraint composition');values.append(k['state']['goal'])
            return values
        messages=validate_stage(ks[:4*n],context,c['c_expr']);require(r['messages']==messages,'all C messages preserved')
        drives={'e'+str(i):gain*(2*v-1) for i,v in enumerate(messages)};drives['complete']=gain*(1 if c['complete'] else -1)
        require(class_k['program']==p['programs']['feasible'+str(n)] and class_k['drives']==drives,'count-only classifier and external coverage input')
        kind=tag(class_k,['none','unique','many','incomplete'],p['kernel']);eligibility=[class_k['state']['e'+str(i)] for i in range(n)]
        positives=[i for i,v in enumerate(eligibility) if 2*v-1>=p['kernel']['margin_threshold']];index=None
        if kind=='unique' and len(positives)==1 and all(1-2*v>=p['kernel']['margin_threshold'] for i,v in enumerate(eligibility) if i!=positives[0]):index=positives[0]
        b=r['binding'];expected=dict(schema='hcr-r35-compositional-slot-v1',revision=1,alternative_keys=c['candidates'],eligibility=eligibility,coverage_activation=class_k['state']['complete'],kind=kind,selected_index=index,source_refs=[x['origin_sha256'] for x in candidates],state_sha256=fingerprint(class_k),posterior_is_probability=False)
        require(b==expected and r['kind']==kind and r['selected_index']==index,'native class/source/order/revision binding')
        full_binding=dict(b);del full_binding['alternative_keys'];full_binding['alternatives']=candidates
        values=validate_stage(ks[4*n+1:-1],t,c['t_expr'])
        drives={prefix+str(i):gain*(2*v-1) for prefix,vs in [('e',eligibility),('t',values)] for i,v in enumerate(vs)};drives['complete']=gain*(2*b['coverage_activation']-1)
        require(query_k['program']==p['programs']['query'+str(n)] and query_k['drives']==drives,'packet-only independent T query')
        label=tag(query_k,['qtrue','qfalse','empty','mixed','incomplete'],p['kernel']);value=True if label=='qtrue' else False if label=='qfalse' else None
        reason='decided' if value is not None else 'abstain_inconsistent' if label=='empty' else 'abstain_ambiguous' if label=='mixed' else 'abstain_incomplete' if label=='incomplete' else 'abstain_dynamic'
        require(r['final']==dict(tag=label,value=value,reason=reason,binding_sha256=fingerprint(full_binding),T_sha256=fingerprint(dict(packets=t,expression=p['expressions'][c['t_expr']]))),'final source/AST/packet/native decoder binding')
        require(r['value']==value and r['reason']==reason and r['independent_evidence_added']==0,'unrepaired native result')
        require(all(all(v==c['initial'] for v in k['initial'].values()) for k in ks),'initial fixed binding')
    return dict(case=c['key'],arm=arm,n=n,base_n=c['base_n'],complete=c['complete'],c_expr=c['c_expr'],t_expr=c['t_expr'],namespace=c['namespace'],order=c['order'],kind=r['kind'],value=r['value'],reason=r['reason'],selected_index=r['selected_index'],truth=truth,strict_correct=all(r[k]==truth[k] for k in ['kind','selected_index','value','reason']),value_correct=r['value']==truth['value'],kind_correct=r['kind']==truth['kind'],reason_correct=r['reason']==truth['reason'],physical_native_calls=len(ks),ticks=sum(k['cost']['kernel_ticks'] for k in ks),groups=sum(k['cost']['group_updates'] for k in ks),links=sum(k['cost']['signal_transmissions'] for k in ks))

def mutations(r,c,packets,p,networks):
    rejected=[]
    changes=[('revision',lambda x:x['binding'].update(revision=7)),('origin',lambda x:x['binding']['source_refs'].__setitem__(0,'wrong')),('eligibility',lambda x:x['binding']['eligibility'].__setitem__(0,.5)),('coverage',lambda x:x['binding'].update(coverage_activation=.5)),('selected',lambda x:x.update(selected_index=9)),('C_message',lambda x:x['messages'].__setitem__(0,.5)),('T_hash',lambda x:x['final'].update(T_sha256='wrong')),('value',lambda x:x.update(value=not x['value'])),('network_ref',lambda x:x['network_ids'].__setitem__(0,x['network_ids'][-1])),('alternative_role',lambda x:x['binding']['alternative_keys'].__setitem__(0,c['context'][0]))]
    for name,change in changes:
        altered=deepcopy(r);change(altered)
        try:audit(altered,c,packets,p,networks)
        except (ValueError,KeyError):rejected.append(name)
        else:raise ValueError('accepted semantic mutation '+name)
    return rejected
