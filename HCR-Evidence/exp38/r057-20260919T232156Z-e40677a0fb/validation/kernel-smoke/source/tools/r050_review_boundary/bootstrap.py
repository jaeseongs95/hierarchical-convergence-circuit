"""Run one stage against an explicitly selected source root, without installation."""
from __future__ import annotations
import argparse
from pathlib import Path
import runpy
import sys

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--source',required=True,type=Path)
    p.add_argument('--module',required=True)
    p.add_argument('arguments',nargs=argparse.REMAINDER)
    a=p.parse_args()
    if sys.version_info < (3,12):
        raise SystemExit('Existing Python 3.12+ is required. Nothing is installed.')
    if not (a.module.startswith('tools.r050_review_boundary.') or a.module=='unittest'):
        raise SystemExit('Stage module is not allowlisted.')
    sys.dont_write_bytecode=True
    root=a.source.resolve()
    sys.path[:0]=[str(root/'src'),str(root)]
    args=a.arguments[1:] if a.arguments[:1]==['--'] else a.arguments
    sys.argv=[a.module]+args
    runpy.run_module(a.module,run_name='__main__')

if __name__=='__main__':
    main()
