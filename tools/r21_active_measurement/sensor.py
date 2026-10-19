"""Private synthetic provider. Only this callable reads feature states/fault fixtures."""
from dataclasses import replace
from hcr.codec import plain
from hcr.model import Observation,EdgeObservation,fingerprint
from hcr.tasks.toy_world import World
from tools.r21_active_measurement.policy import panel,require


def deliver(public,request,fixture,p):
    old=panel(public['observation'])
    world=World(old,tuple(zip(['f0','f1'],fixture['hidden_features'])))
    measured=world.measure(request)
    mode=fixture['mode']
    if mode=='stale':measured=replace(measured,revision=old.revision)
    elif mode=='no_information':measured=replace(measured,edges=old.edges)
    elif mode=='flipped':measured=replace(measured,edges=tuple(replace(edge,score=-edge.score) for edge in measured.edges))
    else:require(mode=='valid','provider fixture mode')
    return dict(source_id=p['request_quote']['source_id'],request_sha256=fingerprint(plain(request)),observation=plain(measured))


def expected(public,request,fixture,p):
    """Audit-only formula; does not invoke World.measure or obtain a new measurement."""
    old=panel(public['observation']);mode=fixture['mode'];scores=[]
    for i,value in enumerate(fixture['hidden_features']):
        score=.98 if value else -.98
        if mode=='flipped':score=-score
        elif mode=='no_information':score=old.edges[i].score
        scores.append(score)
    revision=old.revision if mode=='stale' else old.revision+1
    observed=Observation(old.episode_id,revision,old.start,old.goal,tuple(
        EdgeObservation(edge.id,edge.source,edge.target,scores[i]) for i,edge in enumerate(old.edges)))
    return dict(source_id=p['request_quote']['source_id'],request_sha256=fingerprint(plain(request)),observation=plain(observed))
