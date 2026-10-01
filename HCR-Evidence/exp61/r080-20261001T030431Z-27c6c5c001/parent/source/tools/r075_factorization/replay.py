"""Keep config fixed and intervene on the two evidence drives separately."""
import argparse
from pathlib import Path
from hcr.model import Config
from tools.r050_review_boundary.common import dump, load
from tools.r073_decomposition.replay import inputs as old_inputs, simulate


def inputs(parent, spec, cell):
    data = old_inputs(parent, spec, dict(cell, treatment='evidence_only'))
    data['kernel'] = dict(spec['config']['kernel'])
    data['prior'] = 0.0
    for key in spec['prior_drive_keys']:
        data['drives'][key] = 0.0
    data['drives']['e:0'] = cell['e0_scale'] * spec['e0_score']
    data['drives']['e:1'] = cell['e1_scale'] * cell['score']
    return data


def main(out):
    spec = load(out/'plan.json')
    for cell in spec['cells']:
        data = inputs(out/'parent', spec, cell)
        result = simulate(data['program'], data['initial'], data['drives'],
                          Config(**data['kernel']), data['top_down'])
        dump(out/'replays'/cell['id']/'pool.json', dict(cell=cell, inputs=data, result=result,
             evidence_kind='evaluator_formula_counterfactual', native_selection=None, native_cost=None))
        print(cell['id'], result['convergence']['status'], flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--out', type=Path, required=True)
    main(p.parse_args().out)
