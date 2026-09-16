#!/usr/bin/env python3
"""EXP-09 r2의 해시·짝 계약·수치 tick·proof·학습 전이를 재검산한다.
생산 inference/learning 함수는 호출하지 않는다. 전체 frontier 선택의 독립 replay는 범위 밖이다.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
from copy import deepcopy
from math import isfinite
from pathlib import Path
import sys
from collect import (BaselineError, require, canonical, sha, loads, read, safe, inventory,
                     verify_bundle, check_chain, canonical_cost, linked)
from probe_analysis import semantic_decision, input_content, decompose, summarize


SCHEMA='hcr-r02-exp09-manifest-v2'


def verify_files(root: Path) -> dict:
    require(not linked(root) and root.is_dir(), '실제 결과 폴더 필요')
    require(not (root/'FAILED.json').exists(), '실패한 probe 결과')
    m=loads(read(safe(root,'manifest.json')))
    require(m['schema']==SCHEMA and m['state']=='complete','완료된 EXP-09 r2 manifest 필요')
    require(inventory(root,{'manifest.json'})==set(m['files']),'probe 파일 누락/추가')
    for name,expected in m['files'].items():
        require(sha(read(safe(root,name)))==expected,'probe 파일 해시: '+name)
    return m


def audit_pairs(rows: list[dict], plan: dict, seeds: dict, weak: dict, measured: dict, cases: dict) -> dict:
    """실험군을 입력/메모리에 몰래 바꾸지 않았는지 외부에서 검사한다."""
    keys=set();counts=Counter();pairs=defaultdict(dict)
    for r in rows:
        phase,arm=r['phase'],r['arm'];counts[phase]+=1
        require(r['memory_before']==r['memory_after_inference'],'frozen/추론 memory 변경')
        if phase=='factorial':
            key=(phase,arm);require(key not in keys,'중복 factorial');keys.add(key)
            mem,profile,routing=arm.split('/')
            require(mem in ('before','after') and profile in ('weak','measured') and routing in ('circuits','graph_only'),'factorial 조건')
            expected=deepcopy(weak if profile=='weak' else measured);expected['episode_id']='e900002'
            require(r['observation']==expected and r['memory_before']==seeds[mem],'factorial 입력/memory 변경')
            require(r['decision']['mode']=='frozen_eval','factorial 학습 금지')
            require(r['engine_use_circuits'] is (routing=='circuits'),'factorial routing 변경')
        elif phase=='cost_pairs':
            case=r['case'];rep=r['replicate']
            require(case in cases and type(rep) is int and 0<=rep<plan['repeats'],'비용 반복 범위')
            require(arm in ('graph_only','circuits'),'비용 arm')
            require(r['observation']==cases[case]['observation'] and r['external_truth']==cases[case]['external_truth'], '비용 사례 변경')
            require(r['memory_before']==seeds['before'] and r['decision']['mode']=='frozen_eval','비용 memory/학습 변경')
            require(r['engine_use_circuits'] is (arm=='circuits'),'비용 routing 변경')
            expected_order=(0 if arm=='graph_only' else 1) if rep%2==0 else (1 if arm=='graph_only' else 0)
            require(r['order_in_pair']==expected_order,'비용 순서 불균형')
            key=(case,rep);require(arm not in pairs[key],'중복 비용 셀');pairs[key][arm]=r
        elif phase=='persistence':
            key=(phase,arm);require(arm in ('direct','reload') and key not in keys,'persistence 중복/조건');keys.add(key)
            expected=deepcopy(weak);expected['episode_id']='e900002'
            require(r['observation']==expected and r['memory_before']==seeds['live'],'persistence 입력/memory')
            require(r['decision']['mode']=='frozen_eval' and r['engine_use_circuits'] is True,'persistence 실행 조건')
        elif phase=='adaptation':
            require(arm in ('measured_replay','same_score_control','training_3','training_6','training_9'),'adaptation 조건')
            require(r['decision']['mode']=='adapt' and r['engine_use_circuits'] is True,'adaptation 실행 조건')
            if r['decision']['attempt']==1:
                key=(phase,arm);require(key not in keys,'adaptation 최초 시도 중복');keys.add(key)
                seed='before' if arm in ('measured_replay','same_score_control','training_6') else arm
                require(r['observation']==weak and r['memory_before']==seeds[seed],'adaptation 시작 조건 변경')
        else:raise BaselineError('알 수 없는 phase: '+phase)
        if phase!='cost_pairs':
            require(r['external_truth']==cases['conflict_truth'],'통제 입력의 truth 변경')
    require(counts['factorial']==8 and counts['persistence']==2,'factorial/persistence 셀 누락')
    require(len(pairs)==5*plan['repeats'] and counts['cost_pairs']==10*plan['repeats'],'비용 쌍 누락')
    require(all(set(a)=={'graph_only','circuits'} for a in pairs.values()),'비용 쌍 불완전')
    require(all(('adaptation',a) in keys for a in ('measured_replay','same_score_control','training_3','training_6','training_9')),'학습 대조 누락')
    require(len(rows)<=plan['max_inferences'],'최대 추론 한도 초과')
    return dict(factorial_cells=8,persistence_cells=2,cost_pairs=len(pairs),adaptation_arms=5)


def verify_probe(bundle: Path, root: Path) -> dict:
    for p in (bundle,root):
        require(all(not linked(q) for q in (p.absolute(),*p.absolute().parents)),'링크/junction 금지')
    bundle,root=bundle.resolve(),root.resolve()
    manifest=verify_files(root);verify_bundle(bundle)
    plan=loads(read(root/'plan.json'))
    require(plan['schema']=='hcr-r02-exp09-plan-v2' and plan['protocol']=='exp09-paired-correction-cost-r2','plan schema')
    require(plan['baseline_bundle_manifest_sha256']==sha(read(bundle/'bundle_manifest.json'))==manifest['source_bundle_manifest_sha256'],'입력 capture 교체')
    original=loads(read(bundle/'run/plan.json'))
    require(plan['original_plan_sha256']==sha(read(bundle/'run/plan.json')), '원 plan hash 변경')
    require(plan['source_hashes']==original['source_hashes'] and plan['config']==original['config']
            and plan['config_signature']==original['config_signature'],'기준선 실행 설정 변경')
    for name,h in plan['tool_source_hashes'].items():
        require(sha(read(safe(root,'tool_source/'+name)))==h,'실행 도구 snapshot hash')
    source=bundle/'source'
    for name,h in plan['source_hashes'].items():require(sha(read(safe(source,name)))==h,'동결 실행 소스 hash')
    sys.dont_write_bytecode=True
    if 'hcr' in sys.modules:
        require(Path(sys.modules['hcr'].__file__).resolve().is_relative_to(source),'다른 HCR가 로드됨')
    else:sys.path.insert(0,str(source/'src'))
    # 수치 재계산·dict 학습 식·외부 proof 검증만 재사용한다.
    from hcr import codec
    from hcr.model import fingerprint
    from hcr.circuits import AdaptiveMemory
    from hcr.evaluation.audit import independent_step
    from hcr.evaluation.adaptive_audit_support import expected_learning
    from hcr.evaluation.reference import assess
    config=codec.adaptive_config_from(plan['config'])
    status=loads(read(root/'status.json'))
    require(status['schema']=='hcr-r02-exp09-status-v2' and status['state']=='complete','probe 상태')
    rows=[loads(x) for x in read(root/'episodes.jsonl').splitlines() if x.strip()]
    events=[loads(x) for x in read(root/'events.jsonl').splitlines() if x.strip()]
    check_chain(events,status)
    rowmap={r['decision']['id']:r for r in rows}
    require(len(rowmap)==len(rows)==status['inferences'],'record 수/중복')
    seed_files={'before':'memory_after_training.json','after':'memory_after_adaptation.json',
                'training_3':'memory_training_3.json','training_9':'memory_training_9.json'}
    seed_docs={k:AdaptiveMemory.load(bundle/'run'/n,config).document() for k,n in seed_files.items()}
    known={fingerprint(x) for x in seed_docs.values()}
    seeds={k:fingerprint(v) for k,v in seed_docs.items()}
    live=AdaptiveMemory.load(root/'live_after_adaptation.json',config)
    seeds['live']=live.digest
    networks={};starts={};decisions={};assessments={};requests={};delivered={};feedbacks={}
    memory=None;engine=None;pending=None;steps=updates=0;attempts={};counts=defaultdict(Counter)
    memory_after_feedback={}
    for event in events:
        n,p=event['event'],event['payload'];did=p.get('decision_id')
        if n=='r02_engine_created':
            require(pending is None,'학습 transaction 중 새 engine')
            require(p['config']==plan['config'] and p['config_signature']==config.signature,'engine config')
            loaded=AdaptiveMemory.from_document(p['memory_document'],config)
            require(loaded.digest==p['memory_hash'] and loaded.digest in known,'출처 없는 memory')
            memory=loaded.document();engine=deepcopy(p);attempts={}
        elif n=='r02_attempt_started':
            require(engine is not None and pending is None and did not in starts and did in rowmap,'attempt 순서/중복')
            require(fingerprint(memory)==p['memory_hash'] and memory['version']==p['memory_version'],'attempt memory')
            row=rowmap[did];require(row['observation']==p['observation'],'row 입력 변경')
            obs=codec.observation_from(p['observation'])
            prev=p['revision_of']
            if prev is not None:
                require(prev in delivered and delivered[prev]==p['observation'] and p['mode']=='adapt','재시도 허가/입력')
            else:require(obs.episode_id not in attempts,'episode 중복')
            attempts[obs.episode_id]=attempts.get(obs.episode_id,0)+1
            require(p['attempt']==attempts[obs.episode_id],'attempt 번호')
            starts[did]=dict(payload=p,obs=obs,memory=deepcopy(memory),engine=deepcopy(engine))
            row['engine_use_circuits']=engine['use_circuits']
        elif n=='r02_network':
            require(did in starts and p['network_id'] not in networks,'network 순서/중복')
            require(p['kind'] in ('pool','decision') and p['top_down'] is starts[did]['engine']['top_down'],'network 조건')
            require(fingerprint(p['program'])==p['program_digest'],'network digest')
            networks[p['network_id']]=dict(p=p,state={g['id']:.5 for g in p['program']['groups']},history=[],
                ticks=0,stable=0,residual=1.,terminal=False,settled=False,oscillating=False)
        elif n=='r02_tick':
            x=networks[p['network_id']];q=x['p']
            require(q['decision_id']==did and not x['terminal'] and not x['settled'],'tick 순서')
            result=independent_step(q['program'],x['state'],q['drives'],config.kernel,q['top_down'])
            require(set(result)==set(p['state']) and all(isfinite(v) and abs(result[k]-v)<2e-12 for k,v in p['state'].items()),'수치 tick 불일치')
            residual=max(abs(result[k]-x['state'][k]) for k in result)
            stable=x['stable']+1 if residual<=config.kernel.residual_tolerance else 0
            require(p['tick']==x['ticks']+1 and p['tick']<=config.kernel.max_ticks
                    and abs(p['residual']-residual)<2e-12 and p['stable_steps']==stable,'tick residual/번호')
            oscillating=bool(x['history'] and residual>config.kernel.residual_tolerance*10 and
                             max(abs(result[k]-x['history'][-1][k]) for k in result)<config.kernel.residual_tolerance)
            x['history']=(x['history']+[x['state']])[-3:]
            x.update(state=dict(p['state']),ticks=p['tick'],stable=stable,residual=p['residual'],oscillating=oscillating,
                     terminal=stable>=config.kernel.patience or oscillating or p['tick']==config.kernel.max_ticks)
            counts[did]['kernel_ticks']+=1;counts[did]['group_updates']+=len(result)
            counts[did]['signal_transmissions']+=sum(q['top_down'] or z['kind']!='top_down' for z in q['program']['links'])
            steps+=1
        elif n=='r02_settled':
            x=networks[p['network_id']]
            require(x['p']['decision_id']==did and x['terminal'] and not x['settled'] and p['state']==x['state'],'settled 상태')
            margin=abs(2*x['state']['goal']-1)
            st=('stable_decision' if margin>=config.kernel.margin_threshold else 'stable_ambiguous') if x['stable']>=config.kernel.patience else ('oscillating' if x['oscillating'] else 'budget_exhausted')
            require(p['convergence']==dict(status=st,ticks=x['ticks'],residual=x['residual'],margin=margin,stable_steps=x['stable']),'수렴 분류')
            x['settled']=True
        elif n=='r02_decision':
            did=p['id'];s=starts[did];require(did not in decisions and rowmap[did]['decision']==p,'판단 누락/덮어쓰기')
            require(rowmap[did]['memory_before']==rowmap[did]['memory_after_inference']==s['payload']['memory_hash'],'판단 memory')
            c=canonical_cost(p['cost'])
            for key in ('kernel_ticks','group_updates','signal_transmissions'):require(c[key]==counts[did][key],'신호 비용: '+key)
            require(c['normalization_ops']==c['group_updates'] and c['proof_nodes_reconstructed']==len(p['proof']['nodes']),'proof/normalization 비용')
            if p['program_digest'] is not None:
                ns=[x for x in networks.values() if x['p']['decision_id']==did and x['p']['kind']=='decision']
                require(ns and ns[-1]['settled'] and ns[-1]['p']['program_digest']==p['program_digest'] and dict(p['state'])==ns[-1]['state'],'판단 signal 연결')
                if p['value'] is not None:
                    require(p['value'] is (dict(p['state'])['goal']>=.5),'readout 뒤집힘')
                    edge_index={e.id:i for i,e in enumerate(s['obs'].edges)}
                    require(all(v is (dict(p['state'])['e:'+str(edge_index[e]) ]>=.5) for e,v in p['proof']['assumed_edges']),'가정/state 불일치')
            decisions[did]=p
        elif n=='r02_external_assessment':
            require(did in decisions and did not in assessments,'assessment 순서')
            result=codec.plain(assess(codec.adaptive_decision_from(decisions[did]),starts[did]['obs'],rowmap[did]['external_truth']))
            require(result==p['assessment']==rowmap[did]['assessment'],'외부 proof/정답 재검산')
            assessments[did]=result
        elif n=='r02_feedback':
            require(did in assessments and did not in feedbacks and pending is None and decisions[did]['mode']!='frozen_eval','feedback 순서/권한')
            a=assessments[did]
            require(p['correct'] is a['correct'] and p['proof_valid'] is (a['proof_valid'] and a['assumption_correct'] is True),'feedback 외부 평가')
            require(p['observation_digest']==decisions[did]['observation_digest'] and fingerprint(memory)==starts[did]['payload']['memory_hash'],'feedback binding')
            feedbacks[did]=p;pending=did
        elif n=='r02_memory_updated':
            did=p['patch']['decision_id'];require(did==pending,'학습 boundary')
            new,patch,cost=expected_learning(memory,starts[did]['obs'],decisions[did],feedbacks[did],config)
            require(p['memory_document']==new and p['patch']==patch and p['memory_after']==fingerprint(new),'학습 전이 불일치')
            canonical_cost(p['cost']);cost.wall_seconds=p['cost']['wall_seconds']
            require(p['cost']==cost.snapshot(),'학습 비용 불일치')
            AdaptiveMemory.from_document(new,config);memory=new;known.add(fingerprint(new));pending=None;updates+=1
            memory_after_feedback[did]=deepcopy(new)
        elif n=='r02_observation_requested':
            require(did in feedbacks and feedbacks[did]['correct'] is False and did not in requests,'측정 요청 권한')
            obs=starts[did]['obs'];ids=[e.id for e in sorted(obs.edges,key=lambda e:(abs(e.score or 0),e.id)) if e.score is None or abs(e.score)<.9]
            require(decisions[did]['attempt']<=config.kernel.max_observation_requests and p['edge_ids']==ids
                    and p['revision']==obs.revision+1 and p['episode_id']==obs.episode_id,'측정 요청 범위')
            requests[did]=p
        elif n=='exp09_observation_delivery':
            did=p['request']['decision_id'];require(did in requests and did not in delivered and p['request']==requests[did],'측정 전달 권한')
            expected=deepcopy(rowmap[did]['observation']);expected['revision']=requests[did]['revision']
            require(p['control'] in ('same_score','world_measure'),'측정 대조 종류')
            same=p['control']=='same_score'
            require(same is (rowmap[did]['arm']=='same_score_control') and p['new_information'] is (not same),'측정 대조 표시')
            if not same:
                for edge in expected['edges']:
                    if edge['id'] in requests[did]['edge_ids']:edge['score']=.98 if rowmap[did]['external_truth'][edge['id']] else -.98
            require(p['observation']==expected,'허가 밖 관측 변경')
            delivered[did]=expected
        elif n in {'r02_workspace_created','r02_binding_scan','r02_pool_unavailable','r02_pool_result',
                   'r02_proposals','r02_expansion','r02_dead_end','r02_progress','r02_expansion_exhausted'}:
            require(did in starts and did not in decisions,'graph event 순서')
            if n in ('r02_binding_scan','r02_pool_result'):
                require(starts[did]['engine']['use_circuits'] and starts[did]['payload']['revision_of'] is None,'비활성 회로 실행')
            if n=='r02_proposals':
                require(p['circuits_enabled'] is (starts[did]['engine']['use_circuits'] and starts[did]['payload']['revision_of'] is None),'reopen routing')
        else:raise BaselineError('알 수 없는 이벤트: '+n)
    require(pending is None and set(rowmap)==set(starts)==set(decisions)==set(assessments),'미완료 판단/학습')
    require(set(feedbacks)=={k for k,d in decisions.items() if d['mode']!='frozen_eval'} and set(requests)==set(delivered),'누락 feedback/측정')
    require(all(x['settled'] for x in networks.values()),'미완료 network')
    measured_rows=sorted((r for r in rows if r['phase']=='adaptation' and r['arm']=='measured_replay'),key=lambda r:r['decision']['attempt'])
    require(bool(measured_rows), 'measured replay 없음')
    last_id=measured_rows[-1]['decision']['id']
    require(live.document()==memory_after_feedback[last_id], 'live checkpoint가 재현 correction 직후 상태와 다름')
    first_id=measured_rows[0]['decision']['id']
    if measured_rows[0]['assessment']['correct'] is False:
        error_memory=AdaptiveMemory.load(root/'memory_after_error.json',config)
        require(error_memory.document()==memory_after_feedback[first_id], '최초 오류 직후 memory checkpoint 불일치')
    else: require(not (root/'memory_after_error.json').exists(), '오류가 없는데 오류 checkpoint가 있음')
    original_rows=[loads(x) for x in read(bundle/'run/episodes.jsonl').splitlines() if x.strip()]
    conflict=sorted((r for r in original_rows if r['phase']=='misconvergence' and r['arm']=='full'),key=lambda r:r['decision']['attempt'])
    weak,measured=deepcopy(conflict[0]['observation']),deepcopy(conflict[-1]['observation'])
    for x in (weak,measured):x['episode_id']='e900001';x['revision']=0
    cases={'conflict_truth':conflict[0]['external_truth']}
    for case in plan['cost_cases']:
        rs=[r for r in original_rows if r['case']==case and r['arm'] in ('cold','graph_only')]
        require(len(rs)==1,'기준 비용 입력');cases[case]=rs[0]
    pairing=audit_pairs(rows,plan,seeds,weak,measured,cases)
    direct=next(r for r in rows if r['phase']=='persistence' and r['arm']=='direct')
    reload=next(r for r in rows if r['phase']=='persistence' and r['arm']=='reload')
    summary=loads(read(root/'summary.json'));p=summary['persistence']
    require(p['memory_equal'] is True and p['memory_digest']==seeds['live'],'persistence digest')
    require(p['behavior_equal'] is (semantic_decision(direct['decision'])==semantic_decision(reload['decision']))
            and p['assessment_equal'] is (direct['assessment']==reload['assessment'])
            and p['both_correct']==[direct['assessment']['correct'],reload['assessment']['correct']],'persistence 집계')
    # 집계 코드는 공유한다. 이 부분을 독립 알고리즘 검산이라고 표시하지 않는다.
    recalculated=summarize(rows,events,p)
    require(all(summary[k]==v for k,v in recalculated.items()),'probe 요약 집계 변경')
    require(loads(read(root/'candidate_trace.json'))==recalculated['details']['candidates'],'후보 표 불일치')
    require(loads(read(root/'feedback_changes.json'))==recalculated['details']['feedback'],'학습 표 불일치')
    verify_files(root);verify_bundle(bundle)
    return dict(schema='hcr-r02-exp09-audit-v2',state='complete',verified=True,differences=[],
        records=len(rows),scalar_ticks_replayed=steps,memory_updates_checked=updates,proofs_reassessed=len(rows),**pairing,
        independent_checks=['numerical recurrence','external proof/reference assessment','memory transition','paired input and conditions'],
        shared_components=['frozen R0.2 independent audit helpers','JSON/data contracts','probe summary aggregation'],
        full_runtime_graph_audit=False,frontier_policy_replayed=False,timing_replayed=False,
        inference_executed=False,original_capture_modified=False,
        limitations=['프로토콜 전체 graph/frontier 선택은 독립 재생하지 않는다.',
                     '완료 기록의 내부 검산이며 외부 실행 인증/가설 증명이 아니다.'])


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--bundle',required=True,type=Path);p.add_argument('--run',required=True,type=Path)
    a=p.parse_args(argv)
    try:print(canonical(verify_probe(a.bundle,a.run)).decode('utf-8'));return 0
    except (BaselineError,OSError,ValueError,TypeError,KeyError,IndexError) as e:
        print(canonical(dict(state='failed',error=type(e).__name__+': '+str(e))).decode('utf-8'),file=sys.stderr);return 2


if __name__=='__main__':raise SystemExit(main())
