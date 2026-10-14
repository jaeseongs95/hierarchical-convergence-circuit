"""현재 상태만 쓰는 지역 수렴 인증의 동결된 실험 입력을 결속한다."""
import argparse
from datetime import datetime,timedelta,timezone
import hashlib,json,os
from pathlib import Path
import subprocess,sys,time
def atomic(path,obj):
 path=Path(path);tmp=path.with_name(path.name+'.writing')
 if path.exists() or tmp.exists():raise ValueError('immutable output already exists')
 with tmp.open('x',encoding='utf-8',newline='\n') as f:
  json.dump(obj,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())
 tmp.rename(path)
def main(args):
 started=time.monotonic();deadline=datetime.now(timezone.utc)+timedelta(seconds=180)
 def remaining():
  wall=(deadline-datetime.now(timezone.utc)).total_seconds();mono=180-(time.monotonic()-started)
  if not 0<wall<=180 or not mono>0:raise ValueError('absolute180 budget exhausted or clock inconsistent')
  return min(wall,mono)
 repo=Path(args.repo).resolve();data=Path(args.protocol).read_bytes()
 if hashlib.sha256(data).hexdigest()!=args.protocol_sha256:raise ValueError('protocol bytes/hash mismatch')
 p=json.loads(data)
 for ref in p['sources']:
  remaining();path=(repo/ref['path']).resolve()
  if not path.is_relative_to(repo):raise ValueError('source outside repository')
  b=path.read_bytes()
  if len(b)!=ref['bytes'] or hashlib.sha256(b).hexdigest()!=ref['sha256']:raise ValueError('source pin mismatch')
 proposal={'schema':'HCCONOnlineConvergenceGateProposal.v1','protocol_sha256':args.protocol_sha256,
  'sample_id':p['sample_id'],'score_hex':p['score_hex'],'drive_hex':p['drive_hex'],
  'ticks':p['ticks'],'radii_x_exact':p['radii_x_exact'],'epsilon_p_exact':p['epsilon_p_exact']}
 atomic(args.output,proposal);remaining()
 print('5ticks/2radii/2bounds proposed; localcertificate nofutureanchor inputs',flush=True)
 if args.verify_output:
  argv=[sys.executable,'-B','-X','utf8',str(Path(__file__).with_name('check_on_online_convergence_gate.py')),
   '--repo',str(repo),'--protocol',args.protocol,'--protocol-sha256',args.protocol_sha256,'--input',args.output,
   '--output',args.verify_output,'--remaining-seconds',str(remaining())]
  child=subprocess.run(argv,timeout=remaining());remaining()
  if child.returncode:raise SystemExit(child.returncode)
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 for name in ('repo','protocol','protocol-sha256','output'):p.add_argument('--'+name,required=True)
 p.add_argument('--verify-output');main(p.parse_args())
