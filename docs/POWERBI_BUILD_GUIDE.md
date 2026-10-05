# Power BI Build Guide

Open `powerbi/NHANES_Metabolic_Surgery_Risk_Analytics.pbip` in Power BI Desktop. The project defines all 11 tables and the measures, but a PBIP file does not carry imported rows until the model is refreshed in Desktop.

## First Open: Load and Verify Data

1. In Power BI Desktop, open the `.pbip` file above.
2. Select **Home > Refresh**. Wait for every query to finish. The source rows are embedded in the project, so no CSV path or login is required.
3. Select **Table view** on the left and choose `analytic_cohort`. The status bar should show **8,295 rows**. Confirm that `dashboard_kpis` has **6 rows**.
4. Select **File > Save as** and save `NHANES_Metabolic_Surgery_Risk_Analytics.pbix` in `powerbi/`. Reopen that `.pbix` and confirm the same row counts before building visuals.

If Power BI reports a missing `model.bim`, the `SemanticModel/definition.pbism` file is outdated. It must specify version `4.2` for this TMDL project. If the tables appear but show no rows, use **Home > Refresh**; opening a PBIP file alone does not import its data.

## Report Style

Use a clinical research style that differs from the previous surgical registry reports:

- dark navy top header, not a left navigation rail;
- light blue-gray canvas;
- white rounded panels;
- accent colors: blue, teal, rose, amber, violet;
- compact typography with Aptos or Segoe UI;
- explicit footnotes for weighting and interpretation limits.

Apply theme:

`powerbi/theme-metabolic-surgery.json`

## Included Tables

The project already defines these tables; do not import duplicate CSV copies:

- `analytic_cohort.csv`
- `dashboard_kpis.csv`
- `eligibility_summary.csv`
- `cardiometabolic_risk_summary.csv`
- `eligibility_by_age_group.csv`
- `eligibility_by_sex.csv`
- `eligibility_by_race_ethnicity.csv`
- `eligibility_by_bmi_category.csv`
- `missingness_summary.csv`
- `cohort_flow.csv`
- `sql_validation_summary.csv`

## Measures

The measures are already under `analytic_cohort`, organized in `01 Eligibility KPIs` and `02 Risk Signals` display folders. `powerbi/measures.dax` is the reviewable source for their formulas. Do not create same-named measures again.

Recommended formatting:

| Measure | Format |
| --- | --- |
| `Analytic Cohort Adults` | whole number, thousands separator |
| `Weighted Eligibility Rate` | percentage, 1 decimal |
| `Weighted BMI >=35 Rate` | percentage, 1 decimal |
| `Weighted BMI 30-34.9 + Metabolic Disease Rate` | percentage, 1 decimal |
| `Weighted Mean BMI` | decimal, 1 decimal |
| `Eligible Weighted Mean BMI` | decimal, 1 decimal |
| risk-signal rates | percentage, 1 decimal |
| eligible risk-signal rates | percentage, 1 decimal |

## Page 1: Eligibility Overview

Reference: `assets/powerbi-page-1-eligibility-overview.png`

Title: `Metabolic Surgery Eligibility Analytics`

Subtitle: `NHANES 2017-March 2020 adult cohort phenotype view`

KPI cards:

| Card title | Field |
| --- | --- |
| Analytic cohort | `analytic_cohort[Analytic Cohort Adults]` |
| Weighted eligible | `analytic_cohort[Weighted Eligibility Rate]` |
| BMI >=35 | `analytic_cohort[Weighted BMI >=35 Rate]` |
| BMI 30-34.9 + metabolic disease | `analytic_cohort[Weighted BMI 30-34.9 + Metabolic Disease Rate]` |

Main visuals:

| Visual | Type | Axis / Category | Value |
| --- | --- | --- | --- |
| Eligibility phenotype | clustered bar chart | `eligibility_summary[eligibility_group]` | `eligibility_summary[weighted_share]` |
| Eligibility rate by BMI category | clustered column chart | `eligibility_by_bmi_category[bmi_category]` | `eligibility_by_bmi_category[guideline_like_eligible_rate]` |

Footer:

`Interpretation: eligibility is guideline-like population phenotyping, not individual clinical candidacy.`

## Page 2: Cardiometabolic Risk Profile

Reference: `assets/powerbi-page-2-risk-profile.png`

Title: `Cardiometabolic Risk Profile`

Subtitle: `Risk clustering among guideline-like eligible and non-eligible adults`

KPI cards:

| Card title | Field |
| --- | --- |
| Eligible mean BMI | `analytic_cohort[Eligible Weighted Mean BMI]` |
| Eligible diabetes signal | `analytic_cohort[Eligible Diabetes Signal Rate]` |
| Eligible hypertension signal | `analytic_cohort[Eligible Hypertension Signal Rate]` |
| Eligible 2+ risk signals | `analytic_cohort[Eligible Adults With 2+ Risk Signals]` |

Main visuals:

| Visual | Type | Axis / Category | Value |
| --- | --- | --- | --- |
| Risk signal prevalence | clustered bar chart | `cardiometabolic_risk_summary[risk_signal]` | `cardiometabolic_risk_summary[eligible_rate]` |
| Eligible vs non-eligible contrast | table | `risk_signal` | `eligible_rate`, `not_eligible_rate` |

## Page 3: Equity Lens and Cohort Audit

Reference: `assets/powerbi-page-3-equity-audit.png`

Title: `Equity Lens and Cohort Audit`

Subtitle: `Demographic variation, denominator checks, and missingness review`

Main visuals:

| Visual | Type | Axis / Category | Value |
| --- | --- | --- | --- |
| Eligibility by age group | clustered column chart | `eligibility_by_age_group[age_group]` | `guideline_like_eligible_rate` |
| Eligibility by race/ethnicity | clustered bar chart | `eligibility_by_race_ethnicity[race_ethnicity]` | `guideline_like_eligible_rate` |
| Missingness audit | table | `missingness_summary[field]` | `missing_n`, `missing_rate` |
| Dashboard note | text box | interpretation and weighting caveats | not applicable |

## Slicers

Use slicers from `analytic_cohort`:

- `age_group`
- `sex`
- `race_ethnicity`
- `bmi_category`
- `eligibility_group`
- `risk_burden_group`

Use dropdown style for compactness. Keep slicers at the top or right side, but do not let them dominate the page.

## Common Fixes

| Problem | Fix |
| --- | --- |
| Percent values show as decimals | Format as percentage with 1 decimal |
| Counts show as `8K` | Display units = None |
| Long labels are cut off | Increase visual width or reduce axis text to 9-10 pt |
| `Count of weighted_share` appears | Change aggregation to Sum or use the measure/value field directly |
| The report looks like prior projects | Keep the top navy header, tab-like page labels, and rose/teal/amber palette |
