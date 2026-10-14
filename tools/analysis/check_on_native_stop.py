"""동결 첫 ON 표본의 현지 native 재생과 정확 실수 prefix를 별도로 검산한다."""
from __future__ import annotations

import argparse
from fractions import Fraction as Q
import hashlib
import importlib
import json
import math
from pathlib import Path
import platform
import re
import runpy
import sys
import time

ORDER = ['e:0', 'e:1', 'e:2', 'e:3', 'p:0:0', 'p:0:1', 'goal']
GRID = re.compile(r'-?(?:0|[1-9][0-9]*)\.[0-9]{30}\Z')
SCORE_HEX = [
    '0x1.eb851eb851eb8p-6', '0x1.1eb851eb851ecp-5',
    '0x1.2777776d1ce92p-5', '0x1.2779904c10ffep-5',
    '0x1.277991a3bb859p-5', '0x1.277991a3bb85ap-5',
    '0x1.277991a3bb85bp-5', '0x1.277992fb660b5p-5',
    '0x1.277babda5a221p-5', '0x1.2f1a9fbe76c8bp-5',
    '0x1.47ae147ae147bp-5']
SCORE_IDS = ['raw03', 'below_wide', 'below_near', 'bracket_lo',
             'mid_prev', 'mid', 'mid_next', 'bracket_hi', 'above_near',
             'above_wide', 'raw04']
POLICIES = [
    {'id': 'native160', 'tolerance_hex': '0x1.0c6f7a0b5ed8dp-20', 'patience': 4, 'cap': 160},
    {'id': 'extended', 'tolerance_hex': '0x1.0c6f7a0b5ed8dp-20', 'patience': 4, 'cap': 20000},
    {'id': 'strict', 'tolerance_hex': '0x1.5798ee2308c3ap-27', 'patience': 4, 'cap': 20000},
    {'id': 'impatient', 'tolerance_hex': '0x1.0c6f7a0b5ed8dp-20', 'patience': 1, 'cap': 20000}]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def fields(value, expected, name):
    require(isinstance(value, dict) and set(value) == set(expected), name + ' fields mismatch')


def decode(data):
    def pairs(items):
        out = {}
        for key, value in items:
            require(key not in out, 'duplicate JSON key')
            out[key] = value
        return out

    def invalid(value):
        raise ValueError('nonfinite JSON constant: ' + value)

    return json.loads(data, object_pairs_hook=pairs, parse_constant=invalid)


def source_pin(repo, reference):
    fields(reference, {'path', 'sha256', 'bytes'}, 'pin')
    require(isinstance(reference['path'], str) and isinstance(reference['sha256'], str)
            and re.fullmatch('[0-9a-f]{64}', reference['sha256'])
            and type(reference['bytes']) is int and reference['bytes'] > 0, 'invalid source pin')
    repo = Path(repo).resolve()
    path = (repo / reference['path']).resolve()
    require(path.is_relative_to(repo), 'source path outside repository')
    data = path.read_bytes()
    require(len(data) == reference['bytes'] and hashlib.sha256(data).hexdigest() == reference['sha256'],
            'source hash/byte mismatch: ' + reference['path'])
    return data


def binary(value):
    require(type(value) in (int, float) and math.isfinite(value), 'invalid binary primitive')
    return Q(*float(value).as_integer_ratio())


def hex_state(state):
    return [p.hex() for p in state]


def first_stop(trace, policy, margin):
    """동일 ignored-stop 궤적의 최초 적법 종료. 입력은 initial 포함 list[list[float]]."""
    cap, patience = policy['cap'], policy['patience']
    tol = float.fromhex(policy['tolerance_hex'])
    require(type(cap) is int and type(patience) is int and 1 <= patience <= cap
            and math.isfinite(tol) and tol > 0 and len(trace) > cap, 'invalid stop policy/trace')
    require(all(len(s) == 7 and all(type(v) is float and math.isfinite(v) and 0 <= v <= 1
                                  for v in s) for s in trace[:cap + 1]), 'invalid native trace')
    stable = 0
    for n in range(1, cap + 1):
        delta = [abs(trace[n][i] - trace[n - 1][i]) for i in range(7)]
        residual = max(delta)
        stable = stable + 1 if residual <= tol else 0
        goal_margin = abs(2 * trace[n][6] - 1)
        status = None
        # MUTATION_TARGET_PATIENCE: residual failure must reset the consecutive count.
        if stable >= patience:
            status = 'stable_decision' if goal_margin >= margin else 'stable_ambiguous'
        elif (n >= 2 and residual > tol * 10
              and max(abs(trace[n][i] - trace[n - 2][i]) for i in range(7)) < tol):
            status = 'oscillating'
        elif n == cap:
            status = 'budget_exhausted'
        if status is not None:
            return {'status': status, 'tick': n, 'state_hex': hex_state(trace[n]),
                    'residual_hex': residual.hex(), 'margin_hex': goal_margin.hex(),
                    'stable_steps': stable,
                    'residual_dominant': [i for i, value in enumerate(delta) if value == residual]}
    raise AssertionError('stop cap was not reached')


def contains_transition(image_lo, image_hi, next_lo, next_hi):
    # MUTATION_TARGET_TRANSITION: endpoint containment, not overlap, is required.
    return (bool(image_lo) and len(image_lo) == len(image_hi) == len(next_lo) == len(next_hi)
            and all(next_lo[i] <= image_lo[i] <= image_hi[i] <= next_hi[i]
                    for i in range(len(image_lo))))


def score_position(score, lo, hi):
    require(lo <= hi, 'critical interval reversed')
    return 'below' if score < lo else 'above' if score > hi else 'inside'


def decimal_grid(text):
    require(isinstance(text, str) and len(text) <= 34 and GRID.fullmatch(text), 'invalid fixed30 endpoint')
    value = Q(text)
    require(-1 <= value <= 1 and not (value == 0 and text.startswith('-')), 'state endpoint domain/negative zero')
    return value


def upper_decimal(value):
    scale = 10 ** 30
    integer = -((-value.numerator * scale) // value.denominator)
    whole, fraction = divmod(integer, scale)
    return f'{whole}.{fraction:030d}'


def environment():
    return {'python': sys.version, 'implementation': platform.python_implementation(),
            'platform': platform.platform()}


def protocol_check(p):
    require(p.get('schema') == 'HCCONNativeStopProtocol.v1' and p.get('state_order') == ORDER
            and p.get('network_id') == 'network-8' and p.get('initial_p') == '1/2', 'protocol binding')
    require(p['budget'] == {'real_prefix_ticks': 160, 'native_forced_ticks': 20000,
                           'max_scores': 11, 'wall_time_seconds': 1800,
                           'auto_retry': False, 'cap_escalation': False}, 'frozen budget mismatch')
    require(p['arithmetic'] == {'decimal_precision': 80, 'interval_grid_places': 30, 'taylor_degree': 96}
            and p['policies'] == POLICIES and p['native_checkpoints'] == [160, 1000, 10000, 20000],
            'frozen arithmetic/policies mismatch')
    require([s['id'] for s in p['scores']] == SCORE_IDS
            and [s['hex'] for s in p['scores']] == SCORE_HEX, 'frozen score inventory mismatch')
    for score in p['scores']:
        f = float.fromhex(score['hex'])
        drive = float.fromhex(score['drive_hex'])
        require(f.hex() == score['hex'] and drive.hex() == score['drive_hex']
                and 0.03 <= f <= 0.04 and binary(drive) == 4 * binary(f), 'parameter scale not exact')
    require([r['model_id'] for r in p['raw']] == ['swapped-s003-td1-off', 'swapped-s004-td1-off'],
            'raw inventory mismatch')


def bind(repo, p):
    pinned_sources = {s['path']: source_pin(repo, s) for s in p['sources']}
    require(len(pinned_sources) == len(p['sources']), 'duplicate source pin')
    required_sources = {'src/hcr/dynamics.py', 'src/hcr/model.py', 'src/hcr/workspace.py',
                        'src/hcr/runtime.py', 'tools/analysis/on_fixed_points.py',
                        'tools/analysis/check_on_basins.py',
                        'experiments/exp-62-top-down/on-critical-strip-protocol-20261013.json',
                        'experiments/exp-62-top-down/on-critical-strip-certificates-20261013.json',
                        'experiments/exp-62-top-down/on-critical-strip-decision-20261013.json'}
    require(set(pinned_sources) == required_sources, 'source inventory mismatch')
    # Native source is intentionally reused; this is a platform replay, not an IEEE emulator.
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(repo / 'src'))
    model = importlib.import_module('hcr.model')
    dynamics = importlib.import_module('hcr.dynamics')
    for module, relative in ((model, 'src/hcr/model.py'), (dynamics, 'src/hcr/dynamics.py')):
        require(Path(module.__file__).resolve() == (repo / relative).resolve(), 'imported source path mismatch')
    helper = runpy.run_path(str(repo / 'tools/analysis/check_on_basins.py'), run_name='native_stop_exact_helper')
    require(helper['DEGREE'] == 96, 'Taylor degree mismatch')
    helper['initial_source_check'](pinned_sources['src/hcr/dynamics.py'], pinned_sources['src/hcr/runtime.py'])
    raws = [decode(source_pin(repo, {k: r[k] for k in ('path', 'sha256', 'bytes')})) for r in p['raw']]
    networks, configs, controls = [], [], []
    for raw, reference in zip(raws, p['raw']):
        require(raw['cell']['id'] == reference['model_id'] and raw['cell']['top_down'] is True, 'raw cell mismatch')
        events = raw['execution']['packet']['document']['events']
        raw_hashes = raw['execution']['packet']['document']['source_hashes']
        require(all(raw_hashes.get(s['path']) == s['sha256'] for s in p['sources']
                    if s['path'].startswith('src/')), 'raw production source hashes mismatch')
        config = events[0]['payload']['config']['kernel']
        net_events = [e for e in events if e['event'] == 'r02_network'
                      and e['payload']['network_id'] == p['network_id']]
        require(len(net_events) == 1 and net_events[0]['seq'] == 8, 'first network inventory')
        net = net_events[0]['payload']
        require(net['kind'] == 'decision' and net['top_down'] is True
                and [g['id'] for g in net['program']['groups']] == ORDER, 'ordered7 graph mismatch')
        prog = model.Program(tuple(model.Group(**g) for g in net['program']['groups']),
                             tuple(model.Link(**e) for e in net['program']['links']),
                             tuple(tuple(path) for path in net['program']['paths']), net['program']['edge_count'])
        cfg = model.Config(**config)
        prog.validate(cfg)
        require(prog.digest == net['program_digest'], 'program digest mismatch')
        require(config['prior_gain'] == 0 and config['evidence_gain'] == 4.0
                and config['temperature'] == 1.0 and config['damping'] == 0.45
                and config['self_excitation'] == 0.25 and config['inhibition'] == 0.2
                and config['max_ticks'] == 160 and config['patience'] == 4
                and float(config['residual_tolerance']).hex() == POLICIES[0]['tolerance_hex'], 'raw kernel mismatch')
        require(binary(net['drives']['e:1']) == 4 * binary(raw['cell']['score']), 'raw parameter drive mismatch')
        recorded = [e['payload'] for e in events if e['event'] == 'r02_tick'
                    and e['payload']['network_id'] == p['network_id']]
        settled = [e['payload'] for e in events if e['event'] == 'r02_settled'
                   and e['payload']['network_id'] == p['network_id']]
        require(len(settled) == 1 and [t['tick'] for t in recorded] == list(range(1, len(recorded) + 1)),
                'raw tick/settled inventory mismatch')
        seen = []
        state, convergence = dynamics.settle(prog, net['drives'], cfg, model.Cost(),
            top_down=True, observe=lambda n, s, r, stable: seen.append(
                (n, [s[key] for key in ORDER], r, stable)))
        require(len(seen) == len(recorded), 'raw replay tick count mismatch')
        for (n, values, residual, stable), expected in zip(seen, recorded):
            require(set(expected['state']) == set(ORDER) and hex_state(values) == hex_state([expected['state'][key] for key in ORDER])
                    and residual.hex() == float(expected['residual']).hex()
                    and stable == expected['stable_steps'] and n == expected['tick'], 'raw replay bit mismatch')
        conv = settled[0]['convergence']
        require(hex_state([state[key] for key in ORDER]) == hex_state([settled[0]['state'][key] for key in ORDER])
                and convergence.status.value == conv['status'] and convergence.ticks == conv['ticks']
                and convergence.stable_steps == conv['stable_steps']
                and convergence.residual.hex() == float(conv['residual']).hex()
                and convergence.margin.hex() == float(conv['margin']).hex(), 'raw convergence mismatch')
        trace = [[0.5] * 7] + [v for _, v, _, _ in seen]
        control_policy = dict(POLICIES[0], cap=len(seen))
        independent = first_stop(trace, control_policy, cfg.margin_threshold)
        require(independent['status'] == conv['status'] and independent['tick'] == conv['ticks']
                and independent['residual_hex'] == float(conv['residual']).hex()
                and independent['margin_hex'] == float(conv['margin']).hex()
                and independent['stable_steps'] == conv['stable_steps'], 'independent raw stop mismatch')
        controls.append({'model_id': reference['model_id'], 'ticks': len(seen),
                         'status': convergence.status.value, 'bitwise_equal': True})
        networks.append((net, prog, cfg))
        configs.append(config)
    require(configs[0] == configs[1] and networks[0][0]['program'] == networks[1][0]['program']
            and networks[0][0]['program_digest'] == networks[1][0]['program_digest'], 'two raw graph/kernel mismatch')
    drives0, drives1 = (item[0]['drives'] for item in networks)
    require(set(drives0) == set(drives1) and all(binary(drives0[key]) == binary(drives1[key])
                for key in drives0 if key != 'e:1'), 'nonparameter drive differs')
    critical = decode(pinned_sources['experiments/exp-62-top-down/on-critical-strip-certificates-20261013.json'])
    result = critical['scientific_result']
    require(result['claim_status'] == 'certified_full_equilibrium_census_and_unique_equilibrium_fold'
            and result['uniform_count_inside_enclosure'] == 'UNKNOWN'
            and result['counts_relative_to_unknown_exact_h_star']['h_above_actual_fold'] == 1,
            'pinned critical artifact claim mismatch')
    lo, hi = map(Q, result['score_critical_interval_exact'])
    require(lo < hi and result['score_critical_interval_outward12'] == p['critical_score_outward12'],
            'critical bracket binding mismatch')
    return model, dynamics, helper, networks[0], controls, (lo, hi)


def real_model(net, config, drive):
    T = binary(config.temperature)
    k = (binary(config.self_excitation) + binary(config.inhibition)) / (2 * T)
    require(T == 1 and 0 < k < Q(1, 4), 'real diagonal/temperature mismatch')
    drives = dict(net['drives'], **{'e:1': drive})
    b = [(binary(g['bias']) + binary(drives.get(g['id'], 0.0))) / T for g in net['program']['groups']]
    G = [[Q(0) for _ in ORDER] for _ in ORDER]
    index = {key: i for i, key in enumerate(ORDER)}
    for edge in net['program']['links']:
        G[index[edge['target']]][index[edge['source']]] += binary(edge['weight']) / T
    for i in range(7):
        G[i][i] += k
    for isolated in (2, 3):
        require(all(G[isolated][j] == (k if j == isolated else 0) for j in range(7))
                and all(G[j][isolated] == 0 for j in range(7) if j != isolated),
                'isolated state has incident coupling')
    d = binary(config.damping)
    require(0 < d <= 1 and 1 - d + d * k < 1, 'isolated lift contraction failed')
    require(b[6] == 0 and G[6] == [Q(0), Q(0), Q(0), Q(0), Q(0), Q(2), k],
            'high equilibrium goal relation mismatch')
    return b, G, d


def absolute_difference(a_lo, a_hi, b_lo, b_hi):
    lo = max(Q(0), a_lo - b_hi, b_lo - a_hi)
    hi = max(abs(a_lo - b_hi), abs(a_hi - b_lo))
    return lo, hi


def real_stop(boxes, policy, margin):
    """실수 map/default predicate만 인증한다. 한 비교라도 미결정이면 UNKNOWN."""
    tol, stable = binary(float.fromhex(policy['tolerance_hex'])), 0
    for n in range(1, policy['cap'] + 1):
        previous, current = boxes[n - 1], boxes[n]
        differences = [absolute_difference(*current[i], *previous[i]) for i in range(7)]
        # x=2p-1, 따라서 p residual은 x interval 차의 절반이다.
        rlo, rhi = max(v[0] for v in differences) / 2, max(v[1] for v in differences) / 2
        if rhi <= tol:
            stable += 1
        elif rlo > tol:
            stable = 0
        else:
            return {'status': 'UNKNOWN', 'first_ambiguous_tick': n, 'reason': 'residual comparison'}
        mlo, mhi = absolute_difference(*current[6], Q(0), Q(0))
        status = None
        if stable >= policy['patience']:
            if mlo >= margin:
                status = 'stable_decision'
            elif mhi < margin:
                status = 'stable_ambiguous'
            else:
                return {'status': 'UNKNOWN', 'first_ambiguous_tick': n, 'reason': 'margin comparison'}
        elif n >= 2:
            two = [absolute_difference(*current[i], *boxes[n - 2][i]) for i in range(7)]
            olo, ohi = max(v[0] for v in two) / 2, max(v[1] for v in two) / 2
            if rlo > 10 * tol and ohi < tol:
                status = 'oscillating'
            elif rhi <= 10 * tol or olo >= tol:
                pass
            else:
                return {'status': 'UNKNOWN', 'first_ambiguous_tick': n, 'reason': 'oscillation comparison'}
        if status is not None or n == policy['cap']:
            return {'status': status or 'budget_exhausted', 'tick': n, 'stable_steps': stable,
                    'residual_p_interval': [str(rlo), str(rhi)], 'margin_interval': [str(mlo), str(mhi)],
                    'goal_p_interval': [str((current[6][0] + 1) / 2), str((current[6][1] + 1) / 2)]}
    raise AssertionError('real stop cap not reached')


def verify(repo, protocol, sha, document):
    start = time.monotonic()

    def guard():
        require(time.monotonic() - start <= protocol['budget']['wall_time_seconds'], 'frozen wall budget exhausted')

    protocol_check(protocol)
    fields(document, {'schema', 'protocol_sha256', 'environment', 'replay', 'samples'}, 'proposal')
    require(document['schema'] == 'HCCONNativeStopProposal.v1' and document['protocol_sha256'] == sha,
            'proposal protocol binding mismatch')
    require(document['environment'] == environment(), 'producer/checker environment metadata mismatch')
    model, dynamics, helper, (net, program, config), replay, critical = bind(repo, protocol)
    require(document['replay'] == replay, 'proposal replay controls mismatch')
    require(isinstance(document['samples'], list) and len(document['samples']) == 11, 'sample count mismatch')
    high_goal = helper['tanh_enclosure'](Q(31, 20))[0]
    require(high_goal > Q(9, 10), 'Taylor high equilibrium goal bound failed')
    analyses, global_error, global_defect = [], Q(0), Q(0)
    for sample, score_spec in zip(document['samples'], protocol['scores']):
        guard()
        fields(sample, {'id', 'score_hex', 'drive_hex', 'native_full_trace_sha256',
                        'native_prefix_hex', 'real_x_boxes', 'policies', 'checkpoints'}, 'sample')
        require(sample['id'] == score_spec['id'] and sample['score_hex'] == score_spec['hex']
                and sample['drive_hex'] == score_spec['drive_hex'], 'sample score binding mismatch')
        score, drive = float.fromhex(sample['score_hex']), float.fromhex(sample['drive_hex'])
        drives = dict(net['drives'], **{'e:1': drive})
        state = {key: 0.5 for key in ORDER}
        trace, cost = [[0.5] * 7], model.Cost()
        digest = hashlib.sha256(','.join(hex_state(trace[0])).encode('ascii'))
        for n in range(1, 20001):
            if n % 100 == 0:
                guard()
            state = dynamics.tick(program, state, drives, config, cost, top_down=True)
            values = [state[key] for key in ORDER]
            trace.append(values)
            digest.update(('\n' + ','.join(hex_state(values))).encode('ascii'))
        require(sample['native_full_trace_sha256'] == digest.hexdigest(), 'full native trace digest mismatch')
        require(sample['native_prefix_hex'] == [hex_state(s) for s in trace[:161]], 'native prefix bit mismatch')
        checkpoints = {str(n): hex_state(trace[n]) for n in protocol['native_checkpoints']}
        require(sample['checkpoints'] == checkpoints, 'native checkpoints mismatch')
        policies = {p['id']: first_stop(trace, p, config.margin_threshold) for p in protocol['policies']}
        require(sample['policies'] == policies, 'first legal stop mismatch')
        b, G, d = real_model(net, config, drive)
        require(isinstance(sample['real_x_boxes'], list) and len(sample['real_x_boxes']) == 160,
                'real prefix box count mismatch')
        boxes = [[(Q(0), Q(0)) for _ in ORDER]]
        max_error, max_defect, max_width = Q(0), Q(0), Q(0)
        error_tick = defect_tick = 0
        for n, encoded in enumerate(sample['real_x_boxes'], 1):
            guard()
            require(isinstance(encoded, list) and len(encoded) == 7
                    and all(isinstance(v, list) and len(v) == 2 for v in encoded), 'real box dimensions')
            box = [tuple(map(decimal_grid, pair)) for pair in encoded]
            require(all(lo <= hi for lo, hi in box), 'real box reversed')
            image_lo, image_hi = helper['advance'](b, G, d, [v[0] for v in boxes[-1]], [v[1] for v in boxes[-1]])
            require(contains_transition(image_lo, image_hi, [v[0] for v in box], [v[1] for v in box]),
                    'real transition not contained: ' + sample['id'] + ':' + str(n))
            boxes.append(box)
            xnow = [2 * binary(p) - 1 for p in trace[n]]
            error = max(max(abs(xnow[i] - box[i][0]), abs(xnow[i] - box[i][1])) for i in range(7)) / 2
            if error > max_error:
                max_error, error_tick = error, n
            max_width = max(max_width, max(hi - lo for lo, hi in box) / 2)
            xprevious = [2 * binary(p) - 1 for p in trace[n - 1]]
            defect_lo, defect_hi = helper['advance'](b, G, d, xprevious, xprevious)
            defect = max(max(abs(xnow[i] - defect_lo[i]), abs(xnow[i] - defect_hi[i])) for i in range(7)) / 2
            if defect > max_defect:
                max_defect, defect_tick = defect, n
        position = score_position(binary(score), *critical)
        distances = {}
        if position == 'above':
            for key in ('native160', 'extended'):
                stop_goal = binary(float.fromhex(policies[key]['state_hex'][6]))
                distances[key] = str(max(Q(0), Q(19, 20) - stop_goal))
        analysis = {'id': sample['id'], 'critical_bracket_position': position,
                    'native_p_real_p_prefix_distance_upper30': upper_decimal(max_error),
                    'distance_max_tick': error_tick,
                    'native_one_step_p_defect_upper30': upper_decimal(max_defect),
                    'defect_max_tick': defect_tick,
                    'real_p_box_width_upper30': upper_decimal(max_width),
                    'real_default160_stop': real_stop(boxes, POLICIES[0], binary(config.margin_threshold)),
                    'policies': policies, 'checkpoints': checkpoints,
                    'stop_distance_to_any_real_equilibrium_lower': distances}
        analyses.append(analysis)
        global_error, global_defect = max(global_error, max_error), max(global_defect, max_defect)
    guard()
    return {'schema': 'HCCONNativeStopCheck.v1', 'protocol_sha256': sha, 'accepted': True,
            'environment': environment(), 'replay': replay, 'sample_count': 11,
            'verified_real_transitions': 1760, 'native_forced_ticks_per_sample': 20000,
            'native_p_real_p_prefix_distance_upper30': upper_decimal(global_error),
            'native_one_step_p_defect_upper30': upper_decimal(global_defect),
            'above_fold_any_real_equilibrium_goal_p_strict_lower': '19/20',
            'samples': analyses,
            'limits': ['11 frozen scores only; no uniform native threshold or native equilibrium census.',
                       'Native transitions reuse pinned production tick and local libm with raw bit controls; no independent IEEE emulator or portable exp error bound.',
                       'Exact real enclosure covers 160 ticks; native continuation to 20000 is a platform observation, not a real long-horizon or asymptotic basin proof.',
                       'Prior equilibrium census is referenced by pinned completed artifact, not rerun; enclosure interior fold-side remains UNKNOWN.',
                       'First incomplete decision graph only; no latergraph/full inference or new R081 sample.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('repo', 'protocol', 'protocol-sha256', 'input', 'output'):
        parser.add_argument('--' + name, required=True)
    args = parser.parse_args()
    result = {'schema': 'HCCONNativeStopCheck.v1', 'protocol_sha256': args.protocol_sha256,
              'accepted': False, 'status': 'INCONCLUSIVE'}
    try:
        protocol_data = Path(args.protocol).read_bytes()
        require(hashlib.sha256(protocol_data).hexdigest() == args.protocol_sha256, 'protocol hash mismatch')
        result = verify(Path(args.repo).resolve(), decode(protocol_data), args.protocol_sha256,
                        decode(Path(args.input).read_bytes()))
    except (ValueError, TypeError, KeyError, IndexError, OverflowError, OSError, ImportError) as error:
        result['reason'] = type(error).__name__ + ': ' + str(error)
    with Path(args.output).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps({'accepted': result['accepted'], 'reason': result.get('reason')}, ensure_ascii=False))
    if not result['accepted']:
        sys.exit(1)


if __name__ == '__main__':
    main()
