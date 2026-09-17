"""기존 합성 session을 재사용하는 self-test 장치. native 모델이 아니다."""
import importlib.util
from pathlib import Path
from copy import deepcopy

path = Path(__file__).resolve().parents[2]/'r037_online_selection/tests/helpers.py'
spec = importlib.util.spec_from_file_location('_r037_fake_for_r038',path)
parent = importlib.util.module_from_spec(spec); spec.loader.exec_module(parent)
OBS,CONFIG,MEMORY = parent.OBS,parent.CONFIG,parent.MEMORY


class FakeBackend(parent.FakeBackend):
    def select(self,view,policy,limits):
        result = super().select(view,policy,limits)
        result['wall_seconds'] = 0.0  # 합성 fixture의 명시적 시간. 실제 측정값이 아니다.
        return result

    def capture(self,session):
        c = super().capture(session)
        c['synthetic_view'].update(observation=deepcopy(OBS),min_abs_score=0.0)
        c['decision']['proof']['assumed_edges'] = [['e0',True]]
        c['synthetic_view']['original_proof'] = deepcopy(c['decision']['proof'])
        return c


def fake_audit(view,output):
    # wrapper binding만 검사하기 위한 stub. 실제 proof 독립 검증으로 보고하지 않는다.
    from r038_early_adoption.contracts import demand,digest
    demand(output['input_sha256'] == digest(view),'synthetic input hash')
    demand(output['value'] is (view['raw_value'] if output['accepted'] else None),'synthetic value')
    return dict(verified=True,supported_assumptions=len(output['proof']['assumed_edges']),
                synthetic_audit_stub=True)


def frames(frontier_on_support=True):
    return [dict(native=False,support=False,frontier=True),
            dict(native=False,support=True,frontier=frontier_on_support),
            dict(native=False,support=True,frontier=False)]


def graph_view(complete_count=2,frontier=False):
    obs = dict(episode_id='r038-selector-selftest',revision=0,start='s',goal='g',edges=[
        dict(id='e0',source='s',target='a',score=1.0),dict(id='e1',source='a',target='g',score=1.0),
        dict(id='e2',source='s',target='b',score=None),dict(id='e3',source='b',target='g',score=1.0),
        dict(id='e4',source='s',target='c',score=-1.0),dict(id='e5',source='c',target='g',score=1.0)])
    paths = [[2,3],[0,1],[4,5]][:complete_count]
    state = {'goal':.99,**{f'e:{i}':.9 if i != 4 else .1 for i in range(6)}}
    for pi,path in enumerate(paths):
        for j in range(len(path)): state[f'p:{pi}:{j}'] = [.99,.9,.1][pi]
    proof = dict(nodes=[
        dict(id='f2',rule='assumed_open',edge_id='e2',parents=[],path_index=None),
        dict(id='r0',rule='start_edge',edge_id=None,parents=['f2'],path_index=0),
        dict(id='f3',rule='assumed_open',edge_id='e3',parents=[],path_index=None),
        dict(id='r1',rule='extend_path',edge_id=None,parents=['r0','f3'],path_index=0)],
        final='r1',primitive_depth=2,assumed_edges=[['e2',True],['e3',True]],under_assumptions_valid=True,
        paths=[[obs['edges'][s]['id'] for s in p] for p in paths])
    return dict(schema='hcr-frozen-proof-view-r035-v1',observation=obs,raw_value=True,state=state,
                completed_paths=paths,graph_complete=not frontier,original_proof=proof,min_abs_score=0.0)
