"""Independent full triple/set oracle and saved native causal replay checks."""
from copy import deepcopy
from collections import Counter
from hcr.model import fingerprint
from tools.r32_semantic_join.runtime import require
from tools.r34_feasible_state.verify import tag
from tools.r36_overlap_composition.verify import SavedNetworks

def oracle(domains,relations,order,split=False):
    R={(f['subject'],f['object']) for f in relations['R']};S={(f['subject'],f['object']) for f in relations['S']};U={(f['subject'],f['object']) for f in relations['U']}
    triples={(x,y,z) for x in domains['X'] for y in domains['Y'] for z in domains['Z'] if (x,y) in R and (y,z) in S and (x,z) in U}
    projected={(x,y) for x,y,z in triples}
    if split:projected={(x,y) for x,y in R if y in {a for a,b in S} and x in {a for a,b in U}}
    xy=[(x,y) for x in domains['X'] for y in domains['Y']][::1 if not order else -1];eligible=[p in projected for p in xy];ids=[i for i,v in enumerate(eligible) if v]
    return dict(eligible=eligible,kind='none' if not ids else 'unique' if len(ids)==1 else 'many',selected_index=ids[0] if len(ids)==1 else None,consistent=bool(ids),triples=sorted(triples))

def audit(r,c,packets,p,networks):
    d=c['domains'];order=c['order'];a=[(x,y) for x in d['X'] for y in d['Y']][::1 if not order else -1];relations={n:[packets[k] for k in keys] for n,keys in c['relations'].items()};truth=oracle(d,relations,order);relaxed=oracle(d,relations,order,True);arm=r['arm'];scores={n+'_'+s:0 for n in ['role','pair','membership','composition'] for s in ['total','correct']};ks=[]
    def bits(vs):return [None if abs(2*v-1)<p['kernel']['margin_threshold'] else v>.5 for v in vs]
    if arm=='exact_joint':
        require(not r['network_ids'] and r['native_calls']==0,'exact native zero')
        require(all(r[k]==truth[k] for k in ['eligible','kind','selected_index','consistent']) and sorted(map(tuple,r['triples']))==truth['triples'],'exact full triple oracle');observed=truth['eligible']
    else:
        require(arm in ['native_shared','native_split'],'numeric arm');expected_calls=12*sum(map(len,relations.values()))+12+(17 if arm=='native_shared' else 13);require(len(r['network_ids'])==r['native_calls']==expected_calls,'all physical references');ks=[networks[n] for n in r['network_ids']];cursor=0;gain=p['kernel']['evidence_gain'];codes={x:i for i,x in enumerate(c['vocabulary'])}
        def check(k,name,drives):require(k['program']==p['programs'][name] and k['drives']==drives,'native Program/drives '+name)
        messages={}
        for name,axes in [('R',('X','Y')),('S',('Y','Z')),('U',('X','Z'))]:
            values=[];facts=relations[name];assignments=[(x,y) for x in d[axes[0]] for y in d[axes[1]]][::1 if not order else -1]
            for assignment in assignments:
                matches=[]
                for fact in facts:
                    fields=ks[cursor:cursor+2];pair=ks[cursor+2];cursor+=3;expected=[]
                    for k,token,field in zip(fields,assignment,['subject','object'],strict=True):
                        drives={prefix+str(i):gain*(1 if (codes[t]>>i)&1 else -1) for prefix,t in [('x',token),('y',fact[field])] for i in range(3)};check(k,'role',drives);expected.append(token==fact[field]);scores['role_total']+=1;scores['role_correct']+=k['adopted'] is expected[-1]
                    check(pair,'pair',dict(m0=gain*(2*fields[0]['state']['goal']-1),m1=gain*(2*fields[1]['state']['goal']-1),m2=-gain));matches.append(pair['state']['goal']);scores['pair_total']+=1;scores['pair_correct']+=pair['adopted'] is all(expected)
                k=ks[cursor];cursor+=1;check(k,'or'+str(len(facts)),{'m'+str(i):gain*(2*v-1) for i,v in enumerate(matches)});values.append(k['state']['goal']);scores['membership_total']+=1;scores['membership_correct']+=k['adopted'] is (assignment in {(f['subject'],f['object']) for f in facts})
            messages[name]=values
        require(r['messages']==messages,'relation messages');ij=[(i,j) for i in range(2) for j in range(2)][::1 if not order else -1];position={xy:i for i,xy in enumerate(ij)}
        logical={name:[(x,y) in {(f['subject'],f['object']) for f in facts} for x in d[axes[0]] for y in d[axes[1]]][::1 if not order else -1] for name,axes in [('R',('X','Y')),('S',('Y','Z')),('U',('X','Z'))] for facts in [relations[name]]}
        def gate(name,values,expected):
            nonlocal cursor
            k=ks[cursor];cursor+=1;drives={'m'+str(i):gain*(2*v-1) for i,v in enumerate(values)}
            if name=='pair':drives['m2']=-gain
            check(k,name,drives);scores['composition_total']+=1;scores['composition_correct']+=k['adopted'] is expected;return k['state']['goal']
        applied=[]
        if arm=='native_shared':
            witnesses=[];joins=[]
            for x,y in ij:
                expected=[logical['S'][position[y,z]] and logical['U'][position[x,z]] for z in range(2)]
                zz=[gate('pair',[messages['S'][position[y,z]],messages['U'][position[x,z]]],expected[z]) for z in range(2)];union=gate('or2',zz,any(expected));witnesses.append(zz);joins.append(union);applied.append(gate('pair',[messages['R'][position[x,y]],union],logical['R'][position[x,y]] and any(expected)))
            intermediate=dict(shared_witnesses=witnesses,existential_join=joins)
        else:
            sl=[any(logical['S'][position[y,z]] for z in range(2)) for y in range(2)];ul=[any(logical['U'][position[x,z]] for z in range(2)) for x in range(2)]
            sy=[gate('or2',[messages['S'][position[y,z]] for z in range(2)],sl[y]) for y in range(2)];ux=[gate('or2',[messages['U'][position[x,z]] for z in range(2)],ul[x]) for x in range(2)];joins=[]
            for x,y in ij:
                v=gate('pair',[sy[y],ux[x]],sl[y] and ul[x]);joins.append(v);applied.append(gate('pair',[messages['R'][position[x,y]],v],logical['R'][position[x,y]] and sl[y] and ul[x]))
            intermediate=dict(independent_S=sy,independent_U=ux,independent_join=joins)
        require(r['intermediate']==intermediate and r['applied']==applied,'same-witness causal intermediates');k=ks[cursor];cursor+=1;check(k,'feasible',dict(**{'e'+str(i):gain*(2*v-1) for i,v in enumerate(applied)},complete=gain));eligible=[k['state']['e'+str(i)] for i in range(4)];kind=tag(k,['none','unique','many','incomplete'],p['kernel']);hi=(1+p['kernel']['margin_threshold'])/2;lo=(1-p['kernel']['margin_threshold'])/2;ids=[i for i,v in enumerate(eligible) if v>=hi];index=ids[0] if kind=='unique' and len(ids)==1 and all(v<=lo for i,v in enumerate(eligible) if i!=ids[0]) else None
        expected=dict(schema='hcr-r38-shared-witness-v1',revision=1,variables=['X','Y','Z'],projected_variables=['X','Y'],domains=d,alternatives=[dict(X=x,Y=y) for x,y in a],eligibility=eligible,kind=kind,selected_index=index,coverage_activation=k['state']['complete'],shared_witness=arm=='native_shared',source_refs={n:[f['origin_sha256'] for f in fs] for n,fs in relations.items()},state_sha256=fingerprint(k),posterior_is_probability=False,contract='explicit_complete_domains_and_closed_relation_tables')
        require(r['binding']==expected and r['kind']==kind and r['selected_index']==index and r['consistent']==(True if kind in ['unique','many'] else False if kind=='none' else None),'bound packet/native readout');require(cursor==len(ks) and r['independent_evidence_added']==0 and all(all(v==c['initial'] for v in k['initial'].values()) for k in ks),'call/initial/extra evidence');observed=bits(eligible)
    full=all(r[k]==truth[k] for k in ['kind','selected_index','consistent']) and observed==truth['eligible'];intervention=relaxed if arm=='native_split' else truth;norm=sorted(d['X'].index(a[i][0])*2+d['Y'].index(a[i][1]) for i,v in enumerate(observed) if v is True)
    return dict(case=c['key'],arm=arm,r_mask=c['r_mask'],s_mask=c['s_mask'],u_mask=c['u_mask'],namespace=c['namespace'],order=order,kind=r['kind'],consistent=r['consistent'],normalized_selected=None if r['selected_index'] is None else d['X'].index(a[r['selected_index']][0])*2+d['Y'].index(a[r['selected_index']][1]),normalized_eligible=norm,strict_correct=full,intervention_strict_correct=all(r[k]==intervention[k] for k in ['kind','selected_index','consistent']) and observed==intervention['eligible'],eligibility_correct=sum(x is y for x,y in zip(observed,truth['eligible'],strict=True)),intervention_eligibility_correct=sum(x is y for x,y in zip(observed,intervention['eligible'],strict=True)),tuple_total=4,false_consistency=r['consistent'] is True and not truth['consistent'],false_inconsistency=r['consistent'] is False and truth['consistent'],truth=truth,relaxed=relaxed,first_failed_intermediate=next((n for n in ['role','pair','membership','composition'] if scores[n+'_total']!=scores[n+'_correct']),None),**scores,physical_native_calls=len(ks),ticks=sum(k['cost']['kernel_ticks'] for k in ks),groups=sum(k['cost']['group_updates'] for k in ks),links=sum(k['cost']['signal_transmissions'] for k in ks))

def mutations(r,c,packets,p,networks):
    changes=[('revision',lambda x:x['binding'].update(revision=2)),('shared_witness',lambda x:x['binding'].update(shared_witness=False)),('source',lambda x:x['binding']['source_refs']['R'].__setitem__(0,'wrong')),('variables',lambda x:x['binding'].update(variables=['Z','Y','X'])),('eligibility',lambda x:x['binding']['eligibility'].__setitem__(0,.5)),('S_message',lambda x:x['messages']['S'].__setitem__(0,.5)),('witness',lambda x:x['intermediate']['shared_witnesses'][0].__setitem__(0,.5)),('applied',lambda x:x['applied'].__setitem__(0,.5)),('state_hash',lambda x:x['binding'].update(state_sha256='wrong')),('consistent',lambda x:x.update(consistent=not x['consistent'])),('selected',lambda x:x.update(selected_index=99)),('network_ref',lambda x:x['network_ids'].__setitem__(0,x['network_ids'][-1]))];rejected=[]
    for name,change in changes:
        bad=deepcopy(r);change(bad)
        try:audit(bad,c,packets,p,networks)
        except (ValueError,KeyError):rejected.append(name)
        else:raise ValueError('accepted mutation '+name)
    return rejected

def summarize(rows):
    arms=sorted({r['arm'] for r in rows});sums=['strict_correct','intervention_strict_correct','eligibility_correct','intervention_eligibility_correct','tuple_total','false_consistency','false_inconsistency','role_total','role_correct','pair_total','pair_correct','membership_total','membership_correct','composition_total','composition_correct','physical_native_calls','ticks','groups','links'];counts={a:dict(cases=len(rr),**{k:sum(r[k] for r in rr) for k in sums},kinds=dict(Counter(str(r['kind']) for r in rr)),first_failed_intermediates=dict(Counter(str(r['first_failed_intermediate']) for r in rr))) for a in arms for rr in [[r for r in rows if r['arm']==a]]}
    base={(r['arm'],r['r_mask'],r['s_mask'],r['u_mask']):r for r in rows if r['namespace']==r['order']==0};meta={}
    for arm in arms:
        rr=[r for r in rows if r['arm']==arm and (r['namespace'] or r['order'])];meta[arm]=dict(pairs=len(rr),invariant=sum(all(r[k]==base[(arm,r['r_mask'],r['s_mask'],r['u_mask'])][k] for k in ['kind','consistent','normalized_selected','normalized_eligible']) for r in rr))
    examples=[{k:r[k] for k in ['case','arm','r_mask','s_mask','u_mask','namespace','order','kind','consistent','truth','relaxed','normalized_eligible','strict_correct']} for r in rows if r['r_mask']==r['s_mask']==9 and r['u_mask'] in [6,9]]
    return dict(counts=counts,metamorphic=meta,cycle_counterexamples=examples)
