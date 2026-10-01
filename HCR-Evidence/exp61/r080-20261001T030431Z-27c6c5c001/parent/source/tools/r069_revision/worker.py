"""Native donor, one feedback consumption, and six paired branches; no world access."""
import argparse
from pathlib import Path
from hcr import codec
from hcr.sessions import AdaptiveSession
from tools.r050_review_boundary.common import dump, fingerprint, load, require
from tools.r063_formation.worker import execute
from tools.r064_retention.worker import consume, revision


def main(out, phase):
    plan = load(out/'plan.json')
    before = load(out/'parent/memory/after_correction.json')
    if phase == 'initial':
        dump(out/'memory/M0.json', before)
        e = execute(plan, dict(observation=plan['observation']), before, True, 'adapt',
                    out/'initial/progress', 'r069-donor')
        dump(out/'initial/inference.json', e)
    elif phase == 'feedback':
        e = load(out/'initial/inference.json'); ref = load(out/'initial/reference.json')
        result = consume(e, ref, before)
        result['schema'] = 'hcc-r064-learning-v1'
        dump(out/'initial/learning.json', result)
        dump(out/'memory/M1.json', result['memory_after'])
        request = None; packet = None
        if ref['feedback'] is not None and ref['feedback']['correct'] is False:
            doc = result['packet']['document']; last = doc['transitions'][-1]
            expected = dict(session_id=doc['session_id'],generation=last['generation'],
                            state_hash=last['after_state'],transition_hash=last['sha256'])
            session = AdaptiveSession.from_packet(result['packet'], expected_ref=expected,
                expected_memory_hash=fingerprint(result['memory_after']), expected_judgment_prior='route_only')
            request = codec.plain(session.request_revision(ref['feedback']['decision_id']))
            packet = session.packet()
        dump(out/'request.json', dict(schema='hcc-r064-request-v1', request=request, request_packet=packet,
            status='requested' if request is not None else 'native_no_request' if packet is not None
                   else 'not_requested_no_error'))
    else:
        base = load(out/'request.json'); payloads = load(out/'measurements.json')
        for cell in plan['cells']:
            identity = cell['id']; where = out/'evaluation'/identity
            obs = payloads['observations'].get(cell['payload'])
            if obs is None:
                e = None; status = 'not_run_no_authorized_payload'
            elif cell['path'] == 'revision':
                # Reuse the existing bounded native revision runner. Each fork restores the same packet.
                require(base['request_packet']['document']['engine']['memory'] ==
                        load(out/'memory/M1.json'), 'Revision checkpoint binding')
                e = revision(plan, obs, base, where/'progress')
                status = 'executed'
            else:
                memory = load(out/'memory'/f"{cell['memory']}.json")
                e = execute(plan, dict(observation=obs), memory, True, 'adapt',
                            where/'progress', 'r069-'+identity)
                status = 'executed'
            delivery = dict(branch=identity, payload=cell['payload'], observation=obs,
                request_sha256=fingerprint(base), measurement_sha256=fingerprint(payloads),
                acquisition_id=payloads['acquisition']['id'] if cell['payload']=='fresh' and obs else None)
            dump(where/'inference.json', dict(cell=cell, status=status, delivery=delivery, execution=e))
            print(identity, status, flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--out',type=Path,required=True)
    p.add_argument('--phase',choices=['initial','feedback','branches'],required=True)
    a = p.parse_args(); main(a.out,a.phase)
