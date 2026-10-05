"""Build a SQLite database from processed NHANES reporting tables."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = ROOT / "data" / "processed"
DB_PATH = PROCESSED_DIR / "nhanes_metabolic_surgery.sqlite"

TABLES = {
    "analytic_cohort": "analytic_cohort.csv",
    "dashboard_kpis": "dashboard_kpis.csv",
    "eligibility_summary": "eligibility_summary.csv",
    "cardiometabolic_risk_summary": "cardiometabolic_risk_summary.csv",
    "eligibility_by_age_group": "eligibility_by_age_group.csv",
    "eligibility_by_sex": "eligibility_by_sex.csv",
    "eligibility_by_race_ethnicity": "eligibility_by_race_ethnicity.csv",
    "eligibility_by_bmi_category": "eligibility_by_bmi_category.csv",
    "missingness_summary": "missingness_summary.csv",
    "cohort_flow": "cohort_flow.csv",
}


def main() -> None:
    if DB_PATH.exists():
        DB_PATH.unlink()
    with sqlite3.connect(DB_PATH) as conn:
        for table, filename in TABLES.items():
            path = PROCESSED_DIR / filename
            frame = pd.read_csv(path)
            frame.to_sql(table, conn, index=False, if_exists="replace")
    print(f"Built SQLite database: {DB_PATH}")


if __name__ == "__main__":
    main()
