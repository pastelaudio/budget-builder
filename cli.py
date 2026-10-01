"""Headless CLI: generate the budget workbook without launching the GUI.

Example:
    python cli.py --month "November 2026" --out budget_nov.xlsx
"""
from __future__ import annotations

import argparse

from budget_generator.currency import CURRENCIES, DEFAULT_CURRENCY
from budget_generator.excel_writer import save_workbook
from budget_generator.layout import DEFAULT_EXPENSES, DEFAULT_INCOME


def main():
    parser = argparse.ArgumentParser(description="Generate a monthly budget Excel workbook.")
    parser.add_argument("--month", default="This Month", help="Label shown in the workbook title, e.g. 'October 2026'")
    parser.add_argument("--out", default="budget.xlsx", help="Output .xlsx file path")
    parser.add_argument(
        "--currency", default=DEFAULT_CURRENCY, choices=sorted(CURRENCIES), help="Currency code for formatting amounts"
    )
    parser.add_argument("--sheets", action="store_true", help="Also push the budget to a new Google Sheet")
    args = parser.parse_args()

    save_workbook(args.out, args.month, DEFAULT_INCOME, DEFAULT_EXPENSES, args.currency)
    print(f"Saved Excel budget to {args.out}")

    if args.sheets:
        from budget_generator.sheets_writer import create_budget_sheet

        url = create_budget_sheet(args.month, DEFAULT_INCOME, DEFAULT_EXPENSES, currency=args.currency)
        print(f"Created Google Sheet: {url}")


if __name__ == "__main__":
    main()
