#!/usr/bin/env python3
"""Bootstrap script: install dependencies, initialize database, set up directories."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent

DATA_DIRS = [
    "data/browser_profiles",
    "data/identities",
    "data/sessions",
    "data/telemetry",
    "data/telemetry/traces",
]


def create_directories() -> None:
    print("Creating data directories...")
    for d in DATA_DIRS:
        path = PROJECT_ROOT / d
        path.mkdir(parents=True, exist_ok=True)
        print(f"  ✓ {path}")


def install_dependencies() -> None:
    print("\nInstalling Python dependencies (uv)...")
    subprocess.check_call([
        "uv", "pip", "install",
        "-e", str(PROJECT_ROOT) + "[dev]",
    ])


def install_playwright() -> None:
    print("\nInstalling Playwright browsers (uv)...")
    subprocess.check_call([
        "uv", "run",
        "python", "-m", "playwright", "install", "chromium"
    ])


def initialize_database() -> None:
    print("\nInitializing database...")
    sys.path.insert(0, str(PROJECT_ROOT / "src"))
    from storage.sqlite import SQLiteDatabase

    db = SQLiteDatabase(PROJECT_ROOT / "data" / "pdp.db")
    db.initialize()
    db.close()

    print("  ✓ Database created at data/pdp.db")


def main() -> None:
    print("=== PDP Bootstrap ===\n")
    create_directories()
    install_dependencies()
    install_playwright()
    initialize_database()
    print("\n=== Bootstrap complete ===")
    print("Run with: uv run python src/app.py --profile desktop --dry-run")


if __name__ == "__main__":
    main()