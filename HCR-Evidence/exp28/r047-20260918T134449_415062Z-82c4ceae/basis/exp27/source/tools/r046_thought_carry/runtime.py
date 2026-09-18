"""Native HCR core + explicit carry adapter. Never imports evaluator or receives world labels.

This is not AdaptiveSession: path search and decision kernel are unchanged native calls,
while cross-query proof identity and carry guards are new, externally visible mechanisms.
"""
from __future__ import annotations
from copy import deepcopy
from time import perf_counter
from .storage import require, digest, canonical
from .contracts import ARMS


def _bridge_cost():
    return dict(export_bytes=0,import_bytes=0,packet_hash_checks=0,dependency_checks=0,
        endpoint_checks=0,state_groups_read=0,state_groups_written=0,
        proof_nodes_created=0,proof_nodes_reused=0,proof_ref_checks=0,
        support_checks=0,typed_term_checks=0,candidate_nodes_created=0,candidate_discarded_nodes=0)


def _namespaced(proof, namespace):
    out=deepcopy(proof)
    out['nodes']=[dict(n,id=namespace+n['id'],parents=[namespace+p for p in n['parents']]) for n in proof['nodes']]
    out['final']=None if proof['final'] is None else namespace+proof['final']
    out['external_node_refs']=[]
    return out


def _export(source, kind, cost):
    """Serialize a prior adopted result, not a value supplied by the experiment host."""
    if not source['accepted'] or source['raw_value'] is not True:
        return None
    obs=source['observation']; proof=source['proof_graph']
    # Current design exports positive path relations only; no negative fact compression.
    require(proof['final'] is not None and proof['under_assumptions_valid'], 'export without proof')
    require(len(proof['paths'])==1,'EXP27 export scope is one supported source path')
    require(not proof['external_node_refs'],'EXP27 supports one A-to-B carry boundary; nested carry is not implemented')
    edges={e['id']:e for e in obs['edges']}
    deps=[deepcopy(edges[eid]) for eid,truth in proof['assumed_edges'] if truth is True]
    packet=dict(schema='hcr-exp27-carry-v1',kind=kind,origin_record_sha256=digest(source),
        episode_id=obs['episode_id'],origin_revision=obs['revision'],
        config_sha256=digest(source['config']),start=obs['start'],end=obs['goal'],value=True,
        dependencies=deps,proof_ref=proof['final'],
        node_refs=[n['id'] for n in proof['nodes']],source_paths=deepcopy(proof['paths']))
    if kind=='state_carry':
        packet['state']=deepcopy(source['final_state'])
    elif kind=='proof_memo':
        packet['cache_key']=[obs['episode_id'],obs['start'],obs['goal']]
    elif kind=='relation_carry':
        packet['term']=dict(predicate='reachable',arguments=[obs['start'],obs['goal']])
    else: raise ValueError('unknown carry kind')
    packet['sha256']=digest(packet)
    cost['export_bytes']=len(canonical(packet))
    return packet


def import_guard(packet, obs, cfg, source, cost):
    """Corruption raises; valid-but-inapplicable data is rejected without repair."""
    if packet is None: return False,'no_adopted_positive_source'
    cost['import_bytes']=len(canonical(packet)); cost['packet_hash_checks']+=2
    require(packet.get('sha256')==digest({k:v for k,v in packet.items() if k!='sha256'}),'carry checksum')
    require(packet['origin_record_sha256']==digest(source),'foreign origin record')
    require(packet['schema']=='hcr-exp27-carry-v1','carry schema')
    base={'schema','kind','origin_record_sha256','episode_id','origin_revision','config_sha256',
          'start','end','value','dependencies','proof_ref','node_refs','source_paths','sha256'}
    extras={'state_carry':{'state'},'proof_memo':{'cache_key'},'relation_carry':{'term'}}
    require(packet['kind'] in extras and set(packet)==base|extras[packet['kind']],'carry fields')
    require(packet['value'] is True,'carry value contract')
    require(packet['proof_ref']==source['proof_graph']['final'] and
        packet['node_refs']==[n['id'] for n in source['proof_graph']['nodes']], 'carry proof identity')
    cost['proof_ref_checks']+=1+len(packet['node_refs'])
    if packet['kind']=='relation_carry':
        cost['typed_term_checks']+=1
        require(packet['term']=={'predicate':'reachable','arguments':[packet['start'],packet['end']]},'typed term binding')
    elif packet['kind']=='proof_memo':
        require(packet['cache_key']==[packet['episode_id'],packet['start'],packet['end']],'memo key')
    cost['endpoint_checks']+=3
    if packet['config_sha256']!=digest(cfg): return False,'config_changed'
    if packet['episode_id']!=obs['episode_id']: return False,'episode_mismatch'
    if packet['start']!=obs['start']: return False,'subject_mismatch'
    if obs['revision']<packet['origin_revision']: return False,'revision_rollback'
    current={e['id']:e for e in obs['edges']}
    for dep in packet['dependencies']:
        cost['dependency_checks']+=1
        if current.get(dep['id'])!=dep: return False,'support_dependency_changed'
    return True,'bound_and_dependencies_current'


def _state_initial(program, obs, source, packet, cost):
    """Bind by edge identity/endpoints and prefix relation, never by coincidental slot names."""
    initial={g.id:.5 for g in program.groups}; mapping=[]
    old_obs=source['observation'];old_edges=old_obs['edges'];new_edges=obs['edges']
    old_state=packet['state'];descriptors={}
    for i,e in enumerate(old_edges):
        descriptors[('edge',e['id'],e['source'],e['target'])]='e:'+str(i)
    for pi,path in enumerate(source['program']['paths']):
        for j in range(len(path)):
            key=('prefix',old_obs['start'],tuple(old_edges[s]['id'] for s in path[:j+1]))
            descriptors[key]=f'p:{pi}:{j}'
    def copy(key,new):
        old=descriptors.get(key)
        if old is not None:
            v=old_state[old]
            require(type(v) in (int,float) and 0<=v<=1,'source activation range')
            initial[new]=v;mapping.append(dict(source_group=old,target_group=new,value=v))
            cost['state_groups_read']+=1;cost['state_groups_written']+=1
    for i,e in enumerate(new_edges): copy(('edge',e['id'],e['source'],e['target']),'e:'+str(i))
    for pi,path in enumerate(program.paths):
        for j in range(len(path)):
            copy(('prefix',obs['start'],tuple(new_edges[s]['id'] for s in path[:j+1])),f'p:{pi}:{j}')
    require(initial['goal']==.5,'old goal must not initialize a different query goal')
    return initial,mapping


def _compose_candidate(obs, program, packet, source, namespace, cost):
    """Construct B from A+current suffix BEFORE decision settling; no B activation input."""
    old_path=packet['source_paths'][0]
    candidates=range(len(program.paths))
    for pi in candidates:
        path=program.paths[pi]
        ids=[obs['edges'][i]['id'] for i in path]
        if ids[:len(old_path)]!=old_path or len(ids)<=len(old_path): continue
        if not all(obs['edges'][i]['score'] is not None and obs['edges'][i]['score']>0 for i in path[len(old_path):]):continue
        # The source graph is kept in its own raw record. Only references are imported here.
        nodes=[];prev=packet['proof_ref'];depth=source['proof_graph']['primitive_depth']
        for j in range(len(old_path),len(path)):
            slot=path[j];fid=namespace+f'f:{slot}:1';rid=namespace+f'r:{pi}:{j}'
            nodes.append(dict(id=fid,rule='assumed_open',edge_id=ids[j],parents=[],path_index=None))
            nodes.append(dict(id=rid,rule='extend_path',edge_id=None,parents=[prev,fid],path_index=pi))
            prev=rid;depth+=1
        cost['proof_nodes_reused']=len(packet['node_refs'])
        cost['proof_nodes_created']=len(nodes)
        cost['candidate_nodes_created']=len(nodes)
        return dict(nodes=nodes,external_node_refs=list(packet['node_refs']),final=prev,
            primitive_depth=depth,assumed_edges=sorted([[eid,True] for eid in ids]),
            under_assumptions_valid=True,paths=[[obs['edges'][i]['id'] for i in p] for p in program.paths])
    return None


def _directionally_supported(proof, obs, value, cost):
    if not proof['under_assumptions_valid'] or proof['final'] is None or value is None: return False
    edges={e['id']:e for e in obs['edges']}
    for eid,truth in proof['assumed_edges']:
        cost['support_checks']+=1
        require(eid in edges,'proof mentions absent evidence')
        score=edges[eid]['score']
        if score is None or score==0 or (score>0) is not truth:return False
    # The proof builder supplies structural validity; an independent auditor checks it separately.
    return True


def run_query(observation, config, arm='cold', source=None, event_sink=None):
    """No scenario/variant/world input. Every mutation is local and traceable."""
    from hcr.model import Config,Cost,Status,ExpansionLimit
    from hcr.codec import observation_from,plain
    from hcr.binding import Binding,Topology
    from hcr.workspace import discover_paths,make_program
    from hcr.dynamics import settle
    from hcr.proof import reconstruct
    require(arm in ARMS,'unknown arm'); require(arm=='cold' or source is not None,'carry requires A')
    obs=observation_from(deepcopy(observation));cfg=Config(**deepcopy(config))
    cost=Cost(); bridge=_bridge_cost();t0=perf_counter();events=[]
    def emit(name,data):
        event=dict(ordinal=len(events),event=name,payload=deepcopy(data));events.append(event)
        if event_sink is not None:event_sink(event)
    emit('begin',dict(observation_sha256=obs.digest,config_sha256=digest(config),arm=arm,
        source_sha256=None if source is None else digest(source)))
    packet=None;valid=False;reason='not_requested'
    if arm!='cold':
        packet=_export(source,arm,bridge)
        valid,reason=import_guard(packet,observation,config,source,bridge)
    gate_reason=reason
    emit('carry_gate',dict(packet=packet,valid=valid,reason=gate_reason,
        fallback_to_cold=(arm!='cold' and not valid)))
    # All arms execute the same native topology discovery; no graph search reduction is claimed.
    try:
        paths=discover_paths(Topology.from_observation(obs),cfg,cost)
    except ExpansionLimit as exc:
        emit('budget_termination',dict(stage='native_path_search',message=str(exc)))
        return dict(schema='hcr-exp27-query-v1',observation=deepcopy(observation),config=deepcopy(config),arm=arm,
            source_sha256=None if source is None else digest(source),carry_packet=packet,gate_valid=valid,gate_reason=gate_reason,
            pre_decision_candidate=None,censored=True,reason='path_budget',raw_value=None,accepted=False,program=None,raw_drives=None,
            effective_drives=None,initial_state=None,transfer_map=[],ticks=[],convergence=None,final_state=None,
            proof_graph=None,native_cost=cost.snapshot(),bridge_cost=bridge,events=events,wall_seconds=perf_counter()-t0)
    require(paths,'EXP27 scope requires at least one structural path; no path is not silently fabricated')
    program=make_program(len(obs.edges),paths,cfg,cost)
    drives={f'e:{i}':cfg.evidence_gain*(e.score or 0.0) for i,e in enumerate(obs.edges)};drives['goal']=0.0
    effective={g.id:drives.get(g.id,0.0) for g in program.groups}
    initial={g.id:.5 for g in program.groups};mapping=[]
    if arm=='state_carry' and valid:initial,mapping=_state_initial(program,observation,source,packet,bridge)
    namespace='q:'+obs.digest[:24]+':'
    candidate=None
    if arm in ('proof_memo','relation_carry') and valid:
        candidate=_compose_candidate(observation,program,packet,source,namespace,bridge)
    emit('relation_candidate',dict(value=True if candidate is not None else None,
        term={'predicate':'reachable','arguments':[obs.start,obs.goal]} if candidate is not None else None,
        proof=candidate,before_decision_kernel=True))
    emit('network',dict(program=plain(program),raw_drives=drives,effective_drives=effective,
        initial=initial,transfer_map=mapping,top_down=True))
    ticks=[]
    def observe(i,state,residual,stable):
        row=dict(tick=i,state=deepcopy(state),residual=residual,stable_steps=stable)
        ticks.append(row);emit('tick',row)
    state,convergence=settle(program,drives,cfg,cost,initial=initial,observe=observe,top_down=True)
    value=(state['goal']>=.5) if convergence.status==Status.STABLE_DECISION else None
    emit('settled',dict(state=state,convergence=plain(convergence),raw_value=value))
    proof=deepcopy(candidate) if candidate is not None and value is True else None
    if candidate is not None and value is not True:
        bridge['candidate_discarded_nodes']=len(candidate['nodes'])
        bridge['proof_nodes_reused']=0
        emit('candidate_not_adopted',dict(reason='native_verifier_did_not_accept_positive',
            candidate_value=True,native_value=value,candidate_preserved=True))
    if proof is None:
        native_proof=reconstruct(obs,program,Binding(obs.digest,obs.revision,tuple(range(len(obs.edges)))),state,value,cost)
        proof=_namespaced(plain(native_proof),namespace)
        bridge['proof_nodes_created']=len(proof['nodes'])+bridge['candidate_discarded_nodes']
    emit('proof_built',dict(proof=proof,native_nodes_reconstructed=cost.proof_nodes_reconstructed,
         bridge_nodes_created=bridge['proof_nodes_created'],foreign_nodes_reused=bridge['proof_nodes_reused']))
    accepted=_directionally_supported(proof,observation,value,bridge)
    censored=convergence.status==Status.BUDGET_EXHAUSTED
    reason=('kernel_budget' if censored else 'adopted_supported' if accepted else 'unsupported_or_unsettled')
    emit('adoption',dict(accepted=accepted,value=value,reason=reason))
    return dict(schema='hcr-exp27-query-v1',observation=deepcopy(observation),config=deepcopy(config),arm=arm,
        source_sha256=None if source is None else digest(source),carry_packet=packet,gate_valid=valid,gate_reason=gate_reason,
        pre_decision_candidate=candidate,censored=censored,reason=reason,raw_value=value,accepted=accepted,program=plain(program),
        raw_drives=drives,effective_drives=effective,initial_state=initial,transfer_map=mapping,ticks=ticks,
        convergence=plain(convergence),final_state=state,proof_graph=proof,native_cost=cost.snapshot(),
        bridge_cost=bridge,events=events,wall_seconds=perf_counter()-t0)
