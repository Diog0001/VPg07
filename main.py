"""
Точка входа Telegram-бота v2 (Haystack + Docling + Pinecone).
Запуск из корня проекта: python main.py
"""

from __future__ import annotations

import logging
import os

import telebot

from bot.context import MEMORY_NAMESPACE, OPENAI_CHAT_MODEL
from bot.handlers import register_handlers
from bot.lock import acquire_single_instance_lock
from config import load_project_env

load_project_env()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    raise RuntimeError("Задайте TELEGRAM_BOT_TOKEN в .env")


def create_bot() -> telebot.TeleBot:
    bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN, parse_mode="HTML")
    register_handlers(bot)
    return bot


def main() -> None:
    acquire_single_instance_lock()
    logger.info(
        "Бот v2 запущен (Haystack + Docling). Модель: %s, namespace: %s",
        OPENAI_CHAT_MODEL,
        MEMORY_NAMESPACE,
    )
    bot = create_bot()
    bot.infinity_polling(
        timeout=60,
        long_polling_timeout=60,
        skip_pending=True,
    )


if __name__ == "__main__":
    main()
