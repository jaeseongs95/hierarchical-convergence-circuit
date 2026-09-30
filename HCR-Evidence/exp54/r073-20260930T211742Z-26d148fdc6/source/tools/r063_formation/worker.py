"""Native inference and feedback consumption; no truth/reference evaluator calls."""
import argparse
from pathlib import Path
import sys
from tools.r050_review_boundary.common import dump, load, require, seal, unseal


def execute(plan, case, memory, gate, mode, location, identity):
    from hcr import codec
    from hcr.circuits import AdaptiveMemory
    from hcr.model import Mode
    from hcr.sessions import AdaptiveSession
    from hcr.review import capture_candidate
    cfg = codec.adaptive_config_from(plan['config'])
    session = AdaptiveSession(cfg, AdaptiveMemory.from_document(memory, cfg), session_id=identity,
        use_circuits=gate, top_down=True, allow_reexpansion=True, judgment_prior='route_only')
    dump(location/'step-000-init.json', session.packet())
    session.begin(codec.observation_from(case['observation']), Mode(mode))
    dump(location/'step-001-begin.json', session.packet())
    advances = 0
    # Existing core admits at most one activation pool plus one decision kernel.
    bound = cfg.kernel.max_ticks * (2 if gate and memory['circuits'] else 1)
    while session.phase == 'running':
        before = session.current['pending']['cost']['kernel_ticks']
        if advances >= plan['limits']['max_advances_per_session'] or before+bound > plan['limits']['max_kernel_ticks_per_session']:
            break
        session.advance()
        advances += 1
        dump(location/f'step-{advances+1:03d}-advance.json', session.packet())
        require(session.current['pending']['cost']['kernel_ticks']-before <= bound, 'Native advance exceeded reservation')
    candidate = capture_candidate(session, 0) if session.phase=='readout_ready' else None
    if candidate is not None:
        dump(location/'candidate.json', candidate)
    require(session.memory_document == memory, 'Inference changed persistent memory')
    return dict(packet=session.packet(),candidate=candidate,advances=advances,
        ready=session.phase=='readout_ready',stop='readout_ready' if session.phase=='readout_ready' else 'external_compute_budget')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--run',type=Path,required=True)
    parser.add_argument('--phase',choices=['train','feedback','eval'],required=True)
    parser.add_argument('--episode',type=int)
    args=parser.parse_args();run=args.run
    packet=load(run/'plan.json');plan=unseal(packet,'hcc-r063-plan-v1')
    if args.phase=='train':
        i=args.episode;case=plan['training'][i-1]
        memory=load(run/'memory'/f'{i-1}.json')
        e=execute(plan,case,memory,True,'train',run/'training'/f'{i:02d}'/'progress','r063-train-'+case['id'])
        dump(run/'training'/f'{i:02d}'/'inference.json',seal(dict(schema='hcc-r063-training-v1',
            plan_sha256=packet['sha256'],episode=i,case_id=case['id'],memory_before=memory,execution=e)))
    elif args.phase=='feedback':
        from hcr.model import Feedback
        from hcr.sessions import AdaptiveSession
        i=args.episode;where=run/'training'/f'{i:02d}'
        record=unseal(load(where/'inference.json'),'hcc-r063-training-v1')
        evaluated=unseal(load(where/'reference.json'),'hcc-r063-reference-v1')
        feedback=evaluated['feedback']
        if feedback is None:
            result=dict(packet=None,patch=None,feedback=None,memory_after=record['memory_before'],status='not_applied_no_candidate')
        else:
            # Continue the exact native finish branch that was independently assessed.
            session=AdaptiveSession.from_packet(record['execution']['candidate']['packet'])
            patch=session.feedback(Feedback(**feedback))
            result=dict(packet=session.packet(),patch=patch,feedback=feedback,memory_after=session.memory_document,status='applied')
        dump(where/'learning.json',seal(dict(schema='hcc-r063-learning-v1',**result)))
        dump(run/'memory'/f'{i}.json',result['memory_after'])
    else:
        for n in (0,len(plan['training'])):
            memory=load(run/'memory'/f'{n}.json')
            for gate in (False,True):
                for case in plan['cases']:
                    identity=f"m{n}-{'on' if gate else 'off'}-{case['id']}"
                    e=execute(plan,case,memory,gate,'frozen_eval',run/'evaluation'/identity/'progress','r063-eval-'+identity)
                    dump(run/'evaluation'/identity/'inference.json',seal(dict(schema='hcc-r063-evaluation-v1',
                        plan_sha256=packet['sha256'],identity=identity,case_id=case['id'],memory_count=n,
                        use_circuits=gate,memory_before=memory,execution=e)))
                    print(identity,'recorded',flush=True)


if __name__=='__main__':
    main()
