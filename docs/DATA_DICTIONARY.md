# Data Dictionary

## `analytic_cohort.csv`

| Field | Description |
| --- | --- |
| `person_id` | NHANES public respondent sequence number |
| `age_years` | age in years |
| `age_group` | grouped age category |
| `sex` | male/female label |
| `race_ethnicity` | NHANES race/ethnicity category |
| `poverty_income_ratio` | family poverty-income ratio |
| `mec_exam_weight` | NHANES MEC exam weight |
| `bmi` | body mass index, kg/m2 |
| `bmi_category` | BMI category |
| `waist_cm` | waist circumference in cm |
| `systolic_bp` | mean available oscillometric systolic BP |
| `diastolic_bp` | mean available oscillometric diastolic BP |
| `a1c_percent` | glycated hemoglobin percent |
| `a1c_category` | normoglycemia, prediabetes range, or diabetes range |
| `total_cholesterol_mg_dl` | total cholesterol |
| `hdl_mg_dl` | HDL cholesterol |
| `ldl_mg_dl` | LDL cholesterol |
| `triglycerides_mg_dl` | triglycerides |
| `diagnosed_diabetes` | self-reported diabetes diagnosis flag |
| `lab_diabetes_range` | A1c >=6.5% flag |
| `diabetes_or_lab_range` | diagnosis or lab diabetes-range flag |
| `hypertension_or_treatment` | hypertension or treatment signal |
| `dyslipidemia_signal` | lipid risk or treatment signal |
| `central_adiposity_signal` | sex-specific waist circumference signal |
| `cardiometabolic_risk_count` | count of risk signals |
| `risk_burden_group` | grouped risk-signal count |
| `metabolic_disease_signal` | diabetes, hypertension, or dyslipidemia signal |
| `meets_bmi_35_recommended` | BMI >=35 kg/m2 flag |
| `bmi_30_349_with_metabolic_disease` | BMI 30-34.9 with metabolic disease signal |
| `guideline_like_eligible` | combined guideline-like eligibility flag |
| `eligibility_group` | eligibility phenotype group |

## Reporting Tables

| Table | Purpose |
| --- | --- |
| `dashboard_kpis.csv` | top-level dashboard values |
| `eligibility_summary.csv` | phenotype-level weighted rates and risk burden |
| `cardiometabolic_risk_summary.csv` | eligible vs non-eligible risk signal contrast |
| `eligibility_by_age_group.csv` | demographic subgroup reporting |
| `eligibility_by_sex.csv` | sex subgroup reporting |
| `eligibility_by_race_ethnicity.csv` | race/ethnicity subgroup reporting |
| `eligibility_by_bmi_category.csv` | BMI-category reporting |
| `missingness_summary.csv` | field-level missingness audit |
| `cohort_flow.csv` | inclusion/exclusion flow |
| `sql_validation_summary.csv` | independent SQL validation outputs |
