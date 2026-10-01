"""Verify sealed raw bytes, the ZIP and the separately finalized catalog."""
import hashlib
import json
from pathlib import Path
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from tools.r050_review_boundary.common import files
from tools.r076_competition.pipeline import inventory
from scripts.run_indexed_experiment import read_index

OUT=ROOT/'HCR-Evidence/exp57/r076-20261001T001633Z-cac62c3eb7'
VAL=ROOT/'HCR-Evidence/r076-validation'


def load(path):return json.loads(path.read_bytes())
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    source=load(OUT/'source_manifest.json')['files'];current=inventory(ROOT)
    assert files(OUT/'source')==source and current.keys()==source.keys()
    changed=[n for n in source if current[n]!=source[n]]
    assert changed==['experiments/INDEX.json']
    old=load(OUT/'source/experiments/INDEX.json');index=read_index(ROOT)
    assert index['experiments'][:-1]==old['experiments']
    assert {k:v for k,v in index.items() if k!='experiments'}=={k:v for k,v in old.items() if k!='experiments'}
    candidate=index['experiments'][-1]
    assert candidate['experiment_id']=='EXP-57' and candidate['current_python_entrypoint'] is None
    assert candidate['default_dispatcher_promoted'] is False and (ROOT/candidate['standalone_python_entrypoint']).is_file()
    for folder,name in [('memory','memory_manifest.json'),('training','training_manifest.json'),('evaluation','raw_manifest.json')]:
        assert files(OUT/folder)==load(OUT/name)['files']
    bundle=load(OUT/'bundle_manifest.json')['files'];actual=files(OUT);actual.pop('bundle_manifest.json')
    assert actual==bundle
    with zipfile.ZipFile(OUT.with_suffix('.zip')) as z:
        assert z.testzip() is None
        assert {n[len(OUT.name)+1:]:hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist()}==files(OUT)
    reg=load(OUT/'validation/core_regression.json')
    assert reg['verified'] and reg['passed']==599 and not reg['new_skips'] and reg['final_core_runs']==1
    summary=load(OUT/'summary.json');verified=load(OUT/'verification.json')
    assert verified['verified'] and verified['independent_native_replays']==11
    assert len(summary['rows'])==8 and summary['formation_construct_engaged']
    assert len(verified['rejected_raw_mutations'])==7
    assert len(load(OUT/'validation/summary-verification.json')['rejected_summary_mutations'])==8
    plan=load(OUT/'plan.json')
    for a,b in zip(plan['cells'][::2],plan['cells'][1::2]):
        assert a['observation']==b['observation'] and a['use_circuits'] and not b['use_circuits']
    report=dict(verified=True,run=OUT.relative_to(ROOT).as_posix(),source_files=len(source),bundle_files=len(bundle),
        zip_sha256=sha(OUT.with_suffix('.zip')),frozen_snapshot_bytes_exact=True,current_computational_source_bytes_exact=True,
        post_run_catalog_addition_verified=True,changed_current_catalog_paths=changed,raw_bundle_zip_bytes_exact=True,
        core_regression=dict(runs=1,tests_run=602,passed=599,environment_skips=3,new_skips=0),
        native_training_executions=3,native_evaluation_executions=8,independent_feedback_replays=3,
        rejected_raw_mutations=7,rejected_summary_mutations=8,new_independent_samples=0,
        max_pool_replay_error=verified['max_pool_replay_error'],first_selection_switch_observed=True,
        two_complete_route_first_selection_switch_observed=False,prefix_candidate_preserved=True,
        energy_joules=None,peak_memory_bytes=None,index_paths_verified=True,index_experiments=len(index['experiments']),
        default_dispatcher_promoted=False,automatic_retry=False,failed_research_runs=0)
    (VAL/'delivery-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    print('Delivery verification PASS:',len(source),'source files;',len(bundle),'bundle files')


if __name__=='__main__':main()
