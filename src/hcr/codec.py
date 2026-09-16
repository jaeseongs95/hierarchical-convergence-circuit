"""표준 JSON만 사용. 신뢰되지 않은 pickle/코드 역직렬화를 하지 않는다."""
from pathlib import Path
from dataclasses import asdict, is_dataclass
from enum import Enum
import json
import math
import os
import tempfile
from .model import ContractError


def plain(x):
    if is_dataclass(x): return plain(asdict(x))
    if isinstance(x, Enum): return x.value
    if isinstance(x, dict): return {str(k): plain(v) for k,v in x.items()}
    if isinstance(x, (tuple,list)): return [plain(v) for v in x]
    return x


def dumps(x) -> str:
    return json.dumps(plain(x), sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False)


def loads(raw: str | bytes):
    if len(raw) > 32 * 1024**2: raise ContractError('JSON byte budget')
    def pairs(xs):
        out={}
        for k,v in xs:
            if k in out: raise ContractError('duplicate JSON key: '+k)
            out[k]=v
        return out
    def constant(x): raise ContractError('nonfinite JSON '+x)
    def floating(x):
        v=float(x)
        if not math.isfinite(v): raise ContractError('nonfinite JSON number')
        return v
    try: return json.loads(raw, object_pairs_hook=pairs, parse_constant=constant, parse_float=floating)
    except (UnicodeError,json.JSONDecodeError) as e: raise ContractError('invalid JSON') from e


def save(path: Path, value, *, replace: bool=False) -> None:
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.is_symlink() or (path.exists() and not replace): raise FileExistsError(path)
    fd,temp=tempfile.mkstemp(prefix='.'+path.name+'.',suffix='.tmp',dir=path.parent)
    try:
        with os.fdopen(fd,'w',encoding='utf-8',newline='\n') as stream:
            stream.write(dumps(value)+'\n');stream.flush();os.fsync(stream.fileno())
        if replace: os.replace(temp,path)
        else:
            # 대상 생성은 exclusive. 이미 존재하는 사용자 파일은 덮어쓰지 않는다.
            with path.open('x',encoding='utf-8',newline='\n') as out:
                out.write(Path(temp).read_text(encoding='utf-8'));out.flush();os.fsync(out.fileno())
    finally:
        if os.path.exists(temp): os.unlink(temp)


def observation_from(value):
    """공개 입력의 정확한 필드만 허용한다. truth/label/scenario 키는 거부한다."""
    from .model import Observation, EdgeObservation
    try:
        if not isinstance(value, dict) or set(value) != {'episode_id','revision','start','goal','edges'}:
            raise ContractError('observation fields: 공개 관측 외 필드 금지')
        if not isinstance(value['edges'], list):
            raise ContractError('observation edges must be a JSON array')
        return Observation(**dict(value, edges=tuple(EdgeObservation(**e) for e in value['edges'])))
    except (TypeError, KeyError) as exc:
        raise ContractError('invalid observation schema') from exc


def decision_from(value):
    """감사 도구 전용 자료 복원. 코드를 실행하는 pickle은 사용하지 않는다."""
    from .model import Decision, Convergence, Mode, Status, Proof, ProofNode
    try:
        proof = value['proof']
        pr = Proof(**dict(proof, nodes=tuple(ProofNode(**dict(n, parents=tuple(n['parents']))) for n in proof['nodes']),
                          assumed_edges=tuple(tuple(e) for e in proof['assumed_edges']),
                          paths=tuple(tuple(p) for p in proof['paths'])))
        cv = Convergence(**dict(value['convergence'], status=Status(value['convergence']['status'])))
        return Decision(**dict(value, proof=pr, convergence=cv, mode=Mode(value['mode']),
                               state=tuple(tuple(p) for p in value['state'])))
    except (TypeError, KeyError, ValueError) as exc:
        raise ContractError('invalid decision record') from exc
