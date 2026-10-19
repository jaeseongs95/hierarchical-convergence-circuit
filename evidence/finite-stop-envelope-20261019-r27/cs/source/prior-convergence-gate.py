"""같은 실수 모델의 두 인증 상태를 잔차·수축률 거리 gate에 결속한다. Git 조작은 별도다."""
import argparse
from datetime import datetime,timedelta,timezone
from fractions import Fraction as Q
import hashlib,json,os
from pathlib import Path
import subprocess,sys

def pinned(repo,ref):
 data=(repo/ref['path']).read_bytes()
 if len(data)!=ref['bytes'] or hashlib.sha256(data).hexdigest()!=ref['sha256']:raise ValueError('source hash/bytes mismatch')
 return data
def grid(value,places):
 n=value*10**places
 if n.denominator!=1:raise ValueError('geometry not exactly representable on fixedgrid')
 whole,fraction=divmod(abs(n.numerator),10**places)
 return ('-' if n<0 else '')+f'{whole}.{fraction:0{places}d}'
def atomic(path,obj):
 path=Path(path);temporary=path.with_name(path.name+'.writing')
 if path.exists() or temporary.exists():raise ValueError('immutable output exists')
 with temporary.open('x',encoding='utf-8',newline='\n') as f:
  json.dump(obj,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())
 temporary.rename(path)
def main(args):
 start=datetime.now(timezone.utc);deadline=start+timedelta(seconds=180)
 def guard():
  remaining=(deadline-datetime.now(timezone.utc)).total_seconds()
  if not 0<remaining<=180:raise ValueError('absolute180s wallbudget exhausted orclock inconsistent')
  return remaining
 repo=Path(args.repo).resolve();data=Path(args.protocol).read_bytes()
 if hashlib.sha256(data).hexdigest()!=args.protocol_sha256:raise ValueError('protocol hash mismatch')
 proto=json.loads(data);refs={r['path']:r for r in proto['sources']}
 for ref in proto['sources']:guard();pinned(repo,ref)
 cases=[]
 for case in proto['cases']:
  record=json.loads(pinned(repo,refs[case['record']]))
  entries=[entry for entry in record['proposal']['suffix'] if entry['tick']==case['tick']]
  if len(entries)!=1:raise ValueError('case tick notunique inaccepteddependency')
  B=entries[0]['x_box'];radius=Q(proto['region']['radius_x_exact']);centers=[(Q(lo)+Q(hi))/2 for lo,hi in B]
  C={'lower':[grid(c-radius,31) for c in centers],'upper':[grid(c+radius,31) for c in centers],'weights':[1]*7}
  cases.append({'id':case['id'],'tick':case['tick'],'record_pin':refs[case['record']],'x_box':B,'region':C})
 proposal={'schema':'HCCONConvergenceGateProposal.v1','protocol_sha256':args.protocol_sha256,
 'sample_id':proto['sample_id'],'score_hex':proto['score_hex'],'drive_hex':proto['drive_hex'],'cases':cases}
 atomic(args.output,proposal);guard()
 print('Two fixedwhole7 boxes bound; no newtrajectory/native/census replay',flush=True)
 if args.verify_output:
  argv=[sys.executable,'-B','-X','utf8',str(Path(__file__).with_name('check_on_convergence_gate.py')),
   '--repo',str(repo),'--protocol',args.protocol,'--protocol-sha256',args.protocol_sha256,
   '--input',args.output,'--output',args.verify_output,'--remaining-seconds',str(guard())]
  r=subprocess.run(argv,timeout=guard());guard()
  if r.returncode:raise SystemExit(r.returncode)
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 for name in ('repo','protocol','protocol-sha256','output'):p.add_argument('--'+name,required=True)
 p.add_argument('--verify-output');main(p.parse_args())
