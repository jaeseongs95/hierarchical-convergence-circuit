"""Saved-data verifier: scalar native replay and independent feasible-set semantics."""
from copy import deepcopy
from math import exp,isclose
from hcr.model import fingerprint
from tools.r32_semantic_join.runtime import require,export

def replay(k,cfg,tol):
    p=k['program'];require(fingerprint(p)==k['program_sha256'],'program digest');state=dict(k['initial']);history=[];stable=0;error=0.;stop=None
    require(set(state)=={g['id'] for g in p['groups']},'initial identity')
    for i,row in enumerate(k['ticks'],1):
        drive={g['id']:g['bias']+k['drives'].get(g['id'],0.) for g in p['groups']}
        for e in p['links']:drive[e['target']]+=e['weight']*(2*state[e['source']]-1)
        nxt={}
        for g in p['groups']:
            key=g['id'];v=state[key];d=drive[key];z=((d+cfg['self_excitation']*v-cfg['inhibition']*(1-v))-(-d+cfg['self_excitation']*(1-v)-cfg['inhibition']*v))/cfg['temperature'];sig=1/(1+exp(-z)) if z>=0 else exp(z)/(1+exp(z));nxt[key]=(1-cfg['damping'])*v+cfg['damping']*sig
        residual=max(abs(nxt[k]-state[k]) for k in state);stable=stable+1 if residual<=cfg['residual_tolerance'] else 0
        require(row['tick']==i and row['stable_steps']==stable and set(row['state'])==set(nxt),'tick controller')
        for key in nxt:error=max(error,abs(nxt[key]-row['state'][key]));require(isclose(nxt[key],row['state'][key],rel_tol=0,abs_tol=tol),'scalar tick state')
        error=max(error,abs(residual-row['residual']));require(isclose(residual,row['residual'],rel_tol=0,abs_tol=tol),'scalar residual')
        margin=abs(2*nxt['goal']-1)
        if stable>=cfg['patience']:stop='stable_decision' if margin>=cfg['margin_threshold'] else 'stable_ambiguous'
        elif len(history)>=1 and residual>cfg['residual_tolerance']*10 and max(abs(nxt[k]-history[-1][k]) for k in nxt)<cfg['residual_tolerance']:stop='oscillating'
        if stop:require(i==len(k['ticks']),'continued after stop');state=nxt;break
        history.append(state);history=history[-3:];state=nxt
    if stop is None:require(len(k['ticks'])==cfg['max_ticks'],'early stop');stop='budget_exhausted'
    c=k['convergence'];require(c['status']==stop and c['ticks']==i and c['stable_steps']==stable,'convergence controller')
    for key in state:require(isclose(state[key],k['state'][key],rel_tol=0,abs_tol=tol),'final state')
    require(isclose(c['margin'],margin,rel_tol=0,abs_tol=tol) and isclose(c['residual'],residual,rel_tol=0,abs_tol=tol),'final residual/margin')
    adopted=state['goal']>=.5 if stop=='stable_decision' else None;require(k['adopted']==adopted,'native adoption')
    cost=k['cost'];require(cost['kernel_ticks']==i and cost['group_updates']==i*len(p['groups']) and cost['normalization_ops']==i*len(p['groups']) and cost['signal_transmissions']==i*len(p['links']),'native counts')
    return error

def oracle(candidates,context,mode,t):
    # Enumerate complete alternatives independently from runtime exact() implementation.
    a={i for i,c in enumerate(candidates) if c['object']==context[0]['subject']};b={i for i,c in enumerate(candidates) if c['object']==context[1]['subject']}
    feasible=a if mode=='one0' else b if mode=='one1' else a|b if mode=='either' else a&b
    values={candidates[i]['object']==t['subject'] for i in feasible};selected=next(iter(feasible)) if len(feasible)==1 else None
    value=next(iter(values)) if len(values)==1 else None
    return dict(feasible=sorted(feasible),selected_index=selected,value=value,reason='abstain_inconsistent' if not feasible else 'abstain_ambiguous' if len(values)>1 else 'decided')

def audit(record,c,packets,p):
    from tools.r33_typed_feedback.runtime import promote
    candidates=[packets[k] for k in c['candidates']];context=[packets[k] for k in c['context']];t=packets[c['t']];truth=oracle(candidates,context,c['mode'],t);arm=record['arm'];err=0.
    require(record['case']==c['key'],'case binding')
    if arm=='exact':
        for k,v in truth.items():require(record[k]==v,'exact semantics '+k)
        require(record['kernels']==[],'exact no native')
        ks=[]
    else:
        first=record['initial_selection'];rev=record['revised_selection'];upper=record['compatibility'];ks=[first,*upper,rev,record['final']['kernel']]
        require(len(upper)==2 and record['native_settles']==5 and record['feedback_is_replacement'] and record['independent_evidence_added']==0,'one bounded replacement pass')
        require(record['initial_packet']==promote(candidates,first,0) and record['packet']==promote(candidates,rev,1),'selection/source/revision binding')
        require(record['selected_index']==record['packet']['selected_index'],'selected index')
        local=c['evidence'][candidates[1]['object']]-c['evidence'][candidates[0]['object']];gain=p['kernel']['evidence_gain'];code={c['vocabulary'][0]:-gain,c['vocabulary'][1]:gain}
        returned=[k['state']['goal'] for k in upper];applied=returned if arm=='full' else [0.,0.]
        require(record['returned']==returned and record['applied']==applied,'message routing/replacement')
        require(first['drives']==dict(local=gain*local,context=0.) and rev['drives']==dict(local=gain*local,context=gain*(applied[1]-applied[0])),'lower drive encoding')
        require(first['program']==p['programs']['selector'] and rev['program']==p['programs']['selector'],'selector program')
        used=[context[0]] if c['mode']=='one0' else [context[1]] if c['mode']=='one1' else context
        for candidate,k in zip(candidates,upper,strict=True):
            drives={'x':code[candidate['object']]};drives.update({'y'+str(i):code[s['subject']] for i,s in enumerate(used)})
            require(k['drives']==drives and k['program']==p['programs']['one' if len(used)==1 else c['mode']],'role-only compatibility encoding')
        packet=record['packet'];selected=packet['selected'];final=record['final'];k=final['kernel']
        require(k['program']==p['programs']['one'] and k['drives']==dict(x=0. if selected is None else code[selected['object']],y0=code[t['subject']]),'separate T input boundary')
        value=None if selected is None else k['adopted'];require(final['value']==value and record['value']==value and record['reason']==('abstain_dynamic' if value is None else 'decided'),'final decoder')
        require(final['binding_sha256']==fingerprint(packet) and final['t_sha256']==fingerprint(t),'final packet binding')
        arg=None if selected is None or value is None else dict(rule='typed_join' if value else 'typed_join_counterexample',role_terms=[selected['object'],t['subject']],source_refs=[selected['origin_sha256'],t['origin_sha256']])
        require(final['argument']==arg,'final argument source/roles')
        for k in ks:require(all(v==c['initial'] for v in k['initial'].values()),'initial binding');err=max(err,replay(k,p['kernel'],p['scalar_tolerance']))
    return dict(case=c['key'],arm=arm,mode=c['mode'],prior=c['prior'],namespace=c['namespace'],order=c['order'],initial=c['initial'],t=c['t'],truth=truth,value=record['value'],reason=record['reason'],selected_index=record['selected_index'],
        query_value_correct=record['value']==truth['value'],strict_correct=all(record[k]==truth[k] for k in ['value','reason','selected_index']),binding_correct=record['selected_index']==truth['selected_index'],
        native_settles=len(ks),ticks=sum(k['cost']['kernel_ticks'] for k in ks),group_updates=sum(k['cost']['group_updates'] for k in ks),signal_transmissions=sum(k['cost']['signal_transmissions'] for k in ks),numeric_replay_max_absolute_error=err,
        original_selected=None if arm=='exact' else record['initial_packet']['selected_index'],revised_selected=record['selected_index'])

def mutants(record,c,packets,p):
    cases=[]
    for name,change in [('selected_role',lambda r:r['packet']['selected'].update(object='forged')),('revision',lambda r:r['packet'].update(revision=4)),('feedback',lambda r:r['applied'].__setitem__(0,r['applied'][0]+.1)),('source',lambda r:r['packet']['source_refs'].__setitem__(0,'forged')),('T_drive',lambda r:r['final']['kernel']['drives'].update(y0=0.)),('value',lambda r:r.update(value=not r['value'])),('kernel_count',lambda r:r['revised_selection']['cost'].update(kernel_ticks=0))]:
        mutant=deepcopy(record);change(mutant)
        try:audit(mutant,c,packets,p)
        except (ValueError,KeyError):cases.append(name)
        else:raise ValueError('mutation accepted '+name)
    return cases
