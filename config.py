"""Пути проекта и загрузка переменных окружения."""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent
PACKAGE_ROOT = PROJECT_ROOT


def load_project_env() -> None:
    load_dotenv(PROJECT_ROOT / ".env")
