"""Research-only exact fixed-point shortcut; original settle controller is unchanged."""
from dataclasses import asdict
from types import MappingProxyType
from hcr import dynamics
from hcr.model import Config,Cost,Group,Link,Program

NATIVE_TICK=dynamics.tick

def bits(state,ids):
    if set(state)!=set(ids) or any(type(state[k]) is not float for k in ids):
        raise ValueError('binary64 state contract')
    return tuple(state[k].hex() for k in ids)

class FixedTick:
    def __init__(self,program,drives,config,cost,top_down):
        self.program,self.drives,self.config,self.cost,self.top_down=program,drives,config,cost,top_down
        self.ids=tuple(g.id for g in program.groups)
        self.links=sum(e.kind!='top_down' or top_down for e in program.links)
        self.fixed=None;self.native_calls=0;self.skipped_calls=0;self.detection_checks=0

    def __call__(self,program,current,drives,config,cost,*,top_down=True):
        if not(program is self.program and drives is self.drives and config is self.config and cost is self.cost and top_down is self.top_down):
            raise ValueError('settle binding')
        if self.fixed is not None:
            if bits(current,self.ids)!=self.fixed:raise ValueError('fixed state mutation')
            self.skipped_calls+=1
            cost.kernel_ticks+=1;cost.group_updates+=len(self.ids);cost.normalization_ops+=len(self.ids);cost.signal_transmissions+=self.links
            return dict(current)
        self.native_calls+=1
        nxt=NATIVE_TICK(program,current,drives,config,cost,top_down=top_down)
        self.detection_checks+=1
        if bits(current,self.ids)==bits(nxt,self.ids):self.fixed=bits(nxt,self.ids)
        return nxt

def invoke(kernel,kernel_config,arm,*,keep_trace=True):
    """Owns all mutable inputs/observer; no arbitrary callback or shared cache API."""
    p=kernel['program'];program=Program(tuple(Group(**g) for g in p['groups']),tuple(Link(**e) for e in p['links']),tuple(tuple(path) for path in p['paths']),p['edge_count'])
    config=Config(**kernel_config);drives=MappingProxyType(dict(kernel['drives']));cost=Cost();ticks=[]
    observer=(lambda n,s,r,k:ticks.append(dict(tick=n,state=dict(s),residual=r,stable_steps=k))) if keep_trace else (lambda n,s,r,k:None)
    if arm not in ('baseline','fixed_point'):raise ValueError('arm')
    if dynamics.tick is not NATIVE_TICK:raise ValueError('single worker tick ownership')
    shortcut=FixedTick(program,drives,config,cost,True) if arm=='fixed_point' else None
    try:
        if shortcut is not None:dynamics.tick=shortcut
        state,conv=dynamics.settle(program,drives,config,cost,top_down=True,initial=dict(kernel['initial']),observe=observer)
    finally:dynamics.tick=NATIVE_TICK
    c=asdict(conv);c['status']=conv.status.value
    record=dict(program=p,program_sha256=program.digest,drives=dict(drives),initial=dict(kernel['initial']),ticks=ticks,state=state,convergence=c,cost=cost.snapshot(),adopted=None if c['status']!='stable_decision' else state['goal']>=.5)
    native=cost.kernel_ticks if shortcut is None else shortcut.native_calls
    skipped=0 if shortcut is None else shortcut.skipped_calls
    physical=dict(native_tick_calls=native,skipped_tick_arithmetic=skipped,logical_ticks=cost.kernel_ticks,
        physical_group_updates=native*len(program.groups),physical_signal_transmissions=native*len(program.links),
        omitted_group_updates=skipped*len(program.groups),omitted_signal_transmissions=skipped*len(program.links),
        detection_checks=0 if shortcut is None else shortcut.detection_checks)
    return dict(record=record,physical=physical)
