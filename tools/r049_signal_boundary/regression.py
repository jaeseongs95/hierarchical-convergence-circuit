"""HF1: distinguish reference-byte identity from strict numerical/behavioral regression.

No producer/native import, no regeneration of expected traces, no reference updating,
no rounding of actual records. SHA256 remains mandatory for all stored source/raw files.
"""
from pathlib import Path
from math import isfinite
from tools.r048_precision import io
from . import spec

ABS_TOL = 2e-12  # Same absolute bound as the pre-existing independent scalar auditor.
REFERENCE_FILE = 'docs/R049_HF1_EXPLORATION.json'
SOURCE_SHA256 = '525432b15b4320a6d8615919a7f22246ffd659f859c6e5058a4970e5516ce44e'


def references(prior, root=None):
    root = Path(root) if root is not None else Path(__file__).resolve().parents[2]
    data = io.read(root / REFERENCE_FILE)
    io.require(prior['source_sha256'] == SOURCE_SHA256 and io.sha(data) == SOURCE_SHA256,
               'original exploratory source bytes changed')
    source = io.loads(data); out = {}
    for e in prior['entries']:
        key = (e['strength'], e['pattern'], e['arm'])
        mode = 'neutral' if e['arm'].endswith('neutral') else 'diagnostic_high_edge_prefix'
        rs = [r for r in source['runs'] if r['scores'] == [e['strength']]*2
              and r['initial_mode'] == mode and r['top_down'] is e['arm'].startswith('on_')]
        io.require(key not in out and len(rs) == 1 and e['pattern'] == 'positive', 'reference selection')
        r = rs[0]
        io.require(io.digest(dict(ticks=r['ticks'], convergence=r['convergence'])) == e['dynamics_sha256'],
                   'full reference trace does not match the ORIGINAL stored digest')
        io.require(r['convergence']['ticks'] == e['ticks'] and r['raw_value'] is e['raw_value'], 'reference annotations')
        out[key] = r
    io.require(len(out) == 8, 'missing/duplicate original exploratory reference')
    return out


def compare(record, reference, expected_digest):
    """Compare EVERY executed tick and scalar; keep all discrete decisions exact.

Caller must also run the unchanged independent record auditor. This function is an
additional cross-environment reference check, not a substitute for numerical replay.
"""
    ref = reference; r = record
    io.require(io.digest(dict(ticks=ref['ticks'], convergence=ref['convergence'])) == expected_digest,
               'reference checksum mismatch')
    problems = []; discrete = []; max_delta = 0.; max_location = None; compared = 0
    def bad(path, why):
        if len(problems) < 32: problems.append(dict(path=path, reason=why))
    def exact(path, actual, expected):
        ok = type(actual) is type(expected) and actual == expected
        if not ok: discrete.append(path); bad(path, 'exact_structure_or_decision_mismatch')
        return ok
    def scalar(path, actual, expected):
        nonlocal max_delta, max_location, compared
        if type(actual) not in (int, float) or type(expected) not in (int, float) or not isfinite(actual) or not isfinite(expected):
            bad(path, 'nonfinite_or_nonnumeric'); return
        delta = abs(actual-expected); compared += 1
        if delta > max_delta: max_delta, max_location = delta, path
        if delta > ABS_TOL: bad(path, 'absolute_error_exceeds_2e-12')
    def states(path, actual, expected):
        if not isinstance(actual, dict) or not exact(path+'.keys', sorted(actual), sorted(expected)): return
        for key in expected:
            scalar(path+'.'+key, actual[key], expected[key])
            # A tiny numeric change that crosses a semantic 0.5 boundary is NOT hidden.
            if type(actual[key]) in (int,float) and isfinite(actual[key]):
                sign = lambda x: (x > .5) - (x < .5)
                exact(path+'.'+key+'.sign', sign(actual[key]), sign(expected[key]))
    exact('config', r['config'], spec.CONFIG)
    exact('scores', [e['score'] for e in r['observation']['edges']], ref['scores'])
    exact('top_down', r['intervention']['top_down'], ref['top_down'])
    exact('initial_state', r['initial_state'], ref['initial_state'])
    # Structural equality is separate from serialized -0.0 versus 0.0 spelling.
    exact('program', r['program'], ref['program'])
    exact('initial_stable_steps', r['initial_stable_steps'], 0)
    expected_mode = 'neutral' if ref['initial_mode'] == 'neutral' else 'high'
    exact('initial_mode', r['intervention']['initial_mode'], expected_mode)
    if exact('trajectory_length', len(r['ticks']), len(ref['ticks'])):
        for i, (a, b) in enumerate(zip(r['ticks'], ref['ticks'])):
            p = 'ticks['+str(i)+']'
            if not exact(p+'.keys', sorted(a), sorted(b)): continue
            exact(p+'.tick', a['tick'], b['tick'])
            exact(p+'.stable_steps', a['stable_steps'], b['stable_steps'])
            states(p+'.state', a['state'], b['state'])
            scalar(p+'.residual', a['residual'], b['residual'])
            exact(p+'.margin_crossed', abs(2*a['state']['goal']-1) >= spec.CONFIG['margin_threshold'],
                  abs(2*b['state']['goal']-1) >= spec.CONFIG['margin_threshold'])
    if isinstance(r['convergence'], dict) and exact('convergence.keys', sorted(r['convergence']), sorted(ref['convergence'])):
        for key in ('status', 'ticks', 'stable_steps'): exact('convergence.'+key, r['convergence'][key], ref['convergence'][key])
        for key in ('margin', 'residual'): scalar('convergence.'+key, r['convergence'][key], ref['convergence'][key])
    else: bad('convergence', 'missing_convergence')
    states('final_state', r['final_state'], ref['final_state'])
    exact('raw_value', r['raw_value'], ref['raw_value'])
    exact('accepted', r['accepted'], ref['adopted'])
    exact('censored', r['censored'], ref['convergence']['status'] == 'budget_exhausted')
    if isinstance(r['proof'], dict):
        exact('proof.under_assumptions_valid', r['proof']['under_assumptions_valid'], ref['proof_under_assumptions_valid'])
        exact('proof.primitive_depth', r['proof']['primitive_depth'], ref['D_DAG'])
    else: bad('proof', 'missing_proof')
    exact('native.group_updates', r['native_cost']['group_updates'], ref['group_updates'])
    exact('native.signal_transmissions', r['native_cost']['signal_transmissions'], ref['signal_transmissions'])
    actual_digest = io.digest(dict(ticks=r['ticks'], convergence=r['convergence']))
    equal = actual_digest == expected_digest
    passed = not problems
    return dict(dynamics_equal=equal, exact_sha256_equal=equal, expected=expected_digest, actual=actual_digest,
        numerical_and_discrete_equivalent=passed, regression_passed=passed, tolerance_absolute=ABS_TOL,
        comparison='exact_decisions_AND_all_scalars_absolute_error_le_2e-12_AND_independent_audit',
        max_absolute_difference=max_delta, max_difference_location=max_location, compared_scalars=compared,
        discrete_mismatch_fields=discrete, mismatches=problems,
        classification='exact_match' if passed and equal else 'numeric_equivalent_hash_different' if passed else 'substantive_regression',
        raw_values_modified=False, expected_hash_replaced=False, independent_new_evidence=False)
