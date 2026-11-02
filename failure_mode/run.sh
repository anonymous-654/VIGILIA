#!/usr/bin/env bash
set -euo pipefail
repo_root="${SLURM_SUBMIT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
while [[ "$repo_root" != / && ! -f "$repo_root/classroom/simulate_class_session.py" ]]; do
    repo_root="$(dirname "$repo_root")"
done
if [[ ! -f "$repo_root/classroom/simulate_class_session.py" ]]; then
    echo "Cannot locate the repository root" >&2
    exit 1
fi
cd "$repo_root"
python_bin="${PYTHON:-python3}"
if [[ -z "${PYTHON:-}" && -x .venv/bin/python ]]; then
    python_bin=.venv/bin/python
fi
exec "$python_bin" -m failure_mode.run "$@"
