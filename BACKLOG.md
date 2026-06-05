# Backlog — deepseek4free API + Telegram Bot

## Done
- [x] Clone repo `xtekky/deepseek4free`
- [x] Fix SSE parser di `dsk/api.py`
- [x] Fix relative import di `dsk/server.py`
- [x] Buat wrapper OpenAI-compatible `openai_api.py`
- [x] Endpoint `/health`
- [x] Endpoint `/v1/models`
- [x] Endpoint `/v1/chat/completions`
- [x] Endpoint `/v1/responses` dasar
- [x] API key protection via `OPENAI_API_KEY`
- [x] Aktivasi auth via file `.env`
- [x] Build & run container `deepseek4free-api`
- [x] Test live non-streaming
- [x] Test live streaming
- [x] Buat `telegram_bot.py`
- [x] Deploy bot `@bravo_deepseek_chat_bot`
- [x] Whitelist user default `638445510`
- [x] Rate limit ringan bot
- [x] Logging JSONL bot
- [x] Command `/start`, `/ping`, `/reset`, `/whoami`

## Next — High Priority
- [ ] Restart bot container agar fitur terbaru aktif (`/whoami`, whitelist, logging, rate limit)
- [ ] Verifikasi command bot setelah restart
  - [ ] `/start`
  - [ ] `/ping`
  - [ ] `/whoami`
  - [ ] `/reset`
- [ ] Verifikasi log file bot dibuat di `/data/bot_logs.jsonl`
- [ ] Verifikasi memory file bot di `/data/bot_memory.json`

## Next — Security
- [ ] Pindah token sensitif dari file contoh/chat ke storage host lebih aman
- [ ] Rotasi `TELEGRAM_BOT_TOKEN` bila perlu karena pernah terkirim di chat
- [ ] Rotasi `DEEPSEEK_AUTH_TOKEN` bila perlu karena pernah terkirim di chat
- [ ] Batasi akses port `2224` hanya host/docker bridge
- [ ] Tambah auth juga untuk endpoint sensitif lain bila nanti dibuka publik

## Next — Infra
- [ ] Buat subdomain publik `deepseek.bravo-tim.siat.web.id`
- [ ] Pasang SSL untuk subdomain
- [ ] Tambah nginx reverse proxy ke `127.0.0.1:8787`
- [ ] Verifikasi akses HTTPS publik
- [ ] Dokumentasikan path config nginx + cert

## Next — Bot Features
- [ ] Tambah command admin `/logs` ringkas
- [ ] Tambah command admin `/status`
- [ ] Tambah command admin `/prompt` untuk lihat/ganti system prompt
- [ ] Tambah whitelist multi-user via env
- [ ] Tambah persistent rate-limit state jika perlu
- [ ] Tambah mode streaming/reply bertahap jika UX perlu
- [ ] Tambah fallback jawaban error lebih manusiawi

## Next — API Features
- [ ] Tambah streaming compatibility untuk `/v1/responses`
- [ ] Tambah `/v1/models` lebih dari 1 alias jika perlu kompatibilitas client
- [ ] Tambah metrics/log request dasar
- [ ] Tambah health detail (`upstream`, `auth`, `version`)
- [ ] Tambah request timeout/retry policy lebih rapi
- [ ] Tambah validation untuk payload OpenAI edge cases

## Next — Ops
- [ ] Buat README deploy ringkas untuk host Bravo
- [ ] Buat prosedur restart/rebuild resmi
- [ ] Tambah smoke test script untuk API + bot
- [ ] Tambah backup/log rotation untuk `bot_logs.jsonl`
- [ ] Tambah monitor sederhana untuk container API dan bot

## Nice to Have
- [ ] Dukungan Telegram inline keyboard
- [ ] Dukungan persona per bot
- [ ] Dukungan multi-bot / multi-tenant
- [ ] Web dashboard admin ringan
