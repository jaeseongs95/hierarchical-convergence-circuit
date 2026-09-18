"""EXP29 producer: reuse the pinned R047 adapter without editing its execution rules."""
from . import io,spec


def validate_body(plan):
    for name,value in spec.body().items():io.require(plan[name]==value,'frozen design changed: '+name)


def execute(plan,root):
    # World labels and strength metadata stay outside run_query's argument boundary.
    from tools.r047_state_ablation.runtime import run_query
    validate_body(plan)
    cases={c['id']:c for c in plan['cases']};sources={};completed=0;query=None
    try:
        with io.safe(root/'attempts.jsonl').open('xb') as stream:
            def once(q,ob,arm='cold',source=None):
                io.append(stream,dict(event='query_started',query=q))
                r=run_query(ob,plan['kernel_config'],arm,source,
                    event_sink=lambda e:io.append(stream,dict(event='query_event',query=q,record=e)))
                wrapper=dict(schema='hcr-exp29-raw-v1',query=q,record=r)
                io.put(root/'raw'/(q['kind']+'_'+q['id']+'.json'),wrapper)
                io.append(stream,dict(event='query_completed',query=q,raw_sha256=io.digest(wrapper)))
                return r
            for case in plan['cases']:
                key=case['source'];s=plan['sources'][key]
                query=dict(kind='A',id=key)
                sources[key]=once(query,s['observation']);completed+=1
                print('A saved: '+key,flush=True)
            for t in plan['trials']:
                query=dict(kind='B',id=t['id'],trial=t)
                source=sources[t['source']];before=io.digest(source)
                once(query,cases[t['case']]['observation'],t['arm'],source)
                io.require(io.digest(source)==before,'source A was mutated by B')
                completed+=1
                print(f'B saved: {completed-14}/98 {t["id"]}',flush=True)
        return dict(population=plan['population'],sources=14,followups=98,queries=completed,automatic_retry=False)
    except BaseException as e:
        io.failure(root,'execute',e)
        io.put(root/'partial_progress.json',dict(completed=completed,current_query=query,automatic_retry=False))
        raise
