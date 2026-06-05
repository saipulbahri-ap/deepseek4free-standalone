# Deploy Spec: deepseek4free API

## Spesifikasi Container

|Item|Nilai|
|-|-|
|**Image**|`deepseek4free-api:latest`|
|**Base**|`python:3.11-slim`|
|**Port**|`8787` (internal) → `8787` (host)|
|**Restart**|`always`|
|**Network**|`bridge` (host network untuk akses ke Telegram bot nanti)|
|**Volume mount**| `-v /home/saipul/.openclaw-workspace/deepseek4free/cookies.json:/app/dsk/cookies.json` (optional)|

## Environment Variables

|Variabel|Value|Keterangan|
|-|-|-|
|`DEEPSEEK_AUTH_TOKEN`|`356ugYpZ9ZyysOQpv8T2jnp2LYNnTlKBui/G9EM4JJfIlPjshKe4SqwNfndO8XE/`|Token DeepSeek|
|`PORT`|`8787`|Port API|

## Volume/Data Persistence

- `cookies.json` opsional untuk Cloudflare bypass
- Token disimpan di env (tidak di file)

## Health Check

```bash
curl -f http://localhost:8787/health
```

## Dependencies

Ada di `requirements.txt`:
- curl-cffi==0.8.1b9
- wasmtime
- numpy
- fastapi
- uvicorn
- python-dotenv

## File yang diperlukan Hermes

Source: `/home/saipul/.openclaw-workspace/deepseek4free/`
```
dsk/
  __init__.py
  api.py
  pow.py
  server.py
  bypass.py
  CloudflareBypasser.py
  run_and_get_cookies.py
  wasm/sha3_wasm_bg.7b9ca65ddd.wasm
openai_api.py
requirements.txt
patches/deepseek4free-local-fixes.patch
```

## Catatan

- Patch SSE parser sudah diterapkan di `dsk/api.py`
- API sudah OpenAI-compatible di `/v1/chat/completions`
- Non-streaming & streaming support
