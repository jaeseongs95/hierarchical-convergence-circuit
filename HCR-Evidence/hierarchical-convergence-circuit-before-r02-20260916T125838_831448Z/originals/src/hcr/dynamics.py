"""모든 A 수준에 동일한 동기 갱신. correctness·world·learning을 읽지 않는다."""
from __future__ import annotations
from math import exp, isfinite
from .model import Config, Program, Cost, Convergence, Status, ContractError


def tick(program: Program, current: dict[str,float], drives: dict[str,float], config: Config,
         cost: Cost, *, top_down: bool=True) -> dict[str,float]:
    ids={g.id for g in program.groups}
    if set(current)!=ids or not set(drives)<=ids:
        raise ContractError('state/drive identity mismatch')
    if any(not isfinite(v) or not 0 <= v <= 1 for v in current.values()) or any(not isfinite(v) for v in drives.values()):
        raise ContractError('nonfinite/out of range state')
    totals={g.id:g.bias+drives.get(g.id,0.0) for g in program.groups}
    for edge in program.links:
        if edge.kind=='top_down' and not top_down: continue
        totals[edge.target]+=edge.weight*(2*current[edge.source]-1)
        cost.signal_transmissions+=1
    nxt={}
    for g in program.groups:
        p=current[g.id];drive=totals[g.id]
        positive=drive+config.self_excitation*p-config.inhibition*(1-p)
        negative=-drive+config.self_excitation*(1-p)-config.inhibition*p
        z=(positive-negative)/config.temperature
        target=1/(1+exp(-z)) if z>=0 else exp(z)/(1+exp(z))
        nxt[g.id]=(1-config.damping)*p+config.damping*target
        cost.group_updates+=1;cost.normalization_ops+=1
    cost.kernel_ticks+=1
    return nxt


def settle(program: Program, drives: dict[str,float], config: Config, cost: Cost, *,
           top_down: bool=True, initial: dict[str,float] | None=None, observe=None):
    program.validate(config)
    state={g.id:0.5 for g in program.groups} if initial is None else dict(initial)
    history=[];stable=0;residual=1.0
    for i in range(1,config.max_ticks+1):
        nxt=tick(program,state,drives,config,cost,top_down=top_down)
        residual=max(abs(nxt[k]-state[k]) for k in state)
        stable=stable+1 if residual<=config.residual_tolerance else 0
        if observe is not None: observe(i,nxt,residual,stable)
        margin=abs(2*nxt['goal']-1)
        if stable>=config.patience:
            status=Status.STABLE_DECISION if margin>=config.margin_threshold else Status.STABLE_AMBIGUOUS
            return nxt,Convergence(status,i,residual,margin,stable)
        if len(history)>=1 and residual>config.residual_tolerance*10 and max(abs(nxt[k]-history[-1][k]) for k in nxt)<config.residual_tolerance:
            return nxt,Convergence(Status.OSCILLATING,i,residual,margin,stable)
        history.append(state);history=history[-3:];state=nxt
    return state,Convergence(Status.BUDGET_EXHAUSTED,config.max_ticks,residual,abs(2*state['goal']-1),stable)
