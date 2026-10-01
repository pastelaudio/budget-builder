"""Push the same budget layout to a new Google Sheet via the Sheets API.

Requires a Google Cloud OAuth client (credentials.json) placed next to this
package or passed in explicitly -- see README.md for the one-time setup steps.
Authenticating opens a browser window the first time; a token.json cache is
then reused for subsequent runs.
"""
from __future__ import annotations

import os

from .currency import DEFAULT_CURRENCY, symbol_for
from .layout import DEFAULT_EXPENSES, DEFAULT_INCOME, build_row_plan

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

SECTION_COLOR = {"red": 0.12, "green": 0.31, "blue": 0.47}
HEADER_COLOR = {"red": 0.85, "green": 0.89, "blue": 0.95}
SUMMARY_COLOR = {"red": 0.89, "green": 0.94, "blue": 0.86}


def _get_credentials(credentials_path: str, token_path: str):
    # Imports are deferred so the Excel-only path never requires these optional deps.
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow

    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(credentials_path):
                raise FileNotFoundError(
                    f"Missing Google OAuth client file at '{credentials_path}'. "
                    "See README.md for how to create one in Google Cloud Console."
                )
            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, "w", encoding="utf-8") as token_file:
            token_file.write(creds.to_json())
    return creds


def create_budget_sheet(
    month_label: str,
    incomes: list[tuple[str, float]] | None = None,
    expenses: list[tuple[str, float, float]] | None = None,
    credentials_path: str = "credentials.json",
    token_path: str = "token.json",
    currency: str = DEFAULT_CURRENCY,
) -> str:
    """Creates a new Google Sheet with the budget layout and returns its URL."""
    from googleapiclient.discovery import build

    incomes = incomes or DEFAULT_INCOME
    expenses = expenses or DEFAULT_EXPENSES
    plan = build_row_plan(month_label, incomes, expenses)

    creds = _get_credentials(credentials_path, token_path)
    service = build("sheets", "v4", credentials=creds)

    spreadsheet = (
        service.spreadsheets()
        .create(body={"properties": {"title": f"Monthly Budget - {month_label}"}})
        .execute()
    )
    spreadsheet_id = spreadsheet["spreadsheetId"]
    sheet_id = spreadsheet["sheets"][0]["properties"]["sheetId"]

    values = [[cell.value for cell in row] for row in plan.rows]
    service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range="A1",
        valueInputOption="USER_ENTERED",
        body={"values": values},
    ).execute()

    requests = _build_format_requests(sheet_id, plan, currency)
    service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id, body={"requests": requests}
    ).execute()

    return f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit"


def _build_format_requests(sheet_id: int, plan, currency: str = DEFAULT_CURRENCY) -> list[dict]:
    def row_range(row_num: int, num_cols: int = 4) -> dict:
        return {
            "sheetId": sheet_id,
            "startRowIndex": row_num - 1,
            "endRowIndex": row_num,
            "startColumnIndex": 0,
            "endColumnIndex": num_cols,
        }

    def bg_request(row_num: int, color: dict, bold: bool = False, num_cols: int = 4) -> dict:
        fmt = {"backgroundColor": color}
        if bold:
            fmt["textFormat"] = {"bold": True}
        return {
            "repeatCell": {
                "range": row_range(row_num, num_cols),
                "cell": {"userEnteredFormat": fmt},
                "fields": "userEnteredFormat(backgroundColor,textFormat)",
            }
        }

    requests = []
    for row_cells, row_idx in zip(plan.rows, range(1, len(plan.rows) + 1)):
        style = row_cells[0].style if row_cells else "normal"
        if style == "section":
            requests.append(bg_request(row_idx, {"red": SECTION_COLOR["red"], "green": SECTION_COLOR["green"], "blue": SECTION_COLOR["blue"]}, bold=True))
        elif style == "header":
            requests.append(bg_request(row_idx, HEADER_COLOR, bold=True))
        elif style in ("total", "summary"):
            requests.append(bg_request(row_idx, SUMMARY_COLOR, bold=True))

    # Conditional formatting: highlight overspent categories (Difference < 0) in red.
    requests.append(
        {
            "addConditionalFormatRule": {
                "rule": {
                    "ranges": [
                        {
                            "sheetId": sheet_id,
                            "startRowIndex": plan.expense_start_row - 1,
                            "endRowIndex": plan.expense_end_row,
                            "startColumnIndex": 3,
                            "endColumnIndex": 4,
                        }
                    ],
                    "booleanRule": {
                        "condition": {"type": "NUMBER_LESS", "values": [{"userEnteredValue": "0"}]},
                        "format": {"backgroundColor": {"red": 0.96, "green": 0.8, "blue": 0.8}},
                    },
                },
                "index": 0,
            }
        }
    )

    requests.append(
        {
            "updateDimensionProperties": {
                "range": {"sheetId": sheet_id, "dimension": "COLUMNS", "startIndex": 0, "endIndex": 1},
                "properties": {"pixelSize": 220},
                "fields": "pixelSize",
            }
        }
    )

    # Currency formatting for every amount cell except the savings-rate percentage row.
    currency_pattern = f'"{symbol_for(currency)}"#,##0.00'
    requests.append(
        {
            "repeatCell": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": 0,
                    "endRowIndex": plan.savings_rate_row - 1,
                    "startColumnIndex": 1,
                    "endColumnIndex": 4,
                },
                "cell": {"userEnteredFormat": {"numberFormat": {"type": "CURRENCY", "pattern": currency_pattern}}},
                "fields": "userEnteredFormat.numberFormat",
            }
        }
    )
    requests.append(
        {
            "repeatCell": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": plan.savings_rate_row,
                    "endRowIndex": len(plan.rows),
                    "startColumnIndex": 1,
                    "endColumnIndex": 4,
                },
                "cell": {"userEnteredFormat": {"numberFormat": {"type": "CURRENCY", "pattern": currency_pattern}}},
                "fields": "userEnteredFormat.numberFormat",
            }
        }
    )
    requests.append(
        {
            "repeatCell": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": plan.savings_rate_row - 1,
                    "endRowIndex": plan.savings_rate_row,
                    "startColumnIndex": 1,
                    "endColumnIndex": 2,
                },
                "cell": {"userEnteredFormat": {"numberFormat": {"type": "PERCENT", "pattern": "0.0%"}}},
                "fields": "userEnteredFormat.numberFormat",
            }
        }
    )
    return requests
