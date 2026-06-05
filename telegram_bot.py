import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

import requests
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

API_BASE = os.getenv("OPENAI_API_BASE", "http://127.0.0.1:8787")
API_KEY = os.getenv("OPENAI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
MODEL = os.getenv("OPENAI_MODEL", "deepseek-chat")
MEMORY_PATH = Path(os.getenv("BOT_MEMORY_PATH", "bot_memory.json"))
LOG_PATH = Path(os.getenv("BOT_LOG_PATH", "bot_logs.jsonl"))
MAX_HISTORY = int(os.getenv("BOT_MAX_HISTORY", "12"))
SYSTEM_PROMPT = os.getenv("BOT_SYSTEM_PROMPT", "Kamu asisten yang ringkas, akurat, dan membantu.")
RATE_LIMIT_SECONDS = int(os.getenv("BOT_RATE_LIMIT_SECONDS", "3"))
ALLOWED_USERS = {
    item.strip()
    for item in os.getenv("BOT_ALLOWED_USERS", "638445510").split(",")
    if item.strip()
}

LAST_SEEN: Dict[str, float] = {}


def load_memory() -> Dict[str, List[dict]]:
    if not MEMORY_PATH.exists():
        return {}
    try:
        return json.loads(MEMORY_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_memory(memory: Dict[str, List[dict]]) -> None:
    MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    MEMORY_PATH.write_text(json.dumps(memory, ensure_ascii=False, indent=2), encoding="utf-8")


def append_log(event: dict) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    event.setdefault("ts", datetime.now(timezone.utc).isoformat())
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


def get_headers() -> dict:
    headers = {"Content-Type": "application/json"}
    if API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"
    return headers


def build_messages(history: List[dict], user_text: str) -> List[dict]:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(history[-MAX_HISTORY:])
    messages.append({"role": "user", "content": user_text})
    return messages


def ask_model(messages: List[dict]) -> str:
    response = requests.post(
        f"{API_BASE}/v1/chat/completions",
        headers=get_headers(),
        json={"model": MODEL, "messages": messages, "stream": False},
        timeout=180,
    )
    response.raise_for_status()
    data = response.json()
    if "choices" in data and len(data["choices"]) > 0:
        return data["choices"][0]["message"]["content"]
    else:
        raise ValueError("Invalid API response format")


def is_allowed(update: Update) -> bool:
    user = update.effective_user
    if not user:
        return False
    return str(user.id) in ALLOWED_USERS


def is_rate_limited(update: Update) -> bool:
    user = update.effective_user
    if not user:
        return True
    uid = str(user.id)
    now = time.time()
    last = LAST_SEEN.get(uid, 0)
    if now - last < RATE_LIMIT_SECONDS:
        return True
    LAST_SEEN[uid] = now
    return False


async def reject_if_needed(update: Update) -> bool:
    if not update.message:
        return True
    if not is_allowed(update):
        append_log({
            "type": "reject",
            "reason": "not_allowed",
            "user_id": getattr(update.effective_user, "id", None),
            "chat_id": getattr(update.effective_chat, "id", None),
            "text": update.message.text,
        })
        await update.message.reply_text("Akses ditolak.")
        return True
    if is_rate_limited(update):
        append_log({
            "type": "reject",
            "reason": "rate_limited",
            "user_id": getattr(update.effective_user, "id", None),
            "chat_id": getattr(update.effective_chat, "id", None),
            "text": update.message.text,
        })
        await update.message.reply_text("Terlalu cepat. Coba lagi sebentar.")
        return True
    return False


async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    if await reject_if_needed(update):
        return
    await update.message.reply_text(
        "Bot siap. Kirim pesan biasa untuk chat.\n"
        "Perintah:\n"
        "/reset - hapus memory chat\n"
        "/ping - cek status\n"
        "/whoami - info user/chat"
    )


async def ping_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    if await reject_if_needed(update):
        return
    try:
        response = requests.get(f"{API_BASE}/health", timeout=10)
        response.raise_for_status()
        await update.message.reply_text("pong ✅ API sehat")
    except Exception as e:
        await update.message.reply_text(f"pong ❌ API error: {e}")


async def whoami_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_user or not update.effective_chat:
        return
    if await reject_if_needed(update):
        return
    user = update.effective_user
    chat = update.effective_chat
    await update.message.reply_text(
        f"user_id: {user.id}\n"
        f"username: @{user.username or '-'}\n"
        f"chat_id: {chat.id}\n"
        f"allowed: {'yes' if str(user.id) in ALLOWED_USERS else 'no'}"
    )


async def reset_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_chat:
        return
    if await reject_if_needed(update):
        return
    memory = load_memory()
    chat_id = str(update.effective_chat.id)
    memory.pop(chat_id, None)
    save_memory(memory)
    append_log({"type": "reset", "chat_id": chat_id, "user_id": getattr(update.effective_user, "id", None)})
    await update.message.reply_text("Memory chat direset ✅")


async def chat_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text or not update.effective_chat:
        return
    if await reject_if_needed(update):
        return

    chat_id = str(update.effective_chat.id)
    user_id = str(update.effective_user.id) if update.effective_user else ""
    user_text = update.message.text.strip()
    memory = load_memory()
    history = memory.get(chat_id, [])
    messages = build_messages(history, user_text)

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)

    try:
        answer = ask_model(messages)
    except requests.HTTPError as e:
        body = e.response.text[:300] if e.response is not None else str(e)
        append_log({"type": "api_error", "chat_id": chat_id, "user_id": user_id, "error": body})
        await update.message.reply_text(f"Error API: {body}")
        return
    except Exception as e:
        append_log({"type": "api_error", "chat_id": chat_id, "user_id": user_id, "error": str(e)})
        await update.message.reply_text(f"Error API: {e}")
        return

    history.append({"role": "user", "content": user_text})
    history.append({"role": "assistant", "content": answer})
    memory[chat_id] = history[-MAX_HISTORY:]
    save_memory(memory)
    append_log({
        "type": "chat",
        "chat_id": chat_id,
        "user_id": user_id,
        "prompt": user_text,
        "answer": answer,
    })

    await update.message.reply_text(answer)


def main() -> None:
    if not TELEGRAM_BOT_TOKEN:
        raise SystemExit("TELEGRAM_BOT_TOKEN is required")

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("ping", ping_cmd))
    app.add_handler(CommandHandler("whoami", whoami_cmd))
    app.add_handler(CommandHandler("reset", reset_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat_handler))
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
