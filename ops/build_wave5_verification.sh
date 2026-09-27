#!/bin/sh
set -eu
mkdir -p public
python3 -m pip install -e '.[vercel-sandbox]' --disable-pip-version-check
python3 ops/verify_wave5_candidate.py --preflight --output public/preflight.json
python3 ops/verify_wave5_candidate.py --output public/wave5-verification.json
