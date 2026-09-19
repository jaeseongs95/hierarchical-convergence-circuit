"""Thin entrypoint to installed HCC experiments. No installer/retry/repair logic."""
from __future__ import annotations
import argparse
import json
from pathlib import Path, PurePosixPath
import subprocess
import sys


def main() -> int:
    if sys.version_info < (3, 12):
        raise SystemExit("Python 3.12+ required; no automatic installation.")
    root = Path(__file__).resolve().parents[1]
    index = json.loads((root / "experiments/INDEX.json").read_text(encoding="utf-8"))
    p = argparse.ArgumentParser(description="Use the installed experiment entrypoint; not an old OneClick installer.")
    p.add_argument("--list", action="store_true")
    p.add_argument("--experiment", help="For example EXP-30. Default is explicit in experiments/INDEX.json.")
    a = p.parse_args()
    records = index["experiments"]
    if a.list:
        for row in records:
            print(row["experiment_id"], row.get("legacy_python_entrypoint") or "(no Python launcher registered)")
        return 0
    requested = a.experiment or index["default_experiment"]
    matches = [row for row in records if row["experiment_id"] == requested]
    if len(matches) != 1 or not matches[0].get("legacy_python_entrypoint"):
        p.error("No unique installed Python launcher: " + requested)
    rel = matches[0]["legacy_python_entrypoint"]
    path = PurePosixPath(rel)
    if (path.is_absolute() or len(path.parts) != 1 or path.suffix != ".py"
            or not path.name.startswith("Run-HCR-R") or ":" in rel or "\\" in rel):
        p.error("Unsafe launcher reference")
    entry = root / rel
    if entry.is_symlink() or not entry.is_file() or entry.resolve().parent != root:
        p.error("Installed launcher is missing or not local")
    # Preserve the original launcher's default arguments, scope, source and failure behavior.
    # Older launchers that require an --out argument will report their own usage failure;
    # this bridge deliberately does not invent experimental settings.
    return subprocess.call([sys.executable, "-X", "utf8", "-B", str(entry)], cwd=root)


if __name__ == "__main__":
    raise SystemExit(main())
