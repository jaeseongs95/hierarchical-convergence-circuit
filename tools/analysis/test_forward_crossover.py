"""계측 경계 회귀와 봉인 후 교차 대조 검증. 수치 궤적 재생은 하지 않는다."""
import gc
import hashlib
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
import termination_compare_core as core
import termination_compare_runner as runner
import termination_forward_crossover as cross


class Clock:
    def __init__(self): self.value = 0
    def __call__(self): self.value += 100; return self.value


def check_success_bytes(expected_bytes, final, completed):
    # A successful callback followed by a hard kill is not a completed policy.
    if expected_bytes is not None and completed:
        assert final and core.canonical(final['certificate']) == expected_bytes


class CrossoverTests(unittest.TestCase):
    def test_success_callback_then_timeout_is_censored(self):
        expected = core.canonical({'proof': 'same'})
        check_success_bytes(expected, None, False)
        with self.assertRaises(AssertionError): check_success_bytes(expected, None, True)
        check_success_bytes(expected, {'certificate': {'proof': 'same'}}, True)
        with self.assertRaises(AssertionError):
            check_success_bytes(expected, {'certificate': {'proof': 'different'}}, True)

    def test_highres_body_not_legacy_quantized_clock(self):
        with tempfile.TemporaryDirectory() as tmp:
            o = cross.Observer(tmp, (Clock(), lambda: 0, Clock()), lambda: None)
            self.assertEqual(o.call('advance', lambda: 37), 37)
            r = o.rows['advance']
            self.assertGreater(r['wall_seconds'], 0)
            self.assertEqual(r['legacy_wall_seconds'], 0)
            self.assertGreater(r['clock_bracket_seconds'], 0)

    def test_nested_and_exception_counts_not_disjoint_sum(self):
        with tempfile.TemporaryDirectory() as tmp:
            o = cross.Observer(tmp, (Clock(), Clock(), Clock()), lambda: None)
            o.call('advance', lambda: o.call('numeric_advance', lambda: None))
            self.assertNotIn('numeric_advance', o.rows)
            self.assertEqual(o.nested['numeric_advance']['calls'], 1)
            self.assertGreater(o.rows['advance']['wall_seconds'], o.nested['numeric_advance']['wall_seconds'])
            with self.assertRaisesRegex(ValueError, 'probe'):
                o.call('certificate', lambda: (_ for _ in ()).throw(ValueError('probe')))
            self.assertEqual(o.rows['certificate']['completed'], 0)
            self.assertEqual(o.stack, [])

    def test_gc_passive_phase_binding_and_settings(self):
        before = gc.isenabled(), gc.get_threshold(), list(gc.callbacks)
        with tempfile.TemporaryDirectory() as tmp:
            o = cross.Observer(tmp, (Clock(), Clock(), Clock()), lambda: None)
            o.stack.append('numeric_advance')
            o.gc_callback('start', {'generation': 0})
            o.gc_callback('stop', {'generation': 0, 'collected': 3, 'uncollectable': 0})
            self.assertEqual(o.gc_rows['numeric_advance/generation-0']['calls'], 1)
            self.assertEqual(o.gc_rows['numeric_advance/generation-0']['collected'], 3)
        self.assertEqual(before, (gc.isenabled(), gc.get_threshold(), list(gc.callbacks)))

    def test_crossed_pairs_and_censoring(self):
        rows = [dict(variant=v, status='COMPLETE', policy_supervision={'highres_wall_seconds': w})
                for v, w in zip(('C0','C1','C1','C0'), (20,15,17,24))]
        self.assertEqual(cross.paired_effects(rows)['C1_minus_C0_seconds'], [-5,-7])
        self.assertEqual(cross.paired_effects(rows)['mean_seconds'], -6)
        rows[2]['status'] = 'BUDGET_INCOMPLETE'
        self.assertIsNone(cross.paired_effects(rows)['mean_seconds'])
        self.assertEqual(cross.paired_effects(rows)['planned_pairs'], 2)
        with self.assertRaisesRegex(ValueError, 'crossed'):
            cross.paired_effects([rows[0]]*4)

    def test_wrapper_delegation_restores_original_after_failure(self):
        before = list(gc.callbacks)
        original = cross.cost.BASE_ARITHMETIC
        seen = {}
        def fake(*args):
            a = cross.cost.BASE_ARITHMETIC.__new__(cross.cost.BASE_ARITHMETIC)
            self.assertIsInstance(a, core.Arithmetic)
            seen['timings'] = cross.cost.Timings()
            raise ValueError('injected')
        with tempfile.TemporaryDirectory() as tmp, patch.object(cross.cost, 'policy', fake):
            with self.assertRaisesRegex(ValueError, 'injected'):
                cross.policy('unused', 'unused', 'C1', {'out': tmp})
        self.assertIsInstance(seen['timings'], cross.Observer)
        self.assertIs(cross.cost.BASE_ARITHMETIC, original)
        self.assertIs(core.Arithmetic, cross.ORIGINAL)
        self.assertEqual(gc.callbacks, before)

    def test_instrumented_exact_step_and_certificate_match_original(self):
        sources = {n: (Path(__file__).parent/n).read_text(encoding='utf-8') for n in core.LIB_PINS}
        model = dict(b=['0']*7, G=[['0']*7 for _ in range(7)], d='1/2')
        from fractions import Fraction
        box = core.encode_box([(Fraction(0), Fraction(0))]*7)
        baseline = cross.ORIGINAL(sources, core.Meter())
        expected_step = baseline.step(model, box)
        expected_certificate = baseline.certificate(model, box)
        observed = {}
        def fake(*args):
            a = cross.cost.BASE_ARITHMETIC(sources, core.Meter())
            observed['step'] = a.step(model, box)
            observed['certificate'] = a.certificate(model, box)
            observed['observer'] = cross.cost.Timings()
        with tempfile.TemporaryDirectory() as tmp, patch.object(cross.cost, 'policy', fake):
            cross.policy('unused', 'unused', 'C0', {'out': tmp})
        self.assertEqual(observed['step'], expected_step)
        self.assertEqual(observed['certificate'], expected_certificate)
        self.assertEqual(observed['observer'].nested['numeric_advance']['calls'], 1)


def verify_study(out):
    release = core.decode(sys.stdin.buffer.readline())
    start = time.perf_counter_ns()
    def guard():
        if time.monotonic() >= release['deadline']: raise core.BudgetStop('verification deadline')
    out = Path(out)
    sealed = core.decode((out/'cells-sealed.json').read_bytes())
    data = core.decode((out/'setup/public-input.json').read_bytes())
    model = runner.validate_input(data)
    import check_termination_comparison as evaluator
    assert evaluator.independent_model(data['public']) == model
    cfg, _ = cross.contract()
    rows = sealed['rows']
    assert len(rows) == 4 and [r['variant'] for r in rows] == cfg['sequential_order']
    reference = {}; states_equal = 0; summaries = []; cache = {}; occurrences = []
    successes = []; complete = 0
    numerical = core.Arithmetic(data['math_sources'], core.Meter(release['deadline']))
    for index, row in enumerate(rows):
        guard(); cid = f'{index+1:02d}-{row["variant"]}'
        assert row['cell_id'] == cid and row['policy_cap_seconds'] == 1575
        if row['status'] == 'NOT_RUN':
            summaries.append(dict(cell_id=cid, variant=row['variant'], status='NOT_RUN')); continue
        child = out/cid
        seal = core.decode((child/'sealed-cell.json').read_bytes())
        assert seal['supervision'] == row['policy_supervision']
        assert seal['supervision']['active_processes'] == 0
        assert seal['input_sha256'] == hashlib.sha256((out/'setup/public-input.json').read_bytes()).hexdigest()
        last = runner.last_snapshot(child, seal['supervision'])
        assert last == seal['last_complete']
        local_states = {}
        for tick in range(last['snapshot']['tick']+1 if last else 0):
            guard(); s = core.decode((child/f'state-{tick:06d}.json').read_bytes())
            assert s['tick'] == tick and s['model_digest'] == data['model_digest']
            assert s['observation_digest'] == data['observation_digest'] and s['processed_digest'] == data['processed_digest']
            assert s['diagnostic'] == core.diagnostic(s['current_x_box'])
            b = s['current_x_box']; local_states[tick] = b
            if tick in reference:
                assert b == reference[tick], (cid, tick); states_equal += 1
            else: reference[tick] = b
        timing = core.decode((child/'timings.json').read_bytes()) if (child/'timings.json').exists() else None
        trace = core.decode((child/'trace.json').read_bytes()) if (child/'trace.json').exists() else None
        final = seal['final']; gates = timing['gate_attempts'] if timing else []
        if row['status'] == 'COMPLETE':
            assert final and timing and trace and final['stop_reason'] == 'CERTIFIED'
            assert timing['counts'] == final['counters']
            assert trace['gc_before'] == trace['gc_after'] and not trace['gc_pending']
            assert trace['phases'] == timing['phases']
            assert len(gates) == final['counters']['certificate_attempts'] == last['snapshot']['tick']//16
            assert [g['attempt'] for g in gates] == list(range(1, len(gates)+1))
            assert [g['attempt']*16 for g in gates if g['status'] == 'CERTIFIED_WITHIN_EPS'] == [last['snapshot']['tick']]
            assert sum(g['screen'] is not None for g in gates) == final['counters']['prefilter_rejections']
            assert trace['phases']['advance']['calls'] == last['snapshot']['tick']
            assert trace['nested']['numeric_advance']['calls'] == last['snapshot']['tick']
            previous = 0
            for block_no in range(1, trace['blocks']+1):
                block = core.decode((child/f'block-{block_no:04d}.json').read_bytes())
                assert block['tick_start_exclusive'] == previous
                end = block['tick_end_inclusive']; assert end > previous
                assert end-previous <= 128
                assert block['input_state_digest'] == core.digest(local_states[previous])
                assert block['output_state_digest'] == core.digest(local_states[end])
                previous = end
            assert previous == last['snapshot']['tick']
            complete += 1
            successes.append((cid, last['snapshot']['tick'], core.canonical(final['certificate'])))
        # Predicate answers are freshly computed after seals, never copied from r11.
        for g in gates:
            guard(); tick = g['attempt']*16; b = local_states[tick]
            assert core.digest(b) == g['state_digest']
            if row['variant'] == 'C1':
                payload = core.canonical(dict(model=model, current_x_box=b,
                    radius_x_exact=str(core.RADIUS), epsilon_p_exact=[str(core.EPSILON)],
                    helper_pins=core.LIB_PINS))
                key = hashlib.sha256(payload).hexdigest()
                if key in cache:
                    assert cache[key]['payload'] == payload  # hash alone never authorizes reuse
                else:
                    original = numerical.certificate(model, b)
                    cache[key] = dict(payload=payload, status=original['bounds']['component_vector'][0]['status'],
                        success=core.canonical(original) if original['bounds']['component_vector'][0]['status'] == 'CERTIFIED_WITHIN_EPS' else None)
                expected = cache[key]
                assert expected['status'] == g['status']
                check_success_bytes(expected['success'], final, row['status'] == 'COMPLETE')
                occurrences.append(dict(cell_id=cid, tick=tick, payload_sha256=key, original_status=expected['status']))
        evaluation = row.get('evaluation')
        summaries.append(dict(cell_id=cid, variant=row['variant'], status=row['status'],
            tick=last['snapshot']['tick'] if last else None,
            highres_wall_seconds=seal['supervision']['highres_wall_seconds'],
            legacy_wall_seconds=seal['supervision']['wall_seconds_after_report'],
            tree_cpu_seconds=seal['supervision']['tree_cpu_seconds'],
            peak_job_committed_bytes=seal['supervision']['peak_job_committed_bytes'],
            phases=trace['phases'] if trace else None, nested=trace['nested'] if trace else None,
            gc_nested=trace['gc_nested'] if trace else None,
            candidate=evaluation.get('candidate') if evaluation else None,
            candidate_correct=evaluation.get('candidate_correct') if evaluation else None,
            distance=evaluation.get('distance') if evaluation else None,
            counters=final['counters'] if final else (last['snapshot']['counters'] if last else None)))
    if successes:
        assert all((tick, cert) == successes[0][1:] for _, tick, cert in successes)
    effects = cross.paired_effects(rows)
    quality = complete == 4 and all(s.get('candidate_correct') is True and
        (s.get('distance') or {}).get('status') == 'INSIDE' for s in summaries)
    # Read evaluator shape rather than silently upgrading missing quality evidence.
    result = dict(schema='HCCForwardCrossoverVerification.v1', status='PASS' if quality else 'PASS_INTEGRITY_ONLY',
        planned_denominator=4, completed=complete, cells=summaries,
        common_reference_full7_equalities=states_equal, fresh_unique_original_predicates=len(cache),
        original_C1_predicate_occurrences=occurrences, postseal_exact_full_payload_dedup=True,
        successful_certificate_bytes_and_first_tick_equal=complete == 4,
        paired_policy_cost=effects, quality_all_four=quality,
        wholecost_win=(quality and effects['mean_seconds'] is not None and effects['mean_seconds'] < 0),
        verification_highres_wall_seconds=(time.perf_counter_ns()-start)/1e9,
        independent_discovery_samples=0, no_nonlinear_prefix_replay=True,
        host_load_uncontrolled=True, shared_numeric_helpers_trusted=True,
        gc_may_be_policy_mediator=True, retrospective_r11_cause='NOT_IDENTIFIED',
        per_variant_repeats=2, no_general_or_statistical_superiority=True)
    guard(); runner.write_new(Path(release['out'])/'result.json', result); guard()
    print(core.canonical(dict(status=result['status'], complete=complete,
        unique_predicates=len(cache), predicate_occurrences=len(occurrences))).decode(), flush=True)


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--verify-study': verify_study(sys.argv[2])
    else: unittest.main()
