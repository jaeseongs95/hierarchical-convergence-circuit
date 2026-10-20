"""Separate set oracle and full saved-data causal/semantic audit; no native runs."""
from copy import deepcopy
from collections import Counter
from hcr.model import fingerprint
from tools.r32_semantic_join.runtime import require
from tools.r34_feasible_state.verify import tag
from tools.r36_overlap_composition.verify import SavedNetworks

def oracle(alternatives,context,t,closure=False):
    pairs={(f['subject'],f['object']) for f in context}
    if closure:pairs={(x,y) for x in {x for x,y in pairs} for y in {y for x,y in pairs}}
    positive={(f['subject'],f['object']) for f in t};eligible=[(a['X'],a['Y']) in pairs for a in alternatives];ids=[i for i,v in enumerate(eligible) if v];values={xy in positive for xy in pairs}
    value=next(iter(values)) if len(values)==1 else None
    return dict(kind='none' if not ids else 'unique' if len(ids)==1 else 'many',selected_index=ids[0] if len(ids)==1 else None,value=value,reason='abstain_inconsistent' if not ids else 'abstain_ambiguous' if value is None else 'decided',eligible=eligible,feasible=ids)

def audit(r,c,packets,p,networks):
    a=c['alternatives'];C=[packets[k] for k in c['context']];T=[packets[k] for k in c['T']];truth=oracle(a,C,T);closure=oracle(a,C,T,True);arm=r['arm'];require(r['case']==c['key'],'case binding');ks=[]
    scores=dict(role_total=0,role_correct=0,pair_total=0,pair_correct=0,membership_total=0,membership_correct=0,projection_total=0,projection_correct=0)
    if arm=='exact_joint':
        require(r['network_ids']==[] and r['native_calls']==0,'exact native gate')
        require(all(r[k]==truth[k] for k in ['kind','selected_index','value','reason','feasible']),'exact vs separate set oracle')
        observed=truth['eligible'];pre=truth['eligible'];normalized=sorted(c['domains']['X'].index(a[i]['X'])*2+c['domains']['Y'].index(a[i]['Y']) for i,v in enumerate(observed) if v)
    else:
        require(arm in ['native_joint','native_marginal'],'numeric arm');expected_calls=12*(len(C)+len(T))+10+int(arm=='native_marginal');require(len(r['network_ids'])==r['native_calls']==expected_calls,'all physical refs')
        ks=[networks[n] for n in r['network_ids']];cursor=0;gain=p['kernel']['evidence_gain'];codes={x:i for i,x in enumerate(c['vocabulary'])}
        def check(k,name,drives):require(k['program']==p['programs'][name] and k['drives']==drives,'native Program/field/message drives '+name)
        def member(facts):
            nonlocal cursor
            values=[]
            for assignment in a:
                pairs=[]
                for fact in facts:
                    fields=ks[cursor:cursor+2];pair=ks[cursor+2];cursor+=3;expected=[]
                    for k,(variable,field) in zip(fields,[('X','subject'),('Y','object')],strict=True):
                        drives={prefix+str(i):gain*(1 if (codes[token]>>i)&1 else -1) for prefix,token in [('x',assignment[variable]),('y',fact[field])] for i in range(3)};check(k,'role',drives);expected.append(assignment[variable]==fact[field]);scores['role_total']+=1;scores['role_correct']+=k['adopted'] is expected[-1]
                    check(pair,'pair',dict(m0=gain*(2*fields[0]['state']['goal']-1),m1=gain*(2*fields[1]['state']['goal']-1),m2=-gain));scores['pair_total']+=1;scores['pair_correct']+=pair['adopted'] is all(expected);pairs.append(pair['state']['goal'])
                k=ks[cursor];cursor+=1;check(k,'or'+str(len(facts)),{'m'+str(i):gain*(2*v-1) for i,v in enumerate(pairs)});values.append(k['state']['goal']);logical=(assignment['X'],assignment['Y']) in {(f['subject'],f['object']) for f in facts};scores['membership_total']+=1;scores['membership_correct']+=k['adopted'] is logical
            return values
        messages=member(C);require(r['messages']==messages,'C native messages');applied=messages
        if arm=='native_marginal':
            k=ks[cursor];cursor+=1;check(k,'projection'+str(c['order']),{'f'+str(i):gain*(2*v-1) for i,v in enumerate(messages)});applied=[k['state']['e'+str(i)] for i in range(4)]
            bits=[None if abs(2*v-1)<p['kernel']['margin_threshold'] else v>.5 for v in applied];scores['projection_total']=4;scores['projection_correct']=sum(x is y for x,y in zip(bits,closure['eligible'],strict=True))
        require(r['applied']==applied,'projection-only intervention');k=ks[cursor];cursor+=1;check(k,'feasible',dict(**{'e'+str(i):gain*(2*v-1) for i,v in enumerate(applied)},complete=gain))
        b=r['binding'];eligible=[k['state']['e'+str(i)] for i in range(4)];kind=tag(k,['none','unique','many','incomplete'],p['kernel']);hi=(1+p['kernel']['margin_threshold'])/2;lo=(1-p['kernel']['margin_threshold'])/2;ids=[i for i,v in enumerate(eligible) if v>=hi];index=ids[0] if kind=='unique' and len(ids)==1 and all(v<=lo for i,v in enumerate(eligible) if i!=ids[0]) else None
        expected=dict(schema='hcr-r37-joint-tuple-v1',revision=1,variables=['X','Y'],domains=c['domains'],alternatives=a,eligibility=eligible,coverage_activation=k['state']['complete'],kind=kind,selected_index=index,representation=arm,constraint_origin_refs=[f['origin_sha256'] for f in C],state_sha256=fingerprint(k),posterior_is_probability=False,contract='explicit_complete_domains_and_closed_relation_tables')
        require(b==expected and r['kind']==kind and r['selected_index']==index,'tuple source/variables/eligibility/revision/native classification')
        tvalues=member(T);query=ks[cursor];cursor+=1;drives={prefix+str(i):gain*(2*v-1) for prefix,vs in [('e',eligible),('t',tvalues)] for i,v in enumerate(vs)};drives['complete']=gain*(2*b['coverage_activation']-1);check(query,'query',drives);label=tag(query,['qtrue','qfalse','empty','mixed','incomplete'],p['kernel']);value=True if label=='qtrue' else False if label=='qfalse' else None;reason='decided' if value is not None else 'abstain_inconsistent' if label=='empty' else 'abstain_ambiguous' if label=='mixed' else 'abstain_incomplete' if label=='incomplete' else 'abstain_dynamic'
        require(r['final']==dict(tag=label,value=value,reason=reason,binding_sha256=fingerprint(b),T_sha256=fingerprint(T)) and r['value']==value and r['reason']==reason,'independent T causal hash/readout')
        require(cursor==len(ks) and r['independent_evidence_added']==0 and all(all(v==c['initial'] for v in k['initial'].values()) for k in ks),'complete calls/initial/no extra evidence')
        observed=[None if abs(2*v-1)<p['kernel']['margin_threshold'] else v>.5 for v in eligible];pre=[None if abs(2*v-1)<p['kernel']['margin_threshold'] else v>.5 for v in messages];normalized=sorted(c['domains']['X'].index(a[i]['X'])*2+c['domains']['Y'].index(a[i]['Y']) for i,v in enumerate(observed) if v is True)
    intervention=closure if arm=='native_marginal' else truth;fields=['kind','selected_index','value','reason'];first=next((name for name in ['role','pair','membership','projection'] if scores[name+'_total']!=scores[name+'_correct']),None)
    return dict(case=c['key'],arm=arm,c_mask=c['c_mask'],t_mask=c['t_mask'],namespace=c['namespace'],order=c['order'],kind=r['kind'],selected_index=r['selected_index'],value=r['value'],reason=r['reason'],truth=truth,closure=closure,strict_correct=all(r[k]==truth[k] for k in fields),intervention_strict_correct=all(r[k]==intervention[k] for k in fields),tuple_eligibility_correct=sum(x is y for x,y in zip(observed,truth['eligible'],strict=True)),intervention_eligibility_correct=sum(x is y for x,y in zip(observed,intervention['eligible'],strict=True)),tuple_total=4,pre_membership_correct=sum(x is y for x,y in zip(pre,truth['eligible'],strict=True)),eligibility=observed,normalized_eligible=normalized,normalized_selected=None if r['selected_index'] is None else c['domains']['X'].index(a[r['selected_index']]['X'])*2+c['domains']['Y'].index(a[r['selected_index']]['Y']),unnecessary_abstention=truth['value'] is not None and r['value'] is None,incorrect_assertion=r['value'] is not None and r['value'] is not truth['value'],first_failed_intermediate=first,**scores,physical_native_calls=len(ks),ticks=sum(k['cost']['kernel_ticks'] for k in ks),groups=sum(k['cost']['group_updates'] for k in ks),links=sum(k['cost']['signal_transmissions'] for k in ks))

def mutations(r,c,packets,p,networks):
    rejected=[]
    for name,change in [('revision',lambda x:x['binding'].update(revision=2)),('source',lambda x:x['binding']['constraint_origin_refs'].__setitem__(0,'wrong')),('variables',lambda x:x['binding'].update(variables=['Y','X'])),('tuple',lambda x:x['binding']['alternatives'][0].update(Y='wrong')),('eligibility',lambda x:x['binding']['eligibility'].__setitem__(0,.5)),('messages',lambda x:x['messages'].__setitem__(0,.5)),('applied',lambda x:x['applied'].__setitem__(0,.5)),('state_hash',lambda x:x['binding'].update(state_sha256='wrong')),('T_hash',lambda x:x['final'].update(T_sha256='wrong')),('value',lambda x:x.update(value=not x['value'])),('selected',lambda x:x.update(selected_index=99)),('network_ref',lambda x:x['network_ids'].__setitem__(0,x['network_ids'][-1]))]:
        bad=deepcopy(r);change(bad)
        try:audit(bad,c,packets,p,networks)
        except (ValueError,KeyError):rejected.append(name)
        else:raise ValueError('accepted mutation '+name)
    return rejected

def summarize(rows):
    arms=sorted({r['arm'] for r in rows});counts={}
    sums=['strict_correct','intervention_strict_correct','tuple_eligibility_correct','intervention_eligibility_correct','tuple_total','pre_membership_correct','unnecessary_abstention','incorrect_assertion','role_total','role_correct','pair_total','pair_correct','membership_total','membership_correct','projection_total','projection_correct','physical_native_calls','ticks','groups','links']
    for arm in arms:
        rr=[r for r in rows if r['arm']==arm];counts[arm]=dict(cases=len(rr),**{k:sum(r[k] for r in rr) for k in sums},kinds=dict(Counter(str(r['kind']) for r in rr)),reasons=dict(Counter(r['reason'] for r in rr)),first_failed_intermediates=dict(Counter(str(r['first_failed_intermediate']) for r in rr)))
    base={(r['arm'],r['c_mask'],r['t_mask']):r for r in rows if r['namespace']==r['order']==0};meta={}
    for arm in arms:
        rr=[r for r in rows if r['arm']==arm and (r['namespace'] or r['order'])];meta[arm]=dict(pairs=len(rr),invariant=sum(all(r[k]==base[(arm,r['c_mask'],r['t_mask'])][k] for k in ['kind','normalized_selected','value','reason','normalized_eligible']) for r in rr))
    signatures={arm:len({tuple(base[(arm,cm,0)]['normalized_eligible']) for cm in range(16)}) for arm in arms}
    paired=[r for r in rows if r['c_mask'] in [6,9] and r['t_mask'] in [6,9]]
    return dict(counts=counts,metamorphic=meta,distinct_joint_signatures=signatures,same_marginals_counterexamples={arm:[{k:r[k] for k in ['case','c_mask','t_mask','namespace','order','normalized_eligible','value','reason','strict_correct']} for r in paired if r['arm']==arm] for arm in arms})
