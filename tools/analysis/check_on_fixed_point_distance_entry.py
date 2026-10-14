"""고정된 과거 인증의 유리수 anchor와 전체 ordered7 거리만 검산한다."""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from fractions import Fraction as Q
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sys
import time

PROTOCOL_SHA = '4c2fe642852678cbfd6a84eca4138ee382de01a9a9dfb6ee16d6c6df61da6e9e'
BASE = 'experiments/exp-62-top-down/'
FIRST_PROTOCOL = BASE + 'on-first-convergence-gate-protocol-20261014.json'
FIRST_RECORD = BASE + 'on-first-convergence-gate-certificates-20261014.json'
FIRST_CHECKER = 'tools/analysis/check_on_first_convergence_gate.py'
FIRST_PRODUCER = 'tools/analysis/on_first_convergence_gate.py'
GATE_RECORD = BASE + 'on-convergence-gate-certificates-20261014.json'
ORDER = ['e:0', 'e:1', 'e:2', 'e:3', 'p:0:0', 'p:0:1', 'goal']
EPSILONS = ['1/1000000', '1/100000000']
FIXED_RANGE = {'first_tick': 0, 'last_tick': 6144}
GATE_TICKS = dict(zip(EPSILONS, (5161, 5173)))
PUBLIC = re.compile(r'-?(?:0|[1-9][0-9]*)\.[0-9]{40}\Z')
ULP = Q(1, 10**40)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def decode(data):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, 'duplicate JSON key')
            result[key] = value
        return result
    return json.loads(data, object_pairs_hook=unique,
                      parse_constant=lambda value: require(False, 'nonfinite JSON'))


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


def file_pin(path):
    path = Path(path).resolve()
    data = path.read_bytes()
    return {'path': str(path), 'sha256': digest(data), 'bytes': len(data)}


def pinned(repo, ref):
    require(isinstance(ref, dict) and set(ref) == {'path', 'sha256', 'bytes'}, 'pin fields')
    require(isinstance(ref['path'], str) and isinstance(ref['sha256'], str)
            and re.fullmatch('[0-9a-f]{64}', ref['sha256'])
            and type(ref['bytes']) is int and ref['bytes'] > 0, 'pin types')
    relative = Path(ref['path'])
    require(not relative.is_absolute() and '..' not in relative.parts, 'pin traversal')
    path = (repo / relative).resolve()
    require(path.is_relative_to(repo), 'pin outside repository')
    data = path.read_bytes()
    require(len(data) == ref['bytes'] and digest(data) == ref['sha256'], 'pin bytes/hash')
    return data


def public(value):
    require(isinstance(value, str) and PUBLIC.fullmatch(value), 'public40 format')
    result = Q(value)
    require(not (result == 0 and value.startswith('-')), 'negative zero')
    return result


def outward(value, upper=True):
    value = Q(value)
    scaled = value.numerator * 10**40
    integer = -((-scaled) // value.denominator) if upper else scaled // value.denominator
    whole, decimal = divmod(abs(integer), 10**40)
    return ('-' if integer < 0 else '') + f'{whole}.{decimal:040d}'


def full_box(box):
    require(isinstance(box, (list, tuple)) and len(box) == 7, 'whole7 box')
    result = []
    for pair in box:
        require(isinstance(pair, (list, tuple)) and len(pair) == 2, 'endpoint pair')
        lo, hi = map(Q, pair)
        require(-1 <= lo <= hi <= 1, 'endpoint domain/order')
        result.append((lo, hi))
    return result


def root_anchor(high, model):
    """인증된 enclosure를 신뢰하고 새 유리수 관계와 geometry를 확인한다."""
    b, G, d = model
    require(len(b) == len(G) == 7 and all(len(row) == 7 for row in G)
            and 0 < d <= 1, 'whole7 model/damping')
    require(high['id'] == 'high6144' and type(high['tick']) is int and high['tick'] == 6144
            and high['all7_strict_entry'] is True and high['region_valid'] is True,
            'accepted terminal entry')
    B = full_box(high['x_box'])
    region, proof = high['region'], high['local_proof']
    require(region['weights'] == [1]*7 and all(type(w) is int for w in region['weights']),
            'all7 unweighted norm')
    require(len(region['lower']) == len(region['upper']) == 7, 'region dimensions')
    C = full_box(list(zip(region['lower'], region['upper'])))
    require(proof['accepted'] is True and proof['exact_qH_lt_one'] is True
            and proof['exact_qF_lt_one'] is True, 'accepted contraction missing')
    require(all(len(proof[key]) == 7 for key in ('H_lower', 'H_upper', 'slope_upper')),
            'whole7 contraction witnesses')
    mids = [(lo+hi)/2 for lo, hi in B]
    slopes = list(map(public, proof['slope_upper']))
    require(all(0 <= value <= 1 for value in slopes), 'slope range')
    for i, ((lo, hi), (bl, bh)) in enumerate(zip(C, B)):
        require(-1 < lo < bl <= bh < hi < 1 and lo == mids[i]-Q(1, 1000000)
                and hi == mids[i]+Q(1, 1000000), 'C/B strict entry/fixed geometry')
        hl, hh = public(proof['H_lower'][i]), public(proof['H_upper'][i])
        require(lo < hl <= hh < hi, 'stored H strict self-map enclosure')
    qH = public(proof['qH_upper'])
    require(0 <= qH < 1, 'strict qH')
    # Exact slopes and qH were rounded separately. This is consistency, not a new qH proof.
    q_lo = max(sum(abs(v) for v in row)*max(Q(0), s-ULP) for row, s in zip(G, slopes))
    q_hi = max(sum(abs(v) for v in row)*s for row, s in zip(G, slopes))
    require(q_lo <= qH <= q_hi+ULP, 'independent slope/qH rounding inconsistency')
    residual, pair = high['current_residual'], high['paired_bound']
    require(residual['all7'] is True and residual['current_not_previous_tick_delta'] is True
            and residual['definition'] == 'sup_B ||H(x)-x||_infinity outer interval'
            and all(len(residual[key]) == 7 for key in
                    ('H_B_lower', 'H_B_upper', 'coordinate_residual_x_upper')),
            'whole current B residual contract')
    coordinate = []
    for i, (lo, hi) in enumerate(B):
        hl, hh = public(residual['H_B_lower'][i]), public(residual['H_B_upper'][i])
        require(-1 <= hl <= hh <= 1, 'stored H(B) enclosure order')
        coordinate.append(max(abs(hl-hi), abs(hh-lo)))
        # Grid30 B endpoints make floor/ceil40 commute with these residual differences.
        require(public(residual['coordinate_residual_x_upper'][i]) == coordinate[-1],
                'coordinate residual algebra')
    eH = Q(residual['eH_x_cert'])
    require(eH == max(coordinate) == public(residual['eH_x_upper40']), 'whole residual algebra')
    qF, eF = 1-d+d*qH, d*eH/2
    E = eH/(2*(1-qH))
    require(0 <= qF < 1 and E >= 0 and E == eF/(1-qF), 'paired damping identity')
    require(pair['evaluated'] is True and pair['paired_damping_identity'] is True
            and Q(pair['qH_cert']) == qH and Q(pair['qF_coupled']) == qF
            and Q(pair['E_exact']) == E and Q(residual['eF_p_coupled']) == eF,
            'stored paired algebra')
    require(pair['qF_upper40'] == proof['qF_upper'] == outward(qF)
            and public(pair['qF_upper40']) < 1 and pair['E_upper40'] == outward(E)
            and residual['eF_p_upper40'] == outward(eF), 'paired public outward witnesses')
    R = 2*E
    A = [(max(lo, m-R), min(hi, m+R)) for (lo, hi), m in zip(C, mids)]
    require(all(lo <= hi for lo, hi in A), 'empty root anchor')
    full_box(A)
    return {'tick': 6144, 'midpoint_x_exact': list(map(str, mids)),
            'radius_x_exact': str(R), 'tail_E_p_exact': str(E),
            'qH_cert': str(qH), 'qF_coupled': str(qF),
            'x_box_exact': [[str(lo), str(hi)] for lo, hi in A],
            'x_box_outward40': [[outward(lo, False), outward(hi)] for lo, hi in A],
            'enclosure_basis': 'accepted pinned C self-map/contraction and wholeB residual; m in B subset C',
            'rounding_check_is_new_qH_proof': False}


def distance_bounds(B, A):
    B, A = full_box(B), full_box(A)
    lower = max(max(Q(0), lo-ah, al-hi) for (lo, hi), (al, ah) in zip(B, A))/2
    upper = max(max(abs(lo-ah), abs(hi-al)) for (lo, hi), (al, ah) in zip(B, A))/2
    require(0 <= lower <= upper, 'distance enclosure order')
    return lower, upper


def classify(lower, upper, epsilon):
    lower, upper, epsilon = Q(lower), Q(upper), Q(epsilon)
    require(0 <= lower <= upper and epsilon > 0, 'distance/epsilon domain')
    return 'INSIDE' if upper <= epsilon else ('OUTSIDE' if lower > epsilon else 'AMBIGUOUS')


def summarize(rows, epsilon, gate_tick, tail_E):
    require(isinstance(rows, list) and rows and type(gate_tick) is int and gate_tick >= 0,
            'summary inventory/gate tick')
    eps, tail_E = Q(epsilon), Q(tail_E)
    require(eps > 0 and tail_E >= 0, 'summary epsilon/tail')
    states, a, inside = [], None, None
    for tick, row in enumerate(rows):
        require(type(row['tick']) is int and row['tick'] == tick, 'summary gap/order/duplicate')
        lo, hi = Q(row['lower_p_exact']), Q(row['upper_p_exact'])
        state = classify(lo, hi, eps)
        states.append(state)
        if a is None and lo <= eps:
            a = tick
        if inside is None and state == 'INSIDE':
            inside = tick
    first = inside if inside is not None and all(v == 'OUTSIDE' for v in states[:inside]) else None
    if first is not None:
        require(first <= gate_tick, 'exact distance entry later than trusted sufficient gate')
    permanent = (first is not None and all(v == 'INSIDE' for v in states[first:]) and tail_E <= eps)
    delay = gate_tick-first if first is not None else None
    return {'epsilon_p_exact': str(eps), 'first_tick': first,
            'status': 'CERTIFIED_EARLIEST_DISTANCE_ENTRY' if first is not None else 'UNRESOLVED_BRACKET',
            'bracket': {'lower_tick': a, 'upper_tick': inside},
            'predecessor_coverage': {'range': [0, first-1] if first else [],
                                     'count': first, 'complete': first is not None},
            'old_fixed_gate_first_tick': gate_tick, 'fixed_gate_delay_ticks': delay,
            'fixed_gate_delay_bracket': [gate_tick-inside if inside is not None else None,
                                       gate_tick-a if a is not None else None],
            'permanence_status': 'CERTIFIED_FROM_EXACT_FIRST' if permanent else 'NOT_ESTABLISHED',
            'first_permanent_tick': first if permanent else None,
            'stored_suffix_terminal_tick': len(rows)-1, 'infinite_tail_E_le_epsilon': tail_E <= eps,
            'time_monotonicity_assumed': False,
            'ambiguous_ticks': [t for t, state in enumerate(states) if state == 'AMBIGUOUS']}


def self_check():
    """실제 궤적을 읽지 않는 작은 합성 guard 검사."""
    B, A = [(Q(0), Q(0))]*7, [(Q(0), Q(0))]*7
    B[2] = (Q(1, 2), Q(1, 2))
    assert distance_bounds(B, A) == (Q(1, 4), Q(1, 4))
    assert classify(Q(1, 4), Q(1, 4), Q(1, 4)) == 'INSIDE'
    assert classify(Q(1, 4), Q(1, 2), Q(1, 4)) == 'AMBIGUOUS'
    assert classify(Q(1, 3), Q(1, 2), Q(1, 4)) == 'OUTSIDE'
    rows = [{'tick': 0, 'lower_p_exact': '1/3', 'upper_p_exact': '1/2'},
            {'tick': 1, 'lower_p_exact': '1/4', 'upper_p_exact': '1/3'},
            {'tick': 2, 'lower_p_exact': '0', 'upper_p_exact': '1/4'}]
    result = summarize(rows, Q(1, 4), 3, Q(0))
    assert result['first_tick'] is None and result['bracket'] == {'lower_tick': 1, 'upper_tick': 2}
    rows[1]['upper_p_exact'] = '1/4'
    result = summarize(rows, Q(1, 4), 3, Q(0))
    assert result['first_tick'] == 1 and result['first_permanent_tick'] == 1


def load_binding(repo, protocol, guard):
    refs = {ref['path']: ref for ref in protocol['sources']}
    require(len(refs) == len(protocol['sources']) == 30, '30 unique source pins')
    data = {}
    for name, ref in refs.items():
        guard()
        data[name] = pinned(repo, ref)
    require(len(protocol['raw']) == 2, 'two raw pins')
    for ref in protocol['raw']:
        guard()
        pinned(repo, {key: ref[key] for key in ('path', 'sha256', 'bytes')})
    # No helper executes until the complete new source and raw inventory was checked.
    sys.dont_write_bytecode = True
    scope = {'__name__': 'distance_entry_legacy_binding', '__file__': str(repo/FIRST_CHECKER)}
    exec(compile(data[FIRST_CHECKER], str(repo/FIRST_CHECKER), 'exec'), scope)
    prior_protocol, prior_record = decode(data[FIRST_PROTOCOL]), decode(data[FIRST_RECORD])
    require(set(refs) == {ref['path'] for ref in prior_protocol['sources']} |
            {FIRST_PROTOCOL, FIRST_RECORD, FIRST_CHECKER, FIRST_PRODUCER}, 'source closure')
    require(protocol['legacy_first_gate_protocol'] == refs[FIRST_PROTOCOL]
            and protocol['raw'] == prior_protocol['raw']
            and digest(data[FIRST_PROTOCOL]) == scope['PROTOCOL_SHA'], 'legacy protocol/raw pin')
    gate, roots, model, model_digest, old_refs, inventory = scope['bind'](
        repo, prior_protocol, prior_record['proposal'], guard)
    require(all(refs[name] == ref for name, ref in old_refs.items()), 'legacy closure mismatch')
    gate['frozen_binding'](prior_record, prior_protocol, FIRST_PROTOCOL,
                          FIRST_PRODUCER, FIRST_CHECKER, refs)
    checked = prior_record['independent_verification']
    require(prior_record['schema'] == 'HCCONFirstConvergenceGateCertificates.v1'
            and checked['schema'] == 'HCCONFirstConvergenceGateCheck.v1'
            and checked['accepted'] is True and checked['status'] == 'CERTIFIED_EARLIEST_FIXED_GATE'
            and checked['protocol_sha256'] == refs[FIRST_PROTOCOL]['sha256']
            and checked['checker_pin'] == file_pin(repo/FIRST_CHECKER)
            and checked['model_digest'] == model_digest and checked['state_order'] == ORDER
            and checked['sample_id'] == protocol['sample_id'] and checked['norm'] == protocol['norm']
            and checked['all7'] is True and checked['epsilon_p_exact'] == EPSILONS
            and checked['source_pins'] == prior_protocol['sources']
            and checked['raw_pins'] == protocol['raw'] and checked['first_ticks'] == GATE_TICKS
            and checked['fixed_range'] == FIXED_RANGE
            and checked['dependency_records'] == [refs[path] for path in scope['DEPENDENCIES']],
            'trusted first gate accepted binding')
    proposal_bytes = (json.dumps(prior_record['proposal'], ensure_ascii=False, indent=2,
                                allow_nan=False)+'\n').encode('utf-8')
    require(checked['proposal_sha256'] == digest(proposal_bytes), 'trusted first proposal digest')
    require(checked['coverage'] == [scope['coverage'](checked['negative_ledger'], eps, GATE_TICKS[eps])
                                  for eps in EPSILONS], 'trusted first gate coverage')
    require(checked['boxes_digest'] == digest(canonical(inventory)), 'complete boxes digest')
    high = decode(data[GATE_RECORD])['independent_verification']['cases'][1]
    require(high['x_box'] == inventory[6144]['x_box'], 'anchor terminal binding')
    guard()
    return model, model_digest, inventory, high


def verify(args, result, guard):
    require(args.protocol_sha256 == PROTOCOL_SHA, 'protocol argument differs')
    protocol_data = Path(args.protocol).read_bytes()
    require(digest(protocol_data) == PROTOCOL_SHA, 'protocol fixed hash')
    protocol = decode(protocol_data)
    require(protocol['schema'] == 'HCCONFixedPointDistanceEntryProtocol.v1'
            and protocol['state_order'] == ORDER and protocol['range'] == FIXED_RANGE
            and protocol['initial_x'] == '0' and protocol['network_id'] == 'network-8'
            and protocol['epsilon_p_exact'] == EPSILONS and protocol['norm'] == 'p_infinity_all7'
            and type(protocol['anchor']['tick']) is int and protocol['anchor']['tick'] == 6144,
            'fixed protocol identity')
    proposal_data = Path(args.input).read_bytes()
    proposal = decode(proposal_data)
    require(set(proposal) == {'schema', 'protocol_sha256', 'sample_id', 'score_hex', 'drive_hex',
                              'range', 'anchor_tick', 'epsilon_p_exact'}, 'proposal fields')
    require(proposal['schema'] == 'HCCONFixedPointDistanceEntryProposal.v1'
            and proposal['protocol_sha256'] == PROTOCOL_SHA
            and proposal['range'] == FIXED_RANGE
            and all(type(proposal['range'][key]) is int for key in FIXED_RANGE)
            and type(proposal['anchor_tick']) is int and proposal['anchor_tick'] == 6144
            and proposal['epsilon_p_exact'] == EPSILONS
            and all(proposal[key] == protocol[key] for key in ('sample_id', 'score_hex', 'drive_hex')),
            'proposal identity/range')
    repo = Path(args.repo).resolve()
    result['counters']['binding_scalar_sanity'] = 1
    model, model_digest, inventory, high = load_binding(repo, protocol, guard)
    anchor = root_anchor(high, model)
    result.update(proposal_sha256=digest(proposal_data), source_pins=protocol['sources'],
                  raw_pins=protocol['raw'], model_digest=model_digest, state_order=ORDER,
                  sample_id=protocol['sample_id'], norm=protocol['norm'], all7=True,
                  boxes_digest=digest(canonical(inventory)), anchor=anchor,
                  old_first_gate_ticks=GATE_TICKS, epsilon_p_exact=EPSILONS,
                  trusted_dependencies=protocol['trusted_dependencies'], limits=protocol['scope_limits'],
                  old_trajectory_rerun=0, native_replays=0, prior_census_rerun=False)
    journal = Path(str(args.output)+'.partial.jsonl')
    result['journal_path'] = str(journal.resolve())
    with journal.open('x', encoding='utf-8', newline='\n') as stream:
        for tick, entry in enumerate(inventory):
            guard()
            require(type(entry['tick']) is int and entry['tick'] == tick, 'distance inventory tick')
            lower, upper = distance_bounds(entry['x_box'], anchor['x_box_exact'])
            row = {'tick': tick, 'lower_p_exact': str(lower), 'upper_p_exact': str(upper),
                   'lower_p_outward40': outward(lower, False), 'upper_p_outward40': outward(upper),
                   'classification': {eps: classify(lower, upper, Q(eps)) for eps in EPSILONS}}
            stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False)+'\n')
            result['distance_results'].append(row)
            result['counters']['distance_records'] += 1
            if (tick+1)%64 == 0 or tick == 6144:
                stream.flush()
                os.fsync(stream.fileno())
                result['counters']['committed_distance_records'] = tick+1
            guard()
    require(result['counters']['distance_records'] == 6145
            and result['counters']['committed_distance_records'] == 6145, 'incomplete full scan')
    summaries = [summarize(result['distance_results'], eps, GATE_TICKS[eps], anchor['tail_E_p_exact'])
                 for eps in EPSILONS]
    firsts = {entry['epsilon_p_exact']: entry['first_tick'] for entry in summaries}
    if all(value is not None for value in firsts.values()):
        require(firsts[EPSILONS[0]] <= firsts[EPSILONS[1]], 'epsilon first ordering')
    result.update(summaries=summaries, first_ticks=firsts, full_scan_complete=True,
                  accepted=True, status='CERTIFIED_EARLIEST_DISTANCE_ENTRY' if
                  all(value is not None for value in firsts.values()) else 'CERTIFIED_DISTANCE_BRACKETS')
    guard()


def main():
    parser = argparse.ArgumentParser()
    for name in ('repo', 'protocol', 'protocol-sha256', 'input', 'output'):
        parser.add_argument('--'+name, required=True)
    parser.add_argument('--remaining-seconds', type=float, default=120)
    args = parser.parse_args()
    started, started_utc = time.monotonic(), datetime.now(timezone.utc)
    valid_budget = math.isfinite(args.remaining_seconds) and 0 < args.remaining_seconds <= 120
    deadline = started_utc+timedelta(seconds=args.remaining_seconds) if valid_budget else started_utc
    result = {'schema': 'HCCONFixedPointDistanceEntryCheck.v1', 'accepted': False,
              'status': 'INCONCLUSIVE', 'protocol_sha256': args.protocol_sha256,
              'checker_pin': file_pin(__file__), 'started_at_utc': started_utc.isoformat(),
              'deadline_utc': deadline.isoformat(), 'first_ticks': {eps: None for eps in EPSILONS},
              'distance_results': [], 'full_scan_complete': False,
              'counters': {'binding_scalar_sanity': 0, 'distance_records': 0,
                           'committed_distance_records': 0, 'new_H_root_trajectory_native_census_runs': 0}}
    output, journal = Path(args.output), Path(str(args.output)+'.partial.jsonl')
    pending = Path(str(args.output)+'.pending')
    if output.exists() or journal.exists() or pending.exists():
        print(json.dumps({'accepted': False, 'status': 'INCONCLUSIVE', 'reason': 'immutable output/journal/pending exists'}))
        raise SystemExit(2)

    def guard():
        require(math.isfinite(args.remaining_seconds) and 0 < args.remaining_seconds <= 120,
                'remaining budget outside0..120')
        require(time.monotonic()-started < args.remaining_seconds
                and datetime.now(timezone.utc) < deadline, 'absolute budget expired')
        require(result['counters']['binding_scalar_sanity'] <= 1
                and result['counters']['distance_records'] <= 6145, 'frozen counter cap exceeded')

    try:
        guard()
        verify(args, result, guard)
        result['journal_pin'] = file_pin(journal)
        result['elapsed_seconds'] = time.monotonic()-started
        payload = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)+'\n'
        guard()
        with pending.open('x', encoding='utf-8', newline='\n') as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        guard()
        pending.rename(output)
    except (ValueError, KeyError, TypeError, IndexError, OSError, OverflowError, ZeroDivisionError) as error:
        result.update(accepted=False, status='INCONCLUSIVE', reason=str(error),
                      full_scan_complete=False, first_ticks={eps: None for eps in EPSILONS})
        result.pop('summaries', None)
        result['distance_results'] = result['distance_results'][:result['counters']['committed_distance_records']]
        if journal.exists():
            result['journal_pin'] = file_pin(journal)
        result['elapsed_seconds'] = time.monotonic()-started
        if not output.exists():
            with output.open('x', encoding='utf-8', newline='\n') as stream:
                json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
                stream.write('\n')
                stream.flush()
                os.fsync(stream.fileno())
    print(json.dumps({'accepted': result['accepted'], 'status': result['status'],
                      'reason': result.get('reason')}, ensure_ascii=False), flush=True)
    if not result['accepted']:
        raise SystemExit(2)


if __name__ == '__main__':
    main()
