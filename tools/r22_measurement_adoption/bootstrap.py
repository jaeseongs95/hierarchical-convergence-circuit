"""Checked archive, exclusive extraction, and bounded parent/worker processes."""
import hashlib
import json
import os
from pathlib import Path,PurePosixPath
import resource
import subprocess
import sys
import time
import zipfile

started=time.monotonic();root=Path('/home/mcpops/hcc-measurement-adoption-20261019-r22')
if sys.version_info<(3,12):raise RuntimeError('Python3.12 required')
if root.exists():raise RuntimeError('exclusive root exists')
root.mkdir(mode=0o700)
with zipfile.ZipFile('/home/mcpops/hcc-measurement-adoption-source-20261019-r22.zip') as z:
    for item in z.infolist():
        p=PurePosixPath(item.filename)
        if p.is_absolute() or '..' in p.parts or item.is_dir():raise ValueError('archive path')
        target=root.joinpath(*p.parts);target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('xb') as f:f.write(z.read(item))
manifest=json.loads((root/'source_manifest.json').read_text())
if not all(hashlib.sha256((root/n).read_bytes()).hexdigest()==h for n,h in manifest.items()):raise ValueError('source manifest')
limits=json.loads((root/'experiments/exp-68-measurement-adoption/frozen_spec.json').read_text())['limits']
if not(0<limits['total_seconds']<=600 and 0<limits['parent_address_space_bytes']<=512*1024**2 and 0<limits['parent_file_bytes']<=32*1024**2):raise ValueError('parent caps')
def parent_limits():
    resource.setrlimit(resource.RLIMIT_AS,(limits['parent_address_space_bytes'],)*2)
    resource.setrlimit(resource.RLIMIT_FSIZE,(limits['parent_file_bytes'],)*2)
env=dict(os.environ,PYTHONPATH=str(root/'src')+':'+str(root),PYTHONDONTWRITEBYTECODE='1',PYTHONOPTIMIZE='0')
remaining=max(1,limits['total_seconds']-(time.monotonic()-started))
with (root/'launch.stdout').open('xb') as stdout,(root/'launch.stderr').open('xb') as stderr:
    child=subprocess.Popen(['timeout','--kill-after=5s',str(remaining)+'s',sys.executable,'-B',str(root/'tools/r22_measurement_adoption/probe.py'),
        '--phase','run','--started',str(started)],stdout=stdout,stderr=stderr,env=env,cwd=root,start_new_session=True,preexec_fn=parent_limits)
receipt=dict(pid=child.pid,root=str(root),total_wall_cap_seconds=600,maximum_native_settle_calls=260,maximum_measurement_requests=39,
    native_training=0,single_worker=True,no_retry=True,parent_limits=limits,preparation_seconds=time.monotonic()-started)
with (root/'launch.json').open('x',encoding='utf-8',newline='\n') as f:json.dump(receipt,f)
print(json.dumps(receipt))
