"""Replay sealed pool equations; never import or execute the native producer."""
import argparse
from copy import deepcopy
from pathlib import Path
import sys
from hcr import codec
from hcr.evaluation.adaptive_audit_support import pool_network, decision_network
from hcr.evaluation.audit import independent_step
from tools.r050_review_boundary.audit import candidate_measures, counter_values, FORBIDDEN
from tools.r050_review_boundary.common import dump, fingerprint, load, require
from tools.r063_formation.audit import verify_execution


def replay(row, memory, config):
    e = row['execution']; obs = codec.observation_from(row['delivery']['observation'])
    events = e['packet']['document']['events']
    networks = [x['payload'] for x in events if x['event'] == 'r02_network']
    pools = [n for n in networks if n['kind'] == 'pool']
    require(len(pools) == 1, 'One pool per frozen new-session cell')
    n = pools[0]; candidates = n['metadata']['candidates']
    records = [dict(circuit_id=c['circuit_id'], binding=c['binding']) for c in candidates]
    program, drives, meta, _ = pool_network(obs, records, memory, config)
    require(n['program'] == program and n['drives'] == drives and candidates == meta,
            'Independent pool grammar/strength/drive/mismatch')
    ticks = [x['payload'] for x in events if x['event'] == 'r02_tick'
             and x['payload']['network_id'] == n['network_id']]
    state = {g['id']: .5 for g in program['groups']}; error = 0.0
    for tick in ticks:
        state = independent_step(program, state, drives, config.kernel, n['top_down'])
        error = max(error, max(abs(state[k] - tick['state'][k]) for k in state))
        require(error < 2e-12, 'Pool trajectory recurrence')
    settled = next(x['payload'] for x in events if x['event'] == 'r02_settled'
                   and x['payload']['network_id'] == n['network_id'])
    require(max(abs(state[k] - settled['state'][k]) for k in state) < 2e-12,
            'Pool settled state')
    activations = next(x['payload']['activations'] for x in events
                       if x['event'] == 'r02_pool_result')
    require(len(activations) == len(meta) == 1, 'Single candidate, no circuit competition')
    c = meta[0]; a = activations[0]; activation = state['c:0']
    stable = settled['convergence']['status'] in ('stable_decision', 'stable_ambiguous')
    eligible = stable and activation >= config.activation_threshold and c['mismatch'] <= config.mismatch_threshold
    require(abs(a['activation'] - activation) < 2e-12 and a['eligible'] is eligible
            and {k: a[k] for k in c} == c, 'Pool eligibility readout')
    proposals = next(x['payload'] for x in events if x['event'] == 'r02_proposals')
    chosen = next(x['payload']['candidate'] for x in events if x['event'] == 'r02_expansion')
    require(chosen == proposals['candidates'][0], 'First proposed candidate selection')
    require((chosen['source'] == 'circuit') is eligible, 'Circuit/primitive eligibility boundary')
    decision = [n for n in networks if n['kind'] == 'decision']
    require(len(decision) == 1, 'Single final decision network')
    d = decision[0]; expected, ddrives = decision_network(obs, d['metadata']['routes'], config,
                                                        judgment_prior='route_only')
    require(d['program'] == expected and d['drives'] == ddrives, 'Route-only decision input')
    dticks = [x['payload']['state'] for x in events if x['event'] == 'r02_tick'
              and x['payload']['network_id'] == d['network_id']]
    return dict(id=row['cell']['id'], strength=memory['circuits'][0]['strength'], prior=c['prior'],
        mismatch=c['mismatch'], activation=a['activation'], eligible=eligible,
        activation_threshold=config.activation_threshold, mismatch_threshold=config.mismatch_threshold,
        stable=stable, pool_status=settled['convergence']['status'], pool_ticks=len(ticks),
        pool_program_sha256=fingerprint(program), pool_drives=drives,
        pool_trajectory=[t['state'] for t in ticks], max_replay_error=error,
        selected_source=chosen['source'], selected_edges=chosen['edges'],
        decision_program_sha256=fingerprint(d['program']), decision_drives=ddrives,
        decision_trajectory_sha256=fingerprint(dticks), decision_ticks=len(dticks),
        measures=candidate_measures(e, False), cost=counter_values(e), circuit_competition='not_measurable_single_candidate')


def summarize(rows):
    lookup = {r['id']: r for r in rows}; pairs = {}
    for payload in ('stale', 'fresh'):
        a, b = [lookup[f'new-{m}-{payload}'] for m in ('M0', 'M1')]
        require(len(a['pool_trajectory']) == len(b['pool_trajectory']), 'Paired tick alignment')
        delta = max(abs(x[k]-y[k]) for x,y in zip(a['pool_trajectory'], b['pool_trajectory']) for k in x)
        # A threshold interval is a derived reclassification, not a new native execution.
        lo, hi = sorted([a['activation'], b['activation']])
        feasible = lo < hi and a['stable'] and b['stable'] and max(a['mismatch'],b['mismatch']) <= a['mismatch_threshold']
        pairs[payload] = dict(prior_delta=b['prior']-a['prior'], activation_delta=b['activation']-a['activation'],
            max_pool_trajectory_delta=delta, pool_program_equal=a['pool_program_sha256']==b['pool_program_sha256'],
            pool_drive_equal=a['pool_drives']==b['pool_drives'], eligible_equal=a['eligible']==b['eligible'],
            selection_equal=(a['selected_source'],a['selected_edges'])==(b['selected_source'],b['selected_edges']),
            decision_program_equal=a['decision_program_sha256']==b['decision_program_sha256'],
            decision_drives_equal=a['decision_drives']==b['decision_drives'],
            decision_trajectory_equal=a['decision_trajectory_sha256']==b['decision_trajectory_sha256'],
            measures_equal=a['measures']==b['measures'], integer_cost_equal=a['cost']==b['cost'],
            derived_activation_threshold_interval=dict(lower_exclusive=lo,upper_inclusive=hi,
                midpoint=(lo+hi)/2) if feasible else None)
    return dict(rows=[{k:v for k,v in r.items() if k!='pool_trajectory'} for r in rows],pairs=pairs,
        reanalysis=True,new_native_research_executions=0,new_independent_samples=0,
        pure_strength_intervention=False,circuit_competition='not_measurable_single_candidate',
        actual_energy_joules=None,peak_memory_bytes=None,
        claim_boundary='Same R069 evidence. Checkpoint comparison and formula attribution, no new sample, native threshold intervention or autonomous sensing.')


def main(out, selftest=False):
    plan=load(out/'plan.json'); parent=out/'parent'; old=load(parent/'plan.json')
    config=codec.adaptive_config_from(old['config']);rows=[]
    for name in plan['cells']:
        row=load(parent/'evaluation'/name/'inference.json'); memory=load(parent/'memory'/f"{row['cell']['memory']}.json")
        verify_execution(old,row['execution'],dict(observation=row['delivery']['observation']),memory,True,'adapt','r069-'+name)
        rows.append(replay(row,memory,config))
    if selftest:
        row=load(parent/'evaluation/new-M0-stale/inference.json');memory=load(parent/'memory/M0.json')
        def event(r, name): return next(x['payload'] for x in r['execution']['packet']['document']['events'] if x['event']==name)
        mutations = {
            'pool_drive': lambda r: event(r,'r02_network')['drives'].__setitem__('c:0',.9),
            'pool_prior': lambda r: event(r,'r02_network')['metadata']['candidates'][0].__setitem__('prior',.9),
            'pool_tick': lambda r: event(r,'r02_tick')['state'].__setitem__('c:0',.5),
            'pool_activation': lambda r: event(r,'r02_pool_result')['activations'][0].__setitem__('activation',.5),
            'pool_eligibility': lambda r: event(r,'r02_pool_result')['activations'][0].__setitem__('eligible',False),
            'selected_source': lambda r: event(r,'r02_expansion')['candidate'].__setitem__('source','primitive'),
            'decision_drive': lambda r: next(x['payload'] for x in r['execution']['packet']['document']['events']
                if x['event']=='r02_network' and x['payload']['kind']=='decision')['drives'].__setitem__('goal',.033),
        }
        rejected=[]
        for name, mutate in mutations.items():
            bad=deepcopy(row);mutate(bad)
            try: replay(bad,memory,config)
            except (ValueError,AssertionError,RuntimeError,KeyError): rejected.append(name)
            else: raise AssertionError('Undetected measurement mutation '+name)
        bad=deepcopy(memory);bad['circuits'][0]['strength']*=2
        try: replay(row,bad,config)
        except (ValueError,AssertionError,RuntimeError,KeyError): rejected.append('memory_strength')
        else: raise AssertionError('Undetected strength mutation')
        require(not FORBIDDEN & set(sys.modules), 'Producer import boundary')
        dump(out/'validation/selftest.json',dict(verified=True,rejected_mutations=rejected,
            synthetic_native_executions=0,research_sample=False));return
    require(not FORBIDDEN & set(sys.modules), 'Producer import boundary')
    dump(out/'analysis.json',dict(rows=rows));dump(out/'summary.json',summarize(rows))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--selftest',action='store_true')
    a=p.parse_args();main(a.out,a.selftest)
