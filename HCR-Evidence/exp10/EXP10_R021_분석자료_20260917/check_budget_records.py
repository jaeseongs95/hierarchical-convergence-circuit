"""원격에서 읽은 budget 기록의 바이트 재구성·해시 검증·의미 대조. 새 inference 없음."""
import zipfile, json, hashlib
from pathlib import Path
from copy import deepcopy
root=Path(__file__).parent

def enc(v):
 return json.dumps(v, ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')

def sha(b):return hashlib.sha256(b).hexdigest()
expected={
 'legacy':dict(wall=0.0004963000010320684, sha256='3c3f1d78a122455f375efbfaa752e95e50fc694789eb97979959d75651215088', blob='60abf26c41437b05a84c228ebfadd28176af5c5e'),
 'resumed':dict(wall=0.0005237999976088759,sha256='f606d39119a6cc47e02d62c8d7f0f65a9f8d1abf3dbaa455d1d10d9505487877',blob='d62def1f451db1f7d5f8bfed4f86694834099813')}
records={};hashes={}
with zipfile.ZipFile('/mnt/data/hcr_r021_delivery/R021_작성환경_검증자료.zip') as z:
 for arm,e in expected.items():
  record=json.loads(z.read(f'exp10-dev-final-01/budget/{arm}/record.json'))
  # 커넥터의 실제 사용자 기록에서 읽은 값. 일치 여부는 최종 SHA-256/Git blob로 검증한다.
  record['rows'][0]['decision']['cost']['wall_seconds']=e['wall']
  prev='0'*64
  for event in record['events']:
   if event['event']=='r02_decision':event['payload']['cost']['wall_seconds']=e['wall']
   event['previous']=prev
   event['sha256']=sha(enc({k:event[k] for k in ('seq','event','payload','previous')}))
   prev=event['sha256']
  raw=enc(record)+b'\n'
  blob=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
  assert sha(raw)==e['sha256'], (arm,sha(raw),'sha256 mismatch; cannot use reconstruction')
  assert blob==e['blob'], (arm,blob,'Git blob mismatch')
  p=root/'verified_budget'/arm/'record.json';p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
  records[arm]=record
  hashes[arm]=dict(sha256=sha(raw),git_blob=blob,matched_remote_hashes=True)
left,right=deepcopy(records['legacy']),deepcopy(records['resumed'])
for r in (left,right):
 r.pop('arm')
 for row in r['rows']:row['decision']['cost'].pop('wall_seconds')
 for event in r['events']:
  event.pop('sha256');event.pop('previous')
  if event['event']=='r02_decision':event['payload']['cost'].pop('wall_seconds')
assert left==right
result=dict(budget_hash_checks=hashes,budget_semantics_equal=True,exclusions=['arm','decision.cost.wall_seconds','event hash chain derived from elapsed time'],inference_executed=False,full_run_audit_executed=False,scope='2 budget records only; byte reconstruction accepted only after both manifest SHA-256 and Git blob SHA matched retrieved remote values')
(root/'budget_comparison.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result,ensure_ascii=False,indent=2))
