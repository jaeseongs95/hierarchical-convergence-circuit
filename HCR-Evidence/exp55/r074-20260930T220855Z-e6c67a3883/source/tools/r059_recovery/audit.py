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
from tools.r057_initial.audit import CONDITIONS, _require_inventory, _verify_original_program, _verify_historical_sources
from tools.r058_horizon.audit import (
    FORBIDDEN as OLD_FORBIDDEN, R057_MANIFEST, band,
    validate_spec as validate_r058_spec, verify_record as verify_r058_record,
)

SPEC_FINGERPRINT = 'e5fbaa6d04b3b3fbef4bee0f4240b9bd6ffad59cccb85b3f695d3f44b8ba78b5'
R058_MANIFEST = '0a6d3e288786495afb8a74dc67a28d4d8940eb44242270eabeee29cde49902cf'
FORBIDDEN = OLD_FORBIDDEN | {'tools.r059_recovery.worker'}
COORDINATES = ['e:0', 'e:1', 'p:0:0', 'p:0:1', 'goal']
ARMS = [dict(id='control', coordinate=None, delta=0.0)] + [
    dict(id=f'{i}_{sign}', coordinate=c, delta=d) for i, c in enumerate(COORDINATES)
    for sign, d in [('minus', -1e-4), ('plus', 1e-4)]]
INTERVENTION = dict(one_coordinate_once=True, clipping=False, reset_stability=True,
                    initial_stable_steps=0, stop_early=False)
UNMEASURED = ('native_session_packet', 'proof', 'support', 'raw_decision', 'adoption', 'actual_energy_joules')


def validate_spec(spec):
    require(fingerprint(spec) == SPEC_FINGERPRINT, 'Exact R059 spec')
    require(spec['arms'] == ARMS and spec['coordinates'] == COORDINATES, 'Coordinate matrix')
    require(spec['conditions'] == ['goal_i05', 'goal_i09'] and spec['horizon'] == 128, 'Horizon/conditions')
    require(spec['intervention'] == INTERVENTION, 'Intervention contract')


def verify_record(packet, condition, arm, anchor, anchor_sha, config):
    raw = unseal(packet, 'hcc-r059-kernel-v1')
    expected_fields = {'schema', 'condition', 'arm', 'anchor_record_sha256', 'anchor_tick',
        'program', 'drives', 'anchor_state', 'intervention', 'horizon', 'top_down', 'completion',
        'counterfactual', 'initial_state', 'final_state', 'ticks', 'cost', *UNMEASURED}
    require(set(raw) == expected_fields, 'Exact record fields')
    require(raw['condition'] == condition and raw['arm'] == arm and raw['anchor_record_sha256'] == anchor_sha,
            'Condition/arm/anchor binding')
    require(raw['program'] == anchor['program'] and raw['drives'] == anchor['drives']
            and raw['anchor_state'] == anchor['final_state'], 'Program/drive/anchor state changed')
    require(raw['anchor_tick'] == 512 and type(raw['anchor_tick']) is int
            and raw['horizon'] == 128 and type(raw['horizon']) is int
            and raw['intervention'] == INTERVENTION and raw['top_down'] is True
            and raw['counterfactual'] is True and raw['completion'] == 'fixed_horizon_completed', 'Metadata')
    require(all(raw[k] is None for k in UNMEASURED), 'Unmeasured native outcomes')
    initial = {k: v + (arm['delta'] if k == arm['coordinate'] else 0.0)
               for k, v in anchor['final_state'].items()}
    require(all(type(v) in (float, int) and isfinite(v) and 0 <= v <= 1 for v in initial.values()),
            'Intervention range')
    require(raw['initial_state'] == initial, 'Exact one-coordinate intervention; no correction')
    require(isinstance(raw['ticks'], list) and len(raw['ticks']) == 128, 'Tick inventory')
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
    expected = dict(kernel_ticks=128, group_updates=128*len(raw['program']['groups']),
                    normalization_ops=128*len(raw['program']['groups']),
                    signal_transmissions=128*len(raw['program']['links']))
    require(raw['cost'] == expected and all(type(v) is int for v in raw['cost'].values()), 'Cost')
    return raw


def measure(raw, control):
    states = [raw['initial_state']] + [t['state'] for t in raw['ticks']]
    references = [control['initial_state']] + [t['state'] for t in control['ticks']]
    distances = [max(abs(a[k]-b[k]) for k in a) for a, b in zip(states, references, strict=True)]
    outside = [n for n, d in enumerate(distances) if d > 1e-8]
    return_tick = (outside[-1]+1 if outside else 0) if distances[-1] <= 1e-8 else None
    regime = band(raw['anchor_state']['goal'])
    mismatches = [n for n, s in enumerate(states) if band(s['goal']) != regime]
    perturbed = raw['arm']['coordinate'] is not None
    return dict(condition=raw['condition'], arm=raw['arm'], distance_by_tick=distances,
        initial_distance=distances[0], final_distance=distances[-1],
        max_distance=max(distances), max_amplification=max(distances)/distances[0] if perturbed else None,
        recovery_tail_max_distance=max(distances[113:129]),
        recovered=all(d <= 1e-8 for d in distances[113:129]) if perturbed else None,
        first_tick_with_all_remaining_distances_within_tolerance=return_tick if perturbed else None,
        initial_band=regime, band_preserved=not mismatches,
        first_nonmatching_tick=mismatches[0] if mismatches else None,
        final_state=raw['final_state'], final_residual=raw['ticks'][-1]['residual'],
        final_stable_steps=raw['ticks'][-1]['stable_steps'],
        checkpoint_distances={str(n): distances[n] for n in (1,16,32,64,128)}, cost=raw['cost'])


def verify_anchors(run, spec, config, original):
    root = run/'anchors'
    _require_inventory(root, spec['anchor_files'], 'R058 anchor inventory')
    packet = load(root/'plan.json'); plan = unseal(packet, 'hcc-r058-plan-v1')
    validate_r058_spec(plan['spec'])
    source = load(root/'source_manifest.json')
    require(source['schema'] == 'hcc-r058-source-manifest-v1'
            and plan['source_manifest_sha256'] == sha((root/'source_manifest.json').read_bytes()), 'Anchor source binding')
    require(plan['purpose'] == 'research' and plan['automatic_retry'] is False
            and plan['config'] == config and plan['spec']['parent_files'] == spec['parent_files'], 'Anchor plan binding')
    manifest, audit = load(root/'raw_manifest.json'), load(root/'analysis/audit.json')
    require(manifest['schema'] == 'hcc-r058-raw-manifest-v1' and audit['schema'] == 'hcc-r058-audit-v1'
            and audit['verified'] is True and audit['research_experiment'] is True
            and audit['plan_sha256'] == packet['sha256'], 'Anchor audit binding')
    records = {}
    for c in spec['conditions']:
        name = f'study/{c}/full.json'
        require(manifest['files'][f'{c}/full.json'] == spec['anchor_files'][name], 'Anchor raw binding')
        raw = load(root/name)
        row = verify_r058_record(raw, CONDITIONS[c], dict(id='full', remove=[]), original,
                                sha((run/'parents'/spec['program_parent']).read_bytes()), config)
        matching = [r for r in audit['rows'] if r['condition'] == c and r['mask'] == 'full']
        require(len(matching) == 1 and _close(row, matching[0]), 'Anchor audit row replay')
        records[c] = unseal(raw, 'hcc-r058-kernel-v1')
    return records


def audit(run):
    source = load(run/'source_manifest.json')
    require(source['schema'] == 'hcc-r059-source-manifest-v1', 'Source schema')
    _require_inventory(run/'source', source['files'], 'Frozen source inventory')
    require(git_tree(run/'source/src') == SRC_TREE and git_tree(run/'source/tests') == TEST_TREE, 'Protected trees')
    _verify_historical_sources(run/'source')
    for version, expected in [('R057', R057_MANIFEST), ('R058', R058_MANIFEST)]:
        path = run/'source'/(version+'_MANIFEST.json')
        require(sha(path.read_bytes().replace(b'\r\n', b'\n')) == expected, 'Historical manifest')
        for name, digest in load(path)['files'].items():
            require(sha((run/'source'/name).read_bytes().replace(b'\r\n', b'\n')) == digest, 'Historical source')
    packet = load(run/'plan.json'); plan = unseal(packet, 'hcc-r059-plan-v1'); spec = plan['spec']
    require(plan['source_manifest_sha256'] == sha((run/'source_manifest.json').read_bytes())
            and plan['automatic_retry'] is False and plan['config'] == plain(Config()), 'Plan binding')
    require(spec == load(run/'source/experiments/exp-40-local-recovery/frozen_spec.json'), 'Frozen spec binding')
    validate_spec(spec)
    require(plan['purpose'] in ('research', 'implementation_validation'), 'Purpose')
    research = plan['purpose'] == 'research'
    arms = ARMS if research else [a for a in ARMS if a['id'] in ('control','4_minus','4_plus')]
    rawroot = run/('study' if research else 'smoke'); manifest = load(run/'raw_manifest.json')
    require(manifest['schema'] == 'hcc-r059-raw-manifest-v1', 'Raw schema')
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
    return dict(schema='hcc-r059-audit-v1', verified=True, purpose=plan['purpose'],
        research_experiment=research, plan_sha256=packet['sha256'], rows=rows,
        anchor_replays=2, independent_samples=False, native_outcomes_measured=False,
        inference_scope=spec['inference_scope'])


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--run', type=Path, required=True)
    run = parser.parse_args().run; report = audit(run)
    dump(run/'analysis/audit.json', report)
    lines = ['# EXP-40 / R059 국소 교란 복원', '', f"실행 목적: {report['purpose']}", '',
             '| condition | arm | final distance | tail max | recovered | band preserved |',
             '|---|---|---:|---:|---|---|']
    for r in report['rows']:
        lines.append('| '+' | '.join(map(str, (r['condition'], r['arm']['id'], r['final_distance'],
                     r['recovery_tail_max_distance'], r['recovered'], r['band_preserved'])))+' |')
    lines += ['', '128 tick의 유한시간 좌표 교란 복원 검사다. 수학적 attractor 또는 근방 전체의 안정성을 증명하지 않는다.', '']
    publish(run/'analysis/summary.ko.md', '\n'.join(lines).encode('utf-8'))
    print('VERIFIED:', len(report['rows']), 'branches / 2 R058 anchor replays', flush=True)


if __name__ == '__main__':
    main()
