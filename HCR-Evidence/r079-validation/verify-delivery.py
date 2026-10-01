"""Verify sealed bytes and clarify two inherited secondary summary labels.

No native execution, source/run overwrite, changed primary metric or new sample.
"""
from datetime import datetime, timezone
from pathlib import Path
import sys
import zipfile
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from tools.r050_review_boundary.common import dump, files, load, require, sha


def clarify(out):
    rows=[];summary=load(out/'summary.json')
    for row in summary['rows']:
        e=load(out/'evaluation'/row['id']/'inference.json')['execution']
        p=e['packet']['document']['engine']['pending'];c=e['candidate'];events=e['packet']['document']['events']
        active=p['active_seconds'];finish=None if c is None else c['proof_finish_seconds']
        decision_time=None if c is None else c['decision']['cost']['wall_seconds']
        require(active>=0 and (finish is None or finish>=0),'Finite nonnegative durations')
        if c is not None:require(abs((decision_time-active)-finish)<1e-12,'Disjoint native and finish durations')
        pools=[]
        for pool in row['pools']:
            nid=pool['network_id'];n=next(x['payload'] for x in events if x['event']=='r02_network' and x['payload']['network_id']==nid)
            ticks=[x['payload'] for x in events if x['event']=='r02_tick' and x['payload']['network_id']==nid]
            state=ticks[-1]['state'];previous=ticks[-2]['state'] if len(ticks)>1 else {g['id']:.5 for g in n['program']['groups']}
            terms=[]
            for link in n['program']['links']:
                if not (link['source'].startswith('c:') and link['target'].startswith('c:')):continue
                src,dst=link['source'],link['target'];w=link['weight']
                old=next(v for v in pool['candidates'][int(dst.split(':')[1])]['inhibition_inputs'] if v['source']==src)
                require(abs(old['final_signed_input']-w*state[src])<=2e-12,'Inherited uncentered diagnostic definition')
                terms.append(dict(source=src,target=dst,weight=w,terminal_source_activation=state[src],
                    inherited_uncentered_weight_times_activation=old['final_signed_input'],
                    terminal_centered_link_term=w*(2*state[src]-1),
                    last_tick_source_activation=previous[src],last_tick_centered_link_input=w*(2*previous[src]-1)))
            pools.append(dict(network_id=nid,terms=terms))
        rows.append(dict(id=row['id'],native_active_seconds=active,proof_finish_seconds=finish,
            finished_decision_wall_seconds=decision_time,
            candidate_capture_seconds=None if c is None else c['capture_seconds'],
            pending_cost_wall_seconds=p['cost']['wall_seconds'],pending_cost_is_duration=False,
            pool_link_terms=pools))
    return dict(schema='hcc-r079-secondary-metric-clarification-v1',verified=True,
        timing='post_execution_secondary_label_clarification',primary_metrics_predictions_unchanged=True,
        native_executions=0,new_independent_samples=0,
        source_rules=['src/hcr/runtime.py: finish sets cost.wall_seconds = active_seconds + finish interval',
                      'src/hcr/dynamics.py: link contribution is weight*(2*current[source]-1), prior state for each synchronous tick'],
        limitations=['Frozen row.wall_seconds is the raw pending counter (0), not a measured duration. Use native_active_seconds or finished_decision_wall_seconds here.',
                     'Inherited pool.inhibition_inputs.final_signed_input is weight*terminal_activation, not the actual kernel input. Actual last-tick and terminal centered terms are separately computed here.',
                     'candidate_capture_seconds overlaps finish/capture work; do not add it to finished_decision_wall_seconds as an independent duration.',
                     'These are measurements of one local execution, not energy, memory, general speed or isolated inhibition causal effects.'],rows=rows)


def main(out):
    bundle=load(out/'bundle_manifest.json')['files'];actual=files(out);actual.pop('bundle_manifest.json')
    require(actual==bundle,'Exact sealed bundle coverage')
    hashes=files(out)
    with zipfile.ZipFile(out.with_suffix('.zip')) as z:
        require(set(z.namelist())=={out.name+'/'+p for p in hashes},'ZIP coverage')
        require(all(sha(z.read(out.name+'/'+p))==digest for p,digest in hashes.items()),'ZIP exact bytes')
    source=load(out/'source_manifest.json')['files'];require(files(out/'source')==source,'Frozen source snapshot')
    require(all(sha((ROOT/name).read_bytes())==digest for name,digest in source.items()
        if name!='experiments/INDEX.json'),'Current executable/design source bytes')
    old_catalog=load(out/'source/experiments/INDEX.json');new_catalog=load(ROOT/'experiments/INDEX.json')
    prior_view=dict(new_catalog,experiments=[x for x in new_catalog['experiments'] if x['experiment_id']!='EXP-60'])
    require(prior_view==old_catalog and len(new_catalog['experiments'])==len(old_catalog['experiments'])+1,
        'Catalog changed only by one post-run EXP60 registration')
    plan=load(out/'plan.json');parent=ROOT/plan['parent_run'];inputs=load(out/'input_manifest.json')['files']
    require(files(parent)==inputs==files(out/'parent'),'R077 original/copied evidence intact')
    repeats=load(out/'repeat_manifest.json')['files'];repeat=ROOT/plan['reproduction_run']
    require(files(out/'repeat')==repeats and all(sha((repeat/n).read_bytes())==d for n,d in repeats.items()),'R078 repeat input intact')
    reg=load(out/'validation/core_regression.json')
    require(reg['verified'] and reg['final_core_runs']==1 and reg['tests_run']==602 and reg['passed']==599
        and len(reg['environment_skips'])==3 and not reg['new_skips'],'Final regression1')
    timing=load(out/'timing.json');freeze=load(ROOT/'HCR-Evidence/r079-validation/design-freeze.json')
    amendment=load(ROOT/'experiments/exp-60-score-readout/pre-execution-amendment.json')
    require(datetime.fromisoformat(freeze['frozen_at'])<datetime.fromisoformat(amendment['recorded_at'])<
        datetime.fromisoformat(timing['native_started_at']),'Design/amendment before native')
    require(datetime.fromisoformat(timing['freeze_completed_at'])<datetime.fromisoformat(timing['selftest_completed_at'])<=
        datetime.fromisoformat(timing['native_started_at'])<datetime.fromisoformat(timing['native_finished_at']),'Pipeline temporal order')
    clarification=clarify(out);dump(ROOT/'HCR-Evidence/r079-validation/secondary-metric-clarification.json',clarification)
    index=load(ROOT/'experiments/INDEX.json');entry=next(x for x in index['experiments'] if x['experiment_id']=='EXP-60')
    for key in ('directory','evidence_directory','design','frozen_design','implementation_validation_directory','release_manifest','standalone_python_entrypoint'):
        require((ROOT/entry[key]).exists(),'Catalog path '+key)
    dump(ROOT/'HCR-Evidence/r079-validation/delivery-verification.json',dict(verified=True,recorded_at=datetime.now(timezone.utc).isoformat(),
        run=out.relative_to(ROOT).as_posix(),bundle_files=len(hashes),source_files=len(source),
        zip_sha256=sha(out.with_suffix('.zip').read_bytes()),raw_bundle_zip_exact=True,current_executable_design_source_exact=True,
        catalog_only_post_run_entry_added=True,frozen_catalog_sha256=source['experiments/INDEX.json'],
        current_catalog_sha256=sha((ROOT/'experiments/INDEX.json').read_bytes()),
        original_parent_and_repeat_inputs_exact=True,design_and_amendment_before_native=True,
        core_regression=dict(runs=1,tests=602,passed=599,existing_environment_skips=3,new_skips=0),
        independent_raw_replays=20,reproduction_journals=8,
        raw_mutations_rejected=len(load(out/'verification.json')['rejected_raw_mutations']),
        summary_mutations_rejected=len(load(out/'validation/summary-verification.json')['rejected_summary_mutations']),
        secondary_label_clarification=True,primary_metrics_predictions_unchanged=True,index_paths_verified=True))
    print('Delivery and secondary metric clarification verified',flush=True)


if __name__=='__main__':main(Path(sys.argv[1]).resolve())
