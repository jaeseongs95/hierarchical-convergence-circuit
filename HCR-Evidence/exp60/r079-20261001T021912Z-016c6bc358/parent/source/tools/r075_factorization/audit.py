"""Five-node score effects, separated scale effects, and their interaction."""
import argparse
from dataclasses import replace
from pathlib import Path
import sys
from hcr.model import Config
from tools.r050_review_boundary.common import dump, files, fingerprint, load, require
from tools.r050_review_boundary.audit import FORBIDDEN
from tools.r073_decomposition.replay import simulate
from tools.r075_factorization.replay import inputs


def identity(e0, e1, sid):
    return f'e0-{int(e0)}-e1-{int(e1)}-{sid}'


def check_spec(out):
    s = load(out/'plan.json'); old = load(out/'anchor/plan.json')
    require(s == load(out/'source/experiments/exp-56-drive-factorization/frozen_spec.json'), 'Frozen plan')
    for key in ('config', 'initial', 'top_down', 'program_sha256', 'scores', 'prior_drive_keys',
                'baseline_score', 'e0_score', 'numeric_tolerance', 'direction_tolerance'):
        require(s[key] == old[key], 'Pinned condition: '+key)
    require(s['scales'] == [4.0, 1.0] and s['checkpoints'] == {'M0': 4} and s['prior'] == 0.0, 'Bounded intervention')
    require(s['nodes'] == ['e:0', 'e:1', 'p:0:0', 'p:0:1', 'c:0'], 'Five separate readouts')
    expected = [dict(id=identity(a,b,sid), e0_scale=a, e1_scale=b, checkpoint='M0', score_id=sid, score=score)
                for a in s['scales'] for b in s['scales'] for sid,score in s['scores'].items()]
    require(s['cells'] == expected and len(expected) == 12, 'Exact factorial grid')
    require(s['predictions'] == {'s06':'negative', 's08':'zero', 's10':'positive'}, 'Frozen direction predictions')
    require(s['scale_predictions'] == {'e1_scale':['e:1','c:0'], 'e0_scale':['c:0']}, 'Frozen scale predictions')
    return s


def summarize(s, raws):
    nodes = s['nodes']; tol = s['direction_tolerance']; rows = []; differences = []; deltas = {}
    for c in s['cells']:
        raw = raws[c['id']]; r = raw['result']
        rows.append(dict(c, terminal={n:r['state'][n] for n in nodes}, prior=raw['inputs']['prior'],
                         drives=raw['inputs']['drives'], convergence=r['convergence'], evaluable=r['evaluable'],
                         trajectory_sha256=fingerprint(r['trajectory'])))
        base = raws[identity(c['e0_scale'],c['e1_scale'],'s08')]['result']
        ok = r['evaluable'] and base['evaluable']
        delta = {n:r['state'][n]-base['state'][n] if ok else None for n in nodes}
        directions = {n:('positive' if v>tol else 'negative' if v < -tol else 'zero') if ok else None for n,v in delta.items()}
        predictions = {n:('not_evaluable' if not ok else 'supported' if directions[n]==s['predictions'][c['score_id']] else 'falsified')
                       for n in ('e:1','c:0')}
        row = dict(id=c['id'], evaluable=ok, deltas=delta, directions=directions, predictions=predictions)
        differences.append(row); deltas[c['id']] = row
    pairs = []
    for axis in ('e1_scale','e0_scale'):
        for fixed in s['scales']:
            for sid in ('s06','s10'):
                ids = [identity(fixed,v,sid) if axis=='e1_scale' else identity(v,fixed,sid) for v in s['scales']]
                high, low = [deltas[key] for key in ids]; ok = high['evaluable'] and low['evaluable']
                ratios = {n:abs(low['deltas'][n])/abs(high['deltas'][n]) if ok and abs(high['deltas'][n])>tol else None for n in nodes}
                predictions = {n:('not_evaluable' if not ok else 'supported' if abs(low['deltas'][n])-abs(high['deltas'][n])>tol else 'falsified')
                               for n in s['scale_predictions'][axis]}
                pairs.append(dict(axis=axis, fixed_scale=fixed, score_id=sid, high_id=ids[0], low_id=ids[1], evaluable=ok,
                                  high_deltas=high['deltas'], low_deltas=low['deltas'], absolute_effect_ratios=ratios, predictions=predictions))
    interactions = []
    for sid in ('s06','s10'):
        terms = {f'{a}{b}':deltas[identity(a,b,sid)] for a,b in ((4,4),(4,1),(1,4),(1,1))}
        ok = all(x['evaluable'] for x in terms.values())
        values = {n:terms['11']['deltas'][n]-terms['14']['deltas'][n]-terms['41']['deltas'][n]+terms['44']['deltas'][n] if ok else None for n in nodes}
        interactions.append(dict(score_id=sid, evaluable=ok, signed_score_effect_interaction=values))
    return dict(rows=rows, differences=differences, scale_pairs=pairs, interactions=interactions,
        reanalysis=True, formula_replay_cells=12, prior_replay_correspondences=6, mixed_scale_cells=6,
        new_native_research_executions=0, new_training_executions=0, new_feedback_applications=0,
        new_independent_samples=0, native_expansions=None, native_decision_cost=None,
        actual_energy_joules=None, peak_memory_bytes=None)


def selftest(out):
    s = check_spec(out); d = inputs(out/'parent',s,s['cells'][0]); cfg = Config(**d['kernel'])
    short = simulate(d['program'],d['initial'],d['drives'],replace(cfg,max_ticks=1,patience=1),d['top_down'])
    flat = simulate(dict(groups=[dict(id='c:0',bias=0.0),dict(id='goal',bias=0.0)],links=[]),
                    {'c:0':.5,'goal':.5},{},replace(cfg,self_excitation=0.0,inhibition=0.0),True)
    require(not short['evaluable'] and short['convergence']['status']=='budget_exhausted', 'Budget unknown')
    require(flat['evaluable'] and flat['convergence']['status']=='stable_ambiguous', 'Ambiguity preserved')
    synthetic = {c['id']:dict(result=short,inputs=d) for c in s['cells']}
    report = summarize(s,synthetic)
    require(all(all(v is None for v in row['deltas'].values()) and set(row['predictions'].values())=={'not_evaluable'}
                for row in report['differences']), 'No score effects on budget failure')
    require(all(all(v is None for v in row['absolute_effect_ratios'].values()) for row in report['scale_pairs']), 'No unknown ratios')
    require(all(all(v is None for v in row['signed_score_effect_interaction'].values()) for row in report['interactions']), 'No unknown interaction')
    dump(out/'validation/selftest.json',dict(verified=True,budget_preserved=True,ambiguity_preserved=True,
         unevaluable_summary_preserved=True,research_sample=False,synthetic_native_executions=0))


def main(out,phase):
    if phase == 'selftest':
        selftest(out)
    else:
        s = check_spec(out)
        require(files(out/'replays') == load(out/'raw_manifest.json')['files'], 'Raw manifest')
        raws = {c['id']:load(out/'replays'/c['id']/'pool.json') for c in s['cells']}
        for c in s['cells']:
            raw = raws[c['id']]
            require(raw['cell']==c and raw['inputs']==inputs(out/'parent',s,c), 'Exact cell inputs')
            require(raw['native_selection'] is None and raw['native_cost'] is None, 'Native boundary')
        dump(out/'summary.json',summarize(s,raws))
    require(not FORBIDDEN & set(sys.modules), 'Producer boundary')


if __name__ == '__main__':
    p=argparse.ArgumentParser(); p.add_argument('--out',type=Path,required=True)
    p.add_argument('--phase',choices=['selftest','final'],required=True); a=p.parse_args(); main(a.out,a.phase)
