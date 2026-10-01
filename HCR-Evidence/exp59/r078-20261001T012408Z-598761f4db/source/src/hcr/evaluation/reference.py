"""외부 세계와 proof의 독립 판정. runtime/compiler/dynamics에서 import하지 않는다."""
from collections import Counter
from dataclasses import dataclass
from ..model import Observation,Decision,Proof,ContractError


@dataclass(frozen=True)
class Assessment:
    correct: bool | None
    proof_valid: bool
    assumption_correct: bool | None
    wrong_stable: bool
    actual_primitive_depth: int | None
    verification_checks: int
    error: str | None


def reachable(obs:Observation,truth:dict[str,bool], counter:list[int]|None=None) -> bool:
    if set(truth)!={e.id for e in obs.edges} or any(type(v) is not bool for v in truth.values()):
        raise ContractError('hidden state must cover exactly public edges')
    seen={obs.start};queue=[obs.start]
    while queue:
        node=queue.pop(0)
        for e in obs.edges:
            if counter is not None:counter[0]+=1
            if e.source==node and truth[e.id] and e.target not in seen:
                seen.add(e.target);queue.append(e.target)
    return obs.goal in seen


def public_paths(obs:Observation, counter:list[int]|None=None):
    paths=[];todo=[(obs.start,(obs.start,),())]
    while todo:
        node,visited,path=todo.pop()
        if node==obs.goal:paths.append(path);continue
        for edge in obs.edges:
            if counter is not None:counter[0]+=1
            if edge.source==node and edge.target not in visited:
                todo.append((edge.target,visited+(edge.target,),path+(edge.id,)))
    return set(paths)


def validate_proof(proof:Proof,obs:Observation,value:bool|None):
    checks=0
    if value is None:return False,None,checks,'abstention'
    byid={};depth={};facts={};claims={};edge_map={e.id:e for e in obs.edges}
    try:
        if not proof.nodes or not proof.final:raise ValueError('no proof')
        if len(set(proof.paths))!=len(proof.paths):raise ValueError('duplicate proof paths')
        for path in proof.paths:
            node=obs.start;visited={node}
            for eid in path:
                checks+=1;e=edge_map[eid]
                if e.source!=node or e.target in visited:raise ValueError('invalid path binding')
                node=e.target;visited.add(node)
            if node!=obs.goal:raise ValueError('path not to goal')
        for n in proof.nodes:
            checks+=1
            if n.id in byid or any(p not in byid for p in n.parents) or len(set(n.parents))!=len(n.parents):raise ValueError('node identity/parent order')
            byid[n.id]=n
            if n.rule in ('assumed_open','assumed_closed'):
                if n.parents or n.edge_id not in edge_map:raise ValueError('invalid assumption')
                val=n.rule=='assumed_open'
                if n.edge_id in facts and facts[n.edge_id]!=val:raise ValueError('contradictory assumptions')
                facts[n.edge_id]=val;claims[n.id]=('edge',n.edge_id,val);depth[n.id]=0
            else:
                depth[n.id]=1+max((depth[p] for p in n.parents),default=-1)
                if n.rule=='start_edge':
                    if len(n.parents)!=1:raise ValueError('start arity')
                    tag,eid,val=claims[n.parents[0]];e=edge_map[eid]
                    if tag!='edge' or not val or e.source!=obs.start:raise ValueError('bad start premise')
                    claims[n.id]=('path',(eid,))
                elif n.rule=='extend_path':
                    if len(n.parents)!=2:raise ValueError('extend arity')
                    tag,path=claims[n.parents[0]];tag2,eid,val=claims[n.parents[1]]
                    if tag!='path' or tag2!='edge' or not val or edge_map[path[-1]].target!=edge_map[eid].source:raise ValueError('bad direct premises')
                    claims[n.id]=('path',path+(eid,))
                elif n.rule=='path_blocked':
                    if len(n.parents)!=1 or type(n.path_index) is not int or not 0<=n.path_index<len(proof.paths):raise ValueError('cut arity/index')
                    tag,eid,val=claims[n.parents[0]]
                    if tag!='edge' or val or eid not in proof.paths[n.path_index]:raise ValueError('bad cut witness')
                    claims[n.id]=('cut',n.path_index)
                elif n.rule=='all_paths_blocked':
                    ids=[claims[x][1] for x in n.parents if claims[x][0]=='cut']
                    if len(ids)!=len(n.parents) or set(ids)!=set(range(len(proof.paths))) or len(ids)!=len(set(ids)):raise ValueError('missing path cut')
                    coverage_cost=[0]
                    all_paths=public_paths(obs,coverage_cost);checks+=coverage_cost[0]
                    if set(proof.paths)!=all_paths:raise ValueError('incomplete path coverage')
                    claims[n.id]=('unreachable',)
                else:raise ValueError('unregistered primitive')
        last=claims[proof.final]
        if value:
            if last[0]!='path' or last[1] not in proof.paths or edge_map[last[1][-1]].target!=obs.goal:raise ValueError('proof not reachable')
        elif last!=('unreachable',):raise ValueError('proof not unreachable')
        reached=set();stack=[proof.final]
        while stack:
            node=stack.pop()
            if node not in reached:reached.add(node);stack.extend(byid[node].parents)
        if reached!=set(byid):raise ValueError('unjustified extra proof nodes')
        if dict(proof.assumed_edges)!=facts or len(proof.assumed_edges)!=len(facts):raise ValueError('assumption registry')
        if depth[proof.final]!=proof.primitive_depth:raise ValueError('reported proof depth mismatch')
        return True,depth[proof.final],checks,None
    except (KeyError,ValueError,TypeError,IndexError) as error:
        return False,None,checks,str(error)


def assess(decision:Decision,obs:Observation,truth:dict[str,bool]) -> Assessment:
    if decision.observation_digest!=obs.digest:raise ContractError('assessing wrong observation')
    truth_cost=[0]
    actual=reachable(obs,truth,truth_cost)
    correct=None if decision.value is None else decision.value==actual
    valid,depth,checks,error=validate_proof(decision.proof,obs,decision.value)
    assumptions=None if not decision.proof.assumed_edges else all(truth[eid]==v for eid,v in decision.proof.assumed_edges)
    return Assessment(correct,valid,assumptions,decision.convergence.status.value=='stable_decision' and correct is False,
                      depth,checks+truth_cost[0],error)
