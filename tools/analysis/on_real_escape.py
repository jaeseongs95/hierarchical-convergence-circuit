"""같은 입력의 실수 continuation 후보와 고정 묶음 검산을 실행한다. Git 조작은 별도다."""
import argparse
from datetime import datetime,timedelta,timezone
from decimal import Decimal,Context,ROUND_FLOOR,ROUND_CEILING
import hashlib,json,os
from pathlib import Path
import runpy,subprocess,sys,time

def digest(data):return hashlib.sha256(data).hexdigest()
def pin(path):
 p=Path(path);data=p.read_bytes();return {'path':str(p),'sha256':digest(data),'bytes':len(data)}
def atomic(path,obj):
 p=Path(path);temp=p.with_name(p.name+'.writing')
 if p.exists() or temp.exists():raise ValueError('immutable output already exists: '+str(p))
 with temp.open('x',encoding='utf-8',newline='\n') as f:
  json.dump(obj,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())
 temp.rename(p)
def pinned(repo,ref):
 data=(repo/ref['path']).read_bytes()
 if len(data)!=ref['bytes'] or digest(data)!=ref['sha256']:raise ValueError('source hash/bytes mismatch')
 return data

def proposal(repo,proto,sha):
 refs={r['path']:r for r in proto['sources']}
 priorref=refs['experiments/exp-62-top-down/on-real-stop-certificates-20261014.json']
 prior=json.loads(pinned(repo,priorref));prefix=prior['proposal']['suffix'][-1]
 if prefix['tick']!=2048:raise ValueError('prior terminal tick mismatch')
 if any(prior['proposal'][k]!=proto[k] for k in ('sample_id','score_hex','drive_hex')):raise ValueError('prior target mismatch')
 raw=json.loads(pinned(repo,{k:proto['raw'][0][k] for k in ('path','sha256','bytes')}))
 events=raw['execution']['packet']['document']['events'];config=events[0]['payload']['config']['kernel']
 net=next(e['payload'] for e in events if e['event']=='r02_network' and e['payload']['network_id']=='network-8')
 helper=runpy.run_path(str(repo/'tools/analysis/on_fixed_points.py'))
 P,A,M=helper['point'],helper['add'],helper['mul'];D=Decimal.from_float
 order=proto['state_order'];drives=dict(net['drives'],**{'e:1':float.fromhex(proto['drive_hex'])})
 b=[A(P(D(g['bias'])),P(D(drives.get(g['id'],0)))) for g in net['program']['groups']]
 G=[[P(0) for _ in order] for _ in order]
 for edge in net['program']['links']:
  i,j=order.index(edge['target']),order.index(edge['source']);G[i][j]=A(G[i][j],P(D(edge['weight'])))
 diag=helper['div'](A(P(D(config['self_excitation'])),P(D(config['inhibition']))),P(2))
 for i in range(7):G[i][i]=A(G[i][i],diag)
 d=P(D(config['damping']));keep=A(P(1),helper['neg'](d))
 unit=Decimal('1e-30');down=Context(prec=80,rounding=ROUND_FLOOR);up=Context(prec=80,rounding=ROUND_CEILING)
 box=[(Decimal(lo),Decimal(hi)) for lo,hi in prefix['x_box']];suffix=[]
 for n in range(2049,6145):
  guard()
  z=helper['preactivation'](b,G,box);h=[helper['tanh_interval'](v) for v in z]
  image=[A(M(keep,x),M(d,v)) for x,v in zip(box,h)]
  encoded=[[format(down.quantize(lo,unit),'f'),format(up.quantize(hi,unit),'f')] for lo,hi in image]
  suffix.append({'tick':n,'x_box':encoded});box=[(Decimal(lo),Decimal(hi)) for lo,hi in encoded]
 center=[down.divide(down.add(lo,hi),Decimal(2)) for lo,hi in box];radius=Decimal('1e-6');rootunit=Decimal('1e-31')
 root={'lower':[format(down.quantize(down.subtract(c,radius),rootunit),'f') for c in center],
       'upper':[format(up.quantize(up.add(c,radius),rootunit),'f') for c in center],'weights':[1]*7}
 return {'schema':'HCCONRealEscapeProposal.v1','protocol_sha256':sha,'sample_id':proto['sample_id'],
  'score_hex':proto['score_hex'],'drive_hex':proto['drive_hex'],'prefix_pin':priorref,'prefix_end_x_box':prefix['x_box'],'suffix':suffix,'root_box':root}

def main(args):
 global guard
 repo=Path(args.repo).resolve();data=Path(args.protocol).read_bytes()
 if digest(data)!=args.protocol_sha256:raise ValueError('protocol hash mismatch')
 proto=json.loads(data)
 for ref in proto['sources']:pinned(repo,ref)
 output=Path(args.output).resolve();statepath=output.with_name(output.name+'.run.json')
 checker=Path(__file__).with_name('check_on_real_escape.py')
 identity={'protocol_sha256':args.protocol_sha256,'producer_pin':pin(__file__),'checker_pin':pin(checker)}
 if args.resume:
  state=json.loads(statepath.read_bytes())
  if state['identity']!=identity:raise ValueError('resume code/input mismatch')
 else:
  started=datetime.now(timezone.utc)
  state={'schema':'HCCONRealEscapeRun.v1','identity':identity,'started_utc':started.isoformat(),
   'deadline_utc':(started+timedelta(seconds=1800)).isoformat(),'resume_policy':'only committed success and neverstartednextchunk; no retries'}
  atomic(statepath,state)
 deadline=datetime.fromisoformat(state['deadline_utc'])
 def remaining():return (deadline-datetime.now(timezone.utc)).total_seconds()
 def guard():
  if not 0<remaining()<=1800:raise ValueError('absolute1800s deadline exhausted or clock inconsistent')
 guard()
 proposalpin=output.with_name(output.name+'.pin.json')
 if args.resume:
  if not output.exists() or not proposalpin.exists():raise ValueError('interrupted proposal is INCOMPLETE; no retry')
  frozen=json.loads(proposalpin.read_bytes())
  if frozen['identity']!=identity or frozen['proposal_pin']!=pin(output):raise ValueError('resume immutable proposal mismatch')
 else:
  atomic(output,proposal(repo,proto,args.protocol_sha256))
  atomic(proposalpin,{'identity':identity,'proposal_pin':pin(output)})
 inputpin=pin(output)
 if not args.verify_output:
  print('one fixed4096 suffix proposed; native0; sourceproof dependency2048 retained');return
 root=Path(args.verify_output).resolve().with_name(Path(args.verify_output).name+'.chunks');root.mkdir(exist_ok=True)
 observations=[];previous=proto['sources'][[r['path'] for r in proto['sources']].index('experiments/exp-62-top-down/on-real-stop-certificates-20261014.json')]['sha256']
 for i in range(64):
  guard()
  for ref in proto['sources']:pinned(repo,ref)
  if identity['producer_pin']!=pin(__file__) or identity['checker_pin']!=pin(checker) or inputpin!=pin(output):raise ValueError('live code/candidate changed')
  started=root/f'chunk-{i:02d}.started.json';receipt=root/f'chunk-{i:02d}.receipt.json';journal=root/f'chunk-{i:02d}.observed.json'
  argv=[sys.executable,'-B','-X','utf8',str(checker),'--repo',str(repo),'--protocol',args.protocol,
   '--protocol-sha256',args.protocol_sha256,'--input',str(output),'--output',str(receipt),
   '--chunk-index',str(i),'--previous-receipt-sha256',previous,'--remaining-seconds',str(remaining())]
  if journal.exists():
   if not args.resume:raise ValueError('existing receipt without resume')
   obs=json.loads(journal.read_bytes())
   if obs['index']!=i or obs['exit_code']!=0 or obs['execution_observed'] is not True or obs['receipt']!=pin(receipt) or obs['input_pin']!=inputpin or obs['identity']!=identity:raise ValueError('resume observed receipt pin mismatch')
  else:
   if started.exists() or receipt.exists():raise ValueError('started uncommitted chunk INCOMPLETE; no retry')
   atomic(started,{'index':i,'input_pin':inputpin,'identity':identity,'previous_receipt_sha256':previous,'argv':argv})
   before=time.monotonic()
   try:r=subprocess.run(argv,capture_output=True,encoding='utf-8',timeout=min(60,remaining()))
   except subprocess.TimeoutExpired as e:
    atomic(root/f'chunk-{i:02d}.failed.json',{'index':i,'status':'TIMED_OUT','argv':argv,'stdout':str(e.stdout),'stderr':str(e.stderr)});raise
   obs={'index':i,'argv':argv,'exit_code':r.returncode,'stdout':r.stdout,'stderr':r.stderr,
    'execution_observed':True,'input_pin':inputpin,'identity':identity,'elapsed_seconds':time.monotonic()-before}
   if r.returncode:
    atomic(root/f'chunk-{i:02d}.failed.json',obs);raise ValueError('first chunk failure preserved: '+str(i))
   checked=json.loads(receipt.read_bytes())
   if checked.get('accepted') is not True or checked.get('chunk_index')!=i:raise ValueError('child result not accepted')
   obs['receipt']=pin(receipt);atomic(journal,obs)
  observations.append(obs);previous=obs['receipt']['sha256']
  print(f'committed chunk {i+1}/64: {2049+64*i}..{2112+64*i}',flush=True)
 guard();ledger=root/'complete-ledger.json'
 doc={'schema':'HCCONRealEscapeExecutionLedger.v1','protocol_sha256':args.protocol_sha256,'proposal_sha256':inputpin['sha256'],
  'deadline_utc':state['deadline_utc'],'producer_pin':identity['producer_pin'],'checker_pin':identity['checker_pin'],'observations':observations}
 if ledger.exists():
  if not args.resume or json.loads(ledger.read_bytes())!=doc:raise ValueError('ledger mismatch')
 else:atomic(ledger,doc)
 final=Path(args.verify_output).resolve();marker=root/'final.started.json'
 if marker.exists() or final.exists():raise ValueError('final already started; no retry')
 argv=[sys.executable,'-B','-X','utf8',str(checker),'--repo',str(repo),'--protocol',args.protocol,
 '--protocol-sha256',args.protocol_sha256,'--input',str(output),'--output',str(final),'--receipts',str(ledger),'--remaining-seconds',str(remaining())]
 atomic(marker,{'argv':argv,'ledger_pin':pin(ledger)})
 r=subprocess.run(argv,capture_output=True,encoding='utf-8',timeout=min(60,remaining()));guard()
 atomic(root/'final.observed.json',{'argv':argv,'exit_code':r.returncode,'stdout':r.stdout,'stderr':r.stderr,'execution_observed':True,'ledger_pin':pin(ledger)})
 print(r.stdout,flush=True)
 if r.returncode:raise SystemExit(r.returncode)

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 for name in ('repo','protocol','protocol-sha256','output'):p.add_argument('--'+name,required=True)
 p.add_argument('--verify-output');p.add_argument('--resume',action='store_true')
 main(p.parse_args())
