"""Byte verification plus post-execution clarification of final proof ancestry.

The frozen run/summary stays untouched. Proof.paths is a path inventory; final
support is recovered from Proof.final and its dependency closure independently.
"""
import hashlib
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT/'src'),str(ROOT)]
from tools.r050_review_boundary.common import dump, files, load, require, sha
from copy import deepcopy


def proof_support(proof):
    nodes = {n['id']:n for n in proof['nodes']}
    require(len(nodes) == len(proof['nodes']), 'Unique proof node identity')
    reached = set(); active = set(); depths = {}
    def visit(identity):
        require(identity in nodes and identity not in active, 'Existing acyclic proof parent')
        if identity in reached: return depths[identity]
        active.add(identity); node = nodes[identity]
        depth = 0 if not node['parents'] else 1+max(visit(i) for i in node['parents'])
        active.remove(identity); reached.add(identity); depths[identity] = depth
        return depth
    depth = visit(proof['final'])
    require(depth == proof['primitive_depth'], 'Final dependency depth')
    index = nodes[proof['final']]['path_index']
    require(type(index) is int and 0 <= index < len(proof['paths']), 'Final positive path index')
    path = proof['paths'][index]
    require({nodes[i]['edge_id'] for i in reached if nodes[i]['edge_id'] is not None} == set(path), 'Final ancestry edge IDs')
    require(all(nodes[i]['path_index'] in (None,index) for i in reached), 'One positive path ancestry')
    require({e for e,value in proof['assumed_edges'] if value} == set(path), 'Selected positive assumptions')
    return dict(final=proof['final'], final_path_index=index, selected_edge_id_path=path,
        final_support_node_ids=sorted(reached), recomputed_D_DAG=depth)


def main(out):
    bundle = load(out/'bundle_manifest.json')['files']
    actual = files(out); actual.pop('bundle_manifest.json')
    require(actual == bundle, 'Complete sealed bundle')
    with zipfile.ZipFile(out.with_suffix('.zip')) as z:
        require(set(z.namelist()) == {out.name+'/'+p for p in files(out)}, 'ZIP coverage')
        require(all(sha(z.read(out.name+'/'+p)) == digest for p,digest in files(out).items()), 'ZIP exact bytes')
    source = load(out/'source_manifest.json')['files']
    require(files(out/'source') == source, 'Source snapshot')
    require(all(sha((ROOT/name).read_bytes()) == digest for name,digest in source.items()), 'Current frozen source bytes')
    plan = load(out/'plan.json'); parent = ROOT/plan['parent_run']
    parent_files = load(out/'input_manifest.json')['files']
    require(files(parent) == parent_files == files(out/'parent'), 'Original and copied R077 intact')
    regression = load(out/'validation/core_regression.json')
    require(regression['verified'] and regression['tests_run'] == 602 and regression['passed'] == 599
        and len(regression['environment_skips']) == 3 and not regression['new_skips'], 'Single final regression')
    rows = []; rejections = []
    for cell in plan['cells']:
        e = load(out/'evaluation'/cell['id']/'inference.json')['execution']; candidate = e['candidate']
        if candidate is None: rows.append(dict(id=cell['id'],evaluable=False)); continue
        proof = candidate['decision']['proof']; support = proof_support(proof)
        states = dict(candidate['decision']['state'])
        ranking = sorted(range(len(proof['paths'])), key=lambda i:(-states[f'p:{i}:{len(proof["paths"][i])-1}'],i))
        require(support['final_path_index'] == ranking[0], 'Independent terminal path ranking')
        networks = [event['payload'] for event in e['packet']['document']['events']
            if event['event'] == 'r02_network' and event['payload']['kind'] == 'decision']
        network_states = []
        for n in networks:
            settled = next(event['payload'] for event in e['packet']['document']['events']
                if event['event'] == 'r02_settled' and event['payload']['network_id'] == n['network_id'])
            network_states.append(dict(network_id=n['network_id'],ticks=settled['convergence']['ticks'],
                status=settled['convergence']['status'], goal_activation=settled['state']['goal'],
                route_slot_paths=[r['path'] for r in n['metadata']['routes']]))
        rows.append(dict(id=cell['id'],evaluable=True, path_inventory=proof['paths'], **support,
            decision_networks=network_states,
            progress_mismatch_kinds=[x['payload']['mismatch']['kind'] for x in e['packet']['document']['events'] if x['event'] == 'r02_progress'],
            raw_value=candidate['decision']['value'], accepted=candidate['readout']['accepted'],
            adopted_value=candidate['readout']['value']))
    probe = load(out/'evaluation/swapped-s00-off/inference.json')['execution']['candidate']['decision']['proof']
    mutations = {
        'final_reference':lambda x:x.update(final='invented'),
        'path_index':lambda x:next(n for n in x['nodes'] if n['id'] == x['final']).update(path_index=0),
        'parent_reference':lambda x:next(n for n in x['nodes'] if n['id'] == x['final']).update(parents=['invented']),
        'public_edge_id':lambda x:next(n for n in x['nodes'] if n['edge_id'] is not None).update(edge_id='invented'),
    }
    for name,mutate in mutations.items():
        bad=deepcopy(probe);mutate(bad)
        try: proof_support(bad)
        except ValueError: rejections.append(name)
        else: raise AssertionError('Undetected final-support mutation '+name)
    audit = dict(verified=True,analysis_timing='post_execution_metric_clarification',
        frozen_prediction_results_unchanged=True, new_native_executions=0, new_independent_samples=0,
        distinction='proof.paths inventory versus final dependency closure',rows=rows,rejected_mutations=rejections)
    dump(ROOT/'HCR-Evidence/r078-validation/proof-support-audit.json',audit)
    index = load(ROOT/'experiments/INDEX.json'); entry = next(x for x in index['experiments'] if x['experiment_id'] == 'EXP-59')
    for key in ('directory','evidence_directory','design','frozen_design','implementation_validation_directory','release_manifest','standalone_python_entrypoint'):
        require((ROOT/entry[key]).exists(), 'Index target exists: '+key)
    dump(ROOT/'HCR-Evidence/r078-validation/delivery-verification.json',dict(verified=True,
        run=out.relative_to(ROOT).as_posix(), source_files=len(source), bundle_files=len(files(out)),
        zip_sha256=sha(out.with_suffix('.zip').read_bytes()), frozen_source_bytes_exact=True,
        current_frozen_source_bytes_exact=True, parent_evidence_bytes_exact=True,
        raw_bundle_zip_bytes_exact=True,core_regression=dict(runs=1,tests_run=602,passed=599,environment_skips=3,new_skips=0),
        native_training_executions=0,native_evaluation_executions=12,feedback_applications=0,
        rejected_raw_mutations=len(load(out/'verification.json')['rejected_raw_mutations']),
        rejected_summary_mutations=len(load(out/'validation/summary-verification.json')['rejected_summary_mutations']),
        rejected_proof_support_mutations=len(rejections), new_independent_samples=0,
        max_pool_replay_error=load(out/'verification.json')['max_pool_replay_error'],
        predictions=load(out/'summary.json')['predictions'], final_support_separately_verified=True,
        index_paths_verified=True, index_experiments=len(index['experiments']),default_dispatcher_promoted=False,
        automatic_retry=False,energy_joules=None,peak_memory_bytes=None))
    print('Delivery bytes and final proof support verified',flush=True)


if __name__ == '__main__': main(Path(sys.argv[1]).resolve())
