"""Produce design-aware estimates and an adjusted association model.

The analysis treats NHANES strata, primary sampling units, and MEC examination
weights as survey-design variables. Estimates are descriptive associations and
must not be interpreted as causal effects or individual clinical eligibility.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
REPORTS = ROOT / "reports"
Z_975 = 1.959963984540054


def design_variance(linearized: np.ndarray, strata: np.ndarray, psu: np.ndarray) -> float:
    """Taylor-linearized variance from centered PSU score totals."""
    frame = pd.DataFrame({"z": linearized, "stratum": strata, "psu": psu})
    totals = frame.groupby(["stratum", "psu"], observed=True)["z"].sum().reset_index()
    variance = 0.0
    for _, group in totals.groupby("stratum", observed=True):
        m = len(group)
        if m < 2:
            continue
        centered = group["z"].to_numpy() - group["z"].mean()
        variance += m / (m - 1) * float(centered @ centered)
    return variance


def survey_proportion(df: pd.DataFrame, outcome: str, domain: pd.Series | None = None) -> dict[str, float]:
    if domain is None:
        domain = pd.Series(True, index=df.index)
    domain = domain.fillna(False).astype(bool)
    valid = domain & df[outcome].notna() & df["mec_exam_weight"].gt(0)
    denominator = float(df.loc[valid, "mec_exam_weight"].sum())
    estimate = float(np.average(df.loc[valid, outcome], weights=df.loc[valid, "mec_exam_weight"]))

    linearized = np.zeros(len(df), dtype=float)
    linearized[valid.to_numpy()] = (
        df.loc[valid, "mec_exam_weight"].to_numpy()
        * (df.loc[valid, outcome].to_numpy() - estimate)
        / denominator
    )
    variance = design_variance(
        linearized,
        df["survey_stratum"].to_numpy(),
        df["survey_psu"].to_numpy(),
    )
    se = float(np.sqrt(max(variance, 0.0)))
    return {
        "unweighted_n": int(valid.sum()),
        "weighted_estimate": estimate,
        "standard_error": se,
        "ci_lower": max(0.0, estimate - Z_975 * se),
        "ci_upper": min(1.0, estimate + Z_975 * se),
    }


def make_prevalence_table(df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    definitions = [("Overall", "All adults", pd.Series(True, index=df.index))]
    for variable in ["age_group", "sex", "race_ethnicity"]:
        for level in df[variable].dropna().unique():
            definitions.append((variable, str(level), df[variable].eq(level)))

    for subgroup, level, domain in definitions:
        result = survey_proportion(df, "guideline_like_eligible", domain)
        rows.append({"subgroup": subgroup, "level": level, **result})
    return pd.DataFrame(rows)


def make_threshold_sensitivity(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    domains = [
        ("Overall", pd.Series(True, index=df.index)),
        ("Non-Hispanic Asian", df["race_ethnicity"].eq("Non-Hispanic Asian")),
    ]
    outcomes = [
        ("Common adult BMI thresholds", "guideline_like_eligible"),
        ("Asian-adjusted BMI threshold sensitivity", "guideline_like_eligible_asian_adjusted"),
    ]
    for population, domain in domains:
        for definition, outcome in outcomes:
            rows.append(
                {
                    "population": population,
                    "definition": definition,
                    **survey_proportion(df, outcome, domain),
                }
            )
    return pd.DataFrame(rows)


def design_matrix(df: pd.DataFrame) -> tuple[pd.DataFrame, list[dict[str, str]]]:
    columns: dict[str, pd.Series] = {"Intercept": pd.Series(1.0, index=df.index)}
    metadata: list[dict[str, str]] = []
    specifications = [
        ("age_group", "20-39", ["40-59", "60-79", "80+"]),
        ("sex", "Male", ["Female"]),
        (
            "race_ethnicity",
            "Non-Hispanic White",
            [
                "Mexican American",
                "Other Hispanic",
                "Non-Hispanic Black",
                "Non-Hispanic Asian",
                "Other / Multiracial",
            ],
        ),
    ]
    for variable, reference, levels in specifications:
        for level in levels:
            term = f"{variable}: {level}"
            columns[term] = df[variable].eq(level).astype(float)
            metadata.append({"term": term, "variable": variable, "level": level, "reference": reference})
    return pd.DataFrame(columns), metadata


def fit_survey_logistic(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    model_df = df.dropna(subset=["guideline_like_eligible", "age_group", "sex", "race_ethnicity"]).copy()
    x_frame, metadata = design_matrix(model_df)
    x = x_frame.to_numpy(dtype=float)
    y = model_df["guideline_like_eligible"].to_numpy(dtype=float)
    weights = model_df["mec_exam_weight"].to_numpy(dtype=float)
    weights = weights / weights.mean()

    beta = np.zeros(x.shape[1], dtype=float)
    for _ in range(100):
        eta = np.clip(x @ beta, -30, 30)
        probability = 1 / (1 + np.exp(-eta))
        working_weight = weights * np.clip(probability * (1 - probability), 1e-9, None)
        information = x.T @ (working_weight[:, None] * x)
        score = x.T @ (weights * (y - probability))
        step = np.linalg.solve(information, score)
        beta += step
        if np.max(np.abs(step)) < 1e-9:
            break
    else:
        raise RuntimeError("Survey-weighted logistic regression did not converge")

    probability = 1 / (1 + np.exp(-np.clip(x @ beta, -30, 30)))
    bread = x.T @ ((weights * probability * (1 - probability))[:, None] * x)
    score_rows = (weights * (y - probability))[:, None] * x
    score_frame = pd.DataFrame(score_rows)
    score_frame["stratum"] = model_df["survey_stratum"].to_numpy()
    score_frame["psu"] = model_df["survey_psu"].to_numpy()
    psu_scores = score_frame.groupby(["stratum", "psu"], observed=True).sum().reset_index()

    meat = np.zeros((x.shape[1], x.shape[1]), dtype=float)
    score_columns = list(range(x.shape[1]))
    for _, group in psu_scores.groupby("stratum", observed=True):
        values = group[score_columns].to_numpy(dtype=float)
        m = len(values)
        if m < 2:
            continue
        centered = values - values.mean(axis=0)
        meat += m / (m - 1) * centered.T @ centered
    bread_inverse = np.linalg.inv(bread)
    covariance = bread_inverse @ meat @ bread_inverse
    standard_errors = np.sqrt(np.clip(np.diag(covariance), 0, None))

    metadata_by_term = {row["term"]: row for row in metadata}
    rows = []
    for index, term in enumerate(x_frame.columns):
        if term == "Intercept":
            continue
        meta = metadata_by_term[term]
        rows.append(
            {
                **meta,
                "adjusted_odds_ratio": float(np.exp(beta[index])),
                "ci_lower": float(np.exp(beta[index] - Z_975 * standard_errors[index])),
                "ci_upper": float(np.exp(beta[index] + Z_975 * standard_errors[index])),
                "log_odds_coefficient": float(beta[index]),
                "standard_error": float(standard_errors[index]),
            }
        )

    diagnostics = pd.DataFrame(
        [
            {
                "analysis": "Primary adjusted demographic association model",
                "unweighted_n": len(model_df),
                "events": int(y.sum()),
                "survey_strata": int(model_df["survey_stratum"].nunique()),
                "survey_psus": int(model_df[["survey_stratum", "survey_psu"]].drop_duplicates().shape[0]),
                "converged": True,
            }
        ]
    )
    return pd.DataFrame(rows), diagnostics


def format_percent(value: float) -> str:
    return f"{100 * value:.1f}%"


def write_abstract(
    df: pd.DataFrame,
    prevalence: pd.DataFrame,
    model: pd.DataFrame,
    threshold_sensitivity: pd.DataFrame,
) -> None:
    overall = prevalence.query("subgroup == 'Overall'").iloc[0]
    race = prevalence[prevalence["subgroup"] == "race_ethnicity"].sort_values("weighted_estimate", ascending=False)
    highest = race.iloc[0]
    lowest = race.iloc[-1]
    age_40_59 = model[(model["variable"] == "age_group") & (model["level"] == "40-59")].iloc[0]
    age_60_79 = model[(model["variable"] == "age_group") & (model["level"] == "60-79")].iloc[0]
    asian = model[
        (model["variable"] == "race_ethnicity") & (model["level"] == "Non-Hispanic Asian")
    ].iloc[0]
    sensitivity = threshold_sensitivity.set_index(["population", "definition"])
    asian_adjusted_overall = sensitivity.loc[
        ("Overall", "Asian-adjusted BMI threshold sensitivity"), "weighted_estimate"
    ]
    asian_adjusted_asian = sensitivity.loc[
        ("Non-Hispanic Asian", "Asian-adjusted BMI threshold sensitivity"), "weighted_estimate"
    ]
    text = f"""# Draft Research Abstract

## Title

Demographic Variation in Guideline-Like Metabolic Surgery Eligibility Among U.S. Adults: A Survey-Weighted NHANES Analysis

## Background

Metabolic and bariatric surgery eligibility criteria have expanded, but the population-level distribution of potentially eligible adults is not fully characterized.

## Objective

To estimate guideline-like metabolic surgery eligibility among U.S. adults and describe adjusted demographic associations with eligibility.

## Methods

We conducted a cross-sectional analysis of public-use NHANES 2017-March 2020 pre-pandemic data. Adults aged 20 years or older with measured body mass index (BMI) were included; pregnant participants were excluded. The common-threshold phenotype was BMI >=35 kg/m2 or BMI 30.0-34.9 kg/m2 with a diabetes, hypertension, or dyslipidemia signal. Estimates incorporated MEC examination weights, strata, and primary sampling units. Survey-weighted prevalence estimates and 95% confidence intervals (CIs) were calculated. A survey-weighted multivariable logistic regression estimated demographic associations after mutual adjustment for age group, sex, and race/ethnicity. A sensitivity analysis classified non-Hispanic Asian adults with BMI >=27.5 kg/m2 as eligible in accordance with the guideline's ethnicity-specific threshold.

## Results

The analytic cohort included {len(df):,} adults. The survey-weighted prevalence of the common-threshold phenotype was {format_percent(overall['weighted_estimate'])} (95% CI, {format_percent(overall['ci_lower'])}-{format_percent(overall['ci_upper'])}). Prevalence ranged from {format_percent(lowest['weighted_estimate'])} among {lowest['level']} adults to {format_percent(highest['weighted_estimate'])} among {highest['level']} adults. Compared with adults aged 20-39 years, adjusted odds ratios were {age_40_59['adjusted_odds_ratio']:.2f} (95% CI, {age_40_59['ci_lower']:.2f}-{age_40_59['ci_upper']:.2f}) at ages 40-59 and {age_60_79['adjusted_odds_ratio']:.2f} (95% CI, {age_60_79['ci_lower']:.2f}-{age_60_79['ci_upper']:.2f}) at ages 60-79. Compared with non-Hispanic White adults, non-Hispanic Asian adults had lower adjusted odds under the common-threshold definition (adjusted odds ratio, {asian['adjusted_odds_ratio']:.2f}; 95% CI, {asian['ci_lower']:.2f}-{asian['ci_upper']:.2f}). Applying the Asian-specific BMI threshold increased estimated eligibility among non-Hispanic Asian adults to {format_percent(asian_adjusted_asian)} and overall eligibility to {format_percent(asian_adjusted_overall)}.

## Conclusion

More than one-third of U.S. adults met this population-level guideline-like phenotype, with meaningful demographic variation. These estimates describe potential eligibility burden and should not be interpreted as individual surgical candidacy or causal effects.

## Submission Status

Draft for methodological and clinical mentor review. Conference-specific word limits, authorship, institutional determination, and reporting requirements must be confirmed before submission.
"""
    (REPORTS / "ABSTRACT_DRAFT.md").write_text(text, encoding="utf-8")


def main() -> None:
    REPORTS.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(PROCESSED / "analytic_cohort.csv")
    required = {"survey_stratum", "survey_psu", "mec_exam_weight"}
    missing = required.difference(df.columns)
    if missing:
        raise RuntimeError(f"Rebuild analytic_cohort.csv first; missing columns: {sorted(missing)}")

    prevalence = make_prevalence_table(df)
    threshold_sensitivity = make_threshold_sensitivity(df)
    model, diagnostics = fit_survey_logistic(df)
    prevalence.to_csv(PROCESSED / "survey_weighted_prevalence.csv", index=False)
    model.to_csv(PROCESSED / "adjusted_associations.csv", index=False)
    diagnostics.to_csv(PROCESSED / "model_diagnostics.csv", index=False)
    threshold_sensitivity.to_csv(PROCESSED / "threshold_sensitivity.csv", index=False)
    write_abstract(df, prevalence, model, threshold_sensitivity)
    print("Wrote design-aware prevalence estimates, adjusted associations, and abstract draft.")


if __name__ == "__main__":
    main()
