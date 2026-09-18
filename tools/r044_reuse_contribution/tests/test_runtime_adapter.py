"""API contract doubles, never a native research result or native replay substitute."""
from copy import deepcopy
from contextlib import contextmanager
import sys
import types
import unittest
from unittest.mock import patch
from r044_reuse_contribution import runtime

@contextmanager
def native_doubles():
    logs=[]
    class Session:
        def __init__(self,cfg,memory,**kw):
            logs.append(dict(config=deepcopy(cfg),memory=deepcopy(memory),kwargs=deepcopy(kw)))
            self.current=dict(config=deepcopy(cfg),memory=deepcopy(memory),switches=dict(
                use_circuits=kw['use_circuits'],top_down=True,allow_reexpansion=True))
        def begin(self,observation,mode):logs[-1].update(observation=deepcopy(observation),mode=mode)
    class Memory:
        @staticmethod
        def from_document(memory,cfg):return deepcopy(memory)
    class NativeBackend:
        kind='native_hcr'
        def capture(self,*a):return 'inherited_capture'
        def project(self,*a):return 'inherited_project'
        def select(self,*a):return 'inherited_select'
        def reservation(self,*a):return 'inherited_reservation'
    class Trial:
        def __init__(self,*args,**kwargs):self.args=args;self.kwargs=kwargs
    modules={}
    def mod(name,**members):
        m=types.ModuleType(name);m.__dict__.update(members);modules[name]=m;return m
    codec=mod('hcr.codec',adaptive_config_from=lambda c:deepcopy(c),observation_from=lambda o:deepcopy(o))
    mod('hcr',codec=codec);mod('hcr.circuits',AdaptiveMemory=Memory)
    mod('hcr.model',Mode=types.SimpleNamespace(FROZEN_EVAL='frozen_eval'))
    mod('hcr.sessions',AdaptiveSession=Session)
    mod('r037_online_selection');mod('r037_online_selection.backend',NativeBackend=NativeBackend)
    mod('r041_scheduler_direction');mod('r041_scheduler_direction.runtime',ScheduledTimingTrial=Trial)
    mod('r041_scheduler_direction.contracts',Budget=lambda **kw:dict(kw))
    with patch.dict(sys.modules,modules):yield logs

class Adapter(unittest.TestCase):
    def test_only_constructor_switch_differs(self):
        with native_doubles() as logs:
            for gate in (True,False):runtime.backend_for(gate).begin({'observation':'same'},{'config':'same'},{'memory':'same'},'route_only','same_session_id')
            a,b=deepcopy(logs)
            self.assertIs(a['kwargs'].pop('use_circuits'),True);self.assertIs(b['kwargs'].pop('use_circuits'),False)
            self.assertEqual(a,b)
    def test_other_backend_operations_are_inherited(self):
        with native_doubles():
            b=runtime.backend_for(False)
            self.assertEqual(b.capture(None),'inherited_capture');self.assertEqual(b.select(None),'inherited_select')
            self.assertEqual(b.project(None),'inherited_project');self.assertEqual(b.reservation(None),'inherited_reservation')
    def test_gate_type_is_strict(self):
        with native_doubles():
            for value in (1,0,None,'false'):
                with self.subTest(value=value),self.assertRaises(ValueError):runtime.backend_for(value)
    def test_legacy_not_silently_substituted(self):
        with native_doubles(),self.assertRaises(ValueError):runtime.backend_for(True).begin({},{},{},'legacy','same')
    def test_worker_reuses_loop_and_passes_no_world_labels(self):
        with native_doubles():
            o,c,m={'public':1},{'cfg':1},{'saved':2};sink=lambda e:None
            w=runtime.worker(o,c,m,{},'input_order',False,sink)
            self.assertEqual(w.args,(o,c,m,'route_only','online_support',{}))
            self.assertEqual(set(w.kwargs),{'scheduler','backend','event_sink'})
            self.assertIs(w.kwargs['event_sink'],sink);self.assertEqual(w.kwargs['backend'].kind,'native_hcr')
    def test_worker_inputs_defensively_copied(self):
        with native_doubles():
            o,c,m={'p':[1]},{'q':[2]},{'r':[3]};w=runtime.worker(o,c,m,{},'input_order',True,None)
            o['p'].append(5);m['r'].clear();self.assertEqual(w.args[0],{'p':[1]});self.assertEqual(w.args[2],{'r':[3]})
    def test_scheduler_change_rejected(self):
        with native_doubles(),self.assertRaises(ValueError):runtime.worker({},{},{},{},'edge_id_min',True,None)
