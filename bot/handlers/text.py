"""Обработка текстовых сообщений пользователя."""

from __future__ import annotations

import logging

import telebot
from telebot import types

from bot.context import (
    DOCUMENT_RETRIEVAL_TOP_K,
    MEMORY_KINDS_FOR_CONTEXT,
    MEMORY_RETRIEVAL_TOP_K,
    assistant,
)
from bot.document_focus import get_active_file
from bot.handlers import memory_store
from bot.messaging import maybe_send_dog_photo, send_long_message
from bot.session import append_session, get_session

logger = logging.getLogger(__name__)


def register(bot: telebot.TeleBot) -> None:
    @bot.message_handler(content_types=["text"])
    def handle_text(message: types.Message) -> None:
        if not message.text or message.text.startswith("/"):
            return

        user_text = message.text.strip()
        if not user_text:
            return

        user_id = message.from_user.id
        bot.send_chat_action(message.chat.id, "typing")

        try:
            memory_store.save_to_memory(message, user_text, kind="user_message")

            reply = assistant.generate_reply(
                user_id=user_id,
                user_text=user_text,
                session_messages=get_session(user_id),
                memory_kinds=MEMORY_KINDS_FOR_CONTEXT,
                memory_top_k=MEMORY_RETRIEVAL_TOP_K,
                document_top_k=DOCUMENT_RETRIEVAL_TOP_K,
                active_file_name=get_active_file(user_id),
            )

            memory_store.save_to_memory(message, reply, kind="assistant_message")
            append_session(user_id, user_text, reply)

            send_long_message(bot, message.chat.id, reply)
            maybe_send_dog_photo(bot, message.chat.id, reply)
        except Exception:
            logger.exception("Ошибка обработки сообщения user_id=%s", user_id)
            bot.send_message(
                message.chat.id,
                "Произошла ошибка при обработке сообщения. Попробуй ещё раз через минуту.",
            )
