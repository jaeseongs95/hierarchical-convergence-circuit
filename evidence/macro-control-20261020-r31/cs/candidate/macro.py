"""Source-derived bounded native matching, conventional positive-evidence applicability.

The stored certificate/path representation is deliberately shared. This control tests
execution policy, not an independent learning algorithm or a new theory of learning.
"""
from hcr.activation import CircuitActivation
from hcr.codec import plain
from hcr.identity import bind_path

class OrdinaryMacroPool:
    def __init__(self,config,memory,*,top_down=True):
        self.config,self.memory=config,memory

    def activate_candidates(self,workspace,budget):
        prefix,obs,cost=workspace.frontier[0],workspace.observation,workspace.cost
        inspected,scans,matches=[],[],[];reason=None
        for circuit in sorted(self.memory.circuits,key=lambda c:(c.pattern.length,c.id)):
            inspected.append(circuit.id);cost.recall_checks+=1
            if not circuit.active or len(prefix.path)+circuit.pattern.length>self.config.kernel.max_path_length:continue
            todo=[(prefix.end,prefix.visited,())]
            while todo and reason is None:
                vertex,visited,slots=todo.pop()
                if len(slots)==circuit.pattern.length:
                    matches.append((circuit,bind_path(obs,circuit.id,slots)));cost.candidate_circuits+=1
                    if len(matches)>self.config.max_pool_candidates:reason='pool_capacity'
                    continue
                if vertex==obs.goal:continue
                children=[]
                for i,edge in enumerate(obs.edges):
                    if len(scans)>=budget.remaining_binding_checks:reason='binding_budget';break
                    scans.append([circuit.id,list(slots),i]);cost.binding_checks+=1;cost.binding_operations+=1
                    if edge.source==vertex and edge.target not in visited:
                        children.append((edge.target,visited+(edge.target,),slots+(i,)))
                todo.extend(reversed(children))
            if reason is not None:break
        workspace.trace.emit('r02_binding_scan',dict(decision_id=workspace.decision_id,prefix=plain(prefix),inspected=inspected,
            scans=scans,matched=[dict(circuit_id=c.id,binding=plain(b)) for c,b in matches],complete=reason is None,fallback_reason=reason))
        if reason is not None or not matches:return ()
        # Common candidate-group allowance: no numeric pool is constructed here.
        groups=len(obs.edges)+1+sum(len(c.pattern.program.groups)-c.pattern.length for c,_ in matches)
        if groups>self.config.kernel.max_groups:
            workspace.trace.emit('r02_pool_unavailable',dict(decision_id=workspace.decision_id,reason='common_kernel_group_budget'));return ()
        result=[];score_checks=0
        for c,b in matches:
            scores=[obs.edges[i].score for i in b.edge_order];score_checks+=len(scores)
            eligible=all(s is not None and s>0 for s in scores)
            # Constant ranking, not a numeric confidence estimate or readout.
            result.append(CircuitActivation(c.id,b,1.0,0.0,0.0,c.version,eligible))
        workspace.trace.emit('r31_macro_result',dict(decision_id=workspace.decision_id,activations=plain(result),score_checks=score_checks,group_allowance_checked=groups))
        return tuple(result)
