# Data Source and Validation

## Source

The project uses public-use NHANES 2017-March 2020 pre-pandemic files from CDC/NCHS.

Primary source links:

- CDC/NCHS NHANES: https://www.cdc.gov/nchs/nhanes/
- NHANES 2017-March 2020 pre-pandemic data files: https://wwwn.cdc.gov/nchs/nhanes/search/datapage.aspx?Cycle=2017-2020
- NHANES 2017-March 2020 analytic guidance: https://www.cdc.gov/nchs/data/series/sr_02/sr02-190.pdf

NHANES combines interviews, physical examinations, and laboratory testing. The 2017-March 2020 pre-pandemic release combines the full 2017-2018 cycle with partial 2019-March 2020 data using special sample weights to support national estimates.

## Files Used

| NHANES file | Domain | Use |
| --- | --- | --- |
| `P_DEMO` | Demographics and sample weights | age, sex, race/ethnicity, pregnancy flag, MEC exam weight |
| `P_BMX` | Body measures | BMI, height, weight, waist circumference |
| `P_BPXO` | Blood pressure exam | systolic and diastolic BP measurements |
| `P_GHB` | Glycohemoglobin | A1c |
| `P_TCHOL` | Total cholesterol | total cholesterol |
| `P_HDL` | HDL cholesterol | HDL |
| `P_TRIGLY` | Triglycerides and LDL | triglycerides, LDL |
| `P_DIQ` | Diabetes questionnaire | diabetes diagnosis and medication flags |
| `P_BPQ` | Blood pressure and cholesterol questionnaire | hypertension/cholesterol awareness and treatment |

## Cohort

Primary analytic cohort:

1. NHANES public-use participants.
2. Adults age 20+.
3. Pregnancy excluded for the primary BMI-based cohort.
4. BMI available.

Final analytic cohort: 8,295 adults.

## Validation Checks

The pipeline exports `sql_validation_summary.csv`, which independently recalculates:

- analytic cohort count;
- unweighted guideline-like eligibility count;
- BMI >=35 eligibility count;
- BMI 30-34.9 plus metabolic disease count;
- weighted eligibility rate;
- weighted BMI-threshold rates;
- weighted mean BMI among eligible adults.
- minimum ascertainment completeness for each composite risk domain;
- weighted eligibility in the primary and complete-ascertainment populations.

Automated tests verify:

- required processed outputs exist;
- key KPI values match expected ranges and SQL validation;
- eligibility groups are mutually consistent;
- raw XPT files are not required in Git;
- no patient identifiers beyond NHANES public respondent sequence numbers are introduced.

## Limitations

- NHANES is cross-sectional; do not infer causality.
- This project does not include operative outcomes, long-term weight loss, complications, or mortality.
- Eligibility is guideline-like population phenotyping, not patient-level surgical clearance.
- Some laboratory components have meaningful missingness, especially fasting lipid measures.
- Composite risk indicators use any-positive evidence; a zero may include partially observed source components. Separate completeness and sensitivity outputs quantify this limitation.
- Survey weighting is used for descriptive estimates; this project does not implement full complex-survey variance estimation.
