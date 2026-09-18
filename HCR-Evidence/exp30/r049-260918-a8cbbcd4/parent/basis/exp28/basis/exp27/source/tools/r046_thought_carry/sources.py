"""Read pinned local repository/evidence only; never fetch, upgrade or rewrite dependencies."""
from pathlib import Path
from . import storage as io
from .contracts import *
import hashlib

CAPSULE=('manifest.json','plan.json','analysis/manifest.json','analysis/audit.json',
         'analysis/trials.csv','analysis/decision_networks.csv','analysis/readouts.csv','upstream/seed/6.json')
BLOBS={'manifest.json':'f32abaeda7ac000fbccd3499c33ae39d2dfe6a84',
 'plan.json':'93e17a52d1a2cce2e7046da04e6599d49e0faece',
 'analysis/manifest.json':'04e43f6e0fb6bcd04ed98cd5006811db40846797',
 'analysis/audit.json':'c71e7d9d9fb4cc521e93ca89d29a65c1fd7e310b',
 'analysis/trials.csv':'42245146207931d20782192a43e63a51ad2424d0',
 'analysis/decision_networks.csv':'87737de1bb3f11a33624e5722964035df9304045',
 'analysis/readouts.csv':'89bc482c2a9791093d5f0bee4f6d6958677a9b8b'}

def repo_root():return Path(__file__).resolve().parents[2]

def blob(data):return hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()

def core_inventory(root):
    inventory={}
    for n,h in NATIVE_BLOBS.items():
        rel='src/hcr/'+n;data=io.read(io.child(root,rel))
        io.require(blob(data.replace(b'\r\n',b'\n'))==h,'native baseline mismatch: '+rel)
        inventory[rel]=io.text_hash(io.child(root,rel))
    return inventory

def addon_inventory(root):
    manifest=io.load(root/'R046_MANIFEST.json')
    io.require(set(manifest)=={'schema','basis_commit','files'} and
        manifest['schema']=='hcr-r046-additive-v1' and manifest['basis_commit']==BASE_COMMIT,'R046 release manifest')
    for name,h in manifest['files'].items():io.require(io.text_hash(io.child(root,name))==h,'R046 source changed: '+name)
    actual={p.relative_to(root).as_posix() for p in (root/'tools/r046_thought_carry').rglob('*.py')}
    listed={n for n in manifest['files'] if n.startswith('tools/r046_thought_carry/') and n.endswith('.py')}
    io.require(actual==listed,'unlisted/missing R046 Python source')
    return dict(manifest['files'],**{'R046_MANIFEST.json':io.text_hash(root/'R046_MANIFEST.json')})

def baseline(root):
    raw=io.read(root/'R045_MANIFEST.json').replace(b'\r\n',b'\n')
    io.require(blob(raw)==R045_MANIFEST_BLOB,'expected R045 + seed-schema hotfix baseline')
    return {**core_inventory(root),**addon_inventory(root)}

def read_basis(parent):
    p=io.safe(parent);data={n:io.read(io.child(p,n)) for n in CAPSULE}
    io.require(io.bytes_hash(data['manifest.json'])==PARENT_MANIFEST_SHA256,'pinned EXP26 raw manifest changed')
    for n,h in BLOBS.items():io.require(blob(data[n])==h,'pinned EXP26 capsule changed: '+n)
    manifest=io.loads(data['manifest.json'])
    io.require(manifest['state']=='raw_complete' and manifest['schema']=='hcr-exp26-raw-manifest-v1','EXP26 incomplete')
    for n in ('plan.json','upstream/seed/6.json'):
        io.require(io.bytes_hash(data[n])==manifest['files'][n],'EXP26 raw leaf mismatch: '+n)
    doc=io.loads(data['upstream/seed/6.json']);engine=doc['document']['engine']
    cfg=engine['config'];memory=engine['memory']
    io.require(memory['schema']=='hcr-memory-r02','seed schema')
    lengths=[]
    for c in memory['circuits']:
        io.require(type(c['active']) is bool,'active flag type');pattern=c['pattern']
        n=pattern['program']['edge_count']
        io.require(type(n) is int and n==len(pattern['relations']) and len(pattern['roles'])==n+1,'pattern relation/role/edge count')
        if c['active']:lengths.append(n)
    io.require(sorted(lengths)==[2,3],'unexpected seed; no fallback/pruning/repair')
    from hcr.model import Config
    Config(**cfg['kernel'])
    return dict(config=cfg['kernel'],adaptive_config=cfg,memory=memory,
                data=data,hashes={n:io.bytes_hash(b) for n,b in data.items()})
