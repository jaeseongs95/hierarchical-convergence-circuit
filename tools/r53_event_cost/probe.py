"""R53 / EXP-99: recount circuit-reuse cost with a send-on-delta (event) executor.

Research harness around the unchanged AdaptiveEngine.  Design, predictions and decision rules:
experiments/exp-99-event-cost/DESIGN.ko.md
"""
import argparse
import copy
import hashlib
import json
import platform
import sys
import time
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
EXP = ROOT / 'experiments/exp-99-event-cost'

from tools.r53_event_cost.core import decision_outcome, event_settle, pool_outcome  # noqa: E402


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require(ok, message):
    if not ok:
        raise ValueError(message)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)


def key(theta):
    return repr(float(theta))


def infer(engine, obs, mode, cfg, thetas):
    """One native inference, then every recorded network re-run by the event executor at each theta."""
    kernel = asdict(cfg.kernel)
    start = len(engine.trace.records)
    decision = engine.infer(obs, mode)
    nets, order, applied = {}, [], []
    for r in engine.trace.records[start:]:
        p = r['payload']
        if r['event'] == 'r02_network':
            nets[p['network_id']] = dict(payload=p, states=[], settled=None)
            order.append(p['network_id'])
        elif r['event'] == 'r02_tick':
            nets[p['network_id']]['states'].append(p['state'])
        elif r['event'] == 'r02_settled':
            nets[p['network_id']]['settled'] = p
        elif r['event'] == 'r02_expansion' and p['candidate']['source'] == 'circuit':
            applied.append(list(p['candidate']['edges']))
    networks = []
    for n in order:
        p, native = nets[n]['payload'], nets[n]['settled']
        outcome = (lambda r: pool_outcome(r, p['metadata']['candidates'], cfg.activation_threshold, cfg.mismatch_threshold)) if p['kind'] == 'pool' else decision_outcome
        native_result = dict(state=native['state'], status=native['convergence']['status'])
        row = dict(kind=p['kind'], groups=len(p['program']['groups']), links=len([l for l in p['program']['links'] if p['top_down'] or l['kind'] != 'top_down']),
                   ticks=native['convergence']['ticks'], native_outcome=outcome(native_result), by_theta={})
        for theta in thetas:
            r = event_settle(p['program'], p['drives'], kernel, p['top_down'], theta)
            entry = dict(link_events=r['link_events'], group_updates=r['group_updates'], ticks=r['ticks'], preserved=outcome(r) == row['native_outcome'],
                         max_state_abs_diff=max(abs(r['state'][g] - native['state'][g]) for g in native['state']))
            if theta == 0:
                entry['bitwise_trajectory'] = r['states'] == nets[n]['states'] and r['ticks'] == row['ticks'] and r['status'] == native['convergence']['status']
                require(r['dense_link_events'] == row['links'] * row['ticks'], 'dense link count')
            row['by_theta'][key(theta)] = entry
        networks.append(row)
    require(sum(n['ticks'] for n in networks) == decision.cost['kernel_ticks'], 'per-network ticks add up to the cost counter')
    require(sum(n['links'] * n['ticks'] for n in networks) == decision.cost['signal_transmissions'], 'dense link count equals native signal_transmissions')
    require(sum(n['groups'] * n['ticks'] for n in networks) == decision.cost['group_updates'], 'dense group count equals native group_updates')
    totals = {}
    for theta in thetas:
        t = key(theta)
        totals[t] = dict(link_events=sum(n['by_theta'][t]['link_events'] for n in networks), group_updates=sum(n['by_theta'][t]['group_updates'] for n in networks),
                         pool_link_events=sum(n['by_theta'][t]['link_events'] for n in networks if n['kind'] == 'pool'),
                         pool_group_updates=sum(n['by_theta'][t]['group_updates'] for n in networks if n['kind'] == 'pool'),
                         preserved=all(n['by_theta'][t]['preserved'] for n in networks))
    row = dict(value=decision.value, status=decision.convergence.status.value, applied=applied, expansions=decision.cost['expansions'], pool_calls=decision.cost['pool_calls'],
               ticks_total=decision.cost['kernel_ticks'], ticks_pool=sum(n['ticks'] for n in networks if n['kind'] == 'pool'),
               dense_link_events=decision.cost['signal_transmissions'], dense_group_updates=decision.cost['group_updates'], networks=networks, totals=totals)
    return decision, row


def feedback(engine, decision, obs, name):
    from hcr.model import Feedback
    engine.feedback(Feedback(name, decision.id, obs.digest, decision.value is True, decision.proof.under_assumptions_valid))


def part_a(cfg, spec, thetas):
    from hcr import codec
    from hcr.circuits import AdaptiveMemory
    from hcr.model import Mode
    from hcr.runtime import AdaptiveEngine
    a = spec['part_a']
    source = read(ROOT / a['source'])['research']
    trainer = AdaptiveEngine(cfg, judgment_prior=a['policy'])
    memories = {0: copy.deepcopy(trainer.memory.document())}
    training = []
    for i, case in enumerate(source['training'], 1):
        obs = codec.observation_from(case['observation'])
        decision, row = infer(trainer, obs, Mode(a['training_mode']), cfg, thetas)
        feedback(trainer, decision, obs, 'r53-a-fb-%d' % i)
        training.append(dict(id=case['id'], **row))
    memories[3] = copy.deepcopy(trainer.memory.document())
    circuits = memories[3]['circuits']
    require(len(circuits) == a['anchors']['circuits'] and circuits[0]['strength'] == a['anchors']['strength'], 'EXP-44 anchor: one circuit at strength 0.55')
    rows = []
    for n in a['memories']:
        for gate in a['use_circuits']:
            for case in source['cases']:
                engine = AdaptiveEngine(cfg, AdaptiveMemory.from_document(copy.deepcopy(memories[n]), cfg), use_circuits=gate, judgment_prior=a['policy'])
                _, row = infer(engine, codec.observation_from(case['observation']), Mode.FROZEN_EVAL, cfg, thetas)
                rows.append(dict(case=case['id'], memory=n, use_circuits=gate, **row))
    for case, (off, on) in a['anchors']['post_ticks_off_on'].items():
        got = [next(r['ticks_total'] for r in rows if r['case'] == case and r['memory'] == 3 and r['use_circuits'] is g) for g in (False, True)]
        require(got == [off, on], 'EXP-44 anchor ticks for ' + case)
    return memories, training, rows


def part_b(cfg, spec, thetas):
    from hcr.model import Mode
    from hcr.runtime import AdaptiveEngine
    from hcr.tasks.toy_world import chain
    b = spec['part_b']
    series = []
    for length in b['lengths']:
        for policy in b['policies']:
            for gate in b['use_circuits']:
                engine = AdaptiveEngine(cfg, use_circuits=gate, judgment_prior=policy)
                name = 'L%d-%s-%s' % (length, policy, 'on' if gate else 'off')
                episodes = []
                for i in range(1, b['episodes'] + 1):
                    obs = chain('r53-b-%s-%02d' % (name, i), (True,) * length, scores=(b['score'],) * length, prefix='b%s%02d' % (name, i)).observation
                    decision, row = infer(engine, obs, Mode(b['mode']), cfg, thetas)
                    feedback(engine, decision, obs, 'r53-b-fb-%s-%02d' % (name, i))
                    doc = engine.memory.document()
                    episodes.append(dict(episode=i, circuits_after=len(doc['circuits']), strengths_after=[c['strength'] for c in doc['circuits']], **row))
                series.append(dict(name=name, length=length, policy=policy, use_circuits=gate, episodes=episodes))
    return series


def verdict(ok):
    return 'supported' if ok else 'falsified'


def reading_at(pairs, t, minimum):
    on_ge = sum(1 for p in pairs if p['on']['totals'][t]['link_events'] >= p['off']['totals'][t]['link_events'])
    on_lt = len(pairs) - on_ge
    pool_ge = sum(1 for p in pairs if p['on']['totals'][t]['pool_link_events'] >= p['off']['totals'][t]['link_events'])
    pool_lt = len(pairs) - pool_ge
    if on_lt >= minimum:
        return 'ACCOUNTING_ARTIFACT'
    if on_ge >= minimum and pool_lt >= minimum:
        return 'RECOMPUTATION'
    if on_ge >= minimum and pool_ge >= minimum:
        return 'SELECTION_COST'
    return 'MIXED'


def summarize(spec, memories, rows_a, series, training):
    thetas = [key(t) for t in spec['thetas']]
    every = rows_a + training + [e for s in series for e in s['episodes']]
    preserved = {t: dict(inferences=len(every), preserved=sum(1 for r in every if r['totals'][t]['preserved'])) for t in thetas}
    scope = rows_a + [e for s in series for e in s['episodes']]
    ok = [t for t in thetas if all(r['totals'][t]['preserved'] for r in scope)]
    primary = max(ok, key=float) if ok else thetas[0]
    pairs = [dict(case=c, off=next(r for r in rows_a if r['case'] == c and r['memory'] == 3 and not r['use_circuits']),
                  on=next(r for r in rows_a if r['case'] == c and r['memory'] == 3 and r['use_circuits'])) for c in spec['part_a']['anchors']['post_ticks_off_on']]
    table = []
    for p in pairs:
        entry = dict(case=p['case'], expansions=[p['off']['expansions'], p['on']['expansions']], ticks=[p['off']['ticks_total'], p['on']['ticks_total']],
                     dense_link_events=[p['off']['dense_link_events'], p['on']['dense_link_events']], by_theta={})
        for t in thetas:
            entry['by_theta'][t] = dict(off_link_events=p['off']['totals'][t]['link_events'], on_link_events=p['on']['totals'][t]['link_events'],
                                        on_pool_link_events=p['on']['totals'][t]['pool_link_events'],
                                        off_group_updates=p['off']['totals'][t]['group_updates'], on_group_updates=p['on']['totals'][t]['group_updates'],
                                        on_pool_group_updates=p['on']['totals'][t]['pool_group_updates'],
                                        both_preserved=p['off']['totals'][t]['preserved'] and p['on']['totals'][t]['preserved'])
        table.append(entry)
    networks = [n for r in every for n in r['networks']]
    zero = thetas[0]
    ratios = [n['by_theta'][zero]['link_events'] / (n['links'] * n['ticks']) for n in networks]
    P = {}
    P['P1'] = dict(verdict=verdict(all(n['by_theta'][zero]['bitwise_trajectory'] for n in networks)), networks=len(networks))
    P['P2'] = dict(verdict=verdict(min(ratios) >= spec['p2_min_ratio']), min_ratio=min(ratios), max_ratio=max(ratios))
    all_ok = lambda t: all(r['totals'][t]['preserved'] for r in scope)
    P['P3'] = dict(verdict=verdict(all(all_ok(t) for t in thetas if float(t) <= 1e-3) and not all_ok(key(1e-2))), all_preserved={t: all_ok(t) for t in thetas})
    P['P4'] = dict(verdict=verdict(all(e['by_theta'][primary]['on_link_events'] > e['by_theta'][primary]['off_link_events'] for e in table)))
    P['P5'] = dict(verdict=verdict(sum(1 for e in table if e['by_theta'][primary]['on_pool_link_events'] >= e['by_theta'][primary]['off_link_events']) >= spec['reading_min_pairs']))
    formed = spec['part_b']['formed_after']
    mean = lambda values: sum(values) / len(values)
    b_rows = []
    for s in series:
        ev = [e['totals'][primary]['link_events'] for e in s['episodes']]
        b_rows.append(dict(name=s['name'], length=s['length'], policy=s['policy'], use_circuits=s['use_circuits'], link_events=ev,
                           dense_link_events=[e['dense_link_events'] for e in s['episodes']], ticks=[e['ticks_total'] for e in s['episodes']],
                           expansions=[e['expansions'] for e in s['episodes']], applied=[len(e['applied']) for e in s['episodes']],
                           mean_before=mean(ev[:formed]), mean_after=mean(ev[formed:])))
    p6 = []
    for on in [r for r in b_rows if r['use_circuits']]:
        off = next(r for r in b_rows if not r['use_circuits'] and r['length'] == on['length'] and r['policy'] == on['policy'])
        p6.append(dict(name=on['name'], after_ge_before=on['mean_after'] >= on['mean_before'],
                       on_gt_off_every_episode_after=all(a > b for a, b in zip(on['link_events'][formed:], off['link_events'][formed:]))))
    P['P6'] = dict(verdict=verdict(all(x['after_ge_before'] and x['on_gt_off_every_episode_after'] for x in p6)), series=p6)
    pattern = memories[3]['circuits'][0]['pattern']['program']
    primitive = next(n for n in next(r for r in rows_a if r['case'] == 'renamed-control' and r['memory'] == 0 and not r['use_circuits'])['networks'][::-1] if n['kind'] == 'decision')
    sizes = dict(pattern_groups=len(pattern['groups']), pattern_links=len(pattern['links']), primitive_groups=primitive['groups'], primitive_links=primitive['links'])
    P['P7'] = dict(verdict=verdict(sizes['pattern_groups'] == sizes['primitive_groups'] and sizes['pattern_links'] == sizes['primitive_links']), **sizes)
    minimum = spec['reading_min_pairs']
    return dict(primary_theta=primary, preserved_by_theta=preserved, part_a_post_pairs=table, part_b_series_at_primary=b_rows, predictions=P,
                reading=reading_at(pairs, primary, minimum), reading_by_theta={t: reading_at(pairs, t, minimum) for t in ok},
                event_to_dense_ratio_at_primary=dict(
                    part_a_post_off=[e['by_theta'][primary]['off_link_events'] / e['dense_link_events'][0] for e in table],
                    part_a_post_on=[e['by_theta'][primary]['on_link_events'] / e['dense_link_events'][1] for e in table]))


def run(out, smoke):
    from hcr.model import AdaptiveConfig
    from hcr.tasks.toy_world import World

    def forbidden(*a, **k):
        raise ValueError('R53 world measurement forbidden')
    World.measure = forbidden
    started, cpu0 = time.monotonic(), time.process_time()
    spec = read(EXP / 'frozen_spec.json')
    require(all(sha(ROOT / n) == h for n, h in read(EXP / 'input_manifest.json').items()), 'input SHA pins')
    cfg = AdaptiveConfig()
    thetas = spec['thetas']
    if smoke:
        from hcr import codec
        from hcr.model import Mode
        from hcr.runtime import AdaptiveEngine
        engine = AdaptiveEngine(cfg, judgment_prior='route_only')
        case = read(ROOT / spec['part_a']['source'])['smoke']['training'][0]
        _, row = infer(engine, codec.observation_from(case['observation']), Mode.TRAIN, cfg, [0.0])
        print(canonical(dict(smoke=True, bitwise=all(n['by_theta'][key(0.0)]['bitwise_trajectory'] for n in row['networks']), networks=len(row['networks']))))
        return
    memories, training, rows_a = part_a(cfg, spec, thetas)
    series = part_b(cfg, spec, thetas)
    require(len(rows_a) == spec['expected_counts']['part_a_eval'] and sum(len(s['episodes']) for s in series) == spec['expected_counts']['part_b_inferences'], 'declared counts')
    summary = summarize(spec, memories, rows_a, series, training)
    result = dict(schema='hcr-r53-event-cost-analysis-v1', design_sha256=sha(EXP / 'DESIGN.ko.md'), frozen_spec_sha256=sha(EXP / 'frozen_spec.json'),
                  input_manifest_sha256=sha(EXP / 'input_manifest.json'), config_signature=cfg.signature,
                  memory_after_training_sha256=hashlib.sha256(canonical(memories[3]).encode()).hexdigest(),
                  part_a_training=training, part_a=rows_a, part_b=series, summary=summary, world_measurement=0, revision_requests=0)
    result['rows_sha256'] = hashlib.sha256(canonical([training, rows_a, series]).encode()).hexdigest()
    result['environment'] = dict(python=sys.version, platform=platform.platform(), libc=list(platform.libc_ver()), machine=platform.machine())
    result['cost'] = dict(wall_seconds=time.monotonic() - started, cpu_seconds=time.process_time() - cpu0)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    with (out / 'analysis.json').open('x', encoding='utf-8', newline='\n') as f:
        f.write(json.dumps(result, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n')
    print(canonical(dict(reading=summary['reading'], primary_theta=summary['primary_theta'], predictions={k: v['verdict'] for k, v in summary['predictions'].items()},
                         rows_sha256=result['rows_sha256'], seconds=result['cost']['wall_seconds'])))


if __name__ == '__main__':
    a = argparse.ArgumentParser(description=__doc__)
    a.add_argument('--out', help='new output folder (must not exist)')
    a.add_argument('--smoke', action='store_true', help='one training inference at theta 0; not evidence')
    args = a.parse_args()
    require(sys.version_info >= (3, 12), 'Python 3.12 required')
    require(args.smoke or args.out, '--out required')
    run(args.out, args.smoke)
