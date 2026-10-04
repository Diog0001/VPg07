"""Выбор активного загруженного файла для RAG."""

from __future__ import annotations

import logging

import telebot
from telebot import types

from bot.document_focus import get_active_file, list_user_files, set_active_file

logger = logging.getLogger(__name__)

CALLBACK_PREFIX = "docfocus:"


def _build_keyboard(user_id: int) -> types.InlineKeyboardMarkup | None:
    files = list_user_files(user_id)
    if not files:
        return None
    active = get_active_file(user_id)
    markup = types.InlineKeyboardMarkup()
    for index, name in enumerate(files):
        label = name if len(name) <= 48 else f"{name[:45]}…"
        if name == active:
            label = f"✓ {label}"
        markup.add(
            types.InlineKeyboardButton(
                text=label,
                callback_data=f"{CALLBACK_PREFIX}{index}",
            )
        )
    return markup


def register(bot: telebot.TeleBot) -> None:
    @bot.message_handler(commands=["files"])
    def handle_files(message: types.Message) -> None:
        user = message.from_user
        if user is None:
            return
        files = list_user_files(user.id)
        if not files:
            bot.send_message(
                message.chat.id,
                "Пока нет загруженных файлов в этой сессии бота. Пришли PDF или другой документ.",
            )
            return
        active = get_active_file(user.id)
        header = "Выбери файл, по которому отвечать на вопросы:"
        if active:
            header += f"\n\nСейчас активен: «{active}»"
        keyboard = _build_keyboard(user.id)
        bot.send_message(message.chat.id, header, reply_markup=keyboard)

    @bot.callback_query_handler(func=lambda call: call.data and call.data.startswith(CALLBACK_PREFIX))
    def handle_file_pick(call: types.CallbackQuery) -> None:
        user = call.from_user
        if user is None or call.message is None:
            return
        try:
            index = int(call.data[len(CALLBACK_PREFIX) :])
        except ValueError:
            bot.answer_callback_query(call.id, "Некорректный выбор.")
            return

        files = list_user_files(user.id)
        if index < 0 or index >= len(files):
            bot.answer_callback_query(call.id, "Файл не найден.")
            return

        chosen = files[index]
        set_active_file(user.id, chosen)
        bot.answer_callback_query(call.id, f"Активен: {chosen}")
        try:
            bot.edit_message_text(
                f"Активный файл для вопросов: «{chosen}»\n\n"
                "Можешь писать вопросы по этому документу.",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=_build_keyboard(user.id),
            )
        except Exception:
            logger.debug("Не удалось обновить сообщение выбора файла", exc_info=True)
