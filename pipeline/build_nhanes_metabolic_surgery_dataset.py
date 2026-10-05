"""Build NHANES metabolic surgery eligibility and cardiometabolic risk outputs.

The pipeline downloads public-use NHANES 2017-March 2020 pre-pandemic XPT files,
creates an adult analytic cohort, engineers clinical phenotype flags, and exports
dashboard-ready reporting tables.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.request import urlretrieve

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
REPORTS_DIR = ROOT / "reports"

NHANES_BASE = "https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/{name}.XPT"


@dataclass(frozen=True)
class SourceFile:
    name: str
    description: str

    @property
    def url(self) -> str:
        return NHANES_BASE.format(name=self.name)

    @property
    def path(self) -> Path:
        return RAW_DIR / f"{self.name}.XPT"


SOURCES = [
    SourceFile("P_DEMO", "Demographics and sample weights"),
    SourceFile("P_BMX", "Body measures"),
    SourceFile("P_BPXO", "Oscillometric blood pressure"),
    SourceFile("P_GHB", "Glycohemoglobin"),
    SourceFile("P_TCHOL", "Total cholesterol"),
    SourceFile("P_HDL", "HDL cholesterol"),
    SourceFile("P_TRIGLY", "Triglycerides and LDL cholesterol"),
    SourceFile("P_DIQ", "Diabetes questionnaire"),
    SourceFile("P_BPQ", "Blood pressure and cholesterol questionnaire"),
]


RACE_MAP = {
    1: "Mexican American",
    2: "Other Hispanic",
    3: "Non-Hispanic White",
    4: "Non-Hispanic Black",
    6: "Non-Hispanic Asian",
    7: "Other / Multiracial",
}

SEX_MAP = {1: "Male", 2: "Female"}


def ensure_directories() -> None:
    for path in [RAW_DIR, PROCESSED_DIR, REPORTS_DIR]:
        path.mkdir(parents=True, exist_ok=True)


def download_sources() -> None:
    ensure_directories()
    for source in SOURCES:
        if not source.path.exists():
            urlretrieve(source.url, source.path)


def read_xpt(source: SourceFile, columns: list[str] | None = None) -> pd.DataFrame:
    frame = pd.read_sas(source.path, format="xport", encoding="utf-8")
    if columns is None:
        return frame
    return frame[[col for col in columns if col in frame.columns]]


def clean_yes_no(series: pd.Series) -> pd.Series:
    return series.where(series.isin([1, 2]))


def row_mean(df: pd.DataFrame, columns: list[str]) -> pd.Series:
    available = [col for col in columns if col in df.columns]
    if not available:
        return pd.Series(np.nan, index=df.index)
    return df[available].replace({0: np.nan}).mean(axis=1)


def classify_age(age: pd.Series) -> pd.Series:
    return pd.cut(
        age,
        bins=[19, 39, 59, 79, np.inf],
        labels=["20-39", "40-59", "60-79", "80+"],
        right=True,
    ).astype("object")


def classify_bmi(bmi: pd.Series) -> pd.Series:
    return pd.cut(
        bmi,
        bins=[0, 24.9, 29.9, 34.9, 39.9, np.inf],
        labels=[
            "Normal or underweight",
            "Overweight",
            "Obesity class I",
            "Obesity class II",
            "Obesity class III",
        ],
        right=True,
    ).astype("object")


def classify_a1c(a1c: pd.Series) -> pd.Series:
    return pd.cut(
        a1c,
        bins=[0, 5.6, 6.4, np.inf],
        labels=["Normoglycemia", "Prediabetes range", "Diabetes range"],
        right=True,
    ).astype("object")


def load_analytic_inputs() -> pd.DataFrame:
    download_sources()
    by_name = {source.name: source for source in SOURCES}

    demo = read_xpt(
        by_name["P_DEMO"],
        [
            "SEQN",
            "RIAGENDR",
            "RIDAGEYR",
            "RIDRETH3",
            "DMDEDUC2",
            "INDFMPIR",
            "RIDEXPRG",
            "WTMECPRP",
            "SDMVPSU",
            "SDMVSTRA",
        ],
    )
    bmx = read_xpt(by_name["P_BMX"], ["SEQN", "BMXWT", "BMXHT", "BMXBMI", "BMXWAIST"])
    bpxo = read_xpt(
        by_name["P_BPXO"],
        ["SEQN", "BPXOSY1", "BPXOSY2", "BPXOSY3", "BPXODI1", "BPXODI2", "BPXODI3"],
    )
    ghb = read_xpt(by_name["P_GHB"], ["SEQN", "LBXGH"])
    tchol = read_xpt(by_name["P_TCHOL"], ["SEQN", "LBXTC"])
    hdl = read_xpt(by_name["P_HDL"], ["SEQN", "LBDHDD"])
    trigly = read_xpt(by_name["P_TRIGLY"], ["SEQN", "LBXTR", "LBDLDL"])
    diq = read_xpt(by_name["P_DIQ"], ["SEQN", "DIQ010", "DIQ050", "DIQ070"])
    bpq = read_xpt(by_name["P_BPQ"], ["SEQN", "BPQ020", "BPQ040A", "BPQ080", "BPQ100D"])

    merged = demo
    for frame in [bmx, bpxo, ghb, tchol, hdl, trigly, diq, bpq]:
        merged = merged.merge(frame, on="SEQN", how="left")
    return merged


def build_analytic_cohort() -> pd.DataFrame:
    df = load_analytic_inputs()

    df = df[df["RIDAGEYR"] >= 20].copy()
    df = df[df["RIDEXPRG"].fillna(2) != 1].copy()
    df = df[df["BMXBMI"].notna()].copy()

    df["person_id"] = df["SEQN"].astype(int)
    df["age_years"] = df["RIDAGEYR"].astype(int)
    df["age_group"] = classify_age(df["age_years"])
    df["sex"] = df["RIAGENDR"].map(SEX_MAP)
    df["race_ethnicity"] = df["RIDRETH3"].map(RACE_MAP).fillna("Unknown")
    df["poverty_income_ratio"] = df["INDFMPIR"]
    df["mec_exam_weight"] = df["WTMECPRP"].fillna(0)

    df["bmi"] = df["BMXBMI"]
    df["bmi_category"] = classify_bmi(df["bmi"])
    df["waist_cm"] = df["BMXWAIST"]
    df["systolic_bp"] = row_mean(df, ["BPXOSY1", "BPXOSY2", "BPXOSY3"])
    df["diastolic_bp"] = row_mean(df, ["BPXODI1", "BPXODI2", "BPXODI3"])
    df["a1c_percent"] = df["LBXGH"]
    df["a1c_category"] = classify_a1c(df["a1c_percent"])
    df["total_cholesterol_mg_dl"] = df["LBXTC"]
    df["hdl_mg_dl"] = df["LBDHDD"]
    df["ldl_mg_dl"] = df["LBDLDL"]
    df["triglycerides_mg_dl"] = df["LBXTR"]

    df["diagnosed_diabetes"] = (clean_yes_no(df["DIQ010"]) == 1).astype(int)
    df["uses_insulin"] = (clean_yes_no(df["DIQ050"]) == 1).astype(int)
    df["uses_diabetes_pills"] = (clean_yes_no(df["DIQ070"]) == 1).astype(int)
    df["lab_diabetes_range"] = (df["a1c_percent"] >= 6.5).astype(int)
    df["diabetes_or_lab_range"] = ((df["diagnosed_diabetes"] == 1) | (df["lab_diabetes_range"] == 1)).astype(int)

    df["told_hypertension"] = (clean_yes_no(df["BPQ020"]) == 1).astype(int)
    df["taking_bp_medication"] = (clean_yes_no(df["BPQ040A"]) == 1).astype(int)
    df["measured_hypertension_range"] = ((df["systolic_bp"] >= 130) | (df["diastolic_bp"] >= 80)).astype(int)
    df["hypertension_or_treatment"] = (
        (df["told_hypertension"] == 1)
        | (df["taking_bp_medication"] == 1)
        | (df["measured_hypertension_range"] == 1)
    ).astype(int)

    df["told_high_cholesterol"] = (clean_yes_no(df["BPQ080"]) == 1).astype(int)
    df["taking_cholesterol_medication"] = (clean_yes_no(df["BPQ100D"]) == 1).astype(int)
    df["low_hdl"] = np.where(
        df["sex"].eq("Male"),
        df["hdl_mg_dl"] < 40,
        df["hdl_mg_dl"] < 50,
    ).astype(int)
    df["dyslipidemia_signal"] = (
        (df["total_cholesterol_mg_dl"] >= 240)
        | (df["ldl_mg_dl"] >= 160)
        | (df["triglycerides_mg_dl"] >= 200)
        | (df["low_hdl"] == 1)
        | (df["told_high_cholesterol"] == 1)
        | (df["taking_cholesterol_medication"] == 1)
    ).astype(int)

    df["central_adiposity_signal"] = np.where(
        df["sex"].eq("Male"),
        df["waist_cm"] >= 102,
        df["waist_cm"] >= 88,
    ).astype(int)

    risk_cols = [
        "diabetes_or_lab_range",
        "hypertension_or_treatment",
        "dyslipidemia_signal",
        "central_adiposity_signal",
    ]
    df["cardiometabolic_risk_count"] = df[risk_cols].sum(axis=1)
    df["metabolic_disease_signal"] = (
        (df["diabetes_or_lab_range"] == 1)
        | (df["hypertension_or_treatment"] == 1)
        | (df["dyslipidemia_signal"] == 1)
    ).astype(int)

    df["meets_bmi_35_recommended"] = (df["bmi"] >= 35).astype(int)
    df["bmi_30_349_with_metabolic_disease"] = (
        (df["bmi"] >= 30) & (df["bmi"] < 35) & (df["metabolic_disease_signal"] == 1)
    ).astype(int)
    df["guideline_like_eligible"] = (
        (df["meets_bmi_35_recommended"] == 1) | (df["bmi_30_349_with_metabolic_disease"] == 1)
    ).astype(int)
    df["eligibility_group"] = np.select(
        [
            df["meets_bmi_35_recommended"] == 1,
            df["bmi_30_349_with_metabolic_disease"] == 1,
        ],
        [
            "BMI >=35: guideline-recommended",
            "BMI 30-34.9 + metabolic disease: consider",
        ],
        default="Not guideline-like eligible",
    )
    df["risk_burden_group"] = pd.cut(
        df["cardiometabolic_risk_count"],
        bins=[-1, 0, 1, 2, 4],
        labels=["0 risk signals", "1 risk signal", "2 risk signals", "3-4 risk signals"],
    ).astype("object")

    columns = [
        "person_id",
        "age_years",
        "age_group",
        "sex",
        "race_ethnicity",
        "poverty_income_ratio",
        "mec_exam_weight",
        "bmi",
        "bmi_category",
        "waist_cm",
        "systolic_bp",
        "diastolic_bp",
        "a1c_percent",
        "a1c_category",
        "total_cholesterol_mg_dl",
        "hdl_mg_dl",
        "ldl_mg_dl",
        "triglycerides_mg_dl",
        "diagnosed_diabetes",
        "lab_diabetes_range",
        "diabetes_or_lab_range",
        "hypertension_or_treatment",
        "dyslipidemia_signal",
        "central_adiposity_signal",
        "cardiometabolic_risk_count",
        "risk_burden_group",
        "metabolic_disease_signal",
        "meets_bmi_35_recommended",
        "bmi_30_349_with_metabolic_disease",
        "guideline_like_eligible",
        "eligibility_group",
    ]
    return df[columns].sort_values("person_id").reset_index(drop=True)


def weighted_mean(values: pd.Series, weights: pd.Series) -> float:
    valid = values.notna() & weights.notna() & (weights > 0)
    if valid.sum() == 0:
        return float("nan")
    return float(np.average(values[valid], weights=weights[valid]))


def weighted_rate(flag: pd.Series, weights: pd.Series) -> float:
    return weighted_mean(flag.astype(float), weights)


def group_summary(df: pd.DataFrame, group_col: str) -> pd.DataFrame:
    rows = []
    for value, group in df.groupby(group_col, dropna=False):
        weights = group["mec_exam_weight"]
        rows.append(
            {
                group_col: value,
                "unweighted_n": len(group),
                "weighted_share": weighted_rate(pd.Series(1, index=group.index), weights)
                * weights.sum()
                / df["mec_exam_weight"].sum()
                if df["mec_exam_weight"].sum() > 0
                else np.nan,
                "guideline_like_eligible_rate": weighted_rate(group["guideline_like_eligible"], weights),
                "mean_bmi": weighted_mean(group["bmi"], weights),
                "diabetes_or_lab_range_rate": weighted_rate(group["diabetes_or_lab_range"], weights),
                "hypertension_or_treatment_rate": weighted_rate(group["hypertension_or_treatment"], weights),
                "dyslipidemia_signal_rate": weighted_rate(group["dyslipidemia_signal"], weights),
                "mean_risk_signal_count": weighted_mean(group["cardiometabolic_risk_count"], weights),
            }
        )
    return pd.DataFrame(rows)


def make_dashboard_kpis(df: pd.DataFrame) -> pd.DataFrame:
    weights = df["mec_exam_weight"]
    eligible = df[df["guideline_like_eligible"] == 1]
    return pd.DataFrame(
        [
            {"metric": "Analytic cohort adults", "value": len(df), "format": "count"},
            {
                "metric": "Weighted eligibility rate",
                "value": weighted_rate(df["guideline_like_eligible"], weights),
                "format": "percent",
            },
            {
                "metric": "BMI >=35 recommended rate",
                "value": weighted_rate(df["meets_bmi_35_recommended"], weights),
                "format": "percent",
            },
            {
                "metric": "BMI 30-34.9 + metabolic disease rate",
                "value": weighted_rate(df["bmi_30_349_with_metabolic_disease"], weights),
                "format": "percent",
            },
            {
                "metric": "Mean BMI among eligible adults",
                "value": weighted_mean(eligible["bmi"], eligible["mec_exam_weight"]) if not eligible.empty else np.nan,
                "format": "decimal",
            },
            {
                "metric": "Eligible adults with 2+ risk signals",
                "value": weighted_rate(
                    (eligible["cardiometabolic_risk_count"] >= 2).astype(int),
                    eligible["mec_exam_weight"],
                )
                if not eligible.empty
                else np.nan,
                "format": "percent",
            },
        ]
    )


def make_eligibility_summary(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for group_name, group in df.groupby("eligibility_group"):
        rows.append(
            {
                "eligibility_group": group_name,
                "unweighted_n": len(group),
                "weighted_share": group["mec_exam_weight"].sum() / df["mec_exam_weight"].sum(),
                "mean_bmi": weighted_mean(group["bmi"], group["mec_exam_weight"]),
                "diabetes_or_lab_range_rate": weighted_rate(group["diabetes_or_lab_range"], group["mec_exam_weight"]),
                "hypertension_or_treatment_rate": weighted_rate(
                    group["hypertension_or_treatment"], group["mec_exam_weight"]
                ),
                "dyslipidemia_signal_rate": weighted_rate(group["dyslipidemia_signal"], group["mec_exam_weight"]),
                "mean_risk_signal_count": weighted_mean(
                    group["cardiometabolic_risk_count"], group["mec_exam_weight"]
                ),
            }
        )
    return pd.DataFrame(rows).sort_values("weighted_share", ascending=False)


def make_risk_summary(df: pd.DataFrame) -> pd.DataFrame:
    risk_fields = [
        ("Diabetes or A1c diabetes range", "diabetes_or_lab_range"),
        ("Hypertension or treatment", "hypertension_or_treatment"),
        ("Dyslipidemia signal", "dyslipidemia_signal"),
        ("Central adiposity signal", "central_adiposity_signal"),
        ("Two or more risk signals", "cardiometabolic_risk_count"),
    ]
    rows = []
    for label, col in risk_fields:
        values = (df[col] >= 2).astype(int) if col == "cardiometabolic_risk_count" else df[col]
        rows.append(
            {
                "risk_signal": label,
                "overall_rate": weighted_rate(values, df["mec_exam_weight"]),
                "eligible_rate": weighted_rate(values[df["guideline_like_eligible"] == 1], df.loc[df["guideline_like_eligible"] == 1, "mec_exam_weight"]),
                "not_eligible_rate": weighted_rate(values[df["guideline_like_eligible"] == 0], df.loc[df["guideline_like_eligible"] == 0, "mec_exam_weight"]),
            }
        )
    return pd.DataFrame(rows)


def make_missingness_summary(df: pd.DataFrame) -> pd.DataFrame:
    columns = {
        "BMI": "bmi",
        "Waist circumference": "waist_cm",
        "Systolic BP": "systolic_bp",
        "Diastolic BP": "diastolic_bp",
        "A1c": "a1c_percent",
        "Total cholesterol": "total_cholesterol_mg_dl",
        "HDL cholesterol": "hdl_mg_dl",
        "LDL cholesterol": "ldl_mg_dl",
        "Triglycerides": "triglycerides_mg_dl",
    }
    rows = []
    for label, col in columns.items():
        rows.append(
            {
                "field": label,
                "non_missing_n": int(df[col].notna().sum()),
                "missing_n": int(df[col].isna().sum()),
                "missing_rate": float(df[col].isna().mean()),
            }
        )
    return pd.DataFrame(rows).sort_values("missing_rate", ascending=False)


def make_cohort_flow(df: pd.DataFrame) -> pd.DataFrame:
    raw = load_analytic_inputs()
    adults = raw[raw["RIDAGEYR"] >= 20]
    non_pregnant = adults[adults["RIDEXPRG"].fillna(2) != 1]
    with_bmi = non_pregnant[non_pregnant["BMXBMI"].notna()]
    return pd.DataFrame(
        [
            {"step": "NHANES 2017-March 2020 public-use participants", "records": len(raw)},
            {"step": "Adults age 20+", "records": len(adults)},
            {"step": "Pregnancy excluded for primary BMI cohort", "records": len(non_pregnant)},
            {"step": "BMI available", "records": len(with_bmi)},
            {"step": "Final analytic cohort", "records": len(df)},
        ]
    )


def write_outputs(df: pd.DataFrame) -> None:
    ensure_directories()
    df.to_csv(PROCESSED_DIR / "analytic_cohort.csv", index=False)
    make_dashboard_kpis(df).to_csv(PROCESSED_DIR / "dashboard_kpis.csv", index=False)
    make_eligibility_summary(df).to_csv(PROCESSED_DIR / "eligibility_summary.csv", index=False)
    make_risk_summary(df).to_csv(PROCESSED_DIR / "cardiometabolic_risk_summary.csv", index=False)
    group_summary(df, "age_group").to_csv(PROCESSED_DIR / "eligibility_by_age_group.csv", index=False)
    group_summary(df, "sex").to_csv(PROCESSED_DIR / "eligibility_by_sex.csv", index=False)
    group_summary(df, "race_ethnicity").to_csv(PROCESSED_DIR / "eligibility_by_race_ethnicity.csv", index=False)
    group_summary(df, "bmi_category").to_csv(PROCESSED_DIR / "eligibility_by_bmi_category.csv", index=False)
    make_missingness_summary(df).to_csv(PROCESSED_DIR / "missingness_summary.csv", index=False)
    make_cohort_flow(df).to_csv(PROCESSED_DIR / "cohort_flow.csv", index=False)
    create_analyst_brief(df)


def pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def create_analyst_brief(df: pd.DataFrame) -> None:
    kpis = make_dashboard_kpis(df).set_index("metric")["value"]
    risk_summary = make_risk_summary(df).set_index("risk_signal")
    text = f"""# Analyst Brief: Metabolic Surgery Eligibility and Cardiometabolic Risk

## Executive Summary

This project uses public-use NHANES 2017-March 2020 pre-pandemic data to phenotype
U.S. adults by guideline-like metabolic surgery eligibility and cardiometabolic risk
burden. The analytic cohort includes {len(df):,} adults with BMI available after
excluding pregnancy for the primary BMI-based cohort.

Using a guideline-like definition based on BMI >=35 kg/m2 or BMI 30-34.9 kg/m2
with a metabolic disease signal, the weighted eligibility rate is
{pct(kpis['Weighted eligibility rate'])}. The BMI >=35 recommended group accounts
for {pct(kpis['BMI >=35 recommended rate'])}, while BMI 30-34.9 with metabolic
disease accounts for {pct(kpis['BMI 30-34.9 + metabolic disease rate'])}.

Among guideline-like eligible adults, {pct(kpis['Eligible adults with 2+ risk signals'])}
have at least two cardiometabolic risk signals. Eligible adults have a weighted mean
BMI of {kpis['Mean BMI among eligible adults']:.1f} kg/m2.

## Selected Risk Signals

| Risk signal | Overall | Eligible | Not eligible |
| --- | ---: | ---: | ---: |
"""
    for signal, row in risk_summary.iterrows():
        text += (
            f"| {signal} | {pct(row['overall_rate'])} | "
            f"{pct(row['eligible_rate'])} | {pct(row['not_eligible_rate'])} |\n"
        )
    text += """
## Interpretation Boundary

The project is an analytic demonstration using public-use cross-sectional survey data.
It does not determine clinical candidacy for surgery, does not include operative
outcomes, and should not be interpreted as a causal analysis. Eligibility is framed
as guideline-like population phenotyping, not as patient-level medical advice.
"""
    (REPORTS_DIR / "ANALYST_BRIEF.md").write_text(text, encoding="utf-8")


def main() -> None:
    df = build_analytic_cohort()
    write_outputs(df)
    eligible = df["guideline_like_eligible"].sum()
    weighted_eligible_rate = weighted_rate(df["guideline_like_eligible"], df["mec_exam_weight"])
    print(
        "Built NHANES metabolic surgery project: "
        f"{len(df):,} adults, {eligible:,} unweighted guideline-like eligible, "
        f"{weighted_eligible_rate * 100:.1f}% weighted eligibility rate."
    )


if __name__ == "__main__":
    main()
