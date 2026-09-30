"""Reference fixture checks only; never counted as native research executions."""
import argparse
from pathlib import Path
from hcr import codec
from hcr.evaluation.reference import reachable
from tools.r050_review_boundary.common import dump, load, require
from .verify import prediction


def main(out):
    plan = load(out/'plan.json'); world = load(out/'source'/plan['world_file'])
    obs = codec.observation_from(plan['observation'])
    require(world == dict(e0=True,e1=False), 'Frozen toy world')
    require(reachable(obs,world) is False, 'World is blocked despite misleading positive score')
    require(reachable(obs,dict(e0=True,e1=True)) is True, 'Alternate world is reachable')
    require(plan['observation']['edges'][0]['score']==1.0 and plan['observation']['edges'][1]['score']==.8,
            'Exactly one less-certain edge')
    require(len(plan['cells'])==6 and len({c['id'] for c in plan['cells']})==6, 'Six distinct paired branches')
    require(prediction(None,True)=='not_evaluable' and prediction(True,True,False)=='not_evaluable',
            'Missing judgment/execution is not a falsified prediction')
    require(prediction(False,False)=='supported' and prediction(False,True)=='falsified', 'Observed prediction comparison')
    dump(out/'validation/selftest.json',dict(passed=['blocked_world','alternate_world','one_weak_edge','six_cells','prediction_boundaries'],
        synthetic_only=True,native_executions=0))


if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);main(p.parse_args().out)
