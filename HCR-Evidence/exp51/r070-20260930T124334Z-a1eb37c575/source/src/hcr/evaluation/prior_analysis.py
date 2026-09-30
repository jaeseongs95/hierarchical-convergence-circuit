"""EXP-12 원시 이벤트의 집계. 생성된 후보와 평가기 topology universe를 구분한다."""
from __future__ import annotations
from collections import Counter
from ..model import fingerprint
from .adaptive_audit_support import circuit_id
from .audit import require


def _key(cid, slots):
    return cid + ':' + ','.join(map(str, slots))


def structural_universe(observation, prefix, memory, max_length):
    """평가기 전용: 이번 실제 frontier에서 가능한 단순 motif binding을 독립 열거.

    모델에 돌려주지 않는다. inactive/길이 예산 탈락도 원인을 붙여 남긴다.
    """
    out = []
    for c in memory['circuits']:
        length = len(c['pattern']['relations'])
        def walk(vertex, visited, slots):
            if len(slots) == length:
                out.append(dict(key=_key(circuit_id(c), slots), circuit_id=circuit_id(c), slots=slots,
                                active=c['active'], length_allowed=len(prefix['path']) + length <= max_length))
                require(len(out) <= 4096, 'diagnostic universe bound')
                return
            if vertex == observation['goal']:
                return
            for i, edge in enumerate(observation['edges']):
                if edge['source'] == vertex and edge['target'] not in visited:
                    walk(edge['target'], visited + [edge['target']], slots + [i])
        walk(prefix['visited'][-1], prefix['visited'], [])
    return out


def candidate_funnel(events, obs, memory, config, enabled):
    funnels = []
    start = 0
    # Every actual frontier quantum is included, including one that stops before a proposal.
    for end, event in enumerate(events):
        if event['event'] not in ('r02_expansion', 'r02_dead_end', 'r02_expansion_exhausted'):
            continue
        segment = events[start:end+1]; start = end+1
        scans = [e for e in segment if e['event'] == 'r02_binding_scan']
        proposals = [e for e in segment if e['event'] == 'r02_proposals']
        prefix = (proposals[-1]['payload']['prefix'] if proposals else
                  scans[-1]['payload']['prefix'] if scans else event['payload'].get('prefix'))
        if prefix is None:
            funnels.append(dict(event_seq=event['seq'], outcome='preproposal_budget_boundary', universe_not_enumerated=True))
            continue
        scan = scans[-1]['payload'] if scans else None
        pools = [e['payload'] for e in segment if e['event'] == 'r02_pool_result']
        activations = { _key(a['circuit_id'], a['binding']['edge_order']): a
                       for a in (pools[-1]['activations'] if pools else []) }
        matched = {_key(a['circuit_id'], a['binding']['edge_order']) for a in (scan['matched'] if scan else [])}
        pcs = proposals[-1]['payload']['candidates'] if proposals else []
        proposed = {_key(c['circuit_id'], c['edges']) for c in pcs if c['source'] == 'circuit'}
        executed = event['payload'].get('candidate') if event['event'] == 'r02_expansion' else None
        executed_key = _key(executed['circuit_id'], executed['edges']) if executed and executed['source'] == 'circuit' else None
        records = []
        for u in structural_universe(obs, prefix, memory, config['kernel']['max_path_length']):
            k = u['key']; a = activations.get(k); reasons = []
            if not enabled: reasons.append('circuit_policy_disabled')
            elif not u['active']: reasons.append('inactive_memory')
            elif not u['length_allowed']: reasons.append('primitive_length_budget')
            elif k not in matched:
                reasons.append('scan_incomplete_' + scan['fallback_reason'] if scan and not scan['complete'] else 'not_matched')
            elif a is None:
                reasons.append('pool_not_instantiated_or_partial_scan')
            elif not a['eligible']:
                if a['activation'] < config['activation_threshold']: reasons.append('activation_below_threshold')
                if a['mismatch'] > config['mismatch_threshold']: reasons.append('mismatch_above_threshold')
                if not reasons: reasons.append('pool_not_stably_settled')
            elif k != executed_key:
                reasons.append('expansion_budget_not_executed' if event['event']=='r02_expansion_exhausted'
                               and pcs and pcs[0]['source']=='circuit' and _key(pcs[0]['circuit_id'],pcs[0]['edges'])==k
                               else 'eligible_not_selected')
            else: reasons.append('executed')
            records.append(dict(u, matched=k in matched, pool_instantiated=a is not None,
                                eligible=a['eligible'] if a else None, proposed=k in proposed,
                                executed=k == executed_key, reasons=reasons,
                                routing_prior=a['prior'] if a else None,
                                activation=a['activation'] if a else None,
                                mismatch=a['mismatch'] if a else None))
        funnels.append(dict(event_seq=event['seq'], prefix=prefix, outcome=event['event'], candidates=records,
            scan_complete=scan['complete'] if scan else None, scan_fallback=scan['fallback_reason'] if scan else None,
            primitive_candidates=[c['edges'] for c in pcs if c['source'] == 'primitive'],
            executed_candidate=executed, evaluation_only_universe=True))
    return funnels


def record_metrics(raw):
    packet = raw['packet']; doc = packet['document']; events = doc['events']
    d = raw['decision']; obs = raw['observation']; cfg = doc['engine']['config']
    costs = {'pool_ticks':0,'decision_ticks':0,'pool_signals':0,'decision_signals':0}
    networks = {}; drives = []; pools = []; expansions = []; first_route_events = []
    first_done = False
    for e in events:
        name, p = e['event'], e['payload']
        if name == 'r02_network':
            networks[p['network_id']] = p
            if p['kind'] == 'pool': pools.extend(p['metadata']['candidates'])
            else:
                drives.append(dict(event_seq=e['seq'], network_id=p['network_id'], program_digest=p['program_digest'],
                    routes=p['metadata']['routes'], observation_drive={k:v for k,v in p['drives'].items() if k.startswith('e:')},
                    judgment_drive={k:v for k,v in p['drives'].items() if not k.startswith('e:')},
                    scope=raw['judgment_prior']))
        if name == 'r02_tick':
            n = networks[p['network_id']]; kind = n['kind']
            costs[kind+'_ticks'] += 1
            costs[kind+'_signals'] += sum(n['top_down'] or l['kind'] != 'top_down' for l in n['program']['links'])
        if name == 'r02_expansion': expansions.append(p)
        if not first_done and name in ('r02_binding_scan','r02_network','r02_tick','r02_settled','r02_pool_result','r02_proposals','r02_expansion','r02_dead_end'):
            first_route_events.append(dict(event=name,payload=p))
        if name in ('r02_expansion','r02_dead_end','r02_expansion_exhausted'): first_done=True
    require(costs['pool_ticks']+costs['decision_ticks']==d['cost']['kernel_ticks'], 'tick split')
    require(costs['pool_signals']+costs['decision_signals']==d['cost']['signal_transmissions'], 'signal split')
    first_pass = []
    for n in networks.values():
        if n['kind'] != 'decision':continue
        ticks = [e['payload'] for e in events if e['event']=='r02_tick' and e['payload']['network_id']==n['network_id']]
        threshold = cfg['kernel']['margin_threshold']
        first_pass.append(dict(network_id=n['network_id'],
            first_true_margin_tick=next((t['tick'] for t in ticks if 2*t['state']['goal']-1 >= threshold),None),
            first_false_margin_tick=next((t['tick'] for t in ticks if 1-2*t['state']['goal'] >= threshold),None),
            first_passage_is_not_stable_convergence=True))
    return dict(**costs, value=d['value'], convergence=d['convergence'],
        primitive_D=d['proof']['primitive_depth'], expansions=d['cost']['expansions'],
        circuit_reuses=d['cost']['circuit_reuses'], binding_operations=d['cost']['binding_operations'],
        program_digest=d['program_digest'], circuit_ids=d['circuit_ids'], assumed_edges=d['proof']['assumed_edges'],
        state=d['state'], missing_slots=[i for i,e in enumerate(obs['edges']) if e['score'] is None],
        zero_slots=[i for i,e in enumerate(obs['edges']) if e['score'] == 0 and e['score'] is not None],
        readout_support_guard=(not drives or not any(drives[-1]['judgment_drive'].values())) and all(e['score'] in (None,0) for e in obs['edges']),
        memory_circuits=[dict(circuit_id=circuit_id(c),length=len(c['pattern']['relations']),strength=c['strength'],
            evidence_count=len(c['evidence_episodes']),balance=len(c['evidence_episodes'])/(len(c['evidence_episodes'])+1),
            failures=c['failures'],active=c['active'],version=c['version']) for c in raw['initial_memory']['circuits']],
        pool_candidates=pools, judgment_networks=drives, first_passage=first_pass,
        first_routing=first_route_events,
        expansion_sequence=[dict(prefix=p['prefix']['path'], candidate=p['candidate']) for p in expansions],
        funnel=candidate_funnel(events,obs,raw['initial_memory'],cfg,raw['use_circuits']),
        end_to_end_wall_seconds=raw['timing']['total_wall_seconds'],
        engine_active_seconds=d['cost']['wall_seconds'], management_seconds=raw['timing']['management_seconds'],
        checkpoint_io_in_inference=False, candidate_funnel_is_not_cause_diagnosis=True)


def summarize(rows, fixed_rows):
    table=[]; pairs=[]; mapping={}; groups=Counter()
    for row in rows:
        r=row['raw']; m=row['metrics']; key=(r['training_count'],r['case'],r['arm']);mapping[key]=row
        outcomes={k:a['correct'] for k,a in row['assessments'].items()}
        table.append(dict(training_count=r['training_count'],case=r['case'],family=r['family'],arm=r['arm'],
                          value=m['value'],assessments=outcomes,status=m['convergence']['status'],
                          primitive_D=m['primitive_D'],expansions=m['expansions'],reuses=m['circuit_reuses'],
                          pool_ticks=m['pool_ticks'],decision_ticks=m['decision_ticks'],
                          pool_signals=m['pool_signals'],decision_signals=m['decision_signals'],
                          binding_operations=m['binding_operations'],all_missing=bool(len(m['missing_slots'])==len(r['observation']['edges']))))
        groups[r['arm']+'/'+('abstained' if m['value'] is None else 'answered')]+=1
    for n,case in sorted({(n,c) for n,c,a in mapping}):
        left=mapping[(n,case,'legacy')];right=mapping[(n,case,'route_only')];graph=mapping[(n,case,'graph_only')]
        lm,rm,gm=[x['metrics'] for x in (left,right,graph)]
        pairs.append(dict(training_count=n,case=case,
            same_observation=left['raw']['observation']==right['raw']['observation']==graph['raw']['observation'],
            same_memory=left['raw']['initial_memory']==right['raw']['initial_memory']==graph['raw']['initial_memory'],
            initial_routing_equal=lm['first_routing']==rm['first_routing'],
            full_expansion_sequence_equal=lm['expansion_sequence']==rm['expansion_sequence'],
            legacy_output=lm['value'],route_only_output=rm['value'],graph_only_output=gm['value'],
            delta_expansions=rm['expansions']-lm['expansions'],
            delta_pool_ticks=rm['pool_ticks']-lm['pool_ticks'],delta_decision_ticks=rm['decision_ticks']-lm['decision_ticks']))
    return dict(schema='hcr-exp12-summary-r031-v1',task_inferences=len(rows),
                training_inferences=9,public_input_count=len({r['raw']['case'] for r in rows}),
                fixed_network_pairs=len(fixed_rows),fixed_network_replays=2*len(fixed_rows),paired_cells=pairs,cases=table,answer_counts=dict(groups),
                unique_tasks_are_not_inference_count=True,hidden_world_reassessments_are_not_new_inferences=True,
                comparisons_are_development_fixtures=True,rigidity_or_human_habit_proved=False,
                learning_rule_changed=False,pool_rule_changed=False,wall_time_speedup_claim=False,
                frozen_network_results=[dict(training_count=f['training_count'],case=f['case'],
                    same_program=f['same_program'],same_initial=f['same_initial'],
                    legacy_goal=f['legacy_goal'],route_only_goal=f['route_only_goal'],
                    legacy_ticks=f['legacy_ticks'],route_only_ticks=f['route_only_ticks']) for f in fixed_rows])


def render(summary):
    lines=['# EXP-12 / R0.3.1 — 회로 선택용 prior와 판단용 prior의 분리','',
           '실행·수치 재연산의 검증과 과학적 가설 판정을 구분한다. 학습/pool 정책은 그대로다.',
           'task inference와 고정 network 재실행을 합쳐 정답률로 세지 않는다. 0점과 결측은 별도 조건이다.','',
           '| 학습 | 사례 | 조건 | 출력 | 외부 평가(world: correct) | 상태 | 확장 | pool tick | 판단 tick |',
           '|---:|---|---|---|---|---|---:|---:|---:|']
    for r in summary['cases']:
        lines.append(f"| {r['training_count']} | {r['case']} | {r['arm']} | {r['value']} | {r['assessments']} | {r['status']} | {r['expansions']} | {r['pool_ticks']} | {r['decision_ticks']} |")
    lines += ['', '## 해석 경계', '',
        'route_only는 pool prior·매칭·첫 macro 선택을 유지하고 최종 relation/goal learned drive만 0으로 만든다. 이후 경로 변경은 별도로 보고한다.',
        'all_missing/all_zero에서 적용되지 않은 prior를 판단 근거로 세지 않는다. fixed_network 결과에는 이 readout support guard를 적용하지 않고 신호 동역학만 비교한다.',
        'funnel의 구조적 universe는 평가기 전용이다. 미매칭/예산 미실행/경쟁 탈락을 원인 확정이나 candidate suppression의 증명으로 바꾸지 않는다.',
        '같은 입력에 숨은 참값 두 개를 평가하는 경우 하나의 추론에 대한 두 채점이다. 추가 정보 없이 둘을 구분했다고 주장하지 않는다.',
        'prior 정책은 session packet과 이벤트에 결속된다. 과거 source hash를 현재 소스에 맞게 고쳐 복원하지 않는다.',
        '강도·검증 횟수·balance는 함께 기록한다. rigidity, 공유 dependency, consolidation, 부정 예외 학습, pool 최적화는 아직 구현하지 않았다.','']
    return '\n'.join(lines)
