"""Independent EXP30 auditor: no native or producer import, no corrective writes."""
from math import tanh, isfinite, isclose
from tools.r048_precision import io
TOL=2e-12


def close(a,b):
    if isinstance(a,dict) and isinstance(b,dict):return set(a)==set(b) and all(close(a[k],b[k]) for k in a)
    if isinstance(a,list) and isinstance(b,list):return len(a)==len(b) and all(close(x,y) for x,y in zip(a,b))
    if type(a) in (int,float) and type(b) in (int,float):return isfinite(a) and isfinite(b) and isclose(a,b,rel_tol=TOL,abs_tol=TOL)
    return type(a) is type(b) and a==b


def path_from_observation(ob):
    e=ob['edges'];io.require(len(e)==2,'auditor scope: two public edges')
    paths=[(i,j) for i in range(2) for j in range(2) if i!=j and e[i]['source']==ob['start']
        and e[i]['target']==e[j]['source'] and e[j]['target']==ob['goal']]
    io.require(len(paths)==1,'not a unique length-two chain')
    return list(paths[0])


def verify_program(r):
    c=r['config'];path=path_from_observation(r['observation'])
    g=[dict(id='e:0',level=0,bias=0.0),dict(id='e:1',level=0,bias=0.0),
       dict(id='p:0:0',level=1,bias=0.0),dict(id='p:0:1',level=1,bias=-c['relation_gain']),dict(id='goal',level=1,bias=0.0)]
    dependencies=[(f'e:{path[0]}','p:0:0'),(f'e:{path[1]}','p:0:1'),('p:0:0','p:0:1'),('p:0:1','goal')]
    links=[]
    for source,target in dependencies:
        links.extend([dict(source=source,target=target,weight=c['relation_gain'],kind='support'),
                      dict(source=target,target=source,weight=c['top_down_gain'],kind='top_down')])
    expected=dict(edge_count=2,groups=g,links=links,paths=[path])
    io.require(close(r['program'],expected),'stored graph changed')
    drives={f'e:{i}':c['evidence_gain']*(e['score'] or 0.) for i,e in enumerate(r['observation']['edges'])};drives['goal']=0.0
    io.require(r['raw_drives']==drives,'external drive changed')
    td=r['intervention']['top_down']; active=[i for i,x in enumerate(links) if td or x['kind']=='support']
    io.require(r['active_link_indices']==active,'active-link mask inconsistent with top_down')
    initial={x['id']:(.99 if r['intervention']['initial_mode']=='high' and x['id']!='goal' else .5) for x in g}
    io.require(r['initial_state']==initial and initial['goal']==.5,'initial values/goal')
    sig=io.digest(dict(program=r['program'],config=r['config'],raw_drives=drives,top_down=td,active_link_indices=active))
    io.require(r['effective_program_sha256']==sig,'effective signature missing policy/mask')
    io.require(r['native_cost']['search_edge_checks']==4 and r['native_cost']['dynamic_groups_created']==5
               and r['native_cost']['dynamic_links_created']==8,'native construction counters')


def replay(r):
    p=r['program'];c=r['config'];old=dict(r['initial_state']);history=[];stable=0;stop=None;maxerr=0.
    io.require(bool(r['ticks']),'missing numeric trajectory')
    for t,row in enumerate(r['ticks'],1):
        io.require(stop is None and t<=c['max_ticks'] and row['tick']==t,'tick order/budget/post-stop extension')
        nxt={}
        for g in p['groups']:
            k=g['id']; field=g['bias']+r['raw_drives'].get(k,0.)
            for idx in r['active_link_indices']:
                l=p['links'][idx]
                if l['target']==k:field+=l['weight']*(2*old[l['source']]-1)
            half=(field+.5*(c['self_excitation']+c['inhibition'])*(2*old[k]-1))/c['temperature']
            target=.5+.5*tanh(half)
            nxt[k]=(1-c['damping'])*old[k]+c['damping']*target
        residual=max(abs(nxt[k]-old[k]) for k in old)
        stable=stable+1 if residual<=c['residual_tolerance'] else 0
        io.require(set(row)=={'tick','state','residual','stable_steps'} and close(row['state'],nxt)
            and close(row['residual'],residual) and type(row['stable_steps']) is int and row['stable_steps']==stable,
            'independent scalar replay mismatch at tick '+str(t))
        maxerr=max(maxerr,max(abs(row['state'][k]-nxt[k]) for k in old))
        margin=abs(2*nxt['goal']-1)
        if stable>=c['patience']:stop='stable_decision' if margin>=c['margin_threshold'] else 'stable_ambiguous'
        elif history and residual>10*c['residual_tolerance'] and max(abs(nxt[k]-history[-1][k]) for k in nxt)<c['residual_tolerance']:stop='oscillating'
        elif t==c['max_ticks']:stop='budget_exhausted'
        history=(history+[old])[-3:];old=nxt
    io.require(stop is not None,'trajectory stops without a native termination condition')
    io.require(close(r['convergence'],dict(status=stop,ticks=t,residual=residual,margin=margin,stable_steps=stable))
        and close(r['final_state'],nxt),'terminal state/convergence')
    value=nxt['goal']>=.5 if stop=='stable_decision' else None
    io.require(r['raw_value'] is value and r['censored'] is (stop=='budget_exhausted'),'raw or censored flag')
    for k,v in dict(kernel_ticks=t,group_updates=t*5,normalization_ops=t*5,signal_transmissions=t*len(r['active_link_indices'])).items():
        io.require(r['native_cost'][k]==v,'native count: '+k)
    return maxerr


def verify_proof(r):
    pr=r['proof'];ob=r['observation'];value=r['raw_value'];state=r['final_state'];path=path_from_observation(ob)
    io.require(set(pr)=={'nodes','final','primitive_depth','assumed_edges','under_assumptions_valid','paths'},'proof schema')
    slots={e['id']:i for i,e in enumerate(ob['edges'])};edges={e['id']:e for e in ob['edges']}
    neg=[i for i in path if state[f'e:{i}']<.5]
    can_build=(value is True and not neg) or (value is False and bool(neg))
    if not can_build:
        io.require(pr['nodes']==[] and pr['final'] is None and pr['primitive_depth'] is None
                   and pr['assumed_edges']==[] and pr['under_assumptions_valid'] is False,'unjustified proof or suppressed native failure')
        expected_paths=[] if value is None else [[ob['edges'][i]['id'] for i in path]]
        io.require(pr['paths']==expected_paths,'empty proof path registry')
        depth=None
    else:
        io.require(pr['under_assumptions_valid'] is True,'valid proof suppressed')
        table={x['id']:x for x in pr['nodes']};io.require(len(table)==len(pr['nodes']),'duplicate proof identity')
        terms={};depths={};visiting=set();assumed={}
        for n in pr['nodes']:
            io.require(set(n)=={'id','rule','edge_id','parents','path_index'} and isinstance(n['parents'],list),'node schema')
        def visit(key):
            io.require(key in table and key not in visiting,'dangling parent/cycle')
            if key in terms:return terms[key]
            visiting.add(key);n=table[key];ps=[visit(k) for k in n['parents']];rule=n['rule']
            d=0 if not ps else 1+max(depths[k] for k in n['parents'])
            if rule in ('assumed_open','assumed_closed'):
                eid=n['edge_id'];io.require(not ps and eid in edges and n['path_index'] is None,'fact rule')
                truth=rule=='assumed_open';io.require((state[f'e:{slots[eid]}']>=.5) is truth,'fact not supported by internal state')
                assumed[eid]=truth;e=edges[eid];term=('edge',e['source'],e['target'],truth,eid)
            else:
                io.require(n['edge_id'] is None,'inference has an edge id')
                if rule=='start_edge':
                    io.require(n['path_index']==0 and len(ps)==1 and ps[0][0]=='edge' and ps[0][3] is True and ps[0][1]==ob['start'],'start binding')
                    term=('reachable',ps[0][1],ps[0][2])
                elif rule=='extend_path':
                    io.require(n['path_index']==0 and len(ps)==2 and ps[0][0]=='reachable' and ps[1][0]=='edge'
                        and ps[1][3] is True and ps[0][2]==ps[1][1],'parent composition')
                    term=('reachable',ps[0][1],ps[1][2])
                elif rule=='path_blocked':
                    io.require(n['path_index']==0 and len(ps)==1 and ps[0][0]=='edge' and ps[0][3] is False,'blocked rule')
                    chosen=min(neg,key=lambda i:(state[f'e:{i}'],i))
                    io.require(ps[0][4]==ob['edges'][chosen]['id'],'native proof selection altered')
                    term=('blocked',0)
                elif rule=='all_paths_blocked':
                    io.require(n['path_index'] is None and ps==[('blocked',0)],'negative completeness')
                    term=('unreachable',ob['start'],ob['goal'])
                else:raise io.ContractError('unknown proof rule')
            visiting.remove(key);terms[key]=term;depths[key]=d;return term
        final=visit(pr['final'])
        io.require(final==('reachable' if value else 'unreachable',ob['start'],ob['goal']) and len(terms)==len(table),'final proof semantics/unreferenced nodes')
        depth=depths[pr['final']]
        io.require(pr['primitive_depth']==depth and pr['paths']==[[ob['edges'][i]['id'] for i in path]],'proof depth/paths')
        io.require(pr['assumed_edges']==sorted([[k,v] for k,v in assumed.items()]),'assumptions registry')
        io.require(len(pr['nodes'])==(4 if value else 3),'unexpected proof work')
    checks=[];accepted=can_build
    if accepted:
        for eid,truth in pr['assumed_edges']:
            s=edges[eid]['score'];ok=s is not None and s!=0 and (s>0) is truth
            checks.append(dict(edge_id=eid,assumed=truth,observation_score=s,supported=ok))
            if not ok:accepted=False;break
    io.require(r['support_checks']==checks and r['accepted'] is bool(accepted),'support/adoption')
    io.require(r['adapter_cost']==dict(initial_assignments=5,support_checks=len(checks)),'adapter cost')
    io.require(r['native_cost']['proof_nodes_reconstructed']==len(pr['nodes']),'native proof count')
    expected='kernel_budget' if r['censored'] else 'adopted_supported' if accepted else 'unsupported_or_unsettled'
    io.require(r['termination']==expected,'terminal reason')
    return depth


def verify_events(r):
    expected=[]
    def e(name,payload):expected.append(dict(ordinal=len(expected),event=name,payload=payload))
    e('begin',dict(observation_sha256=io.digest(r['observation']),config_sha256=io.digest(r['config']),arm=r['arm'],intervention=r['intervention']))
    e('network',{k:r[k] for k in ('program','raw_drives','active_link_indices','effective_program_sha256','initial_state')})
    first=None
    for row in r['ticks']:
        e('tick',row);goal=row['state']['goal'];margin=abs(2*goal-1)
        if first is None and margin>=r['config']['margin_threshold']:
            first=dict(tick=row['tick'],value=goal>=.5,goal=goal,margin=margin,adopted=False);e('first_margin_readout',first)
    e('terminal_raw',dict(state=r['final_state'],convergence=r['convergence'],value=r['raw_value']))
    e('proof_constructed',dict(proof=r['proof']));e('support_checked',dict(checks=r['support_checks']))
    e('adoption',dict(value=r['raw_value'],accepted=r['accepted'],reason=r['termination']))
    io.require(r['events']==expected and r['first_margin_readout']==first,'event/readout boundary inconsistency')
    if first is not None:io.require(r['first_margin_readout']['adopted'] is False,'provisional adoption flag type')


def audit_record(r, world=None):
    fields={'schema','observation','config','arm','intervention','prior_state_imported','initial_stable_steps',
        'energy_joules','peak_memory_bytes','native_adaptive_expansions','program','raw_drives','active_link_indices',
        'effective_program_sha256','initial_state','first_margin_readout','ticks','convergence','final_state','raw_value',
        'proof','support_checks','accepted','censored','termination','native_cost','adapter_cost','events','wall_seconds'}
    io.require(set(r)==fields and r['schema']=='hcr-exp30-query-v1','record schema')
    io.require(r['arm'] in ('on_neutral','off_neutral','on_high','off_high'),'arm')
    td,init=r['arm'].split('_')
    io.require(type(r['intervention'].get('top_down')) is bool and r['intervention'].get('reuse_applied') is False
        and r['intervention'].get('learning_applied') is False,'intervention flag types')
    io.require(r['intervention']==dict(top_down=td=='on',initial_mode=init,high_value=.99,new_goal_initial=.5,
        initialization_origin='experimental_assignment_NOT_carry',reuse_applied=False,learning_applied=False),'policy/schema')
    io.require(r['prior_state_imported'] is False and type(r['initial_stable_steps']) is int and r['initial_stable_steps']==0,'history transfer')
    io.require(all(r[k] is None for k in ('energy_joules','peak_memory_bytes','native_adaptive_expansions')),'unmeasured values')
    io.require(type(r['wall_seconds']) in (int,float) and isfinite(r['wall_seconds']) and r['wall_seconds']>=0,'wall time')
    io.require(type(r['accepted']) is bool and type(r['censored']) is bool,'flag types')
    native_fields={'search_edge_checks','dynamic_groups_created','dynamic_links_created','binding_checks','recall_checks',
        'circuit_groups_instantiated','kernel_ticks','group_updates','signal_transmissions','normalization_ops',
        'proof_nodes_reconstructed','compilation_items','memory_write_items','observation_requests','verification_checks','wall_seconds'}
    n=r['native_cost'];io.require(set(n)==native_fields and n['wall_seconds'] is None,'native cost schema')
    io.require(all(type(v) is int and v>=0 for k,v in n.items() if k!='wall_seconds'),'cost type/range')
    for k in ('binding_checks','recall_checks','circuit_groups_instantiated','compilation_items','memory_write_items','observation_requests','verification_checks'):
        io.require(n[k]==0,'unexpected native operation: '+k)
    if r['program'] is None:
        # Fixed two-edge shape. Counter-check the small structural budget without native code.
        path_from_observation(r['observation']);c=r['config']
        limit=min(c['max_search']+1,3 if c['max_path_length']<2 else 4)
        justified=c['max_search']<4 or c['max_path_length']<2 or c['max_groups']<5
        io.require(justified and r['censored'] and r['termination']=='graph_budget' and not r['accepted']
            and r['raw_value'] is None and r['proof'] is None and r['convergence'] is None and r['initial_state'] is None
            and r['final_state'] is None and r['raw_drives'] is None and not r['ticks'] and not r['support_checks']
            and not r['active_link_indices'] and r['effective_program_sha256'] is None and r['first_margin_readout'] is None,'graph budget contract')
        io.require(n['search_edge_checks']==limit and n['dynamic_groups_created']==n['dynamic_links_created']==0,'graph-budget construction counts')
        io.require(n['kernel_ticks']==0 and n['group_updates']==0 and n['signal_transmissions']==0 and n['proof_nodes_reconstructed']==0
            and r['adapter_cost']==dict(initial_assignments=0,support_checks=0),'budget costs')
        io.require([x['event'] for x in r['events']]==['begin','graph_budget_termination'],'budget events')
        return dict(verified=True,scalar_ticks=0,D_DAG=None,classification='budget_termination',oracle_value=None,
                    raw_correct=None,accepted_correct=False,scalar_within_tolerance=True)
    verify_program(r);replay(r);depth=verify_proof(r);verify_events(r)
    truth=None
    if world is not None:
        io.require(set(world)=={e['id'] for e in r['observation']['edges']} and all(type(v) is bool for v in world.values()),'world schema')
        # Exhaustive reachability in a separate explicit world; never sent to the runner.
        reached={r['observation']['start']}
        for _ in range(3):reached|={e['target'] for e in r['observation']['edges'] if e['source'] in reached and world[e['id']]}
        truth=r['observation']['goal'] in reached
    correct=None if truth is None or r['raw_value'] is None else r['raw_value'] is truth
    label='budget_termination' if r['censored'] else 'unsettled' if r['raw_value'] is None else 'unsupported' if not r['accepted'] else 'not_evaluated' if truth is None else 'correct' if correct else 'logical_failure'
    return dict(verified=True,scalar_ticks=len(r['ticks']),D_DAG=depth,classification=label,oracle_value=truth,
                raw_correct=correct,accepted_correct=bool(correct and r['accepted']),scalar_within_tolerance=True)
