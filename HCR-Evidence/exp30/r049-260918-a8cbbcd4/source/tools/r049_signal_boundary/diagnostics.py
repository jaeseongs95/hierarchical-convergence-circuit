"""Read-only algebraic ledgers from audited native ticks. Does not call/update the kernel."""
from tools.r048_precision import io


def signal_rows(r):
    if r['program'] is None:return []
    p=r['program'];c=r['config'];previous=r['initial_state'];out=[];active=set(r['active_link_indices'])
    for row in r['ticks']:
        for g in p['groups']:
            key=g['id'];support=0.;top=0.;masked=0.;ns=nt=0
            for i,l in enumerate(p['links']):
                if l['target']!=key:continue
                term=l['weight']*(2*previous[l['source']]-1)
                if i not in active:masked+=term
                elif l['kind']=='support':support+=term;ns+=1
                else:top+=term;nt+=1
            bias=g['bias'];external=r['raw_drives'].get(key,0.);field=bias+external+support+top
            self_term=(c['self_excitation']+c['inhibition'])*(2*previous[key]-1)
            logit=(2*field+self_term)/c['temperature'];after=row['state'][key]
            # Implied update target comes from native before/after. Independent tanh replay
            # validates it in audit.py, avoiding platform-specific exp/tanh bytes in the ledger.
            implied=(after-(1-c['damping'])*previous[key])/c['damping']
            out.append(dict(tick=row['tick'],group=key,bias=bias,external_drive=external,
                support_sum=support,top_down_sum=top,masked_top_down_term=masked,
                masked_term_is_executed=False,self_competition_logit=self_term,
                network_field=field,logit=logit,target_implied_by_native_update=implied,
                damping=c['damping'],before=previous[key],after=after,delta=after-previous[key],
                support_transmissions=ns,top_down_transmissions=nt,
                diagnostic_origin='read_only_postexecution',independent_target_validated=True))
        previous=row['state']
    return out


def boundary(r,a):
    if r['program'] is None:
        return dict(raw_value_incorrect=None,edge_activation_observation_sign_conflict=None,
            proof_construction_failed=None,proof_assumption_support_conflict=None,adoption_rejected=True,
            budget_terminated=True,measurement_failed=False,first_sign_conflict_tick={},first_negative_edge_tick={},
            initial_sign_conflicts=[],terminal_sign_conflicts=[],executed_goal_direction_switches=None)
    ob=r['observation'];seq=[(0,r['initial_state'])]+[(x['tick'],x['state']) for x in r['ticks']]
    first_conf={};first_negative={};initial=[];terminal=[]
    for i,e in enumerate(ob['edges']):
        key=f'e:{i}';s=e['score']
        conflicts=[t for t,v in seq if s is not None and (2*v[key]-1)*s<0]
        first_conf[e['id']]=conflicts[0] if conflicts else None
        neg=[t for t,v in seq[1:] if v[key]<.5];first_negative[e['id']]=neg[0] if neg else None
        if 0 in conflicts:initial.append(e['id'])
        if s is not None and (2*r['final_state'][key]-1)*s<0:terminal.append(e['id'])
    pr=r['proof'];byid={e['id']:e for e in ob['edges']}
    unsupported=[eid for eid,v in pr['assumed_edges'] if byid[eid]['score'] is None or byid[eid]['score']==0 or (byid[eid]['score']>0) is not v]
    directions=[x['state']['goal']>=.5 for x in r['ticks']]
    return dict(raw_value_incorrect=None if a['raw_correct'] is None else not a['raw_correct'],
        edge_activation_observation_sign_conflict=bool(terminal),
        proof_construction_failed=r['raw_value'] is not None and pr['final'] is None,
        proof_assumption_support_conflict=bool(unsupported),adoption_rejected=not r['accepted'],
        budget_terminated=r['censored'],measurement_failed=False,first_sign_conflict_tick=first_conf,
        first_negative_edge_tick=first_negative,initial_sign_conflicts=initial,terminal_sign_conflicts=terminal,
        unsupported_assumption_ids=unsupported,
        executed_goal_direction_switches=sum(x!=y for x,y in zip(directions,directions[1:])))
