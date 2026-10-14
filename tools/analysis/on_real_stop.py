"""기존 exactreal 160 상자에서 단일점 suffix를 제안한다. --verify-output은 독립 검산기를 호출한다."""
import argparse
from decimal import Decimal, Context, ROUND_FLOOR, ROUND_CEILING
import hashlib
import json
from pathlib import Path
import runpy
import subprocess
import sys
import time


def pinned(repo, ref):
    data=(repo/ref['path']).read_bytes()
    if len(data)!=ref['bytes'] or hashlib.sha256(data).hexdigest()!=ref['sha256']:
        raise ValueError('source hash/bytes mismatch')
    return data


def main(args):
    start=time.monotonic()
    repo=Path(args.repo).resolve();data=Path(args.protocol).read_bytes()
    if hashlib.sha256(data).hexdigest()!=args.protocol_sha256:raise ValueError('protocol hash mismatch')
    proto=json.loads(data)
    bound=proto['budget']['wall_time_seconds_combined']
    def guard():
        if time.monotonic()-start>bound:raise ValueError('combined wall budget exhausted')
    sources={p['path']:p for p in proto['sources']}
    for ref in proto['sources']:pinned(repo,ref)
    prefix_ref=sources['experiments/exp-62-top-down/on-native-stop-certificates-20261014.json']
    prior=json.loads(pinned(repo,prefix_ref))
    sample=next(s for s in prior['proposal']['samples'] if s['id']==proto['sample_id'])
    if sample['score_hex']!=proto['score_hex'] or sample['drive_hex']!=proto['drive_hex']:raise ValueError('prefix sample mismatch')
    raw=json.loads(pinned(repo,{k:proto['raw'][0][k] for k in ('path','sha256','bytes')}))
    events=raw['execution']['packet']['document']['events']
    config=next(e['payload']['config']['kernel'] for e in events if e['event']=='r02_engine_created')
    net=next(e['payload'] for e in events if e['event']=='r02_network' and e['payload']['network_id']==proto['network_id'])
    helper=runpy.run_path(str(repo/'tools/analysis/on_fixed_points.py'))
    P,A,M=helper['point'],helper['add'],helper['mul'];D=Decimal.from_float
    order=proto['state_order'];drive=dict(net['drives'],**{'e:1':float.fromhex(proto['drive_hex'])})
    b=[A(P(D(g['bias'])),P(D(drive.get(g['id'],0.0)))) for g in net['program']['groups']]
    matrix=[[P(0) for _ in order] for _ in order]
    for edge in net['program']['links']:
        i,j=order.index(edge['target']),order.index(edge['source'])
        matrix[i][j]=A(matrix[i][j],P(D(edge['weight'])))
    diagonal=helper['div'](A(P(D(config['self_excitation'])),P(D(config['inhibition']))),P(2))
    for i in range(7):matrix[i][i]=A(matrix[i][i],diagonal)
    damping=P(D(config['damping']));keep=A(P(1),helper['neg'](damping))
    unit=Decimal('1e-30');down=Context(prec=80,rounding=ROUND_FLOOR);up=Context(prec=80,rounding=ROUND_CEILING)
    prefix_end=sample['real_x_boxes'][159]
    box=[(Decimal(lo),Decimal(hi)) for lo,hi in prefix_end];suffix=[]
    for n in range(161,proto['policy']['cap']+1):
        guard()
        z=helper['preactivation'](b,matrix,box)
        image=[helper['tanh_interval'](v) for v in z]
        nxt=[A(M(keep,x),M(damping,h)) for x,h in zip(box,image)]
        encoded=[[format(down.quantize(lo,unit),'f'),format(up.quantize(hi,unit),'f')] for lo,hi in nxt]
        suffix.append({'tick':n,'x_box':encoded});box=[(Decimal(lo),Decimal(hi)) for lo,hi in encoded]
    proposal={'schema':'HCCONRealStopProposal.v1','protocol_sha256':args.protocol_sha256,
        'sample_id':proto['sample_id'],'score_hex':proto['score_hex'],'drive_hex':proto['drive_hex'],
        'prefix_pin':prefix_ref,'prefix_end_x_box':prefix_end,'suffix':suffix}
    with Path(args.output).open('x',encoding='utf-8',newline='\n') as f:json.dump(proposal,f,ensure_ascii=False,indent=2);f.write('\n')
    guard()
    print('1888 suffix boxes proposed; old160 not regenerated; native runs0',flush=True)
    if args.verify_output:
        remaining=bound-(time.monotonic()-start)
        if remaining<=0:raise ValueError('no checker wall budget left')
        argv=[sys.executable,'-B','-X','utf8',str(Path(__file__).with_name('check_on_real_stop.py')),
              '--repo',str(repo),'--protocol',args.protocol,'--protocol-sha256',args.protocol_sha256,
              '--input',args.output,'--output',args.verify_output,'--remaining-seconds',str(remaining)]
        # One entry point shares the frozen wall budget; Git delivery is separate.
        result=subprocess.run(argv,timeout=remaining)
        guard()
        if result.returncode:raise SystemExit(result.returncode)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('repo','protocol','protocol-sha256','output'):parser.add_argument('--'+name,required=True)
    parser.add_argument('--verify-output')
    main(parser.parse_args())
