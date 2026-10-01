"""Execute a stage against frozen source with an explicit module allowlist."""
import argparse
from pathlib import Path
import runpy
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--module', required=True)
    parser.add_argument('arguments', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if sys.version_info < (3, 12):
        raise SystemExit('Python 3.12+ required; no installation is performed.')
    allowed = {'unittest', 'tools.r050_review_boundary.regression',
               'tools.r061_linear.worker', 'tools.r061_linear.audit',
               'tools.r061_linear.selftest'}
    if args.module not in allowed:
        raise SystemExit('Stage module is not allowlisted')
    sys.dont_write_bytecode = True
    source = args.source.resolve()
    sys.path[:0] = [str(source / 'src'), str(source)]
    sys.argv = [args.module] + (args.arguments[1:] if args.arguments[:1] == ['--'] else args.arguments)
    runpy.run_module(args.module, run_name='__main__')


if __name__ == '__main__':
    main()
