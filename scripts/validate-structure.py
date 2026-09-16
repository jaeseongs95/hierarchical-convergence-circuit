from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    "README.md",
    "README.ko.md",
    "theory/core-hypothesis.md",
    "theory/source/2026-09-16-integrated-hypothesis-ko.md",
    "formalism/notation.md",
    "evidence/claims.yaml",
    "experiments/README.md",
    "architecture/minimal-computational-architecture.md",
    "docs/research-principles.md",
]

missing = [path for path in REQUIRED if not (ROOT / path).exists()]
if missing:
    raise SystemExit("Missing required paths:\n- " + "\n- ".join(missing))

print(f"OK: {len(REQUIRED)} required repository paths found")
