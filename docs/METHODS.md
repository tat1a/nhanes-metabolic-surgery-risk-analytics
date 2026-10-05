# Methods

## Analytic Design

This project is a cross-sectional clinical analytics study using public-use NHANES 2017-March 2020 pre-pandemic data.

Clinical threshold source: 2022 ASMBS/IFSO indications for metabolic and bariatric surgery: https://asmbs.org/resources/2022-asmbs-and-ifso-indications-for-metabolic-and-bariatric-surgery/

## Cohort Construction

The analytic cohort includes adults age 20+ with BMI available. Pregnant participants are excluded from the primary BMI-based cohort because pregnancy affects anthropometric interpretation.

## Phenotype Definitions

### Diabetes Signal

`diabetes_or_lab_range = 1` if either:

- participant reported being told they had diabetes; or
- A1c was >=6.5%.

### Hypertension Signal

`hypertension_or_treatment = 1` if any of:

- participant reported being told they had high blood pressure;
- participant reported taking antihypertensive medication;
- mean measured systolic BP >=130 mmHg;
- mean measured diastolic BP >=80 mmHg.

### Dyslipidemia Signal

`dyslipidemia_signal = 1` if any of:

- total cholesterol >=240 mg/dL;
- LDL cholesterol >=160 mg/dL;
- triglycerides >=200 mg/dL;
- low HDL using sex-specific thresholds;
- participant reported high cholesterol;
- participant reported cholesterol medication use.

### Central Adiposity Signal

`central_adiposity_signal = 1` if waist circumference is:

- >=102 cm for men;
- >=88 cm for women.

### Missing-data and composite-rule handling

Risk domains use an any-positive rule: a domain is positive when any available
questionnaire, examination, or laboratory component is positive. A zero means no
positive evidence was observed; it does not assert that every component was
measured. The pipeline therefore exports `risk_domain_completeness.csv` and a
complete metabolic-disease ascertainment sensitivity estimate in
`eligibility_sensitivity.csv`.

## Eligibility Logic

Guideline-like eligibility is defined as either:

- BMI >=35 kg/m2; or
- BMI 30-34.9 kg/m2 with a metabolic disease signal.

This operationalizes the eligibility concept for population-level analytics only. It is not medical advice and does not determine individual surgical candidacy.

## Weighting

Descriptive rates use NHANES MEC exam weights (`WTMECPRP`) from the 2017-March 2020 pre-pandemic release.

## Outputs

The pipeline produces:

- individual-level analytic cohort table;
- KPI table;
- eligibility and risk summaries;
- demographic subgroup summaries;
- missingness audit;
- risk-domain completeness and eligibility sensitivity audits;
- SQL validation summary;
- analyst brief;
- Power BI reference previews.
