"""제어/로그 검산을 위한 합성 backend. hcr native를 흉내 낸 연구 결과로 사용하지 않는다."""
from copy import deepcopy
from r040_frontier_schedule.contracts import digest,USAGE_KEYS
OBS=dict(episode_id='r040-unit',revision=0,start='s',goal='g',edges=[
    dict(id='a',source='s',target='g',score=1.0),
    dict(id='b',source='s',target='m',score=1.0),
    dict(id='z',source='m',target='g',score=None)])
CONFIG={'kernel':{'max_ticks':5}};MEMORY={'circuits':[]}


class Session:
    def __init__(self,obs,config,memory,session_id):
        self.session_id=session_id;self.transitions=[];self.states={};self.support=False;self.calls=[]
        self._core=dict(config=deepcopy(config),memory=deepcopy(memory),pending=None,
            switches=dict(use_circuits=True,top_down=True,allow_reexpansion=True),held={},feedback={},requests={})
        self._append('init')
        self._core['pending']=dict(observation=deepcopy(obs),mode='frozen_eval',revision_of=None,
            ready=False,failure_reason=None,workspace=dict(frontier=[dict(path=[])],routes=[]),cost={'kernel_ticks':0})
        self._append('begin')

    def _append(self,operation,arguments=None):
        g=len(self.transitions);state=deepcopy(self._core)
        body=dict(operation=operation,arguments={} if arguments is None else arguments,after_state=digest(state))
        self.transitions.append(dict(body,sha256=digest([g,body])))
        self.states[g]=state

    @property
    def current(self): return deepcopy(self._core)
    @property
    def generation(self): return len(self.transitions)-1
    @property
    def phase(self): return 'readout_ready' if self._core['pending']['ready'] else 'running'
    @property
    def reference(self):
        t=self.transitions[-1]
        return dict(session_id=self.session_id,generation=self.generation,state_hash=t['after_state'],transition_hash=t['sha256'])
    def packet(self):
        d=dict(session_id=self.session_id,engine=self.current,transitions=deepcopy(self.transitions),events=[])
        return dict(schema='SYNTHETIC-CONTROLLER-TEST-NOT-NATIVE',document=d,sha256=digest(d))
    def advance(self):
        self.calls.append('advance');p=self._core['pending'];f=p['workspace']['frontier']
        head=f.pop(0)['path']
        if not head: f.extend([dict(path=[2]),dict(path=[0])])
        elif head==[0]: self.support=True
        p['cost']['kernel_ticks']+=3;p['ready']=True;self._append('advance')
    def continue_dependency(self):
        self.calls.append('continue_dependency');self._core['pending']['ready']=False;self._append('continue_dependency')
    def prioritize_frontier(self,path):
        p=self._core['pending'];assert not p['ready']
        f=p['workspace']['frontier'];i=next(i for i,r in enumerate(f) if r['path']==path)
        p['workspace']['frontier']=[f[i]]+f[:i]+f[i+1:]
        self.calls.append('prioritize_frontier');self._append('prioritize_frontier',dict(path=list(path)))
        return i


class Backend:
    kind='synthetic_controller_test'
    def __init__(self,*,selection_error=False,raw=True,selection_budget=False):
        self.selection_error=selection_error;self.raw=raw;self.selection_budget=selection_budget
        self.session=None;self.policies=[]
    def begin(self,observation,config,memory,scope,session_id):
        self.session=Session(observation,config,memory,session_id);return self.session
    def reservation(self,session): return session.current['config']['kernel']['max_ticks']
    def capture(self,session):
        value=self.raw;proof=dict(nodes=[{'id':'synthetic'}],final='synthetic',assumed_edges=[['a',True]])
        ref=dict(segment=0,generation=session.generation)
        view=dict(raw_value=value,native_accept=False,support_accept=session.support,
            original_proof=proof,observation=deepcopy(OBS),min_abs_score=0.0)
        return dict(candidate_id='synthetic-'+digest(ref),reference=ref,
            decision=dict(value=value,proof=proof,cost=session.current['pending']['cost']),
            readout=dict(value=None,accepted=False),synthetic_view=view)
    def project(self,candidate):return deepcopy(candidate['synthetic_view'])
    def select(self,view,policy,limits):
        if self.selection_error:raise RuntimeError('synthetic selector failure')
        self.policies.append(policy)
        accepted=policy=='support_first' and view['raw_value'] is True and view['support_accept'] and not self.selection_budget
        usage={k:0 for k in USAGE_KEYS};usage['proof_nodes_reused']=1
        return dict(policy=policy,input_sha256=digest(view),limits=limits,accepted=accepted,
            value=view['raw_value'] if accepted else None,
            reason='scan_budget' if self.selection_budget else 'supported' if accepted else 'no_supported_existing_path',
            proof=deepcopy(view['original_proof']),usage=usage,wall_seconds=0.0)


def fake_selector_audit(view,out):
    from r040_frontier_schedule.contracts import demand
    demand(out['input_sha256']==digest(view),'fake selector hash')
    return dict(verified=True,supported_assumptions=len(out['proof']['assumed_edges']),synthetic=True)


def core_for(view):
    return dict(pending=dict(ready=False,observation={'edges':[{'id':eid,'score':None} for eid in view['edge_ids']]},
                workspace={'frontier':[{'path':p} for p in view['frontier_paths']]}))
