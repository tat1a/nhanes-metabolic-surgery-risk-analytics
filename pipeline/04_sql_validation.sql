with cohort as (
    select
        person_id,
        mec_exam_weight,
        guideline_like_eligible,
        meets_bmi_35_recommended,
        bmi_30_349_with_metabolic_disease,
        cardiometabolic_risk_count,
        bmi
    from analytic_cohort
),
totals as (
    select
        count(*) as analytic_cohort_n,
        sum(guideline_like_eligible) as unweighted_eligible_n,
        sum(meets_bmi_35_recommended) as unweighted_bmi_35_recommended_n,
        sum(bmi_30_349_with_metabolic_disease) as unweighted_bmi_30_349_metabolic_n,
        sum(case when guideline_like_eligible = 1 and cardiometabolic_risk_count >= 2 then 1 else 0 end) as eligible_with_2plus_risk_n
    from cohort
),
weighted as (
    select
        sum(mec_exam_weight * guideline_like_eligible) / sum(mec_exam_weight) as weighted_eligibility_rate,
        sum(mec_exam_weight * meets_bmi_35_recommended) / sum(mec_exam_weight) as weighted_bmi_35_recommended_rate,
        sum(mec_exam_weight * bmi_30_349_with_metabolic_disease) / sum(mec_exam_weight) as weighted_bmi_30_349_metabolic_rate,
        sum(case when guideline_like_eligible = 1 then mec_exam_weight * bmi end)
            / nullif(sum(case when guideline_like_eligible = 1 then mec_exam_weight end), 0) as weighted_mean_bmi_eligible
    from cohort
)
select 'analytic_cohort_n' as check_name, analytic_cohort_n as check_value from totals
union all
select 'unweighted_eligible_n', unweighted_eligible_n from totals
union all
select 'unweighted_bmi_35_recommended_n', unweighted_bmi_35_recommended_n from totals
union all
select 'unweighted_bmi_30_349_metabolic_n', unweighted_bmi_30_349_metabolic_n from totals
union all
select 'eligible_with_2plus_risk_n', eligible_with_2plus_risk_n from totals
union all
select 'weighted_eligibility_rate', weighted_eligibility_rate from weighted
union all
select 'weighted_bmi_35_recommended_rate', weighted_bmi_35_recommended_rate from weighted
union all
select 'weighted_bmi_30_349_metabolic_rate', weighted_bmi_30_349_metabolic_rate from weighted
union all
select 'weighted_mean_bmi_eligible', weighted_mean_bmi_eligible from weighted;
