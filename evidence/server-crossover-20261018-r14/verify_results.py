"""Check preserved r14 metadata/accounting; does not rerun numerical research."""
import hashlib
import json
import math
from pathlib import Path


PUB = Path(__file__).resolve().parent
ROOT = PUB.parents[1]
RESULTS = PUB / 'results'


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True)


def verify():
    cfg = load(PUB / 'execution-contract.json')
    for pin in cfg['code_pins'] + cfg['input_pins'] + [cfg['distance_reference']]:
        path = ROOT / pin['path']
        assert path.stat().st_size == pin['bytes'] and sha(path) == pin['sha256'], pin['path']
    manifest = load(RESULTS / 'manifest.json')
    assert manifest['raw_tick_states_local'] is False
    for pin in manifest['files']:
        rel = Path(pin['path'])
        assert not rel.is_absolute() and '..' not in rel.parts
        path = RESULTS / rel
        assert path.stat().st_size == pin['bytes'] and sha(path) == pin['sha256'], pin['path']
    draw = load(RESULTS / 'draw.json')
    seed = bytes.fromhex(draw['seed_hex'])
    assert len(seed) == 32 and draw['one_draw'] is True
    expected = [v for bit in (0, 1) for v in
                (('C1', 'C0') if (seed[0] >> bit) & 1 else ('C0', 'C1'))]
    assert draw['order'] == expected
    assert draw['contract_sha256'] == sha(PUB / 'execution-contract.json')
    comparison = load(RESULTS / 'comparison.json')
    rows = comparison['rows']
    assert comparison['planned'] == len(rows) == cfg['planned_cells'] == 4
    assert [r['variant'] for r in rows] == expected
    assert comparison['verdict'] == 'DESCRIPTIVE_SERVER_COMPARISON'
    assert comparison['global_seconds'] == cfg['global_seconds'] == 13100
    assert 0 < comparison['charged_seconds'] <= comparison['global_seconds']
    assert comparison['interference_excluded'] is False
    assert comparison['windows_retrospective_correction'] is False
    verifier = load(RESULTS / 'verification.json')
    assert verifier == comparison['verification']
    assert verifier == dict(status='PASS', all_four_quality=True,
        full7_equalities=15507, fresh_unique_full_payloads=323, gate_occurrences=1292,
        canonical_success_certificates_checked=4, shared_helpers_and_accepted_anchor_trusted=True,
        nonlinear_full_prefix_replay=False)
    certificates, gate_signatures, means, phase_means, host_deltas = [], [], {}, {}, []
    input_sha = sha(PUB / 'public-input.json')
    for index, row in enumerate(rows, 1):
        assert row['cell_id'] == f'{index:02d}-{row["variant"]}'
        assert row['status'] == 'COMPLETE' and row['last_tick'] == 5168
        ev = row['evaluation']
        assert ev['candidate_correct'] is True and ev['distance']['status'] == 'INSIDE'
        assert ev['gate_state'] == 'CERTIFIED_WITHIN_EPS'
        assert ev['full_engine_accuracy'] == 'NOT_ESTABLISHED' and ev['processed_graph_complete'] is False
        for receipt in (row['policy_supervision'], row['evaluation_supervision']):
            assert receipt['status'] == 'COMPLETE' and receipt['returncode'] == 0
            assert receipt['active_processes'] == 0 and receipt['whole_wall_seconds'] > 0
        tm = load(RESULTS / row['cell_id'] / 'timings.json')
        final = load(RESULTS / row['cell_id'] / 'final.json')
        assert tm['variant'] == row['variant'] and tm['counts'] == final['counters']
        assert final['input_sha256'] == input_sha and final['last_complete']['tick'] == 5168
        assert final['stop_reason'] == 'CERTIFIED' and final['last_gate_status'] == 'CERTIFIED_WITHIN_EPS'
        counts, gates = tm['counts'], tm['gate_attempts']
        assert counts['real_map_steps'] == 5168 and counts['real_coordinate_updates'] == 36176
        assert counts['certificate_attempts'] == len(gates) == 323
        assert counts['prefilter_rejections'] == (322 if row['variant'] == 'C1' else 0)
        assert counts['region_proofs'] == (1 if row['variant'] == 'C1' else 323)
        assert counts['taylor_calls'] == (76891 if row['variant'] == 'C1' else 83653)
        for n, gate in enumerate(gates, 1):
            assert gate['attempt'] == n
            assert gate['status'] == ('CERTIFIED_WITHIN_EPS' if n == 323 else 'NOT_CERTIFIED')
            assert gate['screen'] == ('SCREENED_NOT_CERTIFIABLE' if row['variant'] == 'C1' and n < 323 else None)
        gate_signatures.append([(g['attempt'], g['state_digest'], g['status']) for g in gates])
        certificates.append(canonical(final['certificate']))
        assert tm['phases']['advance']['completed'] == 5168
        assert tm['phases']['state_persistence']['completed'] == 5169
        assert tm['phases']['certificate']['completed'] == 323
        receipt = row['policy_supervision']
        before, after = receipt['host_before'], receipt['host_after']
        # Host counters describe the VM, not an attributable delay of this child.
        host_deltas.append(dict(cell=row['cell_id'],
            global_steal_ticks=after['cpu']['cpu'][7] - before['cpu']['cpu'][7],
            flags=receipt['interference_flags']))
    assert all(c == certificates[0] for c in certificates)
    assert all(g == gate_signatures[0] for g in gate_signatures)
    assert comparison['verification_supervision']['status'] == 'COMPLETE'
    assert comparison['verification_supervision']['active_processes'] == 0
    assert comparison['verification_supervision']['returncode'] == 0
    differences = []
    for pair in (rows[:2], rows[2:]):
        by = {r['variant']: r['policy_supervision']['whole_wall_seconds'] for r in pair}
        differences.append(by['C1'] - by['C0'])
    for got, saved in zip(differences, comparison['paired_C1_minus_C0_seconds']):
        assert math.isclose(got, saved, rel_tol=0, abs_tol=1e-9)
    assert math.isclose(sum(differences) / 2, comparison['mean_seconds'], rel_tol=0, abs_tol=1e-9)
    for variant in ('C0', 'C1'):
        group = [r for r in rows if r['variant'] == variant]
        means[variant] = sum(r['policy_supervision']['whole_wall_seconds'] for r in group) / 2
        phase_means[variant] = sum(load(RESULTS / r['cell_id'] / 'timings.json')['phases']['certificate']['wall_seconds'] for r in group) / 2
    return dict(status='PASS_METADATA_AND_ACCOUNTING', cells=4,
        paired_C1_minus_C0_seconds=differences, mean_seconds=comparison['mean_seconds'],
        mean_policy_wall_seconds=means, observed_reduction_percent=100 * (1 - means['C1'] / means['C0']),
        mean_certificate_phase_wall_seconds=phase_means, host_endpoint_observations=host_deltas,
        numerical_verifier_rerun=False, raw_tick_states_local=False)


if __name__ == '__main__':
    print(json.dumps(verify(), ensure_ascii=False, sort_keys=True))
