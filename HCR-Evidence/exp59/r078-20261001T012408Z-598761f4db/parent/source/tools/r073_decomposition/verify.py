"""A second recurrence and separate report checks; no producer calls."""
import argparse
from copy import deepcopy
from math import exp
from pathlib import Path
import sys
from tools.r050_review_boundary.common import dump, files, fingerprint, load, require
from tools.r050_review_boundary.audit import FORBIDDEN
from tools.r072_range.verify import check as check_native


def expected_inputs(parent,spec,cell):
    raw=load(parent/'evaluation'/('s08-default-'+cell['checkpoint'])/'inference.json')
    n=next(e['payload'] for e in raw['execution']['packet']['document']['events']
           if e['event']=='r02_network' and e['payload']['kind']=='pool')
    c=load(parent/'parent'/raw['cell']['memory_file'])['circuits'][0]
    score_e=spec['baseline_score'] if cell['treatment']=='prior_only' else cell['score']
    score_p=spec['baseline_score'] if cell['treatment']=='evidence_only' else cell['score']
    balance=len(c['evidence_episodes'])/(1+len(c['evidence_episodes']))
    prior=spec['config']['kernel']['prior_gain']*c['strength']*balance*(1-abs(score_p))
    drives=dict(n['drives']);drives['e:1']=spec['config']['kernel']['evidence_gain']*score_e
    for g in n['program']['groups']:
        if g['level']==1 and g['id']!='goal':drives[g['id']]=prior
    require(fingerprint(n['program'])==spec['program_sha256'] and n['top_down'] is spec['top_down'],'Sealed program/top_down')
    return dict(program=n['program'],initial={g['id']:.5 for g in n['program']['groups']},
        top_down=n['top_down'],drives=drives,evidence_score=score_e,prior_score=score_p,prior=prior,
        strength=c['strength'],balance=balance,mismatch=0.0)


def calculate(data,k):
    state=dict(data['initial']);stable=0;history=[];trajectory=[];status='budget_exhausted'
    for number in range(1,k['max_ticks']+1):
        # Link accumulation first and explicit positive/negative channels differ
        # from the evaluator's target-wise single-difference implementation.
        totals={g['id']:g['bias']+data['drives'].get(g['id'],0.0) for g in data['program']['groups']}
        for link in data['program']['links']:
            if data['top_down'] or link['kind']!='top_down':
                totals[link['target']]+=link['weight']*(2*state[link['source']]-1)
        nxt={}
        for key,drive in totals.items():
            old=state[key]
            positive=drive+k['self_excitation']*old-k['inhibition']*(1-old)
            negative=-drive+k['self_excitation']*(1-old)-k['inhibition']*old
            z=(positive-negative)/k['temperature']
            target=1/(1+exp(-z)) if z>=0 else exp(z)/(1+exp(z))
            nxt[key]=(1-k['damping'])*old+k['damping']*target
        residual=max(abs(nxt[key]-state[key]) for key in state)
        stable=stable+1 if residual<=k['residual_tolerance'] else 0
        trajectory.append(dict(tick=number,state=nxt,residual=residual,stable_steps=stable))
        margin=abs(2*nxt['goal']-1)
        if stable>=k['patience']:
            status='stable_decision' if margin>=k['margin_threshold'] else 'stable_ambiguous';state=nxt;break
        if history and residual>10*k['residual_tolerance'] and max(abs(nxt[key]-history[-1][key]) for key in nxt)<k['residual_tolerance']:
            status='oscillating';state=nxt;break
        history.append(state);history=history[-3:];state=nxt
    return dict(trajectory=trajectory,state=state,activation=state['c:0'],
        convergence=dict(status=status,ticks=len(trajectory),residual=residual,margin=margin,stable_steps=stable),
        evaluable=status in ('stable_decision','stable_ambiguous'))


def close(a,b,tol):
    require(type(a)==type(b),'Exact measurement type')
    if isinstance(a,dict):
        require(a.keys()==b.keys(),'Exact measurement keys')
        return max((close(a[k],b[k],tol) for k in a),default=0.0)
    if isinstance(a,list):
        require(len(a)==len(b),'Trajectory length');return max((close(x,y,tol) for x,y in zip(a,b)),default=0.0)
    if isinstance(a,float):require(abs(a-b)<=tol,'Independent numeric recurrence');return abs(a-b)
    require(a==b,'Exact measurement value');return 0.0


def check_cell(out,spec,cell,raw):
    require(raw['cell']==cell and raw['evidence_kind']=='evaluator_formula_counterfactual','Counterfactual identity')
    require(raw['native_selection'] is None and raw['native_cost'] is None,'No invented native result/cost')
    data=expected_inputs(out/'parent',spec,cell);require(raw['inputs']==data,'Exact independent drive intervention')
    calculated=calculate(data,spec['config']['kernel'])
    calculated['eligibility']={arm:(calculated['activation']>=threshold if calculated['evaluable'] else None)
                              for arm,threshold in spec['thresholds'].items()}
    error=close(raw['result'],calculated,spec['numeric_tolerance'])
    match=None
    if cell['treatment']=='joint':
        # A joint replay corresponds to a recorded native pool, not to a new run.
        errors=[]
        for arm in spec['thresholds']:
            old=load(out/'parent/evaluation'/f"{cell['score_id']}-{arm}-{cell['checkpoint']}"/'inference.json')
            events=old['execution']['packet']['document']['events']
            n=next(e['payload'] for e in events if e['event']=='r02_network' and e['payload']['kind']=='pool')
            require(n['program']==data['program'] and n['drives']==data['drives'] and n['top_down']==data['top_down'],'Observed joint input')
            ticks=[{k:e['payload'][k] for k in ('tick','state','residual','stable_steps')}
                   for e in events if e['event']=='r02_tick' and e['payload']['network_id']==n['network_id']]
            settled=next(e['payload'] for e in events if e['event']=='r02_settled' and e['payload']['network_id']==n['network_id'])
            errors.append(close(raw['result']['trajectory'],ticks,spec['numeric_tolerance']))
            errors.append(close(raw['result']['convergence'],settled['convergence'],spec['numeric_tolerance']))
            errors.append(close(raw['result']['state'],settled['state'],spec['numeric_tolerance']))
            activation=next(e['payload']['activations'][0] for e in events if e['event']=='r02_pool_result')
            require(raw['result']['eligibility'][arm] is activation['eligible'],'Observed eligibility')
        match=dict(verified=True,max_error=max(errors),native_anchor_arms=2)
    return error,match


def check_summary(out,spec,summary):
    expected_rows=[];lookup={}
    for cell in spec['cells']:
        raw=load(out/'replays'/cell['id']/'pool.json');r=raw['result'];d=raw['inputs']
        row=dict(cell,activation=r['activation'],prior=d['prior'],drives=d['drives'],convergence=r['convergence'],
            evaluable=r['evaluable'],eligibility=r['eligibility'],trajectory_sha256=fingerprint(r['trajectory']),evidence_kind=raw['evidence_kind'])
        expected_rows.append(row);lookup[cell['id']]=row
    require(summary['rows']==expected_rows,'Exact report row projection')
    expected=[]
    for checkpoint in spec['checkpoints']:
        baseline=lookup[f's08-{checkpoint}-joint']
        for score_id,score in spec['scores'].items():
            terms={key:lookup[f'{score_id}-{checkpoint}-{treatment}'] for key,treatment in
                   [('evidence','evidence_only'),('prior','prior_only'),('joint','joint')]}
            valid=baseline['evaluable'] and all(r['evaluable'] for r in terms.values())
            deltas={key:r['activation']-baseline['activation'] if valid else None for key,r in terms.items()}
            tol=spec['direction_tolerance']
            directions={key:('positive' if value>tol else 'negative' if value < -tol else 'zero') if valid else None
                        for key,value in deltas.items()}
            predictions={key:('not_evaluable' if not valid else 'supported' if direction==spec['predictions'][score_id][key] else 'falsified')
                         for key,direction in directions.items()}
            interaction=(terms['joint']['activation']-terms['evidence']['activation']-terms['prior']['activation']+baseline['activation']) if valid else None
            expected.append(dict(score=score,checkpoint=checkpoint,evaluable=valid,activation_deltas=deltas,
                interaction=interaction,directions=directions,predictions=predictions))
    require(summary['comparisons']==expected,'Independent differences/interaction/predictions')
    pairs=[]
    for treatment in ('prior_only','joint'):
        a,b=[load(out/'replays'/f's10-{m}-{treatment}'/'pool.json') for m in spec['checkpoints']]
        valid=all(x['result']['evaluable'] for x in (a,b))
        pairs.append(dict(treatment=treatment,evaluable=valid,prior_zero=all(x['inputs']['prior']==0 for x in (a,b)),
            inputs_equal=all(a['inputs'][key]==b['inputs'][key] for key in ('program','initial','top_down','drives')),
            trajectory_equal=a['result']['trajectory']==b['result']['trajectory'],
            prediction='not_evaluable' if not valid else 'supported' if a['result']==b['result'] else 'falsified'))
    require(summary['zero_prior_checkpoint_pairs']==pairs,'Zero-prior checkpoint comparison')
    boundary=dict(baseline_score=.8,reanalysis=True,new_native_research_executions=0,new_training_executions=0,
        new_feedback_applications=0,new_independent_samples=0,native_anchor_cells=12,formula_replay_cells=18,
        observed_corresponding_replays=6,synthetic_native_executions=0,native_expansions=None,
        native_decision_cost=None,actual_energy_joules=None,peak_memory_bytes=None)
    require({k:v for k,v in summary.items() if k not in ('rows','comparisons','zero_prior_checkpoint_pairs')}==boundary,'Exact sample/cost boundary')


def main(out):
    spec=load(out/'plan.json');require(files(out/'replays')==load(out/'raw_manifest.json')['files'],'Replay hash coverage')
    native=load(out/'native-reanalysis.json');check_native(out/'parent',native)
    require(native==load(out/'parent/summary.json'),'Native report binding')
    errors=[];matches={}
    for cell in spec['cells']:
        raw=load(out/'replays'/cell['id']/'pool.json');error,match=check_cell(out,spec,cell,raw)
        errors.append(error)
        if match is not None:matches[cell['id']]=match
    summary=load(out/'summary.json');check_summary(out,spec,summary)
    cell=spec['cells'][0];original=load(out/'replays'/cell['id']/'pool.json')
    mutations={
        'drive':lambda x:x['inputs']['drives'].__setitem__('e:1',0.0),
        'prior':lambda x:x['inputs'].__setitem__('prior',0.0),
        'initial':lambda x:x['inputs']['initial'].__setitem__('c:0',.9),
        'top_down':lambda x:x['inputs'].__setitem__('top_down',False),
        'tick':lambda x:x['result']['trajectory'][0]['state'].__setitem__('c:0',.5),
        'convergence':lambda x:x['result']['convergence'].__setitem__('status','budget_exhausted'),
        'eligibility':lambda x:x['result']['eligibility'].__setitem__('default',False),
        'native_cost':lambda x:x.__setitem__('native_cost',{'kernel_ticks':35}),
    }
    rejected=[]
    for name,mutate in mutations.items():
        bad=deepcopy(original);mutate(bad)
        try:check_cell(out,spec,cell,bad)
        except (ValueError,AssertionError,KeyError):rejected.append(name)
        else:raise AssertionError('Undetected replay mutation: '+name)
    rejected_summary=[]
    for name,mutate in {
        'activation':lambda x:x['rows'][0].__setitem__('activation',.5),
        'interaction':lambda x:x['comparisons'][0].__setitem__('interaction',1.0),
        'zero_prior':lambda x:x['zero_prior_checkpoint_pairs'][0].__setitem__('trajectory_equal',False),
        'native_samples':lambda x:x.__setitem__('new_native_research_executions',18),
    }.items():
        bad=deepcopy(summary);mutate(bad)
        try:check_summary(out,spec,bad)
        except (ValueError,AssertionError,KeyError):rejected_summary.append(name)
        else:raise AssertionError('Undetected summary mutation: '+name)
    short=calculate(expected_inputs(out/'parent',spec,cell),dict(spec['config']['kernel'],max_ticks=1,patience=1))
    require(not short['evaluable'] and short['convergence']['status']=='budget_exhausted','Independent budget check')
    require(not FORBIDDEN & set(sys.modules),'Verifier imported native producer')
    dump(out/'verification.json',dict(verified=True,formula_cells=18,native_anchor_cells=12,
        observed_joint_matches=matches,max_independent_formula_error=max(errors),
        rejected_replay_mutations=rejected,rejected_summary_mutations=rejected_summary,
        budget_preserved=True,native_producer_imports=[],new_native_research_executions=0,new_independent_samples=0))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);main(p.parse_args().out)
