"""Команды /start, /help, /memory, /forget, /reset."""

from __future__ import annotations

import logging
import textwrap

import telebot
from telebot import types

from bot.context import (
    MEMORY_KINDS_FOR_CONTEXT,
    MEMORY_NAMESPACE,
    MEMORY_RETRIEVAL_TOP_K,
    memory,
)
from bot.handlers import memory_store
from bot.messaging import display_user_name, send_long_message
from components.memory_service import MEMORY_COSINE_SIMILARITY_THRESHOLD
from services.assistant import format_memory_block

logger = logging.getLogger(__name__)


def register(bot: telebot.TeleBot) -> None:
    @bot.message_handler(commands=["start", "help"])
    def handle_start(message: types.Message) -> None:
        user = message.from_user
        greeting = textwrap.dedent(
            f"""
            Привет, {display_user_name(user)}!

            Я персональный помощник v2 на Haystack: память в Pinecone, RAG по загруженным файлам
            (PDF, DOCX и др. через Docling) и диалог как у живого собеседника.

            Могу по запросу:
            • рассказать случайный факт о собаках (внешний API);
            • прислать фото собаки и описать породу через OpenAI Vision.

            Пришли документ — проанализирую, сохраню в базу и кратко расскажу содержание.

            Команды:
            /memory — что я помню о тебе и сколько фрагментов файлов сохранено
            /forget — удалить твою память и загруженные фрагменты документов
            /reset — очистить текущую сессию диалога
            /help — справка

            Просто пиши или присылай файлы — отвечу с учётом памяти, документов и истории чата.
            """
        ).strip()
        bot.send_message(message.chat.id, greeting)

        profile_bits = [f"Telegram id={user.id}", f"display_name={display_user_name(user)}"]
        if user.username:
            profile_bits.append(f"username=@{user.username}")
        memory_store.save_to_memory(message, "Профиль: " + ", ".join(profile_bits), kind="profile")

    @bot.message_handler(commands=["memory"])
    def handle_memory(message: types.Message) -> None:
        bot.send_chat_action(message.chat.id, "typing")
        user_id = message.from_user.id
        docs = memory.retrieve_relevant(
            user_id,
            "имя город работа хобби предпочтения факты профиль пользователя",
            top_k=MEMORY_RETRIEVAL_TOP_K,
            kinds=MEMORY_KINDS_FOR_CONTEXT,
        )
        block = format_memory_block(docs)
        count = memory.count_user_documents(user_id)
        doc_chunks = memory.count_document_chunks(user_id)
        footer = (
            f"\n\n<i>Порог дедупликации: {MEMORY_COSINE_SIMILARITY_THRESHOLD}</i>\n"
            f"<i>Namespace Pinecone: {MEMORY_NAMESPACE}</i>\n"
            f"<i>Записей памяти (все kind): {count}</i>\n"
            f"<i>Фрагментов документов: {doc_chunks}</i>"
        )
        send_long_message(bot, message.chat.id, block + footer)

    @bot.message_handler(commands=["forget"])
    def handle_forget(message: types.Message) -> None:
        user_id = message.from_user.id
        try:
            memory.delete_user_memory(user_id)
            from bot.session import reset_session

            reset_session(user_id)
            bot.send_message(
                message.chat.id,
                "Готово: память о тебе и все сохранённые фрагменты загруженных файлов удалены из Pinecone.",
            )
        except Exception:
            logger.exception("Ошибка удаления памяти user_id=%s", user_id)
            bot.send_message(
                message.chat.id,
                "Не удалось очистить память. Попробуй позже.",
            )

    @bot.message_handler(commands=["reset"])
    def handle_reset(message: types.Message) -> None:
        from bot.session import reset_session

        user_id = message.from_user.id
        reset_session(user_id)
        bot.send_message(
            message.chat.id,
            "Сессия диалога в памяти бота сброшена. Долговременная память в Pinecone сохранена.",
        )
