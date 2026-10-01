"""Separate input reconstruction and recurrence, plus independent report arithmetic."""
import argparse
from copy import deepcopy
from pathlib import Path
import sys
from tools.r050_review_boundary.common import dump, files, fingerprint, load, require
from tools.r050_review_boundary.audit import FORBIDDEN
from tools.r073_decomposition.verify import calculate, close


def expected_inputs(out,s,c):
    raw=load(out/'parent/evaluation'/f"s08-default-{c['checkpoint']}"/'inference.json')
    n=next(e['payload'] for e in raw['execution']['packet']['document']['events'] if e['event']=='r02_network' and e['payload']['kind']=='pool')
    memory=load(out/'parent/parent'/raw['cell']['memory_file'])['circuits'][0]
    balance=len(memory['evidence_episodes'])/(1+len(memory['evidence_episodes']))
    prior=0.0 if c['prior_mode']=='zero' else s['config']['kernel']['prior_gain']*memory['strength']*balance*(1-abs(s['baseline_score']))
    gain=s['gains'][c['gain_id']];drives={}
    for g in n['program']['groups']:
        key=g['id']
        if key!='goal':
            drives[key]=gain*(s['e0_score'] if key=='e:0' else c['score']) if g['level']==0 else prior
    require(fingerprint(n['program'])==s['program_sha256'] and n['top_down']==s['top_down'],'Pinned topology and top_down')
    return dict(program=n['program'],initial={g['id']:.5 for g in n['program']['groups']},top_down=n['top_down'],
        drives=drives,prior=prior,evidence_score=c['score'],prior_score=s['baseline_score'],
        strength=memory['strength'],balance=balance,mismatch=0.0,kernel=dict(s['config']['kernel'],evidence_gain=gain))


def check_cell(out,s,c,raw):
    require(raw['cell']==c and raw['evidence_kind']=='evaluator_formula_counterfactual','Cell identity')
    require(raw['native_selection'] is None and raw['native_cost'] is None,'No native behavior or cost')
    d=expected_inputs(out,s,c);require(raw['inputs']==d,'Independent input intervention')
    result=calculate(d,d['kernel']);error=close(raw['result'],result,s['numeric_tolerance'])
    anchor_error=None
    if c['gain_id']=='g4' and c['prior_mode']=='fixed':
        old=load(out/'anchor/replays'/f"{c['score_id']}-{c['checkpoint']}-evidence_only"/'pool.json')
        require(all(d[k]==old['inputs'][k] for k in ('program','initial','top_down','drives')),'R073 input correspondence')
        anchor_error=close(raw['result'],{k:v for k,v in old['result'].items() if k!='eligibility'},s['numeric_tolerance'])
    return error,anchor_error


def check_summary(out,s,report):
    raws={c['id']:load(out/'replays'/c['id']/'pool.json') for c in s['cells']};nodes=s['nodes'];tol=s['direction_tolerance']
    rows=[];diffs=[];by_delta={}
    for identity,raw in raws.items():
        c=raw['cell'];r=raw['result']
        rows.append(dict(c,terminal={n:r['state'][n] for n in nodes},prior=raw['inputs']['prior'],drives=raw['inputs']['drives'],
                         convergence=r['convergence'],evaluable=r['evaluable'],trajectory_sha256=fingerprint(r['trajectory'])))
        base=raws[f"{c['gain_id']}-{c['prior_mode']}-{c['checkpoint']}-s08"]['result']
        valid=r['evaluable'] and base['evaluable'];delta={n:r['state'][n]-base['state'][n] if valid else None for n in nodes}
        direction={n:('negative' if v < -tol else 'positive' if v>tol else 'zero') if valid else None for n,v in delta.items()}
        prediction={n:('not_evaluable' if not valid else 'falsified' if direction[n]!=s['predictions'][c['score_id']] else 'supported') for n in nodes}
        record=dict(id=identity,evaluable=valid,deltas=delta,directions=direction,predictions=prediction)
        diffs.append(record);by_delta[identity]=record
    pairs=[]
    for prior in s['prior_modes']:
        for checkpoint in s['checkpoints']:
            for sid in ['s06','s10']:
                high=by_delta[f'g4-{prior}-{checkpoint}-{sid}'];low=by_delta[f'g1-{prior}-{checkpoint}-{sid}']
                ok=all(r['evaluable'] for r in (high,low));ratio={};pred={}
                for node in nodes:
                    a,b=high['deltas'][node],low['deltas'][node]
                    ratio[node]=None if not ok or abs(a)<=tol else abs(b)/abs(a)
                    pred[node]='not_evaluable' if not ok else 'supported' if abs(b)-abs(a)>tol else 'falsified'
                pairs.append(dict(prior_mode=prior,checkpoint=checkpoint,score_id=sid,evaluable=ok,
                    gain4_deltas=high['deltas'],gain1_deltas=low['deltas'],absolute_effect_ratios=ratio,predictions=pred))
    zeros=[]
    for gain in s['gains']:
        for sid in s['scores']:
            records=[raws[f'{gain}-zero-{checkpoint}-{sid}'] for checkpoint in s['checkpoints']]
            a,b=records;ok=all(r['result']['evaluable'] for r in records)
            equal={k:a['inputs'][k] for k in ('program','initial','top_down','drives','kernel')}=={k:b['inputs'][k] for k in ('program','initial','top_down','drives','kernel')} and a['result']==b['result']
            zeros.append(dict(gain_id=gain,score_id=sid,evaluable=ok,numeric_inputs_and_results_equal=equal,
                              prediction='not_evaluable' if not ok else 'supported' if equal else 'falsified'))
    require(report['rows']==rows and report['differences']==diffs,'Independent terminal/difference/direction tests')
    require(report['gain_pairs']==pairs and report['zero_prior_checkpoint_pairs']==zeros,'Independent gain/zero prior comparisons')
    boundary=dict(reanalysis=True,formula_replay_cells=24,prior_replay_correspondences=6,new_native_research_executions=0,
        new_training_executions=0,new_feedback_applications=0,new_independent_samples=0,native_expansions=None,
        native_decision_cost=None,actual_energy_joules=None,peak_memory_bytes=None)
    require({k:v for k,v in report.items() if k not in ('rows','differences','gain_pairs','zero_prior_checkpoint_pairs')}==boundary,'Sample/cost boundary')


def main(out):
    s=load(out/'plan.json');require(s==load(out/'source/experiments/exp-55-evidence-gain-sensitivity/frozen_spec.json'),'Plan binding')
    require(files(out/'replays')==load(out/'raw_manifest.json')['files'],'Raw hash coverage')
    errors=[];anchors={}
    for c in s['cells']:
        err,anchor=check_cell(out,s,c,load(out/'replays'/c['id']/'pool.json'));errors.append(err)
        if anchor is not None:anchors[c['id']]=anchor
    require(len(anchors)==6,'Exact prior replay correspondence count')
    report=load(out/'summary.json');check_summary(out,s,report)
    c=s['cells'][0];original=load(out/'replays'/c['id']/'pool.json');rejected=[]
    for name,mutate in {
        'e0_drive':lambda x:x['inputs']['drives'].__setitem__('e:0',1.0),
        'e1_drive':lambda x:x['inputs']['drives'].__setitem__('e:1',0.0),
        'gain_config':lambda x:x['inputs']['kernel'].__setitem__('evidence_gain',1.0),
        'prior':lambda x:x['inputs'].__setitem__('prior',0.0),
        'initial':lambda x:x['inputs']['initial'].__setitem__('c:0',.9),
        'top_down':lambda x:x['inputs'].__setitem__('top_down',False),
        'tick':lambda x:x['result']['trajectory'][0]['state'].__setitem__('e:1',.5),
        'convergence':lambda x:x['result']['convergence'].__setitem__('status','budget_exhausted'),
        'native_cost':lambda x:x.__setitem__('native_cost',{'kernel_ticks':35}),
    }.items():
        bad=deepcopy(original);mutate(bad)
        try:check_cell(out,s,c,bad)
        except (ValueError,AssertionError,KeyError):rejected.append(name)
        else:raise AssertionError('Undetected replay mutation: '+name)
    summary_rejected=[]
    for name,mutate in {
        'node':lambda x:x['rows'][0]['terminal'].__setitem__('e:1',.5),
        'delta':lambda x:x['differences'][0]['deltas'].__setitem__('c:0',0.0),
        'gain_ratio':lambda x:x['gain_pairs'][0]['absolute_effect_ratios'].__setitem__('e:1',0.0),
        'zero_prior':lambda x:x['zero_prior_checkpoint_pairs'][0].__setitem__('numeric_inputs_and_results_equal',False),
        'native_samples':lambda x:x.__setitem__('new_independent_samples',24),
    }.items():
        bad=deepcopy(report);mutate(bad)
        try:check_summary(out,s,bad)
        except (ValueError,AssertionError,KeyError):summary_rejected.append(name)
        else:raise AssertionError('Undetected summary mutation: '+name)
    d=expected_inputs(out,s,c);short=calculate(d,dict(d['kernel'],max_ticks=1,patience=1))
    flat=calculate(dict(program=dict(groups=[dict(id='c:0',bias=0.0),dict(id='goal',bias=0.0)],links=[]),
                        drives={},initial={'c:0':.5,'goal':.5},top_down=True),dict(d['kernel'],self_excitation=0.0,inhibition=0.0))
    require(not short['evaluable'] and short['convergence']['status']=='budget_exhausted','Independent budget preservation')
    require(flat['evaluable'] and flat['convergence']['status']=='stable_ambiguous','Independent ambiguity preservation')
    require(not FORBIDDEN & set(sys.modules),'No native producer imports')
    dump(out/'verification.json',dict(verified=True,formula_cells=24,max_independent_formula_error=max(errors),
        prior_replay_matches=anchors,rejected_replay_mutations=rejected,rejected_summary_mutations=summary_rejected,
        budget_preserved=True,ambiguity_preserved=True,native_producer_imports=[],new_native_research_executions=0,new_independent_samples=0))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);main(p.parse_args().out)
