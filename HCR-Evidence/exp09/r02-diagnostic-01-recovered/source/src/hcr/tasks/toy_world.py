"""작은 공개 관측 생성기. World의 hidden state는 평가 실행기에만 남는다."""
from dataclasses import dataclass,replace
from ..model import Observation,EdgeObservation,ObservationRequest,ContractError


@dataclass(frozen=True)
class World:
    observation: Observation
    hidden: tuple[tuple[str,bool], ...]

    def measure(self,request:ObservationRequest) -> Observation:
        obs=self.observation
        if request.episode_id!=obs.episode_id or request.revision!=obs.revision+1:raise ContractError('measurement scope')
        truth=dict(self.hidden)
        if not set(request.edge_ids)<=set(truth):raise ContractError('unknown measurement target')
        # 허용된 고정밀 측정이다. goal label/정답 graph를 반환하지 않는다.
        edges=tuple(replace(e,score=0.98 if truth[e.id] else -0.98) if e.id in request.edge_ids else e for e in obs.edges)
        return Observation(obs.episode_id,request.revision,obs.start,obs.goal,edges)


def chain(episode_id:str,values:tuple[bool,...]=(True,True),scores:tuple[float|None,...]|None=None,*,prefix:str='v') -> World:
    if not values or len(values)>4 or any(type(v) is not bool for v in values):raise ContractError('chain size/truth')
    if scores is None:scores=tuple(0.92 if v else -0.92 for v in values)
    if len(scores)!=len(values):raise ContractError('measurement count')
    edges=tuple(EdgeObservation(f'{prefix}-edge-{i}',f'{prefix}-{i}',f'{prefix}-{i+1}',score) for i,score in enumerate(scores))
    obs=Observation(episode_id,0,edges[0].source,edges[-1].target,edges)
    return World(obs,tuple((e.id,v) for e,v in zip(edges,values)))


def diamond(episode_id:str,values=(True,False,True,True),*,prefix='q') -> World:
    if len(values)!=4 or any(type(v) is not bool for v in values):raise ContractError('diamond truth requires four bools')
    arcs=((0,1),(1,3),(0,2),(2,3));edges=tuple(EdgeObservation(f'{prefix}e{i}',f'{prefix}{a}',f'{prefix}{b}',0.92 if val else -0.92) for i,((a,b),val) in enumerate(zip(arcs,values)))
    return World(Observation(episode_id,0,prefix+'0',prefix+'3',edges),tuple((e.id,v) for e,v in zip(edges,values)))
