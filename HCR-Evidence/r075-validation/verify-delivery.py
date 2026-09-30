"""Verify sealed bytes and the separately finalized catalog without resealing."""
import hashlib
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT/'src'), str(ROOT)]
from tools.r050_review_boundary.common import files
from tools.r075_factorization.pipeline import inventory, anchor_integrity
from tools.r065_information.pipeline import input_inventory
from scripts.run_indexed_experiment import read_index

OUT = ROOT/'HCR-Evidence/exp56/r075-20260930T230143Z-63f9346db8'
VAL = ROOT/'HCR-Evidence/r075-validation'


def load(path):
    return json.loads(path.read_bytes())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    spec = load(OUT/'plan.json'); source = load(OUT/'source_manifest.json')['files']
    current = inventory(ROOT)
    assert files(OUT/'source') == source and current.keys() == source.keys()
    changed = [n for n in source if current[n] != source[n]]
    assert changed == ['experiments/INDEX.json']
    old_index = load(OUT/'source/experiments/INDEX.json'); index = read_index(ROOT)
    assert index['experiments'][:-1] == old_index['experiments']
    assert {k:v for k,v in index.items() if k!='experiments'} == {k:v for k,v in old_index.items() if k!='experiments'}
    candidate = index['experiments'][-1]
    assert candidate['experiment_id']=='EXP-56' and candidate['current_python_entrypoint'] is None
    assert candidate['default_dispatcher_promoted'] is False and (ROOT/candidate['standalone_python_entrypoint']).is_file()
    for key in ('parent','anchor'):
        assert files(OUT/key) == spec[key+'_files']
        original = ROOT/spec[key+'_run']
        for name,want in spec[key+'_files'].items():
            assert digest(original/name) == digest(OUT/key/name) == want
    assert load(OUT/'input_manifest.json')['integrity'] == dict(parent=input_inventory(ROOT,spec),anchor=anchor_integrity(ROOT,spec))
    assert files(OUT/'replays') == load(OUT/'raw_manifest.json')['files']
    bundle = load(OUT/'bundle_manifest.json')['files']; actual = files(OUT); actual.pop('bundle_manifest.json')
    assert bundle == actual
    with zipfile.ZipFile(OUT.with_suffix('.zip')) as z:
        assert z.testzip() is None
        assert {n[len(OUT.name)+1:]:hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist()} == files(OUT)
    reg = load(OUT/'validation/core_regression.json')
    assert reg['verified'] and reg['passed']==599 and not reg['new_skips'] and reg['final_core_runs']==1
    verification = load(OUT/'verification.json'); summary = load(OUT/'summary.json')
    assert verification['verified'] and len(verification['prior_replay_matches'])==6
    assert len(summary['rows'])==12 and summary['mixed_scale_cells']==6
    result = dict(verified=True,run=OUT.relative_to(ROOT).as_posix(),source_files=len(source),bundle_files=len(bundle),
        zip_sha256=digest(OUT.with_suffix('.zip')),original_and_copy_input_bytes_exact=True,
        frozen_snapshot_bytes_exact=True,current_computational_source_bytes_exact=True,post_run_catalog_addition_verified=True,
        changed_current_catalog_paths=changed,raw_bundle_zip_bytes_exact=True,
        core_regression=dict(runs=1,tests_run=602,passed=599,environment_skips=3,new_skips=0),
        formula_cells=12,prior_replay_correspondences=6,mixed_scale_cells=6,
        max_formula_error=verification['max_independent_formula_error'],new_native_research_executions=0,new_independent_samples=0,
        index_paths_verified=True,index_experiments=len(index['experiments']),default_dispatcher_promoted=False,
        automatic_retry=False,failed_research_runs=0,delivery_check_failure_preserved='catalog-observation.json')
    (VAL/'delivery-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    print('Delivery verification PASS:',len(source),'source files,',len(bundle),'bundle files')


if __name__ == '__main__':
    main()
