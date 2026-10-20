"""Saved full-state/controller/cost audit; no native tick or settle calls."""
from copy import deepcopy
import math
from hcr.model import Cost,fingerprint
from tools.r19_cross_level.probe import require
from tools.r24_trust_boundary.census import freeze
from tools.r26_contraction_warmstart.verify import scalar
from tools.r29_research_direction.verify import verify as partition_verify

def audit_pair(data,job,entry,tolerance):
    require(data['job']==job and data['entry_sha256']==fingerprint(entry),'job/input binding')
    require(data['order']==job['order'] and set(data['arms'])=={'native','shared'},'pair order')
    require(data['native_settle_calls']==2 and data['training_calls']==data['world_measure_calls']==0,'pair scope')
    native,shared=(data['arms'][a] for a in ['native','shared']);ids=[g['id'] for g in entry['program']['groups']]
    require(native['plan'] is native['verification'] is None,'baseline no plan')
    checked=partition_verify(entry,shared['plan']);require(shared['verification']==checked,'partition verification')
    maximum=0.;ticks=len(native['kernel']['ticks'])
    for arm,row in [('native',native),('shared',shared)]:
        require(row['arm']==arm and row['binding']==fingerprint(entry) and row['native_settle_calls']==1,'arm binding')
        k=row['kernel'];require(freeze(k['program'])==freeze(entry['program']) and freeze(k['drives'])==freeze(entry['drives']) and freeze(k['initial'])==freeze(entry['initial']),'kernel inputs')
        require(k['program_sha256']==fingerprint(entry['program']),'program digest')
        require(k['state_key_order']==ids and all(t['state_key_order']==ids for t in k['ticks']),'full state order')
        n=len(k['ticks']);require(n==ticks and 0<n<=entry['config']['max_ticks'],'tick matrix')
        full=Cost().snapshot();full.update(kernel_ticks=n,group_updates=n*len(ids),normalization_ops=n*len(ids),signal_transmissions=n*len(entry['program']['links']))
        replay=deepcopy(k);replay['cost']=full;maximum=max(maximum,scalar(replay,entry['config'],tolerance))
        groups=len(ids) if arm=='native' else len(shared['plan']['classes'])
        links=len(entry['program']['links']) if arm=='native' else sum(len([e for e in entry['program']['links'] if e['target']==c[0]]) for c in shared['plan']['classes'])
        expected=dict(full,group_updates=n*groups,normalization_ops=n*groups,signal_transmissions=n*links)
        require(k['cost']==expected,'actual arithmetic cost')
        require(row['work']==dict(tick_calls=n,full_state_output_slots=n*len(ids),alias_copy_slots=n*(len(ids)-groups) if arm=='shared' else 0),'restoration ledger')
        timing=row['timing']
        for axis in ['cpu','wall']:
            a,b=timing['cold_'+axis+'_seconds'],timing['preparation_seconds'][axis]
            require(type(a) is float and type(b) is float and math.isfinite(a) and math.isfinite(b) and 0<=b<=a,'cold timing inclusion')
            require(type(timing['clock_resolution_seconds'][axis]) is float and timing['clock_resolution_seconds'][axis]>0,'clock resolution')
        require(type(timing['payload_serialized_bytes']) is int and timing['payload_serialized_bytes']>0,'serialized payload')
    for field in ['program','program_sha256','drives','initial','ticks','state','state_key_order','convergence','adopted']:
        require(freeze(native['kernel'][field])==freeze(shared['kernel'][field]),'exact native/shared '+field)
    before,after=(v['kernel']['cost'] for v in [native,shared])
    return dict(key=job['key'],program=job['program'],condition=job['condition'],ticks=ticks,nontrivial_classes=checked['nontrivial_classes'],groups_saved=before['group_updates']-after['group_updates'],links_saved=before['signal_transmissions']-after['signal_transmissions'],normalizations_saved=before['normalization_ops']-after['normalization_ops'],alias_copy_slots=shared['work']['alias_copy_slots'],cold_seconds={a:dict(cpu=data['arms'][a]['timing']['cold_cpu_seconds'],wall=data['arms'][a]['timing']['cold_wall_seconds']) for a in ['native','shared']},scalar_max_absolute_error=maximum)

def audit_all(data,p):
    from tools.r30_spatial_sharing.probe import entry_for
    require(set(data)=={j['key'] for j in p['cases']} and len(data)==32,'fixed32pair matrix')
    rows=[audit_pair(data[j['key']],j,entry_for(p,j),p['scalar_tolerance']) for j in p['cases']]
    calls=2*len(rows);ticks=2*sum(r['ticks'] for r in rows)
    require(calls==p['maximum_native_settle_calls']==64 and ticks<=p['maximum_logical_ticks']==10240,'global caps')
    return dict(status='A1_EXACT_SHARED_RUNTIME_AUDITED',exact_pairs=len(rows),opportunity_pairs=sum(r['nontrivial_classes']>0 for r in rows),actual_arithmetic_reduction_pairs=sum(r['groups_saved']>0 for r in rows),native_settle_calls=calls,kernel_ticks=ticks,actual_groups_saved=sum(r['groups_saved'] for r in rows),actual_links_saved=sum(r['links_saved'] for r in rows),actual_normalizations_saved=sum(r['normalizations_saved'] for r in rows),alias_copy_slots=sum(r['alias_copy_slots'] for r in rows),rows=rows,cold_totals={a:{axis:sum(r['cold_seconds'][a][axis] for r in rows) for axis in ['cpu','wall']} for a in ['native','shared']},scalar_max_absolute_error=max(r['scalar_max_absolute_error'] for r in rows),training_calls=0,world_measure_calls=0,statistical_speed_verdict=None,learned_compression_tested=False,production_adoption=False)

def mutations(data,p):
    rejected={};key=p['cases'][0]['key']
    for name in ['binding','trace','state_order','cost','restoration','timing','readout','partition','missing_pair']:
        bad=deepcopy(data);row=bad[key]['arms']['shared']
        if name=='binding':row['binding']='0'*64
        elif name=='trace':row['kernel']['ticks'][0]['state']['goal']+=.01
        elif name=='state_order':row['kernel']['state_key_order'].reverse()
        elif name=='cost':row['kernel']['cost']['group_updates']-=1
        elif name=='restoration':row['work']['alias_copy_slots']+=1
        elif name=='timing':row['timing']['preparation_seconds']['cpu']=row['timing']['cold_cpu_seconds']+1.
        elif name=='readout':row['kernel']['adopted']='mutated'
        elif name=='partition':row['plan']['classes'][0].append(row['plan']['classes'][0][0])
        else:del bad[key]
        try:audit_all(bad,p)
        except ValueError as exc:rejected[name]=str(exc)
        else:raise ValueError('mutation accepted '+name)
    return rejected
