"""Загрузка и индексация файлов через Docling."""

from __future__ import annotations

import logging
from pathlib import Path

import telebot
from telebot import types

from bot.context import ingestion_service
from bot.messaging import base_user_metadata, send_long_message

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = frozenset(
    {
        ".pdf",
        ".docx",
        ".doc",
        ".pptx",
        ".ppt",
        ".html",
        ".htm",
        ".md",
        ".xlsx",
        ".xls",
        ".csv",
        ".png",
        ".jpg",
        ".jpeg",
        ".tiff",
        ".bmp",
        ".webp",
    }
)

MAX_FILE_BYTES = 20 * 1024 * 1024


def _resolve_file_name(message: types.Message) -> str | None:
    if message.document:
        name = message.document.file_name or f"document_{message.document.file_unique_id}"
        return name
    return None


def register(bot: telebot.TeleBot) -> None:
    @bot.message_handler(content_types=["document"])
    def handle_document(message: types.Message) -> None:
        user = message.from_user
        if user is None or message.document is None:
            return

        file_name = _resolve_file_name(message)
        if not file_name:
            bot.send_message(message.chat.id, "Не удалось определить имя файла.")
            return

        suffix = Path(file_name).suffix.lower()
        if suffix and suffix not in SUPPORTED_EXTENSIONS:
            bot.send_message(
                message.chat.id,
                f"Формат «{suffix}» пока не поддерживается. "
                f"Пришли PDF, DOCX, HTML, изображение или другой офисный документ.",
            )
            return

        if message.document.file_size and message.document.file_size > MAX_FILE_BYTES:
            bot.send_message(
                message.chat.id,
                "Файл слишком большой (лимит 20 МБ). Пришли документ меньшего размера.",
            )
            return

        bot.send_message(
            message.chat.id,
            "Файл получен. Запускаю анализ и сохранение. Это может занять немного времени…",
        )
        bot.send_chat_action(message.chat.id, "typing")

        try:
            file_info = bot.get_file(message.document.file_id)
            downloaded = bot.download_file(file_info.file_path)
            file_bytes = bytes(downloaded)

            extra_meta = base_user_metadata(message)
            result, summary = ingestion_service.ingest_file(
                file_bytes=file_bytes,
                file_name=file_name,
                user_id=user.id,
                chat_id=message.chat.id,
                extra_meta=extra_meta,
            )

            if result.documents_written <= 0:
                bot.send_message(
                    message.chat.id,
                    "Не удалось извлечь содержимое из файла. Попробуй другой формат или файл.",
                )
                return

            bot.send_message(
                message.chat.id,
                "Готово. Я изучил этот файл, теперь можем его обсудить.",
            )
            send_long_message(bot, message.chat.id, summary)
        except Exception:
            logger.exception(
                "Ошибка обработки документа user_id=%s file=%s",
                user.id,
                file_name,
            )
            bot.send_message(
                message.chat.id,
                "Не удалось обработать файл. Попробуй позже или пришли другой документ.",
            )
