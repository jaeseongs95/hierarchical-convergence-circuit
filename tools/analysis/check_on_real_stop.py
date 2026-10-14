"""한 점의 exactreal 유한 연장과 최초 종료를 검산한다. native 재생은 없다."""
from __future__ import annotations

import argparse
from fractions import Fraction as Q
import hashlib
import json
import math
from pathlib import Path
import re
import runpy
import sys
import time
from types import SimpleNamespace

ORDER = ['e:0', 'e:1', 'e:2', 'e:3', 'p:0:0', 'p:0:1', 'goal']
BASE = 'experiments/exp-62-top-down/'
NATIVE_PROTOCOL = BASE + 'on-native-stop-protocol-20261014.json'
NATIVE_RECORD = BASE + 'on-native-stop-certificates-20261014.json'
CRITICAL_PROTOCOL = BASE + 'on-critical-strip-protocol-20261013.json'
CRITICAL_RECORD = BASE + 'on-critical-strip-certificates-20261013.json'
NATIVE_CHECKER = 'tools/analysis/check_on_native_stop.py'
BASIN_CHECKER = 'tools/analysis/check_on_basins.py'
CRITICAL_CHECKER = 'tools/analysis/check_on_critical_strip.py'
FOLD_CHECKER = 'tools/analysis/check_on_fold.py'
SOURCES = {'src/hcr/dynamics.py', 'src/hcr/model.py', 'src/hcr/workspace.py',
           'src/hcr/runtime.py', 'tools/analysis/on_fixed_points.py', BASIN_CHECKER,
           NATIVE_CHECKER, CRITICAL_CHECKER, FOLD_CHECKER, NATIVE_PROTOCOL,
           NATIVE_RECORD, CRITICAL_PROTOCOL, CRITICAL_RECORD}
SAMPLE = {'sample_id': 'above_near', 'score_hex': '0x1.277babda5a221p-5',
          'drive_hex': '0x1.277babda5a221p-3'}
POLICY = {'id': 'exactreal_extended', 'tolerance_hex': '0x1.0c6f7a0b5ed8dp-20',
          'patience': 4, 'cap': 2048, 'margin_hex': '0x1.3333333333333p-2'}
GRID = re.compile(r'-?(?:0|[1-9][0-9]*)\.[0-9]{30}\Z')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def fields(value, expected, name):
    require(isinstance(value, dict) and set(value) == set(expected), name + ' fields mismatch')


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


def source_pin(repo, reference):
    fields(reference, {'path', 'sha256', 'bytes'}, 'source pin')
    require(isinstance(reference['path'], str) and isinstance(reference['sha256'], str)
            and re.fullmatch('[0-9a-f]{64}', reference['sha256'])
            and type(reference['bytes']) is int and reference['bytes'] > 0, 'invalid source pin')
    path = (repo / reference['path']).resolve()
    require(path.is_relative_to(repo), 'source path outside repository')
    data = path.read_bytes()
    require(len(data) == reference['bytes'] and hashlib.sha256(data).hexdigest() == reference['sha256'],
            'source hash/byte mismatch: ' + reference['path'])
    return data


def binary(value):
    require(type(value) in (int, float) and math.isfinite(value), 'invalid binary primitive')
    return Q(*float(value).as_integer_ratio())


def box(encoded):
    require(isinstance(encoded, list) and len(encoded) == 7, 'box must contain ordered7 states')
    result = []
    for pair in encoded:
        require(isinstance(pair, list) and len(pair) == 2, 'box endpoint pair')
        require(all(isinstance(s, str) and len(s) <= 34 and GRID.fullmatch(s) for s in pair),
                'invalid fixed30 endpoint')
        lo, hi = map(Q, pair)
        require(-1 <= lo <= hi <= 1 and not any(Q(s) == 0 and s.startswith('-') for s in pair),
                'box reversed/domain/negative zero')
        result.append((lo, hi))
    return result


def sample_binding(record, spec):
    require(all(record.get(key) == spec[key] == SAMPLE[key] for key in SAMPLE), 'sample binding mismatch')
    require(binary(float.fromhex(record['drive_hex'])) == 4 * binary(float.fromhex(record['score_hex'])),
            'score4 drive not exact')
    return True


def splice(prefix, suffix, prefixend, cap):
    require(type(cap) is int and cap == 2048 and isinstance(prefix, list) and len(prefix) == 160,
            'prefix/cap count mismatch')
    require(prefixend == prefix[-1], 'complete old B160 splice mismatch')
    require(isinstance(suffix, list) and len(suffix) == cap - 160, 'suffix count mismatch')
    for encoded in prefix:
        box(encoded)
    encoded_boxes = list(prefix)
    for n, entry in enumerate(suffix, 161):
        fields(entry, {'tick', 'x_box'}, 'suffix entry')
        require(type(entry['tick']) is int and entry['tick'] == n, 'suffix tick gap/order mismatch')
        box(entry['x_box'])
        encoded_boxes.append(entry['x_box'])
    return encoded_boxes


def distance_lower(goal_p_interval):
    require(isinstance(goal_p_interval, list) and len(goal_p_interval) == 2, 'goal interval dimensions')
    lo, hi = map(Q, goal_p_interval)
    require(0 <= lo <= hi <= 1, 'goal interval reversed/domain')
    return max(Q(0), Q(19, 20) - hi)


def lower_decimal(value):
    integer = value.numerator * 10 ** 30 // value.denominator
    whole, fraction = divmod(integer, 10 ** 30)
    return f'{whole}.{fraction:030d}'


def low_witness(stop, cap):
    if stop.get('status') != 'stable_decision':
        return False
    require(type(cap) is int and cap == 2048 and type(stop['tick']) is int
            and 1 <= stop['tick'] <= cap and type(stop['stable_steps']) is int
            and stop['stable_steps'] >= 4, 'invalid decided stop')
    distance = distance_lower(stop['goal_p_interval'])
    return Q(stop['goal_p_interval'][1]) < Q(1, 10) and distance > Q(17, 20)


def protocol_check(p):
    require(p.get('schema') == 'HCCONRealStopProtocol.v1' and p.get('state_order') == ORDER
            and p.get('network_id') == 'network-8' and p.get('initial_x') == '0'
            and type(p.get('prefix_ticks')) is int and p['prefix_ticks'] == 160
            and type(p.get('first_suffix_tick')) is int and p['first_suffix_tick'] == 161,
            'frozen graph/initial/prefix mismatch')
    sample_binding(p, p)
    require(p['policy'] == POLICY and all(type(p['policy'][k]) is int for k in ('cap', 'patience')),
            'frozen policy mismatch')
    require(p['arithmetic'] == {'decimal_precision': 80, 'interval_grid_places': 30,
                               'taylor_degree': 96, 'exact_tanh_cache': False}, 'frozen arithmetic mismatch')
    require(all(type(p['arithmetic'][k]) is int for k in ('decimal_precision', 'interval_grid_places', 'taylor_degree'))
            and p['arithmetic']['exact_tanh_cache'] is False, 'arithmetic field types')
    require(p['budget'] == {'max_suffix_transitions': 1888, 'max_total_transitions': 2048,
                           'wall_time_seconds_combined': 1800, 'auto_retry': False,
                           'adaptive_precision': False, 'cap_escalation': False}, 'frozen budget mismatch')
    require(all(type(p['budget'][k]) is int for k in ('max_suffix_transitions', 'max_total_transitions',
                                                     'wall_time_seconds_combined'))
            and all(p['budget'][k] is False for k in ('auto_retry', 'adaptive_precision', 'cap_escalation')),
            'budget field types')
    require(p['success'] == {'required_status': 'stable_decision', 'goal_p_upper_strict': '1/10',
                            'distance_to_all_real_equilibria_strict': '17/20',
                            'required_same_native_tick': False}, 'frozen success mismatch')
    require(isinstance(p['sources'], list) and len(p['sources']) == 13
            and {s['path'] for s in p['sources']} == SOURCES, 'source inventory mismatch')


def prior_binding(native, native_protocol, refs):
    require(native['schema'] == 'HCCONNativeStopCertificates.v1'
            and native['source_commit'] == native_protocol['source_commit']
            and native['protocol'] == refs[NATIVE_PROTOCOL], 'old prefix protocol/header mismatch')
    for section, schema in (('proposal', 'HCCONNativeStopProposal.v1'),
                            ('independent_verification', 'HCCONNativeStopCheck.v1')):
        require(native[section]['schema'] == schema
                and native[section]['protocol_sha256'] == refs[NATIVE_PROTOCOL]['sha256'],
                'old prefix result protocol mismatch')
    verified = native['independent_verification']
    require(verified['accepted'] is True and verified['sample_count'] == 11
            and verified['verified_real_transitions'] == 1760, 'old prefix not accepted')
    frozen = native['frozen_execution']
    require(frozen['protocol'] == refs[NATIVE_PROTOCOL]
            and frozen['numerical_runs_before_freeze'] == 0, 'old prefix frozen input mismatch')
    frozen_files = {ref['path']: ref for ref in frozen['files']}
    require(frozen_files[NATIVE_CHECKER] == refs[NATIVE_CHECKER]
            and frozen_files[NATIVE_PROTOCOL] == refs[NATIVE_PROTOCOL], 'old checker/protocol freeze mismatch')
    require(native_protocol['state_order'] == ORDER and native_protocol['initial_p'] == '1/2'
            and native_protocol['network_id'] == 'network-8'
            and native_protocol['arithmetic'] == {'decimal_precision': 80, 'interval_grid_places': 30,
                                                  'taylor_degree': 96}
            and native_protocol['budget']['real_prefix_ticks'] == 160, 'old prefix geometry mismatch')
    old_refs = {ref['path']: ref for ref in native_protocol['sources']}
    require(all(refs[path] == old_refs[path] for path in refs.keys() & old_refs.keys()),
            'old source pin differs')
    samples = [s for s in native['proposal']['samples'] if s['id'] == SAMPLE['sample_id']]
    analyses = [s for s in verified['samples'] if s['id'] == SAMPLE['sample_id']]
    specs = [s for s in native_protocol['scores'] if s['id'] == SAMPLE['sample_id']]
    require(len(samples) == len(analyses) == len(specs) == 1, 'old target inventory mismatch')
    target, analysis, spec = samples[0], analyses[0], specs[0]
    require(target['score_hex'] == spec['hex'] == SAMPLE['score_hex']
            and target['drive_hex'] == spec['drive_hex'] == SAMPLE['drive_hex'], 'old target value mismatch')
    return target['real_x_boxes'], analysis['real_default160_stop']


def model_binding(raws, rawrefs, refs, protocol, old, exact, data):
    require([r['model_id'] for r in rawrefs] == ['swapped-s003-td1-off', 'swapped-s004-td1-off'],
            'raw model inventory mismatch')
    networks, kernels = [], []
    for raw, reference, endpoint in zip(raws, rawrefs, (.03, .04)):
        require(raw['cell']['id'] == reference['model_id'] and raw['cell']['top_down'] is True,
                'raw cell mismatch')
        require(binary(raw['cell']['score']) == binary(endpoint), 'raw endpoint score mismatch')
        document = raw['execution']['packet']['document']
        require(all(document['source_hashes'][path] == refs[path]['sha256']
                    for path in refs if path.startswith('src/')), 'raw production source hashes mismatch')
        events = document['events']
        require(events[0]['event'] == 'r02_engine_created' and events[0]['seq'] == 0,
                'raw initial engine event mismatch')
        kernel = events[0]['payload']['config']['kernel']
        selected = [e for e in events if e['event'] == 'r02_network'
                    and e['payload']['network_id'] == 'network-8']
        require(len(selected) == 1 and selected[0]['seq'] == 8, 'raw first network inventory')
        net = selected[0]['payload']
        require(net['kind'] == 'decision' and net['top_down'] is True
                and [g['id'] for g in net['program']['groups']] == ORDER, 'raw ordered7 graph mismatch')
        digest = hashlib.sha256(json.dumps(net['program'], sort_keys=True, ensure_ascii=False,
                                           separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest()
        require(digest == net['program_digest'], 'raw program digest mismatch')
        require(binary(net['drives']['e:1']) == 4 * binary(raw['cell']['score']), 'raw score4 mismatch')
        networks.append(net)
        kernels.append(kernel)
    require(kernels[0] == kernels[1] and networks[0]['program'] == networks[1]['program']
            and networks[0]['program_digest'] == networks[1]['program_digest'], 'raw graph/kernel differs')
    drives0, drives1 = (net['drives'] for net in networks)
    require(set(drives0) == set(drives1) and all(binary(drives0[key]) == binary(drives1[key])
                                               for key in drives0 if key != 'e:1'), 'nonparameter drive differs')
    kernel = kernels[0]
    expected = {'prior_gain': 0, 'evidence_gain': 4, 'temperature': 1, 'damping': .45,
                'self_excitation': .25, 'inhibition': .2, 'relation_gain': 2, 'top_down_gain': .35,
                'max_ticks': 160, 'patience': 4}
    require(all(kernel[key] == value for key, value in expected.items())
            and float(kernel['residual_tolerance']).hex() == POLICY['tolerance_hex']
            and float(kernel['margin_threshold']).hex() == POLICY['margin_hex'], 'raw kernel mismatch')
    exact['initial_source_check'](data['src/hcr/dynamics.py'], data['src/hcr/runtime.py'])
    b, G, d = old['real_model'](networks[0], SimpleNamespace(**kernel), float.fromhex(protocol['drive_hex']))
    k, alpha = (binary(kernel['self_excitation']) + binary(kernel['inhibition'])) / 2, binary(.35)
    expected_G = [[Q(0) for _ in ORDER] for _ in ORDER]
    for i in range(7):
        expected_G[i][i] = k
    for source, target, weight in ((0, 4, 2), (4, 0, alpha), (1, 5, 2), (5, 1, alpha),
                                    (4, 5, 2), (5, 4, alpha), (5, 6, 2), (6, 5, alpha)):
        expected_G[target][source] = weight
    require(G == expected_G and b == [4, binary(float.fromhex(protocol['drive_hex'])), 4,
                                    binary(2.4), 0, -2, 0] and d == binary(.45),
            'real family/goal-y semantic mapping mismatch')
    return b, G, d


def root_dependency(critical, critical_protocol, refs, regions, protocol, exact):
    require(critical['schema'] == 'HCCONCriticalStripCertificates.v1'
            and critical['source_commit'] == critical_protocol['source_commit']
            and critical['protocol'] == refs[CRITICAL_PROTOCOL], 'critical header/protocol mismatch')
    for section, schema in (('proposal', 'HCCONCriticalStripProposal.v1'),
                            ('independent_verification', 'HCCONCriticalStripCheck.v1')):
        require(critical[section]['schema'] == schema
                and critical[section]['protocol_sha256'] == refs[CRITICAL_PROTOCOL]['sha256'],
                'critical result protocol mismatch')
    checked = critical['independent_verification']
    require(checked['accepted'] is True and checked['status'] == 'CERTIFIED'
            and checked['family']['fixed_first_network_real_family'] is True
            and checked['reduction']['all_root_rectangle'] is True
            and checked['coverage'] == {'cells': 1024, 'whole_h_faces': 4, 'new_queries': 1028,
                                       'reverified_fold_queries': 2, 'uncovered_cells': 0}
            and checked['counts']['h_above_actual_fold'] == 1, 'prior fullstrip theorem not accepted')
    require(regions == [('low', Q(-999, 1000), Q(-1, 4), 96),
                        ('middle', Q(-1, 4), Q(9, 10), 128),
                        ('high', Q(9, 10), Q(999, 1000), 32)]
            and critical_protocol['regions'] == [{'id': name, 'y': [str(lo), str(hi)], 'cells': count}
                                                for name, lo, hi, count in regions], 'high y>.9 region dependency')
    require('Middle has no roots; high strict monotonicity and boundary signs give one root.'
            in checked['proof'], 'high root location proof missing')
    for name, path in (('workspace', 'src/hcr/workspace.py'), ('dynamics', 'src/hcr/dynamics.py'),
                       ('runtime', 'src/hcr/runtime.py'), ('fold_checker', FOLD_CHECKER)):
        require(critical_protocol['dependencies'][name] == refs[path], 'critical model/helper pin mismatch')
    frozen_files = {r['path']: r for r in critical['frozen_execution']['files']}
    require(frozen_files[CRITICAL_CHECKER] == refs[CRITICAL_CHECKER]
            and frozen_files[CRITICAL_PROTOCOL] == refs[CRITICAL_PROTOCOL], 'critical frozen code mismatch')
    result = critical['scientific_result']
    require(result['claim_status'] == 'certified_full_equilibrium_census_and_unique_equilibrium_fold'
            and result['uniform_count_inside_enclosure'] == 'UNKNOWN', 'critical claim mismatch')
    critical_interval = list(map(Q, result['score_critical_interval_exact']))
    require(critical_interval == list(map(Q, checked['fold']['score_interval']))
            and critical_interval[0] < critical_interval[1], 'exact critical upper mismatch')
    score = binary(float.fromhex(protocol['score_hex']))
    endpoints = list(map(Q, checked['family']['score_endpoints']))
    require(endpoints == [binary(.03), binary(.04)] and endpoints[0] <= score <= endpoints[1]
            and score > critical_interval[1], 'target outside abovefold family')
    require(exact['tanh_enclosure'](Q(31, 20))[0] > Q(9, 10), 'goal equilibrium lower bound failed')


def verify(repo, protocol, sha, document, remaining_seconds=1800):
    require(type(remaining_seconds) in (int, float) and math.isfinite(remaining_seconds)
            and 0 < remaining_seconds <= 1800, 'remaining seconds outside combined budget')
    started = time.monotonic()

    def guard():
        require(time.monotonic() - started <= remaining_seconds, 'remaining wall budget exhausted')

    repo = Path(repo).resolve()
    protocol_check(protocol)
    fields(document, {'schema', 'protocol_sha256', 'sample_id', 'score_hex', 'drive_hex',
                      'prefix_pin', 'prefix_end_x_box', 'suffix'}, 'proposal')
    require(document['schema'] == 'HCCONRealStopProposal.v1' and document['protocol_sha256'] == sha,
            'proposal protocol binding mismatch')
    sample_binding(document, protocol)
    refs = {r['path']: r for r in protocol['sources']}
    data = {}
    for path, ref in refs.items():
        guard()
        data[path] = source_pin(repo, ref)
    require(document['prefix_pin'] == refs[NATIVE_RECORD], 'proposal prior prefix pin mismatch')
    require(isinstance(protocol['raw'], list) and len(protocol['raw']) == 2, 'raw inventory size mismatch')
    raws = [decode(source_pin(repo, {k: r[k] for k in ('path', 'sha256', 'bytes')})) for r in protocol['raw']]
    native_protocol, native = decode(data[NATIVE_PROTOCOL]), decode(data[NATIVE_RECORD])
    require(protocol['raw'] == native_protocol['raw'], 'raw pins differ from prior prefix')
    prefix, prior_stop = prior_binding(native, native_protocol, refs)
    encoded = splice(prefix, document['suffix'], document['prefix_end_x_box'], POLICY['cap'])
    guard()
    sys.dont_write_bytecode = True
    old = runpy.run_path(str(repo / NATIVE_CHECKER), run_name='real_stop_policy_dependency')
    exact = runpy.run_path(str(repo / BASIN_CHECKER), run_name='real_stop_exact_dependency')
    critical_helper = runpy.run_path(str(repo / CRITICAL_CHECKER), run_name='real_stop_census_dependency')
    require(exact['DEGREE'] == 96 and old['ORDER'] == ORDER, 'exact helper geometry mismatch')
    b, G, d = model_binding(raws, protocol['raw'], refs, protocol, old, exact, data)
    root_dependency(decode(data[CRITICAL_RECORD]), decode(data[CRITICAL_PROTOCOL]), refs,
                    critical_helper['REGIONS'], protocol, exact)
    boxes = [[(Q(0), Q(0)) for _ in ORDER]]
    for tick, encoded_box in enumerate(encoded, 1):
        guard()
        current = box(encoded_box)
        image_lo, image_hi = exact['advance'](b, G, d, [v[0] for v in boxes[-1]], [v[1] for v in boxes[-1]])
        require(old['contains_transition'](image_lo, image_hi, [v[0] for v in current], [v[1] for v in current]),
                'real transition not contained: ' + str(tick))
        boxes.append(current)
        if tick == 160:
            prefix_stop = old['real_stop'](boxes, dict(POLICY, cap=160), binary(float.fromhex(POLICY['margin_hex'])))
            require(prefix_stop == prior_stop and prefix_stop['status'] == 'budget_exhausted'
                    and prefix_stop['tick'] == 160 and prefix_stop['stable_steps'] == 0,
                    'old target160 stop clock mismatch')
    guard()
    stop = old['real_stop'](boxes, POLICY, binary(float.fromhex(POLICY['margin_hex'])))
    guard()
    result = {'schema': 'HCCONRealStopCheck.v1', 'protocol_sha256': sha,
              'accepted': stop['status'] != 'UNKNOWN', 'witness': False,
              'sample_id': SAMPLE['sample_id'], 'rechecked_prefix_transitions': 160,
              'verified_suffix_transitions': 1888, 'verified_transitions': 2048,
              'native_replays': 0, 'prior_census_rerun': False, 'stop': stop,
              'prefix_stop_rechecked': prefix_stop,
              'abovefold_any_real_equilibrium_goal_p_strict_lower': '19/20',
              'elapsed_seconds': time.monotonic() - started,
              'limits': ['One exactreal trajectory of lifted binary64 primitives and extended policy only.',
                         'Prior pinned fullstrip/high-root theorem reused; its1030 queries not rerun.',
                         'No native replay, native1848 invariance, future escape or originalcap160/fullEngine claim.',
                         'Remaining deadline is cooperative; caller controls combined wall1800 and child timeout.']}
    if stop['status'] == 'UNKNOWN':
        result.update(status='INCONCLUSIVE', reason=stop['reason'],
                      first_ambiguous_tick=stop['first_ambiguous_tick'])
    else:
        result['witness'] = low_witness(stop, POLICY['cap'])
        result['outcome'] = 'CERTIFIED_LOW_STOP' if result['witness'] else 'NOT_WITNESS'
        result['status'] = 'CERTIFIED'
        distance = distance_lower(stop['goal_p_interval'])
        result['distance_lower_exact'] = str(distance)
        result['distance_lower_outward30'] = lower_decimal(distance)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('repo', 'protocol', 'protocol-sha256', 'input', 'output'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--remaining-seconds', type=float, default=1800)
    args = parser.parse_args()
    result = {'schema': 'HCCONRealStopCheck.v1', 'protocol_sha256': args.protocol_sha256,
              'accepted': False, 'witness': False, 'status': 'INCONCLUSIVE'}
    try:
        data = Path(args.protocol).read_bytes()
        require(hashlib.sha256(data).hexdigest() == args.protocol_sha256, 'protocol hash mismatch')
        result = verify(Path(args.repo), decode(data), args.protocol_sha256,
                        decode(Path(args.input).read_bytes()), args.remaining_seconds)
    except (ValueError, TypeError, KeyError, IndexError, OverflowError, OSError, ImportError, UnicodeError) as error:
        result['reason'] = type(error).__name__ + ': ' + str(error)
    with Path(args.output).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps({'accepted': result['accepted'], 'witness': result['witness'],
                      'reason': result.get('reason')}, ensure_ascii=False))
    if not result['accepted']:
        sys.exit(1)


if __name__ == '__main__':
    main()
