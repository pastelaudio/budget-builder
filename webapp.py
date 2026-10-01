"""Flask API + static host for the Budget Builder web app.

Local/LAN use (e.g. from an iPad on the same Wi-Fi):
    python webapp.py
    -> open http://<this-computer's-LAN-IP>:5000 on the iPad

Split deployment (frontend on Netlify, this backend elsewhere e.g. Render):
    - Deploy the web/ folder as a static site on Netlify.
    - Deploy this file (with requirements.txt + Procfile) to a Python host.
    - Set API_BASE_URL in web/app.js to this backend's public URL.
    - CORS is enabled below so the Netlify-hosted frontend can call this API.
"""
from __future__ import annotations

import io
import os

from flask import Flask, jsonify, request, send_file, send_from_directory
from flask_cors import CORS

from budget_generator.currency import CURRENCIES, DEFAULT_CURRENCY
from budget_generator.excel_writer import build_workbook

WEB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")
MAX_ROWS = 200  # guard against pathological payloads

app = Flask(__name__, static_folder=WEB_DIR, static_url_path="")
CORS(app, resources={r"/export/*": {"origins": "*"}})


def _parse_incomes(raw: list) -> list[tuple[str, float]]:
    incomes = []
    for item in raw[:MAX_ROWS]:
        name = str(item.get("name", "")).strip()
        if not name:
            continue
        incomes.append((name, _safe_float(item.get("amount"))))
    return incomes


def _parse_expenses(raw: list) -> list[tuple[str, float, float]]:
    expenses = []
    for item in raw[:MAX_ROWS]:
        name = str(item.get("name", "")).strip()
        if not name:
            continue
        expenses.append((name, _safe_float(item.get("budgeted")), _safe_float(item.get("actual"))))
    return expenses


def _safe_float(value) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


@app.route("/")
def index():
    return send_from_directory(WEB_DIR, "index.html")


@app.route("/export/excel", methods=["POST"])
def export_excel():
    data = request.get_json(force=True, silent=True) or {}
    month = str(data.get("month") or "Budget")[:100]
    currency = data.get("currency") if data.get("currency") in CURRENCIES else DEFAULT_CURRENCY
    incomes = _parse_incomes(data.get("incomes", []))
    expenses = _parse_expenses(data.get("expenses", []))

    wb = build_workbook(month, incomes, expenses, currency)
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    filename = f"Budget_{month.replace(' ', '_')}.xlsx"
    return send_file(
        buf,
        as_attachment=True,
        download_name=filename,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@app.route("/export/sheets", methods=["POST"])
def export_sheets():
    from budget_generator.sheets_writer import create_budget_sheet

    data = request.get_json(force=True, silent=True) or {}
    month = str(data.get("month") or "Budget")[:100]
    currency = data.get("currency") if data.get("currency") in CURRENCIES else DEFAULT_CURRENCY
    incomes = _parse_incomes(data.get("incomes", []))
    expenses = _parse_expenses(data.get("expenses", []))

    try:
        url = create_budget_sheet(month, incomes, expenses, currency=currency)
        return jsonify({"url": url})
    except FileNotFoundError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:  # surfaced to the browser instead of a 500 stack trace
        return jsonify({"error": str(exc)}), 500


def main():
    # host="0.0.0.0" so other devices on the same Wi-Fi (like an iPad) can reach it.
    # Only run this on a trusted home/office network -- anyone on the LAN could use it.
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)


if __name__ == "__main__":
    main()
