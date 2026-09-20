"""실행 후 현재 상태를 primitive 증명으로 복원한다. 복원 비용과 실행 비용은 분리한다."""
from .model import Observation, Program, Proof, ProofNode, Cost
from .binding import Binding


def reconstruct(obs:Observation,program:Program,binding:Binding,state:dict[str,float],value:bool|None,cost:Cost) -> Proof:
    if value is None:return Proof((),None,None,(),False)
    binding.check(obs);paths=tuple(tuple(obs.edges[binding.edge_order[i]].id for i in p) for p in program.paths);nodes=[];assumed={};depth={}
    def feature(slot, truth):
        edge=obs.edges[binding.edge_order[slot]]
        if (state['e:'+str(slot)]>=0.5)!=truth:return None
        key=f'f:{slot}:{int(truth)}'
        if key not in depth:
            nodes.append(ProofNode(key,'assumed_open' if truth else 'assumed_closed',edge.id,()))
            depth[key]=0;assumed[edge.id]=truth;cost.proof_nodes_reconstructed+=1
        return key
    def add(key,rule,parents,path_index=None):
        nodes.append(ProofNode(key,rule,None,tuple(parents),path_index));cost.proof_nodes_reconstructed+=1
        depth[key]=1+max(depth[x] for x in parents);return key
    final=None
    if value:
        order=sorted(range(len(program.paths)),key=lambda i:(-state[f'p:{i}:{len(program.paths[i])-1}'],i))
        for pi in order:
            path=program.paths[pi]
            if not all(state['e:'+str(slot)]>=0.5 for slot in path):continue
            prev=None
            for j,slot in enumerate(path):
                f=feature(slot,True)
                prev=add(f'r:{pi}:{j}','start_edge' if prev is None else 'extend_path',[f] if prev is None else [prev,f],pi)
            final=prev
            break
    else:
        cuts=[]
        for pi,path in enumerate(program.paths):
            choices=[slot for slot in path if state['e:'+str(slot)]<0.5]
            if not choices:return Proof(tuple(nodes),None,None,tuple(sorted(assumed.items())),False,paths)
            slot=min(choices,key=lambda i:(state['e:'+str(i)],i));f=feature(slot,False)
            cuts.append(add('cut:'+str(pi),'path_blocked',[f],pi))
        final=add('conclusion','all_paths_blocked',cuts)
    return Proof(tuple(nodes),final,depth.get(final),tuple(sorted(assumed.items())),final is not None,paths)
