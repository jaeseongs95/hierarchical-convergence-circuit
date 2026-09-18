from copy import deepcopy
from r039_order_isolation import spec,input_audit
from r039_order_isolation.contracts import ARMS,SCOPES,USAGE_KEYS


def parent():
    return dict(name='three_branch_l3_early',observation=input_audit.canonical_observation(),worlds=input_audit.canonical_worlds())


def cases():return spec.make_cases(parent())


def view(obs,count=2):
    from r035_frozen_selection.selection import positive_proof
    slots={e['id']:i for i,e in enumerate(obs['edges'])}
    paths=[[slots[e] for e in p] for p in (('e2','e3'),('e0','e1'),('e4','e5','e6'))[:count]]
    state={f'e:{i}':(.01 if e['id']=='e4' else .8 if e['id']=='e2' else .99) for i,e in enumerate(obs['edges'])}
    state['goal']=.999
    for i,path in enumerate(paths):
        for j,_ in enumerate(path):state[f'p:{i}:{j}']=[.999,.99,.01][i]
    v=dict(schema='hcr-frozen-proof-view-r035-v1',observation=deepcopy(obs),raw_value=True,state=state,
        completed_paths=paths,graph_complete=count==3,min_abs_score=0.0,original_proof={})
    v['original_proof']=positive_proof(v,0)
    return v


def trajectory_fixture(case=None,count=2):
    from r035_frozen_selection.selection import run_policy
    from r038_early_adoption.metrics import opportunity
    case=case or cases()[0];obs=case['observation'];candidates=[];rows=[];events=[];routes=[]
    for i in range(count):
        v=view(obs,i+1);out=run_policy(v,'support_first')
        native=run_policy(v,'native_saved')
        path=v['completed_paths'][-1];ids=[obs['edges'][s]['id'] for s in path]
        vertices=[obs['start']]+[obs['edges'][s]['target'] for s in path]
        prefix=dict(path=path,visited=vertices);routes.append(prefix)
        events.append(dict(seq=i,event='r02_expansion',payload={'added':[prefix]}))
        row=dict(ordinal=i,kernel_ticks_at_readout=68+34*i,raw_value=True,native_accepted=native['accepted'],
            policy_accepted=out['accepted'],graph_complete=v['graph_complete'],native_assumptions=v['original_proof']['assumed_edges'],
            selected_assumptions=None if out['proof'] is None else out['proof']['assumed_edges'],
            native_D_DAG=2,D_DAG=None if out['proof'] is None else 2)
        row.update(opportunity(v,native['accepted'],3-(i+1)))
        rows.append(row);candidates.append({'view':v})
    remaining=3-count
    pending=dict(observation=obs,workspace=dict(routes=routes,frontier=[dict(path=[],visited=['s'])]*remaining))
    run={'base':dict(candidates=candidates,packet={'document':{'engine':{'pending':pending},'events':events}})}
    return run,dict(readouts=rows),case


def reporting_fixture():
    records=[]
    for ci,c in enumerate(cases()):
        for scope in SCOPES:
            for arm in ARMS:
                online=arm=='online_support';n=2 if online else 3;ticks=6 if online else 9;accepted=arm!='native'
                rows=[dict(native_view_sha256='v'+str(i),ordinal=i,supported_frontier_opportunity=i==1,
                    differential_opportunity=i==1) for i in range(n)]
                detail=[]
                for i in range(n):
                    detail.append(dict(ordinal=i,ticks=(i+1)*3,raw_value=True,native_accepted=False,policy_accepted=online and i==1,
                        native_D_DAG=2,policy_D_DAG=2 if online and i==1 else None,frontier_count=3-i-1,
                        differential_opportunity=i==1,completed_paths_edge_ids=[['e2','e3']]+([['e0','e1']] if i>0 else []),
                        supported_completed_edge_ids=[['e0','e1']] if i>0 else []))
                zeros={k:0 for k in USAGE_KEYS}
                records.append(dict(trial=dict(id=f't{len(records):04d}',case=c['name'],scope=scope,arm=arm),cohort='order_only',
                    native_event_semantic_hashes=['a','b','c'][:n],readouts=rows,
                    final=dict(accepted=accepted,value=True if accepted else None,reason='synthetic_fixture'),
                    classification='correct_in_all_declared_worlds' if accepted else 'abstained',
                    native_cost=dict(expansions=n,kernel_ticks=ticks,wall_seconds=0),
                    usage=dict(native_kernel_ticks=ticks,online_selection_calls=n,online_selection=zeros.copy(),
                               posthoc_selection_calls=int(arm=='posthoc_support'),posthoc_selection=zeros.copy()),
                    audit={'controller':{'native_advances':n}},native_finish_proof_nodes=n*4,
                    final_frontier_count=int(online),terminal_pending_ready=True,base_stop_reason='fixture',final_assumption_counts=None,
                    order_diagnostics=dict(branch_order=c['manipulation']['branch_order'],support_route_completion_rank=2,
                        first_supported_available_readout=dict(ordinal=1,ticks=6,frontier_count=1),
                        first_differential_readout=dict(ordinal=1,ticks=6,frontier_count=1),readouts=detail,
                        completion_trace=[dict(rank=j+1,path_edge_ids=p) for j,p in enumerate((['e2','e3'],['e0','e1'],['e4','e5','e6'])[:n])])))
    return records
