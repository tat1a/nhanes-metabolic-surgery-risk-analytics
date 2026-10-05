# Pipeline Overview

This pipeline builds a reproducible NHANES 2017-March 2020 pre-pandemic analytic cohort for metabolic surgery eligibility and cardiometabolic risk phenotyping.

## Steps

1. Download public-use NHANES XPT files into `data/raw/`.
2. Merge tables by respondent sequence number (`SEQN`).
3. Restrict to adults age 20+.
4. Exclude pregnancy for the primary BMI-based cohort.
5. Engineer BMI category, diabetes, hypertension, dyslipidemia, central adiposity, and cardiometabolic risk-count flags.
6. Apply guideline-like metabolic surgery eligibility logic:
   - BMI >=35 kg/m2.
   - BMI 30-34.9 kg/m2 with a metabolic disease signal.
7. Export dashboard-ready processed tables.
8. Build a SQLite database and SQL validation summary.

## Run

```bash
python pipeline/build_nhanes_metabolic_surgery_dataset.py
python pipeline/build_sqlite_database.py
python pipeline/run_sql_validation.py
python pipeline/create_powerbi_previews.py
python -m unittest discover -s tests -v
```

The analysis uses public-use, de-identified survey data. It does not use patient records, PHI, MIMIC-IV, or restricted clinical data.
