"""Native evaluation only; no world, reference scoring, learning or repair."""
import argparse
from pathlib import Path
from tools.r050_review_boundary.common import dump, load
from tools.r063_formation.worker import execute


def main(out):
    plan = load(out/'plan.json')
    memory = load(out/'parent/memory/3.json')
    for cell in plan['cells']:
        execution = execute(plan, cell, memory, cell['use_circuits'], 'frozen_eval',
            out/'evaluation'/cell['id']/'progress', 'r080-'+cell['id'])
        dump(out/'evaluation'/cell['id']/'inference.json', dict(cell=cell, execution=execution))
        print(cell['id'], execution['stop'], flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--out', type=Path, required=True)
    main(p.parse_args().out)
