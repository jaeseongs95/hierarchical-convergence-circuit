"""EXP-15 독립 검산. production selection/controller 함수를 호출하지 않는다.

증명은 DAG로 다시 해석한다. session recurrence/원래 finish 검산은 기존 독립
EXP-14 auditor를 재사용한다. 이 파일의 순수 proof 검산은 표준 라이브러리만 쓴다.
"""
from __future__ import annotations
from copy import deepcopy
import hashlib
import json
from math import isfinite


class SelectionAuditError(ValueError):
    pass


def demand(ok, message):
    if not ok:
        raise SelectionAuditError(message)


def sha(x):
    return hashlib.sha256(json.dumps(x, ensure_ascii=False, sort_keys=True,
        separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest()


def finite(x):
    return type(x) in (int, float) and isfinite(x) and x >= 0


def source_view(candidate):
    """생산 projection을 재사용하지 않고 원 candidate의 원자료로 입력을 재구성."""
    dec = candidate['decision']; packet = candidate['packet']; doc = packet['document']
    events = doc['events']; obs = None; net = None; emitted = []
    for e in events:
        p = e['payload']
        if e['event'] == 'r02_attempt_started' and p['decision_id'] == dec['id']:
            demand(obs is None, 'duplicate observation source'); obs = p['observation']
        if e['event'] == 'r02_network' and p['decision_id'] == dec['id'] and p['kind'] == 'decision':
            net = p
        if e['event'] == 'r02_decision' and p['id'] == dec['id']:
            emitted.append(p)
    demand(obs is not None and emitted == [dec], 'source decision/observation')
    demand(packet['sha256'] == sha(doc), 'source packet sha')
    demand(dec['observation_digest'] == sha(obs) and dec['observation_revision'] == obs['revision']
        and dec['episode_id'] == obs['episode_id'], 'source observation identity')
    if net is not None:
        demand(dec['program_digest'] == net['program_digest'] == sha(net['program']), 'source program')
        demand(dec['expanded_paths'] == net['program']['paths'] == [r['path'] for r in net['metadata']['routes']], 'source route provenance')
    else:
        demand(dec['program_digest'] is None and not dec['expanded_paths'], 'unexpected generated paths')
    demand(len(dict(dec['state']))==len(dec['state']), 'duplicate state identity')
    return dict(schema='hcr-selection-view-r034-v1', source_candidate_id=candidate['candidate_id'],
        source_reference=deepcopy(candidate['reference']), source_decision_sha256=sha(dec),
        source_packet_sha256=packet['sha256'], observation=deepcopy(obs), observation_digest=sha(obs),
        raw_value=dec['value'], state=dict(dec['state']), completed_paths=deepcopy(dec['expanded_paths']),
        graph_complete=dec['graph_complete'], original_proof=deepcopy(dec['proof']),
        min_abs_score=candidate['diagnostic']['contract']['min_abs_score'])


def _verify_selection(view, output):
    """등록된 선택 순서/예산과 실제 proof DAG를 독립 재계산한다."""
    demand(view['schema'] == 'hcr-selection-view-r034-v1', 'view schema')
    demand(set(view) == {'schema','source_candidate_id','source_reference','source_decision_sha256',
        'source_packet_sha256','observation','observation_digest','raw_value','state','completed_paths',
        'graph_complete','original_proof','min_abs_score'}, 'view fields')
    demand(type(view['raw_value']) in (bool, type(None)), 'typed raw value')
    demand(type(view['graph_complete']) is bool, 'typed graph completeness')
    obs = view['observation']; edges = obs['edges']; paths = view['completed_paths']; state = view['state']
    demand(set(obs) == {'episode_id','revision','start','goal','edges'} and sha(obs) == view['observation_digest'], 'public observation')
    demand(type(obs['revision']) is int and obs['revision'] >= 0, 'revision')
    demand(all(isinstance(obs[k], str) and obs[k] for k in ('episode_id','start','goal')), 'observation ids')
    demand(isinstance(edges, list) and len(edges) <= 4096, 'edge bound')
    demand(all(isinstance(e,dict) and set(e)=={'id','source','target','score'} for e in edges), 'edge fields')
    demand(all(all(isinstance(e[k],str) and e[k] for k in ('id','source','target')) for e in edges), 'edge ids')
    demand(len({e['id'] for e in edges}) == len(edges), 'edge uniqueness')
    demand(all(e['score'] is None or type(e['score']) in (int,float) and isfinite(e['score'])
        and -1 <= e['score'] <= 1 for e in edges), 'score domain')
    threshold = view['min_abs_score']
    demand(type(threshold) in (int,float) and isfinite(threshold) and 0 <= threshold < 1, 'threshold')
    demand(isinstance(state,dict) and all(isinstance(k,str) and type(v) in (int,float)
        and isfinite(v) and 0 <= v <= 1 for k,v in state.items()), 'state domain')
    demand(isinstance(paths,list) and len(paths) <= 4096 and all(isinstance(p,list) for p in paths), 'path type')
    demand(len({tuple(p) for p in paths})==len(paths), 'path uniqueness')
    for i,p in enumerate(paths):
        demand(p and all(type(s)is int and 0<=s<len(edges) for s in p), 'path slots')
        route = [edges[s] for s in p]
        demand(route[0]['source']==obs['start'] and route[-1]['target']==obs['goal'], 'route endpoints')
        demand(all(a['target']==b['source'] for a,b in zip(route,route[1:])), 'route continuity')
        vertices = [obs['start']] + [e['target'] for e in route]
        demand(len(set(vertices))==len(vertices), 'route cycle')
        demand(all('e:'+str(s) in state for s in p) and f'p:{i}:{len(p)-1}' in state, 'route activation')
    ref = view['source_reference']
    demand(set(ref)=={'segment','generation','ready_sha256','finished_sha256'} and
        all(type(ref[k]) is int and ref[k]>=0 for k in ('segment','generation')), 'source reference')
    demand(ref['finished_sha256']==view['source_packet_sha256'] and
        view['source_candidate_id']=='review-candidate-'+sha(ref), 'candidate source identity')
    for h in (view['source_decision_sha256'],view['source_packet_sha256'],view['observation_digest'],ref['ready_sha256'],ref['finished_sha256']):
        demand(isinstance(h,str) and len(h)==64 and set(h)<=set('0123456789abcdef'), 'digest domain')
    demand(set(output) == {'schema','policy','source_candidate_id','source_view_sha256','source_reference',
        'source_decision_sha256','source_packet_sha256','limits','usage_before','usage_delta','usage_after',
        'path_checks','selected_path_index','proof','value','accepted','reason','boundaries','candidate_id','wall_seconds'}, 'selection fields')
    demand(output['schema']=='hcr-proof-selection-r034-v1' and output['policy']=='support_first_same_value', 'selection version')
    demand(output['source_view_sha256']==sha(view), 'selection input hash')
    for k in ('source_candidate_id','source_reference','source_decision_sha256','source_packet_sha256'):
        demand(sha(output[k])==sha(view[k]), 'selection source: '+k)
    unsigned = {k:v for k,v in output.items() if k not in ('candidate_id','wall_seconds')}
    demand(output['candidate_id']=='selection-candidate-'+sha(unsigned) and finite(output['wall_seconds']), 'selection identity/time')
    usage_keys=('ranked_paths','path_checks','edge_checks','proof_nodes')
    limits=output['limits'];before=output['usage_before'];delta={k:0 for k in usage_keys}
    demand(set(limits)=={'max_'+k for k in usage_keys} and
        all(type(v)is int and 0<=v<=100000 for v in limits.values()), 'limit contract')
    demand(set(before)==set(usage_keys) and all(type(before[k])is int and 0<=before[k]<=limits['max_'+k] for k in before), 'before budget')
    scanned=[];winner=None;reason='raw_value_not_true'
    if view['raw_value'] is True:
        if before['ranked_paths']+len(paths)>limits['max_ranked_paths']:
            reason='selection_ranking_budget'
        else:
            delta['ranked_paths']=len(paths)
            rank=sorted(enumerate(paths),key=lambda pair:(-state[f'p:{pair[0]}:{len(pair[1])-1}'],pair[0]))
            reason='no_supported_existing_path'
            for i,p in rank:
                if (before['path_checks']+delta['path_checks']>=limits['max_path_checks'] or
                    before['edge_checks']+delta['edge_checks']+len(p)>limits['max_edge_checks']):
                    reason='selection_scan_budget';break
                delta['path_checks']+=1;delta['edge_checks']+=len(p)
                activation_ok=not any(state['e:'+str(s)]<.5 for s in p)
                evidence_ok=not any(edges[s]['score'] is None or edges[s]['score']<=threshold for s in p)
                scanned.append(dict(path_index=i,slots=p,activation_eligible=activation_ok,observation_supported=evidence_ok))
                if activation_ok and evidence_ok:
                    if before['proof_nodes']+2*len(p)>limits['max_proof_nodes']:
                        reason='selection_proof_budget';break
                    winner=i;delta['proof_nodes']=2*len(p);reason='supported_existing_positive_path';break
    demand(output['selected_path_index'] is None or type(output['selected_path_index']) is int, 'selected index type')
    demand(sha(output['path_checks'])==sha(scanned) and output['selected_path_index']==winner, 'selection order/result')
    for name in ('usage_delta','usage_after'):
        demand(set(output[name])==set(usage_keys) and all(type(v)is int and v>=0 for v in output[name].values()), 'counter types')
    demand(output['usage_delta']==delta and output['usage_after']=={k:before[k]+delta[k] for k in usage_keys}, 'selection cost counters')
    demand(type(output['accepted'])is bool and output['accepted']==(winner is not None), 'acceptance')
    demand(output['value'] is (True if winner is not None else None) and output['reason']==reason, 'value/reason')
    demand(output['boundaries']==dict(original_decision_modified=False,activation_modified=False,
        new_paths_generated=False,hidden_truth_accessed=False,learned_memory_modified=False,
        value_flip_allowed=False,explicit_proof_selection_intervention=True,counters_are_full_cpu_cost=False), 'selection boundaries')
    proof=output['proof']
    if winner is None:
        demand(proof is None, 'unexpected proof for abstention')
    else:
        demand(view['raw_value'] is True, 'selection cannot flip a raw value')
        demand(set(proof)=={'nodes','final','primitive_depth','assumed_edges','under_assumptions_valid','paths'}, 'proof fields')
        demand(proof['under_assumptions_valid'] is True, 'proof validity flag')
        demand(proof['paths']==[[edges[s]['id'] for s in p] for p in paths], 'proof path inventory')
        chosen=paths[winner];chosen_ids=[edges[s]['id'] for s in chosen]
        demand(all(isinstance(a,list) and len(a)==2 and isinstance(a[0],str) and a[1] is True for a in proof['assumed_edges']), 'assumption types')
        demand(proof['assumed_edges']==sorted([[eid,True] for eid in chosen_ids]), 'assumption provenance')
        demand(len(proof['nodes'])==2*len(chosen), 'proof node inventory')
        meanings={};depth={};order=[]
        for node in proof['nodes']:
            demand(set(node)=={'id','rule','edge_id','parents','path_index'}, 'proof node fields')
            nid=node['id'];parents=node['parents'];rule=node['rule']
            demand(isinstance(nid,str) and isinstance(parents,list) and all(isinstance(p,str) for p in parents), 'node identity/parents')
            demand(node['path_index'] is None or type(node['path_index'])is int, 'path index type')
            demand(nid not in meanings and all(p in meanings for p in parents), 'DAG order/cycle/duplicate')
            if rule=='assumed_open':
                demand(not parents and node['path_index'] is None and node['edge_id'] in chosen_ids, 'fact node')
                meanings[nid]=('fact',node['edge_id']);depth[nid]=0
                demand(nid==f"f:{chosen[chosen_ids.index(node['edge_id'])]}:1", 'fact identity')
            elif rule=='start_edge':
                demand(len(parents)==1 and meanings[parents[0]][0]=='fact' and node['edge_id'] is None
                       and node['path_index']==winner, 'start inference')
                meanings[nid]=('path',[meanings[parents[0]][1]]);depth[nid]=1
            elif rule=='extend_path':
                demand(len(parents)==2 and meanings[parents[0]][0]=='path' and meanings[parents[1]][0]=='fact'
                       and node['edge_id'] is None and node['path_index']==winner, 'extend inference')
                meanings[nid]=('path',meanings[parents[0]][1]+[meanings[parents[1]][1]])
                depth[nid]=1+max(depth[p] for p in parents)
            else:
                raise SelectionAuditError('unregistered proof primitive')
            order.append(nid)
        demand(proof['final'] in meanings and meanings[proof['final']]==('path',chosen_ids), 'final primitive path')
        demand(type(proof['primitive_depth'])is int and proof['primitive_depth']==depth[proof['final']]==len(chosen), 'D_DAG recomputation')
        expected_order=[x for j,s in enumerate(chosen) for x in (f'f:{s}:1',f'r:{winner}:{j}')]
        demand(order==expected_order and proof['final']==expected_order[-1], 'proof canonical identity')
    return dict(verified=True,paths_checked=len(scanned),edge_checks=delta['edge_checks'],
                proof_nodes_checked=delta['proof_nodes'],value_preserved=True)


def verify_selection(view, output):
    try:
        return _verify_selection(view, output)
    except SelectionAuditError:
        raise
    except (KeyError, TypeError, IndexError, AttributeError) as exc:
        raise SelectionAuditError('malformed selection evidence: '+str(exc)) from exc


def audit_flow(baseline, run, *, world=None, provider_mode='perfect'):
    """기록으로 controller 순서를 재생. 실행기/선택기를 호출하지 않는다."""
    from .review_audit import packet_states, verify_candidate, audit_rollout
    from ..prior_policy import read_scope
    demand(baseline['sha256']==sha({k:v for k,v in baseline.items() if k!='sha256'}), 'baseline seal')
    if run['schema']=='hcr-selection-observation-reference-r034-v1':
        demand(set(run)=={'schema','baseline_sha256','arm','reference'} and run['arm']=='observe_first'
            and run['baseline_sha256']==baseline['sha256'] and run['reference']['policy']=='observe_first', 'reference binding')
        report=audit_rollout(baseline,run['reference'],world=world,provider_mode=provider_mode)
        return dict(verified=True,kind='exp14_observation_reference',reference_audit=report)
    demand(run['schema']=='hcr-selection-flow-r034-v1' and run['baseline_sha256']==baseline['sha256'], 'flow schema/baseline')
    demand(set(run)=={'schema','baseline_sha256','arm','limits','selection_limits','segments','candidates',
        'selections','actions','result','usage','cost','timing','boundaries'}, 'flow fields')
    arm=run['arm'];demand(arm in ('hold','expand_only','restart_same','restart_route_only','select_only','expand_then_select','continue'), 'arm')
    lim=run['limits'];slim=run['selection_limits']
    demand(set(lim)=={'max_extra_advances','max_extra_kernel_ticks','max_measurements'} and
        all(type(lim[k])is int and 0<=lim[k]<=v for k,v in [('max_extra_advances',128),('max_extra_kernel_ticks',100000),('max_measurements',16)]), 'work limits')
    demand(set(slim)=={'max_ranked_paths','max_path_checks','max_edge_checks','max_proof_nodes'} and
        all(type(v)is int and 0<=v<=100000 for v in slim.values()), 'selection limits')
    base=baseline['ready']['document'];g0=len(base['transitions'])-1
    demand(baseline['ready']['sha256']==sha(base), 'base packet seal')
    demand(baseline['observation']==base['engine']['pending']['observation'] and
        baseline['judgment_prior']==read_scope(base['engine']), 'baseline public bindings')
    memory=base['engine']['memory'];config=base['engine']['config'];flags=base['engine']['switches']
    segments=run['segments'];demand(1<=len(segments)<=2, 'segment bound')
    maps=[]
    for i,p in enumerate(segments):
        states,report=packet_states(p);maps.append(states);core=p['document']['engine']
        demand(core['pending'] is not None and core['memory']==memory and core['config']==config
            and core['switches']==flags and not core['held'] and not core['feedback'] and not core['requests'], 'frozen segment')
        demand(core['pending']['observation']==baseline['observation'], 'observation changed in non-observation arm')
        demand(set(t['operation'] for t in p['document']['transitions'])<={'init','begin','advance','continue_dependency'}, 'unregistered work')
        expected_scope=baseline['judgment_prior'] if i==0 or arm=='restart_same' else 'route_only'
        demand(read_scope(core)==expected_scope, 'scope intervention')
    doc0=segments[0]['document']
    demand(doc0['transitions'][:g0+1]==base['transitions'] and doc0['events'][:len(base['events'])]==base['events']
        and maps[0][g0]==base['engine'], 'baseline prefix changed')
    candidates=run['candidates'];bykey={};byid={}
    for c in candidates:
        i=c['reference']['segment'];g=c['reference']['generation']
        demand(type(i)is int and 0<=i<len(segments) and (i,g) not in bykey and c['candidate_id'] not in byid, 'candidate uniqueness')
        verify_candidate(c,segments[i],maps[i]);bykey[i,g]=c;byid[c['candidate_id']]=c
    if baseline['first'] is None:
        demand(baseline['schema']=='hcr-selection-running-baseline-r034-v1' and not base['engine']['pending']['ready'], 'running baseline')
        demand(not flags['use_circuits'] and baseline['judgment_prior']=='route_only' and
            baseline['initial_advances']==sum(t['operation']=='advance' for t in base['transitions']), 'computation control boundary')
        current=None;seen=[]
    else:
        demand(baseline['schema']=='hcr-review-baseline-r033-v1' and candidates and candidates[0]==baseline['first'], 'first candidate preserved')
        demand(candidates[0]['reference']['segment']==0 and candidates[0]['reference']['generation']==g0, 'first candidate boundary')
        current=candidates[0];seen=[current['candidate_id']]
    selections=run['selections'];selidx=0;selected=None;checked=set()
    u=dict(extra_advances=0,extra_kernel_ticks=0,restarts=0,selection_calls=0,ranked_paths=0,path_checks=0,edge_checks=0,proof_nodes=0)
    segment=0;generation=g0;stop=None
    demand(isinstance(run['actions'],list) and 1<=len(run['actions'])<=1024, 'action bound')
    for turn,record in enumerate(run['actions']):
        demand(stop is None, 'action after terminal condition')
        core=maps[segment][generation];pending=core['pending'];doc=segments[segment]['document'];tr=doc['transitions'][generation]
        bound=config['kernel']['max_ticks']*(2 if flags['use_circuits'] and pending['revision_of'] is None and memory['circuits'] else 1)
        affordable=u['extra_advances']<lim['max_extra_advances'] and u['extra_kernel_ticks']+bound<=lim['max_extra_kernel_ticks']
        if pending['ready'] and current is not None and current['readout']['accepted']:
            wanted='stop_supported_native'
        elif selected is not None and selected['accepted']:
            wanted='stop_supported_selection'
        elif arm=='hold':wanted='stop_hold'
        elif pending['failure_reason'] is not None:wanted='stop_engine_failure'
        elif not pending['ready']:wanted='advance' if affordable else 'stop_compute_budget'
        elif arm in ('restart_same','restart_route_only'):
            wanted='stop_restart_finished' if u['restarts'] else 'restart' if affordable else 'stop_compute_budget'
        elif arm in ('select_only','expand_then_select') and current['candidate_id'] not in checked:
            wanted='select_existing_proof'
        elif arm=='select_only':wanted='stop_no_supported_selection'
        elif pending['workspace']['frontier']:wanted='continue_dependency' if affordable else 'stop_compute_budget'
        else:wanted='stop_frontier_exhausted'
        ref=dict(session_id=doc['session_id'],generation=generation,state_hash=tr['after_state'],transition_hash=tr['sha256'])
        expected_record=dict(ordinal=turn,action=wanted,segment=segment,generation=generation,reference=ref,
            source_candidate_id=None if current is None else current['candidate_id'],usage_before=u)
        demand(sha(record)==sha(expected_record), 'controller action replay')
        if wanted.startswith('stop_'):
            stop=wanted;continue
        if wanted=='select_existing_proof':
            demand(selidx<len(selections), 'missing sidecar selection')
            selected=selections[selidx];selidx+=1
            demand(selected['limits']==slim and selected['usage_before']=={k:u[k] for k in ('ranked_paths','path_checks','edge_checks','proof_nodes')}, 'cumulative selection budget')
            verify_selection(source_view(current),selected)
            checked.add(current['candidate_id']);u['selection_calls']+=1;u.update(selected['usage_after'])
        elif wanted in ('advance','continue_dependency'):
            demand(generation+1 in maps[segment] and doc['transitions'][generation+1]['operation']==wanted, 'missing or fabricated operation')
            old=pending;generation+=1;new=maps[segment][generation]['pending']
            if wanted=='continue_dependency':current=None;selected=None
            else:
                ticks=new['cost']['kernel_ticks']-old['cost']['kernel_ticks']
                demand(0<=ticks<=bound, 'kernel budget exceeded')
                u['extra_advances']+=1;u['extra_kernel_ticks']+=ticks
                if new['ready']:
                    demand((segment,generation) in bykey, 'unreported native readout')
                    current=bykey[segment,generation];seen.append(current['candidate_id']);selected=None
        else:
            demand(generation==len(doc['transitions'])-1 and segment+1<len(segments), 'restart discards unreported work')
            segment+=1;generation=1;newdoc=segments[segment]['document']
            demand([t['operation'] for t in newdoc['transitions'][:2]]==['init','begin'] and
                not maps[segment][generation]['pending']['ready'], 'restart initial state')
            u['restarts']+=1;current=None;selected=None
    demand(stop is not None and segment==len(segments)-1 and generation==len(segments[-1]['document']['transitions'])-1, 'unreported tail work')
    demand(seen==[c['candidate_id'] for c in candidates] and selidx==len(selections), 'unreported candidate/selection')
    result=dict(value=None,origin='none',candidate_id=None,reason=stop)
    if stop=='stop_supported_native':result.update(value=current['decision']['value'],origin='native',candidate_id=current['candidate_id'])
    if stop=='stop_supported_selection':result.update(value=selected['value'],origin='selection',candidate_id=selected['candidate_id'])
    demand(sha(run['result'])==sha(result) and sha(run['usage'])==sha(u), 'final selection/usage mismatch')
    initial=base['engine']['pending']['cost']['kernel_ticks'];total=sum(p['document']['engine']['pending']['cost']['kernel_ticks'] for p in segments)
    initial_nodes=0 if baseline['first'] is None else len(baseline['first']['decision']['proof']['nodes'])
    native_nodes=sum(len(c['decision']['proof']['nodes']) for c in candidates)
    demand(total==initial+u['extra_kernel_ticks'], 'shared baseline counted twice')
    expected_cost=dict(initial_kernel_ticks=initial,pathway_kernel_ticks=total,initial_native_proof_nodes=initial_nodes,
        native_proof_nodes=native_nodes,extra_native_proof_nodes=native_nodes-initial_nodes,sidecar_proof_nodes=u['proof_nodes'],measurements=0)
    demand(sha(run['cost'])==sha(expected_cost), 'cost ledger')
    demand(set(run['timing'])=={'wall_seconds','selection_wall_seconds'} and all(finite(t) for t in run['timing'].values())
        and run['timing']['selection_wall_seconds']==sum(s['wall_seconds'] for s in selections), 'timing accounting')
    demand(run['boundaries']==dict(original_candidate_preserved=True,frozen_memory=True,observation_unchanged=True,
        support_selection_is_sidecar=True,no_value_flips_by_selection=True,selection_cost_is_not_kernel_cost=True,
        not_autonomous_policy_learning=True), 'boundaries')
    return dict(verified=True,kind='exp15_selection_flow',session_segments=len(segments),
        native_candidates=len(candidates),selection_calls=selidx,controller_actions=len(run['actions']),
        extra_kernel_ticks=u['extra_kernel_ticks'],sidecar_proof_nodes=u['proof_nodes'],
        original_candidate_preserved=True,native_auditors_reused=True)
