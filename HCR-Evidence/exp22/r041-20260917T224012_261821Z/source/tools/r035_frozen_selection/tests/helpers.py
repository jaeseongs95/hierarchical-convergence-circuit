"""테스트 전용 synthetic 입력. 실제 EXP-15/EXP-16의 관찰 결과로 세지 않는다."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'tools'))
from copy import deepcopy
from r035_frozen_selection.native_bridge import rebuild
from r035_frozen_selection.contracts import digest
from r035_frozen_selection.selection import gate


def empty_proof():
    return dict(nodes=[],final=None,primitive_depth=None,assumed_edges=[],under_assumptions_valid=False,paths=[])


def make_view(*,raw=True,expanded=True,complete=True,score=None):
    edges=[dict(id='e0',source='s',target='a',score=.92),dict(id='e1',source='a',target='g',score=.92),
           dict(id='e2',source='s',target='b',score=score),dict(id='e3',source='b',target='g',score=.92)]
    paths=[[2,3],[0,1]] if expanded else [[2,3]]
    state={'e:0':.9997,'e:1':.9997,'e:2':.707,'e:3':.9998,'goal':.9999}
    for pi,p in enumerate(paths):
        for j in range(len(p)):state[f'p:{pi}:{j}']=.9996 if pi==0 else .9939
    v=dict(schema='hcr-frozen-proof-view-r035-v1',observation=dict(episode_id='synthetic-only',revision=0,start='s',goal='g',edges=edges),
        raw_value=raw,state=state,completed_paths=paths,graph_complete=complete,original_proof=empty_proof(),min_abs_score=0.)
    v['original_proof']=rebuild(v)[0]
    return v


def negative_view(*,complete=True):
    v=make_view(raw=None,complete=complete)
    v['state']['e:0']=.1;v['state']['e:2']=.15
    v['observation']['edges'][0]['score']=-.06;v['observation']['edges'][2]['score']=-.98
    v['raw_value']=False;v['original_proof']=rebuild(v)[0]
    return v


def native_candidate(v):
    """projector 계약용 가짜 계보. native recurrence 검산 fixture가 아니다."""
    d=dict(id='synthetic-decision',episode_id=v['observation']['episode_id'],observation_revision=v['observation']['revision'],
        observation_digest=digest(v['observation']),state=sorted(v['state'].items()),value=v['raw_value'],
        expanded_paths=deepcopy(v['completed_paths']),graph_complete=v['graph_complete'],proof=deepcopy(v['original_proof']),
        cost=dict(kernel_ticks=123))
    program=dict(paths=deepcopy(v['completed_paths']))
    d['program_digest']=digest(program)
    events=[dict(event='r02_attempt_started',payload=dict(decision_id=d['id'],observation=deepcopy(v['observation']))),
        dict(event='r02_network',payload=dict(decision_id=d['id'],kind='decision',program=program,program_digest=digest(program),
            metadata=dict(routes=[dict(path=deepcopy(p)) for p in v['completed_paths']]))),dict(event='r02_decision',payload=d)]
    doc=dict(events=events);packet=dict(document=doc,sha256=digest(doc))
    ref=dict(segment=0,generation=2,ready_sha256='1'*64,finished_sha256=packet['sha256'])
    accepted,_=gate(v,v['original_proof'])
    return dict(candidate_id='review-candidate-'+digest(ref),reference=ref,packet=packet,decision=d,
        diagnostic=dict(source=dict(decision_sha256=digest(d)),contract=dict(min_abs_score=v['min_abs_score'])),
        readout=dict(accepted=accepted,value=v['raw_value'] if accepted else None))
