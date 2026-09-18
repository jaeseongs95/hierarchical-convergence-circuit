"""Post-run independent audit and descriptive paired contrasts. No model execution."""
from pathlib import Path
from tools.r048_precision import io
from . import spec,audit,diagnostics,regression


def read_audit(plan,root):
    cases={c['id']:c for c in plan['cases']};records={};audits={};items=[]
    for t in plan['trials']:
        raw=io.load(root/'raw'/(t['id']+'.json'))
        io.require(set(raw)=={'trial','record'} and raw['trial']==t,'trial provenance/order')
        r=raw['record'];io.require(r['observation']==cases[t['case']]['observation']
            and r['config']==plan['kernel_config'] and r['arm']==t['arm'],'input or intervention differs from plan')
        a=audit.audit_record(r,plan['worlds'][t['case']]);records[t['id']]=r;audits[t['id']]=a;items.append(raw)
    count=0
    with (root/'attempts.jsonl').open('rb') as f:
        def take(expected):
            nonlocal count
            b=f.readline();io.require(b and io.loads(b)==expected,'event stream mismatch at row '+str(count));count+=1
        for raw in items:
            t=raw['trial'];take(dict(event='query_started',trial=t))
            for ev in raw['record']['events']:take(dict(event='query_event',trial_id=t['id'],record=ev))
            take(dict(event='query_completed',trial_id=t['id'],raw_sha256=io.digest(raw)))
        io.require(f.read()==b'','extra trial/retry/tail not in frozen plan')
    return records,audits,count


def summarize(plan,records,audits,prior):
    cases={c['id']:c for c in plan['cases']};cells={};rows=[];flags=[];signals=[];signatures=[];hyp=[];regress=[]
    reference={(x['strength'],x['pattern'],x['arm']):x for x in prior['entries']}
    reference_traces=regression.references(prior)
    for t in plan['trials']:
        c=cases[t['case']];r=records[t['id']];a=audits[t['id']];b=diagnostics.boundary(r,a)
        cells[c['strength'],c['pattern'],c['variant'],t['arm']]=(t,r,a,b)
        cov=dict(trial=t['id'],case=t['case'],strength=c['strength'],pattern=c['pattern'],variant=c['variant'],arm=t['arm'],evidence_role=t['evidence_role'])
        rows.append(dict(cov,raw_value=r['raw_value'],accepted=r['accepted'],classification=a['classification'],
            raw_correct=a['raw_correct'],accepted_correct=a['accepted_correct'],censored=r['censored'],
            termination=r['termination'],D_DAG=a['D_DAG'],native_ticks=a['scalar_ticks'],
            first_margin_readout=r['first_margin_readout'],final_state=r['final_state'],wall_seconds=r['wall_seconds'],
            energy_joules=None,peak_memory_bytes=None,native_adaptive_expansions=None,
            **{'native.'+k:v for k,v in r['native_cost'].items() if k!='wall_seconds'},
            **{'adapter.'+k:v for k,v in r['adapter_cost'].items()}))
        flags.append(dict(cov,**b))
        for x in diagnostics.signal_rows(r):signals.append(dict(trial=t['id'],**x))
        dyn=io.digest(dict(ticks=r['ticks'],convergence=r['convergence']))
        signatures.append(dict(trial=t['id'],stored_program_sha256=io.digest(r['program']),
            effective_program_sha256=r['effective_program_sha256'],initial_sha256=io.digest(r['initial_state']),
            dynamics_sha256=dyn,proof_sha256=io.digest(r['proof'])))
        def predict(name,ok,available=True):
            hyp.append(dict(cov,hypothesis=name,status='not_evaluable' if not available else 'supported' if ok else 'falsified'))
        if not r['intervention']['top_down']:
            align=not b['terminal_sign_conflicts'] and r['final_state'] is not None
            if align:align=all((2*r['final_state'][f'e:{i}']-1)*e['score']>0 for i,e in enumerate(r['observation']['edges']))
            predict('H_off_edge_alignment',align,not r['censored'])
        if c['pattern']=='mixed_negative' and t['arm'].endswith('high'):
            predict('H_negative_high_raw',r['raw_value'] is False,not r['censored'] and r['raw_value'] is not None)
        predict('H_adoption_safety',not r['accepted'] or a['accepted_correct'],not r['censored'])
        if t['evidence_role']=='prior_exploration_replication':
            ref=reference[c['strength'],c['pattern'],t['arm']]
            comparison=regression.compare(r,reference_traces[c['strength'],c['pattern'],t['arm']],ref['dynamics_sha256'])
            regress.append(dict(cov,**comparison))
    pairs=[];interactions=[];ids=[]
    def compare(key,arm,control,factor):
        t,r,a,b=cells[*key,arm];u,q,z,d=cells[*key,control]
        uncensored=not r['censored'] and not q['censored']
        raw_known=r['raw_value'] is not None and q['raw_value'] is not None
        overlap=min(len(r['ticks']),len(q['ticks']))
        dif=max((abs(x['state'][g]-y['state'][g]) for x,y in zip(r['ticks'],q['ticks']) for g in x['state']),default=None)
        pairs.append(dict(strength=key[0],pattern=key[1],variant=key[2],factor=factor,treatment=arm,control=control,
            treatment_trial=t['id'],control_trial=u['id'],uncensored=uncensored,
            delta_ticks=a['scalar_ticks']-z['scalar_ticks'] if uncensored else None,
            raw_delta=int(r['raw_value'])-int(q['raw_value']) if raw_known and uncensored else None,
            treatment_raw=r['raw_value'],control_raw=q['raw_value'],treatment_accepted=r['accepted'],control_accepted=q['accepted'],
            both_correct_adoptions=a['accepted_correct'] and z['accepted_correct'],
            stored_graph_equal=r['program']==q['program'],effective_function_equal=r['effective_program_sha256']==q['effective_program_sha256'],
            trajectory_equal=r['ticks']==q['ticks'],overlap_ticks=overlap,overlap_Linf=dif,
            general_efficiency_claimed=False))
    for level in spec.LEVELS:
        for pattern in spec.PATTERNS:
            for v in spec.VARIANTS:
                key=(level,pattern,v)
                for init in ('neutral','high'):compare(key,'off_'+init,'on_'+init,'top_down')
                for td in ('on','off'):compare(key,td+'_high',td+'_neutral','initialization')
                rr={arm:cells[*key,arm][1] for arm in spec.ARMS};available=all(not r['censored'] for r in rr.values())
                def contrast(fn):return fn(rr['on_high'])-fn(rr['on_neutral'])-fn(rr['off_high'])+fn(rr['off_neutral'])
                interactions.append(dict(strength=level,pattern=pattern,variant=v,uncensored=available,
                    ticks_interaction=contrast(lambda r:r['native_cost']['kernel_ticks']) if available else None,
                    raw_interaction=contrast(lambda r:int(r['raw_value'])) if available and all(r['raw_value'] is not None for r in rr.values()) else None,
                    interpretation='signed_descriptive_contrast_NOT_axis_independence_or_attractor_proof'))
            for arm in spec.ARMS:
                t,r,a,b=cells[level,pattern,'identity',arm];u,q,z,d=cells[level,pattern,'fresh_ids',arm]
                eq=r['ticks']==q['ticks'] and r['native_cost']==q['native_cost']
                ids.append(dict(strength=level,pattern=pattern,arm=arm,trajectory_equal=r['ticks']==q['ticks'],native_cost_equal=r['native_cost']==q['native_cost']))
                hyp.append(dict(strength=level,pattern=pattern,variant='identity_vs_fresh',arm=arm,hypothesis='H_ID_native',
                    status='not_evaluable' if r['censored'] or q['censored'] else 'supported' if eq else 'falsified'))
    return dict(schema='hcr-exp30-summary-v1',population=plan['population'],queries=len(rows),
        unique_native_ticks=sum(a['scalar_ticks'] for a in audits.values()),
        regression_cells=sum(t['evidence_role']=='prior_exploration_replication' for t in plan['trials']),
        new_condition_cells=sum(t['evidence_role']=='new_condition_in_frozen_matrix' for t in plan['trials']),
        independent_random_replicates=0,trials=rows,boundaries=flags,signals=signals,pairs=pairs,interactions=interactions,
        ID_controls=ids,hypotheses=hyp,prior_regressions=regress,signatures=signatures,
        claims=dict(native_equations_unchanged=True,top_down_changes_effective_function=True,high_is_experimental_initialization_not_carry=True,
            readout_rejection_is_not_correction=True,learning_tested=False,preallocation_tested=False,reexpansion_tested=False,
            full_HCC_tested=False,energy_efficiency_measured=False,diagnostics_run_after_native_execution=True))
