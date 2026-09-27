#!/bin/sh
set -eu
mkdir -p public
python3 -m venv /tmp/wave5-verifier-venv
/tmp/wave5-verifier-venv/bin/python -m pip install -e '.[vercel-sandbox]' --disable-pip-version-check
/tmp/wave5-verifier-venv/bin/python ops/verify_wave5_candidate.py --preflight --output public/preflight.json
/tmp/wave5-verifier-venv/bin/python ops/verify_wave5_candidate.py --output public/wave5-verification.json
