"""Reuse R34 lossless writer; retain canonical bytes instead of full trace objects."""
import hashlib,json
from tools.r32_semantic_join.runtime import require
from tools.r34_feasible_state.probe import Recorder as PriorRecorder

def work_writer(folder,p):
    used=sum(f.stat().st_size for f in folder.iterdir() if f.is_file())
    def write(path,data,metadata=False):
        nonlocal used
        body=(json.dumps(data,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False)+'\n').encode('utf-8')
        limit=p['limits']['raw_bytes']-(0 if metadata else 2*1024**2)
        require(path.parent==folder and len(body)<=p['limits']['child_file_bytes'] and used+len(body)<=limit,'work raw/file stop boundary with metadata reserve')
        with path.open('xb') as f:f.write(body)
        used+=len(body)
    return write

class Recorder(PriorRecorder):
    def __init__(self,p):super().__init__(p);self.cache={};self.cached_bytes=0;self.peak_record_bytes=0
    def add(self,k):
        body=json.dumps(dict(kernel=k,config=self.p['kernel']),sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode('utf-8')
        require(len(body)<=self.p['budget']['record_encoded_cache_max_bytes'],'canonical trace record bound')
        digest=hashlib.sha256(body).hexdigest()
        if digest in self.seen:
            self.calls+=1;key=self.seen[digest];require(self.cache[key]==body,'canonical content collision exact bytes');return key
        require(len(self.seen)<self.p['budget']['maximum_unique_trace_records'],'finite unique trace bound')
        key=super().add(k);self.items.pop(key);self.cache[key]=body;self.cached_bytes+=len(body);self.peak_record_bytes=max(self.peak_record_bytes,len(body));return key
