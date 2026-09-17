"""명시적인 prepare / execute / audit / verify 진입점."""
from __future__ import annotations
import argparse
import json
from . import io


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    prepare = sub.add_parser('prepare'); prepare.add_argument('--source-run', required=True); prepare.add_argument('--out', required=True)
    execute = sub.add_parser('execute'); execute.add_argument('--plan', required=True); execute.add_argument('--out', required=True)
    execute.add_argument('--source-run')
    for name in ('audit','verify'):
        q = sub.add_parser(name); q.add_argument('--run', required=True)
    a = p.parse_args(argv)
    try:
        if a.command == 'prepare':
            from .protocol import prepare
            result = prepare(a.source_run, a.out)
        elif a.command == 'execute':
            from .protocol import execute
            result = execute(io.load(a.plan), a.out, a.source_run)
        else:
            from .audit import write_analysis
            result = write_analysis(a.run, check_only=a.command == 'verify')
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False), flush=True)
        return 0
    except (OSError, ValueError, KeyError, TypeError, ImportError, RuntimeError) as exc:
        p.exit(2, f'중단: {type(exc).__name__}: {exc}\n')
