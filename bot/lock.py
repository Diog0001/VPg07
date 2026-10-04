"""Блокировка второго экземпляра polling (Telegram 409)."""

from __future__ import annotations

import atexit
import logging
import msvcrt
import os
import sys
from typing import TextIO

from config import PACKAGE_ROOT

logger = logging.getLogger(__name__)

_BOT_LOCK_PATH = PACKAGE_ROOT / ".bot.lock"
_bot_lock_file: TextIO | None = None


def acquire_single_instance_lock() -> None:
    global _bot_lock_file
    _bot_lock_file = open(_BOT_LOCK_PATH, "a+", encoding="utf-8")
    try:
        msvcrt.locking(_bot_lock_file.fileno(), msvcrt.LK_NBLCK, 1)
    except OSError:
        logger.error(
            "Уже запущен другой экземпляр бота v2. Остановите его и запустите снова."
        )
        sys.exit(1)

    _bot_lock_file.seek(0)
    _bot_lock_file.truncate()
    _bot_lock_file.write(str(os.getpid()))
    _bot_lock_file.flush()
    atexit.register(release_single_instance_lock)


def release_single_instance_lock() -> None:
    global _bot_lock_file
    if _bot_lock_file is None:
        return
    try:
        msvcrt.locking(_bot_lock_file.fileno(), msvcrt.LK_UNLCK, 1)
    except OSError:
        pass
    _bot_lock_file.close()
    _bot_lock_file = None
