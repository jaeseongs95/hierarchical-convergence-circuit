#!/usr/bin/env bash
set -euo pipefail

git init
git add .
git commit -m "chore: initialize hierarchical convergence-circuit research repository"

echo "Repository initialized. Add your GitHub remote, then push."
