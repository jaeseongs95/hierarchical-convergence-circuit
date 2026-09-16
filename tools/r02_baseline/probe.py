#!/usr/bin/env python3
"""EXP-09 r2: 기존 R0.2 동결본에서 저장·학습·측정·routing·비용을 분리한다.
인수만 지정하면 계획을 출력한다. --execute를 직접 지정해야 새 추론을 실행한다.
"""
from __future__ import annotations
import argparse
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import sys
from time import perf_counter

from collect import (BaselineError, require, loads, read, canonical, sha, safe, inventory,
                     verify_bundle, canonical_cost, check_chain, write_json, write_csv, linked, examine, analyze)
from probe_analysis import semantic_decision, memory_content, summarize, render
from measurement_journal import MeasurementJournal

TOOLS = ('probe.py', 'probe_analysis.py', 'audit_probe.py', 'collect.py',
         'memory_equivalence.py', 'measurement_journal.py')
PROTOCOL = 'exp09-paired-correction-cost-r2'


def roots(bundle: Path, out: Path | None = None) -> tuple[Path, Path | None]:
    """이동한 bundle을 지원한다. symlink/junction과 원본 내부 출력은 거부한다."""
    repo = Path(__file__).resolve().parents[2]
    for p in (bundle, out):
        if p is not None:
            require(all(not linked(q) for q in (p.absolute(), *p.absolute().parents)), '링크/junction 경로 금지')
    bundle = bundle.resolve()
    if out is not None:
        out = out.resolve()
        require(not out.exists() and not out.is_relative_to(bundle) and not out.is_relative_to(repo),
                '출력은 capture/저장소 밖의 새 폴더여야 함')
    return bundle, out


def make_plan(bundle: Path, repeats: int = 4) -> dict:
    require(type(repeats) is int and 2 <= repeats <= 20 and repeats % 2 == 0, '반복 수는 2~20의 짝수')
    manifest = verify_bundle(bundle)
    original = loads(read(bundle / 'run/plan.json'))
    require(original['schema'] == 'hcr-plan-r02', 'R0.2 capture 필요')
    return dict(schema='hcr-r02-exp09-plan-v2', protocol=PROTOCOL,
        tool_revision='r2-recovery1', memory_comparison='paired-first-error-provenance-v1',
        measurement_journal='measurements.jsonl',
        baseline_bundle_manifest_sha256=sha(read(bundle / 'bundle_manifest.json')),
        original_plan_sha256=sha(read(bundle / 'run/plan.json')),
        source_hashes=original['source_hashes'], config=original['config'], config_signature=original['config_signature'],
        tool_source_hashes={n: sha(read(Path(__file__).with_name(n))) for n in TOOLS},
        training_counts=[3, 6, 9], repeats=repeats,
        matrix=dict(memory=['before', 'after'], measurement=['weak', 'measured'], circuits=[True, False]),
        correction_controls=['measured_replay', 'same_score_control'],
        persistence='재현한 adaptation 직후 memory의 direct/save-load. 원 사용자 세션의 RAM 복구가 아님.',
        cost_comparison='같은 before memory, 같은 입력. use_circuits만 변경; 실행 순서를 반복마다 교대.',
        cost_cases=['same_structure', 'counterfactual', 'renamed_reordered', 'longer_composition', 'branched_composition'],
        equality_exclusions=['decision.id', 'decision.cost.wall_seconds'],
        max_inferences=8+2+5*(1+original['config']['kernel']['max_observation_requests'])+10*repeats,
        source_scope='captured R0.2 engine; repository inference code is not modified',
        current_correction_success_is_not_negative_exception_learning=True,
        original_labels_not_passed_to_engine=True, hypothesis_proved=False,
        complete_runtime_graph_audit=False, preserved_capture_files=len(manifest['files']))


def execute(bundle: Path, out: Path, plan: dict) -> dict:
    bundle, out = roots(bundle, out)
    require(out is not None, '출력 필요')
    require(plan == make_plan(bundle, plan['repeats']), '계획 또는 도구/입력 hash 변경')
    source = bundle / 'source'
    for name, expected in plan['source_hashes'].items():
        require(sha(read(safe(source, name))) == expected, '동결 실행 소스 불일치: ' + name)
    sys.dont_write_bytecode = True
    require(not any(k == 'hcr' or k.startswith('hcr.') for k in sys.modules), '별도 Python 프로세스에서 실행')
    sys.path.insert(0, str(source / 'src'))
    from hcr import codec
    from hcr.circuits import AdaptiveMemory
    from hcr.runtime import AdaptiveEngine
    from hcr.model import Feedback, Mode
    from hcr.trace import Trace
    from hcr.tasks.toy_world import World
    from hcr.evaluation.reference import assess
    from hcr.evaluation.adaptive_audit import verify_run
    import hcr
    require(Path(hcr.__file__).resolve().is_relative_to(source), '잘못된 HCR import')
    config = codec.adaptive_config_from(plan['config'])
    original_audit = verify_run(bundle / 'run', check_source=True)
    require(original_audit['verified'] is True and original_audit['differences'] == [], '기준선 audit 실패')
    original_data = examine(bundle / 'run', source)
    original_costs = analyze(original_data)
    source_rows = original_data['rows']
    conflict = sorted((r for r in source_rows if r['phase']=='misconvergence' and r['arm']=='full'),
                      key=lambda r:r['decision']['attempt'])
    require(len(conflict)>=2, '원 run의 실제 수정 관측이 필요; 정밀 측정값을 만들어 넣지 않음')
    first, last = conflict[0], conflict[-1]
    require(first['external_truth']==last['external_truth'], '수정 전후 truth 불일치')
    weak_raw, strong_raw = deepcopy(first['observation']), deepcopy(last['observation'])
    for raw in (weak_raw, strong_raw):
        raw['episode_id'], raw['revision'] = 'e900001', 0
    require([(e['id'],e['source'],e['target']) for e in weak_raw['edges']] ==
            [(e['id'],e['source'],e['target']) for e in strong_raw['edges']], '측정 topology 불일치')
    require(weak_raw != strong_raw, '약한/강한 관측이 같음')
    truth=tuple(sorted(first['external_truth'].items()))
    weak=World(codec.observation_from(weak_raw),truth)
    strong=World(codec.observation_from(strong_raw),truth)
    retest_weak=replace(weak,observation=replace(weak.observation,episode_id='e900002'))
    retest_strong=replace(strong,observation=replace(strong.observation,episode_id='e900002'))
    checkpoint_files={'before':'memory_after_training.json','after':'memory_after_adaptation.json',
                      'training_3':'memory_training_3.json','training_9':'memory_training_9.json'}
    memory={k:AdaptiveMemory.load(bundle/'run'/n,config) for k,n in checkpoint_files.items()}
    benchmarks=[]
    for case in plan['cost_cases']:
        rs=[r for r in source_rows if r['case']==case and
            ((r['phase']=='familiarity' and r['arm']=='cold') or (r['phase']=='novelty' and r['arm']=='graph_only'))]
        require(len(rs)==1, '고정 비용 사례 누락/중복: '+case)
        r=rs[0]
        benchmarks.append((case,World(codec.observation_from(r['observation']),tuple(sorted(r['external_truth'].items())))))
    out.mkdir(parents=True,exist_ok=False)
    trace=None; journal=None
    rows,initializations=[],[]
    began=perf_counter()
    try:
        write_json(out/'plan.json',plan)
        write_json(out/'original_run_audit.json',original_audit)
        write_json(out/'original_cost_analysis.json',original_costs)
        # 결과를 옮겨도 기준 도구를 추적할 수 있게 작성 소스 그대로 보존한다.
        for name in TOOLS:
            dest=out/'tool_source'/name; dest.parent.mkdir(exist_ok=True)
            dest.write_bytes(read(Path(__file__).with_name(name)))
        trace=Trace(out/'events.jsonl')
        journal=MeasurementJournal(out/'measurements.jsonl')

        def make_engine(mem,key,**switches):
            t=perf_counter();cloned=deepcopy(mem);copy_seconds=perf_counter()-t
            start_seq=trace.count
            t=perf_counter();engine=AdaptiveEngine(config,cloned,trace,**switches)
            initialization=dict(key=key,memory_digest=mem.digest,memory_copy_seconds=copy_seconds,
                engine_init_seconds=perf_counter()-t,trace_start_seq=start_seq,trace_end_seq=trace.count)
            journal.append('engine_initialized',initialization)
            initializations.append(initialization)
            return engine

        def record(engine,item,phase,arm,case,mode=Mode.FROZEN_EVAL,revision_of=None,**meta):
            require(len(rows)<plan['max_inferences'], '사전 계획 추론 한도')
            before=engine.memory.digest;t=perf_counter()
            decision=engine.infer(item.observation,mode,revision_of=revision_of)
            call_seconds=perf_counter()-t
            require(before==engine.memory.digest,'추론 중 장기 memory 변경')
            raw=codec.plain(decision);canonical_cost(raw['cost'])
            t=perf_counter();a=assess(decision,item.observation,dict(item.hidden));assessment_seconds=perf_counter()-t
            trace.emit('r02_external_assessment',dict(decision_id=decision.id,assessment=codec.plain(a)))
            row=dict(phase=phase,arm=arm,case=case,observation=codec.plain(item.observation),external_truth=dict(item.hidden),
                     decision=raw,assessment=codec.plain(a),memory_before=before,memory_after_inference=engine.memory.digest,
                     infer_call_seconds=call_seconds,external_assessment_seconds=assessment_seconds,**meta)
            rows.append(row)
            with (out/'episodes.jsonl').open('a',encoding='utf-8',newline='\n') as f:f.write(codec.dumps(row)+'\n')
            return decision,a,row

        def adapt(mem,key,same_score=False):
            engine=make_engine(mem,key);item=weak;previous=None;after_error=None
            while True:
                d,a,row=record(engine,item,'adaptation',key,'matched_weak_conflict',Mode.ADAPT,previous)
                engine.feedback(Feedback('f-'+d.id,d.id,d.observation_digest,a.correct,
                                         a.proof_valid and a.assumption_correct is True))
                if d.attempt==1 and a.correct is False: after_error=deepcopy(engine.memory)
                if a.correct is not False:break
                # 동일 정보 대조는 딱 1회의 재시도만 한다. 반복 약화를 누적시키지 않는다.
                if same_score and d.attempt>=2:break
                request=engine.request_revision(d.id)
                if request is None:break
                obs=(replace(item.observation,revision=request.revision) if same_score else item.measure(request))
                trace.emit('exp09_observation_delivery',dict(request=codec.plain(request),observation=codec.plain(obs),
                    control='same_score' if same_score else 'world_measure',new_information=not same_score))
                item,previous=replace(item,observation=obs),d.id
            return engine,after_error

        live,after_error=adapt(memory['before'],'measured_replay')
        if after_error is not None:after_error.save(out/'memory_after_error.json')
        live_doc=deepcopy(live.memory.document());t=perf_counter()
        live.memory.save(out/'live_after_adaptation.json');save_seconds=perf_counter()-t
        journal.append('memory_saved',dict(checkpoint='live_after_adaptation.json',
            memory_digest=live.memory.digest,elapsed_seconds=save_seconds))
        t=perf_counter()
        restored=AdaptiveMemory.load(out/'live_after_adaptation.json',config);load_seconds=perf_counter()-t
        journal.append('memory_loaded',dict(checkpoint='live_after_adaptation.json',
            memory_digest=restored.digest,elapsed_seconds=load_seconds))
        require(live_doc==restored.document(),'저장·복원 memory 문서 불일치')
        _,_,direct=record(make_engine(live.memory,'persistence/direct'),retest_weak,'persistence','direct','new_weak')
        _,_,reloaded=record(make_engine(restored,'persistence/reload'),retest_weak,'persistence','reload','new_weak')
        persistence=dict(memory_equal=True,behavior_equal=semantic_decision(direct['decision'])==semantic_decision(reloaded['decision']),
            assessment_equal=direct['assessment']==reloaded['assessment'],
            both_correct=[direct['assessment']['correct'],reloaded['assessment']['correct']],
            direct_id=direct['decision']['id'],reload_id=reloaded['decision']['id'],memory_digest=live.memory.digest,
            save_seconds=save_seconds,load_seconds=load_seconds,
            note='재현 episode ID가 다르므로 capture와 live의 증거 ID/전체 memory digest를 같다고 요구하지 않는다.')
        for mem in ('before','after'):
            for profile,item in (('weak',retest_weak),('measured',retest_strong)):
                for circuits in (True,False):
                    key=mem+'/'+profile+'/'+('circuits' if circuits else 'graph_only')
                    record(make_engine(memory[mem],key,use_circuits=circuits),item,'factorial',key,'new_weak_or_measured')
        adapt(memory['before'],'same_score_control',same_score=True)
        for count in (3,6,9):
            adapt(memory['before'] if count==6 else memory['training_'+str(count)],'training_'+str(count))
        for case,item in benchmarks:
            for repeat in range(plan['repeats']):
                arms=(False,True) if repeat%2==0 else (True,False)
                for order,enabled in enumerate(arms):
                    arm='circuits' if enabled else 'graph_only'
                    record(make_engine(memory['before'],f'cost/{case}/{repeat}/{arm}',use_circuits=enabled),item,
                        'cost_pairs',arm,case,replicate=repeat,order_in_pair=order)
        trace.close()
        check_chain(trace.records,dict(event_count=trace.count,event_head=trace.head))
        measured_seconds=perf_counter()-began
        journal.append('probe_records_finished',dict(inferences=len(rows),elapsed_seconds=measured_seconds))
        journal.close()
        summary=summarize(rows,trace.records,persistence)
        summary.update(initializations=initializations,measured_probe_seconds=measured_seconds,
                       execution_complete=True,new_independent_task_samples=0)
        write_json(out/'summary.json',summary)
        write_json(out/'candidate_trace.json',summary['details']['candidates'])
        write_json(out/'feedback_changes.json',summary['details']['feedback'])
        write_csv(out/'costs.csv',summary['details']['costs'])
        write_csv(out/'initializations.csv',initializations)
        (out/'summary.ko.md').write_text(render(summary),encoding='utf-8',newline='\n')
        write_json(out/'status.json',dict(schema='hcr-r02-exp09-status-v2',state='complete',event_count=trace.count,
            event_head=trace.head,inferences=len(rows),engine_modified=False,original_capture_modified=False,
            actual_llm_calls=0,actual_network_calls=0))
        require(make_plan(bundle,plan['repeats'])==plan, '실행 중 capture/도구 변경')
        def manifest():
            names=inventory(out,{'manifest.json'})
            value=dict(schema='hcr-r02-exp09-manifest-v2',state='complete',
                       source_bundle_manifest_sha256=plan['baseline_bundle_manifest_sha256'],
                       files={n:sha(read(safe(out,n))) for n in sorted(names)})
            # 자체 manifest만 2차 기록으로 갱신. 원본 run/capture에는 쓰지 않는다.
            path=out/'manifest.json'
            if path.exists():path.write_bytes(canonical(value)+b'\n')
            else:write_json(path,value)
        manifest()
        from audit_probe import verify_probe
        audit=verify_probe(bundle,out)
        write_json(out/'audit.json',audit);manifest()
        return dict(state='complete',output=str(out),inferences=len(rows),persistence=persistence,
                    audit_verified=audit['verified'],full_runtime_graph_audit=False)
    except BaseException as error:
        if trace is not None:trace.close()
        if journal is not None:journal.close()
        # 완료 manifest가 있어도 audit 실패는 별도 FAILED 기록으로 완료 bundle의 수용을 막는다.
        if not (out/'FAILED.json').exists():
            write_json(out/'FAILED.json',dict(state='failed',error=type(error).__name__+': '+str(error),inferences=len(rows)))
        raise


def main(argv=None) -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--bundle',required=True,type=Path)
    p.add_argument('--out',type=Path)
    p.add_argument('--repeats',type=int,default=4)
    p.add_argument('--execute',action='store_true')
    args=p.parse_args(argv)
    try:
        bundle,_=roots(args.bundle)
        plan=make_plan(bundle,args.repeats)
        if args.execute:
            require(args.out is not None,'--execute에는 --out 필요')
            result=execute(bundle,args.out,plan)
        else:
            if args.out is not None:roots(bundle,args.out)
            result=dict(state='planned',plan=plan,engine_executed=False,files_written=False)
        print(canonical(result).decode('utf-8'));return 0
    except (BaselineError,OSError,ValueError,KeyError,TypeError,IndexError) as e:
        print(canonical(dict(state='failed',error=type(e).__name__+': '+str(e))).decode('utf-8'),file=sys.stderr);return 2


if __name__=='__main__':raise SystemExit(main())
