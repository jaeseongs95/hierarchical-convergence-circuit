"""Verify projections against independently audited packets, without importing analysis."""
import argparse
from pathlib import Path
import sys
from hcr.evaluation.review_audit import packet_states
from tools.r050_review_boundary.common import dump, fingerprint, load, require
from tools.r050_review_boundary.audit import candidate_measures, counter_values, FORBIDDEN


def main(out):
    rows=load(out/'analysis.json')['rows'];summary=load(out/'summary.json');plan=load(out/'plan.json')
    require([r['id'] for r in rows]==plan['cells'],'Exact row coverage')
    require(summary['rows']==[{k:v for k,v in r.items() if k!='pool_trajectory'} for r in rows], 'Summary projection')
    for r in rows:
        raw=load(out/'parent/evaluation'/r['id']/'inference.json');e=raw['execution']
        _,audit=packet_states(e['packet']);require(audit['verified'],'Independent session audit')
        ev=e['packet']['document']['events']
        n=next(x['payload'] for x in ev if x['event']=='r02_network' and x['payload']['kind']=='pool')
        pool=next(x['payload'] for x in ev if x['event']=='r02_pool_result')['activations'][0]
        require(all(r[k]==pool[k] for k in ('activation','eligible','mismatch','prior')), 'Raw pool measures')
        require(r['pool_drives']==n['drives'] and r['pool_program_sha256']==fingerprint(n['program']), 'Network projection')
        ticks=[x['payload']['state'] for x in ev if x['event']=='r02_tick' and x['payload']['network_id']==n['network_id']]
        require(r['pool_trajectory']==ticks and r['pool_ticks']==len(ticks), 'Whole pool trajectory')
        d=next(x['payload'] for x in ev if x['event']=='r02_network' and x['payload']['kind']=='decision')
        dt=[x['payload']['state'] for x in ev if x['event']=='r02_tick' and x['payload']['network_id']==d['network_id']]
        require(r['decision_trajectory_sha256']==fingerprint(dt) and r['decision_ticks']==len(dt)
                and r['decision_program_sha256']==fingerprint(d['program']) and r['decision_drives']==d['drives'], 'Decision projection')
        choice=next(x['payload']['candidate'] for x in ev if x['event']=='r02_expansion')
        require(r['selected_source']==choice['source'] and r['selected_edges']==choice['edges'], 'Actual choice')
        require(r['measures']==candidate_measures(e,False) and r['cost']==counter_values(e), 'Readout and separate cost counters')
        memory=load(out/'parent/memory'/f"{raw['cell']['memory']}.json")
        require(r['strength']==memory['circuits'][0]['strength'],'Memory projection')
    for payload,pair in summary['pairs'].items():
        a,b=[next(r for r in rows if r['id']==f'new-{m}-{payload}') for m in ('M0','M1')]
        require(pair['prior_delta']==b['prior']-a['prior'] and pair['activation_delta']==b['activation']-a['activation'], 'Pair deltas')
        for key, field in [('pool_program_equal','pool_program_sha256'),('pool_drive_equal','pool_drives'),
                           ('eligible_equal','eligible'),('decision_program_equal','decision_program_sha256'),
                           ('decision_drives_equal','decision_drives'),('decision_trajectory_equal','decision_trajectory_sha256'),
                           ('measures_equal','measures'),('integer_cost_equal','cost')]:
            require(pair[key] is (a[field]==b[field]),'Pair equality '+key)
        delta=max(abs(x[k]-y[k]) for x,y in zip(a['pool_trajectory'],b['pool_trajectory']) for k in x)
        require(pair['max_pool_trajectory_delta']==delta,'Trajectory delta')
        require(pair['selection_equal'] is ((a['selected_source'],a['selected_edges'])==(b['selected_source'],b['selected_edges'])), 'Selection pair')
        interval=pair['derived_activation_threshold_interval']
        if interval is not None:
            lo,hi=sorted([a['activation'],b['activation']]);mid=interval['midpoint']
            require(interval['lower_exclusive']==lo and interval['upper_inclusive']==hi and lo<mid<=hi, 'Derived interval')
            require(a['stable'] and b['stable'] and max(a['mismatch'],b['mismatch'])<=a['mismatch_threshold'],'Threshold alone applicable')
        else:
            require(a['activation']==b['activation'] or not (a['stable'] and b['stable']) or
                    max(a['mismatch'],b['mismatch'])>a['mismatch_threshold'],'Missing interval justified')
    require(summary['reanalysis'] and summary['new_native_research_executions']==summary['new_independent_samples']==0,
            'No new sample claim')
    require(not (FORBIDDEN|{'tools.r070_pool.analyze'}) & set(sys.modules),'Independent projection process')
    dump(out/'verification.json',dict(verified=True,packet_replays=len(rows),independent_process=True,
        independent_researcher=False,summary_projection_verified=True))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);main(p.parse_args().out)
