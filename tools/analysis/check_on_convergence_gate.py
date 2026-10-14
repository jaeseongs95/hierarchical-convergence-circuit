"""동결된 두 전체상태 box의 현재 잔차·영역 수축 충분조건을 검산한다."""
from __future__ import annotations

import argparse
from fractions import Fraction as Q
import hashlib
import json
import math
from pathlib import Path
import re
import sys
import time

ORDER = ['e:0', 'e:1', 'e:2', 'e:3', 'p:0:0', 'p:0:1', 'goal']
BASE = 'experiments/exp-62-top-down/'
STOP_PROTOCOL = BASE + 'on-real-stop-protocol-20261014.json'
STOP_RECORD = BASE + 'on-real-stop-certificates-20261014.json'
ESCAPE_PROTOCOL = BASE + 'on-real-escape-protocol-20261014.json'
ESCAPE_RECORD = BASE + 'on-real-escape-certificates-20261014.json'
STOP_CHECKER = 'tools/analysis/check_on_real_stop.py'
ESCAPE_CHECKER = 'tools/analysis/check_on_real_escape.py'
ROOT_CHECKER = 'tools/analysis/check_on_fixed_points.py'
PROTOCOL_SHA = 'd7ebdde8e5a82a237aaa3105adfedcd4da24c0713c7735b85750105dc7aefb0d'
SAMPLE = {'sample_id': 'above_near', 'score_hex': '0x1.277babda5a221p-5',
          'drive_hex': '0x1.277babda5a221p-3'}
CASE_SPECS = [{'id': 'low1848', 'tick': 1848, 'record': STOP_RECORD},
              {'id': 'high6144', 'tick': 6144, 'record': ESCAPE_RECORD}]
EPSILONS = ['1/1000000', '1/100000000']
SHA = re.compile(r'[0-9a-f]{64}\Z')
PUBLIC = re.compile(r'-?(?:0|[1-9][0-9]*)\.[0-9]{40}\Z')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def fields(value, expected, label):
    require(isinstance(value, dict) and set(value) == set(expected), label + ' fields mismatch')


def decode(data):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'duplicate JSON key')
            result[key] = value
        return result

    def invalid(value):
        raise ValueError('nonfinite JSON constant: ' + value)

    return json.loads(data, object_pairs_hook=pairs, parse_constant=invalid)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'),
                      allow_nan=False).encode('utf-8')


def file_pin(path):
    path = Path(path).resolve()
    data = path.read_bytes()
    return {'path': str(path), 'sha256': digest(data), 'bytes': len(data)}


def pinned(repo, ref):
    fields(ref, {'path', 'sha256', 'bytes'}, 'pin')
    require(isinstance(ref['path'], str) and isinstance(ref['sha256'], str)
            and SHA.fullmatch(ref['sha256']) and type(ref['bytes']) is int
            and ref['bytes'] > 0, 'invalid pin')
    name = Path(ref['path'])
    require(not name.is_absolute() and '..' not in name.parts, 'nonrelative pin or traversal')
    path = (repo / name).resolve()
    require(path.is_relative_to(repo), 'pin outside repository')
    data = path.read_bytes()
    require(len(data) == ref['bytes'] and digest(data) == ref['sha256'], 'pin bytes/hash mismatch')
    return data


def sample_binding(document, protocol):
    require(all(document.get(k) == protocol.get(k) == v for k, v in SAMPLE.items()),
            'sample/score/drive mismatch')
    score, drive = (Q(*float.fromhex(document[k]).as_integer_ratio())
                    for k in ('score_hex', 'drive_hex'))
    require(drive == 4 * score, 'drive is not exact score4')
    return True


def box(encoded, places=30):
    require(isinstance(encoded, list) and len(encoded) == 7, 'whole ordered7 box required')
    pattern = re.compile(r'-?(?:0|[1-9][0-9]*)\.[0-9]{' + str(places) + r'}\Z')
    result = []
    for pair in encoded:
        require(isinstance(pair, list) and len(pair) == 2, 'endpoint pair required')
        require(all(isinstance(s, str) and len(s) <= places + 4 and pattern.fullmatch(s)
                    for s in pair), 'invalid fixed-grid endpoint')
        lo, hi = map(Q, pair)
        require(-1 <= lo <= hi <= 1 and not any(s.startswith('-') and Q(s) == 0 for s in pair),
                'box domain/order/negative zero')
        result.append((lo, hi))
    return result


def extract_case(record, spec):
    suffix = record['proposal']['suffix']
    require(isinstance(suffix, list), 'prior suffix missing')
    selected = [entry for entry in suffix if isinstance(entry, dict)
                and entry.get('tick') == spec['tick']]
    require(len(selected) == 1, 'case tick missing or repeated')
    fields(selected[0], {'tick', 'x_box'}, 'prior case')
    require(type(selected[0]['tick']) is int, 'prior case tick type')
    box(selected[0]['x_box'])
    return selected[0]['x_box']


def case_binding(case, spec, record, ref):
    fields(case, {'id', 'tick', 'record_pin', 'x_box', 'region'}, 'case')
    require(case['id'] == spec['id'] and type(case['tick']) is int
            and case['tick'] == spec['tick'] and case['record_pin'] == ref, 'case identity/pin')
    expected = extract_case(record, spec)
    require(case['x_box'] == expected, 'complete current B differs from accepted proof')
    return box(case['x_box'])


def region_geometry(region, current):
    fields(region, {'lower', 'upper', 'weights'}, 'region')
    require(isinstance(region['lower'], list) and isinstance(region['upper'], list)
            and len(region['lower']) == len(region['upper']) == 7, 'region dimensions')
    require(isinstance(region['weights'], list) and len(region['weights']) == 7
            and all(type(w) is int and w == 1 for w in region['weights']), 'fixed all7 weights')
    bounds = box([[lo, hi] for lo, hi in zip(region['lower'], region['upper'])], 31)
    for (lo, hi), (bl, bh) in zip(bounds, current):
        center = (bl + bh) / 2
        require(-1 < lo < hi < 1 and lo == center - Q(1, 1000000)
                and hi == center + Q(1, 1000000), 'region not exact midpoint plus/minus radius')
    return [v[0] for v in bounds], [v[1] for v in bounds], [Q(1)] * 7


def outward(value, upper=True):
    numerator = value.numerator * 10 ** 40
    integer = -((-numerator) // value.denominator) if upper else numerator // value.denominator
    whole, decimal = divmod(abs(integer), 10 ** 40)
    return ('-' if integer < 0 else '') + f'{whole}.{decimal:040d}'


def public_rational(value, label):
    require(isinstance(value, str) and len(value) <= 80 and PUBLIC.fullmatch(value),
            label + ' invalid public decimal')
    result = Q(value)
    require(not (result == 0 and value.startswith('-')), label + ' negative zero')
    return result


def residual_upper(b, G, current, tanh_bounds, guard=lambda: None):
    require(len(b) == len(G) == len(current) == 7 and all(len(row) == 7 for row in G),
            'residual whole7 dimensions')
    h_lower, h_upper, residuals = [], [], []
    for i in range(7):
        guard()
        lo = b[i] + sum(min(G[i][j] * current[j][0], G[i][j] * current[j][1])
                        for j in range(7))
        hi = b[i] + sum(max(G[i][j] * current[j][0], G[i][j] * current[j][1])
                        for j in range(7))
        hl, hh = tanh_bounds(lo)[0], tanh_bounds(hi)[1]
        require(Q(-1) <= hl <= hh <= Q(1), 'malformed H(B) bounds')
        h_lower.append(outward(hl, False))
        h_upper.append(outward(hh))
        residuals.append(max(abs(hl - current[i][1]), abs(hh - current[i][0])))
    exact_upper = max(residuals)
    # Compact upward40 witnesses avoid serializing the large Taylor rationals.
    certified = Q(outward(exact_upper))
    require(certified >= exact_upper >= 0, 'residual outward bound failed')
    return certified, {'H_B_lower': h_lower, 'H_B_upper': h_upper,
                       'coordinate_residual_x_upper': [outward(v) for v in residuals],
                       'eH_x_cert': str(certified), 'eH_x_upper40': outward(certified),
                       'all7': True, 'definition': 'sup_B ||H(x)-x||_infinity outer interval',
                       'current_not_previous_tick_delta': True}


def paired_bound(d, qH_cert, eH_x_cert):
    require(0 < d <= 1 and qH_cert >= 0 and eH_x_cert >= 0, 'invalid paired bound inputs')
    qF = 1 - d + d * qH_cert
    eF_p = d * eH_x_cert / 2
    E = None
    if qH_cert < 1 and qF < 1:
        E = eF_p / (1 - qF)
        require(E == eH_x_cert / (2 * (1 - qH_cert)), 'paired damping identity failed')
    return qF, eF_p, E


def gate_decision(region_valid, qH_cert, qF_coupled, public_qF, E_exact, public_E, epsilon):
    require(type(region_valid) is bool and epsilon > 0, 'invalid gate inputs')
    reasons = []
    if not region_valid:
        reasons.append('closed invariant contraction region not proved')
    elif any(v is None for v in (qH_cert, qF_coupled, public_qF, E_exact, public_E)):
        reasons.append('contraction/error bound not evaluated')
    else:
        require(qH_cert >= 0 and qF_coupled >= 0 and public_qF >= qF_coupled
                and E_exact >= 0 and public_E >= E_exact, 'malformed gate bounds')
        if not (qH_cert < 1 and qF_coupled < 1 and public_qF < 1):
            reasons.append('strict exact/public contraction not proved')
        if E_exact > epsilon:
            reasons.append('paired exact distance upper bound exceeds epsilon')
        if public_E > epsilon:
            reasons.append('public distance upper bound exceeds epsilon')
    return {'epsilon_p_exact': str(epsilon),
            'status': 'NOT_CERTIFIED' if reasons else 'CERTIFIED_WITHIN_EPS',
            'reasons': reasons}


def frozen_binding(record, protocol, protocol_path, producer, checker, refs):
    require(record['source_commit'] == protocol['source_commit']
            and record['protocol'] == refs[protocol_path], 'prior header/protocol mismatch')
    frozen = record['frozen_execution']
    require(frozen['protocol'] == refs[protocol_path]
            and type(frozen['numerical_runs_before_freeze']) is int
            and frozen['numerical_runs_before_freeze'] == 0, 'prior freeze mismatch')
    files = frozen['files']
    require(isinstance(files, list) and len(files) == 3
            and len({ref['path'] for ref in files}) == 3, 'prior frozen file inventory')
    frozen_refs = {ref['path']: ref for ref in files}
    require(all(frozen_refs.get(path) == refs[path] for path in (protocol_path, producer, checker)),
            'prior frozen code pins mismatch')
    require(isinstance(protocol['sources'], list)
            and len({ref['path'] for ref in protocol['sources']}) == len(protocol['sources'])
            and all(refs.get(ref['path']) == ref for ref in protocol['sources']),
            'prior source closure mismatch')


def load_binding(repo, protocol, guard):
    inventory = protocol['sources']
    require(isinstance(inventory, list) and len(inventory) == 22, '22 source pins required')
    refs = {ref['path']: ref for ref in inventory}
    require(len(refs) == 22, 'duplicate source pin')
    data = {}
    for name, ref in refs.items():
        guard()
        data[name] = pinned(repo, ref)
    sys.dont_write_bytecode = True

    def helper(path):
        scope = {'__name__': 'convergence_gate_dependency', '__file__': str(repo / path)}
        exec(compile(data[path], str(repo / path), 'exec'), scope)
        return scope

    old, escape, roots = helper(STOP_CHECKER), helper(ESCAPE_CHECKER), helper(ROOT_CHECKER)
    require(set(refs) == escape['SOURCE_PATHS'] | {ESCAPE_PROTOCOL, ESCAPE_RECORD,
            'tools/analysis/on_real_escape.py', ESCAPE_CHECKER}, 'source inventory mismatch')
    old_protocol, old_record = decode(data[STOP_PROTOCOL]), decode(data[STOP_RECORD])
    high_protocol, high_record = decode(data[ESCAPE_PROTOCOL]), decode(data[ESCAPE_RECORD])
    old['protocol_check'](old_protocol)
    escape['protocol_check'](high_protocol, old)
    prefix = escape['prefix_binding'](old_record, old_protocol, refs, old)
    frozen_binding(old_record, old_protocol, STOP_PROTOCOL, 'tools/analysis/on_real_stop.py',
                   STOP_CHECKER, refs)
    frozen_binding(high_record, high_protocol, ESCAPE_PROTOCOL, 'tools/analysis/on_real_escape.py',
                   ESCAPE_CHECKER, refs)
    require(high_record['schema'] == 'HCCONRealEscapeCertificates.v1', 'old escape record schema')
    proposal, checked = high_record['proposal'], high_record['independent_verification']
    sample_binding(proposal, protocol)
    require(proposal['schema'] == 'HCCONRealEscapeProposal.v1'
            and proposal['protocol_sha256'] == checked['protocol_sha256'] == refs[ESCAPE_PROTOCOL]['sha256']
            and proposal['prefix_pin'] == refs[STOP_RECORD]
            and proposal['prefix_end_x_box'] == prefix, 'old escape proposal binding')
    require(checked['schema'] == 'HCCONRealEscapeCheck.v1' and checked['accepted'] is True
            and checked['witness'] is True and checked['status'] == 'CERTIFIED'
            and checked['outcome'] == 'CERTIFIED_EVENTUAL_HIGH_CONVERGENCE'
            and checked['unconditional_F_continuation'] is True
            and checked['all7_strict_entry'] is True and checked['prior_census_rerun'] is False,
            'old escape accepted proof missing')
    for key, value in [('verified_new_transitions', 4096), ('trusted_actual_chunks', 64),
                       ('reused_old_transitions', 2048), ('old_transitions_rechecked', 0),
                       ('native_replays', 0), ('terminal_tick', 6144),
                       ('certified_entry_upper_bound', 6144), ('old_first_stop_unchanged', 1848)]:
        require(type(checked[key]) is int and checked[key] == value, 'old escape count/tick mismatch')
    escape['validate_suffix'](prefix, proposal['suffix'])
    escape['root_geometry'](proposal['suffix'][-1]['x_box'], proposal['root_box'])
    require(checked['root_box'] == proposal['root_box'], 'old escape root differs')
    for key in ('checker_pin', 'producer_pin'):
        path = ESCAPE_CHECKER if key == 'checker_pin' else 'tools/analysis/on_real_escape.py'
        require(checked[key] == file_pin(repo / path), 'old escape execution code pin mismatch')
    require(checked['source_pins'] == high_protocol['sources'] and checked['state_order'] == ORDER
            and checked['prefix_pin'] == refs[STOP_RECORD], 'old escape dependency pins mismatch')
    require(isinstance(high_record['conditional_transition_certificates'], list)
            and len(high_record['conditional_transition_certificates']) == 64
            and len(high_record['actual_chunk_execution_ledger']['observations']) == 64,
            'old escape trusted receipt inventory')
    require(protocol['raw'] == old_protocol['raw'] == high_protocol['raw'], 'raw pin inventory differs')
    raws = []
    for ref in protocol['raw']:
        fields(ref, {'model_id', 'path', 'sha256', 'bytes'}, 'raw pin')
        guard()
        raws.append(decode(pinned(repo, {k: ref[k] for k in ('path', 'sha256', 'bytes')})))
    native, exact = helper(old['NATIVE_CHECKER']), helper(old['BASIN_CHECKER'])
    critical = helper(old['CRITICAL_CHECKER'])
    require(roots['DEGREE'] == exact['DEGREE'] == 96 and native['ORDER'] == ORDER,
            'helper geometry/arithmetic mismatch')
    old['prior_binding'](decode(data[old['NATIVE_RECORD']]),
                         decode(data[old['NATIVE_PROTOCOL']]), refs)
    model = old['model_binding'](raws, protocol['raw'], refs, old_protocol, native, exact, data)
    old['root_dependency'](decode(data[old['CRITICAL_RECORD']]),
                           decode(data[old['CRITICAL_PROTOCOL']]), refs, critical['REGIONS'],
                           old_protocol, exact)
    b, G, d = model
    model_digest = digest(canonical({'b': list(map(str, b)),
                                    'G': [list(map(str, row)) for row in G], 'd': str(d)}))
    require(checked['model_digest'] == model_digest, 'old escape model digest differs')
    guard()
    return refs, {STOP_RECORD: old_record, ESCAPE_RECORD: high_record}, model, roots, model_digest


def analyze_case(case, current, model, roots, guard):
    b, G, d = model
    lower, upper, weights = region_geometry(case['region'], current)
    entry = all(lo < bl <= bh < hi for lo, hi, (bl, bh) in zip(lower, upper, current))
    guard()
    proof = roots['check_box'](b, G, d, lower, upper, weights)
    guard()
    require(isinstance(proof, dict) and type(proof.get('accepted')) is bool,
            'malformed local region result')
    reasons = []
    if not entry:
        reasons.append('all7 strict entry failed')
    if not proof['accepted']:
        require(proof.get('reason') in {'strict self-inclusion failed', 'exact contraction failed',
                'public self-inclusion insufficient', 'public contraction insufficient'},
                'malformed region proof: ' + str(proof.get('reason')))
        reasons.append(proof['reason'])
    valid = entry and proof['accepted']
    eH, residual = residual_upper(b, G, current, roots['tanh_bounds'], guard)
    residual['eF_p_coupled'] = str(d * eH / 2)
    residual['eF_p_upper40'] = outward(d * eH / 2)
    paired = {'qH_cert': None, 'qF_coupled': None, 'qF_upper40': None,
              'E_exact': None, 'E_upper40': None, 'evaluated': False,
              'reason': 'region not proved; denominator not evaluated'}
    qH = qF = public_qF = E = public_E = None
    if valid:
        qH = public_rational(proof['qH_upper'], 'qH')
        require(qH >= 0 and proof['exact_qH_lt_one'] is True
                and proof['exact_qF_lt_one'] is True, 'malformed accepted contraction proof')
        qF, eF, E = paired_bound(d, qH, eH)
        public_qF = Q(outward(qF))
        require(public_qF >= qF, 'qF outward failure')
        public_E = Q(outward(E)) if E is not None else None
        paired = {'qH_cert': str(qH), 'qF_coupled': str(qF), 'qF_upper40': outward(qF),
                  'E_exact': str(E) if E is not None else None,
                  'E_upper40': outward(E) if E is not None else None,
                  'evaluated': E is not None, 'paired_damping_identity': E is not None,
                  'reason': 'paired rational bound' if E is not None else 'q>=1; no division',
                  'qF_is_upper_bound_not_optimal_constant': True,
                  'independently_rounded_ratios_equal_claim': False}
        require(residual['eF_p_coupled'] == str(eF), 'residual paired factor mismatch')
    gates = [gate_decision(valid, qH, qF, public_qF, E, public_E, Q(eps)) for eps in EPSILONS]
    guard()
    return {'id': case['id'], 'tick': case['tick'], 'record_pin': case['record_pin'],
            'x_box': case['x_box'], 'region': case['region'], 'all7_strict_entry': entry,
            'closed_convex_box': True, 'region_valid': valid, 'local_proof': proof,
            'region_failure_reasons': reasons, 'current_residual': residual,
            'paired_bound': paired, 'gates': gates}


def verify(args):
    require(math.isfinite(args.remaining_seconds) and 0 < args.remaining_seconds <= 180,
            'remaining budget outside0..180')
    start = time.monotonic()

    def guard():
        require(time.monotonic() - start < args.remaining_seconds, 'combined local budget expired')

    require(args.protocol_sha256 == PROTOCOL_SHA, 'protocol differs from fixed pre-number freeze')
    protocol_data = Path(args.protocol).read_bytes()
    require(digest(protocol_data) == PROTOCOL_SHA, 'protocol bytes/hash mismatch')
    protocol = decode(protocol_data)
    sample_binding(protocol, protocol)
    require(protocol['cases'] == CASE_SPECS and protocol['state_order'] == ORDER
            and protocol['epsilon_p_exact'] == EPSILONS, 'protocol case/norm contract mismatch')
    proposal_data = Path(args.input).read_bytes()
    proposal = decode(proposal_data)
    fields(proposal, {'schema', 'protocol_sha256', 'sample_id', 'score_hex', 'drive_hex', 'cases'},
           'proposal')
    require(proposal['schema'] == 'HCCONConvergenceGateProposal.v1'
            and proposal['protocol_sha256'] == PROTOCOL_SHA, 'proposal protocol/schema mismatch')
    sample_binding(proposal, protocol)
    require(isinstance(proposal['cases'], list) and len(proposal['cases']) == 2, 'exactly2 cases')
    repo = Path(args.repo).resolve()
    refs, records, model, roots, model_digest = load_binding(repo, protocol, guard)
    results = []
    for case, spec in zip(proposal['cases'], CASE_SPECS):
        guard()
        current = case_binding(case, spec, records[spec['record']], refs[spec['record']])
        results.append(analyze_case(case, current, model, roots, guard))
    guard()
    contrast = (all(g['status'] == 'NOT_CERTIFIED' for g in results[0]['gates'])
                and all(g['status'] == 'CERTIFIED_WITHIN_EPS' for g in results[1]['gates']))
    return {'schema': 'HCCONConvergenceGateCheck.v1', 'accepted': True,
            'status': 'CERTIFIED_ANALYSIS', 'protocol_sha256': PROTOCOL_SHA,
            'proposal_sha256': digest(proposal_data), 'checker_pin': file_pin(__file__),
            'source_pins': protocol['sources'], 'raw_pins': protocol['raw'],
            'dependency_records': [refs[STOP_RECORD], refs[ESCAPE_RECORD]],
            'model_digest': model_digest, 'state_order': ORDER, 'sample_id': SAMPLE['sample_id'],
            'cases': results, 'desired_contrast_observed': contrast,
            'all7': True, 'norm': 'p_infinity_all7', 'epsilon_p_exact': EPSILONS,
            'new_local_checks': 2, 'old_trajectory_rerun': 0, 'native_replays': 0,
            'prior_census_rerun': False, 'elapsed_seconds': time.monotonic() - start,
            'limits': ['Old accepted trajectory/census and64 actual-chunk records are trusted pinned dependencies, not rerun.',
                       'Current residual is F(x_t)-x_t over completeB_t, not previous tick difference or patience.',
                       'Two fixed cases/epsilons only; no first certified tick/allinputs/native/fullEngine/product policy fix.',
                       'NOT_CERTIFIED means sufficient conditions were not proved; it does not prove divergence.',
                       'qF is a uniform upper bound; paired rational cancellation does not imply equal independentlyrounded ratios.',
                       'Caller enforces one absolute180-second deadline; no retry/adaptation.']}


def main():
    parser = argparse.ArgumentParser()
    for name in ('repo', 'protocol', 'protocol-sha256', 'input', 'output'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--remaining-seconds', type=float, default=180)
    args = parser.parse_args()
    result = {'schema': 'HCCONConvergenceGateCheck.v1', 'accepted': False,
              'status': 'INCONCLUSIVE', 'protocol_sha256': args.protocol_sha256}
    try:
        result = verify(args)
    except (ValueError, KeyError, TypeError, IndexError, OSError, OverflowError) as error:
        result['reason'] = str(error)
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + '\n',
                                 encoding='utf-8', newline='\n')
    print(json.dumps({'accepted': result['accepted'], 'status': result['status'],
                      'reason': result.get('reason')}, ensure_ascii=False), flush=True)
    if not result['accepted']:
        raise SystemExit(2)


if __name__ == '__main__':
    main()
