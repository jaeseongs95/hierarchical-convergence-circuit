"""Thin native runner. No world, evaluator, parent state, or diagnostic correction enters it."""
from copy import deepcopy
from time import perf_counter
from tools.r048_precision import io
from . import spec


def run_query(observation, config, arm, event_sink=None):
    from hcr.model import Config, Cost, Status, ExpansionLimit
    from hcr.codec import plain, observation_from
    from hcr.binding import Topology, Binding
    from hcr.workspace import discover_paths, make_program
    from hcr.dynamics import settle
    from hcr.proof import reconstruct
    ob=deepcopy(observation); cfg=Config(**deepcopy(config)); obs=observation_from(ob)
    io.require(len(obs.edges)==2, 'EXP30 runner requires exactly two public edges')
    policy=spec.intervention(arm); started=perf_counter();cost=Cost();events=[]
    def emit(name,payload):
        ev=dict(ordinal=len(events),event=name,payload=deepcopy(payload));events.append(ev)
        if event_sink is not None:event_sink(deepcopy(ev))
    emit('begin',dict(observation_sha256=obs.digest,config_sha256=io.digest(config),arm=arm,intervention=policy))
    base=dict(schema='hcr-exp30-query-v1',observation=ob,config=deepcopy(config),arm=arm,intervention=policy,
        prior_state_imported=False,initial_stable_steps=0,energy_joules=None,peak_memory_bytes=None,
        native_adaptive_expansions=None)
    try:
        paths=discover_paths(Topology.from_observation(obs),cfg,cost)
        io.require(len(paths)==1 and len(paths[0])==2,'EXP30 requires one two-edge chain')
        program=make_program(len(obs.edges),paths,cfg,cost)
    except ExpansionLimit as e:
        emit('graph_budget_termination',dict(reason=str(e)))
        n=cost.snapshot();n['wall_seconds']=None
        return dict(base,program=None,raw_drives=None,active_link_indices=[],effective_program_sha256=None,
            initial_state=None,first_margin_readout=None,ticks=[],convergence=None,final_state=None,raw_value=None,
            proof=None,support_checks=[],accepted=False,censored=True,termination='graph_budget',native_cost=n,
            adapter_cost=dict(initial_assignments=0,support_checks=0),events=events,wall_seconds=perf_counter()-started)
    initial={g.id:(spec.HIGH if policy['initial_mode']=='high' and g.id!='goal' else .5) for g in program.groups}
    drives={f'e:{i}':cfg.evidence_gain*(e.score or 0.0) for i,e in enumerate(obs.edges)};drives['goal']=0.0
    active=[i for i,l in enumerate(program.links) if policy['top_down'] or l.kind!='top_down']
    effective=io.digest(dict(program=plain(program),config=plain(cfg),raw_drives=drives,
        top_down=policy['top_down'],active_link_indices=active))
    emit('network',dict(program=plain(program),raw_drives=drives,active_link_indices=active,
        effective_program_sha256=effective,initial_state=initial))
    ticks=[];first=None
    def observe(i,state,residual,stable):
        nonlocal first
        row=dict(tick=i,state=deepcopy(state),residual=residual,stable_steps=stable);ticks.append(row);emit('tick',row)
        if first is None and abs(2*state['goal']-1)>=cfg.margin_threshold:
            first=dict(tick=i,value=state['goal']>=.5,goal=state['goal'],margin=abs(2*state['goal']-1),adopted=False)
            emit('first_margin_readout',first)
    state,cv=settle(program,drives,cfg,cost,top_down=policy['top_down'],initial=initial,observe=observe)
    value=state['goal']>=.5 if cv.status==Status.STABLE_DECISION else None
    emit('terminal_raw',dict(state=state,convergence=plain(cv),value=value))
    # Unmodified native reconstruction; the raw result is not replaced by a reachable-path oracle.
    proof=plain(reconstruct(obs,program,Binding(obs.digest,obs.revision,tuple(range(2))),state,value,cost))
    emit('proof_constructed',dict(proof=proof))
    accepted=value is not None and proof['final'] is not None and proof['under_assumptions_valid']
    checks=[]; lookup={e.id:e for e in obs.edges}
    if accepted:
        for eid,truth in proof['assumed_edges']:
            score=lookup[eid].score
            match=score is not None and score!=0 and (score>0) is truth
            checks.append(dict(edge_id=eid,assumed=truth,observation_score=score,supported=match))
            if not match:accepted=False;break
    emit('support_checked',dict(checks=checks))
    censored=cv.status==Status.BUDGET_EXHAUSTED
    termination='kernel_budget' if censored else 'adopted_supported' if accepted else 'unsupported_or_unsettled'
    emit('adoption',dict(value=value,accepted=bool(accepted),reason=termination))
    io.require(ob==observation,'observation was modified by execution')
    n=cost.snapshot();n['wall_seconds']=None
    return dict(base,program=plain(program),raw_drives=drives,active_link_indices=active,
        effective_program_sha256=effective,initial_state=initial,first_margin_readout=first,ticks=ticks,
        convergence=plain(cv),final_state=state,raw_value=value,proof=proof,support_checks=checks,
        accepted=bool(accepted),censored=censored,termination=termination,native_cost=n,
        adapter_cost=dict(initial_assignments=len(initial),support_checks=len(checks)),events=events,
        wall_seconds=perf_counter()-started)


def produce(plan,root):
    root=io.safe(root);cases={c['id']:c for c in plan['cases']};completed=0;current=None
    try:
        with (root/'attempts.jsonl').open('xb') as stream:
            for trial in plan['trials']:
                current=trial
                io.append(stream,dict(event='query_started',trial=trial))
                r=run_query(cases[trial['case']]['observation'],plan['kernel_config'],trial['arm'],
                    event_sink=lambda ev:io.append(stream,dict(event='query_event',trial_id=trial['id'],record=ev)))
                raw=dict(trial=trial,record=r);io.put(root/'raw'/(trial['id']+'.json'),raw);completed+=1
                io.append(stream,dict(event='query_completed',trial_id=trial['id'],raw_sha256=io.digest(raw)))
                print(f"Preserved: {completed}/{len(plan['trials'])} {trial['id']}",flush=True)
    except BaseException as e:
        io.failure(root,'native_execution',e)
        io.put(root/'partial_progress.json',dict(completed=completed,current=current,automatic_retry=False))
        raise
    return dict(queries=completed,automatic_retry=False,population=plan['population'])
