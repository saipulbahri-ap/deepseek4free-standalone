#!/usr/bin/env bash
set -euo pipefail
: "${DEEPSEEK_AUTH_TOKEN:?Set DEEPSEEK_AUTH_TOKEN first}"
python3 -m uvicorn openai_api:app --host 0.0.0.0 --port "${PORT:-8787}"
