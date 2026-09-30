"""Native execution only; private world truth is never loaded here."""
import argparse
from pathlib import Path
from tools.r050_review_boundary.common import dump, load, require, seal, unseal
from tools.r063_formation.worker import execute


def revision(plan, observation, base, location):
    from hcr import codec
    from hcr.model import Mode
    from hcr.review import capture_candidate
    from hcr.sessions import AdaptiveSession
    session = AdaptiveSession.from_packet(base['request_packet'])
    memory = session.memory_document
    session.begin(codec.observation_from(observation), Mode.ADAPT, revision_of=base['request']['decision_id'])
    dump(location/'step-000-begin.json', session.packet())
    count = 0
    bound = plan['config']['kernel']['max_ticks']  # Native revision disables circuit use.
    while session.phase == 'running':
        old = session.current['pending']['cost']['kernel_ticks']
        if count >= plan['limits']['max_advances_per_session'] or old+bound > plan['limits']['max_kernel_ticks_per_session']:
            break
        session.advance(); count += 1
        dump(location/f'step-{count:03d}-advance.json', session.packet())
        require(session.current['pending']['cost']['kernel_ticks']-old <= bound, 'Revision reservation')
    candidate = capture_candidate(session, 0) if session.phase == 'readout_ready' else None
    if candidate is not None: dump(location/'candidate.json', candidate)
    require(session.memory_document == memory, 'Revision mutated memory without feedback')
    return dict(packet=session.packet(), candidate=candidate, advances=count,
        ready=session.phase=='readout_ready', stop='readout_ready' if session.phase=='readout_ready' else 'external_compute_budget')


def consume(execution, evaluated, memory):
    from hcr.model import Feedback
    from hcr.sessions import AdaptiveSession
    if evaluated['feedback'] is None:
        return dict(status='not_applied_no_candidate', feedback=None, packet=None, patch=None, memory_after=memory)
    session = AdaptiveSession.from_packet(execution['candidate']['packet'])
    patch = session.feedback(Feedback(**evaluated['feedback']))
    return dict(status='applied', feedback=evaluated['feedback'], packet=session.packet(), patch=patch, memory_after=session.memory_document)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--run',type=Path,required=True)
    parser.add_argument('--phase',choices=['initial','feedback','revision','final-feedback','eval'],required=True)
    args=parser.parse_args();run=args.run;plan=unseal(load(run/'plan.json'),'hcc-r064-plan-v1')
    if args.phase == 'initial':
        e=execute(plan,plan['initial'],load(run/'memory/before.json'),True,'adapt',run/'initial/progress','r064-initial')
        dump(run/'initial/inference.json',seal(dict(schema='hcc-r064-inference-v1',plan_sha256=fingerprint_plan(run),execution=e)))
    elif args.phase == 'feedback':
        from hcr import codec
        from hcr.sessions import AdaptiveSession
        e=unseal(load(run/'initial/inference.json'),'hcc-r064-inference-v1')['execution']
        r=unseal(load(run/'initial/reference.json'),'hcc-r064-reference-v1')
        result=consume(e,r,load(run/'memory/before.json'))
        dump(run/'initial/learning.json',seal(dict(schema='hcc-r064-learning-v1',**result)))
        dump(run/'memory/after_feedback.json',result['memory_after'])
        request=None;packet=None
        if r['feedback'] is not None and r['feedback']['correct'] is False:
            session=AdaptiveSession.from_packet(result['packet'])
            request=codec.plain(session.request_revision(r['feedback']['decision_id']))
            packet=session.packet()
        dump(run/'request.json',seal(dict(schema='hcc-r064-request-v1',request=request,request_packet=packet,
            status='requested' if request is not None else 'native_no_request' if packet is not None else 'not_requested_no_error')))
    elif args.phase == 'revision':
        base=unseal(load(run/'request.json'),'hcc-r064-request-v1')
        observations=unseal(load(run/'measurements.json'),'hcc-r064-measurements-v1')['observations']
        for arm in plan['spec']['revision_arms']:
            e=None if base['request'] is None else revision(plan,observations[arm],base,run/'revision'/arm/'progress')
            dump(run/'revision'/arm/'inference.json',seal(dict(schema='hcc-r064-inference-v1',plan_sha256=fingerprint_plan(run),
                execution=e,status='not_run_no_native_request' if e is None else 'executed')))
    elif args.phase == 'final-feedback':
        e=unseal(load(run/'revision/corrected_observation/inference.json'),'hcc-r064-inference-v1')['execution']
        r=unseal(load(run/'revision/corrected_observation/reference.json'),'hcc-r064-reference-v1')
        result=consume(e,r,load(run/'memory/after_feedback.json'))
        dump(run/'revision/corrected_observation/learning.json',seal(dict(schema='hcc-r064-learning-v1',**result)))
        dump(run/'memory/after_correction.json',result['memory_after'])
    else:
        for snapshot in plan['spec']['memory_snapshots']:
            memory=load(run/'memory'/f'{snapshot}.json')
            for gate in (False,True):
                for case in plan['cases']:
                    identity=f"{snapshot}-{'on' if gate else 'off'}-{case['id']}"
                    e=execute(plan,case,memory,gate,'frozen_eval',run/'evaluation'/identity/'progress','r064-eval-'+identity)
                    dump(run/'evaluation'/identity/'inference.json',seal(dict(schema='hcc-r064-inference-v1',
                        plan_sha256=fingerprint_plan(run),execution=e)))
                    print(identity,'recorded',flush=True)


def fingerprint_plan(run): return load(run/'plan.json')['sha256']


if __name__=='__main__': main()
