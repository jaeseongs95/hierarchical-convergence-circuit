"""Recompute summary projections and comparisons from audited raw events."""
import argparse
from copy import deepcopy
from pathlib import Path
import sys
from hcr import codec
from tools.r050_review_boundary.common import dump, files, fingerprint, load, require
from tools.r050_review_boundary.audit import FORBIDDEN, candidate_measures, counter_values
from tools.r063_formation.audit import verify_execution
from tools.r064_retention.audit import reference


def check(out, summary):
    spec=load(out/'plan.json'); expected=[c['id'] for c in spec['cells']]
    require([r['id'] for r in summary['rows']]==expected, 'Summary exact coverage')
    pool_values={}; raw_values={}; predictions={}; readouts={}; repeats={}
    for cell,row in zip(spec['cells'],summary['rows']):
        identity=cell['id'];raw=load(out/'evaluation'/identity/'inference.json');e=raw['execution']
        require(raw['cell']==cell and all(row[k]==cell[k] for k in ('id','score','arm','checkpoint')), 'Cell identity')
        memory=load(out/'parent'/cell['memory_file']);cfg=spec['configs'][cell['arm']]
        verify_execution(dict(config=cfg,limits=spec['limits']),e,cell,memory,True,'adapt','r072-'+identity)
        measures=candidate_measures(e,False);cost=counter_values(e)
        assessment=reference(e,cell['observation'],load(out/'source'/spec['world_file']))['assessment']
        require(row['measures']==measures and row['cost']==cost and row['assessment']==assessment, 'Summary readout/cost/world')
        events=e['packet']['document']['events']
        selected=[x['payload']['candidate'] for x in events if x['event']=='r02_expansion']
        require(row['selection']==selected, 'Summary selection')
        p=row['pool']
        if e['candidate'] is None:
            require(p is None,'Partial execution cannot have completed pool measurement');pool_values[identity]=None
        else:
            n=next(x['payload'] for x in events if x['event']=='r02_network' and x['payload']['kind']=='pool')
            d=next(x['payload'] for x in events if x['event']=='r02_network' and x['payload']['kind']=='decision')
            a=next(x['payload']['activations'][0] for x in events if x['event']=='r02_pool_result')
            settled=next(x['payload'] for x in events if x['event']=='r02_settled' and x['payload']['network_id']==n['network_id'])
            trajectory=[x['payload']['state'] for x in events if x['event']=='r02_tick' and x['payload']['network_id']==n['network_id']]
            dticks=[x['payload']['state'] for x in events if x['event']=='r02_tick' and x['payload']['network_id']==d['network_id']]
            stable=settled['convergence']['status'] in ('stable_decision','stable_ambiguous')
            eligible=stable and a['activation']>=cfg['activation_threshold'] and a['mismatch']<=cfg['mismatch_threshold']
            require(a['eligible'] is eligible and (selected[0]['source']=='circuit') is eligible,'Native threshold rule')
            pool=dict(pool_program_sha256=fingerprint(n['program']),pool_drives=n['drives'],
                activation=a['activation'],prior=a['prior'],mismatch=a['mismatch'],pool_ticks=len(trajectory),stable=stable,
                pool_trajectory_sha256=fingerprint(trajectory))
            require(all(p[k]==v for k,v in pool.items()), 'Summary pool projection')
            require(p['eligible'] is eligible and p['selected_source']==selected[0]['source'] and
                    p['selected_edges']==selected[0]['edges'] and p['strength']==memory['circuits'][0]['strength'] and
                    p['activation_threshold']==cfg['activation_threshold'] and p['mismatch_threshold']==cfg['mismatch_threshold'], 'Summary eligibility/config/memory')
            require(p['decision_program_sha256']==fingerprint(d['program']) and p['decision_drives']==d['drives'] and
                    p['decision_trajectory_sha256']==fingerprint(dticks) and p['decision_ticks']==len(dticks), 'Decision network projection')
            pool_values[identity]=pool
        raw_values[identity]=dict(selected=selected,measures=measures,cost=cost,eligible=None if p is None else eligible)
        readouts[identity]=('not_evaluable' if assessment is None else 'supported' if
            measures['raw_decision'] is spec['predictions'][identity]['value'] and
            assessment['correct'] is spec['predictions'][identity]['correct'] else 'falsified')
        if cell['score']==spec['repeat_score']:
            old=load(out/'parent/evaluation'/(cell['arm']+'-'+cell['checkpoint'])/'inference.json')['execution']
            old_events=old['packet']['document']['events']
            old_sel=[x['payload']['candidate'] for x in old_events if x['event']=='r02_expansion']
            def networks(events):
                ids={x['payload']['network_id']:i for i,x in enumerate(x for x in events if x['event']=='r02_network')}
                return ([{k:x['payload'][k] for k in ('kind','program','drives','top_down','metadata')}
                         for x in events if x['event']=='r02_network'],
                        [(ids[x['payload']['network_id']],x['payload']['state']) for x in events if x['event']=='r02_tick'])
            repeats[identity]=networks(events)==networks(old_events) and selected==old_sel and measures==candidate_measures(old,False) and cost==counter_values(old)
    def project(m):
        return dict(version=m['version'],circuits=[{k:c[k] for k in ('pattern','strength','evidence_episodes','version','failures','active')} for c in m['circuits']],
                    pending=[{k:p[k] for k in ('pattern','evidence_episodes')} for p in m['pending']])
    paired=all(project(load(out/'parent'/f'arms/default/memory/{i}.json'))==project(load(out/'parent'/f'arms/midpoint/memory/{i}.json')) for i in spec['checkpoints'].values())
    require(summary['config_paired_checkpoint_projection'] is paired, 'Memory pairing summary')
    pairs=[];splits=[]
    for s,score in spec['scores'].items():
        valid=[]
        for m in spec['checkpoints']:
            a,b=[f'{s}-{arm}-{m}' for arm in spec['configs']];pa,pb=pool_values[a],pool_values[b]
            same=pa is not None and pb is not None and pa==pb
            evaluable=bool(paired and same and all(p['stable'] and p['mismatch']==0 for p in (pa,pb)))
            valid.append(evaluable);va,vb=raw_values[a],raw_values[b]
            pairs.append(dict(score=score,checkpoint=m,pool_calculation_equal=bool(same),evaluable=evaluable,
                eligibility_equal=None if not evaluable else va['eligible']==vb['eligible'],
                selection_equal=None if not evaluable else va['selected']==vb['selected'],
                judgment_equal=va['measures']['raw_decision']==vb['measures']['raw_decision'],
                adoption_equal=va['measures']['adopted_value']==vb['measures']['adopted_value'],
                expansions_delta=vb['cost']['expansions']-va['cost']['expansions'],kernel_ticks_delta=vb['cost']['kernel_ticks']-va['cost']['kernel_ticks'],integer_cost_equal=va['cost']==vb['cost']))
            for identity in (a,b): predictions[identity]=('not_evaluable' if not evaluable else 'supported' if
                raw_values[identity]['selected'][0]['source']==spec['predictions'][identity]['first_source'] else 'falsified')
        for arm in spec['configs']:
            a,b=[raw_values[f'{s}-{arm}-{m}'] for m in spec['checkpoints']]
            splits.append(dict(score=score,arm=arm,evaluable=all(valid),separated=None if not all(valid) else a['selected'][0]['source']!=b['selected'][0]['source']))
    require(summary['threshold_pairs']==pairs and summary['checkpoint_splits']==splits,'Paired comparison summary')
    require(summary['selection_predictions']==predictions and summary['readout_predictions']==readouts,'Prediction projection')
    require(summary['repeat_matches_R071']==repeats,'Repeat accounting/projection')
    mid=[s for s in splits if s['arm']=='midpoint']
    robust='not_evaluable' if not all(s['evaluable'] for s in mid) else 'supported' if all(s['separated'] for s in mid) else 'falsified'
    require(summary['constant_checkpoint_split_prediction']==robust,'Range prediction')
    counts=dict(new_native_evaluation_executions=12,repeat_native_evaluations=4,new_score_native_evaluations=8,
                new_training_executions=0,new_feedback_applications=0,independent_discovery_samples=0)
    require(all(summary[k]==v for k,v in counts.items()),'Execution/sample accounting')
    require(summary['independent_samples'] is False and summary['pure_strength_intervention'] is False and
            summary['pure_threshold_across_scores'] is False and summary['actual_energy_joules'] is None and
            summary['peak_memory_bytes'] is None,'Claim/measurement boundary')
    return expected


def main(out):
    summary=load(out/'summary.json');ids=check(out,summary)
    require({p.name for p in (out/'evaluation').iterdir()}==set(ids),'Raw cell coverage')
    require(files(out/'evaluation')==load(out/'raw_manifest.json')['files'],'Raw hash coverage')
    # A poisoned report must fail against the unchanged raw records.
    mutations={
        'activation':lambda x:x['rows'][0]['pool'].__setitem__('activation',.5),
        'cost':lambda x:x['rows'][0]['cost'].__setitem__('kernel_ticks',0),
        'selection':lambda x:x['rows'][0]['selection'][0].__setitem__('source','invented'),
        'pair':lambda x:x['threshold_pairs'][0].__setitem__('evaluable',False),
        'repeat':lambda x:x['repeat_matches_R071'].__setitem__('s08-default-M0',False),
        'sample_count':lambda x:x.__setitem__('independent_discovery_samples',12),
    }
    rejected=[]
    for name,mutate in mutations.items():
        bad=deepcopy(summary);mutate(bad)
        try:check(out,bad)
        except (ValueError,AssertionError,KeyError):rejected.append(name)
        else:raise AssertionError('Undetected summary mutation: '+name)
    require(not FORBIDDEN & set(sys.modules),'Verifier imported producer')
    dump(out/'verification.json',dict(verified=True,independently_audited_cells=ids,
        summary_projection_verified=True,rejected_summary_mutations=rejected,native_producer_imports=[],
        new_research_executions_in_verifier=0))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);main(p.parse_args().out)
