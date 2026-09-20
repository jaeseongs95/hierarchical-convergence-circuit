"""사용자가 check를 실행할 때만 사용하는 R0.2 시험 보조 코드."""
from copy import deepcopy
from dataclasses import replace
from hcr import codec
from hcr.model import AdaptiveConfig, Feedback, Mode
from hcr.runtime import AdaptiveEngine
from hcr.tasks.toy_world import chain
from hcr.evaluation.reference import assess


def train_r02(count=6, config=None):
    engine = AdaptiveEngine(config or AdaptiveConfig())
    for i in range(count):
        world = chain('r02-train-' + str(i), (True, True, True), prefix='r02-obj-' + str(i))
        decision = engine.infer(world.observation, Mode.TRAIN)
        assessment = assess(decision, world.observation, dict(world.hidden))
        engine.feedback(Feedback('f-' + decision.id, decision.id, decision.observation_digest,
            assessment.correct, assessment.proof_valid and assessment.assumption_correct is True))
    return engine


def report_feedback(engine, world, decision, *, identity=None):
    result = assess(decision, world.observation, dict(world.hidden))
    engine.feedback(Feedback(identity or 'f-' + decision.id, decision.id, decision.observation_digest,
                             result.correct, result.proof_valid and result.assumption_correct is True))
    return result


def r02_events(engine, name):
    return [e['payload'] for e in engine.trace.records if e['event'] == name]


def rehash_run(root, events=None):
    """논리 변조 시험용. 체크섬을 고쳐도 독립 검산기가 거부하는지 확인한다."""
    import hashlib
    from hcr.model import fingerprint
    if events is not None:
        head = '0' * 64
        records = []
        for i, event in enumerate(events):
            body = dict(seq=i, previous=head, event=event['event'], payload=event['payload'])
            head = fingerprint(body)
            records.append(dict(body, sha256=head))
        (root / 'events.jsonl').write_text(''.join(codec.dumps(e) + '\n' for e in records), encoding='utf-8')
        status = codec.loads((root / 'status.json').read_bytes())
        status['event_head'], status['event_count'] = head, len(records)
        codec.save(root / 'status.json', status, replace=True)
    manifest = codec.loads((root / 'manifest.json').read_bytes())
    manifest['files'] = {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                        for p in root.rglob('*') if p.is_file() and p != root / 'manifest.json'}
    codec.save(root / 'manifest.json', manifest, replace=True)
