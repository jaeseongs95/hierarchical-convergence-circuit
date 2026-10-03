"""Native generation only. No private world or reference evaluator is loaded."""
import argparse
from pathlib import Path
from hcr import codec
from hcr.circuits import AdaptiveMemory
from tools.r050_review_boundary.common import dump, load
from tools.r063_formation.worker import execute
from tools.r064_retention.worker import consume


def main(out, phase, step=None):
    plan = load(out/'plan.json')
    if phase == 'init':
        dump(out/'memory/0.json', AdaptiveMemory.empty(codec.adaptive_config_from(plan['config'])).document())
    elif phase == 'infer':
        case = plan['training'][step-1]
        e = execute(plan, case, load(out/'memory'/f'{step-1}.json'), True, 'train',
                    out/'training'/str(step)/'progress', 'r077-train-'+case['id'])
        dump(out/'training'/str(step)/'inference.json', e)
    elif phase == 'learn':
        base = out/'training'/str(step)
        result = consume(load(base/'inference.json'), load(base/'reference.json'),
                         load(out/'memory'/f'{step-1}.json'))
        result['schema'] = 'hcc-r064-learning-v1'
        dump(base/'learning.json', result)
        dump(out/'memory'/f'{step}.json', result['memory_after'])
    else:
        memory = load(out/'memory'/f"{len(plan['training'])}.json")
        for cell in plan['cells']:
            e = execute(plan, cell, memory, cell['use_circuits'], 'frozen_eval',
                        out/'evaluation'/cell['id']/'progress', 'r077-'+cell['id'])
            dump(out/'evaluation'/cell['id']/'inference.json', dict(cell=cell, execution=e))
            print(cell['id'], e['stop'], flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--out', type=Path, required=True)
    p.add_argument('--phase', choices=['init', 'infer', 'learn', 'eval'], required=True)
    p.add_argument('--step', type=int)
    a = p.parse_args(); main(a.out, a.phase, a.step)
