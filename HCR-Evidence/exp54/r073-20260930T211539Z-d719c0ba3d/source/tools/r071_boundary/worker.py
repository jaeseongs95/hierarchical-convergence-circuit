"""Native execution and exact feedback consumption; no authored-world access."""
import argparse
from pathlib import Path
from hcr import codec
from hcr.circuits import AdaptiveMemory
from tools.r050_review_boundary.common import dump, load
from tools.r063_formation.worker import execute
from tools.r064_retention.worker import consume


def main(out, phase, arm, step):
    spec = load(out/'plan.json')
    plan = dict(config=spec['configs'][arm], limits=spec['limits'])
    base = out/'arms'/arm
    if phase == 'init':
        dump(base/'memory/0.json', AdaptiveMemory.empty(codec.adaptive_config_from(plan['config'])).document())
    elif phase == 'infer':
        case = spec['recipe'][step-1]
        e = execute(plan, case, load(base/'memory'/f'{step-1}.json'), True, case['mode'],
                    base/'recipe'/str(step)/'progress', 'r071-'+arm+'-'+case['id'])
        dump(base/'recipe'/str(step)/'inference.json', e)
    elif phase == 'learn':
        where = base/'recipe'/str(step)
        result = consume(load(where/'inference.json'), load(where/'reference.json'),
                         load(base/'memory'/f'{step-1}.json'))
        result['schema'] = 'hcc-r064-learning-v1'
        dump(where/'learning.json', result)
        dump(base/'memory'/f'{step}.json', result['memory_after'])
    else:
        for label, index in spec['checkpoints'].items():
            identity = arm+'-'+label
            e = execute(plan, dict(observation=spec['observation']), load(base/'memory'/f'{index}.json'),
                        True, 'adapt', out/'evaluation'/identity/'progress', 'r071-'+identity)
            dump(out/'evaluation'/identity/'inference.json', dict(arm=arm, checkpoint=label, execution=e))
            print(identity, e['stop'], flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--out', type=Path, required=True)
    p.add_argument('--phase', choices=['init','infer','learn','eval'], required=True)
    p.add_argument('--arm', choices=['default','midpoint'], required=True); p.add_argument('--step', type=int)
    a = p.parse_args(); main(a.out, a.phase, a.arm, a.step)
