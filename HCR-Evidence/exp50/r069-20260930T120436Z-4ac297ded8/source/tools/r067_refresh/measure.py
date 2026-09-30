"""Ideal toy observation service. Private worlds stay outside the inference worker."""
import argparse
from itertools import product
from pathlib import Path
from tools.r050_review_boundary.common import dump, fingerprint, load, require, seal


def main(out):
    plan = load(out/'plan.json')
    worlds = load(out/'source/experiments/exp-48-observation-refresh/reference_worlds.json')
    for slot, arm, gate in product(plan['slots'], ('stale','fresh'), (False, True)):
        identity = f"{slot}-{arm}-{'on' if gate else 'off'}"
        request = dict(controller='explicit_baseline', edge_id='e1', source='v1', target='v2',
            scope=plan['fact_scope'], requested_at=1, budget=1, channel='cached' if arm == 'stale' else 'current')
        require(type(worlds[slot]['e1']) is bool, 'Boolean oracle edge')
        response = dict(request=request, delivered_at=1, valid_at=0 if arm == 'stale' else 1,
            source='cached_original' if arm == 'stale' else 'ideal_current_sensor', status='measured',
            score=0.8 if arm == 'stale' else (1.0 if worlds[slot]['e1'] else -1.0))
        dump(out/'measurements'/f'{identity}.json', seal(dict(schema='hcc-r067-response-v1',
            identity=identity, plan_sha256=fingerprint(plan), response=response)))


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--out',type=Path,required=True); main(p.parse_args().out)
