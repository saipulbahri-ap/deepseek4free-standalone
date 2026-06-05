# Deploy Spec: Telegram Bot for deepseek4free API

## Tujuan
Container bot Telegram terpisah yang memanggil wrapper API OpenAI-compatible di host Bravo.

## Build
```bash
cd /home/saipul/.openclaw-workspace/deepseek4free
docker build -t deepseek4free-telegram-bot -f Dockerfile.telegram-bot .
```

## Run
```bash
docker run -d \
  --name deepseek4free-telegram-bot \
  --restart always \
  --add-host=host.docker.internal:host-gateway \
  --env-file /home/saipul/.openclaw-workspace/deepseek4free/.env.telegram-bot \
  -v /home/saipul/.openclaw-workspace/deepseek4free/data:/data \
  deepseek4free-telegram-bot
```

## Env file required
Path:
```bash
/home/saipul/.openclaw-workspace/deepseek4free/.env.telegram-bot
```

Isi minimal:
```bash
TELEGRAM_BOT_TOKEN=...
OPENAI_API_KEY=...
OPENAI_API_BASE=http://172.17.0.1:8787
OPENAI_MODEL=deepseek-chat
BOT_MEMORY_PATH=/data/bot_memory.json
BOT_MAX_HISTORY=12
BOT_SYSTEM_PROMPT=Kamu asisten yang ringkas, akurat, dan membantu.
```

## Verify
```bash
docker logs deepseek4free-telegram-bot --tail 50
```

## Notes
- API wrapper sudah protected dengan `OPENAI_API_KEY`.
- Bot memory disimpan persistent di `/data/bot_memory.json`.
- Tidak expose port publik.
