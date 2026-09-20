"""Check saved derivatives against an independently replayed audit; read-only."""
from __future__ import annotations
import argparse
from pathlib import Path
from .common import dump, load, require, safe
from .analysis_contract import verify_analysis


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run', required=True, type=Path)
    p.add_argument('--audit', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    a = p.parse_args(argv)
    run, source, output = safe(a.run), safe(a.audit), safe(a.output)
    require(output != source and not output.exists(), 'Never replace an input or existing receipt')
    report = verify_analysis(run, load(source))
    dump(output, report)
    print('VERIFIED: audit / summary / CSV / Markdown agree; no inference rerun', flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
