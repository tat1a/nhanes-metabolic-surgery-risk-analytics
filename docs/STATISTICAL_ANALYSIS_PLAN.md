# Statistical Analysis Plan

## Study question

Among U.S. adults represented in NHANES 2017-March 2020, what proportion meets a
guideline-like metabolic surgery eligibility phenotype, and how does eligibility
vary across demographic groups after adjustment?

## Design and population

- Cross-sectional secondary analysis of public-use NHANES data.
- Adults age 20 years or older with measured BMI.
- Pregnant participants excluded from the primary BMI-based cohort.
- No protected health information and no patient-level clinical recommendations.

## Outcome

The binary primary outcome is a common-threshold guideline-like phenotype, defined as either BMI
>=35 kg/m2 or BMI 30.0-34.9 kg/m2 with at least one diabetes, hypertension, or
dyslipidemia signal. This definition is retained as the primary analysis for
cross-group comparability and continuity with the dashboard. It is a population
phenotype, not adjudicated candidacy.

## Primary descriptive analysis

Estimate overall and subgroup prevalence with 95% confidence intervals using MEC
examination weights, masked variance strata, and masked primary sampling units.
Subgroups are age group, sex, and race/ethnicity. Subgroup estimates use domain
analysis so that the full survey design remains represented in variance estimates.

## Adjusted association model

Fit a survey-weighted logistic regression with age group, sex, and race/ethnicity
entered simultaneously. Report adjusted odds ratios and 95% confidence intervals.
Reference groups are age 20-39 years, male sex, and non-Hispanic White
race/ethnicity. BMI and metabolic disease signals are excluded as predictors
because they define the outcome.

The model is descriptive and associational. It does not estimate causal effects.

## Missing data and sensitivity analysis

The primary phenotype uses an any-positive composite rule. Existing completeness
outputs quantify risk-domain ascertainment, and eligibility is repeated among
participants with complete metabolic-disease ascertainment. Demographic model
variables are complete in the analytic cohort; no imputation is planned.

An ethnicity-threshold sensitivity analysis applies the 2022 ASMBS/IFSO
recommendation that Asian adults with BMI >=27.5 kg/m2 should be offered MBS.
Both the overall estimate and the non-Hispanic Asian subgroup estimate are reported
under the common-threshold and Asian-adjusted definitions. Because race/ethnicity
then becomes part of the sensitivity outcome definition, no race-adjusted regression
is fitted for that alternate outcome.

## Reporting

- Provide unweighted sample sizes alongside weighted estimates.
- Report weighted prevalence to one decimal place and odds ratios to two decimals.
- Avoid unweighted percentages as population estimates.
- Interpret subgroup differences descriptively; no causal or clinical-candidacy claims.
- Treat the abstract as a draft until mentor review and conference requirements are confirmed.

## Primary methodological sources

- CDC/NCHS. *NHANES 2017-March 2020 Prepandemic File: Sample Design,
  Estimation, and Analytic Guidelines.*
  https://wwwn.cdc.gov/nchs/nhanes/continuousnhanes/overviewBrief.aspx?Cycle=2017-2020
- Eisenberg D, et al. *2022 ASMBS and IFSO Indications for Metabolic and
  Bariatric Surgery.* Surgery for Obesity and Related Diseases. 2022.
  https://asmbs.org/resources/2022-asmbs-and-ifso-indications-for-metabolic-and-bariatric-surgery/
