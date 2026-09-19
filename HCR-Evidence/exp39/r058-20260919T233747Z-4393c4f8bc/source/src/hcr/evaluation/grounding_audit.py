"""EXP-13 독립 진단 검산. production grounding/runtime을 호출하지 않는다.

기존 session auditor와 primitive reference는 재사용한다. sign 계약의 지지 여부와
score-compatible worlds는 평가기에서 별도 계산하며 원시 실행에 공급하지 않는다.
"""
from __future__ import annotations
from itertools import product
from math import isfinite
from .. import codec
from ..model import fingerprint
from .audit import require
from .reference import validate_proof, reachable
from .prior_audit import verify_task
from .grounding_spec import SUPPORT, READOUT_POLICIES


def evidence_class(score, assumed, threshold):
    if score is None: return 'missing'
    if score == 0: return 'neutral'
    if abs(score) <= threshold: return 'below_threshold'
    return 'directional_support' if (score > 0 and assumed) or (score < 0 and not assumed) else 'sign_conflict'


def _body(packet, schema):
    require(isinstance(packet,dict) and packet.get('schema')==schema,'diagnostic schema')
    data={k:v for k,v in packet.items() if k!='sha256'}
    require(packet.get('sha256')==fingerprint(data),'diagnostic hash')
    return data


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
    if d['value'] is not None:require(valid and d['proof']['under_assumptions_valid'],'invalid primitive proof')
    return dict(verified=True,logical_proof_valid=valid,primitive_depth=depth,proof_checks=checks,
                proof_error=error,new_inferences=0)


def verify_readout(raw, diagnostic, packet, policy):
    b=_body(packet,'hcr-grounded-readout-r032-v1');d=raw['decision'];v=d['value']
    if v is None:accept,reason=False,'original_abstention'
    elif policy=='diagnostic_only':accept,reason=True,'unmodified_diagnostic_control'
    elif policy=='dependency_gate':
        accept=diagnostic['evidence_support_sufficient'] is True
        reason='supported_under_sign_contract' if accept else 'dependency_support_abstention'
    elif policy=='blanket_unknown_gate':
        accept=not any(e['score'] is None or e['score']==0 for e in raw['observation']['edges'])
        reason='blanket_no_unknown' if accept else 'blanket_unknown_abstention'
    else:raise ValueError('unknown readout policy')
    require(fingerprint(b)==fingerprint(dict(schema='hcr-grounded-readout-r032-v1',policy=policy,source_decision_id=d['id'],
        source_decision_sha256=fingerprint(d),diagnostic_sha256=diagnostic['sha256'],original_value=v,
        value=v if accept else None,accepted=accept,reason=reason,intervention=policy!='diagnostic_only',
        original_decision_modified=False,truth_accessed=False,new_inferences=0,inference_cost_unchanged=True)),'readout mismatch or answer correction')


def verify_conflicts(named, packet):
    b=_body(packet,'hcr-grounding-conflict-r032-v1')
    values={k:v['original_value'] for k,v in named.items()}
    assigns={k:{r['edge_id']:r['assumed'] for r in v['assumptions']} for k,v in named.items()}
    edges=sorted(set().union(*(set(v) for v in assigns.values())))
    conflicting=[]
    for e in edges:
        vals={k:v[e] for k,v in assigns.items() if e in v}
        if True in vals.values() and False in vals.values():conflicting.append(dict(edge_id=e,assumptions=vals))
    resolved=[v for v in values.values() if v is not None]
    if len(set(resolved))>1:status='decision_conflict'
    elif len(resolved)<len(values):status='incomplete_or_abstained'
    elif all(d['evidence_support_sufficient'] is True for d in named.values()):status='agreement_under_contract'
    else:status='agreement_with_support_gap'
    require(fingerprint(b)==fingerprint(dict(schema='hcr-grounding-conflict-r032-v1',status=status,sources={k:v['sha256'] for k,v in named.items()},
        values=values,assumption_conflicts=conflicting,support_gap_edges=sorted({e for d in named.values() for e in d['support_gap_edges']}),
        unique_evidence_refs=sorted({r['evidence_ref'] for d in named.values() for r in d['assumptions']}),
        evidence_multiplicity_is_confidence=False,selects_winner=False,new_inferences=0)),'conflict recomputation')


def compatible_worlds(observation):
    """평가기 전용: unknown을 모두 완성해 sign 계약 아래 식별 가능성을 검사한다.

    directional score를 참값으로 선언하는 엔진이 아니다. 이 계약상의 분석은
    actual hidden world 평가와 별도이며 misleading_direction이 차이를 보여준다.
    """
    obs=codec.observation_from(observation)
    require(len(obs.edges)<=8,'bounded evaluator enumeration')
    unknown=[e for e in obs.edges if e.score is None or e.score==0]
    base={e.id:e.score>0 for e in obs.edges if e not in unknown}
    outputs=[];worlds=[]
    for assignment in product((False,True),repeat=len(unknown)):
        world=dict(base,**{e.id:v for e,v in zip(unknown,assignment)})
        value=reachable(obs,world);outputs.append(value);worlds.append((world,value))
    possible=sorted(set(outputs));critical=[]
    for e in unknown:
        for world,v in worlds:
            opposite=dict(world);opposite[e.id]=not opposite[e.id]
            if reachable(obs,opposite)!=v:critical.append(e.id);break
    return dict(evaluation_only=True,worlds_enumerated=len(outputs),possible_values=possible,
                identifiable_under_sign_contract=len(possible)==1,
                value_under_sign_contract=possible[0] if len(possible)==1 else None,
                influential_unknown_edges=critical,used_as_runtime_input=False)


def assess_views(raw,case,diagnostic,readouts):
    obs=codec.observation_from(raw['observation']);compat=compatible_worlds(raw['observation'])
    targets={k:reachable(obs,v) for k,v in case['worlds'].items()}
    return dict(compatible_worlds=compat,external_targets=targets,
        policies={p:dict(value=r['value'],external_correct={k:None if r['value'] is None else r['value']==v for k,v in targets.items()},
            unsupported_commitment=r['value'] is not None and diagnostic['evidence_support_sufficient'] is not True,
            unidentified_commitment=r['value'] is not None and not compat['identifiable_under_sign_contract'],
            withheld_identifiable_case=r['value'] is None and compat['identifiable_under_sign_contract']) for p,r in readouts.items()})


def verify_record(raw,record,case,n,arm,memory,config):
    task_audit,_=verify_task(raw,case,n,arm,memory,config)
    require(set(record)=={'schema','source_task_sha256','diagnostic','readouts','assessment','timing'}
        and record['schema']=='hcr-exp13-record-v1' and record['source_task_sha256']==fingerprint(raw),'EXP13 record binding')
    audit=verify_diagnostic(raw,record['diagnostic'])
    require(set(record['readouts'])==set(READOUT_POLICIES),'readout matrix')
    for p,r in record['readouts'].items():verify_readout(raw,record['diagnostic'],r,p)
    require(record['assessment']==assess_views(raw,case,record['diagnostic'],record['readouts']),'external assessment / identifiability')
    t=record['timing'];require(set(t)=={'diagnostic_seconds','readout_seconds'} and set(t['readout_seconds'])==set(READOUT_POLICIES),'timing keys')
    require(all(type(v) in (int,float) and isfinite(v) and v>=0 for v in [t['diagnostic_seconds'],*t['readout_seconds'].values()]),'diagnostic timing')
    return dict(verified=True,task=task_audit,proof=audit,new_inferences=0)
