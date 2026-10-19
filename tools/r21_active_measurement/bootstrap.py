"""Verified archive entry, exclusive target, bounded background research process."""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys
import time
import zipfile

started = time.monotonic()
root = Path('/home/mcpops/hcc-active-measurement-20261019-r21')
assert sys.version_info >= (3, 12)
assert not root.exists()
root.mkdir(mode=0o700)
with zipfile.ZipFile('/home/mcpops/hcc-active-measurement-source-20261019-r21.zip') as z:
    for item in z.infolist():
        p = PurePosixPath(item.filename)
        assert not p.is_absolute() and '..' not in p.parts and not item.is_dir()
        target = root.joinpath(*p.parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as stream: stream.write(z.read(item))
manifest = json.loads((root/'source_manifest.json').read_text())
assert all(hashlib.sha256((root/n).read_bytes()).hexdigest() == h for n,h in manifest.items())
env = dict(os.environ, PYTHONPATH=str(root/'src')+':'+str(root), PYTHONDONTWRITEBYTECODE='1')
remaining = max(1, 600 - (time.monotonic()-started))
with (root/'launch.stdout').open('xb') as stdout, (root/'launch.stderr').open('xb') as stderr:
    child = subprocess.Popen(['timeout','--kill-after=5s',str(remaining)+'s',sys.executable,'-B',
        str(root/'tools/r21_active_measurement/probe.py'),'--phase','run','--started',str(started)],
        stdout=stdout, stderr=stderr, env=env, cwd=root, start_new_session=True)
receipt = dict(pid=child.pid, root=str(root), total_wall_cap_seconds=600, maximum_native_settle_calls=200, maximum_measurement_requests=20,
    native_training=0, single_worker=True, no_retry=True, preparation_seconds=time.monotonic()-started)
with (root/'launch.json').open('x',encoding='utf-8',newline='\n') as stream:json.dump(receipt,stream)
print(json.dumps(receipt))
