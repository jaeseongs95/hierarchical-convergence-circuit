"""Read-only final delivery checks, distinct from the analysis producer."""
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT/'HCR-Evidence/exp46/r065-20260920T054159Z-5a8a87d609'
def load(p): return json.loads(p.read_text(encoding='utf-8'))
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    bundle = load(RUN/'bundle_manifest.json')['files']
    actual = {p.relative_to(RUN).as_posix():digest(p) for p in RUN.rglob('*') if p.is_file()}
    assert actual.pop('bundle_manifest.json') == digest(RUN/'bundle_manifest.json')
    assert actual == bundle
    with zipfile.ZipFile(RUN.with_suffix('.zip')) as z:
        names = [RUN.name+'/'+n for n in [*bundle,'bundle_manifest.json']]
        assert set(z.namelist()) == set(names) and len(z.namelist()) == len(names)
        for n in names: assert z.read(n) == (RUN/n.split('/',1)[1]).read_bytes()
    for n,h in load(RUN/'source_manifest.json')['files'].items():
        assert digest(RUN/'source'/n) == h
        assert (ROOT/n).read_bytes().replace(b'\r\n',b'\n') == (RUN/'source'/n).read_bytes().replace(b'\r\n',b'\n')
    spec = load(RUN/'spec.json'); parent = ROOT/spec['parent_run']
    for n,h in spec['parent_manifests'].items(): assert digest(parent/n) == h
    parent_bundle = load(parent/'bundle_manifest.json')['files']
    assert {p.relative_to(parent).as_posix():digest(p) for p in parent.rglob('*') if p.is_file() and p.name != 'bundle_manifest.json'} == parent_bundle
    regress = load(RUN/'validation/core_regression.json')
    assert regress['verified'] and regress['tests_run'] == 602 and regress['final_core_runs'] == 1
    assert regress['passed'] == 599 and len(regress['environment_skips']) == 3 and not regress['new_skips']
    check = load(RUN/'verification.json'); assert check['verified'] and len(check['rejected_mutations']) == 9
    rows = load(RUN/'counterfactual.json')['rows']; assert len(rows) == 12
    structural = []
    memories = [load(parent/'memory'/f'{s}.json') for s in spec['snapshots']]
    patterns = [[c['pattern'] for c in m['circuits']] for m in memories]
    assert patterns[0] == patterns[1] == patterns[2]
    for row in rows:
        if row['case'] == 'misleading-repeat' and row['use_circuits']:
            assert row['circuit_reuses'] == 1 and row['value'] is True
            assert next(w for w in row['worlds'] if w['world'] == 'closed')['adopted_correct'] is False
            structural.append(row['identity'])
    assert len(structural) == 3
    anchors = {}
    wanted = {'src/hcr/learning.py':['update_adaptive'], 'src/hcr/runtime.py':['AdaptiveEngine'],
              'src/hcr/circuits.py':['AdaptiveMemory','PatternCircuit'], 'src/hcr/activation.py':['instantiate_pool','CircuitActivationPool'],
              'src/hcr/expansion.py':['DeterministicExpansionPolicy'], 'tools/r063_formation/worker.py':['execute']}
    for name,names in wanted.items():
        raw = (parent/'source'/name).read_bytes(); tree = ast.parse(raw.decode('utf-8'))
        entries = []
        for node in ast.walk(tree):
            if isinstance(node,(ast.ClassDef,ast.FunctionDef)) and node.name in names:
                entries.append(dict(symbol=node.name,start=node.lineno,end=node.end_lineno))
        assert {n['symbol'] for n in entries} == set(names)
        anchors[name] = dict(sha256=hashlib.sha256(raw).hexdigest(),symbols=entries)
    index = subprocess.run([sys.executable,'-X','utf8','-B',str(ROOT/'scripts/run_indexed_experiment.py'),'--check-index'],cwd=ROOT,capture_output=True,text=True,encoding='utf-8')
    assert index.returncode == 0, index.stderr
    return dict(verified=True,bundle_files=len(bundle),zip_exact=True,parent_bundle_files=len(parent_bundle),
        source_anchors=anchors,source_semantics_review='experiments/exp-46-information-boundary/FLOW.ko.md',
        patterns_identical_across_snapshots=True,structural_reuse_retained_cells=structural,
        world_fact_retention=False,existing_packets=12,reference_scores=24,new_native_research_executions=0,
        new_independent_samples=0,core_tests=602,core_passed=599,existing_skips=3,rejected_mutations=9,
        index_stdout=index.stdout.strip(),verification_scope='R064 reanalysis and R065 delivery; no independent researcher audit')


if __name__ == '__main__': print(json.dumps(main(),ensure_ascii=False,indent=2))
