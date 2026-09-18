"""Release integrity + recursive baseline + native API availability. No efficacy assertion."""
import argparse
import ast
import inspect
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tools')]
from r045_direct_support import sources, storage as io


def main(argv=None):
    p=argparse.ArgumentParser();p.add_argument('--addon-only',action='store_true',help='Integrity/syntax only; not native validation')
    args=p.parse_args(argv)
    io.require(sys.version_info>=(3,12),'Python 3.12 or newer required')
    new=sources.addon_hashes()
    for name in new:
        if name.endswith('.py'): ast.parse(io.read(ROOT/name).decode('utf-8'),filename=name)
    report=dict(addon_integrity=True,new_files=len(new),syntax=True,addon_only=args.addon_only)
    if not args.addon_only:
        old=sources.dependencies()
        import hcr
        from hcr.sessions import AdaptiveSession
        from r044_reuse_contribution.runtime import worker
        from r044_reuse_contribution.trial_audit import audit_trial
        from r044_reuse_contribution.gate_audit import measure_execution
        from r036_input_representation.audit import check_seed
        io.require(hasattr(hcr,'__path__') and all(callable(x) for x in (worker,audit_trial,measure_execution,check_seed)),'native dependency API')
        params=inspect.signature(AdaptiveSession.__init__).parameters
        io.require('use_circuits' in params or any(p.kind==p.VAR_KEYWORD for p in params.values()),'native constructor gate API')
        io.require(tuple(inspect.signature(worker).parameters)==('observation','config','memory','budget','scheduler','use_circuits','event_sink'), 'R044 worker signature')
        report.update(dependency_integrity=True,dependency_files=len(old),native_imports=True)
    print(io.canonical(report).decode('utf-8'))
    return 0
if __name__=='__main__': raise SystemExit(main())
