"""Audit frozen-memory provenance, native packets and pool equations separately."""
import argparse
from copy import deepcopy
from pathlib import Path
import sys
from hcr import codec
from tools.r050_review_boundary.common import dump, files, fingerprint, load, require, sha
from tools.r050_review_boundary.audit import FORBIDDEN, candidate_measures, counter_values
from tools.r063_formation.audit import verify_execution, mutation_checks
from tools.r064_retention.audit import reference
from tools.r070_pool.analyze import replay
from tools.r071_boundary.audit import projection, summarize as audit_parent

SPEC = 'experiments/exp-53-selection-input-range/frozen_spec.json'
POOL_KEYS = ('pool_program_sha256', 'pool_drives', 'activation', 'prior', 'mismatch',
             'pool_ticks', 'stable', 'pool_trajectory_sha256')
REPEAT_KEYS = (*POOL_KEYS, 'eligible', 'selected_source', 'selected_edges',
               'decision_program_sha256', 'decision_drives', 'decision_trajectory_sha256', 'decision_ticks')


def assess(out, cell):
    spec = load(out/'plan.json'); raw = load(out/'evaluation'/cell['id']/'inference.json')
    require(raw['cell'] == cell, 'Exact cell binding')
    e = raw['execution']; memory = load(out/'parent'/cell['memory_file'])
    plan = dict(config=spec['configs'][cell['arm']], limits=spec['limits'])
    verify_execution(plan, e, cell, memory, True, 'adapt', 'r072-'+cell['id'])
    pool = None
    if e['candidate'] is not None:
        pool = replay(dict(cell=cell, execution=e, delivery=dict(observation=cell['observation'])),
                      memory, codec.adaptive_config_from(plan['config']))
        pool['pool_trajectory_sha256'] = fingerprint(pool.pop('pool_trajectory'))
    selected = [x['payload']['candidate'] for x in e['packet']['document']['events']
                if x['event'] == 'r02_expansion']
    return dict(id=cell['id'], score=cell['score'], arm=cell['arm'], checkpoint=cell['checkpoint'],
                pool=pool, selection=selected, measures=candidate_measures(e, False), cost=counter_values(e),
                assessment=reference(e, cell['observation'], load(out/'source'/spec['world_file']))['assessment'])


def summarize(out):
    spec = load(out/'plan.json')
    require(spec == load(out/'source'/SPEC), 'Frozen plan')
    require(sha((out/'source'/spec['world_file']).read_bytes()) == spec['world_sha256'], 'Frozen world')
    rows = [assess(out, c) for c in spec['cells']]; lookup = {r['id']:r for r in rows}
    paired_memory = all(projection(load(out/'parent'/f'arms/default/memory/{index}.json')) ==
                        projection(load(out/'parent'/f'arms/midpoint/memory/{index}.json'))
                        for index in spec['checkpoints'].values())
    pairs = []; splits = []
    for score_id, score in spec['scores'].items():
        for checkpoint in spec['checkpoints']:
            a, b = [lookup[f'{score_id}-{arm}-{checkpoint}'] for arm in spec['configs']]
            same = a['pool'] is not None and b['pool'] is not None and all(
                a['pool'][k] == b['pool'][k] for k in POOL_KEYS)
            evaluable = bool(paired_memory and same and all(
                r['pool']['stable'] and r['pool']['mismatch'] == 0 for r in (a,b)))
            pairs.append(dict(score=score, checkpoint=checkpoint, pool_calculation_equal=bool(same),
                evaluable=evaluable, eligibility_equal=None if not evaluable else a['pool']['eligible']==b['pool']['eligible'],
                selection_equal=None if not evaluable else a['selection']==b['selection'],
                judgment_equal=a['measures']['raw_decision']==b['measures']['raw_decision'],
                adoption_equal=a['measures']['adopted_value']==b['measures']['adopted_value'],
                expansions_delta=b['cost']['expansions']-a['cost']['expansions'],
                kernel_ticks_delta=b['cost']['kernel_ticks']-a['cost']['kernel_ticks'],
                integer_cost_equal=a['cost']==b['cost']))
        for arm in spec['configs']:
            a,b = [lookup[f'{score_id}-{arm}-{m}'] for m in spec['checkpoints']]
            evaluable = all(p['evaluable'] for p in pairs if p['score']==score)
            splits.append(dict(score=score, arm=arm, evaluable=evaluable,
                separated=None if not evaluable else a['pool']['selected_source']!=b['pool']['selected_source']))
    repeat = {}
    for cell in spec['cells']:
        if cell['score'] != spec['repeat_score']: continue
        arm, checkpoint = cell['arm'], cell['checkpoint']; identity = arm+'-'+checkpoint
        old = load(out/'parent/evaluation'/identity/'inference.json')['execution']
        cfg = codec.adaptive_config_from(spec['configs'][arm])
        memory = load(out/'parent'/cell['memory_file'])
        old_cell = dict(observation=cell['observation'])
        verify_execution(dict(config=spec['configs'][arm],limits=spec['limits']), old, old_cell,
                         memory, True, 'adapt', 'r071-'+identity)
        old_pool = replay(dict(cell=dict(id=identity),execution=old,delivery=old_cell),memory,cfg)
        old_pool['pool_trajectory_sha256'] = fingerprint(old_pool.pop('pool_trajectory'))
        new = lookup[cell['id']]
        repeat[cell['id']] = bool(new['pool'] is not None and all(new['pool'][k]==old_pool[k] for k in REPEAT_KEYS)
            and new['cost']==counter_values(old) and new['measures']==candidate_measures(old,False))
    eligibility = {f"{s}-{m}":p['evaluable'] for (s,m),p in zip(
        ((s,m) for s in spec['scores'] for m in spec['checkpoints']),pairs)}
    predictions = {r['id']:('not_evaluable' if not eligibility[r['id'].split('-')[0]+'-'+r['checkpoint']] else
        'supported' if r['pool']['selected_source']==spec['predictions'][r['id']]['first_source'] else 'falsified') for r in rows}
    readout = {r['id']:('not_evaluable' if r['assessment'] is None else 'supported' if
        r['measures']['raw_decision'] is spec['predictions'][r['id']]['value'] and
        r['assessment']['correct'] is spec['predictions'][r['id']]['correct'] else 'falsified') for r in rows}
    midpoint = [s for s in splits if s['arm']=='midpoint']
    robust = ('not_evaluable' if not all(s['evaluable'] for s in midpoint) else
              'supported' if all(s['separated'] for s in midpoint) else 'falsified')
    return dict(rows=rows,threshold_pairs=pairs,checkpoint_splits=splits,
        config_paired_checkpoint_projection=bool(paired_memory),repeat_matches_R071=repeat,
        selection_predictions=predictions,readout_predictions=readout,constant_checkpoint_split_prediction=robust,
        new_native_evaluation_executions=12,repeat_native_evaluations=4,new_score_native_evaluations=8,
        new_training_executions=0,new_feedback_applications=0,independent_discovery_samples=0,
        independent_samples=False,pure_strength_intervention=False,pure_threshold_across_scores=False,
        circuit_competition='not_measurable_single_candidate',actual_energy_joules=None,peak_memory_bytes=None)


def selftest(out, parent):
    spec = load(out/'plan.json'); old = load(parent/'plan.json')
    require(spec['configs']==old['configs'] and spec['checkpoints']==old['checkpoints'] and
            spec['limits']==old['limits'], 'Unchanged parent config/checkpoint/budget')
    lineage = audit_parent(parent)
    require(lineage['checkpoint_construct_engaged'] and lineage['config_paired_checkpoint_projection'] and
            lineage['config_paired_pool_calculation'], 'Parent native recipe construct')
    expected = [f'{s}-{a}-{m}' for s in spec['scores'] for a in spec['configs'] for m in spec['checkpoints']]
    require([c['id'] for c in spec['cells']]==expected and len(set(expected))==12, 'Frozen grid coverage')
    for cell in spec['cells']:
        obs = deepcopy(old['observation']); obs['edges'][1]['score']=spec['scores'][cell['score_id']]
        require(cell['observation']==obs and cell['score']==spec['scores'][cell['score_id']], 'Only e1 score changed')
    # Contract validation only, no inference/feedback, no memory re-signing.
    from hcr.circuits import AdaptiveMemory
    for arm in spec['configs']:
        other = next(a for a in spec['configs'] if a!=arm)
        cfg = codec.adaptive_config_from(spec['configs'][arm])
        for checkpoint,index in spec['checkpoints'].items():
            memory=load(out/'parent'/f'arms/{arm}/memory/{index}.json')
            require(AdaptiveMemory.from_document(memory,cfg).document()==memory, 'Exact native memory load')
            try: AdaptiveMemory.from_document(memory,codec.adaptive_config_from(spec['configs'][other]))
            except ValueError: pass
            else: raise AssertionError('Cross-config signature accepted')
    # Replay parent data mutations before generating any new research data.
    cell=next(c for c in spec['cells'] if c['id']=='s08-default-M0')
    old_e=load(out/'parent/evaluation/default-M0/inference.json')['execution']
    rejected=mutation_checks(dict(config=spec['configs']['default'],limits=spec['limits']),old_e,cell,
        load(out/'parent'/cell['memory_file']),True,'adapt','r071-default-M0')
    dump(out/'validation/selftest.json',dict(verified=True,parent_native_recipe_verified=True,
        exact_memories_loaded=4,cross_config_rejections=4,rejected_mutations=rejected,
        synthetic_native_executions=0,research_sample=False))


def main(out, phase, parent=None):
    if phase=='selftest': selftest(out,parent)
    else:
        for folder,manifest in [('source','source_manifest.json'),('parent','input_manifest.json'),('evaluation','raw_manifest.json')]:
            require(files(out/folder)==load(out/manifest)['files'], 'Exact coverage '+folder)
        summary=summarize(out);spec=load(out/'plan.json');cell=spec['cells'][0]
        e=load(out/'evaluation'/cell['id']/'inference.json')['execution']
        rejected=mutation_checks(dict(config=spec['configs'][cell['arm']],limits=spec['limits']),e,cell,
            load(out/'parent'/cell['memory_file']),True,'adapt','r072-'+cell['id'])
        dump(out/'validation/mutation-checks.json',dict(verified=True,rejected_mutations=rejected,research_sample=False))
        dump(out/'summary.json',summary)
    require(not FORBIDDEN & set(sys.modules), 'Auditor imported native producer')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True)
    p.add_argument('--phase',choices=['selftest','final'],required=True);p.add_argument('--parent',type=Path)
    a=p.parse_args();main(a.out,a.phase,a.parent)
