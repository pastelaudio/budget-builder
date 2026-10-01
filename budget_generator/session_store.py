"""Local JSON-backed session cache so the GUI remembers each month's budget
between runs (income/expense rows, currency) without needing a database.

Stored at ~/.budget_builder/sessions.json as:
    {"<month label>": {"currency": "USD", "incomes": [[name, amount], ...],
                        "expenses": [[name, budgeted, actual], ...],
                        "saved_at": "2026-10-01T12:00:00"}}
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

STORE_DIR = os.path.join(os.path.expanduser("~"), ".budget_builder")
STORE_PATH = os.path.join(STORE_DIR, "sessions.json")


def _load_all() -> dict:
    if not os.path.exists(STORE_PATH):
        return {}
    try:
        with open(STORE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def _write_all(data: dict) -> None:
    os.makedirs(STORE_DIR, exist_ok=True)
    tmp_path = STORE_PATH + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp_path, STORE_PATH)


def list_months() -> list[str]:
    """Months with a saved session, most recently saved first."""
    data = _load_all()
    return sorted(data, key=lambda m: data[m].get("saved_at", ""), reverse=True)


def load_session(month: str) -> dict | None:
    return _load_all().get(month)


def save_session(
    month: str,
    currency: str,
    incomes: list[tuple[str, float]],
    expenses: list[tuple[str, float, float]],
) -> None:
    data = _load_all()
    data[month] = {
        "currency": currency,
        "incomes": [list(row) for row in incomes],
        "expenses": [list(row) for row in expenses],
        "saved_at": datetime.now(timezone.utc).isoformat(),
    }
    _write_all(data)


def delete_session(month: str) -> None:
    data = _load_all()
    if month in data:
        del data[month]
        _write_all(data)


def latest_month() -> str | None:
    months = list_months()
    return months[0] if months else None
