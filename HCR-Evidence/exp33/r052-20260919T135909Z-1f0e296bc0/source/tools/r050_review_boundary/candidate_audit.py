"""R050 candidate audit, including explicitly reported proof construction failure.

Derived from the pinned core grounding/review auditors. All provenance, replay,
diagnostic and readout checks are retained. Only the requirement that every
non-abstaining decision possess a valid proof changes: independently invalid,
empty reconstructions must be reported invalid and rejected by the gate.
The core auditors and producer remain unchanged.
"""
from hcr import codec
from hcr.model import fingerprint
from hcr.evaluation.audit import require
from hcr.evaluation.reference import validate_proof
from hcr.evaluation.grounding_audit import _body, evidence_class, verify_readout
from hcr.evaluation.grounding_spec import SUPPORT
from hcr.evaluation.review_audit import packet_states, finite


def verify_diagnostic(raw, packet, support=SUPPORT):
    b=_body(packet,'hcr-grounding-diagnostic-r032-v1')
    d=raw['decision'];obs=raw['observation'];events=raw['packet']['document']['events']
    require(set(b)=={'schema','source','contract','original_value','assumptions','proof_validity_reported',
        'proof_independently_revalidated','graph_complete','negative_coverage_required','evidence_support_sufficient',
        'support_gap_edges','unknown_edges','unknown_outside_selected_proof','explored_path_checks','suggestion','diagnostic_cost','boundaries'},'diagnostic fields')
    require(b['contract']==support,'support contract modified')
    start=[e for e in events if e['event']=='r02_attempt_started' and e['payload']['decision_id']==d['id']]
    end=[e for e in events if e['event']=='r02_decision' and e['payload']['id']==d['id']]
    require(len(start)==len(end)==1 and end[0]['payload']==d,'single decision trace')
    netevents=[e for e in events if e['event']=='r02_network' and e['payload']['kind']=='decision' and e['payload']['decision_id']==d['id'] and e['seq']<end[0]['seq']]
    ne=netevents[-1] if netevents else None;net=ne['payload'] if ne else None
    require(b['source']==dict(observation_digest=d['observation_digest'],observation_revision=obs['revision'],
        memory_digest=start[0]['payload']['memory_hash'],memory_version=start[0]['payload']['memory_version'],
        decision_id=d['id'],decision_sha256=fingerprint(d),program_digest=d['program_digest'],
        decision_event_seq=end[0]['seq'],decision_event_sha256=end[0]['sha256'],network_event_sha256=ne['sha256'] if ne else None,
        event_head=events[-1]['sha256'],event_count=len(events)),'diagnostic provenance')
    require(b['original_value'] is d['value'] and b['proof_validity_reported'] is d['proof']['under_assumptions_valid']
        and b['proof_independently_revalidated'] is False and b['graph_complete'] is d['graph_complete']
        and b['negative_coverage_required'] is (d['value'] is False),'original flags')
    byid={e['id']:(i,e) for i,e in enumerate(obs['edges'])};state=dict(d['state']);rows=[]
    for eid,assumed in d['proof']['assumed_edges']:
        slot,e=byid[eid];require(type(assumed)is bool,'boolean assumption')
        terms=[dict(group=f'p:{pi}:{j}',learned_drive=net['drives'].get(f'p:{pi}:{j}',0.0))
               for pi,path in enumerate(net['program']['paths']) for j,s in enumerate(path) if s==slot]
        uses=[dict(circuit_id=u['circuit_id'],circuit_version=u['circuit_version'],routing_prior=u['prior'],edge_order=u['binding']['edge_order'])
              for route in net['metadata']['routes'] for u in route['uses'] if slot in u['binding']['edge_order']]
        rows.append(dict(edge_id=eid,slot=slot,assumed=assumed,score=e['score'],
            observation_kind='missing' if e['score'] is None else 'neutral' if e['score']==0 else 'directional',
            support=evidence_class(e['score'],assumed,support['min_abs_score']),evidence_ref=d['observation_digest']+':'+eid,
            observed_drive=net['drives'].get('e:'+str(slot),0.0),final_activation=state['e:'+str(slot)],
            relation_drives=terms,goal_learned_drive=net['drives'].get('goal',0.0),routing_uses=uses,
            drive_presence_is_not_causal_attribution=True))
    require(b['assumptions']==rows,'assumption provenance / drive / score report')
    gaps=[r['edge_id'] for r in rows if r['support']!='directional_support']
    unknown=[e['id'] for e in obs['edges'] if e['score'] is None or e['score']==0]
    used={r['edge_id'] for r in rows}
    expected_sufficient=None if d['value'] is None else bool(d['proof']['under_assumptions_valid'] and rows and not gaps and (d['value'] is not False or d['graph_complete']))
    require(b['evidence_support_sufficient'] is expected_sufficient and b['support_gap_edges']==gaps
            and b['unknown_edges']==unknown and b['unknown_outside_selected_proof']==[e for e in unknown if e not in used],'support sufficiency')
    pc=[]
    for path in d['expanded_paths']:
        supported=all(obs['edges'][i]['score'] is not None and obs['edges'][i]['score']>support['min_abs_score'] for i in path)
        cuts=[obs['edges'][i]['id'] for i in path if obs['edges'][i]['score'] is not None and obs['edges'][i]['score'] < -support['min_abs_score']]
        pc.append(dict(slots=path,directionally_open=supported,observed_cut_edges=cuts))
    require(b['explored_path_checks']==pc,'new/unverified path in diagnostic')
    measure=[r['edge_id'] for r in rows if r['support'] in ('missing','neutral','below_threshold')]
    signs=[r['edge_id'] for r in rows if r['support']=='sign_conflict']
    if d['value'] is None:
        action='continue_expansion' if not d['graph_complete'] else 'request_observation_or_abstain'
        measure=sorted({obs['edges'][i]['id'] for p in d['expanded_paths'] for i in p if obs['edges'][i]['score'] is None or obs['edges'][i]['score']==0})
    elif not d['proof']['under_assumptions_valid'] or (d['value'] is False and not d['graph_complete']):action='inspect_invalid_or_incomplete_proof'
    elif measure: action='request_observation'
    elif signs: action='review_prior_or_alternative_method'
    else: action='retain_under_declared_contract'
    require(b['suggestion']==dict(action=action,edge_ids=measure,sign_conflict_edges=signs,executed=False),'suggestion improperly executed or derived')
    require(b['diagnostic_cost']==dict(assumptions_checked=len(rows),source_event_count=len(events),
        explored_path_edge_memberships=sum(map(len,d['expanded_paths'])),kernel_ticks=0,new_task_inferences=0,counts_are_inventory_not_full_cpu_operations=True),'diagnostic counters')
    require(b['boundaries']==dict(decision_modified=False,memory_updated=False,truth_accessed=False,
        new_paths_generated=False,support_is_external_correctness=False,learned_prior_counted_as_observation=False),'diagnostic boundaries')
    valid,depth,checks,error=validate_proof(codec.adaptive_decision_from(d).proof,codec.observation_from(obs),d['value'])
    if d['value'] is not None:
        require(valid is d['proof']['under_assumptions_valid'], 'primitive proof validity self-report')
        if not valid:
            require(not d['proof']['nodes'] and d['proof']['final'] is None,
                    'failed proof must be an empty reconstruction')
            require(b['evidence_support_sufficient'] is False,
                    'failed proof cannot claim grounding support')
    return dict(verified=True,logical_proof_valid=valid,primitive_depth=depth,proof_checks=checks,
                proof_error=error,new_inferences=0)


def verify_candidate(candidate, segment, states):
    ref=candidate['reference'];g=ref['generation'];doc=segment['document'];finished=candidate['packet']
    require(type(g)is int and g in states and states[g]['pending']['ready'], 'candidate from wrong boundary')
    j=doc['transitions'][:g+1];events=doc['events'][:j[-1]['event_end']]
    snap=dict(session_id=doc['session_id'],source_hashes=doc['source_hashes'],engine=states[g],events=events,transitions=j)
    require(ref['ready_sha256']==fingerprint(snap) and ref['finished_sha256']==finished['sha256']
            and candidate['candidate_id']=='review-candidate-'+fingerprint(ref),'candidate global identity')
    fd=finished['document']
    require(fd['transitions'][:-1]==j and fd['events'][:-1]==events and fd['transitions'][-1]['operation']=='finish',
            'candidate is not an unmodified finish branch')
    require(fd['events'][-1]['event']=='r02_decision' and fd['events'][-1]['payload']==candidate['decision'],'candidate decision source')
    _,audit=packet_states(finished)
    raw=dict(observation=states[g]['pending']['observation'],decision=candidate['decision'],packet=finished)
    verify_diagnostic(raw,candidate['diagnostic']);verify_readout(raw,candidate['diagnostic'],candidate['readout'],'dependency_gate')
    if candidate['decision']['proof']['under_assumptions_valid'] is False:
        require(candidate['readout']['accepted'] is False and candidate['readout']['value'] is None,
                'failed proof cannot be adopted')
    require(finite(candidate['capture_seconds']) and finite(candidate['proof_finish_seconds'])
            and candidate['proof_finish_seconds']==candidate['decision']['cost']['wall_seconds']-states[g]['pending']['active_seconds'],
            'proof readout time accounting')
    return audit
