"""Synthetic fixtures. These are not native HCC runs, measurements, or EXP26 results."""
from copy import deepcopy
from r045_direct_support import spec
from r045_direct_support.storage import digest


def pattern_fixture(length):
    return dict(
        entry_conditions=['injective_roles','contiguous_directed_path','current_revision','current_measurements'],
        kernel_signature='fixture-kernel', output_role=f'R{length}',
        program=dict(edge_count=length, groups=[], links=[], paths=[list(range(length))]),
        relations=[dict(kind='open_edge', source_role=f'R{i}', target_role=f'R{i+1}') for i in range(length)],
        roles=[dict(id=f'R{i}', kind='vertex') for i in range(length+1)])


def plan_fixture():
    seed=dict(memory=dict(schema='hcr-memory-r02',circuits=[
            dict(active=True,pattern=pattern_fixture(2)),
            dict(active=True,pattern=pattern_fixture(3))]),
        config=dict(activation_threshold=.55,mismatch_threshold=.8))
    parent=dict(conditions=dict(budget={'max_advances':12},selection_limits={'max_paths':4}),
        memory_sha256=digest(seed['memory']),config_sha256=digest(seed['config']))
    cases,worlds=spec.cases()
    plan=dict(conditions=spec.conditions(parent),cases=cases,evaluation_worlds=worlds,trials=spec.trials(),
        memory_sha256=parent['memory_sha256'],config_sha256=parent['config_sha256'])
    return plan,parent,seed


def measurement_fixture(family='supported_len2', gate=True, variant='identity'):
    plan,_,seed=plan_fixture()
    case=deepcopy(next(c for c in plan['cases'] if c['name']==family+'__'+variant))
    trial=deepcopy(next(t for t in plan['trials'] if t['case']==case['name'] and t['use_circuits'] is gate))
    obs=case['observation'];matching=gate and family!='no_match_len1';macro=matching and family=='supported_len2'
    events=[]
    def emit(name,**payload): events.append(dict(seq=len(events),event=name,payload=payload))
    slots=list(range(len(obs['edges'])))
    if gate:
        emit('r02_binding_scan',prefix={'path':[]},inspected=['fixture-pattern'],scans=[[]]*2,
             matched=[{'circuit_id':'fixture-pattern'}] if matching else [],complete=True,fallback_reason=None)
    for kind in (('pool','decision') if matching else ('decision',)):
        program=dict(groups=[{'id':'e:0','level':0},{'id':'goal','level':1}],links=[],paths=[slots],edge_count=len(slots))
        emit('r02_network',network_id=kind,kind=kind,program=program,drives={'e:0':1.0,'goal':0.0},top_down=True)
        for tick in (1,2): emit('r02_tick',network_id=kind,tick=tick,state={'e:0':.8,'goal':.8},residual=.01,stable_steps=tick)
        emit('r02_settled',network_id=kind,convergence={'ticks':2,'status':'stable_decision','margin':.6,'residual':.01,'stable_steps':2})
        if kind=='pool':
            emit('r02_pool_result',network_id=kind,activations=[dict(circuit_id='fixture-pattern',circuit_version=1,
                 binding={'edge_order':slots},activation=.9,mismatch=.92 if family=='conflict_len2' else 0.0,
                 prior=.1,eligible=macro)])
    value=family!='conflict_len2';route=None
    if value:
        route=dict(canonical_IDs=['e'+str(i) for i in slots],native_IDs=[e['id'] for e in obs['edges']],
                   circuit_uses=[{'fixture_only':True}] if macro else [])
    native_ticks=4 if matching else 2
    counts=dict(adopted_route=route,decision_networks=1,decision_kernel_ticks=2,pool_kernel_ticks=2 if matching else 0,
        pool_networks=int(matching),macro_actions=int(macro),primitive_actions=0 if macro else len(slots),
        binding_scan_calls=int(gate),binding_edge_scans=2 if gate else 0,circuit_inspections=int(gate),
        macro_span_edge_items=2 if macro else 0,exposure='macro_applied' if macro else 'pool_only' if matching else 'binding_only' if gate else 'none',
        actions=[],networks=[],pool_unavailable=0)
    run=dict(base=dict(packet=dict(document=dict(engine=dict(config=seed['config'],
        pending=dict(cost={'candidate_circuits':int(matching)},workspace={'routes':[]})),events=events))),
        final=dict(accepted=True,value=value,reason='stop_supported_policy',readout_ordinal=0))
    return run,trial,case,counts


def report_records():
    from r045_direct_support.measurements import measure
    plan,_,_=plan_fixture();records=[]
    for t in plan['trials']:
        family,variant=t['case'].split('__');gate=t['use_circuits']
        run,trial,case,counts=measurement_fixture(family,gate,variant)
        d=measure(run,trial,case,counts);length=len(case['observation']['edges'])
        value=family!='conflict_len2';ticks=counts['pool_kernel_ticks']+counts['decision_kernel_ticks']
        expansion=1 if counts['macro_actions'] else length
        diag=dict(canonical_readout_sha256=digest({'family':family,'gate':gate}),
            canonical_readouts=[{'ordinal':0,'ticks':ticks,'policy_value':value}],
            final_support_signature=dict(value=value,D_DAG=length,assumed_edges=[['e0',True]],paths=[]))
        records.append(dict(trial=deepcopy(t),family=family,id_variant=variant,final=run['final'],
            classification='correct_in_all_declared_worlds',diagnostics=diag,reuse_measurements=counts,direct_measurements=d,
            usage=dict(native_kernel_ticks=ticks,online_selection={'edge_checks':length}),
            native_cost=dict(kernel_ticks=ticks,expansions=expansion,wall_seconds=0.0,binding_checks=counts['binding_edge_scans']),
            scheduler_usage=dict(decision_calls=expansion),reported_wall_seconds=.01,readouts=[{}]))
    return records
