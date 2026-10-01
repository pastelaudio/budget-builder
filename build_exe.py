"""Packages gui.py into a standalone Windows executable using PyInstaller.

Usage:
    python build_exe.py

Output: dist/BudgetBuilder.exe
"""
import PyInstaller.__main__

PyInstaller.__main__.run(
    [
        "gui.py",
        "--name=BudgetBuilder",
        "--onefile",
        "--windowed",
        "--clean",
    ]
)
