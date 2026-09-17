"""Append-only 이벤트. 이전 기록은 반환 객체를 수정해도 바뀌지 않는다."""
from pathlib import Path
from . import codec
from .model import ContractError,fingerprint


class Trace:
    def __init__(self,path:Path|None=None):
        self.path=path;self._records=[];self._head='0'*64;self._closed=False
        self._stream=None
        if path is not None:
            path.parent.mkdir(parents=True,exist_ok=True)
            self._stream=path.open('x',encoding='utf-8',newline='\n')

    def emit(self,event:str,payload:dict) -> str:
        if self._closed: raise ContractError('trace already closed')
        body={'seq':len(self._records),'previous':self._head,'event':event,'payload':codec.plain(payload)}
        record=dict(body,sha256=fingerprint(body));line=codec.dumps(record)
        if self._stream is not None:self._stream.write(line+'\n');self._stream.flush()
        self._records.append(line);self._head=record['sha256'];return self._head

    @property
    def records(self):return [codec.loads(line) for line in self._records]
    @property
    def head(self):return self._head
    @property
    def count(self):return len(self._records)

    def close(self):
        self._closed=True
        if self._stream is not None:self._stream.close();self._stream=None


def check_chain(records:list,expected_count:int,expected_head:str) -> None:
    head='0'*64
    if len(records)!=expected_count:raise ContractError('event truncation/addition')
    for i,r in enumerate(records):
        if set(r)!={'seq','previous','event','payload','sha256'}:raise ContractError('event schema')
        body={k:r[k] for k in ('seq','previous','event','payload')}
        if r['seq']!=i or r['previous']!=head or fingerprint(body)!=r['sha256']:raise ContractError('event chain mismatch')
        head=r['sha256']
    if head!=expected_head:raise ContractError('event head mismatch')
