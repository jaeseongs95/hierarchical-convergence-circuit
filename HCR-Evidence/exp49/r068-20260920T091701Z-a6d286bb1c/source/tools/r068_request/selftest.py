"""Synthetic API controls only; these are not HCC research observations."""
import argparse
from copy import deepcopy
from pathlib import Path
from hcr import codec
from hcr.circuits import AdaptiveMemory
from hcr.model import ContractError, Feedback, Mode
from hcr.sessions import AdaptiveSession
from tools.r050_review_boundary.common import dump, load, require


def main(out):
    plan = load(out/'plan.json'); rows = []
    for name in plan['synthetic_cases']:
        config = deepcopy(plan['config']); obs = deepcopy(plan['observation'])
        obs['episode_id'] = 'synthetic-'+name
        if name in ('single_candidate_revision', 'duplicate_pending', 'unrequested_edge'):
            obs['edges'][0]['score'] = 1.0
        if name == 'strong_edges':
            for edge in obs['edges']: edge['score'] = 1.0
        if name == 'zero_budget': config['kernel']['max_observation_requests'] = 0
        mode = 'frozen_eval' if name == 'frozen_feedback' else 'train' if name == 'train_mode' else 'adapt'
        cfg = codec.adaptive_config_from(config)
        session = AdaptiveSession(cfg, AdaptiveMemory.from_document(
            load(out/'parent/memory/after_correction.json'), cfg), session_id='r068-synthetic-'+name,
            use_circuits=False, allow_reexpansion=name != 'disabled', judgment_prior='route_only')
        session.begin(codec.observation_from(obs), Mode(mode))
        decision = session.complete(); packets = [session.packet()]
        errors = []; request = None; later = None

        def reject(operation, call):
            before = session.packet()
            try: call()
            except ContractError as error:
                errors.append(dict(operation=operation, message=str(error), before=before, after=session.packet()))
                require(before == session.packet(), 'Rejected operation changed state')
            else: raise AssertionError('Expected contract rejection: '+name)

        feedback = Feedback('synthetic-feedback-'+name, decision.id, decision.observation_digest,
                            name == 'correct_feedback', False)
        if name == 'frozen_feedback':
            reject('feedback', lambda: session.feedback(feedback))
        else:
            session.feedback(feedback); packets.append(session.packet())
            if name == 'correct_feedback':
                reject('request_revision', lambda: session.request_revision(decision.id))
            else:
                request = session.request_revision(decision.id); packets.append(session.packet())
                if name == 'duplicate_pending':
                    reject('request_revision', lambda: session.request_revision(decision.id))
                if name in ('single_candidate_revision', 'unrequested_edge'):
                    require(request is not None and list(request.edge_ids) == ['e1'], 'Single candidate control')
                    changed = deepcopy(obs); changed['revision'] = request.revision
                    changed['edges'][1]['score'] = -1.0
                    if name == 'unrequested_edge':
                        changed['edges'][0]['score'] = -1.0
                        reject('begin', lambda: session.begin(codec.observation_from(changed), Mode.ADAPT, revision_of=decision.id))
                    else:
                        session.begin(codec.observation_from(changed), Mode.ADAPT, revision_of=decision.id)
                        later = codec.plain(session.complete()); packets.append(session.packet())
        row = dict(name=name, observation=obs, config=config, mode=mode, decision=codec.plain(decision),
                   feedback=codec.plain(feedback), request=codec.plain(request), later=later,
                   packets=packets, errors=errors)
        dump(out/'synthetic'/f'{name}.json', row); rows.append(name)
    dump(out/'validation/selftest.json', dict(passed=rows, synthetic_only=True))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--out', type=Path, required=True)
    main(parser.parse_args().out)
