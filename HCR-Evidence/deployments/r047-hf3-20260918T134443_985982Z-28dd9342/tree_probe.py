
import hashlib, json, os, sys
from pathlib import Path
root=Path(sys.argv[1]).resolve()
sys.path[:0]=[str(root/'src'),str(root)]
import hcr
assert Path(hcr.__file__).resolve()==root/'src/hcr/__init__.py', 'hcr module shadowing'
from tools.r047_state_ablation import provenance, storage, spec
assert Path(provenance.__file__).resolve()==root/'tools/r047_state_ablation/provenance.py'
m=provenance.package_check(root)
n=provenance.native_check(root)
source=provenance.source_inventory(root)
report=dict(package_verified=True,native_verified=True,files=len(m['files']),source_files=len(source),
            hcr_origin=str(Path(hcr.__file__).resolve()),design_sha256=storage.digest(spec.design()))
if len(sys.argv)>3:
    dest=Path(sys.argv[3]);dest.mkdir(parents=True,exist_ok=False)
    for name,h in source.items():
        data=(root/name).read_bytes()
        assert hashlib.sha256(data).hexdigest()==h
        p=dest/name;p.parent.mkdir(parents=True,exist_ok=True)
        with p.open('xb') as f:f.write(data)
    report['copied_source_snapshot']=str(dest)
with Path(sys.argv[2]).open('x',encoding='utf-8') as f:json.dump(report,f,ensure_ascii=False,sort_keys=True)
print(json.dumps(report,ensure_ascii=False,sort_keys=True))
