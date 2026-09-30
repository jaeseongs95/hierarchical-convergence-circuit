"""Separate evidence and prior drives using the existing evaluator recurrence."""
import argparse
from pathlib import Path
from hcr import codec
from hcr.evaluation.audit import independent_step
from tools.r050_review_boundary.common import dump, fingerprint, load, require


def network(parent, identity):
    raw = load(parent/'evaluation'/identity/'inference.json')
    events = raw['execution']['packet']['document']['events']
    pools = [e['payload'] for e in events if e['event']=='r02_network' and e['payload']['kind']=='pool']
    require(len(pools)==1, 'Exactly one sealed pool')
    return raw, pools[0]


def inputs(parent, spec, cell):
    raw, n = network(parent, 's08-default-'+cell['checkpoint'])
    require(fingerprint(n['program'])==spec['program_sha256'] and n['top_down']==spec['top_down'], 'Frozen pool')
    memory = load(parent/'parent'/raw['cell']['memory_file'])
    circuit = memory['circuits'][0]; cfg = spec['config']['kernel']
    balance = len(circuit['evidence_episodes'])/(len(circuit['evidence_episodes'])+1)
    evidence_score = cell['score'] if cell['treatment']!='prior_only' else spec['baseline_score']
    prior_score = cell['score'] if cell['treatment']!='evidence_only' else spec['baseline_score']
    prior = cfg['prior_gain']*circuit['strength']*balance*(1-abs(prior_score))
    drives = dict(n['drives']); drives['e:1'] = cfg['evidence_gain']*evidence_score
    for key in spec['prior_drive_keys']: drives[key] = prior
    return dict(program=n['program'], initial=spec['initial'], top_down=n['top_down'], drives=drives,
                evidence_score=evidence_score, prior_score=prior_score, prior=prior,
                strength=circuit['strength'], balance=balance, mismatch=0.0)


def simulate(program, initial, drives, cfg, top_down):
    state=dict(initial); history=[]; stable=0; trajectory=[]; status='budget_exhausted'
    for i in range(1,cfg.max_ticks+1):
        nxt=independent_step(program,state,drives,cfg,top_down)
        residual=max(abs(nxt[k]-state[k]) for k in state)
        stable=stable+1 if residual<=cfg.residual_tolerance else 0
        trajectory.append(dict(tick=i,state=nxt,residual=residual,stable_steps=stable))
        margin=abs(2*nxt['goal']-1)
        if stable>=cfg.patience:
            status='stable_decision' if margin>=cfg.margin_threshold else 'stable_ambiguous'
            state=nxt;break
        if history and residual>cfg.residual_tolerance*10 and max(abs(nxt[k]-history[-1][k]) for k in nxt)<cfg.residual_tolerance:
            status='oscillating';state=nxt;break
        history.append(state);history=history[-3:];state=nxt
    evaluable=status in ('stable_decision','stable_ambiguous')
    return dict(trajectory=trajectory,state=state,activation=state['c:0'],
                convergence=dict(status=status,ticks=len(trajectory),residual=residual,margin=margin,stable_steps=stable),
                evaluable=evaluable)


def main(out):
    spec=load(out/'plan.json');cfg=codec.adaptive_config_from(spec['config']).kernel
    for cell in spec['cells']:
        data=inputs(out/'parent',spec,cell)
        result=simulate(data['program'],data['initial'],data['drives'],cfg,data['top_down'])
        result['eligibility']={arm:(result['activation']>=threshold if result['evaluable'] else None)
                               for arm,threshold in spec['thresholds'].items()}
        dump(out/'replays'/cell['id']/'pool.json',dict(cell=cell,inputs=data,result=result,
             evidence_kind='evaluator_formula_counterfactual',native_selection=None,native_cost=None))
        print(cell['id'],result['convergence']['status'],flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);main(p.parse_args().out)
