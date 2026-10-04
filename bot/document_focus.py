"""Какой загруженный файл считается «активным» для вопросов пользователя."""

from __future__ import annotations

from collections import defaultdict

_user_file_order: dict[int, list[str]] = defaultdict(list)
_user_active_file: dict[int, str] = {}


def _unique_append(user_id: int, file_name: str) -> None:
    names = _user_file_order[user_id]
    if file_name in names:
        names.remove(file_name)
    names.append(file_name)


def register_upload(user_id: int, file_name: str) -> None:
    _unique_append(user_id, file_name)
    _user_active_file[user_id] = file_name


def list_user_files(user_id: int) -> list[str]:
    return list(_user_file_order[user_id])


def get_active_file(user_id: int) -> str | None:
    return _user_active_file.get(user_id)


def set_active_file(user_id: int, file_name: str) -> bool:
    names = _user_file_order[user_id]
    if file_name not in names:
        return False
    _user_active_file[user_id] = file_name
    return True


def clear_user_files(user_id: int) -> None:
    _user_file_order.pop(user_id, None)
    _user_active_file.pop(user_id, None)
