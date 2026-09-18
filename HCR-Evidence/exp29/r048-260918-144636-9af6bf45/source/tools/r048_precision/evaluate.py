"""Read-only EXP29 audit/reaggregation; no imports from any producer or native model."""
from . import io,spec


def stable_audit(record,source,world):
    from tools.r047_state_ablation.audit import audit_record,world_answer
    result=audit_record(record,source,world)
    # Preserve the independently replayed numerical tolerance contract across platforms.
    result.pop('max_scalar_error',None)
    truth=world_answer(record['observation'],world)
    result.update(oracle_value=truth,scalar_tolerance=2e-12,within_tolerance=True,
        raw_correct=None if record['raw_value'] is None else record['raw_value'] is truth,
        accepted_correct=bool(record['accepted'] and record['raw_value'] is truth),
        source_positive_adopted=bool(record['accepted'] and record['raw_value'] is True))
    return result


def read_audit(plan,root):
    cases={c['id']:c for c in plan['cases']};sources={};records={};sa={};ba={};events=[]
    def check_record(kind,key,query,ob,arm,source,world):
        raw=io.load(root/'raw'/(kind+'_'+key+'.json'))
        io.require(set(raw)=={'schema','query','record'} and raw['schema']=='hcr-exp29-raw-v1' and raw['query']==query,'raw query registry')
        r=raw['record']
        io.require(r['observation']==ob and r['config']==plan['kernel_config'] and r['arm']==arm,'observation/config/treatment drift')
        report=stable_audit(r,source,world)
        events.append(dict(event='query_started',query=query))
        events.extend(dict(event='query_event',query=query,record=e) for e in r['events'])
        events.append(dict(event='query_completed',query=query,raw_sha256=io.digest(raw)))
        return r,report
    for case in plan['cases']:
        key=case['source'];s=plan['sources'][key]
        ob=s['observation'];world={e['id']:plan['worlds'][key][e['id']] for e in ob['edges']}
        sources[key],sa[key]=check_record('A',key,dict(kind='A',id=key),ob,'cold',None,world)
    for t in plan['trials']:
        records[t['id']],ba[t['id']]=check_record('B',t['id'],dict(kind='B',id=t['id'],trial=t),
            cases[t['case']]['observation'],t['arm'],sources[t['source']],plan['worlds'][t['case']])
    with (root/'attempts.jsonl').open('rb') as stream:
        for i,e in enumerate(events):
            line=stream.readline();io.require(bool(line) and io.loads(line)==e,'event stream mismatch at '+str(i))
        io.require(stream.read()==b'','unregistered trial/retry/trailing stream bytes')
    return sources,records,sa,ba,len(events)


def checkpoint_comparison(a,b):
    out=[]
    for tick in spec.CHECKPOINTS:
        available=min(len(a['ticks']),len(b['ticks']))>=tick
        row=dict(tick=tick,available=available,missing_reason=None if available else 'one_or_both_native_runs_already_stopped',
                 group_Linf=None,goal_actual_minus_fixed=None,residual_actual_minus_fixed=None)
        if available:
            x,y=a['ticks'][tick-1],b['ticks'][tick-1]
            io.require(set(x['state'])==set(y['state']),'checkpoint role mismatch')
            row.update(group_Linf=max(abs(x['state'][k]-y['state'][k]) for k in x['state']),
                goal_actual_minus_fixed=x['state']['goal']-y['state']['goal'],
                residual_actual_minus_fixed=x['residual']-y['residual'])
        out.append(row)
    return out


def eligibility(a,b,source,sa,aa,bb):
    reasons=[]
    if not(sa['accepted_correct'] and source['raw_value'] is True):reasons.append('A_not_correct_positive_adoption')
    if not(a['gate_valid'] and b['gate_valid']):reasons.append('initialization_not_applied')
    if a['censored'] or b['censored']:reasons.append('B_budget_termination')
    if not aa['accepted_correct']:reasons.append('actual_B_not_correct_adoption')
    if not bb['accepted_correct']:reasons.append('fixed_B_not_correct_adoption')
    return not reasons,reasons


def summarize(plan,sources,records,sa,ba):
    cases={c['id']:c for c in plan['cases']};cells={};lookups={};trials=[];source_rows=[];maps=[];sigs=[];gate_rows=[]
    for case in plan['cases']:
        key=case['source'];s=plan['sources'][key]
        r=sources[key];report=sa[key]
        source_rows.append(dict(source=key,strength=s['strength'],variant=s['variant'],
            raw_value=r['raw_value'],accepted=r['accepted'],classification=report['classification'],
            raw_correct=report['raw_correct'],accepted_correct=report['accepted_correct'],
            native_ticks=r['native_cost']['kernel_ticks'],censored=r['censored'],
            convergence_status=None if r['convergence'] is None else r['convergence']['status'],
            positive_reuse_available=report['source_positive_adopted'],D_DAG=report['D_DAG']))
    for t in plan['trials']:
        c=cases[t['case']];r=records[t['id']];report=ba[t['id']]
        cells[c['strength'],c['variant'],t['arm']]=r;lookups[c['strength'],c['variant'],t['arm']]=report
        ar=sources[t['source']]
        row=dict(trial=t['id'],case=t['case'],source=t['source'],strength=c['strength'],variant=c['variant'],arm=t['arm'],
            anchor=c['strength']==0.92,raw_value=r['raw_value'],accepted=r['accepted'],classification=report['classification'],
            raw_correct=report['raw_correct'],accepted_correct=report['accepted_correct'],censored=r['censored'],
            gate_valid=r['gate_valid'],gate_reason=r['gate_reason'],A_positive_reuse_available=sa[t['source']]['source_positive_adopted'],
            A_ticks=ar['native_cost']['kernel_ticks'],B_ticks=r['native_cost']['kernel_ticks'],
            A_plus_B_ticks=ar['native_cost']['kernel_ticks']+r['native_cost']['kernel_ticks'],
            D_DAG=report['D_DAG'],wall_seconds=r['wall_seconds'],energy_joules=None,peak_memory_bytes=None)
        row.update({'native.'+k:v for k,v in r['native_cost'].items() if k!='wall_seconds'})
        row.update({'bridge.'+k:v for k,v in r['bridge_cost'].items()});trials.append(row)
        maps.extend(dict(trial=t['id'],**m) for m in r['transfer_map'])
        gate_rows.extend(dict(trial=t['id'],check_index=i+1,**x) for i,x in enumerate(r['dependency_check_trace']))
        sigs.append(dict(trial=t['id'],initial_sha256=io.digest(r['initial_state']),
            effective_program_sha256=io.digest(dict(program=r['program'],drives=r['effective_drives'])),
            dynamics_sha256=io.digest(dict(ticks=r['ticks'],convergence=r['convergence'])),proof_sha256=io.digest(r['proof_graph'])))
    io.require(len(cells)==98,'incomplete/duplicate treatment matrix')
    pairs=[];checkpoints=[];hypotheses=[];vs_cold=[]
    for c in plan['cases']:
        level,variant=c['strength'],c['variant'];source=sources[c['source']];sar=sa[c['source']]
        cold=cells[level,variant,'cold'];cold_ok=lookups[level,variant,'cold']['accepted_correct']
        for arm in spec.ARMS[1:]:
            r=cells[level,variant,arm]
            vs_cold.append(dict(case=c['id'],arm=arm,delta_ticks=r['native_cost']['kernel_ticks']-cold['native_cost']['kernel_ticks'],
                evaluable=cold_ok and lookups[level,variant,arm]['accepted_correct'] and r['gate_valid'] and not r['censored'] and not cold['censored']))
            if not sar['source_positive_adopted']:
                gate_ok=not r['gate_valid'] and r['carry_packet'] is None and not r['transfer_map']
                hypotheses.append(dict(case=c['id'],arm=arm,hypothesis='H_gate',status='supported' if gate_ok else 'falsified'))
        for mask in ('edge','prefix','both'):
            a,b=(cells[level,variant,m+'_'+mask] for m in ('carry','fixed'))
            aa,bb=(lookups[level,variant,m+'_'+mask] for m in ('carry','fixed'))
            eligible,reasons=eligibility(a,b,source,sar,aa,bb)
            delta=a['native_cost']['kernel_ticks']-b['native_cost']['kernel_ticks']
            same_program=(a['program'],a['effective_drives'])==(b['program'],b['effective_drives'])
            io.require(same_program,'paired native program/drives differ')
            equal=(a['raw_value'],a['accepted'])==(b['raw_value'],b['accepted'])
            overlap=min(len(a['ticks']),len(b['ticks']))
            maxdiff=(max(abs(x['state'][k]-y['state'][k]) for x,y in zip(a['ticks'],b['ticks']) for k in x['state']) if overlap else None)
            pair=dict(case=c['id'],strength=level,variant=variant,mask=mask,anchor=level==0.92,
                actual_ticks=a['native_cost']['kernel_ticks'],fixed_ticks=b['native_cost']['kernel_ticks'],
                actual_minus_fixed_ticks=delta,eligible=eligible,eligibility_failures=reasons,
                outcome_equal=equal,actual_accepted_correct=aa['accepted_correct'],fixed_accepted_correct=bb['accepted_correct'],
                native_program_equal=same_program,trajectory_equal=a['ticks']==b['ticks'],overlap_ticks=overlap,
                overlap_group_Linf=maxdiff,actual_gate=a['gate_reason'],fixed_gate=b['gate_reason'])
            pairs.append(pair)
            checkpoints.extend(dict(case=c['id'],strength=level,variant=variant,mask=mask,**x) for x in checkpoint_comparison(a,b))
            hypotheses.append(dict(case=c['id'],mask=mask,hypothesis='H_precision_at_cell',
                status=('not_evaluable' if not eligible else 'supported' if delta<0 else 'falsified')))
            hypotheses.append(dict(case=c['id'],mask=mask,hypothesis='H_outcome_at_cell',
                status='not_evaluable' if a['censored'] or b['censored'] else 'supported' if equal else 'falsified'))
    ids=[]
    for level in spec.LEVELS:
        for arm in spec.ARMS:
            a,b=(cells[level,v,arm] for v in spec.VARIANTS)
            costs=[{k:v for k,v in r['native_cost'].items() if k!='wall_seconds'} for r in (a,b)]
            equal=costs[0]==costs[1] and a['ticks']==b['ticks'] and (a['raw_value'],a['accepted'])==(b['raw_value'],b['accepted'])
            ids.append(dict(strength=level,arm=arm,native_equal=equal,
                identity_dependency_checks=a['bridge_cost']['dependency_checks'],fresh_dependency_checks=b['bridge_cost']['dependency_checks']))
            hypotheses.append(dict(strength=level,arm=arm,hypothesis='H_ID_native',status='supported' if equal else 'falsified'))
    from collections import Counter
    return dict(schema='hcr-exp29-summary-v1',population=plan['population'],source_queries=14,followups=98,
        independent_random_replicates=0,unique_native_ticks=sum(r['native_cost']['kernel_ticks'] for r in list(sources.values())+list(records.values())),
        sources=source_rows,trials=trials,pairs=pairs,checkpoints=checkpoints,vs_cold=vs_cold,
        ID_controls=ids,hypotheses=hypotheses,transfer_maps=maps,dependency_scans=gate_rows,signatures=sigs,
        counts=dict(hypotheses=dict(Counter(x['status'] for x in hypotheses)),
                    B_classification=dict(Counter(x['classification'] for x in trials)),
                    eligible_pairs=sum(x['eligible'] for x in pairs),total_pairs=len(pairs)),
        scope=dict(inherited_producer_unmodified=True,inherited_auditor_unmodified=True,formal_HCC_learning=False,
                   precision_values_not_optimized=True,prior_falsifications_preserved=True,
                   native_and_bridge_proof_counts_aliases_not_additive=True,wall_time_efficiency_claimed=False))
