"""Observe the existing request boundary; never inject feedback into research cells."""
import argparse
from itertools import product
from pathlib import Path
from hcr.model import ContractError
from hcr.sessions import AdaptiveSession
from tools.r050_review_boundary.common import dump, load
from tools.r063_formation.worker import execute


def main(out):
    plan = load(out/'plan.json')
    memory = load(out/'parent/memory/after_correction.json')
    for mode, gate in product(plan['modes'], (False, True)):
        identity = f"{mode}-{'on' if gate else 'off'}"
        where = out/'evaluation'/identity
        execution = execute(plan, dict(observation=plan['observation']), memory, gate,
                            mode, where/'progress', 'r068-'+identity)
        dump(where/'inference.json', execution)
        candidate = execution['candidate']
        if candidate is None:
            result = dict(status='no_completed_candidate', request=None, error=None,
                          before=None, after=None)
        else:
            # Restore the exact finished candidate branch, not a new inference session.
            session = AdaptiveSession.from_packet(candidate['packet'])
            before = session.packet()
            try:
                request = session.request_revision(candidate['decision']['id'])
                from hcr.codec import plain
                result = dict(status='returned', request=plain(request), error=None)
            except ContractError as error:
                result = dict(status='contract_rejected', request=None,
                              error=dict(type=type(error).__name__, message=str(error)))
            result.update(before=before, after=session.packet())
        dump(where/'request_attempt.json', result)
        print(identity, result['status'], flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--out', type=Path, required=True)
    main(parser.parse_args().out)
