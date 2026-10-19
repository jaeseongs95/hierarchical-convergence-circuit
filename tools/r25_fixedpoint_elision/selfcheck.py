"""Pure boundary checks only. Does not run archived kernels or timing locally."""
from dataclasses import replace,asdict
from types import MappingProxyType
from hcr.model import Config,Cost,Program,Group
from tools.r25_fixedpoint_elision import shortcut as s

def check():
    count=0
    def require(ok,msg):
        nonlocal count
        if not ok:raise ValueError(msg)
        count+=1
    def reject(call,msg):
        try:call()
        except ValueError as exc:require(str(exc)==msg,'cause '+str(exc))
        else:raise ValueError('accepted '+msg)
    p=Program((Group('goal',1),),(),((0,),),1);d=MappingProxyType(dict(goal=0.));c=Config();cost=Cost()
    require(s.bits(dict(goal=0.),('goal',))!=s.bits(dict(goal=-0.),('goal',)),'signed zero')
    require(s.bits(dict(goal=.5),('goal',))!=s.bits(dict(goal=.5000000000000001),('goal',)),'near float')
    reject(lambda:s.bits(dict(goal=1),('goal',)),'binary64 state contract')
    reject(lambda:s.bits(dict(other=.5),('goal',)),'binary64 state contract')
    original=s.NATIVE_TICK
    try:
        calls=[]
        def identity(pr,state,dr,cf,co,*,top_down):
            calls.append(1);co.kernel_ticks+=1;co.group_updates+=1;co.normalization_ops+=1;return dict(state)
        s.NATIVE_TICK=identity;t=s.FixedTick(p,d,c,cost,True)
        a=t(p,dict(goal=.5),d,c,cost);b=t(p,a,d,c,cost)
        require(a==b and a is not b,'fresh copied result');require(len(calls)==1 and t.native_calls==1 and t.skipped_calls==1,'actual omission')
        require(cost.kernel_ticks==2 and cost.group_updates==2 and cost.normalization_ops==2,'logical costs')
        reject(lambda:t(p,dict(goal=.6),d,c,cost),'fixed state mutation')
        for args in [(replace(p),d,c,cost,True),(p,MappingProxyType(dict(d)),c,cost,True),(p,d,replace(c),cost,True),(p,d,c,Cost(),True),(p,d,c,cost,False)]:
            pr,dr,cf,co,td=args;reject(lambda:t(pr,dict(goal=.5),dr,cf,co,top_down=td),'settle binding')
        cold=s.FixedTick(p,d,c,Cost(),True);require(cold.fixed is None and cold.skipped_calls==0,'cold invocation')
        def near(pr,state,dr,cf,co,*,top_down):return dict(goal=.5000000000000001)
        s.NATIVE_TICK=near;t=s.FixedTick(p,d,c,Cost(),True);t(p,dict(goal=.5),d,c,t.cost);require(t.fixed is None,'no approximate latch')
        def broken(*args,**kwargs):raise RuntimeError('synthetic failure')
        s.NATIVE_TICK=broken;s.dynamics.tick=broken
        kernel=dict(program=asdict(p),drives=dict(d),initial=dict(goal=.5))
        try:s.invoke(kernel,asdict(c),'fixed_point')
        except RuntimeError as exc:require(str(exc)=='synthetic failure','synthetic error')
        else:raise ValueError('expected failure')
        require(s.dynamics.tick is broken,'restore after failure')
    finally:s.NATIVE_TICK=original;s.dynamics.tick=original
    require(s.dynamics.tick is original,'global tick restored')
    return dict(status='PURE_BOUNDARIES_PASSED',assertions=count,archived_native_work=0,timing_work=0,synthetic_tick_stubs_only=True)
