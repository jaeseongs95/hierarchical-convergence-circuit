"""Reconstruct interventions, replay separately, and verify report arithmetic."""
import argparse
from copy import deepcopy
from pathlib import Path
import sys
from tools.r050_review_boundary.common import dump, files, fingerprint, load, require
from tools.r050_review_boundary.audit import FORBIDDEN
from tools.r073_decomposition.verify import calculate, close


def expected_inputs(out,s,c):
    raw=load(out/'parent/evaluation/s08-default-M0/inference.json')
    n=next(e['payload'] for e in raw['execution']['packet']['document']['events'] if e['event']=='r02_network' and e['payload']['kind']=='pool')
    memory=load(out/'parent/parent'/raw['cell']['memory_file'])['circuits'][0]
    drives={g['id']:0.0 for g in n['program']['groups'] if g['id']!='goal'}
    drives.update({'e:0':c['e0_scale']*s['e0_score'], 'e:1':c['e1_scale']*c['score']})
    require(fingerprint(n['program'])==s['program_sha256'] and n['top_down']==s['top_down'], 'Pinned topology/top_down')
    return dict(program=n['program'],initial={g['id']:.5 for g in n['program']['groups']},top_down=n['top_down'],
        drives=drives,prior=0.0,evidence_score=c['score'],prior_score=s['baseline_score'],strength=memory['strength'],
        balance=len(memory['evidence_episodes'])/(1+len(memory['evidence_episodes'])),mismatch=0.0,kernel=s['config']['kernel'])


def check_cell(out,s,c,raw):
    require(raw['cell']==c and raw['evidence_kind']=='evaluator_formula_counterfactual', 'Cell identity')
    require(raw['native_selection'] is None and raw['native_cost'] is None, 'No native outcome or cost')
    d=expected_inputs(out,s,c); require(raw['inputs']==d, 'Independent drive intervention')
    error=close(raw['result'],calculate(d,d['kernel']),s['numeric_tolerance']); anchor_error=None
    if c['e0_scale']==c['e1_scale']:
        old=load(out/'anchor/replays'/f"g{int(c['e0_scale'])}-zero-M0-{c['score_id']}"/'pool.json')
        require(all(d[k]==old['inputs'][k] for k in ('program','initial','top_down','drives')), 'R074 numeric input correspondence')
        anchor_error=close(raw['result'],old['result'],s['numeric_tolerance'])
    return error,anchor_error


def check_summary(s,raws,report):
    nodes=s['nodes']; tol=s['direction_tolerance']; rows=[]; diffs=[]; delta_by={}; lookup={}
    for c in s['cells']:
        lookup[(c['e0_scale'],c['e1_scale'],c['score_id'])]=raws[c['id']]
    for c in s['cells']:
        raw=raws[c['id']]; r=raw['result']; base=lookup[(c['e0_scale'],c['e1_scale'],'s08')]['result']
        rows.append(dict(c,terminal={n:r['state'][n] for n in nodes},prior=raw['inputs']['prior'],drives=raw['inputs']['drives'],
                         convergence=r['convergence'],evaluable=r['evaluable'],trajectory_sha256=fingerprint(r['trajectory'])))
        ok=r['evaluable'] and base['evaluable']; delta={n:r['state'][n]-base['state'][n] if ok else None for n in nodes}
        direction={n:('negative' if v < -tol else 'positive' if v>tol else 'zero') if ok else None for n,v in delta.items()}
        pred={n:'not_evaluable' if not ok else 'falsified' if direction[n]!=s['predictions'][c['score_id']] else 'supported' for n in ('e:1','c:0')}
        record=dict(id=c['id'],evaluable=ok,deltas=delta,directions=direction,predictions=pred)
        diffs.append(record);delta_by[(c['e0_scale'],c['e1_scale'],c['score_id'])]=record
    pairs=[]
    for axis in ('e1_scale','e0_scale'):
        for fixed in (4.0,1.0):
            for sid in ('s06','s10'):
                keys=[(fixed,v,sid) if axis=='e1_scale' else (v,fixed,sid) for v in (4.0,1.0)]
                high,low=[delta_by[key] for key in keys];ok=high['evaluable'] and low['evaluable']
                ratios={};predictions={}
                for node in nodes:
                    a,b=high['deltas'][node],low['deltas'][node]
                    ratios[node]=None if not ok or abs(a)<=tol else abs(b)/abs(a)
                    if node in s['scale_predictions'][axis]:
                        predictions[node]='not_evaluable' if not ok else 'supported' if abs(b)-abs(a)>tol else 'falsified'
                pairs.append(dict(axis=axis,fixed_scale=fixed,score_id=sid,high_id=high['id'],low_id=low['id'],evaluable=ok,
                                  high_deltas=high['deltas'],low_deltas=low['deltas'],absolute_effect_ratios=ratios,predictions=predictions))
    interactions=[]
    for sid in ('s06','s10'):
        cells=[delta_by[(a,b,sid)] for a,b in ((1,1),(1,4),(4,1),(4,4))]; ok=all(c['evaluable'] for c in cells)
        values={n:sum(sign*c['deltas'][n] for sign,c in zip((1,-1,-1,1),cells)) if ok else None for n in nodes}
        interactions.append(dict(score_id=sid,evaluable=ok,signed_score_effect_interaction=values))
    boundary=dict(reanalysis=True,formula_replay_cells=12,prior_replay_correspondences=6,mixed_scale_cells=6,
        new_native_research_executions=0,new_training_executions=0,new_feedback_applications=0,new_independent_samples=0,
        native_expansions=None,native_decision_cost=None,actual_energy_joules=None,peak_memory_bytes=None)
    require(report==dict(rows=rows,differences=diffs,scale_pairs=pairs,interactions=interactions,**boundary), 'Independent full report arithmetic')


def main(out):
    s=load(out/'plan.json'); require(s==load(out/'source/experiments/exp-56-drive-factorization/frozen_spec.json'), 'Plan binding')
    require(files(out/'replays')==load(out/'raw_manifest.json')['files'], 'Raw hash coverage')
    raws={c['id']:load(out/'replays'/c['id']/'pool.json') for c in s['cells']}; errors=[]; anchors={}
    for c in s['cells']:
        error,anchor=check_cell(out,s,c,raws[c['id']]); errors.append(error)
        if anchor is not None: anchors[c['id']]=anchor
    require(len(anchors)==6, 'Six R074 correspondences')
    report=load(out/'summary.json'); check_summary(s,raws,report)
    c=s['cells'][0]; original=raws[c['id']]; rejected=[]
    for name,mutate in {
        'e0_drive':lambda x:x['inputs']['drives'].__setitem__('e:0',1.0),
        'e1_drive':lambda x:x['inputs']['drives'].__setitem__('e:1',0.0),
        'config':lambda x:x['inputs']['kernel'].__setitem__('evidence_gain',1.0),
        'prior':lambda x:x['inputs']['drives'].__setitem__('c:0',.01),
        'initial':lambda x:x['inputs']['initial'].__setitem__('c:0',.9),
        'top_down':lambda x:x['inputs'].__setitem__('top_down',False),
        'tick':lambda x:x['result']['trajectory'][0]['state'].__setitem__('e:1',.5),
        'convergence':lambda x:x['result']['convergence'].__setitem__('status','budget_exhausted'),
        'native_cost':lambda x:x.__setitem__('native_cost',{'kernel_ticks':35}),
    }.items():
        bad=deepcopy(original); mutate(bad)
        try: check_cell(out,s,c,bad)
        except (ValueError,AssertionError,KeyError): rejected.append(name)
        else: raise AssertionError('Undetected replay mutation: '+name)
    summary_rejected=[]
    for name,mutate in {
        'relation':lambda x:x['rows'][0]['terminal'].__setitem__('p:0:0',.5),
        'delta':lambda x:x['differences'][0]['deltas'].__setitem__('c:0',0.0),
        'scale_ratio':lambda x:x['scale_pairs'][0]['absolute_effect_ratios'].__setitem__('e:1',0.0),
        'interaction':lambda x:x['interactions'][0]['signed_score_effect_interaction'].__setitem__('c:0',0.0),
        'native_samples':lambda x:x.__setitem__('new_independent_samples',12),
    }.items():
        bad=deepcopy(report); mutate(bad)
        try: check_summary(s,raws,bad)
        except (ValueError,AssertionError,KeyError): summary_rejected.append(name)
        else: raise AssertionError('Undetected summary mutation: '+name)
    d=expected_inputs(out,s,c); short=calculate(d,dict(d['kernel'],max_ticks=1,patience=1))
    flat=calculate(dict(program=dict(groups=[dict(id='c:0',bias=0.0),dict(id='goal',bias=0.0)],links=[]),
                        drives={},initial={'c:0':.5,'goal':.5},top_down=True),dict(d['kernel'],self_excitation=0.0,inhibition=0.0))
    require(not short['evaluable'] and short['convergence']['status']=='budget_exhausted', 'Independent budget preservation')
    require(flat['evaluable'] and flat['convergence']['status']=='stable_ambiguous', 'Independent ambiguity preservation')
    synthetic={key:dict(value,result=short) for key,value in raws.items()}
    unknown=deepcopy(report)
    for row in unknown['rows']:
        row.update(terminal={n:short['state'][n] for n in s['nodes']},convergence=short['convergence'],evaluable=False,trajectory_sha256=fingerprint(short['trajectory']))
    for row in unknown['differences']:
        row.update(evaluable=False,deltas={n:None for n in s['nodes']},directions={n:None for n in s['nodes']},predictions={n:'not_evaluable' for n in row['predictions']})
    for row in unknown['scale_pairs']:
        row.update(evaluable=False,high_deltas={n:None for n in s['nodes']},low_deltas={n:None for n in s['nodes']},absolute_effect_ratios={n:None for n in s['nodes']},predictions={n:'not_evaluable' for n in row['predictions']})
    for row in unknown['interactions']:
        row.update(evaluable=False,signed_score_effect_interaction={n:None for n in s['nodes']})
    check_summary(s,synthetic,unknown)
    require(not FORBIDDEN & set(sys.modules), 'No native producer imports')
    dump(out/'verification.json',dict(verified=True,formula_cells=12,max_independent_formula_error=max(errors),
        prior_replay_matches=anchors,rejected_replay_mutations=rejected,rejected_summary_mutations=summary_rejected,
        budget_preserved=True,ambiguity_preserved=True,unevaluable_summary_preserved=True,
        native_producer_imports=[],new_native_research_executions=0,new_independent_samples=0))


if __name__ == '__main__':
    p=argparse.ArgumentParser(); p.add_argument('--out',type=Path,required=True); main(p.parse_args().out)
