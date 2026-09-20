#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt
export PLAYWRIGHT_BROWSERS_PATH="$(pwd)/pw-browsers"
python -m playwright install --with-deps chromium chromium-headless-shell
