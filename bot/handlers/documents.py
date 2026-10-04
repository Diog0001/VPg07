"""Загрузка и индексация файлов через Docling."""

from __future__ import annotations

import logging
from pathlib import Path

import telebot
from telebot import types

from bot.context import ingestion_service
from bot.document_focus import register_upload
from bot.messaging import base_user_metadata, send_long_message
from bot.progress import edit_progress, render_progress_bar

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

        chat_id = message.chat.id
        progress_msg = bot.send_message(
            chat_id,
            render_progress_bar(0.05, "Скачивание файла…"),
        )
        last_text = [progress_msg.text or ""]

        def on_progress(label: str, ratio: float) -> None:
            edit_progress(
                bot,
                chat_id,
                progress_msg.message_id,
                ratio=ratio,
                label=label,
                last_text=last_text,
            )

        try:
            on_progress("Скачивание файла…", 0.08)
            file_info = bot.get_file(message.document.file_id)
            downloaded = bot.download_file(file_info.file_path)
            file_bytes = bytes(downloaded)

            extra_meta = base_user_metadata(message)
            result, summary = ingestion_service.ingest_file(
                file_bytes=file_bytes,
                file_name=file_name,
                user_id=user.id,
                chat_id=chat_id,
                extra_meta=extra_meta,
                progress=on_progress,
            )

            if result.documents_written <= 0:
                bot.edit_message_text(
                    "Не удалось извлечь содержимое из файла. Попробуй другой формат или файл.",
                    chat_id,
                    progress_msg.message_id,
                )
                return

            register_upload(user.id, file_name)

            if summary:
                final_text = (
                    f"Готово. Я изучил «{file_name}» — он выбран для вопросов.\n\n"
                    f"{summary}\n\n"
                    "Команда /files — переключить другой загруженный файл."
                )
            else:
                final_text = (
                    f"Готово. Файл «{file_name}» сохранён ({result.documents_written} фрагментов). "
                    "Краткое резюме по тексту сформировать не удалось — можно задавать вопросы по документу.\n\n"
                    "Команда /files — переключить файл."
                )

            try:
                bot.edit_message_text(final_text[:4000], chat_id, progress_msg.message_id)
            except telebot.apihelper.ApiTelegramException:
                send_long_message(bot, chat_id, final_text)
            if len(final_text) > 4000:
                send_long_message(bot, chat_id, final_text[4000:])
        except Exception:
            logger.exception(
                "Ошибка обработки документа user_id=%s file=%s",
                user.id,
                file_name,
            )
            try:
                bot.edit_message_text(
                    "Не удалось обработать файл. Попробуй позже или пришли другой документ.",
                    chat_id,
                    progress_msg.message_id,
                )
            except telebot.apihelper.ApiTelegramException:
                bot.send_message(
                    chat_id,
                    "Не удалось обработать файл. Попробуй позже или пришли другой документ.",
                )
