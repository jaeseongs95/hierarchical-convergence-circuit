"""Synthetic exposure traces and deliberate accounting corruption, not native runs."""
from copy import deepcopy
import unittest
from r045_direct_support.measurements import measure, MeasurementError
from r045_direct_support.storage import digest
from r045_direct_support.tests.fixtures import measurement_fixture


class MeasurementTests(unittest.TestCase):
    def test_six_gate_conditions(self):
        for f in ('supported_len2','no_match_len1','conflict_len2'):
            for g in (True,False):
                with self.subTest(f=f,g=g):
                    args=measurement_fixture(f,g);before=digest(args[0]);d=measure(*args)
                    self.assertEqual(before,digest(args[0]));self.assertTrue(d['verified'])
    def test_direct_on_positive_adopted_route(self):
        d=measure(*measurement_fixture());self.assertIs(d['direct_circuit_use'],True)
    def test_macro_somewhere_is_not_direct_use(self):
        args=list(measurement_fixture());args[3]['adopted_route']['circuit_uses']=[]
        self.assertIs(measure(*args)['direct_circuit_use'],False)
    def test_absent_positive_route_is_unknown_not_zero(self):
        args=list(measurement_fixture());args[3]['adopted_route']=None
        self.assertIsNone(measure(*args)['direct_circuit_use_count'])
    def test_negative_proof_is_not_positive_direct_adoption(self):
        d=measure(*measurement_fixture('conflict_len2'))
        self.assertIsNone(d['direct_circuit_use']);self.assertEqual(d['mismatch_rejected_evaluations'],1)
    def test_binding_without_match_is_not_pool_exposure(self):
        d=measure(*measurement_fixture('no_match_len1'))
        self.assertEqual((len(d['binding_rows']),d['matched_candidates'],d['pool_candidate_evaluations']),(1,0,0))
    def test_alias_projection(self):
        a=measure(*measurement_fixture());b=measure(*measurement_fixture(variant='fresh_ids'))
        self.assertEqual(a['candidates'][0]['canonical_span'],b['candidates'][0]['canonical_span'])
        self.assertEqual(a['decision_signature_sequence'],b['decision_signature_sequence'])
    def test_decision_signature_ignores_pool_event_ids(self):
        a=measure(*measurement_fixture(gate=True));b=measure(*measurement_fixture(gate=False))
        self.assertEqual(a['decision_signature_sequence'],b['decision_signature_sequence'])
    def test_tick_change_changes_signature(self):
        args=measurement_fixture();other=deepcopy(args)
        next(e for e in other[0]['base']['packet']['document']['events'] if e['event']=='r02_tick' and e['payload']['network_id']=='decision')['payload']['state']['goal']=.2
        self.assertNotEqual(measure(*args)['decision_signature_sequence'],measure(*other)['decision_signature_sequence'])
    def test_bad_count_rejected(self):
        args=measurement_fixture();args[0]['base']['packet']['document']['engine']['pending']['cost']['candidate_circuits']=7
        with self.assertRaises(ValueError):measure(*args)
    def test_bad_eligibility_rejected(self):
        args=measurement_fixture('conflict_len2')
        next(e for e in args[0]['base']['packet']['document']['events'] if e['event']=='r02_pool_result')['payload']['activations'][0]['eligible']=True
        with self.assertRaises(ValueError):measure(*args)
    def test_bad_tick_sequence_rejected(self):
        args=measurement_fixture()
        next(e for e in args[0]['base']['packet']['document']['events'] if e['event']=='r02_tick')['payload']['tick']=7
        with self.assertRaises(ValueError):measure(*args)
    def test_direct_without_macro_rejected(self):
        args=measurement_fixture();args[3]['macro_actions']=0
        with self.assertRaises(ValueError):measure(*args)
    def test_missing_settle_rejected(self):
        args=measurement_fixture();events=args[0]['base']['packet']['document']['events']
        events[:]=[e for e in events if not(e['event']=='r02_settled' and e['payload']['network_id']=='decision')]
        with self.assertRaises(ValueError):measure(*args)
    def test_input_mismatch_requires_boundaries_not_repair(self):
        args=measurement_fixture();args[2]['manipulation']['edge_map']={'unknown':'unknown'}
        with self.assertRaises(MeasurementError) as caught:measure(*args)
        self.assertIsInstance(caught.exception.__cause__,KeyError)

if __name__=='__main__':unittest.main()
