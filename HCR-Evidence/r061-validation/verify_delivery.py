"""Read-only delivery check; result written once outside the sealed research bundle."""
from pathlib import Path
import hashlib
import json
import subprocess
import zipfile

root = Path.cwd()
runs = [p for p in (root/'HCR-Evidence/exp42').iterdir() if p.is_dir() and p.name.startswith('r061-')]
assert len(runs) == 1
run = runs[0]
def load(path): return json.loads(path.read_text(encoding='utf-8'))
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def hashes(folder): return {p.relative_to(folder).as_posix(): sha(p) for p in folder.rglob('*') if p.is_file()}

assert load(run/'result.json')['status'] == 'EXECUTED_AND_INDEPENDENTLY_VERIFIED'
bundle = load(run/'bundle_manifest.json')['files']
actual = hashes(run)
del actual['bundle_manifest.json']
assert actual == bundle
source = load(run/'source_manifest.json')['files']
assert hashes(run/'source') == source
assert all(sha(root/n) == h for n,h in source.items())
with zipfile.ZipFile(run.with_suffix('.zip')) as archive:
    assert archive.testzip() is None
    expected = {run.name+'/'+n: h for n,h in hashes(run).items()}
    assert len(archive.namelist()) == len(expected) and set(archive.namelist()) == set(expected)
    assert all(hashlib.sha256(archive.read(n)).hexdigest() == h for n,h in expected.items())

tests = load(run/'validation/selftest.json')
core = load(run/'validation/core_regression.json')
smoke = load(run/'validation/kernel-smoke/analysis/audit.json')
audit = load(run/'analysis/audit.json')
assert all(x['verified'] for x in (tests, core, smoke, audit))
assert tests['tests_run'] == 15
assert core['tests_run'] == 602 and core['passed'] == 599 and len(core['environment_skips']) == 3
assert len(smoke['rows']) == 8 and len(audit['rows']) == 194
spec = load(run/'plan.json')['spec']
assert hashes(run/'study') == load(run/'raw_manifest.json')['files']
assert set(hashes(run/'study')) == {f"{c}/{a['id']}.json" for c in spec['conditions'] for a in spec['arms']}
cost = dict.fromkeys(('kernel_ticks','group_updates','normalization_ops','signal_transmissions'), 0)
stats = {}
for condition in spec['conditions']:
    control = load(run/'study'/condition/'control.json')
    coords = spec['coordinates']
    matrix = control['analytic_jacobian']
    group = []
    for arm in spec['arms']:
        raw = load(run/'study'/condition/(arm['id']+'.json'))
        assert raw['analytic_jacobian'] == matrix
        assert raw['initial_state'] == {k: v+arm['deltas'][k] for k,v in raw['anchor_state'].items()}
        initial = [raw['initial_state'][k]-control['initial_state'][k] for k in coords]
        observed = [raw['final_state'][k]-control['final_state'][k] for k in coords]
        predicted = [sum(matrix[i][j]*initial[j] for j in range(5)) for i in range(5)]
        error = max(abs(observed[i]-predicted[i]) for i in range(5))
        row = next(row for row in audit['rows'] if row['condition'] == condition and row['arm'] == arm)
        assert row['actual_delta'] == initial and row['observed_difference'] == observed
        assert row['linear_prediction'] == predicted and row['linearization_error'] == error
        distance = max(map(abs,initial))
        assert row['actual_gain'] == (max(map(abs,observed))/distance if distance else None)
        for name in cost: cost[name] += raw['cost'][name]
        if arm['epsilon']: group.append(row)
    scales = {}
    for eps in spec['epsilons']:
        subset = [row for row in group if row['arm']['epsilon'] == eps]
        scale = dict(count=len(subset), max_gain=max(row['actual_gain'] for row in subset),
            amplified=sum(row['actual_gain']>1 for row in subset),
            max_linearization_error=max(row['linearization_error'] for row in subset),
            max_normalized_error=max(row['normalized_error'] for row in subset),
            max_gain_gap=max(abs(row['actual_gain']-row['nominal_directional_gain']) for row in subset))
        assert scale == audit['summary'][condition]['scales'][str(eps)]
        scales[str(eps)] = scale
    stats[condition] = dict(scales=scales, jacobian=matrix,
        jacobian_infinity_norm=max(sum(abs(v) for v in row) for row in matrix),
        smallest_epsilon_gain_agreement=all(abs(row['actual_gain']-row['nominal_directional_gain'])<=1e-4
            for row in group if row['arm']['epsilon']==1e-6))
old = json.loads(subprocess.check_output(['git','show','5fcdbb3:experiments/INDEX.json']))
new = load(root/'experiments/INDEX.json')
assert new['experiments'][:-1] == old['experiments']
assert {k:v for k,v in new.items() if k!='experiments'} == {k:v for k,v in old.items() if k!='experiments'}
report = dict(verified=True, run=run.relative_to(root).as_posix(), research_executions=1,
    rows=194, selftests=15, smoke_rows=8, anchor_replays=2,
    core_regression=dict(tests_run=602,passed=599,runs=1,skips=core['environment_skips']),
    source_files=len(source), bundle_hash_targets=len(bundle), zip_files=len(expected),
    source_and_bundle_unmodified=True, metrics_recomputed_from_raw=True,
    previous_index_entries_preserved=True, statistics=stats, research_cost=cost)
with (root/'HCR-Evidence/r061-validation/delivery-verification.json').open('x',encoding='utf-8',newline='\n') as stream:
    json.dump(report,stream,ensure_ascii=False,indent=2)
    stream.write('\n')
print(json.dumps(report,ensure_ascii=False,indent=2))
