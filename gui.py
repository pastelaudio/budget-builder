"""Tkinter front-end for Budget Builder.

Lets the user edit income sources and expense categories, then export the
same budget layout either as an .xlsx file or directly to a new Google Sheet.
"""
from __future__ import annotations

import datetime
import os
import sys
import tkinter as tk
import traceback
import webbrowser
from tkinter import filedialog, messagebox, ttk

from budget_generator.currency import CURRENCIES, DEFAULT_CURRENCY, symbol_for
from budget_generator.excel_writer import save_workbook
from budget_generator.layout import DEFAULT_EXPENSES, DEFAULT_INCOME
from budget_generator import session_store

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

    def __init__(self, parent, columns: list[str], theme: dict, on_change=None):
        super().__init__(parent)
        self.columns = columns
        self.theme = theme
        self.on_change = on_change
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
            if self.on_change:
                entry.bind("<KeyRelease>", self.on_change)
            entries.append(entry)

        def remove():
            for e in entries:
                e.destroy()
            remove_btn.destroy()
            self.entry_rows.remove(entries)
            if self.on_change:
                self.on_change()

        remove_btn = ttk.Button(self.rows_frame, text="x", width=2, command=remove)
        remove_btn.grid(row=row_index, column=len(self.columns), padx=2)
        self.entry_rows.append(entries)
        if self.on_change:
            self.on_change()

    def clear(self):
        for entries in list(self.entry_rows):
            for e in entries:
                e.destroy()
        self.entry_rows.clear()
        for child in self.rows_frame.winfo_children():
            child.destroy()

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
        self._autosave_job = None
        self.pack(fill="both", expand=True)
        self._build_ui()
        self.apply_theme(self.theme_name)
        self._load_last_session()

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
        self.currency_combo.bind("<<ComboboxSelected>>", lambda _e: (self.refresh_chart(), self.schedule_autosave()))
        self.theme_button = ttk.Button(top, text="☀ Light mode", command=self.toggle_theme)
        self.theme_button.pack(side="right")

        saved_row = ttk.Frame(self)
        saved_row.pack(fill="x", pady=(0, 10))
        ttk.Label(saved_row, text="Saved months:").pack(side="left")
        self.saved_months_var = tk.StringVar()
        self.saved_months_combo = ttk.Combobox(
            saved_row, textvariable=self.saved_months_var, values=session_store.list_months(),
            width=20, state="readonly",
        )
        self.saved_months_combo.pack(side="left", padx=6)
        ttk.Button(saved_row, text="Load", command=self.load_selected_month).pack(side="left", padx=2)
        ttk.Button(saved_row, text="🗑 Delete", command=self.delete_selected_month).pack(side="left", padx=2)

        ttk.Label(self, text="Income", font=("Segoe UI", 11, "bold")).pack(anchor="w")
        self.income_editor = RowEditor(self, ["Source", "Amount"], THEMES[self.theme_name], on_change=self.schedule_autosave)
        self.income_editor.pack(fill="x", pady=(0, 10))
        for name, amount in DEFAULT_INCOME:
            self.income_editor.add_row((name, amount))

        ttk.Label(self, text="Expenses", font=("Segoe UI", 11, "bold")).pack(anchor="w")
        self.expense_editor = RowEditor(
            self, ["Category", "Budgeted", "Actual"], THEMES[self.theme_name], on_change=self.schedule_autosave
        )
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
        self.month_entry.bind("<KeyRelease>", self.schedule_autosave)
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

    def schedule_autosave(self, _event=None):
        if self._autosave_job is not None:
            self.after_cancel(self._autosave_job)
        self._autosave_job = self.after(800, self._do_autosave)

    def _do_autosave(self):
        self._autosave_job = None
        month_label, incomes, expenses = self._collect_data()
        if not month_label:
            return
        session_store.save_session(month_label, self.currency_var.get(), incomes, expenses)
        self._refresh_saved_months(keep_selection=month_label)

    def _refresh_saved_months(self, keep_selection: str | None = None):
        months = session_store.list_months()
        self.saved_months_combo.configure(values=months)
        if keep_selection in months:
            self.saved_months_var.set(keep_selection)

    def _load_last_session(self):
        self._refresh_saved_months()
        latest = session_store.latest_month()
        if latest:
            self.load_month_data(latest)

    def load_month_data(self, month: str):
        data = session_store.load_session(month)
        if not data:
            return
        self.month_entry.delete(0, tk.END)
        self.month_entry.insert(0, month)
        if data.get("currency") in CURRENCIES:
            self.currency_var.set(data["currency"])
        self.income_editor.clear()
        for row in data.get("incomes", []):
            self.income_editor.add_row(tuple(row))
        self.expense_editor.clear()
        for row in data.get("expenses", []):
            self.expense_editor.add_row(tuple(row))
        self.saved_months_var.set(month)
        self.refresh_chart()
        self.status.config(text=f"Loaded saved session: {month}")

    def load_selected_month(self):
        month = self.saved_months_var.get()
        if month:
            self.load_month_data(month)

    def delete_selected_month(self):
        month = self.saved_months_var.get()
        if not month:
            return
        if messagebox.askyesno(APP_TITLE, f"Delete saved session for '{month}'?"):
            session_store.delete_session(month)
            self.saved_months_var.set("")
            self._refresh_saved_months()
            self.status.config(text=f"Deleted saved session: {month}")

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
            session_store.save_session(month_label, self.currency_var.get(), incomes, expenses)
            self._refresh_saved_months(keep_selection=month_label)
            self.status.config(text=f"Saved: {path}")
            messagebox.showinfo(APP_TITLE, f"Excel budget saved to:\n{path}")
        except Exception as exc:  # surfaced to the user instead of crashing the GUI
            traceback.print_exc()
            messagebox.showerror(APP_TITLE, f"Failed to save workbook:\n{exc}")

    def export_google_sheets(self):
        month_label, incomes, expenses = self._collect_data()
        session_store.save_session(month_label, self.currency_var.get(), incomes, expenses)
        self._refresh_saved_months(keep_selection=month_label)
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
    # PyInstaller onefile builds extract bundled data to sys._MEIPASS at runtime.
    base_dir = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    icon_path = os.path.join(base_dir, "assets", "icon.ico")
    if os.path.exists(icon_path):
        try:
            root.iconbitmap(icon_path)
        except tk.TclError:
            pass  # icon format unsupported on this platform (e.g. non-Windows)
    BudgetBuilderApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
