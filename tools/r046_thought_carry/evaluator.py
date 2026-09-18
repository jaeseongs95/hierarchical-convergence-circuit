"""Independent audit: no runtime/hcr imports. BFS, scalar equations and proof term semantics.

Inputs are immutable raw records. This module never repairs records or supplies decisions.
"""
from __future__ import annotations
from collections import deque
from math import exp,isclose,isfinite
from .storage import require,digest,canonical

TOL=2e-12

def close(a,b):
    if isinstance(a,dict) and isinstance(b,dict):
        return set(a)==set(b) and all(close(a[k],b[k]) for k in a)
    if isinstance(a,list) and isinstance(b,list):
        return len(a)==len(b) and all(close(x,y) for x,y in zip(a,b))
    if type(a) in (int,float) and type(b) in (int,float):
        return isfinite(a) and isfinite(b) and isclose(a,b,abs_tol=TOL,rel_tol=TOL)
    return type(a)==type(b) and a==b


def paths_bfs(obs,cfg):
    """Enumerate structural paths without reading scores. Return native-search-equivalent work."""
    queue=deque([(obs['start'],(obs['start'],),())]);paths=[];scans=0
    while queue:
        v,seen,path=queue.popleft()
        if v==obs['goal']:
            paths.append(list(path));require(len(paths)<=cfg['max_paths'],'auditor path budget')
            continue
        for i,e in enumerate(obs['edges']):
            scans+=1
            require(scans<=cfg['max_search'],'auditor search budget')
            if e['source']==v and e['target'] not in seen:
                require(len(path)<cfg['max_path_length'],'auditor length budget')
                queue.append((e['target'],seen+(e['target'],),path+(i,)))
    return paths,scans


def world_answer(obs,world):
    require(set(world)=={e['id'] for e in obs['edges']} and all(type(v) is bool for v in world.values()),'world fields')
    seen={obs['start']};work=[obs['start']]
    for v in work:
        for e in obs['edges']:
            if e['source']==v and world[e['id']] and e['target'] not in seen:
                seen.add(e['target']);work.append(e['target'])
    return obs['goal'] in seen


def program_check(r):
    obs,cfg,pg=r['observation'],r['config'],r['program']
    paths,search=paths_bfs(obs,cfg)
    require({tuple(x) for x in paths}=={tuple(x) for x in pg['paths']},'native program missing/extra structural path')
    require(len(paths)==len(pg['paths']) and pg['edge_count']==len(obs['edges']),'program path cardinality')
    groups=[dict(id=f'e:{i}',level=0,bias=0.0) for i in range(len(obs['edges']))];links=[]
    gain=cfg['relation_gain']
    for pi,path in enumerate(pg['paths']):
        for j,slot in enumerate(path):
            key=f'p:{pi}:{j}';parents=[f'e:{slot}']+([] if j==0 else [f'p:{pi}:{j-1}'])
            groups.append(dict(id=key,level=1,bias=-gain*(len(parents)-1)))
            for par in parents:
                links.extend([dict(source=par,target=key,weight=gain,kind='support'),
                              dict(source=key,target=par,weight=cfg['top_down_gain'],kind='top_down')])
    groups.append(dict(id='goal',level=1,bias=gain*(len(pg['paths'])-1)))
    for pi,path in enumerate(pg['paths']):
        end=f'p:{pi}:{len(path)-1}'
        links.extend([dict(source=end,target='goal',weight=gain,kind='support'),
                      dict(source='goal',target=end,weight=cfg['top_down_gain'],kind='top_down')])
    require(close(pg['groups'],groups) and close(pg['links'],links),'program differs from full native path computation')
    expected={g['id']:0.0 for g in groups}
    for i,e in enumerate(obs['edges']):expected[f'e:{i}']=cfg['evidence_gain']*(e['score'] or 0.0)
    require(set(r['raw_drives'])<=set(expected),'unknown drive key')
    require(close({k:r['raw_drives'].get(k,0.0) for k in expected},expected),'unexpected effective drive')
    require(close(r['effective_drives'],expected),'effective drive annotation mismatch')
    require(r['native_cost']['search_edge_checks']==search,'native search work')
    require(r['native_cost']['dynamic_groups_created']==len(groups) and
            r['native_cost']['dynamic_links_created']==len(links),'program construction counts')
    return paths


def scalar_check(r):
    """Algebraically independent update form; replay every recorded state and stopping rule."""
    cfg=r['config'];pg=r['program'];state=r['initial_state'];history=[];stable=0;last=None
    ids={g['id'] for g in pg['groups']}
    require(set(state)==ids and all(type(x) in (int,float) and isfinite(x) and 0<=x<=1 for x in state.values()),'initial identity/range')
    for number,row in enumerate(r['ticks'],1):
        require(number==row['tick'] and last is None,'tick order or continuation after terminal')
        nxt={}
        for group in pg['groups']:
            key=group['id'];drive=group['bias']+r['raw_drives'].get(key,0.0)
            for link in pg['links']:
                if link['target']==key:drive+=link['weight']*(2*state[link['source']]-1)
            logit=(2*drive+(cfg['self_excitation']+cfg['inhibition'])*(2*state[key]-1))/cfg['temperature']
            prob=(1/(1+exp(-logit))) if logit>=0 else exp(logit)/(1+exp(logit))
            nxt[key]=(1-cfg['damping'])*state[key]+cfg['damping']*prob
        residual=max(abs(nxt[k]-state[k]) for k in ids)
        stable=stable+1 if residual<=cfg['residual_tolerance'] else 0
        require(close(row['state'],nxt) and close(row['residual'],residual) and row['stable_steps']==stable,'scalar tick mismatch')
        margin=abs(2*nxt['goal']-1)
        if stable>=cfg['patience']:
            last='stable_decision' if margin>=cfg['margin_threshold'] else 'stable_ambiguous'
        elif history and residual>cfg['residual_tolerance']*10 and max(abs(nxt[k]-history[-1][k]) for k in ids)<cfg['residual_tolerance']:
            last='oscillating'
        elif number==cfg['max_ticks']:last='budget_exhausted'
        history.append(state);history=history[-3:];state=nxt
    require(last is not None and close(state,r['final_state']),'missing terminal/final state')
    require(close(r['convergence'],dict(status=last,ticks=len(r['ticks']),residual=residual,margin=margin,stable_steps=stable)),'convergence mismatch')
    raw=(state['goal']>=.5) if last=='stable_decision' else None
    require(raw is r['raw_value'],'raw value/readout mismatch')
    native=r['native_cost'];n=len(r['ticks'])
    for field,expected in [('kernel_ticks',n),('group_updates',n*len(ids)),('normalization_ops',n*len(ids)),
                           ('signal_transmissions',n*len(pg['links']))]:require(native[field]==expected,'native '+field)
    return n


def guard_check(r,source):
    """Derive applicability from A and current B, not from production's reported gate."""
    arm=r['arm'];packet=r['carry_packet'];source_sha=None if source is None else digest(source)
    require(r['source_sha256']==source_sha,'source provenance')
    if arm=='cold':
        require(packet is None and not r['gate_valid'] and r['gate_reason']=='not_requested','cold received carry')
        return False
    if not source['accepted'] or source['raw_value'] is not True:
        require(packet is None and not r['gate_valid'] and r['gate_reason']=='no_adopted_positive_source','non-adopted A exported')
        return False
    require(packet is not None and packet['kind']==arm,'missing/wrong packet kind')
    require(packet['sha256']==digest({k:v for k,v in packet.items() if k!='sha256'}),'packet hash')
    a=source['observation'];b=r['observation'];pa=source['proof_graph']
    require(packet['origin_record_sha256']==source_sha and packet['config_sha256']==digest(source['config']),'origin/config')
    require(packet['episode_id']==a['episode_id'] and packet['origin_revision']==a['revision'] and
            (packet['start'],packet['end'])==(a['start'],a['goal']),'source term endpoint')
    require(packet['value'] is True and packet['proof_ref']==pa['final'] and packet['source_paths']==pa['paths'],'source proposition/proof')
    require(packet['node_refs']==[n['id'] for n in pa['nodes']],'source node identities')
    ae={e['id']:e for e in a['edges']}
    deps=[ae[eid] for eid,truth in pa['assumed_edges'] if truth]
    require(packet['dependencies']==deps,'source support dependencies')
    if arm=='relation_carry':require(packet['term']=={'predicate':'reachable','arguments':[a['start'],a['goal']]},'typed relation')
    if arm=='proof_memo':require(packet['cache_key']==[a['episode_id'],a['start'],a['goal']],'memo semantics')
    if arm=='state_carry':require(packet['state']==source['final_state'],'source state mutated')
    reason='bound_and_dependencies_current';checks=0
    if r['config']!=source['config']:reason='config_changed'
    elif b['episode_id']!=a['episode_id']:reason='episode_mismatch'
    elif b['start']!=a['start']:reason='subject_mismatch'
    elif b['revision']<a['revision']:reason='revision_rollback'
    else:
        current={e['id']:e for e in b['edges']}
        for d in deps:
            checks+=1
            if current.get(d['id'])!=d:reason='support_dependency_changed';break
    valid=reason=='bound_and_dependencies_current'
    require(r['gate_valid'] is valid and r['gate_reason']==reason,'gate verdict')
    bc=r['bridge_cost']
    expected=dict(export_bytes=len(canonical(packet)),import_bytes=len(canonical(packet)),packet_hash_checks=2,
                  dependency_checks=checks,endpoint_checks=3,proof_ref_checks=1+len(packet['node_refs']),
                  typed_term_checks=int(arm=='relation_carry'))
    for k,v in expected.items():require(bc[k]==v,'carry work '+k)
    return valid


def initial_check(r,source,valid):
    target={g['id']:.5 for g in r['program']['groups']};pairs=[]
    if r['arm']=='state_carry' and valid:
        old=source['observation'];new=r['observation'];oldedge={e['id']:(i,e) for i,e in enumerate(old['edges'])}
        for i,e in enumerate(new['edges']):
            if e['id'] in oldedge:
                j,old_e=oldedge[e['id']]
                if (old_e['source'],old_e['target'])==(e['source'],e['target']):
                    pairs.append((f'e:{j}',f'e:{i}'))
        for pi,path in enumerate(r['program']['paths']):
            for j in range(len(path)):
                target_ids=[new['edges'][s]['id'] for s in path[:j+1]]
                for ai,apath in enumerate(source['program']['paths']):
                    if j<len(apath) and target_ids==[old['edges'][s]['id'] for s in apath[:j+1]] and new['start']==old['start']:
                        pairs.append((f'p:{ai}:{j}',f'p:{pi}:{j}'));break
        for a,b in pairs:target[b]=source['final_state'][a]
    expected=[dict(source_group=a,target_group=b,value=source['final_state'][a]) for a,b in pairs]
    require(r['transfer_map']==expected and r['initial_state']==target,'state transfer binding/initial')
    require(r['bridge_cost']['state_groups_read']==len(pairs)==r['bridge_cost']['state_groups_written'],'state transfer work')
    require(target['goal']==.5,'goal transfer prohibited')


def proof_check(r,source,valid):
    """Compute logical terms and depth from parents; do not trust native depth/validity."""
    proof=r['proof_graph'];obs=r['observation'];edges={e['id']:e for e in obs['edges']}
    current_paths=[tuple(obs['edges'][i]['id'] for i in p) for p in r['program']['paths']]
    require([tuple(x) for x in proof['paths']]==current_paths or
            (r['raw_value'] is None and not proof['paths'] and not proof['nodes'] and proof['final'] is None),
            'proof paths differ from graph')
    own={n['id']:n for n in proof['nodes']}
    require(len(own)==len(proof['nodes']),'duplicate proof nodes')
    external=proof['external_node_refs']
    require(len(set(external))==len(external) and not set(external)&set(own),'duplicate/shadowed references')
    parent_nodes={} if source is None else {n['id']:n for n in source['proof_graph']['nodes']}
    require(not external or (r['arm'] in ('proof_memo','relation_carry') and valid),'unauthorized/stale reuse')
    require(set(external)<=set(parent_nodes),'unresolved external reference')
    nodes=dict(own,**{k:parent_nodes[k] for k in external});memo={};active=set();leaves={}
    def walk(key):
        require(key in nodes and key not in active,'missing parent or proof cycle')
        if key in memo:return memo[key]
        active.add(key);n=nodes[key];rule=n['rule'];parents=[walk(k) for k in n['parents']]
        if rule in ('assumed_open','assumed_closed'):
            require(not parents and n['edge_id'] in edges,'fact rule')
            truth=rule=='assumed_open';term=('fact',n['edge_id'],truth);depth=0
            require(n['edge_id'] not in leaves or leaves[n['edge_id']]==truth,'inconsistent assumptions')
            leaves[n['edge_id']]=truth
        elif rule=='start_edge':
            require(len(parents)==1 and parents[0][0][0]=='fact' and parents[0][0][2] is True,'start rule parents')
            e=edges[parents[0][0][1]];require(e['source']==obs['start'],'bound start mismatch')
            term=('reachable',e['source'],e['target']);depth=1
        elif rule=='extend_path':
            require(len(parents)==2 and parents[0][0][0]=='reachable' and parents[1][0][0]=='fact' and parents[1][0][2] is True,'extension parents')
            a=parents[0][0];e=edges[parents[1][0][1]];require(a[2]==e['source'],'parent/child semantic binding')
            term=('reachable',a[1],e['target']);depth=1+max(v[1] for v in parents)
        elif rule=='path_blocked':
            require(len(parents)==1 and parents[0][0][0]=='fact' and parents[0][0][2] is False,'cut parents')
            idx=n['path_index'];require(type(idx) is int and 0<=idx<len(current_paths),'cut path index')
            require(parents[0][0][1] in current_paths[idx],'cut does not block its path')
            term=('blocked',idx);depth=1+parents[0][1]
        elif rule=='all_paths_blocked':
            require(len(parents)==len(current_paths) and {p[0] for p in parents}=={('blocked',i) for i in range(len(current_paths))},'incomplete negative coverage')
            term=('not_reachable',obs['start'],obs['goal']);depth=1+max(v[1] for v in parents)
        else:raise ValueError('unknown proof rule '+str(rule))
        active.remove(key);memo[key]=(term,depth);return memo[key]
    if proof['final'] is None:
        require(not proof['under_assumptions_valid'] and not r['accepted'],'accepted without proof')
        depth=None;supported=False
    else:
        term,depth=walk(proof['final'])
        expected=('reachable' if r['raw_value'] else 'not_reachable',obs['start'],obs['goal'])
        require(term==expected,'proof final proves a different proposition')
        require(set(external)==set(memo)&set(external),'unused external reference inventory')
        supported=all(edges[e]['score'] is not None and edges[e]['score']!=0 and (edges[e]['score']>0)==t for e,t in leaves.items())
        require(proof['under_assumptions_valid'] is True,'validity flag')
    require(depth==proof['primitive_depth'],'D_DAG differs from unfolded dependencies')
    require(sorted(leaves.items())==[tuple(x) for x in proof['assumed_edges']],'assumption inventory')
    require(r['accepted'] is bool(supported and r['raw_value'] is not None),'adoption/support discrepancy')
    checks=0
    if proof['under_assumptions_valid'] and proof['final'] is not None and r['raw_value'] is not None:
        for eid,t in proof['assumed_edges']:
            checks+=1; score=edges[eid]['score']
            if score is None or score==0 or (score>0)!=t:break
    require(r['bridge_cost']['support_checks']==checks,'support check count')
    require(r['bridge_cost']['proof_nodes_created']==len(own)+r['bridge_cost']['candidate_discarded_nodes'] and r['bridge_cost']['proof_nodes_reused']==len(external),'proof work inventory')
    require(r['native_cost']['proof_nodes_reconstructed']==(0 if external else len(own)),'native reconstruction inventory')
    return dict(D_DAG=depth,own_nodes=len(own),reused_nodes=len(external),
                expanded_reachable_nodes=len(memo),supported=supported,
                relation_dependencies_reused=bool(external),proof_valid=True)


def audit_record(record,source=None,world=None):
    r=record;require(r['schema']=='hcr-exp27-query-v1','record schema')
    if source is not None:require(digest(source)==r['source_sha256'],'A record hash')
    if r['program'] is None:
        justified=False
        try:paths_bfs(r['observation'],r['config'])
        except ValueError as exc:justified=str(exc) in ('auditor path budget','auditor search budget','auditor length budget')
        require(justified,'unjustified path budget termination')
        require(r['censored'] and r['reason']=='path_budget' and not r['accepted'],'non-evaluable record classification')
        return dict(verified=True,measurement_available=False,classification='budget_termination')
    paths=program_check(r);valid=guard_check(r,source);initial_check(r,source,valid);scalar_check(r)
    proof=proof_check(r,source,valid)
    require(r['censored'] is (r['convergence']['status']=='budget_exhausted'),'censor status')
    require(r['reason']==('kernel_budget' if r['censored'] else 'adopted_supported' if r['accepted'] else 'unsupported_or_unsettled'),'terminal reason')
    ev=r['events'];require([x['ordinal'] for x in ev]==list(range(len(ev))),'event ordinal')
    require([x['payload'] for x in ev if x['event']=='tick']==r['ticks'],'raw/event tick mismatch')
    gate=[x['payload'] for x in ev if x['event']=='carry_gate'];require(len(gate)==1,'gate event count')
    require(gate[0]['packet']==r['carry_packet'] and gate[0]['valid']==r['gate_valid'] and gate[0]['reason']==r['gate_reason'],'gate event mismatch')
    cand_events=[x for x in ev if x['event']=='relation_candidate']
    require(len(cand_events)==1 and cand_events[0]['payload']['before_decision_kernel'] is True,'candidate boundary')
    candidate=r['pre_decision_candidate'];ce=cand_events[0]
    require(ce['payload']['proof']==candidate and ce['ordinal']<next(x['ordinal'] for x in ev if x['event']=='network'),'candidate created after native decision')
    if candidate is not None:
        require(r['arm'] in ('proof_memo','relation_carry') and valid,'candidate without authorized source')
        require(ce['payload']['value'] is True and ce['payload']['term']=={'predicate':'reachable','arguments':[r['observation']['start'],r['observation']['goal']]},'candidate term')
        # Check the candidate as a proof of B, independent of B numerical state.
        from copy import deepcopy
        cr=deepcopy(r);cr['proof_graph']=candidate;cr['raw_value']=True;cr['accepted']=True
        cr['bridge_cost']['proof_nodes_created']=len(candidate['nodes'])
        cr['bridge_cost']['candidate_discarded_nodes']=0
        cr['bridge_cost']['proof_nodes_reused']=len(candidate['external_node_refs'])
        cr['bridge_cost']['support_checks']=len(candidate['assumed_edges'])
        cr['native_cost']['proof_nodes_reconstructed']=0
        proof_check(cr,source,valid)
        require(r['bridge_cost']['candidate_nodes_created']==len(candidate['nodes']),'candidate creation count')
        require(r['bridge_cost']['candidate_discarded_nodes']==(0 if r['raw_value'] is True else len(candidate['nodes'])),'candidate discard count')
    else:
        require(ce['payload']['value'] is None and ce['payload']['term'] is None and r['bridge_cost']['candidate_nodes_created']==0 and r['bridge_cost']['candidate_discarded_nodes']==0,'null candidate annotation')
    network=[x['payload'] for x in ev if x['event']=='network'];require(len(network)==1,'network count')
    for a,b in [('program','program'),('raw_drives','raw_drives'),('effective_drives','effective_drives'),('initial','initial_state'),('transfer_map','transfer_map')]:
        require(network[0][a]==r[b],'network event '+a)
    require(network[0]['top_down'] is True,'top-down mode')
    require([x['payload']['proof'] for x in ev if x['event']=='proof_built']==[r['proof_graph']],'proof event mismatch')
    require([x['payload'] for x in ev if x['event']=='adoption']==[dict(accepted=r['accepted'],value=r['raw_value'],reason=r['reason'])],'adoption event mismatch')
    require(type(r['wall_seconds']) in (int,float) and isfinite(r['wall_seconds']) and r['wall_seconds']>=0,'wall time range')
    truth=None if world is None else world_answer(r['observation'],world)
    classification='not_evaluated_against_world' if world is None else 'abstention' if not r['accepted'] else 'correct' if r['raw_value']==truth else 'incorrect'
    return dict(verified=True,measurement_available=True,native_ticks_replayed=len(r['ticks']),
        numeric_scalar_replay=True,proof=proof,classification=classification,evaluator_truth=truth,
        raw_program_drive_sha256=digest(dict(program=r['program'],drives=r['raw_drives'])),
        effective_program_drive_sha256=digest(dict(program=r['program'],drives=r['effective_drives'])),
        dynamics_sha256=digest(dict(ticks=r['ticks'],convergence=r['convergence'])))
