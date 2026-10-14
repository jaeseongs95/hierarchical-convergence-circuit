"""동결된 보수적 전체상태 box의 최초 gate 인증 시점을 검사한다."""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from fractions import Fraction as Q
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import time
import uuid

PROTOCOL_SHA = '91725a812c3afcff7e8ea6f2a3caafee4709a8bf987ddc0f0bda5165fa1d971b'
BASE = 'experiments/exp-62-top-down/'
GATE_PROTOCOL = BASE + 'on-convergence-gate-protocol-20261014.json'
GATE_RECORD = BASE + 'on-convergence-gate-certificates-20261014.json'
GATE_CHECKER = 'tools/analysis/check_on_convergence_gate.py'
NATIVE_RECORD = BASE + 'on-native-stop-certificates-20261014.json'
STOP_RECORD = BASE + 'on-real-stop-certificates-20261014.json'
ESCAPE_RECORD = BASE + 'on-real-escape-certificates-20261014.json'
DEPENDENCIES = [NATIVE_RECORD, STOP_RECORD, ESCAPE_RECORD]
ORDER = ['e:0', 'e:1', 'e:2', 'e:3', 'p:0:0', 'p:0:1', 'goal']
EPSILONS = ['1/1000000', '1/100000000']
RADIUS = Q(1, 1000000)
FIXED_RANGE = {'first_tick': 0, 'last_tick': 6144}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'),
                      allow_nan=False).encode('utf-8')


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


def fixed_decimal(value, places):
    scaled = value * 10 ** places
    require(scaled.denominator == 1, 'non-grid exact decimal')
    integer = scaled.numerator
    whole, fraction = divmod(abs(integer), 10 ** places)
    return ('-' if integer < 0 else '') + f'{whole}.{fraction:0{places}d}'


def compact(value, upper=False):
    numerator = value.numerator * 10 ** 40
    integer = -((-numerator) // value.denominator) if upper else numerator // value.denominator
    return fixed_decimal(Q(integer, 10 ** 40), 40)


def helper(data, name, repo):
    scope = {'__name__': 'first_gate_dependency', '__file__': str(repo / name)}
    exec(compile(data[name], str(repo / name), 'exec'), scope)
    return scope


def assemble_boxes(native, native_protocol, stop, escape, refs, old, escape_helper):
    """과거 증명의 box를 gap 없는 exact tick0..6144 목록으로 결속한다."""
    prefix, _ = old['prior_binding'](native, native_protocol, refs)
    require(stop['proposal']['prefix_pin'] == refs[NATIVE_RECORD], 'native prefix pin differs')
    encoded = old['splice'](prefix, stop['proposal']['suffix'],
                            stop['proposal']['prefix_end_x_box'], 2048)
    require(escape['proposal']['prefix_pin'] == refs[STOP_RECORD]
            and escape['proposal']['prefix_end_x_box'] == encoded[-1], 'B2048 splice differs')
    escape_helper['validate_suffix'](encoded[-1], escape['proposal']['suffix'])
    zero = fixed_decimal(Q(0), 30)
    inventory = [{'tick': 0, 'x_box': [[zero, zero] for _ in ORDER]}]
    inventory.extend({'tick': t, 'x_box': item} for t, item in enumerate(encoded, 1))
    inventory.extend(escape['proposal']['suffix'])
    require(len(inventory) == 6145, 'whole box inventory count')
    for tick, entry in enumerate(inventory):
        require(set(entry) == {'tick', 'x_box'} and type(entry['tick']) is int
                and entry['tick'] == tick, 'absolute tick gap/order/duplicate')
        old['box'](entry['x_box'])
    return inventory


def region_for(current):
    centers = [(lo + hi) / 2 for lo, hi in current]
    return {'lower': [fixed_decimal(m - RADIUS, 31) for m in centers],
            'upper': [fixed_decimal(m + RADIUS, 31) for m in centers],
            'weights': [1] * 7}


def group_proof(midpoints, model, tanh_bounds, guard=lambda: None):
    """ALLmember extrema에서 직접 비교한 고정 H gate 음성 증거만 반환한다."""
    require(isinstance(midpoints, list) and midpoints
            and all(len(m) == 7 for m in midpoints), 'group whole7 midpoints required')
    b, G, d = model
    require(len(b) == len(G) == 7 and all(len(row) == 7 for row in G)
            and 0 < d <= 1, 'group model dimensions/damping')
    statistics = {}
    for index, state in ((5, 'p:0:1'), (6, 'goal')):
        guard()
        require(ORDER[index] == state, 'row/state binding differs')
        arguments = [b[index] + sum(G[index][j] * m[j] for j in range(7))
                     for m in midpoints]
        a_min, a_max = min(arguments), max(arguments)
        m_min, m_max = min(m[index] for m in midpoints), max(m[index] for m in midpoints)
        S = sum(abs(v) for v in G[index])
        statistics[index] = (a_min, a_max, m_min, m_max, S)
    a_min, a_max, m_min, m_max, S = statistics[5]
    U = max(Q(0), max(abs(a_min), abs(a_max)) - RADIUS * S)
    tanh_upper = tanh_bounds(U)[1]
    require(0 <= tanh_upper <= 1, 'invalid group tanh upper')
    lower = S * (1 - tanh_upper ** 2)
    if lower >= 1:
        return {'kind': 'uniform_H_contraction_impossible', 'row_index': 5,
                'state': 'p:0:1', 'member_count': len(midpoints),
                'a_min': str(a_min), 'a_max': str(a_max), 'S': str(S), 'U': str(U),
                'q_lower40': compact(lower), 'comparison': 'exact q_lower>=1',
                'first_failure_reason_order_claim': False}
    for index, state in ((5, 'p:0:1'), (6, 'goal')):
        a_min, a_max, m_min, m_max, S = statistics[index]
        plus = a_min + RADIUS * S
        lower = tanh_bounds(plus)[0]
        if lower >= m_max + RADIUS:
            return {'kind': 'H_upper_corner_outside_strict_region', 'row_index': index,
                    'state': state, 'member_count': len(midpoints), 'a_min': str(a_min),
                    'a_max': str(a_max), 'S': str(S), 'm_min': str(m_min), 'm_max': str(m_max),
                    'corner_argument': str(plus), 'H_lower40': compact(lower),
                    'threshold': str(m_max + RADIUS), 'comparison': 'exact H_lower>=threshold',
                    'first_failure_reason_order_claim': False}
        minus = a_max - RADIUS * S
        upper = tanh_bounds(minus)[1]
        if upper <= m_min - RADIUS:
            return {'kind': 'H_lower_corner_outside_strict_region', 'row_index': index,
                    'state': state, 'member_count': len(midpoints), 'a_min': str(a_min),
                    'a_max': str(a_max), 'S': str(S), 'm_min': str(m_min), 'm_max': str(m_max),
                    'corner_argument': str(minus), 'H_upper40': compact(upper, True),
                    'threshold': str(m_min - RADIUS), 'comparison': 'exact H_upper<=threshold',
                    'first_failure_reason_order_claim': False}
    return None


def coverage(negative_ledger, epsilon, first_tick):
    require(epsilon in EPSILONS and type(first_tick) is int and 0 <= first_tick <= 6144,
            'coverage epsilon/positive tick')
    expected = 0
    ranges = []
    for entry in negative_ledger:
        require(set(entry) == {'first_tick', 'last_tick', 'epsilons', 'witness', 'journal_sequence'},
                'negative ledger fields')
        lo, hi = entry['first_tick'], entry['last_tick']
        require(type(lo) is int and type(hi) is int and 0 <= lo <= hi <= 6144,
                'negative ledger range')
        masks = entry['epsilons']
        require(isinstance(masks, list) and masks and len(set(masks)) == len(masks)
                and all(mask in EPSILONS for mask in masks), 'negative epsilon mask')
        if epsilon not in masks:
            continue
        require(lo == expected and hi < first_tick, 'predecessor gap/overlap/beyondpositive')
        expected = hi + 1
        ranges.append([lo, hi])
    require(expected == first_tick, 'incomplete predecessor coverage')
    return {'epsilon_p_exact': epsilon, 'first_tick': first_tick,
            'negative_range': [0, first_tick - 1] if first_tick else [],
            'negative_tick_count': expected, 'ranges': ranges,
            'gap_count': 0, 'overlap_count': 0, 'complete': True}


def record_first(case, first_ticks):
    require(type(case['tick']) is int and 0 <= case['tick'] <= 6144, 'positive tick type/range')
    require(isinstance(case['gates'], list) and len(case['gates']) == 2, 'two point gates required')
    negatives, positives = [], []
    for epsilon, gate in zip(EPSILONS, case['gates']):
        require(gate['epsilon_p_exact'] == epsilon and gate['status'] in
                {'NOT_CERTIFIED', 'CERTIFIED_WITHIN_EPS'}, 'point gate identity/status')
        if first_ticks[epsilon] is not None:
            continue
        if gate['status'] == 'CERTIFIED_WITHIN_EPS':
            first_ticks[epsilon] = case['tick']
            positives.append(epsilon)
        else:
            negatives.append(epsilon)
    return negatives, positives


def bind(repo, protocol, proposal, guard):
    require(protocol['schema'] == 'HCCONFirstConvergenceGateProtocol.v1'
            and protocol['state_order'] == ORDER and protocol['range'] == FIXED_RANGE
            and protocol['initial_x'] == '0' and protocol['epsilon_p_exact'] == EPSILONS,
            'fixed protocol identity/range')
    refs = {ref['path']: ref for ref in protocol['sources']}
    require(len(protocol['sources']) == len(refs) == 26, '26 unique source pins required')
    sys.dont_write_bytecode = True
    # Bootstrap pin validation is implemented without importing unpinned helper bytes.
    data = {}
    for name, ref in refs.items():
        guard()
        require(set(ref) == {'path', 'sha256', 'bytes'} and isinstance(name, str)
                and not Path(name).is_absolute() and '..' not in Path(name).parts,
                'source pin path/fields')
        path = (repo / name).resolve()
        require(path.is_relative_to(repo), 'source pin outside repository')
        raw = path.read_bytes()
        require(type(ref['bytes']) is int and len(raw) == ref['bytes']
                and digest(raw) == ref['sha256'], 'source bytes/hash mismatch')
        data[name] = raw
    gate = helper(data, GATE_CHECKER, repo)
    old_protocol = decode(data[GATE_PROTOCOL])
    require(protocol['old_gate_protocol'] == refs[GATE_PROTOCOL]
            and digest(data[GATE_PROTOCOL]) == gate['PROTOCOL_SHA']
            and protocol['raw'] == old_protocol['raw'], 'old gate protocol/raw binding')
    for key in ('state_order', 'network_id', 'initial_x', 'sample_id', 'score_hex', 'drive_hex',
                'region', 'norm', 'epsilon_p_exact', 'arithmetic', 'bound_pair'):
        require(protocol[key] == old_protocol[key], 'fixed recipe differs: ' + key)
    require(set(refs) == {ref['path'] for ref in old_protocol['sources']} |
            {GATE_PROTOCOL, GATE_RECORD, GATE_CHECKER, 'tools/analysis/on_convergence_gate.py'},
            '26-source closure differs')
    gate['fields'](proposal, {'schema', 'protocol_sha256', 'sample_id', 'score_hex',
                            'drive_hex', 'range', 'dependency_records'}, 'proposal')
    require(proposal['schema'] == 'HCCONFirstConvergenceGateProposal.v1'
            and proposal['protocol_sha256'] == PROTOCOL_SHA
            and proposal['range'] == FIXED_RANGE
            and all(type(proposal['range'][key]) is int for key in FIXED_RANGE)
            and proposal['dependency_records'] == [refs[path] for path in DEPENDENCIES],
            'proposal schema/range/ordered dependencies')
    gate['sample_binding'](proposal, protocol)
    old_refs, records, model, roots, model_digest = gate['load_binding'](repo, old_protocol, guard)
    require(all(refs[name] == ref for name, ref in old_refs.items()), 'old22 closure differs')
    record = decode(data[GATE_RECORD])
    gate['frozen_binding'](record, old_protocol, GATE_PROTOCOL,
                          'tools/analysis/on_convergence_gate.py', GATE_CHECKER, refs)
    check = record['independent_verification']
    require(record['schema'] == 'HCCONConvergenceGateCertificates.v1'
            and check['schema'] == 'HCCONConvergenceGateCheck.v1'
            and check['accepted'] is True and check['status'] == 'CERTIFIED_ANALYSIS'
            and check['protocol_sha256'] == refs[GATE_PROTOCOL]['sha256']
            and check['checker_pin'] == gate['file_pin'](repo / GATE_CHECKER)
            and check['source_pins'] == old_protocol['sources']
            and check['raw_pins'] == old_protocol['raw']
            and check['model_digest'] == model_digest and check['state_order'] == ORDER
            and check['epsilon_p_exact'] == EPSILONS and check['all7'] is True,
            'old gate accepted source/model proof differs')
    old_proposal_bytes = (json.dumps(record['proposal'], ensure_ascii=False, indent=2,
                                    allow_nan=False) + '\n').encode('utf-8')
    require(check['proposal_sha256'] == digest(old_proposal_bytes), 'old proposal digest differs')
    old = helper(data, 'tools/analysis/check_on_real_stop.py', repo)
    escape_helper = helper(data, 'tools/analysis/check_on_real_escape.py', repo)
    native = decode(data[NATIVE_RECORD])
    native_protocol = decode(data[old['NATIVE_PROTOCOL']])
    require(native_protocol['initial_p'] == '1/2', 'initial p is not1/2')
    inventory = assemble_boxes(native, native_protocol, records[STOP_RECORD],
                               records[ESCAPE_RECORD], refs, old, escape_helper)
    require(len(check['cases']) == len(record['proposal']['cases']) == 2, 'old gate case inventory')
    for case, spec in zip(record['proposal']['cases'], gate['CASE_SPECS']):
        gate['case_binding'](case, spec, records[spec['record']], refs[spec['record']])
    high = check['cases'][1]
    require(high['id'] == 'high6144' and type(high['tick']) is int and high['tick'] == 6144
            and high['x_box'] == inventory[6144]['x_box']
            and high['record_pin'] == refs[ESCAPE_RECORD]
            and high['region'] == record['proposal']['cases'][1]['region']
            and high['all7_strict_entry'] is True
            and high['region_valid'] is True and high['local_proof']['accepted'] is True
            and high['paired_bound']['evaluated'] is True
            and high['current_residual']['all7'] is True
            and high['current_residual']['current_not_previous_tick_delta'] is True
            and len(high['gates']) == 2
            and all(g['epsilon_p_exact'] == eps and g['status'] == 'CERTIFIED_WITHIN_EPS'
                    for g, eps in zip(high['gates'], EPSILONS)), 'old6144 positive binding')
    return gate, roots, model, model_digest, refs, inventory


def verify(args, result):
    require(math.isfinite(args.remaining_seconds) and 0 < args.remaining_seconds <= 1200,
            'remaining budget outside0..1200')
    started = time.monotonic()
    started_utc = datetime.now(timezone.utc)
    deadline = started_utc + timedelta(seconds=args.remaining_seconds)
    counters = {'scalar_proof_calls': 0, 'dependency_scalar_checks': 0,
                'full_gate_checks': 0, 'group_trials': 0, 'group_rejections': 0}
    result.update(first_ticks={eps: None for eps in EPSILONS}, cases=[], negative_ledger=[],
                  counters=counters, started_at_utc=started_utc.isoformat(),
                  deadline_utc=deadline.isoformat(), fixed_range=FIXED_RANGE)

    def guard():
        require(time.monotonic() - started < args.remaining_seconds
                and datetime.now(timezone.utc) < deadline, 'absolute scientific budget expired')
        require(counters['scalar_proof_calls'] <= 65536
                and counters['full_gate_checks'] <= 6145, 'proof-call cap exceeded')

    guard()
    journal_path = Path(str(args.output) + '.partial.jsonl')
    require(not Path(args.output).exists() and not journal_path.exists(), 'output/journal already exists')
    require(args.protocol_sha256 == PROTOCOL_SHA, 'fixed protocol argument differs')
    protocol_data = Path(args.protocol).read_bytes()
    require(digest(protocol_data) == PROTOCOL_SHA, 'protocol bytes/hash differs')
    protocol = decode(protocol_data)
    proposal_data = Path(args.input).read_bytes()
    proposal = decode(proposal_data)
    repo = Path(args.repo).resolve()
    # The pinned old loader performs one positive tanh_enclosure binding sanity check.
    counters['dependency_scalar_checks'] = counters['scalar_proof_calls'] = 1
    gate, roots, model, model_digest, refs, inventory = bind(repo, protocol, proposal, guard)
    result.update(proposal_sha256=digest(proposal_data), source_pins=protocol['sources'],
                  raw_pins=protocol['raw'], dependency_records=[refs[p] for p in DEPENDENCIES],
                  old_gate_record=refs[GATE_RECORD], model_digest=model_digest, state_order=ORDER,
                  sample_id=protocol['sample_id'], norm=protocol['norm'], epsilon_p_exact=EPSILONS,
                  boxes_digest=digest(canonical(inventory)), all7=True,
                  old_trajectory_rerun=0, native_replays=0, prior_census_rerun=False,
                  fresh_scalar_count_scope='One pinned dependency tanh_enclosure sanity check; '
                    'then every roots.tanh_bounds invocation, including negative-argument recursion, '
                    'group witnesses, full local root checks and current wholeB residuals; cacheOFF.')
    current = [gate['box'](entry['x_box']) for entry in inventory]
    regions, midpoints, entries = [], [], []
    for box in current:
        guard()
        region = region_for(box)
        lower, upper, _ = gate['region_geometry'](region, box)
        regions.append(region)
        midpoints.append([(lo + hi) / 2 for lo, hi in box])
        entries.append(all(lo < bl <= bh < hi for lo, hi, (bl, bh)
                           in zip(lower, upper, box)))
    result['geometry_prevalidated_ticks'] = 6145
    result['all7_entry_false_ticks'] = [t for t, entry in enumerate(entries) if not entry]
    original_tanh = roots['tanh_bounds']

    def counted_tanh(value):
        guard()
        require(counters['scalar_proof_calls'] < 65536, 'scalar proof-call cap exhausted')
        counters['scalar_proof_calls'] += 1
        answer = original_tanh(value)
        guard()
        return answer
    # Pinned functions share this globals dict; recursive calls therefore enter this wrapper.
    roots['tanh_bounds'] = counted_tanh
    result['journal_path'] = str(journal_path.resolve())
    sequence = 0
    last_examined = -1
    with journal_path.open('x', encoding='utf-8', newline='\n') as journal:
        def commit(value):
            nonlocal sequence
            guard()
            value = dict(value, sequence=sequence)
            journal.write(json.dumps(value, ensure_ascii=False, allow_nan=False) + '\n')
            journal.flush()
            os.fsync(journal.fileno())
            sequence += 1
            guard()
            return value['sequence']

        commit({'kind': 'source_bound_header', 'protocol_sha256': PROTOCOL_SHA,
                'proposal_sha256': result['proposal_sha256'], 'model_digest': model_digest,
                'boxes_digest': result['boxes_digest'], 'fixed_range': FIXED_RANGE,
                'dependency_records': result['dependency_records']})

        def add_negative(lo, hi, masks, witness):
            entry = {'first_tick': lo, 'last_tick': hi, 'epsilons': masks, 'witness': witness}
            index = commit({'kind': 'negative', **entry, 'first_ticks': result['first_ticks']})
            result['negative_ledger'].append(dict(entry, journal_sequence=index))

        def visit(lo, hi):
            nonlocal last_examined
            guard()
            masks = [eps for eps in EPSILONS if result['first_ticks'][eps] is None]
            if not masks:
                return
            if lo < hi:
                counters['group_trials'] += 1
                witness = group_proof(midpoints[lo:hi + 1], model, counted_tanh, guard)
                if witness is not None:
                    counters['group_rejections'] += 1
                    add_negative(lo, hi, masks, witness)
                    last_examined = hi
                    return
                middle = (lo + hi) // 2
                visit(lo, middle)
                visit(middle + 1, hi)
                return
            require(counters['full_gate_checks'] < 6145, 'full gate-check cap exhausted')
            counters['full_gate_checks'] += 1
            pin = refs[NATIVE_RECORD if lo <= 160 else STOP_RECORD if lo <= 2048 else ESCAPE_RECORD]
            case = {'id': f'tick{lo}', 'tick': lo, 'record_pin': pin,
                    'x_box': inventory[lo]['x_box'], 'region': regions[lo]}
            analyzed = gate['analyze_case'](case, current[lo], model, roots, guard)
            pending = dict(result['first_ticks'])
            negatives, positives = record_first(analyzed, pending)
            index = commit({'kind': 'full_point', 'case': analyzed, 'first_ticks': pending,
                            'new_positive_epsilons': positives})
            result['first_ticks'].update(pending)
            if positives:
                result['cases'].append({'epsilons': positives, 'full_check': analyzed,
                                        'journal_sequence': index})
            if negatives:
                add_negative(lo, lo, negatives, {'kind': 'full_gate_NOT_CERTIFIED',
                             'full_point_journal_sequence': index,
                             'gates': [g for g in analyzed['gates']
                                       if g['epsilon_p_exact'] in negatives]})
            last_examined = lo

        for lo in range(0, 6145, 64):
            visit(lo, min(lo + 63, 6144))
            if all(result['first_ticks'][eps] is not None for eps in EPSILONS):
                break
        guard()
        require(all(result['first_ticks'][eps] is not None for eps in EPSILONS),
                'fixed range exhausted without both firsts')
        require(result['first_ticks'][EPSILONS[0]] <= result['first_ticks'][EPSILONS[1]],
                'epsilon nesting first-tick order failed')
        result['coverage'] = [coverage(result['negative_ledger'], eps, result['first_ticks'][eps])
                              for eps in EPSILONS]
        result['unexamined_after_both_stop'] = ([last_examined + 1, 6144]
                                               if last_examined < 6144 else [])
        result['negative_ledger_digest'] = digest(canonical(result['negative_ledger']))
        result['method_limits'] = protocol['scope_limits']
        result['accepted'] = True
        result['status'] = 'CERTIFIED_EARLIEST_FIXED_GATE'
        result['elapsed_seconds'] = time.monotonic() - started
        commit({'kind': 'complete', 'first_ticks': result['first_ticks'],
                'negative_ledger_digest': result['negative_ledger_digest'],
                'coverage': result['coverage'], 'counters': counters})
    guard()
    return result


def atomic_output(path, result):
    path = Path(path).resolve()
    require(not path.exists(), 'output already exists')
    temporary = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    with temporary.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
        stream.flush()
        os.fsync(stream.fileno())
    os.rename(temporary, path)


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError(message)


def main():
    result = {'schema': 'HCCONFirstConvergenceGateCheck.v1', 'accepted': False,
              'status': 'INCONCLUSIVE', 'protocol_sha256': PROTOCOL_SHA}
    checker_data = Path(__file__).read_bytes()
    result['checker_pin'] = {'path': str(Path(__file__).resolve()),
                             'sha256': digest(checker_data), 'bytes': len(checker_data)}
    parser = Parser()
    for name in ('repo', 'protocol', 'protocol-sha256', 'input', 'output'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--remaining-seconds', type=float, default=1200)
    args = None
    try:
        args = parser.parse_args()
        verify(args, result)
    except (ValueError, KeyError, TypeError, IndexError, OSError, OverflowError, RecursionError) as error:
        result.update(accepted=False, status='INCONCLUSIVE', reason=str(error))
    if args is None:
        arguments = sys.argv[1:]
        if '--output' in arguments and arguments.index('--output') + 1 < len(arguments):
            output = arguments[arguments.index('--output') + 1]
        else:
            output = next((arg.split('=', 1)[1] for arg in arguments
                           if arg.startswith('--output=')), None)
    else:
        output = args.output
    if result.get('journal_path') and Path(result['journal_path']).is_file():
        path = Path(result['journal_path'])
        data = path.read_bytes()
        result['journal_pin'] = {'path': str(path.resolve()), 'sha256': digest(data), 'bytes': len(data)}
    if result.get('first_ticks'):
        progress = []
        for eps in EPSILONS:
            first = result['first_ticks'][eps]
            if first is not None:
                try:
                    progress.append(coverage(result['negative_ledger'], eps, first))
                except ValueError as error:
                    progress.append({'epsilon_p_exact': eps, 'first_tick': first,
                                     'complete': False, 'reason': str(error)})
            else:
                progress.append({'epsilon_p_exact': eps, 'first_tick': None, 'complete': False,
                                 'committed_negative_ranges': [[e['first_tick'], e['last_tick']]
                                    for e in result['negative_ledger'] if eps in e['epsilons']]})
        result['coverage_progress'] = progress
    if output:
        try:
            atomic_output(output, result)
        except (ValueError, OSError) as error:
            result.update(accepted=False, status='INCONCLUSIVE', reason='output: ' + str(error))
    print(json.dumps({'accepted': result['accepted'], 'status': result['status'],
                      'reason': result.get('reason')}, ensure_ascii=False), flush=True)
    if not result['accepted']:
        raise SystemExit(2)


if __name__ == '__main__':
    main()
