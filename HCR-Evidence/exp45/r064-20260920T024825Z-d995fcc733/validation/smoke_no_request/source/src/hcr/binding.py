"""회로 역할을 현재 대상에 결합한다. 이름·정답·관측 강도를 matching에 사용하지 않는다."""
from __future__ import annotations
from collections import Counter
from dataclasses import dataclass
from .model import Observation, Config, Cost, ContractError


@dataclass(frozen=True)
class Topology:
    vertices: int
    start: int
    goal: int
    edges: tuple[tuple[int,int], ...]

    @classmethod
    def from_observation(cls, obs: Observation) -> 'Topology':
        labels=[obs.start,obs.goal]
        for edge in obs.edges:
            for name in (edge.source,edge.target):
                if name not in labels: labels.append(name)
        index={name:i for i,name in enumerate(labels)}
        return cls(len(labels),0,1,tuple((index[e.source],index[e.target]) for e in obs.edges))

    def validate(self, config: Config) -> None:
        if type(self.vertices) is not int or not 2<=self.vertices<=config.max_edges+1 or self.start==self.goal:
            raise ContractError('topology vertex range')
        if not 0<=self.start<self.vertices or not 0<=self.goal<self.vertices:
            raise ContractError('topology endpoints')
        if not 1<=len(self.edges)<=config.max_edges or len(set(self.edges))!=len(self.edges):
            raise ContractError('topology edge count')
        if any(type(a) is not int or type(b) is not int or a==b or not 0<=a<self.vertices or not 0<=b<self.vertices for a,b in self.edges):
            raise ContractError('topology edge roles')


@dataclass(frozen=True)
class Binding:
    observation_digest: str
    revision: int
    edge_order: tuple[int, ...]  # template slot -> current observation edge position

    def check(self, obs: Observation) -> None:
        if self.observation_digest!=obs.digest or self.revision!=obs.revision:
            raise ContractError('stale observation binding')
        if len(self.edge_order)!=len(obs.edges) or set(self.edge_order)!=set(range(len(obs.edges))):
            raise ContractError('non-bijective binding')


def bind(topology: Topology, obs: Observation, config: Config, cost: Cost) -> Binding | None:
    topology.validate(config)
    current=Topology.from_observation(obs)
    if topology.vertices!=current.vertices or len(topology.edges)!=len(current.edges): return None
    left=set(topology.edges);right=set(current.edges)
    li,lo=Counter(b for a,b in left),Counter(a for a,b in left)
    ri,ro=Counter(b for a,b in right),Counter(a for a,b in right)
    candidates={x:[y for y in range(current.vertices) if (li[x],lo[x],x==topology.start,x==topology.goal)==(ri[y],ro[y],y==current.start,y==current.goal)] for x in range(topology.vertices)}
    order=sorted(candidates,key=lambda x:(len(candidates[x]),x))
    assigned={};used=set();checks=0
    def visit(i):
        nonlocal checks
        if i==len(order): return True
        x=order[i]
        for y in candidates[x]:
            checks+=1;cost.binding_checks+=1
            if checks>config.max_search: return False
            if y in used: continue
            if any(((x,u) in left)!=((y,v) in right) or ((u,x) in left)!=((v,y) in right) for u,v in assigned.items()): continue
            assigned[x]=y;used.add(y)
            if visit(i+1): return True
            del assigned[x];used.remove(y)
        return False
    if not visit(0): return None
    lookup={e:i for i,e in enumerate(current.edges)}
    edge_order=tuple(lookup[assigned[a],assigned[b]] for a,b in topology.edges)
    result=Binding(obs.digest,obs.revision,edge_order);result.check(obs)
    return result
