"""독립 합성 oracle와 실행 경계 검사. 실제 연구 셀/원 궤적을 실행하지 않는다."""
from fractions import Fraction as Q
from decimal import Decimal, localcontext
from pathlib import Path
import unittest
from unittest.mock import patch
import termination_compare_core as core

ROOT = Path(__file__).resolve().parent


def arithmetic(meter=None):
    return core.Arithmetic({n: (ROOT/n).read_text(encoding='utf-8')
                            for n in core.LIB_PINS}, meter or core.Meter())


def zero_model(d=Q(1,2)):
    return {'b':['0']*7, 'G':[['0']*7 for _ in range(7)], 'd':str(d)}


def point(x=Q(0)):
    return core.encode_box([(x,x)]*7)


class CoreChecks(unittest.TestCase):
    def test_outward_negative_and_domain(self):
        x = Q(-1,3)
        self.assertLessEqual(Q(core.grid(x)),x)
        self.assertGreaterEqual(Q(core.grid(x,True)),x)
        self.assertEqual(core.grid(0),'0.'+'0'*30)
        with self.assertRaises(ValueError): core.parse_box(point()[:5])
        with self.assertRaises(ValueError): core.parse_box(point(Q(2)))
        with self.assertRaises(ValueError): core.decode('{"x":NaN}')
        with self.assertRaises(ValueError): core.decode('{"x":1,"x":2}')

    def test_sequential_full7_linear_golden(self):
        a=arithmetic(); box=point(Q(2,5))
        for tick in range(1,5):
            box=a.step(zero_model(),box)
            expected=Q(2,5)/2**tick
            self.assertTrue(all(lo<=expected<=hi for lo,hi in core.parse_box(box)))
        self.assertEqual(a.meter.counts['real_map_steps'],4)
        self.assertEqual(a.meter.counts['real_coordinate_updates'],28)
        self.assertEqual(a.meter.counts['interval_matrix_terms'],196)

    def test_nonlinear_signed_bounds_independent_decimal_oracle(self):
        a=arithmetic();m=zero_model(Q(1));m['G'][0][1]='-2'
        box=point();box[1]=[core.grid(Q(1,5)),core.grid(Q(3,10))]
        result=core.parse_box(a.step(m,box))
        with localcontext() as ctx:
            ctx.prec=80
            def reference(s):
                e=(2*Decimal(s)).exp();return Q((e-1)/(e+1))
            self.assertLessEqual(result[0][0],reference('-.6'))
            self.assertGreaterEqual(result[0][1],reference('-.4'))
        self.assertGreater(a.meter.counts['taylor_calls'],0)
        self.assertTrue(all(lo<=0<=hi for lo,hi in result[1:]))

    def test_source_pin_and_pure_information_barrier(self):
        sources={n:(ROOT/n).read_text(encoding='utf-8') for n in core.LIB_PINS}
        sources[next(iter(sources))]+='\n'
        with self.assertRaises(ValueError): core.Arithmetic(sources,core.Meter())
        a=arithmetic()
        self.assertNotIn('ACTUAL_FIRST',a.local.__globals__)
        self.assertNotIn('TICKS',a.local.__globals__)
        self.assertNotIn('open',a.local.__globals__['__builtins__'])
        with patch('builtins.open',side_effect=AssertionError('IO leaked')), \
             patch.object(Path,'read_bytes',side_effect=AssertionError('IO leaked')):
            r=a.certificate(zero_model(),point())
        self.assertEqual(r['bounds']['component_vector'][0]['status'],'CERTIFIED_WITHIN_EPS')
        self.assertEqual(r['bounds']['component_vector'][0]['E_p_exact'],'0')

    def test_comparison_epsilon_boundary_and_invalid_inverse(self):
        solve=arithmetic().local.__globals__['solve_comparison']
        k=[[Q(0)]*7 for _ in range(7)];k[0][0]=Q(1,2)
        v=solve(k,[Q(1,1000000)]+[Q(0)]*6)
        self.assertEqual(v[0]/2,core.EPSILON)
        for bad in (Q(1),Q(-1,2)):
            k[0][0]=bad
            with self.assertRaises(ValueError): solve(k,[Q(1)]+[Q(0)]*6)

    def test_budget_mid_coordinate_does_not_complete_step(self):
        calls=[0]
        def clock(): calls[0]+=1;return calls[0]
        m=core.Meter(deadline=5,clock=clock);a=arithmetic(m)
        model=zero_model();model['b']=['1']*7
        with self.assertRaises(core.BudgetStop): a.step(model,point())
        self.assertEqual(m.counts['real_map_steps'],0)
        self.assertGreater(m.counts['taylor_calls'],0)

    def test_legacy_small_delta_is_not_distance_proof(self):
        legacy=core.Legacy(); p=Q(1,2);older=None;prev=point()
        for tick in range(1,17):
            p=(1-Q(1,10**7))*p+Q(1,10**7)
            now=point(2*p-1);result=legacy.update(tick,prev,now,older)
            if tick<16:self.assertIsNone(result['status'])
            older,prev=prev,now
        self.assertEqual(result['status'],'stable_ambiguous')
        self.assertGreater(1-p,Q(49,100))

    def test_legacy_reset_no_latch_and_two_cycle(self):
        l=core.Legacy();old=point(Q(1,2));prev=old
        for tick in range(1,15):l.update(tick,prev,prev,old)
        jumped=point(Q(3,5));r15=l.update(15,prev,jumped,old)
        self.assertEqual(r15['residual_p_interval'],['1/20','1/20'])
        r=l.update(16,jumped,point(Q(61,100)),prev)
        self.assertEqual(l.stable,0);self.assertIsNone(r['status'])
        l=core.Legacy();l.stable=0
        r=l.update(16,point(Q(-1,2)),point(Q(1,2)),point(Q(1,2)))
        self.assertEqual(r['status'],'oscillating')
        l.stable=4
        r=l.update(16,point(Q(1,2)),point(Q(1,2)),point(Q(-1,2)))
        self.assertEqual(r['status'],'stable_decision')

    def test_strict_readout_and_partial_false(self):
        box=point();box[6]=[core.grid(Q(-1,2)),core.grid(0)]
        self.assertIsNone(core.diagnostic(box)['candidate'])
        for x,candidate in ((core.MARGIN,True),(-core.MARGIN,False)):
            box=point();box[6]=[core.grid(x),core.grid(x,True)]
            # A grid enclosing the exact margin boundary may straddle: never force confidence.
            d=core.diagnostic(box)
            self.assertIsNone(d['candidate'])
            outward_x=x+(Q(1,10**28) if x>0 else -Q(1,10**28))
            box[6]=[core.grid(outward_x),core.grid(outward_x,True)]
            self.assertEqual(core.diagnostic(box)['candidate'],candidate)
        d=core.diagnostic(point(Q(-1,2)))
        self.assertFalse(d['candidate']);self.assertTrue(d['coverage_required'])
        self.assertEqual(d['adopted_value'],'NOT_MEASURED')


if __name__=='__main__':
    unittest.main()
