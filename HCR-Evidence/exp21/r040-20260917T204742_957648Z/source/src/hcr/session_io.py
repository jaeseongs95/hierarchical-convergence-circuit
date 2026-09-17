"""R0.2.1의 위치 독립 체크포인트 I/O. 증거 폴더만 저장소 내부 출력으로 허용한다."""
from __future__ import annotations
import hashlib
import os
from pathlib import Path
import tempfile
from .model import ContractError

MAX_BYTES = 32 * 1024 * 1024


def linked(path: Path) -> bool:
    return path.is_symlink() or (hasattr(path, 'is_junction') and path.is_junction())


def safe_path(path: Path) -> Path:
    path = Path(path).absolute()
    for part in (path, *path.parents):
        if linked(part):
            raise ContractError('session path cannot traverse a symlink/junction: ' + str(part))
    return path.resolve()


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def new_output(path: Path, *, inputs=()) -> Path:
    out = safe_path(path)
    if out.exists():
        raise FileExistsError('기존 결과는 덮어쓰지 않음: ' + str(out))
    root = project_root()
    if out == root / 'HCR-Evidence':
        raise ContractError('HCR-Evidence 자체가 아니라 그 아래 새 경로를 지정')
    # 완료/실패 원시 증거 묶음에 새 파일을 끼워 넣지 않는다.
    sealed = ('manifest.json', 'bundle_manifest.json', 'recovery_manifest.json', 'FAILED.json')
    for parent in out.parents:
        if parent == root:
            break
        if any((parent / name).is_file() for name in sealed):
            raise ContractError('완료/실패 증거 묶음 내부 출력 금지; 새 형제 폴더를 사용')
    if out.is_relative_to(root) and not out.is_relative_to(root / 'HCR-Evidence'):
        raise ContractError('저장소 내부 출력은 HCR-Evidence 아래의 새 경로만 허용')
    for value in inputs:
        source = safe_path(value)
        if out == source or out.is_relative_to(source) or source.is_relative_to(out):
            raise ContractError('입력과 출력 경로의 포함 관계 금지')
    return out


def read_bytes(path: Path) -> bytes:
    p = safe_path(path)
    if not p.is_file() or p.stat().st_size > MAX_BYTES:
        raise ContractError('checkpoint file missing or larger than 32 MiB')
    return p.read_bytes()


def publish(path: Path, raw: bytes) -> None:
    """같은 파일시스템의 임시 파일을 fsync 후 hard-link로 원자적·배타적으로 공개한다.

    지원하지 않는 파일시스템에서는 오류를 내며, 덮어쓰기 방식으로 후퇴하지 않는다.
    NTFS/ext4 같은 hard-link 지원 파일시스템을 사용한다.
    """
    path = new_output(path)
    if len(raw) > MAX_BYTES:
        raise ContractError('checkpoint exceeds 32 MiB')
    path.parent.mkdir(parents=True, exist_ok=True)
    # 생성 직전에도 부모 경계 확인.
    safe_path(path.parent)
    fd, temporary = tempfile.mkstemp(prefix='.hcr-checkpoint-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, path)
    finally:
        os.unlink(temporary)


def source_hashes():
    root = project_root()
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes().replace(b'\r\n', b'\n')).hexdigest()
            for p in sorted((root / 'src/hcr').rglob('*.py'))}
