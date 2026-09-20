from pathlib import Path
from copy import deepcopy
from hcr import codec
from hcr.runtime import Engine
from hcr.model import Mode, Feedback
from hcr.tasks.toy_world import chain
from hcr.evaluation.reference import assess


def trained(count=6):
    engine=Engine()
    for i in range(count):
        world=chain('train-'+str(i),prefix='train-instance-'+str(i))
        d=engine.infer(world.observation,Mode.TRAIN)
        a=assess(d,world.observation,dict(world.hidden))
        engine.feedback(Feedback('feedback-'+d.id,d.id,d.observation_digest,a.correct,
                                 a.proof_valid and a.assumption_correct is True))
    return engine


def adapt(memory,*,reexpand=True,episode='ad'):
    engine=Engine(memory=deepcopy(memory),allow_reexpansion=reexpand)
    world=chain(episode,(False,True),(-.06,.92),prefix='ambiguous-current')
    d=engine.infer(world.observation,Mode.ADAPT);a=assess(d,world.observation,dict(world.hidden))
    engine.feedback(Feedback('feedback-'+d.id,d.id,d.observation_digest,a.correct,a.proof_valid and a.assumption_correct is True))
    request=engine.request_revision(d.id)
    if request:
        obs=world.measure(request);later=engine.infer(obs,Mode.ADAPT,revision_of=d.id);b=assess(later,obs,dict(world.hidden))
        engine.feedback(Feedback('feedback-'+later.id,later.id,later.observation_digest,b.correct,b.proof_valid and b.assumption_correct is True))
        return engine,world,d,a,later,b
    return engine,world,d,a,None,None


def rewrite_manifest(root):
    import hashlib
    manifest=codec.loads((root/'manifest.json').read_bytes())
    manifest['files']={p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
                       for p in root.rglob('*') if p.is_file() and p.name!='manifest.json'}
    codec.save(root/'manifest.json',manifest,replace=True)
