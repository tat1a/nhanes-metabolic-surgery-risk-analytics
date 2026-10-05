"""Run SQL validation checks against processed NHANES outputs."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = ROOT / "data" / "processed"
DB_PATH = PROCESSED_DIR / "nhanes_metabolic_surgery.sqlite"
SQL_PATH = ROOT / "pipeline" / "04_sql_validation.sql"
OUTPUT_PATH = PROCESSED_DIR / "sql_validation_summary.csv"


def main() -> None:
    query = SQL_PATH.read_text(encoding="utf-8")
    with sqlite3.connect(DB_PATH) as conn:
        result = pd.read_sql_query(query, conn)
    result.to_csv(OUTPUT_PATH, index=False)
    print(f"Wrote SQL validation summary: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
