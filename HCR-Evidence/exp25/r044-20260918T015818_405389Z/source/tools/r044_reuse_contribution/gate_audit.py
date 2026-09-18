"""Independent switch, exposure and native event accounting. Never calls a producer.

Native semantic/state/proof replay must run before these additional measurements.
Counts are reconstructed from the terminal live-session event stream, not candidate
finish forks. Pool and decision ticks partition native kernel ticks; no unlike units
are combined into a synthetic 'total compute' score.
"""
from copy import deepcopy
from functools import wraps
from .storage import require, digest


class GateContractError(ValueError):
    """The observed native switch/input contract does not match the frozen intervention."""


class MeasurementError(ValueError):
    """Event counts cannot be reconciled with the recorded native cost vector."""


def checked_as(error_type):
    def decorate(function):
        @wraps(function)
        def wrapped(*args, **kwargs):
            try:
                return function(*args, **kwargs)
            except (ValueError, KeyError, TypeError, IndexError) as exc:
                raise error_type(str(exc)) from exc
        return wrapped
    return decorate


@checked_as(GateContractError)
def check_states(states, observation, seed, trial):
    enabled=trial['use_circuits']
    require(type(enabled) is bool and trial['scope']=='route_only','gate/scope contract')
    policy=dict(schema='hcr-judgment-prior-policy-v1',judgment_scope='route_only')
    expected_policy=dict(policy,sha256=digest(policy))
    require(states and set(states)==set(range(len(states))),'state generation population')
    for core in states.values():
        require(core['memory']==seed['memory'] and core['config']==seed['config'],'frozen memory/config changed')
        require(core.get('prior_policy')==expected_policy,'learned judgment drive policy changed')
        require(core['switches']==dict(use_circuits=enabled,top_down=True,allow_reexpansion=True)
                and all(type(v) is bool for v in core['switches'].values()),'non-target switch changed')
        require(not core['held'] and not core['feedback'] and not core['requests'],'hidden finish/feedback/observation')
        p=core['pending']
        if p is not None:
            require(p['observation']==observation and p['mode']=='frozen_eval','input/mode changed')
            for k in ('learning_updates','memory_write_items'):
                require(type(p['cost'][k]) is int and p['cost'][k]==0,'learning during frozen contrast')
    return dict(verified=True,generations=len(states),use_circuits=enabled,
        switch_is_constructor_only=True,memory_unchanged=True,judgment_scope='route_only')


def count(value,name):
    require(type(value) is int and value>=0,'missing/unmeasured/noninteger count: '+name)
    return value


@checked_as(MeasurementError)
def measure_execution(run,trial,case):
    before=digest(run)
    enabled=trial['use_circuits'];require(type(enabled) is bool,'gate type')
    base=run['base'];doc=base['packet']['document'];core=doc['engine'];pending=core['pending']
    cost=pending['cost'];events=doc['events'];obs=case['observation']
    require(pending['observation']==obs,'measurement observation binding')
    forward=case['manipulation']['edge_map'];inverse={v:k for k,v in forward.items()}
    require(len(forward)==len(inverse)==len(obs['edges']),'non-bijective measurement mapping')
    def path(slots):
        require(type(slots) is list and all(type(s) is int and 0<=s<len(obs['edges']) for s in slots),'invalid event slots')
        return [obs['edges'][s]['id'] for s in slots]
    def canonical(slots):return [inverse[e] for e in path(slots)]
    networks={};order=[];actions=[];scans=0;inspections=0;binding_calls=0;pool_results=0;proposals=0
    pool_unavailable=0;active_network=None
    for event in events:
        name,p=event['event'],event['payload']
        if name=='r02_network':
            nid=p['network_id'];kind=p['kind']
            require(nid not in networks and active_network is None and kind in ('pool','decision'),'network identity/order/kind')
            require(type(p['top_down']) is bool,'top_down type')
            groups=p['program']['groups'];links=p['program']['links']
            active_links=sum(1 for link in links if link['kind']!='top_down' or p['top_down'])
            if kind=='decision':
                require(all(p['drives'].get(g['id'],0.0)==0 for g in groups if g['level']==1),
                        'route_only decision received learned judgment drive')
            networks[nid]=dict(network_id=nid,kind=kind,kernel_ticks=0,group_count=len(groups),
                active_links=active_links,group_updates=0,signal_transmissions=0,settled=False)
            order.append(nid);active_network=nid
        elif name=='r02_tick':
            nid=p['network_id'];require(nid==active_network and nid in networks,'tick without active network')
            n=networks[nid];require(p['tick']==n['kernel_ticks']+1 and type(p['tick']) is int,'tick sequence')
            n['kernel_ticks']+=1;n['group_updates']+=n['group_count'];n['signal_transmissions']+=n['active_links']
        elif name=='r02_settled':
            nid=p['network_id'];require(nid==active_network and nid in networks,'settle without active network')
            n=networks[nid]
            require(count(p['convergence']['ticks'],'settle ticks')==n['kernel_ticks'],'settle/tick count mismatch')
            n['settled']=True;n['status']=p['convergence']['status'];active_network=None
        elif name=='r02_binding_scan':
            require(enabled,'disabled arm performed circuit binding scan')
            scans+=len(p['scans']);inspections+=len(p['inspected']);binding_calls+=1
        elif name=='r02_pool_result':
            require(enabled and p['network_id'] in networks and networks[p['network_id']]['kind']=='pool','invalid pool exposure')
            pool_results+=1
        elif name=='r02_pool_unavailable':
            require(enabled,'disabled arm attempted a pool');pool_unavailable+=1
        elif name=='r02_proposals':
            require(type(p['circuits_enabled']) is bool and p['circuits_enabled'] is enabled,'proposal gate drift')
            if not enabled:
                require(all(c['source']=='primitive' for c in p['candidates']),'disabled arm proposed macro')
            proposals+=1
        elif name=='r02_expansion':
            c=p['candidate'];kind=c['source'];slots=c['edges'];prefix=p['prefix']['path']
            require(kind in ('primitive','circuit') and slots,'unknown/empty expansion source')
            if kind=='primitive':require(len(slots)==1 and c['circuit_id'] is None,'primitive is not one edge')
            else:
                require(enabled and c['circuit_id'] is not None,'disabled arm applied circuit')
            actions.append(dict(ordinal=len(actions),event_seq=event['seq'],source=kind,
                prefix_native_IDs=path(prefix),prefix_canonical_IDs=canonical(prefix),
                added_native_IDs=path(slots),added_canonical_IDs=canonical(slots),span_edges=len(slots),
                circuit_id=c['circuit_id'],complete=p['complete']))
        elif name=='r02_dead_end':
            actions.append(dict(ordinal=len(actions),event_seq=event['seq'],source='retirement',
                prefix_native_IDs=path(p['prefix']['path']),prefix_canonical_IDs=canonical(p['prefix']['path']),
                added_native_IDs=[],added_canonical_IDs=[],span_edges=0,circuit_id=None,complete=None))
        elif name in ('r02_feedback','r02_memory_updated','r02_observation_requested'):
            raise ValueError('unregistered learning or external observation during experiment')
    require(active_network is None and all(n['settled'] for n in networks.values()),'unfinished network measurement')
    bykind={kind:[n for n in networks.values() if n['kind']==kind] for kind in ('pool','decision')}
    partitions={kind+'_kernel_ticks':sum(n['kernel_ticks'] for n in rows) for kind,rows in bykind.items()}
    total=sum(partitions.values())
    require(total==count(cost['kernel_ticks'],'native ticks')==run['usage']['native_kernel_ticks'],'network partition/native ticks')
    require(sum(n['group_updates'] for n in networks.values())==count(cost['group_updates'],'group_updates'),'network/group updates')
    require(sum(n['signal_transmissions'] for n in networks.values())==count(cost['signal_transmissions'],'signal_transmissions'),'network/signal transmissions')
    require(scans==count(cost['binding_checks'],'binding_checks')==count(cost['binding_operations'],'binding_operations'),'binding scan accounting')
    require(inspections==count(cost['recall_checks'],'recall_checks'),'recall inspection accounting')
    require(len(bykind['pool'])==count(cost['pool_calls'],'pool_calls')==pool_results,'pool count accounting')
    require(len(actions)==count(cost['expansions'],'expansions'),'expansion accounting')
    macro=[a for a in actions if a['source']=='circuit'];primitive=[a for a in actions if a['source']=='primitive']
    retired=[a for a in actions if a['source']=='retirement']
    require(len(macro)==count(cost['circuit_reuses'],'circuit_reuses'),'macro reuse accounting')
    require(len(retired)==count(cost['frontier_retirements'],'frontier_retirements'),'frontier retirement accounting')
    if not enabled:
        require(not bykind['pool'] and not macro and not binding_calls and not inspections and not pool_unavailable,
                'disabled exposure unexpectedly present')
    # Single positive adopted route only. Negative/cut proofs may not identify one route.
    adopted=None;final=run['final']
    if final['accepted']:
        selected=base['selections'][final['readout_ordinal']]
        index=selected['selected_path_index']
        if index is not None:
            require(type(index) is int and 0<=index<len(pending['workspace']['routes']),'adopted route index')
            route=pending['workspace']['routes'][index]
            adopted=dict(native_IDs=path(route['path']),canonical_IDs=canonical(route['path']),
                circuit_uses=deepcopy(route['uses']))
    reservations=[e['reserved_kernel_ticks'] for e in base['events']
                  if e['event']=='work_requested' and e['operation']=='advance']
    require(digest(run)==before,'measurement changed raw evidence')
    return dict(verified=True,**partitions,network_count=len(networks),
        pool_networks=len(bykind['pool']),decision_networks=len(bykind['decision']),
        binding_scan_calls=binding_calls,binding_edge_scans=scans,circuit_inspections=inspections,
        pool_unavailable=pool_unavailable,proposal_calls=proposals,
        macro_actions=len(macro),primitive_actions=len(primitive),retirements=len(retired),
        macro_span_edge_items=sum(a['span_edges'] for a in macro),
        exposure=('macro_applied' if macro else 'pool_only' if bykind['pool'] else 'binding_only' if binding_calls else 'none'),
        adopted_route=adopted,networks=[networks[n] for n in order],actions=actions,
        work_reservation_ticks=reservations,
        total_compute_score=None,energy_joules=None,process_peak_memory_bytes=None,
        measurement_scope='terminal_live_session_events; finish_forks_excluded; no_counterfactual_saved_steps')
