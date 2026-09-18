"""기준선·신규 패키지 무결성과 import/native API를 검사한다. 가설 결과를 요구하지 않는다."""
from pathlib import Path
import argparse
import ast
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'src'),str(ROOT/'tools')]
from r044_reuse_contribution import sources, storage as io


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--addon-only',action='store_true',help='신규 파일만 검사. native 통합 검사가 아닙니다.')
    args = parser.parse_args(argv)
    if sys.version_info < (3,12): raise RuntimeError('Python 3.12 이상이 필요합니다.')
    new = sources.addon_hashes()
    for name in new:
        if name.endswith('.py'):
            ast.parse(io.read(ROOT/name).decode('utf-8'),filename=name)
    result = dict(addon_integrity=True,new_files=len(new),syntax=True,addon_only=args.addon_only)
    if not args.addon_only:
        dependencies = sources.dependencies()
        import hcr
        from r041_scheduler_direction.runtime import ScheduledTimingTrial
        from r044_reuse_contribution.trial_audit import audit_trial
        from r036_input_representation.audit import check_seed
        io.require(hasattr(hcr,'__path__'), '루트 hcr.py가 package를 가렸습니다.')
        io.require(callable(ScheduledTimingTrial) and callable(audit_trial) and callable(check_seed), 'R041 API 불일치')
        from hcr.sessions import AdaptiveSession
        import inspect
        io.require('use_circuits' in inspect.signature(AdaptiveSession.__init__).parameters or any(p.kind==p.VAR_KEYWORD for p in inspect.signature(AdaptiveSession.__init__).parameters.values()), 'native constructor switch API')
        result.update(dependency_integrity=True,dependency_files=len(dependencies),native_imports=True)
    print(io.canonical(result).decode('utf-8'))
    return 0
if __name__ == '__main__':
    raise SystemExit(main())
