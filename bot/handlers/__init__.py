"""Регистрация обработчиков Telegram."""

from __future__ import annotations

import telebot

from bot.handlers import commands, documents, files, text as text_handlers


def register_handlers(bot: telebot.TeleBot) -> None:
    commands.register(bot)
    documents.register(bot)
    files.register(bot)
    text_handlers.register(bot)
