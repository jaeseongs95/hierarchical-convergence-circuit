"""결정적 synthetic 경계 조합 검사. 실험 관찰로 집계하지 않는다."""
import random
import unittest
from r037_online_selection.runtime import OnlineTrial
from r037_online_selection.contracts import Budget
from r037_online_selection.control_audit import audit_control
from helpers import FakeBackend,OBS,CONFIG,MEMORY


class BoundaryFuzzTests(unittest.TestCase):
    def test_200_frozen_synthetic_boundary_cases(self):
        rng=random.Random(37018)
        for i in range(200):
            frames=[]
            for _ in range(rng.randrange(1,7)):
                frames.append(dict(ready=rng.choice([True,False]),native=rng.choice([True,False]),
                    support=rng.choice([True,False]),raw=rng.choice([True,False,None]),frontier=True,ticks=rng.randrange(1,6)))
            frames.append(dict(ready=True,native=False,support=False,frontier=False,ticks=1))
            budget=Budget(max_initial_advances=rng.randrange(0,8),max_initial_kernel_ticks=rng.randrange(0,40),
                          max_extra_advances=rng.randrange(0,8),max_extra_kernel_ticks=rng.randrange(0,40))
            backend=FakeBackend(frames)
            worker=OnlineTrial(OBS,CONFIG,MEMORY,rng.choice(['legacy','route_only']),
                               rng.choice(['native_saved','support_first']),budget,backend=backend)
            with self.subTest(case=i):
                run=worker.run();self.assertTrue(audit_control(run,backend.session.states)['verified'])
