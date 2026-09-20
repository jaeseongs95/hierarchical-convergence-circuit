"""Independent recurrence, exact intervention binding and paired recovery metrics."""
import argparse
from math import isfinite
from pathlib import Path
import sys
from hcr.codec import plain
from hcr.model import Config
from hcr.evaluation.audit import independent_step
from tools.r050_review_boundary.common import (
    SRC_TREE, TEST_TREE, dump, fingerprint, git_tree, load, publish, require, sha, unseal,
)
from tools.r053_feedback.audit import _close
from tools.r057_initial.audit import _require_inventory, _verify_original_program, _verify_historical_sources
from tools.r058_horizon.audit import (
    FORBIDDEN as OLD_FORBIDDEN, R057_MANIFEST, band,
)

from tools.r059_recovery.audit import verify_anchors

SPEC_FINGERPRINT = 'fe7f830c4322d9d23496ec5f7f254a18ceb2eaaf950a22a8fcdb3240b4a63f01'
R058_MANIFEST = '0a6d3e288786495afb8a74dc67a28d4d8940eb44242270eabeee29cde49902cf'
FORBIDDEN = OLD_FORBIDDEN | {'tools.r059_recovery.worker', 'tools.r061_linear.worker', 'tools.r060_joint.worker', 'tools.r061_linear.linear'}
COORDINATES = ['e:0', 'e:1', 'p:0:0', 'p:0:1', 'goal']
# Enumerate masks independently of the producer/spec's Cartesian-product generation.
ARMS = [dict(id='control', epsilon=0.0, signs=None, deltas={c: 0.0 for c in COORDINATES})]
for label, epsilon in [('e4', 1e-4), ('e5', 1e-5), ('e6', 1e-6)]:
    for bits in range(32):
        signs = ''.join('p' if b == '1' else 'm' for b in format(bits, '05b'))
        ARMS.append(dict(id=label+'_'+signs, epsilon=epsilon, signs=signs,
                         deltas={c: epsilon if b == 'p' else -epsilon for c, b in zip(COORDINATES, signs)}))
INTERVENTION = dict(all_coordinates_once=True, clipping=False, reset_stability=True,
                    initial_stable_steps=0, stop_early=False)
UNMEASURED = ('native_session_packet', 'proof', 'support', 'raw_decision', 'adoption', 'actual_energy_joules')


def validate_spec(spec):
    require(fingerprint(spec) == SPEC_FINGERPRINT, 'Exact R061 spec')
    require(spec['arms'] == ARMS and spec['coordinates'] == COORDINATES, 'Coordinate matrix')
    require(spec['conditions'] == ['goal_i05', 'goal_i09'] and spec['horizon'] == 1, 'Horizon/conditions')
    require(spec['intervention'] == INTERVENTION, 'Intervention contract')


def verify_record(packet, condition, arm, anchor, anchor_sha, config):
    raw = unseal(packet, 'hcc-r061-kernel-v1')
    expected_fields = {'schema', 'condition', 'arm', 'anchor_record_sha256', 'anchor_tick',
        'program', 'drives', 'anchor_state', 'intervention', 'horizon', 'top_down', 'completion',
        'analytic_jacobian', 'counterfactual', 'initial_state', 'final_state', 'ticks', 'cost', *UNMEASURED}
    require(set(raw) == expected_fields, 'Exact record fields')
    require(raw['condition'] == condition and raw['arm'] == arm and raw['anchor_record_sha256'] == anchor_sha,
            'Condition/arm/anchor binding')
    require(raw['program'] == anchor['program'] and raw['drives'] == anchor['drives']
            and raw['anchor_state'] == anchor['final_state'], 'Program/drive/anchor state changed')
    require(raw['anchor_tick'] == 512 and type(raw['anchor_tick']) is int
            and raw['horizon'] == 1 and type(raw['horizon']) is int
            and raw['intervention'] == INTERVENTION and raw['top_down'] is True
            and raw['counterfactual'] is True and raw['completion'] == 'fixed_horizon_completed', 'Metadata')
    require(all(raw[k] is None for k in UNMEASURED), 'Unmeasured native outcomes')
    initial = {k: v + arm['deltas'][k]
               for k, v in anchor['final_state'].items()}
    require(all(type(v) in (float, int) and isfinite(v) and 0 <= v <= 1 for v in initial.values()),
            'Intervention range')
    require(raw['initial_state'] == initial, 'Exact simultaneous intervention; no correction')
    require(isinstance(raw['ticks'], list) and len(raw['ticks']) == 1, 'Tick inventory')
    cfg, state, stable = Config(**config), initial, 0
    for n, row in enumerate(raw['ticks'], 1):
        require(set(row) == {'tick', 'state', 'residual', 'stable_steps'}
                and type(row['tick']) is int and row['tick'] == n, 'Tick sequence')
        nxt = independent_step(raw['program'], state, raw['drives'], cfg, True)
        residual = max(abs(nxt[k] - state[k]) for k in state)
        stable = stable + 1 if residual <= cfg.residual_tolerance else 0
        require(_close(nxt, row['state']) and _close(residual, row['residual']), 'Independent recurrence/residual')
        require(type(row['stable_steps']) is int and row['stable_steps'] == stable, 'Stability counter')
        # Replay each observed transition; do not accumulate two rounding trajectories.
        state = dict(row['state'])
    require(_close(state, raw['final_state']), 'Final state')
    expected = dict(kernel_ticks=1, group_updates=1*len(raw['program']['groups']),
                    normalization_ops=1*len(raw['program']['groups']),
                    signal_transmissions=1*len(raw['program']['links']))
    require(raw['cost'] == expected and all(type(v) is int for v in raw['cost'].values()), 'Cost')
    require(_close(raw['analytic_jacobian'], reference_jacobian(raw['program'], raw['anchor_state'], raw['drives'], config)), 'Independent analytic derivative')
    return raw


def reference_jacobian(program, state, drives, config):
    # Separate 60-digit Decimal formulation, summing each matrix coefficient directly.
    from decimal import Decimal, localcontext
    with localcontext() as ctx:
        ctx.prec = 60
        D = lambda x: Decimal(str(x))
        d, t = D(config['damping']), D(config['temperature'])
        a = D(config['self_excitation']) + D(config['inhibition'])
        rows = {}
        for group in program['groups']:
            key = group['id']
            z = 2 * (D(group['bias']) + D(drives.get(key, 0)))
            for link in program['links']:
                if link['target'] == key:
                    z += 2 * D(link['weight']) * (2 * D(state[link['source']]) - 1)
            z = (z + a * (2 * D(state[key]) - 1)) / t
            q = z.exp()
            slope = d * q / ((1 + q) ** 2 * t)
            rows[key] = [float((1-d if source == key else 0) + slope * (
                (2*a if source == key else 0) + sum(4*D(link['weight']) for link in program['links']
                    if link['target'] == key and link['source'] == source))) for source in COORDINATES]
        return [rows[k] for k in COORDINATES]


def measure(raw, control):
    delta = [raw['initial_state'][k] - control['initial_state'][k] for k in COORDINATES]
    observed = [raw['final_state'][k] - control['final_state'][k] for k in COORDINATES]
    matrix = raw['analytic_jacobian']
    prediction = [sum(a*b for a,b in zip(row, delta)) for row in matrix]
    initial = max(map(abs, delta))
    error = max(abs(a-b) for a,b in zip(observed, prediction))
    nominal = [raw['arm']['deltas'][k] for k in COORDINATES]
    nominal_prediction = [sum(a*b for a,b in zip(row, nominal)) for row in matrix]
    epsilon = raw['arm']['epsilon']
    return dict(condition=raw['condition'], arm=raw['arm'], actual_delta=delta,
        observed_difference=observed, linear_prediction=prediction,
        initial_distance=initial, one_step_distance=max(map(abs, observed)),
        actual_gain=max(map(abs, observed))/initial if initial else None,
        predicted_gain=max(map(abs, prediction))/initial if initial else None,
        nominal_directional_gain=max(map(abs, nominal_prediction))/epsilon if epsilon else None,
        linearization_error=error, error_over_epsilon_squared=error/epsilon**2 if epsilon else None,
        normalized_error=error/initial if initial else None,
        jacobian_infinity_norm=max(sum(map(abs,row)) for row in matrix),
        cost=raw['cost'])


def summarize(rows):
    result = {}
    for condition in ('goal_i05', 'goal_i09'):
        group = [r for r in rows if r['condition'] == condition and r['arm']['epsilon']]
        scales = {}
        for eps in (1e-4, 1e-5, 1e-6):
            subset = [r for r in group if r['arm']['epsilon'] == eps]
            scales[str(eps)] = dict(count=len(subset), max_gain=max(r['actual_gain'] for r in subset),
                amplified=sum(r['actual_gain'] > 1 for r in subset),
                max_linearization_error=max(r['linearization_error'] for r in subset),
                max_normalized_error=max(r['normalized_error'] for r in subset),
                max_gain_gap=max(abs(r['actual_gain']-r['nominal_directional_gain']) for r in subset))
        smallest = [r for r in group if r['arm']['epsilon'] == 1e-6]
        result[condition] = dict(scales=scales, jacobian_infinity_norm=group[0]['jacobian_infinity_norm'],
            smallest_epsilon_gain_agreement=all(abs(r['actual_gain']-r['nominal_directional_gain']) <= 1e-4 for r in smallest))
    return result


def audit(run):
    source = load(run/'source_manifest.json')
    require(source['schema'] == 'hcc-r061-source-manifest-v1', 'Source schema')
    _require_inventory(run/'source', source['files'], 'Frozen source inventory')
    require(git_tree(run/'source/src') == SRC_TREE and git_tree(run/'source/tests') == TEST_TREE, 'Protected trees')
    _verify_historical_sources(run/'source')
    for version, expected in [('R060', '18ef5aa87c92f7e1ccbbb41947b4edb6b3e8e763f074b0b2556c4b6367598131'), ('R057', R057_MANIFEST), ('R058', R058_MANIFEST), ('R059', '97787e71999adba7ef6c174e077bac281029ed8eafe9e236615cb89ccccfd45f')]:
        path = run/'source'/(version+'_MANIFEST.json')
        require(sha(path.read_bytes().replace(b'\r\n', b'\n')) == expected, 'Historical manifest')
        for name, digest in load(path)['files'].items():
            require(sha((run/'source'/name).read_bytes().replace(b'\r\n', b'\n')) == digest, 'Historical source')
    packet = load(run/'plan.json'); plan = unseal(packet, 'hcc-r061-plan-v1'); spec = plan['spec']
    require(plan['source_manifest_sha256'] == sha((run/'source_manifest.json').read_bytes())
            and plan['automatic_retry'] is False and plan['config'] == plain(Config()), 'Plan binding')
    require(spec == load(run/'source/experiments/exp-42-local-linearization/frozen_spec.json'), 'Frozen spec binding')
    validate_spec(spec)
    require(plan['purpose'] in ('research', 'implementation_validation'), 'Purpose')
    research = plan['purpose'] == 'research'
    arms = ARMS if research else [a for a in ARMS if a['id'] in ('control','e4_mmmmm','e5_ppppp','e6_mpmpm')]
    rawroot = run/('study' if research else 'smoke'); manifest = load(run/'raw_manifest.json')
    require(manifest['schema'] == 'hcc-r061-raw-manifest-v1', 'Raw schema')
    _require_inventory(rawroot, manifest['files'], 'Raw inventory')
    require(set(manifest['files']) == {f"{c}/{a['id']}.json" for c in spec['conditions'] for a in arms}, 'Exact branch inventory')
    original, _ = _verify_original_program(run, spec)
    anchors = verify_anchors(run, spec, plan['config'], original)
    rows = []
    for c in spec['conditions']:
        records = {a['id']: verify_record(load(rawroot/c/(a['id']+'.json')), c, a, anchors[c],
                   spec['anchor_files'][f'study/{c}/full.json'], plan['config']) for a in arms}
        rows.extend(measure(records[a['id']], records['control']) for a in arms)
    require(not (FORBIDDEN & set(sys.modules)), 'Producer/runtime/dynamics imported in audit')
    return dict(schema='hcc-r061-audit-v1', verified=True, purpose=plan['purpose'],
        research_experiment=research, plan_sha256=packet['sha256'], rows=rows,
        summary=summarize(rows) if research else None,
        anchor_replays=2, independent_samples=False, native_outcomes_measured=False,
        inference_scope=spec['inference_scope'])


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--run', type=Path, required=True)
    run = parser.parse_args().run; report = audit(run)
    dump(run/'analysis/audit.json', report)
    lines = ['# EXP-42 / R061 한 단계 선형화', '', f"실행 목적: {report['purpose']}", '',
             '| condition | arm | actual gain | predicted gain | max error |',
             '|---|---|---:|---:|---:|']
    for r in report['rows']:
        lines.append('| '+' | '.join(map(str, (r['condition'], r['arm']['id'], r['actual_gain'],
                     r['predicted_gain'], r['linearization_error'])))+' |')
    lines += ['', '한 단계의 국소 선형 근사 검사이며 장기 안정성이나 basin을 입증하지 않는다.', '']
    publish(run/'analysis/summary.ko.md', '\n'.join(lines).encode('utf-8'))
    print('VERIFIED:', len(report['rows']), 'branches / 2 R058 anchor replays', flush=True)


if __name__ == '__main__':
    main()
