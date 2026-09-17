"""단위 테스트 전용 synthetic session. 실제 native 엔진이나 연구 결과가 아니다."""
from copy import deepcopy
from r037_online_selection.contracts import digest, USAGE_KEYS

OBS = dict(episode_id='unit', revision=0, start='s', goal='g',
           edges=[dict(id='e0', source='s', target='g', score=1.0)])
CONFIG = {'kernel': {'max_ticks': 5}}
MEMORY = {'circuits': []}


class FakeSession:
    def __init__(self, obs, config, memory, session_id, frames, begin_ready=False):
        self.frames = deepcopy(frames); self.calls = []; self.frame = {}
        self.session_id = session_id; self.states = {}; self.transitions = []
        self._current = dict(memory=deepcopy(memory), config=deepcopy(config),
            switches=dict(use_circuits=True, top_down=True, allow_reexpansion=True),
            held={}, feedback={}, requests={}, pending=None)
        self._append('init')
        self._current['pending'] = dict(observation=deepcopy(obs), mode='frozen_eval', revision_of=None,
            ready=begin_ready, failure_reason=None, workspace={'frontier':[0]}, cost={'kernel_ticks':0})
        self._append('begin')

    def _append(self, operation):
        g = len(self.transitions); state = deepcopy(self._current)
        body = dict(operation=operation, after_state=digest(state))
        self.transitions.append(dict(body, sha256=digest([g,body])))
        self.states[g] = state

    @property
    def current(self):
        return deepcopy(self._current)

    @property
    def phase(self):
        return 'readout_ready' if self._current['pending']['ready'] else 'running'

    @property
    def generation(self):
        return len(self.transitions)-1

    @property
    def reference(self):
        t = self.transitions[-1]
        return dict(session_id=self.session_id, generation=self.generation,
                    state_hash=t['after_state'], transition_hash=t['sha256'])

    def packet(self):
        doc = dict(session_id=self.session_id, engine=self.current, transitions=deepcopy(self.transitions))
        return dict(schema='synthetic-unit-not-native', document=doc, sha256=digest(doc))

    def advance(self):
        self.calls.append('advance')
        if not self.frames:
            raise RuntimeError('synthetic frames exhausted')
        frame = self.frames.pop(0)
        if 'raise' in frame:
            raise RuntimeError(frame['raise'])
        p = self._current['pending']; self.frame = frame
        p['ready'] = frame.get('ready',True); p['failure_reason'] = frame.get('failure')
        p['workspace']['frontier'] = [0] if frame.get('frontier',False) else []
        p['cost']['kernel_ticks'] += frame.get('ticks',3)
        self._append('advance')

    def continue_dependency(self):
        self.calls.append('continue_dependency')
        p = self._current['pending']; p['ready'] = False
        self._append('continue_dependency')


class FakeBackend:
    kind = 'synthetic_unit_test'

    def __init__(self, frames=None, *, selection_error=False, mutation=False, capture_mutation=False):
        self.frames = frames if frames is not None else [dict(native=False,support=False,frontier=True),
                                                        dict(native=False,support=True,frontier=False)]
        self.selection_error = selection_error; self.mutation = mutation; self.capture_mutation = capture_mutation
        self.session = None; self.policies = []

    def begin(self, observation, config, memory, scope, session_id):
        self.begin_inputs = deepcopy((observation,config,memory,scope,session_id))
        self.session = FakeSession(observation,config,memory,session_id,self.frames)
        return self.session

    def reservation(self, session):
        c=session.current;p=c['pending']
        return c['config']['kernel']['max_ticks'] * (2 if c['switches']['use_circuits'] and p['revision_of'] is None and c['memory']['circuits'] else 1)

    def capture(self, session):
        f=session.frame;value=f.get('raw',True)
        proof=dict(nodes=[dict(id='unit-node')],final='unit-node')
        ref=dict(segment=0,generation=session.generation)
        view=dict(raw_value=value,native_accept=f.get('native',False),support_accept=f.get('support',False),
                  reason=f.get('reason','no_supported_existing_path'),original_proof=proof)
        if self.capture_mutation:
            session._current['pending']['cost']['kernel_ticks']+=1
        return dict(candidate_id='synthetic-'+digest(ref),reference=ref,
                    decision=dict(value=value,proof=proof,cost=dict(kernel_ticks=session.current['pending']['cost']['kernel_ticks'])),
                    readout=dict(accepted=f.get('native',False),value=value if f.get('native',False) else None),
                    synthetic_view=view)

    def project(self,candidate):
        return deepcopy(candidate['synthetic_view'])

    def select(self,view,policy,limits):
        self.policies.append(policy)
        if self.selection_error:
            raise RuntimeError('synthetic selector failure')
        h=digest(view);raw=view['raw_value']
        accepted=view['native_accept'] if policy=='native_saved' or raw is not True else view['support_accept']
        accepted=accepted and raw is not None
        usage={k:0 for k in USAGE_KEYS};usage['proof_nodes_reused']=1
        out=dict(policy=policy,input_sha256=h,limits=limits,accepted=accepted,value=raw if accepted else None,
                 reason='supported' if accepted else view['reason'],proof=deepcopy(view['original_proof']),usage=usage)
        if self.mutation:
            view['raw_value']=False
        return out
