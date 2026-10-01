"""Shared budget layout logic used by both the Excel and Google Sheets writers.

Both writers consume the same row plan so the spreadsheet structure (and the
cell references the formulas point at) stay identical between formats.
"""
from __future__ import annotations

from dataclasses import dataclass, field

DEFAULT_INCOME: list[tuple[str, float]] = [
    ("Primary Income", 0.0),
    ("Other Income", 0.0),
]

DEFAULT_EXPENSES: list[tuple[str, float, float]] = [
    ("Rent / Mortgage", 0.0, 0.0),
    ("Utilities", 0.0, 0.0),
    ("Groceries", 0.0, 0.0),
    ("Transportation", 0.0, 0.0),
    ("Insurance", 0.0, 0.0),
    ("Debt Payments", 0.0, 0.0),
    ("Subscriptions", 0.0, 0.0),
    ("Entertainment", 0.0, 0.0),
    ("Savings", 0.0, 0.0),
    ("Miscellaneous", 0.0, 0.0),
]


@dataclass
class Cell:
    value: object = ""
    is_formula: bool = False
    style: str = "normal"  # normal | title | header | section | total | summary


@dataclass
class RowPlan:
    rows: list[list[Cell]] = field(default_factory=list)
    # 1-based row numbers for key sections, used by writers for formatting/references
    income_start_row: int = 0
    income_end_row: int = 0
    total_income_row: int = 0
    expense_start_row: int = 0
    expense_end_row: int = 0
    total_expense_row: int = 0
    remaining_row: int = 0
    savings_rate_row: int = 0


def build_row_plan(
    month_label: str,
    incomes: list[tuple[str, float]],
    expenses: list[tuple[str, float, float]],
) -> RowPlan:
    """Build the full row-by-row layout for the budget sheet.

    Column layout: A=Name, B=Planned/Budgeted, C=Actual, D=Difference
    """
    plan = RowPlan()
    rows = plan.rows

    def add_row(cells: list[Cell]) -> int:
        rows.append(cells)
        return len(rows)  # 1-based row number

    add_row([Cell(f"Monthly Budget - {month_label}", style="title")])
    add_row([Cell("")])

    add_row([Cell("INCOME", style="section")])
    add_row([Cell("Source", style="header"), Cell("Amount", style="header")])
    plan.income_start_row = len(rows) + 1
    for name, amount in incomes:
        add_row([Cell(name), Cell(amount)])
    plan.income_end_row = len(rows)
    plan.total_income_row = add_row(
        [
            Cell("Total Income", style="total"),
            Cell(f"=SUM(B{plan.income_start_row}:B{plan.income_end_row})", is_formula=True, style="total"),
        ]
    )
    add_row([Cell("")])

    add_row([Cell("EXPENSES", style="section")])
    add_row(
        [
            Cell("Category", style="header"),
            Cell("Budgeted", style="header"),
            Cell("Actual", style="header"),
            Cell("Difference", style="header"),
        ]
    )
    plan.expense_start_row = len(rows) + 1
    for name, budgeted, actual in expenses:
        row_num = len(rows) + 1
        add_row(
            [
                Cell(name),
                Cell(budgeted),
                Cell(actual),
                Cell(f"=B{row_num}-C{row_num}", is_formula=True),
            ]
        )
    plan.expense_end_row = len(rows)
    plan.total_expense_row = add_row(
        [
            Cell("Total Expenses", style="total"),
            Cell(f"=SUM(B{plan.expense_start_row}:B{plan.expense_end_row})", is_formula=True, style="total"),
            Cell(f"=SUM(C{plan.expense_start_row}:C{plan.expense_end_row})", is_formula=True, style="total"),
            Cell(f"=SUM(D{plan.expense_start_row}:D{plan.expense_end_row})", is_formula=True, style="total"),
        ]
    )
    add_row([Cell("")])

    add_row([Cell("SUMMARY", style="section")])
    add_row([Cell("Total Income", style="header"), Cell(f"=B{plan.total_income_row}", is_formula=True)])
    add_row([Cell("Total Expenses (Actual)", style="header"), Cell(f"=C{plan.total_expense_row}", is_formula=True)])
    plan.remaining_row = add_row(
        [
            Cell("Remaining Balance", style="summary"),
            Cell(
                f"=B{plan.total_income_row}-C{plan.total_expense_row}",
                is_formula=True,
                style="summary",
            ),
        ]
    )
    plan.savings_rate_row = add_row(
        [
            Cell("Savings Rate", style="summary"),
            Cell(
                f"=IF(B{plan.total_income_row}=0,0,(B{plan.total_income_row}-C{plan.total_expense_row})/B{plan.total_income_row})",
                is_formula=True,
                style="summary",
            ),
        ]
    )

    return plan
