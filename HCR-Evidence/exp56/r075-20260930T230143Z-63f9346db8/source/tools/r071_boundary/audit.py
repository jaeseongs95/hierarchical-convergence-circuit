"""Independent reference feedback and equation replay; no native producer imports."""
import argparse
from copy import deepcopy
from pathlib import Path
import sys
from hcr import codec
from tools.r050_review_boundary.common import dump, files, load, require, fingerprint, sha
from tools.r050_review_boundary.audit import FORBIDDEN, candidate_measures, counter_values
from tools.r063_formation.audit import verify_execution, mutation_checks
from tools.r064_retention.audit import reference, check_learning
from tools.r070_pool.analyze import replay


def projection(memory):
    return dict(version=memory['version'], circuits=[{k:c[k] for k in
        ('pattern','strength','evidence_episodes','version','failures','active')} for c in memory['circuits']],
        pending=[{k:c[k] for k in ('pattern','evidence_episodes')} for c in memory['pending']])


def assess_recipe(out, arm, step):
    spec = load(out/'plan.json'); plan = dict(config=spec['configs'][arm], limits=spec['limits'])
    base = out/'arms'/arm; case = spec['recipe'][step-1]; where = base/'recipe'/str(step)
    before = load(base/'memory'/f'{step-1}.json'); e = load(where/'inference.json')
    verify_execution(plan, e, case, before, True, case['mode'], 'r071-'+arm+'-'+case['id'])
    truth = ({edge['id']: True for edge in case['observation']['edges']} if case['mode']=='train'
             else load(out/'source'/spec['world_file']))
    return reference(e, case['observation'], truth)


def summarize(out):
    spec = load(out/'plan.json'); recipe = {}; engaged = True
    require(spec == load(out/'source/experiments/exp-52-native-selection-boundary/frozen_spec.json'), 'Frozen plan')
    require(sha((out/'source'/spec['world_file']).read_bytes()) == spec['world_sha256'], 'Frozen world')
    for arm in spec['configs']:
        base = out/'arms'/arm; records = []
        cfg = codec.adaptive_config_from(spec['configs'][arm])
        empty = load(base/'memory/0.json')
        require(empty == dict(schema='hcr-memory-r02',config_signature=cfg.signature,version=0,
            circuits=[],pending=[],consumed_feedback=[],patches=[]), 'Native empty memory contract')
        for step in range(1, len(spec['recipe'])+1):
            where = base/'recipe'/str(step); expected = assess_recipe(out,arm,step)
            require(load(where/'reference.json') == expected, 'Independent feedback binding')
            before = load(base/'memory'/f'{step-1}.json'); after = load(base/'memory'/f'{step}.json')
            e = load(where/'inference.json'); learn = load(where/'learning.json')
            check_learning(e,expected,learn,before,after)
            records.append(dict(step=step,assessment=expected['assessment'],patch=learn['patch']))
        memories = {label:load(base/'memory'/f'{index}.json') for label,index in spec['checkpoints'].items()}
        for label,memory in memories.items():
            expected = spec['expected_checkpoints'][label]
            circuits = memory['circuits']
            ok = len(circuits)==1 and all(circuits[0][k]==v if k!='strength' else
                abs(circuits[0][k]-v)<spec['tolerance'] for k,v in expected.items())
            engaged = engaged and ok
        for record in records[3:]:
            patch = record['patch']; assessment = record['assessment']
            engaged = engaged and assessment is not None and assessment['correct'] is False and patch is not None and \
                len(patch['changes'])==1 and patch['changes'][0]['kind']=='weaken'
        recipe[arm] = dict(records=records,checkpoints={k:projection(v) for k,v in memories.items()})
    paired = all(recipe['default']['checkpoints'][m] == recipe['midpoint']['checkpoints'][m]
                 for m in spec['checkpoints'])
    rows = []
    for arm in spec['configs']:
        cfg = codec.adaptive_config_from(spec['configs'][arm])
        for label,index in spec['checkpoints'].items():
            identity=arm+'-'+label; raw=load(out/'evaluation'/identity/'inference.json')
            require(raw['arm']==arm and raw['checkpoint']==label, 'Evaluation cell identity')
            e=raw['execution'];memory=load(out/'arms'/arm/'memory'/f'{index}.json')
            plan=dict(config=spec['configs'][arm],limits=spec['limits'])
            verify_execution(plan,e,dict(observation=spec['observation']),memory,True,'adapt','r071-'+identity)
            data=None
            if engaged and e['candidate'] is not None:
                data=replay(dict(cell=dict(id=identity),execution=e,
                    delivery=dict(observation=spec['observation'])),memory,cfg)
                data['pool_trajectory_sha256']=fingerprint(data['pool_trajectory'])
                data.pop('pool_trajectory')
            events=e['packet']['document']['events']
            selected=[x['payload']['candidate'] for x in events if x['event']=='r02_expansion']
            rows.append(dict(id=identity,pool=data,selection=selected,measures=candidate_measures(e,False),
                cost=counter_values(e),assessment=reference(e,spec['observation'],load(out/'source'/spec['world_file']))['assessment']))
    lookup={r['id']:r for r in rows}; same_pool=True
    for label in spec['checkpoints']:
        a,b=[lookup[arm+'-'+label]['pool'] for arm in spec['configs']]
        same_pool = same_pool and a is not None and b is not None and all(a[k]==b[k] for k in
            ('pool_program_sha256','pool_drives','activation','prior','mismatch','pool_ticks','stable','pool_trajectory_sha256'))
    evaluable=engaged and paired and same_pool and all(r['pool']['stable'] and r['pool']['mismatch']==0 for r in rows)
    predictions={r['id']:('not_evaluable' if not evaluable else 'supported' if
        r['pool']['selected_source']==spec['predictions'][r['id']]['first_source'] else 'falsified') for r in rows}
    readout={r['id']:('not_evaluable' if r['assessment'] is None else 'supported' if
        r['measures']['raw_decision'] is spec['predictions'][r['id']]['value'] and
        r['assessment']['correct'] is spec['predictions'][r['id']]['correct'] else 'falsified') for r in rows}
    return dict(recipe=recipe,rows=rows,checkpoint_construct_engaged=bool(engaged),
        config_paired_checkpoint_projection=paired,config_paired_pool_calculation=same_pool,
        selection_predictions=predictions,readout_predictions=readout,threshold_choice='post_hoc_R070_derived',
        pure_strength_intervention=False,independent_discovery_samples=0,
        native_preparation_executions=10,native_evaluation_executions=4,feedback_applications=10,
        circuit_competition='not_measurable_single_candidate',actual_energy_joules=None,peak_memory_bytes=None)


def main(out, phase, arm=None, step=None):
    if phase=='reference':
        dump(out/'arms'/arm/'recipe'/str(step)/'reference.json', assess_recipe(out,arm,step))
    elif phase=='selftest':
        # A contract check on existing data, no synthetic native execution.
        from hcr.circuits import AdaptiveMemory
        spec=load(out/'plan.json'); memory=load(out/'parent/memory/M0.json')
        cfg=codec.adaptive_config_from(spec['configs']['midpoint'])
        try:AdaptiveMemory.from_document(memory,cfg)
        except ValueError:pass
        else:raise AssertionError('Mismatched historical config accepted')
        dump(out/'validation/preflight-selftest.json',dict(verified=True,config_mismatch_rejected=True,
            synthetic_native_executions=0,research_sample=False));return
    else:
        for folder,manifest in [('source','source_manifest.json'),('parent','input_manifest.json'),('arms','raw_manifest.json')]:
            require(files(out/folder)==load(out/manifest)['files'], 'Exact coverage '+folder)
        summary=summarize(out)
        spec=load(out/'plan.json');arm='default';identity=arm+'-M0'
        e=load(out/'evaluation'/identity/'inference.json')['execution']
        memory=load(out/'arms/default/memory/4.json');plan=dict(config=spec['configs'][arm],limits=spec['limits'])
        rejected=mutation_checks(plan,e,dict(observation=spec['observation']),memory,True,'adapt','r071-'+identity)
        dump(out/'validation/mutation-checks.json',dict(verified=True,rejected_mutations=rejected,research_sample=False))
        dump(out/'summary.json',summary)
    require(not FORBIDDEN & set(sys.modules), 'Evaluator imported native producer')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True)
    p.add_argument('--phase',choices=['reference','selftest','final'],required=True)
    p.add_argument('--arm');p.add_argument('--step',type=int);a=p.parse_args();main(a.out,a.phase,a.arm,a.step)
