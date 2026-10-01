"""Summarize finite score effects at evidence and candidate nodes separately."""
import argparse
from dataclasses import replace
from pathlib import Path
import sys
from hcr.model import Config
from tools.r050_review_boundary.common import dump, files, fingerprint, load, require
from tools.r050_review_boundary.audit import FORBIDDEN
from tools.r073_decomposition.replay import simulate
from tools.r074_sensitivity.replay import inputs


def check_spec(out):
    s=load(out/'plan.json');old=load(out/'parent/plan.json')
    require(s==load(out/'source/experiments/exp-55-evidence-gain-sensitivity/frozen_spec.json'),'Frozen plan')
    require(s['config']==old['configs']['default'] and s['scores']==old['scores'] and s['checkpoints']==old['checkpoints'],'Pinned base conditions')
    require(s['gains']=={'g4':4.0,'g1':1.0} and s['prior_modes']==['fixed','zero'] and s['baseline_score']==.8 and s['e0_score']==1.0,'Bounded interventions')
    expected=[dict(id=f'{g}-{p}-{m}-{sid}',gain_id=g,prior_mode=p,checkpoint=m,score_id=sid,score=score)
              for g in ('g4','g1') for p in s['prior_modes'] for m in s['checkpoints'] for sid,score in s['scores'].items()]
    require(s['cells']==expected and len(expected)==24,'Exact grid')
    require(s['nodes']==['e:1','c:0'] and s['predictions']=={'s06':'negative','s08':'zero','s10':'positive'},'Frozen node and direction tests')
    return s


def selftest(out):
    s=check_spec(out);d=inputs(out/'parent',s,s['cells'][0]);cfg=Config(**d['kernel'])
    short=simulate(d['program'],d['initial'],d['drives'],replace(cfg,max_ticks=1,patience=1),d['top_down'])
    require(not short['evaluable'] and short['convergence']['status']=='budget_exhausted','Budget is unknown')
    flat=simulate(dict(groups=[dict(id='c:0',bias=0.0),dict(id='goal',bias=0.0)],links=[]),
                  {'c:0':.5,'goal':.5},{},replace(cfg,self_excitation=0.0,inhibition=0.0),True)
    require(flat['evaluable'] and flat['convergence']['status']=='stable_ambiguous','Ambiguity preserved')
    dump(out/'validation/selftest.json',dict(verified=True,budget_preserved=True,ambiguity_preserved=True,research_sample=False,synthetic_native_executions=0))


def summarize(out):
    s=check_spec(out);rows=[];lookup={};differences=[];gain_pairs=[];zero_pairs=[]
    for c in s['cells']:
        raw=load(out/'replays'/c['id']/'pool.json');r=raw['result']
        require(raw['cell']==c and raw['inputs']==inputs(out/'parent',s,c),'Exact cell and inputs')
        require(raw['native_selection'] is None and raw['native_cost'] is None,'Native boundary')
        row=dict(c,terminal={n:r['state'][n] for n in s['nodes']},prior=raw['inputs']['prior'],
                 drives=raw['inputs']['drives'],convergence=r['convergence'],evaluable=r['evaluable'],trajectory_sha256=fingerprint(r['trajectory']))
        rows.append(row);lookup[c['id']]=row
    tol=s['direction_tolerance'];delta_lookup={}
    for c in s['cells']:
        row=lookup[c['id']];base=lookup[f"{c['gain_id']}-{c['prior_mode']}-{c['checkpoint']}-s08"]
        valid=row['evaluable'] and base['evaluable']
        delta={n:row['terminal'][n]-base['terminal'][n] if valid else None for n in s['nodes']}
        directions={n:('positive' if v>tol else 'negative' if v < -tol else 'zero') if valid else None for n,v in delta.items()}
        predictions={n:('not_evaluable' if not valid else 'supported' if direction==s['predictions'][c['score_id']] else 'falsified') for n,direction in directions.items()}
        difference=dict(id=c['id'],evaluable=valid,deltas=delta,directions=directions,predictions=predictions)
        differences.append(difference);delta_lookup[c['id']]=difference
    for p in s['prior_modes']:
        for m in s['checkpoints']:
            for sid in ('s06','s10'):
                a,b=[delta_lookup[f'{g}-{p}-{m}-{sid}'] for g in ('g4','g1')]
                valid=a['evaluable'] and b['evaluable']
                larger={n:(abs(b['deltas'][n])>abs(a['deltas'][n])+tol if valid else None) for n in s['nodes']}
                ratios={n:(abs(b['deltas'][n])/abs(a['deltas'][n]) if valid and abs(a['deltas'][n])>tol else None) for n in s['nodes']}
                gain_pairs.append(dict(prior_mode=p,checkpoint=m,score_id=sid,evaluable=valid,
                    gain4_deltas=a['deltas'],gain1_deltas=b['deltas'],absolute_effect_ratios=ratios,
                    predictions={n:'not_evaluable' if not valid else 'supported' if bigger else 'falsified' for n,bigger in larger.items()}))
    for g in s['gains']:
        for sid in s['scores']:
            a,b=[load(out/'replays'/f'{g}-zero-{m}-{sid}'/'pool.json') for m in s['checkpoints']]
            equal=all(a['inputs'][k]==b['inputs'][k] for k in ('program','initial','top_down','drives','kernel')) and a['result']==b['result']
            valid=a['result']['evaluable'] and b['result']['evaluable']
            zero_pairs.append(dict(gain_id=g,score_id=sid,evaluable=valid,numeric_inputs_and_results_equal=equal,
                                   prediction='not_evaluable' if not valid else 'supported' if equal else 'falsified'))
    return dict(rows=rows,differences=differences,gain_pairs=gain_pairs,zero_prior_checkpoint_pairs=zero_pairs,
        reanalysis=True,formula_replay_cells=24,prior_replay_correspondences=6,new_native_research_executions=0,
        new_training_executions=0,new_feedback_applications=0,new_independent_samples=0,
        native_expansions=None,native_decision_cost=None,actual_energy_joules=None,peak_memory_bytes=None)


def main(out,phase):
    if phase=='selftest':selftest(out)
    else:
        require(files(out/'replays')==load(out/'raw_manifest.json')['files'],'Raw manifest')
        dump(out/'summary.json',summarize(out))
    require(not FORBIDDEN & set(sys.modules),'Producer boundary')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True)
    p.add_argument('--phase',choices=['selftest','final'],required=True);a=p.parse_args();main(a.out,a.phase)
