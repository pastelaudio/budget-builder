"""Packages gui.py into a standalone Windows executable using PyInstaller.

Usage:
    python build_exe.py

Output: dist/BudgetBuilder.exe
"""
import os

import PyInstaller.__main__

ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")

PyInstaller.__main__.run(
    [
        "gui.py",
        "--name=BudgetBuilder",
        "--onefile",
        "--windowed",
        "--clean",
        "--icon=assets/icon.ico",
        f"--add-data={ASSETS_DIR}{os.pathsep}assets",
    ]
)
