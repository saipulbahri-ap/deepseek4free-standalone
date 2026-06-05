#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${DEEPSEEK_AUTH_TOKEN:-}" ]]; then
  read -rsp "DEEPSEEK_AUTH_TOKEN: " DEEPSEEK_AUTH_TOKEN
  echo
  export DEEPSEEK_AUTH_TOKEN
fi

cd "$(dirname "$0")"
python3 -m uvicorn openai_api:app --host 127.0.0.1 --port "${PORT:-8787}" >/tmp/deepseek4free-api.log 2>&1 &
api_pid=$!
trap 'kill "$api_pid" 2>/dev/null || true' EXIT

for _ in {1..30}; do
  if curl -fsS http://127.0.0.1:${PORT:-8787}/health >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

if ! curl -fsS http://127.0.0.1:${PORT:-8787}/health >/dev/null 2>&1; then
  echo "API failed to start"
  tail -80 /tmp/deepseek4free-api.log
  exit 1
fi

api_key="$(python3 - <<'PY'
from pathlib import Path
p=Path('.env')
for line in p.read_text().splitlines() if p.exists() else []:
    if line.startswith('OPENAI_API_KEY='):
        print(line.split('=',1)[1])
        break
PY
)"

auth_args=()
if [[ -n "$api_key" ]]; then
  auth_args=(-H "Authorization: Bearer $api_key")
fi

curl -sS http://127.0.0.1:${PORT:-8787}/v1/chat/completions \
  -H 'Content-Type: application/json' \
  "${auth_args[@]}" \
  -d '{"model":"deepseek-chat","stream":false,"messages":[{"role":"user","content":"Jawab persis: halo dunia"}]}' \
  | python3 -m json.tool

echo
printf '--- api log ---\n'
tail -80 /tmp/deepseek4free-api.log
