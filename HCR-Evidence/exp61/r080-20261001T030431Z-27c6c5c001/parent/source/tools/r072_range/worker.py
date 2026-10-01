"""Fresh native sessions on exact pinned memories; no world or feedback access."""
import argparse
from pathlib import Path
from tools.r050_review_boundary.common import dump, load
from tools.r063_formation.worker import execute


def main(out):
    spec = load(out/'plan.json')
    for cell in spec['cells']:
        plan = dict(config=spec['configs'][cell['arm']], limits=spec['limits'])
        memory = load(out/'parent'/cell['memory_file'])
        e = execute(plan, cell, memory, True, 'adapt',
                    out/'evaluation'/cell['id']/'progress', 'r072-'+cell['id'])
        dump(out/'evaluation'/cell['id']/'inference.json', dict(cell=cell, execution=e))
        print(cell['id'], e['stop'], flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--out', type=Path, required=True)
    main(p.parse_args().out)
