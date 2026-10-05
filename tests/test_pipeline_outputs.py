from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
ASSETS = ROOT / "assets"
POWERBI = ROOT / "powerbi"
PBIP_NAME = "NHANES_Metabolic_Surgery_Risk_Analytics"


class PipelineOutputTests(unittest.TestCase):
    def test_expected_outputs_exist(self) -> None:
        expected = [
            PROCESSED / "analytic_cohort.csv",
            PROCESSED / "dashboard_kpis.csv",
            PROCESSED / "eligibility_summary.csv",
            PROCESSED / "cardiometabolic_risk_summary.csv",
            PROCESSED / "eligibility_by_age_group.csv",
            PROCESSED / "eligibility_by_sex.csv",
            PROCESSED / "eligibility_by_race_ethnicity.csv",
            PROCESSED / "eligibility_by_bmi_category.csv",
            PROCESSED / "missingness_summary.csv",
            PROCESSED / "risk_domain_completeness.csv",
            PROCESSED / "eligibility_sensitivity.csv",
            PROCESSED / "survey_weighted_prevalence.csv",
            PROCESSED / "adjusted_associations.csv",
            PROCESSED / "model_diagnostics.csv",
            PROCESSED / "threshold_sensitivity.csv",
            PROCESSED / "cohort_flow.csv",
            PROCESSED / "sql_validation_summary.csv",
            ASSETS / "dashboard-preview.png",
            ASSETS / "powerbi-page-1-eligibility-overview.png",
            ASSETS / "powerbi-page-2-risk-profile.png",
            ASSETS / "powerbi-page-3-equity-audit.png",
            POWERBI / "theme-metabolic-surgery.json",
            POWERBI / "measures.dax",
            POWERBI / f"{PBIP_NAME}.pbip",
            POWERBI / f"{PBIP_NAME}.Report" / "definition" / "pages" / "pages.json",
            POWERBI / f"{PBIP_NAME}.SemanticModel" / "definition" / "model.tmdl",
            POWERBI / f"{PBIP_NAME}.SemanticModel" / "definition.pbism",
            ROOT / "docs" / "STATISTICAL_ANALYSIS_PLAN.md",
            ROOT / "reports" / "ABSTRACT_DRAFT.md",
        ]
        for path in expected:
            self.assertTrue(path.exists(), f"Missing expected output: {path}")

    def test_dashboard_kpis_are_consistent(self) -> None:
        kpis = pd.read_csv(PROCESSED / "dashboard_kpis.csv").set_index("metric")["value"]
        self.assertEqual(int(kpis["Analytic cohort adults"]), 8295)
        self.assertAlmostEqual(kpis["Weighted eligibility rate"], 0.3773943670834901, places=10)
        self.assertAlmostEqual(kpis["BMI >=35 recommended rate"], 0.20000432496298853, places=10)
        self.assertAlmostEqual(kpis["BMI 30-34.9 + metabolic disease rate"], 0.17739004212050155, places=10)
        self.assertAlmostEqual(kpis["Mean BMI among eligible adults"], 36.90840836390581, places=10)

    def test_eligibility_logic_is_mutually_consistent(self) -> None:
        cohort = pd.read_csv(PROCESSED / "analytic_cohort.csv")
        recomputed = (
            (cohort["meets_bmi_35_recommended"] == 1)
            | (cohort["bmi_30_349_with_metabolic_disease"] == 1)
        ).astype(int)
        self.assertTrue((cohort["guideline_like_eligible"] == recomputed).all())
        self.assertFalse(
            (
                (cohort["meets_bmi_35_recommended"] == 1)
                & (cohort["bmi_30_349_with_metabolic_disease"] == 1)
            ).any()
        )

    def test_sql_validation_matches_python_kpis(self) -> None:
        sql = pd.read_csv(PROCESSED / "sql_validation_summary.csv").set_index("check_name")["check_value"]
        kpis = pd.read_csv(PROCESSED / "dashboard_kpis.csv").set_index("metric")["value"]
        self.assertEqual(int(sql["analytic_cohort_n"]), int(kpis["Analytic cohort adults"]))
        self.assertAlmostEqual(sql["weighted_eligibility_rate"], kpis["Weighted eligibility rate"], places=10)
        self.assertAlmostEqual(sql["weighted_bmi_35_recommended_rate"], kpis["BMI >=35 recommended rate"], places=10)
        self.assertAlmostEqual(
            sql["weighted_bmi_30_349_metabolic_rate"],
            kpis["BMI 30-34.9 + metabolic disease rate"],
            places=10,
        )
        self.assertAlmostEqual(sql["weighted_mean_bmi_eligible"], kpis["Mean BMI among eligible adults"], places=10)

    def test_risk_burden_is_higher_in_eligible_group(self) -> None:
        summary = pd.read_csv(PROCESSED / "cardiometabolic_risk_summary.csv")
        two_plus = summary[summary["risk_signal"] == "Two or more risk signals"].iloc[0]
        self.assertGreater(two_plus["eligible_rate"], two_plus["not_eligible_rate"])
        self.assertGreater(two_plus["eligible_rate"], 0.85)

    def test_missing_risk_domains_are_explicitly_audited(self) -> None:
        completeness = pd.read_csv(PROCESSED / "risk_domain_completeness.csv").set_index("assessment")
        self.assertEqual(int(completeness.loc["Complete four-domain risk profile", "missing_n"]), 337)
        self.assertGreater(
            int(completeness.loc["Central adiposity", "missing_n"]),
            int(completeness.loc["Diabetes", "missing_n"]),
        )

        sensitivity = pd.read_csv(PROCESSED / "eligibility_sensitivity.csv").set_index("analysis_population")
        primary = sensitivity.loc["Primary analytic cohort", "weighted_eligibility_rate"]
        complete = sensitivity.loc[
            "Complete metabolic-disease ascertainment", "weighted_eligibility_rate"
        ]
        self.assertLess(abs((complete - primary) * 100), 0.2)

    def test_theme_json_is_valid(self) -> None:
        with (POWERBI / "theme-metabolic-surgery.json").open("r", encoding="utf-8") as handle:
            parsed = json.load(handle)
        self.assertEqual(parsed["name"], "Metabolic Surgery Clinical Research")

    def test_powerbi_project_has_expected_tables_and_pages(self) -> None:
        with (POWERBI / f"{PBIP_NAME}.pbip").open("r", encoding="utf-8") as handle:
            pbip = json.load(handle)
        self.assertEqual(pbip["artifacts"][0]["report"]["path"], f"{PBIP_NAME}.Report")

        pbism_path = POWERBI / f"{PBIP_NAME}.SemanticModel" / "definition.pbism"
        with pbism_path.open("r", encoding="utf-8") as handle:
            pbism = json.load(handle)
        self.assertGreaterEqual(float(pbism["version"]), 4.0)

        model_text = (POWERBI / f"{PBIP_NAME}.SemanticModel" / "definition" / "model.tmdl").read_text(
            encoding="utf-8"
        )
        for table in [
            "analytic_cohort",
            "dashboard_kpis",
            "eligibility_summary",
            "cardiometabolic_risk_summary",
            "missingness_summary",
            "sql_validation_summary",
        ]:
            self.assertIn(f"ref table {table}", model_text)

        cohort_table = (
            POWERBI / f"{PBIP_NAME}.SemanticModel" / "definition" / "tables" / "analytic_cohort.tmdl"
        ).read_text(encoding="utf-8")
        self.assertIn("Source = #table(type table [", cohort_table)

        pages_path = POWERBI / f"{PBIP_NAME}.Report" / "definition" / "pages" / "pages.json"
        with pages_path.open("r", encoding="utf-8") as handle:
            pages = json.load(handle)
        self.assertEqual(
            pages["pageOrder"],
            ["eligibilityOverview", "riskProfile", "equityAudit"],
        )

    def test_powerbi_regeneration_requires_explicit_force(self) -> None:
        result = subprocess.run(
            [sys.executable, str(ROOT / "pipeline" / "create_powerbi_project.py")],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Refusing to replace the completed Power BI project", result.stderr)

    def test_no_restricted_data_claims(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8").lower()
        self.assertIn("public-use", readme)
        self.assertIn("no phi", readme)
        self.assertIn("no mimic-iv", readme)

    def test_research_outputs_are_design_aware_and_plausible(self) -> None:
        cohort = pd.read_csv(PROCESSED / "analytic_cohort.csv")
        self.assertTrue({"survey_stratum", "survey_psu", "mec_exam_weight"}.issubset(cohort.columns))

        prevalence = pd.read_csv(PROCESSED / "survey_weighted_prevalence.csv")
        overall = prevalence[prevalence["subgroup"] == "Overall"].iloc[0]
        self.assertEqual(int(overall["unweighted_n"]), 8295)
        self.assertAlmostEqual(overall["weighted_estimate"], 0.3773943670834901, places=10)
        self.assertLess(overall["ci_lower"], overall["weighted_estimate"])
        self.assertGreater(overall["ci_upper"], overall["weighted_estimate"])

        associations = pd.read_csv(PROCESSED / "adjusted_associations.csv")
        self.assertEqual(len(associations), 9)
        self.assertTrue((associations["adjusted_odds_ratio"] > 0).all())
        self.assertTrue((associations["ci_lower"] < associations["adjusted_odds_ratio"]).all())
        self.assertTrue((associations["ci_upper"] > associations["adjusted_odds_ratio"]).all())

        sensitivity = pd.read_csv(PROCESSED / "threshold_sensitivity.csv").set_index(
            ["population", "definition"]
        )
        common_asian = sensitivity.loc[
            ("Non-Hispanic Asian", "Common adult BMI thresholds"), "weighted_estimate"
        ]
        adjusted_asian = sensitivity.loc[
            ("Non-Hispanic Asian", "Asian-adjusted BMI threshold sensitivity"), "weighted_estimate"
        ]
        self.assertGreater(adjusted_asian, common_asian)


if __name__ == "__main__":
    unittest.main()
