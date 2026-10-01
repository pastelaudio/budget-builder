"""Tkinter front-end for Budget Builder.

Lets the user edit income sources and expense categories, then export the
same budget layout either as an .xlsx file or directly to a new Google Sheet.
"""
from __future__ import annotations

import datetime
import os
import tkinter as tk
import traceback
import webbrowser
from tkinter import filedialog, messagebox, ttk

from budget_generator.currency import CURRENCIES, DEFAULT_CURRENCY, symbol_for
from budget_generator.excel_writer import save_workbook
from budget_generator.layout import DEFAULT_EXPENSES, DEFAULT_INCOME

APP_TITLE = "Budget Builder"

THEMES = {
    "dark": {
        "bg": "#1e1e1e",
        "fg": "#e8e8e8",
        "entry_bg": "#2d2d2d",
        "entry_fg": "#f0f0f0",
        "entry_insert": "#ffffff",
        "accent": "#3a7ca5",
        "section_bg": "#2a2a2a",
        "button_bg": "#2d2d2d",
        "status_fg": "#7cd992",
    },
    "light": {
        "bg": "#f5f5f5",
        "fg": "#1a1a1a",
        "entry_bg": "#ffffff",
        "entry_fg": "#1a1a1a",
        "entry_insert": "#000000",
        "accent": "#1f4e78",
        "section_bg": "#eaeaea",
        "button_bg": "#e6e6e6",
        "status_fg": "#1a7a3c",
    },
}

PIE_COLORS = [
    "#4e79a7", "#f28e2b", "#e15759", "#76b7b2", "#59a14f",
    "#edc948", "#b07aa1", "#ff9da7", "#9c755f", "#bab0ac",
]


class RowEditor(ttk.Frame):
    """A dynamic list of labeled entry rows with add/remove buttons."""

    def __init__(self, parent, columns: list[str], theme: dict):
        super().__init__(parent)
        self.columns = columns
        self.theme = theme
        self.entry_rows: list[list[tk.Entry]] = []

        header = ttk.Frame(self)
        header.pack(fill="x")
        for i, col in enumerate(columns):
            ttk.Label(header, text=col, width=18 if i == 0 else 12, font=("Segoe UI", 9, "bold")).grid(
                row=0, column=i, padx=2
            )

        self.rows_frame = ttk.Frame(self)
        self.rows_frame.pack(fill="x")

        ttk.Button(self, text="+ Add row", command=self.add_row).pack(anchor="w", pady=4)

    def add_row(self, values: tuple | None = None):
        row_index = len(self.entry_rows)
        entries = []
        for col_index in range(len(self.columns)):
            width = 18 if col_index == 0 else 12
            entry = tk.Entry(
                self.rows_frame,
                width=width,
                bg=self.theme["entry_bg"],
                fg=self.theme["entry_fg"],
                insertbackground=self.theme["entry_insert"],
                relief="flat",
                highlightthickness=1,
                highlightbackground=self.theme["section_bg"],
            )
            entry.grid(row=row_index, column=col_index, padx=2, pady=2)
            if values:
                entry.insert(0, str(values[col_index]))
            entries.append(entry)

        def remove():
            for e in entries:
                e.destroy()
            remove_btn.destroy()
            self.entry_rows.remove(entries)

        remove_btn = ttk.Button(self.rows_frame, text="x", width=2, command=remove)
        remove_btn.grid(row=row_index, column=len(self.columns), padx=2)
        self.entry_rows.append(entries)

    def get_values(self) -> list[tuple]:
        rows = []
        for entries in self.entry_rows:
            values = [e.get().strip() for e in entries]
            if values[0]:
                rows.append(tuple(values))
        return rows

    def apply_theme(self, theme: dict):
        self.theme = theme
        for entries in self.entry_rows:
            for entry in entries:
                entry.configure(
                    bg=theme["entry_bg"],
                    fg=theme["entry_fg"],
                    insertbackground=theme["entry_insert"],
                    highlightbackground=theme["section_bg"],
                )


class BudgetBuilderApp(ttk.Frame):
    def __init__(self, master: tk.Tk):
        super().__init__(master, padding=12)
        self.master = master
        self.master.title(APP_TITLE)
        self.theme_name = "dark"
        self.style = ttk.Style(master)
        self.style.theme_use("clam")
        self.pack(fill="both", expand=True)
        self._build_ui()
        self.apply_theme(self.theme_name)

    def _build_ui(self):
        top = ttk.Frame(self)
        top.pack(fill="x", pady=(0, 10))
        ttk.Label(top, text="Month / Label:").pack(side="left")
        self.month_entry = tk.Entry(top, width=20)
        self.month_entry.insert(0, datetime.date.today().strftime("%B %Y"))
        self.month_entry.pack(side="left", padx=6)
        ttk.Label(top, text="Currency:").pack(side="left", padx=(10, 0))
        self.currency_var = tk.StringVar(value=DEFAULT_CURRENCY)
        self.currency_combo = ttk.Combobox(
            top, textvariable=self.currency_var, values=sorted(CURRENCIES), width=5, state="readonly"
        )
        self.currency_combo.pack(side="left", padx=6)
        self.currency_combo.bind("<<ComboboxSelected>>", lambda _e: self.refresh_chart())
        self.theme_button = ttk.Button(top, text="☀ Light mode", command=self.toggle_theme)
        self.theme_button.pack(side="right")

        ttk.Label(self, text="Income", font=("Segoe UI", 11, "bold")).pack(anchor="w")
        self.income_editor = RowEditor(self, ["Source", "Amount"], THEMES[self.theme_name])
        self.income_editor.pack(fill="x", pady=(0, 10))
        for name, amount in DEFAULT_INCOME:
            self.income_editor.add_row((name, amount))

        ttk.Label(self, text="Expenses", font=("Segoe UI", 11, "bold")).pack(anchor="w")
        self.expense_editor = RowEditor(self, ["Category", "Budgeted", "Actual"], THEMES[self.theme_name])
        self.expense_editor.pack(fill="x", pady=(0, 10))
        for name, budgeted, actual in DEFAULT_EXPENSES:
            self.expense_editor.add_row((name, budgeted, actual))

        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill="x", pady=10)
        ttk.Button(btn_frame, text="Export to Excel (.xlsx)", command=self.export_excel).pack(side="left", padx=4)
        ttk.Button(btn_frame, text="Export to Google Sheets", command=self.export_google_sheets).pack(
            side="left", padx=4
        )
        ttk.Button(btn_frame, text="📊 Refresh Chart", command=self.refresh_chart).pack(side="left", padx=4)

        ttk.Label(self, text="Expense Breakdown", font=("Segoe UI", 11, "bold")).pack(anchor="w")
        chart_frame = ttk.Frame(self)
        chart_frame.pack(fill="x", pady=(0, 10))
        self.chart_canvas = tk.Canvas(chart_frame, width=200, height=200, highlightthickness=0)
        self.chart_canvas.pack(side="left")
        self.legend_frame = ttk.Frame(chart_frame)
        self.legend_frame.pack(side="left", fill="both", expand=True, padx=10)

        self.status = ttk.Label(self, text="")
        self.status.pack(anchor="w")
        self.refresh_chart()

    def toggle_theme(self):
        self.theme_name = "light" if self.theme_name == "dark" else "dark"
        self.apply_theme(self.theme_name)

    def apply_theme(self, theme_name: str):
        t = THEMES[theme_name]
        self.master.configure(bg=t["bg"])
        self.configure(style="App.TFrame")

        style = self.style
        style.configure("App.TFrame", background=t["bg"])
        style.configure("TFrame", background=t["bg"])
        style.configure("TLabel", background=t["bg"], foreground=t["fg"])
        style.configure(
            "TButton",
            background=t["button_bg"],
            foreground=t["fg"],
            bordercolor=t["section_bg"],
            focuscolor=t["accent"],
        )
        style.map(
            "TButton",
            background=[("active", t["accent"])],
            foreground=[("active", t["fg"])],
        )
        style.configure(
            "TCombobox",
            fieldbackground=t["entry_bg"],
            background=t["entry_bg"],
            foreground=t["entry_fg"],
            arrowcolor=t["fg"],
        )
        self.master.option_add("*TCombobox*Listbox.background", t["entry_bg"])
        self.master.option_add("*TCombobox*Listbox.foreground", t["entry_fg"])

        self.month_entry.configure(
            bg=t["entry_bg"], fg=t["entry_fg"], insertbackground=t["entry_insert"], relief="flat"
        )
        self.status.configure(foreground=t["status_fg"])
        self.theme_button.configure(text="☀ Light mode" if theme_name == "dark" else "🌙 Dark mode")

        self.income_editor.apply_theme(t)
        self.expense_editor.apply_theme(t)

        self.chart_canvas.configure(bg=t["bg"])
        self.refresh_chart()


    def _collect_data(self):
        month_label = self.month_entry.get().strip() or datetime.date.today().strftime("%B %Y")
        incomes = [(name, _to_float(amount)) for name, amount in self.income_editor.get_values()]
        expenses = [
            (name, _to_float(budgeted), _to_float(actual))
            for name, budgeted, actual in self.expense_editor.get_values()
        ]
        return month_label, incomes, expenses

    def refresh_chart(self):
        t = THEMES[self.theme_name]
        _, _, expenses = self._collect_data()
        slices = [(name, actual if actual > 0 else budgeted) for name, budgeted, actual in expenses]
        slices = [(name, amount) for name, amount in slices if amount > 0]

        canvas = self.chart_canvas
        canvas.delete("all")
        for widget in self.legend_frame.winfo_children():
            widget.destroy()

        total = sum(amount for _, amount in slices)
        if total <= 0:
            canvas.create_text(
                100, 100, text="Add expense\namounts to see\nthe breakdown", fill=t["fg"], justify="center"
            )
            return

        start_angle = 90.0
        for i, (name, amount) in enumerate(slices):
            color = PIE_COLORS[i % len(PIE_COLORS)]
            extent = -360.0 * (amount / total)
            canvas.create_arc(
                10, 10, 190, 190,
                start=start_angle,
                extent=extent,
                fill=color,
                outline=t["bg"],
                width=2,
            )
            start_angle += extent

            pct = 100 * amount / total
            row = ttk.Frame(self.legend_frame)
            row.pack(fill="x", anchor="w")
            swatch = tk.Canvas(row, width=12, height=12, highlightthickness=0, bg=t["bg"])
            swatch.create_rectangle(0, 0, 12, 12, fill=color, outline=color)
            swatch.pack(side="left", padx=(0, 6))
            symbol = symbol_for(self.currency_var.get())
            ttk.Label(row, text=f"{name}: {symbol}{amount:,.2f} ({pct:.1f}%)").pack(side="left")

    def export_excel(self):
        month_label, incomes, expenses = self._collect_data()
        default_name = f"Budget_{month_label.replace(' ', '_')}.xlsx"
        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx", initialfile=default_name, filetypes=[("Excel Workbook", "*.xlsx")]
        )
        if not path:
            return
        try:
            save_workbook(path, month_label, incomes, expenses, self.currency_var.get())
            self.status.config(text=f"Saved: {path}")
            messagebox.showinfo(APP_TITLE, f"Excel budget saved to:\n{path}")
        except Exception as exc:  # surfaced to the user instead of crashing the GUI
            traceback.print_exc()
            messagebox.showerror(APP_TITLE, f"Failed to save workbook:\n{exc}")

    def export_google_sheets(self):
        month_label, incomes, expenses = self._collect_data()
        try:
            from budget_generator.sheets_writer import create_budget_sheet
        except ImportError as exc:
            messagebox.showerror(
                APP_TITLE,
                "Google Sheets export requires extra packages.\n"
                "Run: pip install -r requirements.txt\n\n" + str(exc),
            )
            return

        base_dir = os.path.dirname(os.path.abspath(__file__))
        credentials_path = os.path.join(base_dir, "credentials.json")
        token_path = os.path.join(base_dir, "token.json")
        try:
            url = create_budget_sheet(
                month_label,
                incomes,
                expenses,
                credentials_path=credentials_path,
                token_path=token_path,
                currency=self.currency_var.get(),
            )
            self.status.config(text=f"Created: {url}")
            if messagebox.askyesno(APP_TITLE, f"Google Sheet created:\n{url}\n\nOpen it now?"):
                webbrowser.open(url)
        except FileNotFoundError as exc:
            messagebox.showerror(APP_TITLE, str(exc))
        except Exception as exc:
            traceback.print_exc()
            messagebox.showerror(APP_TITLE, f"Failed to create Google Sheet:\n{exc}")


def _to_float(value: str) -> float:
    try:
        return float(str(value).replace(",", "").replace("$", "") or 0)
    except ValueError:
        return 0.0


def main():
    root = tk.Tk()
    root.geometry("620x900")
    BudgetBuilderApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
