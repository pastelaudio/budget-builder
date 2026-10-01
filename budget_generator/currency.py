"""Shared currency symbol table used by the GUI, Excel writer, and Sheets writer."""
from __future__ import annotations

CURRENCIES: dict[str, str] = {
    "USD": "$",
    "EUR": "€",
    "GBP": "£",
    "CAD": "$",
    "AUD": "$",
    "JPY": "¥",
    "INR": "₹",
    "CHF": "CHF",
    "MXN": "$",
    "BRL": "R$",
}

DEFAULT_CURRENCY = "USD"


def symbol_for(currency_code: str) -> str:
    return CURRENCIES.get(currency_code, CURRENCIES[DEFAULT_CURRENCY])


def excel_number_format(currency_code: str) -> str:
    symbol = symbol_for(currency_code)
    return f'"{symbol}"#,##0.00'
