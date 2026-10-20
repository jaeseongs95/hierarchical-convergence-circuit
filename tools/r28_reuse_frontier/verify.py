"""Separate scalar/oracle audit of fixed lifecycle records, never native settle."""
from copy import deepcopy
import math
from hcr.model import fingerprint
from tools.r19_cross_level.probe import require
from tools.r24_trust_boundary.census import freeze
from tools.r26_contraction_warmstart.verify import rational_gate,scalar

def audit_all(data,p):
    from tools.r28_reuse_frontier.probe import context
    base,cfg,program,pr,value=context(p);require(set(data)=={j['key'] for j in p['cases']},'job matrix')
    expected_jobs=[];streams=base['streams']
    for block,(arms,reverse) in enumerate(p['block_order']):
        for stream in (list(reversed(streams)) if reverse else streams):
            for arm in arms:expected_jobs.append(dict(key=f"b{block}_{stream['key']}_{arm}",block=block,stream=stream['key'],policy=arm))
    require(p['cases']==expected_jobs and len(expected_jobs)==48,'frozen job order')
    maximum=0.;total_ticks=0;total_calls=0;equivalent=0;quality=0;nontrivial=0;totals=[]
    for job in p['cases']:
        e=data[job['key']];arm=job['policy'];stream=next(s for s in streams if s['key']==job['stream']);previous=None
        binding=fingerprint(dict(scope=[stream['key'],'reset' if arm=='reset' else 'guarded'],program=pr,config=base['kernel'],dynamics_sha256=value['sources']['native']))
        require(e['job']==job and e['binding']==binding and len(e['rows'])==6,'lifecycle binding')
        for index,(cell,row) in enumerate(zip(stream['cells'],e['rows'],strict=True)):
            kernel=row['kernel'];drives=dict(f0=cfg.evidence_gain*cell['scores'][0],f1=cfg.evidence_gain*cell['scores'][1],goal=0.)
            require(row['index']==index and row['cell']==cell['key'] and freeze(row['cache_before'])==freeze(previous),'cache provenance')
            gate=None if arm=='reset' or previous is None else dict(eligible=rational_gate(pr,base['kernel'],drives,base['weights'])['eligible'])
            require(row['gate']==gate,'gate oracle')
            if arm=='reset':choice=dict(action='reset',reason='baseline',source_cell=None)
            elif previous is None:choice=dict(action='reset',reason='no_source',source_cell=None)
            elif not gate['eligible']:choice=dict(action='reset',reason='contraction_not_established',source_cell=None)
            else:choice=dict(action='warm',reason='real_contraction_screen',source_cell=previous['cell'])
            initial={g.id:.5 for g in program.groups} if choice['action']=='reset' else dict(previous['state'])
            require(row['choice']==choice and freeze(kernel['initial'])==freeze(initial),'initial choice')
            require(freeze(kernel['program'])==freeze(pr) and kernel['program_sha256']==program.digest and freeze(kernel['drives'])==freeze(drives),'native inputs')
            maximum=max(maximum,scalar(kernel,base['kernel'],p['scalar_tolerance']))
            previous=dict(cell=cell['key'],binding=binding,state=dict(kernel['state']),status=kernel['convergence']['status']) if arm!='reset' and kernel['convergence']['status'] in ('stable_decision','stable_ambiguous') else None
            require(freeze(row['cache_after'])==freeze(previous) and row['native_settle_calls']==1,'cache transition')
            total_calls+=1;total_ticks+=kernel['cost']['kernel_ticks']
        require(e['native_settle_calls']==6 and e['training_calls']==e['world_measure_calls']==e['store_load_calls']==0,'work ledger')
        require((arm=='compiled_guarded' and 0<e['compiler_iterations']<=63) or (arm!='compiled_guarded' and e['compiler_iterations']==0),'compiler ledger')
        for axis in ['cpu','wall']:
            a,b=e['cold_'+axis+'_seconds'],e['compiler_'+axis+'_seconds']
            require(type(a) is float and type(b) is float and math.isfinite(a) and math.isfinite(b) and 0<=b<=a,'timing inclusion')
            resolution=e['clock_resolution_seconds'][axis];require(type(resolution) is float and math.isfinite(resolution) and resolution>0,'clock resolution')
    for block in range(4):
        for stream in streams:
            rs={a:data[f"b{block}_{stream['key']}_{a}"] for a in p['policy_names']}
            for i in range(6):
                l,c,r=(rs[a]['rows'][i] for a in ['legacy_guarded','compiled_guarded','reset'])
                for field in ['choice','cache_before','cache_after','kernel']:require(freeze(l[field])==freeze(c[field]),'legacy compiled exact '+field)
                equivalent+=1;bk,ck=r['kernel'],c['kernel'];difference=max(abs(bk['state'][k]-ck['state'][k]) for k in bk['state'])
                require(bk['convergence']['status']==ck['convergence']['status'] and bk['adopted']==ck['adopted'] and difference<=p['terminal_state_tolerance'],'observed reset quality')
                quality+=1;nontrivial+=freeze(bk)!=freeze(ck)
        amounts={a:{axis:sum(data[f"b{block}_{s['key']}_{a}"]['cold_'+axis+'_seconds'] for s in streams) for axis in ['cpu','wall']} for a in p['policy_names']}
        resolution=max(p['minimum_resolved_difference_seconds'],*(e['clock_resolution_seconds'][axis] for e in data.values() for axis in ['cpu','wall']))
        wins={a:all(amounts[a][axis]-amounts['compiled_guarded'][axis]>resolution for axis in ['cpu','wall']) for a in ['reset','legacy_guarded']}
        totals.append(dict(block=block,cold_seconds=amounts,compiled_beats=wins))
    require(total_calls==p['maximum_native_settle_calls']==288 and total_ticks<=p['maximum_logical_ticks']==46080,'global native caps')
    return dict(status='EXACT_PREDICATE_COLD_LIFECYCLE_AUDITED',native_settle_calls=total_calls,kernel_ticks=total_ticks,
        exact_legacy_compiled_pairs=equivalent,observed_reset_quality_pairs=quality,nontrivial_kernel_pairs=nontrivial,
        scalar_max_absolute_error=maximum,blocks=totals,cold_runtime_improvement_observed=all(all(b['compiled_beats'].values()) for b in totals),
        case_process_cost_review_pending=True,training_calls=0,world_measure_calls=0,store_load_calls=0,
        statistical_generalization=False,future_reset_quality_proven=False,production_adoption=False)

def mutations(data,p):
    result={};first=p['cases'][0]['key'];legacy=next(j['key'] for j in p['cases'] if j['policy']=='compiled_guarded')
    for name in ['gate','initial','trace','cost','cache','timing','missing_job']:
        bad=deepcopy(data)
        if name=='gate':bad[legacy]['rows'][1]['gate']['eligible']=not bad[legacy]['rows'][1]['gate']['eligible']
        elif name=='initial':bad[legacy]['rows'][0]['kernel']['initial']['goal']+=.01
        elif name=='trace':bad[legacy]['rows'][0]['kernel']['ticks'][0]['state']['goal']+=.01
        elif name=='cost':bad[legacy]['rows'][0]['kernel']['cost']['kernel_ticks']-=1
        elif name=='cache':bad[legacy]['rows'][1]['cache_before']['cell']='future'
        elif name=='timing':bad[legacy]['compiler_cpu_seconds']=bad[legacy]['cold_cpu_seconds']+1.
        else:del bad[first]
        try:audit_all(bad,p)
        except ValueError as exc:result[name]=str(exc)
        else:raise ValueError('mutation accepted '+name)
    return result
