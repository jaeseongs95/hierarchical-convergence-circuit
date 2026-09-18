"""완료된 native state/event로 온라인 제어를 재계산한다. runtime/backend는 import하지 않는다."""
from __future__ import annotations
from copy import deepcopy
from .contracts import demand, digest, finite_nonnegative, SCHEDULE_USAGE
from .schedule_audit import expected_decision, check_transition


def audit_control(run: dict, states: dict[int, dict]) -> dict:
    """states의 native 의미 검증은 호출자가 packet_states로 수행해야 한다."""
    fields = {'schema', 'backend', 'scope', 'policy', 'budget', 'observation_sha256',
              'memory_sha256', 'config_sha256', 'packet', 'candidates', 'selections',
              'events', 'adoption', 'usage', 'terminal_pending_ready', 'wall_seconds', 'scheduler', 'scheduler_usage'}
    demand(set(run) == fields and run['schema'] == 'hcr-scheduled-online-r040-v1', 'online result 필드')
    demand(run['scope'] in ('legacy', 'route_only') and run['policy'] in ('native_saved', 'support_first'),
           '미등록 온라인 조건')
    demand(finite_nonnegative(run['wall_seconds']), 'wall time 형식')
    budget = run['budget']
    ceilings = dict(max_initial_advances=128, max_initial_kernel_ticks=100000,
                    max_extra_advances=128, max_extra_kernel_ticks=100000)
    demand(set(budget) == set(ceilings) and all(type(v) is int and 0 <= v <= ceilings[k]
           for k, v in budget.items()), '제어 예산 형식')
    doc = run['packet']['document']; transitions = doc['transitions']
    ops = [t['operation'] for t in transitions]
    demand(ops[:2] == ['init', 'begin'] and set(ops[2:]) <= {'advance', 'continue_dependency', 'prioritize_frontier'},
           '재시작/관측/미등록 native 개입')
    demand(set(states) == set(range(len(transitions))), 'state generation population')
    core = states[1]; p = core['pending']; obs = p['observation']
    demand(run['observation_sha256'] == digest(obs) and run['config_sha256'] == digest(core['config'])
           and run['memory_sha256'] == digest(core['memory']), '온라인 입력 binding')
    session_id = 'online-r037-' + run['scope'] + '-' + digest(obs)[:20]
    demand(doc['session_id'] == session_id, 'policy와 무관한 session identity')
    usage_keys = ('ranked_paths', 'path_checks', 'edge_checks', 'proof_nodes_created',
                  'proof_nodes_reused', 'gate_assumptions_checked')
    used = dict(initial_advances=0, extra_advances=0,
                initial_kernel_ticks=p['cost']['kernel_ticks'], extra_kernel_ticks=0,
                selection_calls=0, selection={k: 0 for k in usage_keys})
    demand(0 <= used['initial_kernel_ticks'] <= budget['max_initial_kernel_ticks'], 'begin 예산')
    events = run['events']; candidates = run['candidates']; outputs = run['selections']
    demand(len(candidates) == len(outputs), 'readout/selection population')
    pos = 0; generation = 1; seen = 0; processed = None; selected = None; stop = None
    demand(run['scheduler'] in ('input_order','edge_id_min'),'scheduler field')
    scheduler_used={k:0 for k in SCHEDULE_USAGE};scheduler_rows=[]

    def ref(g):
        t = transitions[g]
        return dict(session_id=session_id, generation=g, state_hash=t['after_state'], transition_hash=t['sha256'])

    def phase(c):
        return 'readout_ready' if c['pending']['ready'] else 'running'

    def take(event, **payload):
        nonlocal pos
        expected = dict(ordinal=pos, event=event, **payload)
        demand(pos < len(events) and digest(events[pos]) == digest(expected),
               f'온라인 event 불일치 at {pos}: {event}')
        pos += 1

    take('begin_requested', session_id=session_id, scope=run['scope'], policy=run['policy'],
         observation_sha256=run['observation_sha256'], config_sha256=run['config_sha256'],
         memory_sha256=run['memory_sha256'])
    take('begin_committed', reference=ref(1), phase=phase(core))
    for _ in range(1024):
        core = states[generation]; p = core['pending']
        if p['ready']:
            if processed != generation:
                demand(seen < len(candidates), '실제 native readout 누락')
                candidate = candidates[seen]; selected = outputs[seen]
                demand(candidate['reference']['generation'] == generation and
                       candidate['reference']['segment'] == 0, 'native candidate generation')
                take('readout_requested', reference=ref(generation), readout_ordinal=seen)
                take('readout_committed', readout_ordinal=seen, candidate=candidate)
                demand(selected['policy'] == run['policy'], 'online selector binding')
                take('selection_requested', readout_ordinal=seen, policy=run['policy'],
                     input_sha256=selected['input_sha256'], candidate_sha256=digest(candidate))
                demand(set(selected['usage']) == set(usage_keys) and all(type(v) is int and v >= 0
                       for v in selected['usage'].values()), 'selector 계측 population')
                take('selection_committed', readout_ordinal=seen, result=selected)
                for k in usage_keys:
                    used['selection'][k] += selected['usage'][k]
                used['selection_calls'] += 1; seen += 1; processed = generation
            demand(type(selected['accepted']) is bool, '선택 accepted 형식')
            if selected['accepted']:
                stop = 'stop_supported_policy'; break
            if selected['reason'] in ('ranking_budget', 'scan_budget', 'proof_budget'):
                stop = 'stop_selection_budget'; break
            if p['failure_reason'] is not None:
                stop = 'stop_engine_failure'; break
            if not p['workspace']['frontier']:
                stop = 'stop_frontier_exhausted'; break
        elif p['failure_reason'] is not None:
            stop = 'stop_engine_failure'; break
        stage = 'extra' if seen else 'initial'
        # 생산 tick_bound/choose_action을 호출하지 않고 공개 native 상태에서 별도 계산한다.
        reserve = core['config']['kernel']['max_ticks'] * (
            2 if core['switches']['use_circuits'] and p['revision_of'] is None and core['memory']['circuits'] else 1)
        affordable = (used[stage+'_advances'] < budget['max_'+stage+'_advances'] and
                      used[stage+'_kernel_ticks'] + reserve <= budget['max_'+stage+'_kernel_ticks'])
        if not affordable:
            stop = 'stop_compute_budget' if seen else 'stop_initial_budget'; break
        operation = 'continue_dependency' if p['ready'] else 'advance'
        if operation == 'advance':
            view,decision=expected_decision(core,run['scheduler'])
            take('schedule_requested',reference=ref(generation),scheduler=run['scheduler'],
                 input_sha256=digest(view),view=view)
            take('schedule_decided',decision=decision)
            scheduler_rows.append(dict(before_generation=generation,
                selected_edge_ids=decision['selected_edge_ids'],selected_index=decision['selected_index'],
                frontier_paths_edge_ids=[[view['edge_ids'][s] for s in path] for path in view['frontier_paths']],
                reordered=decision['priority_required']))
            if decision['priority_required']:
                take('priority_requested',reference=ref(generation),path=decision['selected_path'])
                demand(generation+1 in states,'missing priority state')
                check_transition(core,states[generation+1],transitions[generation+1],decision)
                generation+=1;core=states[generation];p=core['pending']
                take('priority_committed',reference=ref(generation),previous_index=decision['selected_index'])
            for k,v in decision['usage'].items(): scheduler_used[k]+=v
        before = p['cost']['kernel_ticks']
        take('work_requested', operation=operation, reference=ref(generation), stage=stage,
             kernel_ticks=before, reserved_kernel_ticks=reserve if operation == 'advance' else 0)
        demand(generation+1 in states and transitions[generation+1]['operation'] == operation,
               '미실행/누락 native 작업')
        generation += 1; after = states[generation]
        delta = after['pending']['cost']['kernel_ticks'] - before
        if operation == 'advance':
            demand(0 <= delta <= reserve, '예약량을 넘는 native advance')
            used[stage+'_advances'] += 1; used[stage+'_kernel_ticks'] += delta
        else:
            demand(delta == 0 and not after['pending']['ready'], 'continue 경계/비용')
            selected = None
        take('work_committed', operation=operation, reference=ref(generation),
             phase=phase(after), kernel_ticks=after['pending']['cost']['kernel_ticks'])
    demand(stop is not None, '제어 audit bound')
    accepted = stop == 'stop_supported_policy'
    adoption = dict(accepted=accepted, value=selected['value'] if accepted else None, reason=stop,
                    policy=run['policy'], readout_ordinal=seen-1 if accepted else None,
                    candidate_id=candidates[seen-1]['candidate_id'] if accepted else None,
                    proof_sha256=digest(selected['proof']) if accepted else None)
    take('stop', reference=ref(generation), adoption=adoption)
    demand(pos == len(events) and generation == len(transitions)-1 and seen == len(candidates),
           '종료 후 숨겨진 계산/선택/여분 readout')
    demand(run['adoption'] == adoption and run['usage'] == used, '채택 또는 비용 재계산 불일치')
    terminal = states[generation]['pending']
    demand(type(run['terminal_pending_ready']) is bool and run['terminal_pending_ready'] == terminal['ready'],
           '미완성 terminal 상태를 마지막 readout으로 취급함')
    demand(run['scheduler_usage']==scheduler_used,'scheduler costs recomputed differently')
    total = terminal['cost']['kernel_ticks']
    demand(total == used['initial_kernel_ticks'] + used['extra_kernel_ticks'], 'native 비용 중복/누락')
    return dict(verified=True, scheduler=run['scheduler'],scheduler_usage=scheduler_used,scheduler_choices=scheduler_rows,
                controller_events=pos, native_readouts=seen,
                initial_without_readout=seen == 0, native_kernel_ticks=total,
                initial_kernel_ticks=used['initial_kernel_ticks'], extra_kernel_ticks=used['extra_kernel_ticks'],
                native_advances=used['initial_advances']+used['extra_advances'],
                selection_calls=used['selection_calls'], selection_usage=deepcopy(used['selection']),
                stop_reason=stop, terminal_pending_ready=terminal['ready'],
                first_decision_preserved=True, no_retry_or_restart=True)
