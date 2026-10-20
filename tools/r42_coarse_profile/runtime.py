"""Process-local, reversible observation of the unchanged R40 q4 path."""
import time
from hcr import codec,dynamics
from hcr.model import Cost,Program,fingerprint
from tools.r32_semantic_join.runtime import export,require
from tools.r33_typed_feedback.runtime import program
import tools.r37_joint_tuple.runtime as membership_runtime
import tools.r39_z_query.runtime as gate_runtime
import tools.r40_factor_query.runtime as original

LABELS=['core','source_export_guard','contract_validate','document_build','producer','membership','encode_role','consumer','kernel','program_build','settle','result_materialize']
_active=False

class Observer:
    # ponytail: one sequential research process; no concurrent patching is supported.
    def __init__(self):self.events={};self.stack=[];self.saved=[];self.restored=False
    def call(self,label,fn,*args,**kwargs):
        started=time.process_time_ns();frame=[label,0];self.stack.append(frame)
        try:return fn(*args,**kwargs)
        finally:
            elapsed=time.process_time_ns()-started;require(self.stack.pop() is frame,'nested timer stack');require(elapsed>=frame[1]>=0,'exclusive CPU accounting');row=self.events.setdefault(label,dict(calls=0,inclusive_ns=0,exclusive_ns=0));row['calls']+=1;row['inclusive_ns']+=elapsed;row['exclusive_ns']+=elapsed-frame[1]
            if self.stack:self.stack[-1][1]+=elapsed
    def bind(self,obj,name,value):self.saved.append((obj,name,getattr(obj,name)));setattr(obj,name,value)
    def __enter__(self):
        global _active
        require(not _active,'single active observer');_active=True
        try:
            for obj,name,label in [(original,'validate','contract_validate'),(original,'documents','document_build'),(original,'produce','producer'),(original,'membership','membership'),(original,'consume','consumer'),(membership_runtime,'encode_role','encode_role')]:
                old=getattr(obj,name)
                def wrapped(*args,_old=old,_label=label,**kwargs):return self.call(_label,_old,*args,**kwargs)
                self.bind(obj,name,wrapped)
            for obj in [original,membership_runtime,gate_runtime]:self.bind(obj,'kernel',self.kernel)
        except BaseException:self.restore();raise
        return self
    def restore(self):
        global _active
        for obj,name,value in reversed(self.saved):setattr(obj,name,value)
        self.restored=all(getattr(obj,name) is value for obj,name,value in self.saved);_active=False;require(self.restored,'restore exact prior bindings')
    def __exit__(self,*args):self.restore()
    def kernel(self,doc,drives,cfg,initial):return self.call('kernel',self._kernel,doc,drives,cfg,initial)
    def _kernel(self,doc,drives,cfg,initial):
        pr=self.call('program_build',program,doc);cost=Cost(dynamic_groups_created=len(pr.groups),dynamic_links_created=len(pr.links));ticks=[];start={g.id:initial for g in pr.groups}
        state,conv=self.call('settle',dynamics.settle,pr,drives,cfg,cost,initial=start,observe=lambda i,s,r,k:ticks.append(dict(tick=i,state=dict(s),residual=r,stable_steps=k)))
        return self.call('result_materialize',self._materialize,pr,drives,start,ticks,state,conv,cost)
    @staticmethod
    def _materialize(pr,drives,start,ticks,state,conv,cost):
        return dict(program=codec.plain(pr),program_sha256=pr.digest,drives=drives,initial=start,ticks=ticks,state=state,convergence=codec.plain(conv),cost=cost.snapshot(),adopted=state['goal']>=.5 if conv.status.value=='stable_decision' else None)
    def snapshot(self):
        require(self.restored and not self.stack and not _active and set(self.events)<=set(LABELS),'closed observer')
        return dict(events={k:dict(v) for k,v in self.events.items()},restored_bindings=len(self.saved),restored=True,clock='process_time_ns')

def source_packets(c,sources):
    needed=sum(c['relations'].values(),[]);packets={k:export(sources[k]) for k in needed};require(all(packets[k]['origin_sha256']==fingerprint(sources[k]) for k in packets),'source export guard');return packets

def run(c,w,arm,mode,p,sources):
    require(mode in ['plain','profiled'],'mode');started=time.process_time_ns()
    def execute(observer=None):
        packets=source_packets(c,sources) if observer is None else observer.call('source_export_guard',source_packets,c,sources)
        return original.execute(c['domains'],{n:[packets[k] for k in keys] for n,keys in c['relations'].items()},c['vocabulary'],c['order'],w['queries'],arm,p['kernel'],c['initial'])
    if mode=='plain':r=execute();profile=None
    else:
        observer=Observer()
        with observer:r=observer.call('core',execute,observer)
        profile=observer.snapshot()
    elapsed=time.process_time_ns()-started
    if profile is not None:profile.update(observed_core_ns=elapsed,support_ns=elapsed-profile['events']['core']['inclusive_ns']);require(profile['support_ns']>=0,'profile setup/restoration accounting')
    return r,dict(core_cpu_ns=elapsed,profile=profile)

def comparable(r):
    return {k:v for k,v in r.items() if k not in ['mode','prefix_core_cpu_seconds','query_core_cpu_seconds']}
