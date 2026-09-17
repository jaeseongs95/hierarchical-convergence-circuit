"""단위시험 전용 synthetic 상태/가짜 실행 adapter. native 연구 결과가 아니다."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tools')]
from copy import deepcopy
from r035_frozen_selection.contracts import digest
from r035_frozen_selection.selection import run_policy
from unittest.mock import patch


def observation():
    return dict(episode_id='synthetic-r036',revision=0,start='s',goal='g',edges=[
        dict(id='e0',source='s',target='a',score=.92),dict(id='e1',source='a',target='g',score=.92),
        dict(id='e2',source='s',target='b',score=None),dict(id='e3',source='b',target='g',score=.92)])


def proof(obs,paths,pi):
    nodes=[];before=None
    for j,s in enumerate(paths[pi]):
        fid=f'f:{s}:1';rid=f'r:{pi}:{j}'
        nodes += [dict(id=fid,rule='assumed_open',edge_id=obs['edges'][s]['id'],parents=[],path_index=None),
            dict(id=rid,rule='start_edge' if j==0 else 'extend_path',edge_id=None,
                parents=[fid] if j==0 else [before,fid],path_index=pi)]
        before=rid
    return dict(nodes=nodes,final=before,primitive_depth=len(paths[pi]),
        assumed_edges=sorted([[obs['edges'][s]['id'],True] for s in paths[pi]]),under_assumptions_valid=True,
        paths=[[obs['edges'][s]['id'] for s in p] for p in paths])


def view(expanded=True,raw=True):
    obs=observation();paths=[[2,3],[0,1]] if expanded else [[2,3]]
    state={f'e:{i}':(.707 if i==2 else .9997) for i in range(4)};state['goal']=.9999
    for i,p in enumerate(paths):
        for j,_ in enumerate(p):state[f'p:{i}:{j}']=.9996 if i==0 else .9939
    return dict(schema='hcr-frozen-proof-view-r035-v1',observation=obs,raw_value=raw,state=state,
        completed_paths=paths,graph_complete=expanded,original_proof=proof(obs,paths,0),min_abs_score=0.)


def mock_rebuild(v):
    """제어/입출력 시험용 대역. 실제 hcr.proof.reconstruct의 통합시험을 대신하지 않는다."""
    raw=deepcopy(v['original_proof']);return raw,len(raw['nodes'])


def results(v):
    with patch('r035_frozen_selection.native_bridge.rebuild',side_effect=mock_rebuild):
        return {p:run_policy(v,p) for p in ('native_saved','native_rebuild','support_first')}


def candidate(v):
    d=dict(id='synthetic',episode_id=v['observation']['episode_id'],observation_digest=digest(v['observation']),
        observation_revision=v['observation']['revision'],expanded_paths=deepcopy(v['completed_paths']),
        graph_complete=v['graph_complete'],state=sorted(v['state'].items()),value=v['raw_value'],
        proof=deepcopy(v['original_proof']),cost=dict(kernel_ticks=102),convergence={'status':'synthetic'})
    program=dict(paths=deepcopy(v['completed_paths']));d['program_digest']=digest(program)
    events=[dict(event='r02_attempt_started',payload=dict(decision_id=d['id'],observation=deepcopy(v['observation']))),
        dict(event='r02_proposals',payload=dict(decision_id=d['id'],prefix=dict(path=[]),candidates=[dict(edges=[0,1]),dict(edges=[2,3]),dict(edges=[0])])),
        dict(event='r02_network',payload=dict(kind='decision',decision_id=d['id'],program=program,program_digest=digest(program),metadata=dict(routes=[dict(path=p) for p in v['completed_paths']]))),
        dict(event='r02_decision',payload=d)]
    document=dict(events=events);packet=dict(document=document,sha256=digest(document))
    ref=dict(segment=0,generation=2,ready_sha256='1'*64,finished_sha256=packet['sha256'])
    res=run_policy(v,'native_saved')
    return dict(candidate_id='review-candidate-'+digest(ref),reference=ref,packet=packet,decision=d,
        diagnostic=dict(source=dict(decision_sha256=digest(d)),contract=dict(min_abs_score=0.)),
        readout=dict(value=res['value'],accepted=res['accepted']))
