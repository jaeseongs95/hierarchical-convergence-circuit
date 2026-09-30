"""Independent prefix replay and uninterrupted suffix recurrence verification."""
import argparse
from math import isfinite
from pathlib import Path
import sys
from hcr.codec import plain
from hcr.model import Config
from hcr.evaluation.audit import independent_step
from tools.r050_review_boundary.common import (
    SRC_TREE, TEST_TREE, dump, files, fingerprint, git_tree, load, publish, require, seal, sha, unseal,
)
from tools.r053_feedback.audit import _close
from tools.r057_initial.audit import (
    CONDITIONS, MASK_REMOVALS, FORBIDDEN as OLD_FORBIDDEN, _verify_original_program,
    _require_inventory, _verify_historical_sources, validate_spec as validate_r057_spec,
    verify_record as verify_r057_record, classify_endpoint, initial_contrasts, allocation_comparisons,
)

SPEC_FINGERPRINT = '2c8243e45b366fb8becf0ae2330fe1f835c86ef759f1ecf35ad020ee30c44649'
R057_MANIFEST = 'd9255890b1c931d3ce165c46346ce4214705d0a4ac4db466f6cc7cd8dc3deb6a'
INTERVENTION = dict(trigger='after_first_termination', reset_state=False, reset_stability=False,
                    stop_after_marker=False, fixed_horizon=512)
FORBIDDEN = OLD_FORBIDDEN | {'tools.r058_horizon.worker'}


def validate_spec(spec):
    require(fingerprint(spec) == SPEC_FINGERPRINT, 'Exact R058 frozen spec')
    require(spec['conditions'] == list(CONDITIONS.values()), 'Exact R057 conditions')
    require(spec['research_conditions'] == list(CONDITIONS), 'Research matrix')
    require(spec['implementation_validation_conditions'] == ['start_i05', 'goal_i05'], 'Smoke matrix')
    require(spec['bridge_conditions'] == list(CONDITIONS)
            and spec['anchor_condition_map'] == {c:c for c in CONDITIONS}, 'Bridge matrix')
    require(len(spec['parent_files']) == 10 and len(spec['anchor_files']) == 16, 'Evidence counts')
    require(spec['horizon'] == 512 and spec['checkpoint_ticks'] == [160,512]
            and spec['continuation_intervention'] == INTERVENTION, 'Continuation contract')


def prefix_packet(raw):
    """Reconstruct, rather than repair, the producer's claimed original terminal packet."""
    extra = {'first_termination', 'continuation_cost', 'horizon', 'completion', 'continuation_intervention'}
    prefix = {key:value for key,value in raw.items() if key not in extra}
    marker = raw['first_termination']
    require(set(marker) == {'final_state','convergence','cost'}, 'First termination fields')
    length = marker['convergence']['ticks']
    require(type(length) is int and 0 < length <= 160, 'Original terminal tick bound')
    prefix.update(schema='hcc-r057-kernel-v1', termination_scope='counterfactual_kernel_termination',
                  ticks=raw['ticks'][:length], **marker)
    return seal(prefix)


def band(goal):
    require(type(goal) in (int,float) and isfinite(goal), 'Finite goal')
    return 'low' if goal < .5-1e-6 else 'high' if goal > .5+1e-6 else 'inconclusive'


def checkpoint(tick, config):
    # Assessment at this fixed tick, not a new first-termination claim.
    stable = tick['stable_steps'] >= config['patience']
    return dict(tick=tick['tick'], state=tick['state'], residual=tick['residual'],
                stable_steps=tick['stable_steps'], stable_at_checkpoint=stable,
                goal_band=band(tick['state']['goal']),
                stable_regime=band(tick['state']['goal']) if stable else 'inconclusive')


def verify_record(packet, condition, mask, original, parent_sha, config):
    raw = unseal(packet, 'hcc-r058-kernel-v1')
    require(raw['continuation_intervention'] == INTERVENTION
            and raw['horizon'] == 512 and type(raw['horizon']) is int
            and raw['completion'] == 'fixed_horizon_completed'
            and raw['termination_scope'] == 'counterfactual_fixed_horizon', 'Continuation metadata')
    prefix = prefix_packet(raw)
    row = verify_r057_record(prefix, condition, mask, original, parent_sha, config)
    marker = raw['first_termination']
    count = marker['convergence']['ticks']
    require(isinstance(raw['ticks'],list) and len(raw['ticks']) == 512, 'Fixed horizon tick count')
    cfg = Config(**config)
    state, stable = dict(marker['final_state']), marker['convergence']['stable_steps']
    for number, observed in enumerate(raw['ticks'][count:], count+1):
        require(set(observed) == {'tick','state','residual','stable_steps'}
                and type(observed['tick']) is int and observed['tick'] == number, 'Suffix sequence')
        nxt = independent_step(raw['program'], state, raw['drives'], cfg, True)
        residual = max(abs(nxt[key]-state[key]) for key in state)
        stable = stable+1 if residual <= cfg.residual_tolerance else 0
        require(_close(nxt,observed['state']) and _close(residual,observed['residual']),
                'Independent suffix recurrence/residual')
        require(type(observed['stable_steps']) is int and observed['stable_steps'] == stable,
                'Stable counter reset or mismatch')
        state = dict(observed['state'])
    require(_close(raw['final_state'],state), 'Horizon final state')
    expected = dict(kernel_ticks=512, group_updates=512*len(raw['program']['groups']),
                    normalization_ops=512*len(raw['program']['groups']),
                    signal_transmissions=512*len(raw['program']['links']))
    require(raw['cost'] == expected and all(type(v) is int for v in raw['cost'].values()), 'Total cost')
    suffix_cost = {key:value-marker['cost'][key] for key,value in expected.items()}
    require(raw['continuation_cost'] == suffix_cost
            and all(type(v) is int for v in raw['continuation_cost'].values()), 'Continuation cost')
    marker_regime = classify_endpoint(marker['final_state']['goal'],marker['convergence']['status'])
    suffix = raw['ticks'][count:]
    mismatches = [t['tick'] for t in suffix if band(t['state']['goal']) != marker_regime]
    eligible = marker_regime in ('low','high')
    checkpoints = {str(n):checkpoint(raw['ticks'][n-1],config) for n in (160,512)}
    return dict(condition=row['condition'], orientation=row['orientation'],
        initial_activation=row['initial_activation'], input_pair=row['input_pair'], mask=row['mask'],
        first_termination=marker, checkpoints=checkpoints, cost=expected, continuation_cost=suffix_cost,
        marker_regime=marker_regime,
        postmarker_band_preserved=not mismatches if eligible else None,
        postmarker_nonmatching_ticks=len(mismatches) if eligible else None,
        first_nonmatching_tick=(mismatches[0] if mismatches else None) if eligible else None,
        postmarker_max_residual=max(t['residual'] for t in suffix),
        postmarker_max_state_drift=max(abs(t['state'][key]-marker['final_state'][key])
                                      for t in suffix for key in marker['final_state']),
        postmarker_min_stable_steps=min(t['stable_steps'] for t in suffix))


def verify_anchors(run,spec,config,original):
    root=run/'anchors'
    _require_inventory(root,spec['anchor_files'],'R057 anchor inventory/hash')
    packet=load(root/'plan.json');plan=unseal(packet,'hcc-r057-plan-v1')
    validate_r057_spec(plan['spec'])
    source=load(root/'source_manifest.json')
    require(source['schema']=='hcc-r057-source-manifest-v1'
            and plan['source_manifest_sha256']==sha((root/'source_manifest.json').read_bytes()),'Anchor source binding')
    require(plan['purpose']=='research' and plan['automatic_retry'] is False
            and plan['config']==config and plan['spec']['parent_files']==spec['parent_files'],'Anchor plan binding')
    manifest=load(root/'raw_manifest.json');audit=load(root/'analysis/audit.json')
    require(manifest['schema']=='hcc-r057-raw-manifest-v1' and audit['schema']=='hcc-r057-audit-v1'
            and audit['verified'] is True and audit['research_experiment'] is True
            and audit['plan_sha256']==packet['sha256'],'Anchor manifest/audit binding')
    audited={(r['condition'],r['mask']):r for r in audit['rows']}
    records={};parent_sha=sha((run/'parents'/spec['program_parent']).read_bytes())
    for name,condition in CONDITIONS.items():
        for mask,removed in MASK_REMOVALS.items():
            path=f'study/{name}/{mask}.json'
            require(manifest['files'][f'{name}/{mask}.json']==spec['anchor_files'][path],'Anchor raw binding')
            raw=load(root/path)
            row=verify_r057_record(raw,condition,dict(id=mask,remove=list(removed)),original,parent_sha,config)
            require(_close(row,audited[(name,mask)]),'Anchor audited row')
            records[(name,mask)]=unseal(raw,'hcc-r057-kernel-v1')
    return records


def snapshot_rows(rows,point):
    result=[]
    for row in rows:
        metadata={k:row[k] for k in ('condition','mask','orientation','initial_activation','input_pair')}
        if point=='marker':
            state=row['first_termination']['final_state'];status=row['first_termination']['convergence']['status']
        else:
            snapshot=row['checkpoints'][point];state=snapshot['state']
            status='stable_decision' if snapshot['stable_at_checkpoint'] else 'not_stable_at_checkpoint'
        result.append(dict(**metadata,final_state=state,convergence={'status':status},cost={}))
    return result


def audit(run):
    source=load(run/'source_manifest.json')
    require(source['schema']=='hcc-r058-source-manifest-v1','Source schema')
    _require_inventory(run/'source',source['files'],'Frozen source inventory/hash')
    require(git_tree(run/'source/src')==SRC_TREE and git_tree(run/'source/tests')==TEST_TREE,'Protected trees')
    _verify_historical_sources(run/'source')
    manifest=run/'source/R057_MANIFEST.json'
    require(sha(manifest.read_bytes().replace(b'\r\n',b'\n'))==R057_MANIFEST,'Historical R057 manifest')
    for name,digest in load(manifest)['files'].items():
        require(sha((run/'source'/name).read_bytes().replace(b'\r\n',b'\n'))==digest,'Historical R057 source')
    packet=load(run/'plan.json');plan=unseal(packet,'hcc-r058-plan-v1');spec=plan['spec']
    require(plan['source_manifest_sha256']==sha((run/'source_manifest.json').read_bytes())
            and plan['automatic_retry'] is False and plan['config']==plain(Config()),'Plan binding')
    require(spec==load(run/'source/experiments/exp-39-fixed-horizon/frozen_spec.json'),'Frozen spec binding')
    validate_spec(spec)
    require(plan['purpose'] in ('research','implementation_validation'),'Purpose')
    research=plan['purpose']=='research'
    names=spec['research_conditions'] if research else spec['implementation_validation_conditions']
    rawroot=run/('study' if research else 'smoke');rawmanifest=load(run/'raw_manifest.json')
    require(rawmanifest['schema']=='hcc-r058-raw-manifest-v1','Raw manifest schema')
    _require_inventory(rawroot,rawmanifest['files'],'Raw inventory/hash')
    require(set(rawmanifest['files'])=={f'{c}/{m}.json' for c in names for m in MASK_REMOVALS},'Exact branch inventory')
    original,_=_verify_original_program(run,spec)
    anchors=verify_anchors(run,spec,plan['config'],original)
    parent_sha=sha((run/'parents'/spec['program_parent']).read_bytes());rows=[];bridges=[]
    for name in names:
        for mask,removed in MASK_REMOVALS.items():
            rawpacket=load(rawroot/name/(mask+'.json'))
            rows.append(verify_record(rawpacket,CONDITIONS[name],dict(id=mask,remove=list(removed)),original,parent_sha,plan['config']))
            prefix=unseal(prefix_packet(unseal(rawpacket,'hcc-r058-kernel-v1')),'hcc-r057-kernel-v1')
            require(_close(prefix,anchors[(name,mask)]),'Entire R057 prefix bridge mismatch')
            bridges.append(dict(condition=name,mask=mask,anchor='R057',verified=True))
    contrasts={point:initial_contrasts(snapshot_rows(rows,point)) for point in ('marker','160','512')} if research else {}
    masks={point:allocation_comparisons(snapshot_rows(rows,point)) for point in ('marker','160','512')}
    require(not (FORBIDDEN & set(sys.modules)),'Producer/runtime/session/dynamics imported by auditor')
    return dict(schema='hcc-r058-audit-v1',verified=True,purpose=plan['purpose'],research_experiment=research,
                plan_sha256=packet['sha256'],rows=rows,bridges=bridges,initial_contrasts=contrasts,
                mask_comparisons=masks,native_outcomes_measured=False,independent_samples=False,
                inference_scope=spec['inference_scope'])


def render_summary(report):
    lines=['# EXP-39 / R058 고정 horizon continuation','',f"실행 목적: {report['purpose']}",'',
           '| condition | mask | marker tick | marker goal | goal 160 | goal 512 | residual 512 | band preserved | max state drift |',
           '|---|---|---:|---:|---:|---:|---:|---|---:|']
    for r in report['rows']:
        m=r['first_termination'];a=r['checkpoints']['160'];b=r['checkpoints']['512']
        lines.append('| '+' | '.join(map(str,(r['condition'],r['mask'],m['convergence']['ticks'],
            m['final_state']['goal'],a['state']['goal'],b['state']['goal'],b['residual'],
            r['postmarker_band_preserved'],r['postmarker_max_state_drift'])))+' |')
    lines+=['',f"R057 최초 종료까지 전체 packet bridge {len(report['bridges'])}개 통과.",
            'band preserved는 최초 종료 뒤 모든 tick의 goal 범주 비교다. 체크포인트 안정성은 audit에 별도로 보존했다.',
            '계산 연장은 명시적 개입이며 최초 종료를 교체하지 않는다. 유한시간 지속성을 무한시간 안정성으로 확장하지 않는다.','']
    return '\n'.join(lines).encode('utf-8')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--run',type=Path,required=True)
    args=parser.parse_args();report=audit(args.run)
    dump(args.run/'analysis/audit.json',report);publish(args.run/'analysis/summary.ko.md',render_summary(report))
    print('VERIFIED:',len(report['rows']),'fixed horizons /',len(report['bridges']),'R057 bridges',flush=True)


if __name__=='__main__':
    main()
