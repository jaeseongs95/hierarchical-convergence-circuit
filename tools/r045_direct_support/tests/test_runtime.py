"""Mocked forwarding only. Does not execute or certify native HCC."""
import inspect
import sys
import types
import unittest
from unittest.mock import patch
from r045_direct_support import runtime


class RuntimeBoundaryTests(unittest.TestCase):
    def test_signature_excludes_truth_family_maps_and_backend_override(self):
        self.assertEqual(tuple(inspect.signature(runtime.worker).parameters),
            ('observation','config','memory','budget','use_circuits','event_sink'))
    def test_forwards_only_pinned_inputs(self):
        seen={};sentinel=object()
        def inherited(*args):
            seen['args']=args;args[0]['edges'].append('test-mutation');return sentinel
        module=types.ModuleType('r044_reuse_contribution.runtime');module.worker=inherited
        obs={'edges':[]};cfg={};memory={};budget={};sink=lambda _:None
        with patch.dict(sys.modules,{'r044_reuse_contribution.runtime':module}):
            self.assertIs(runtime.worker(obs,cfg,memory,budget,False,sink),sentinel)
        self.assertEqual(obs,{'edges':[]});self.assertEqual(seen['args'][4:6],('input_order',False))
        self.assertIs(seen['args'][-1],sink)
    def test_gate_int_rejected_before_backend(self):
        with self.assertRaises(ValueError):runtime.worker({}, {}, {}, {},1,None)
    def test_native_exceptions_not_retried(self):
        calls=[]
        def inherited(*args):calls.append(args);raise RuntimeError('first-native-error')
        module=types.ModuleType('r044_reuse_contribution.runtime');module.worker=inherited
        with patch.dict(sys.modules,{'r044_reuse_contribution.runtime':module}):
            with self.assertRaisesRegex(RuntimeError,'first-native-error'):runtime.worker({}, {}, {}, {},True,None)
        self.assertEqual(len(calls),1)

if __name__=='__main__':unittest.main()
