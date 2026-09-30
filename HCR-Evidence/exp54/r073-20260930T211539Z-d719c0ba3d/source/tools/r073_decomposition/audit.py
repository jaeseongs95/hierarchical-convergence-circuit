"""Verify native anchors and summarize formula interventions without runtime."""
import argparse
from copy import deepcopy
from pathlib import Path
import sys
from hcr import codec
from tools.r050_review_boundary.common import dump, files, fingerprint, load, require
from tools.r050_review_boundary.audit import FORBIDDEN
from tools.r072_range.audit import summarize as native_summary
from tools.r073_decomposition.replay import inputs, simulate


def sign(value,tolerance):
    return 'positive' if value>tolerance else 'negative' if value < -tolerance else 'zero'


def check_spec(out):
    spec=load(out/'plan.json');old=load(out/'parent/plan.json')
    require(spec==load(out/'source/experiments/exp-54-pool-drive-decomposition/frozen_spec.json'),'Frozen plan')
    require(spec['config']==old['configs']['default'] and spec['thresholds']==
            {arm:c['activation_threshold'] for arm,c in old['configs'].items()},'Pinned configs')
    require(spec['scores']==old['scores'] and spec['checkpoints']==old['checkpoints'] and spec['baseline_score']==.8,'Pinned grid')
    expected=[dict(id=f'{s}-{m}-{t}',score_id=s,score=score,checkpoint=m,treatment=t)
              for s,score in spec['scores'].items() for m in spec['checkpoints']
              for t in ('evidence_only','prior_only','joint')]
    require(spec['cells']==expected and len(expected)==18,'Exact frozen intervention grid')
    for cell in expected:
        d=inputs(out/'parent',spec,cell)
        require(set(d['initial'])=={g['id'] for g in d['program']['groups']} and
                all(v==.5 for v in d['initial'].values()),'Pinned fresh initial state')
        require(spec['prior_drive_keys']==[g['id'] for g in d['program']['groups'] if g['level']==1 and g['id']!='goal'], 'Prior targets')
    return spec


def selftest(out):
    spec=check_spec(out);native=native_summary(out/'parent')
    require(native==load(out/'parent/summary.json'),'Independent native parent summary reproduction')
    dump(out/'native-reanalysis.json',native)
    # Formula apparatus check only; a one-step budget remains unmeasurable.
    d=inputs(out/'parent',spec,spec['cells'][0]);cfg=codec.adaptive_config_from(spec['config']).kernel
    from dataclasses import replace
    short=simulate(d['program'],d['initial'],d['drives'],replace(cfg,max_ticks=1),d['top_down'])
    require(not short['evaluable'] and short['convergence']['status']=='budget_exhausted','Budget is not success')
    zero_program=dict(groups=[dict(id='c:0',bias=0.0),dict(id='goal',bias=0.0)],links=[])
    flat=simulate(zero_program,{'c:0':.5,'goal':.5},{},replace(cfg,self_excitation=0.0,inhibition=0.0),True)
    require(flat['convergence']['status']=='stable_ambiguous','Stable ambiguous preserved')
    dump(out/'validation/selftest.json',dict(verified=True,native_anchor_cells=12,
        one_tick_budget_status=short['convergence']['status'],stable_ambiguous_preserved=True,
        synthetic_native_executions=0,research_sample=False))
    require(not FORBIDDEN & set(sys.modules),'Native producer import boundary')


def summarize(out):
    spec=check_spec(out);rows=[];lookup={}
    for cell in spec['cells']:
        raw=load(out/'replays'/cell['id']/'pool.json');require(raw['cell']==cell,'Replay cell binding')
        d=raw['inputs'];r=raw['result'];require(d==inputs(out/'parent',spec,cell),'Exact input intervention')
        require(raw['native_selection'] is None and raw['native_cost'] is None,'Counterfactual boundary')
        row=dict(cell,activation=r['activation'],prior=d['prior'],drives=d['drives'],
                 convergence=r['convergence'],evaluable=r['evaluable'],eligibility=r['eligibility'],
                 trajectory_sha256=fingerprint(r['trajectory']),evidence_kind=raw['evidence_kind'])
        rows.append(row);lookup[cell['id']]=row
    comparisons=[]
    for m in spec['checkpoints']:
        base=lookup[f's08-{m}-joint']
        for s,score in spec['scores'].items():
            e,p,j=[lookup[f'{s}-{m}-{t}'] for t in ('evidence_only','prior_only','joint')]
            valid=all(x['evaluable'] for x in (base,e,p,j))
            deltas={key:(r['activation']-base['activation'] if valid else None)
                    for key,r in zip(('evidence','prior','joint'),(e,p,j))}
            interaction=j['activation']-e['activation']-p['activation']+base['activation'] if valid else None
            directions={k:(sign(v,spec['direction_tolerance']) if valid else None) for k,v in deltas.items()}
            predictions={k:('not_evaluable' if not valid else 'supported' if v==spec['predictions'][s][k] else 'falsified')
                         for k,v in directions.items()}
            comparisons.append(dict(score=score,checkpoint=m,evaluable=valid,activation_deltas=deltas,
                                    interaction=interaction,directions=directions,predictions=predictions))
    zero=[]
    for treatment in ('prior_only','joint'):
        a,b=[load(out/'replays'/f's10-{m}-{treatment}'/'pool.json') for m in spec['checkpoints']]
        valid=a['result']['evaluable'] and b['result']['evaluable']
        zero.append(dict(treatment=treatment,evaluable=valid,prior_zero=all(x['inputs']['prior']==0 for x in (a,b)),
             inputs_equal=all(a['inputs'][k]==b['inputs'][k] for k in ('program','initial','top_down','drives')),
             trajectory_equal=a['result']['trajectory']==b['result']['trajectory'],
             prediction='not_evaluable' if not valid else 'supported' if a['result']==b['result'] else 'falsified'))
    return dict(rows=rows,comparisons=comparisons,zero_prior_checkpoint_pairs=zero,
        baseline_score=.8,reanalysis=True,new_native_research_executions=0,new_training_executions=0,
        new_feedback_applications=0,new_independent_samples=0,native_anchor_cells=12,
        formula_replay_cells=18,observed_corresponding_replays=6,synthetic_native_executions=0,
        native_expansions=None,native_decision_cost=None,actual_energy_joules=None,peak_memory_bytes=None)


def main(out,phase):
    if phase=='selftest':selftest(out)
    else:
        require(files(out/'replays')==load(out/'raw_manifest.json')['files'],'Replay hash coverage')
        dump(out/'summary.json',summarize(out))
    require(not FORBIDDEN & set(sys.modules),'Native producer import boundary')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True)
    p.add_argument('--phase',choices=['selftest','final'],required=True);a=p.parse_args();main(a.out,a.phase)
