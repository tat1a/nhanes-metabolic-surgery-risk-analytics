"""Create a starter Power BI Project (.pbip) with loaded NHANES tables.

The generated project contains a semantic model with embedded processed tables,
grouped DAX measures, and three blank report pages ready for manual visual design.
"""

from __future__ import annotations

import csv
import json
import math
import re
import shutil
import uuid
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = ROOT / "data" / "processed"
POWERBI_DIR = ROOT / "powerbi"

PROJECT_NAME = "NHANES_Metabolic_Surgery_Risk_Analytics"
PBIP_PATH = POWERBI_DIR / f"{PROJECT_NAME}.pbip"
REPORT_DIR = POWERBI_DIR / f"{PROJECT_NAME}.Report"
MODEL_DIR = POWERBI_DIR / f"{PROJECT_NAME}.SemanticModel"

TABLE_ORDER = [
    "analytic_cohort",
    "dashboard_kpis",
    "eligibility_summary",
    "cardiometabolic_risk_summary",
    "eligibility_by_age_group",
    "eligibility_by_sex",
    "eligibility_by_race_ethnicity",
    "eligibility_by_bmi_category",
    "missingness_summary",
    "cohort_flow",
    "sql_validation_summary",
]

DISPLAY_FOLDERS = {
    "Analytic Cohort Adults": "01 Eligibility KPIs",
    "Weighted Population": "01 Eligibility KPIs",
    "Weighted Eligible Population": "01 Eligibility KPIs",
    "Weighted Eligibility Rate": "01 Eligibility KPIs",
    "Weighted BMI >=35 Rate": "01 Eligibility KPIs",
    "Weighted BMI 30-34.9 + Metabolic Disease Rate": "01 Eligibility KPIs",
    "Weighted Mean BMI": "01 Eligibility KPIs",
    "Eligible Weighted Mean BMI": "01 Eligibility KPIs",
    "Weighted Diabetes Signal Rate": "02 Risk Signals",
    "Weighted Hypertension Signal Rate": "02 Risk Signals",
    "Weighted Dyslipidemia Signal Rate": "02 Risk Signals",
    "Weighted Central Adiposity Signal Rate": "02 Risk Signals",
    "Eligible Adults With 2+ Risk Signals": "02 Risk Signals",
    "Eligible Diabetes Signal Rate": "02 Risk Signals",
    "Eligible Hypertension Signal Rate": "02 Risk Signals",
    "Eligible Dyslipidemia Signal Rate": "02 Risk Signals",
    "Eligible Central Adiposity Signal Rate": "02 Risk Signals",
}

MEASURE_FORMATS = {
    "Analytic Cohort Adults": "#,0",
    "Weighted Population": "#,0.0",
    "Weighted Eligible Population": "#,0.0",
    "Weighted Eligibility Rate": "0.0%;-0.0%;0.0%",
    "Weighted BMI >=35 Rate": "0.0%;-0.0%;0.0%",
    "Weighted BMI 30-34.9 + Metabolic Disease Rate": "0.0%;-0.0%;0.0%",
    "Weighted Mean BMI": "0.0",
    "Eligible Weighted Mean BMI": "0.0",
    "Weighted Diabetes Signal Rate": "0.0%;-0.0%;0.0%",
    "Weighted Hypertension Signal Rate": "0.0%;-0.0%;0.0%",
    "Weighted Dyslipidemia Signal Rate": "0.0%;-0.0%;0.0%",
    "Weighted Central Adiposity Signal Rate": "0.0%;-0.0%;0.0%",
    "Eligible Adults With 2+ Risk Signals": "0.0%;-0.0%;0.0%",
    "Eligible Diabetes Signal Rate": "0.0%;-0.0%;0.0%",
    "Eligible Hypertension Signal Rate": "0.0%;-0.0%;0.0%",
    "Eligible Dyslipidemia Signal Rate": "0.0%;-0.0%;0.0%",
    "Eligible Central Adiposity Signal Rate": "0.0%;-0.0%;0.0%",
}

COLUMN_FORMATS = {
    "mec_exam_weight": "#,0.0",
    "bmi": "0.0",
    "waist_cm": "0.0",
    "systolic_bp": "0.0",
    "diastolic_bp": "0.0",
    "a1c_percent": "0.0",
    "total_cholesterol_mg_dl": "0.0",
    "hdl_mg_dl": "0.0",
    "ldl_mg_dl": "0.0",
    "triglycerides_mg_dl": "0.0",
    "weighted_share": "0.0%;-0.0%;0.0%",
    "guideline_like_eligible_rate": "0.0%;-0.0%;0.0%",
    "diabetes_or_lab_range_rate": "0.0%;-0.0%;0.0%",
    "hypertension_or_treatment_rate": "0.0%;-0.0%;0.0%",
    "dyslipidemia_signal_rate": "0.0%;-0.0%;0.0%",
    "overall_rate": "0.0%;-0.0%;0.0%",
    "eligible_rate": "0.0%;-0.0%;0.0%",
    "not_eligible_rate": "0.0%;-0.0%;0.0%",
    "missing_rate": "0.0%;-0.0%;0.0%",
    "mean_bmi": "0.0",
    "mean_risk_signal_count": "0.0",
    "value": "0.0",
}


def clean_existing_project() -> None:
    for path in [REPORT_DIR, MODEL_DIR, PBIP_PATH]:
        if path.is_dir():
            shutil.rmtree(path)
        elif path.exists():
            path.unlink()


def infer_power_type(series: pd.Series) -> tuple[str, str]:
    if pd.api.types.is_integer_dtype(series):
        return "int64", "Int64.Type"
    if pd.api.types.is_float_dtype(series):
        return "double", "number"
    return "string", "text"


def m_identifier(name: str) -> str:
    return name


def tmdl_string(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def m_text(value: object) -> str:
    if pd.isna(value):
        return "null"
    text = str(value).replace('"', '""')
    return f'"{text}"'


def m_value(value: object, power_type: str) -> str:
    if pd.isna(value):
        return "null"
    if power_type in {"Int64.Type", "number"}:
        number = float(value)
        if math.isnan(number):
            return "null"
        if power_type == "Int64.Type":
            return str(int(number))
        return f"{number:.12g}"
    return m_text(value)


def make_table_literal(frame: pd.DataFrame) -> tuple[str, dict[str, str]]:
    power_types: dict[str, str] = {}
    type_parts = []
    for col in frame.columns:
        _, m_type = infer_power_type(frame[col])
        power_types[col] = m_type
        type_parts.append(f"{m_identifier(col)} = {m_type}")
    rows = []
    for row in frame.itertuples(index=False, name=None):
        values = [m_value(value, power_types[col]) for value, col in zip(row, frame.columns)]
        rows.append("{" + ", ".join(values) + "}")
    source = "#table(type table [" + ", ".join(type_parts) + "], {" + ", ".join(rows) + "})"
    return source, power_types


def parse_measures() -> list[tuple[str, str]]:
    text = (POWERBI_DIR / "measures.dax").read_text(encoding="utf-8")
    measures: list[tuple[str, str]] = []
    current_name: str | None = None
    current_lines: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if not line or line.strip().startswith("--"):
            continue
        if not line.startswith(" ") and not line.startswith("\t") and line.endswith("="):
            if current_name is not None:
                measures.append((current_name, "\n".join(current_lines).strip()))
            current_name = line[:-1].strip()
            current_lines = []
        elif current_name is not None:
            current_lines.append(line)
    if current_name is not None:
        measures.append((current_name, "\n".join(current_lines).strip()))
    return measures


def dax_inline(expression: str) -> str:
    return re.sub(r"\s+", " ", expression).strip()


def write_table_tmdl(table_name: str, frame: pd.DataFrame, table_dir: Path) -> None:
    source, _ = make_table_literal(frame)
    lines = [f"table {table_name}", f"\tlineageTag: {uuid.uuid4()}"]
    if table_name == "analytic_cohort":
        for measure_name, expression in parse_measures():
            lines.append("")
            lines.append(f"\tmeasure {tmdl_string(measure_name)} = {dax_inline(expression)}")
            lines.append(f"\t\tformatString: {MEASURE_FORMATS.get(measure_name, '0.0')}")
            folder = DISPLAY_FOLDERS.get(measure_name)
            if folder:
                lines.append(f"\t\tdisplayFolder: {folder}")
            lines.append(f"\t\tlineageTag: {uuid.uuid4()}")
    for col in frame.columns:
        data_type, _ = infer_power_type(frame[col])
        lines.append("")
        lines.append(f"\tcolumn {col}")
        lines.append(f"\t\tdataType: {data_type}")
        if col in COLUMN_FORMATS:
            lines.append(f"\t\tformatString: {COLUMN_FORMATS[col]}")
        lines.append(f"\t\tlineageTag: {uuid.uuid4()}")
        summarize_by = "sum" if data_type in {"int64", "double"} and col not in {"person_id"} else "none"
        if col.endswith("_rate") or col.endswith("_share") or col in {"value", "bmi"}:
            summarize_by = "none"
        lines.append(f"\t\tsummarizeBy: {summarize_by}")
        lines.append(f"\t\tsourceColumn: {col}")
    lines.append("")
    lines.append(f"\tpartition {table_name} = m")
    lines.append("\t\tmode: import")
    lines.append("\t\tsource =")
    lines.append("\t\t\t\tlet")
    lines.append(f"\t\t\t\t    Source = {source}")
    lines.append("\t\t\t\tin")
    lines.append("\t\t\t\t    Source")
    lines.append("")
    (table_dir / f"{table_name}.tmdl").write_text("\n".join(lines), encoding="utf-8")


def write_semantic_model() -> None:
    definition = MODEL_DIR / "definition"
    table_dir = definition / "tables"
    table_dir.mkdir(parents=True, exist_ok=True)
    (MODEL_DIR / ".pbi").mkdir(parents=True, exist_ok=True)

    (MODEL_DIR / ".platform").write_text(
        json.dumps(
            {
                "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
                "metadata": {"type": "SemanticModel", "displayName": PROJECT_NAME},
                "config": {"version": "2.0", "logicalId": str(uuid.uuid4())},
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (MODEL_DIR / "definition.pbism").write_text('{"version":"1.0"}\n', encoding="utf-8")
    (MODEL_DIR / "diagramLayout.json").write_text("{}\n", encoding="utf-8")
    (definition / "database.tmdl").write_text("database\n\tcompatibilityLevel: 1606\n", encoding="utf-8")

    refs = []
    for table in TABLE_ORDER:
        csv_path = PROCESSED_DIR / f"{table}.csv"
        frame = pd.read_csv(csv_path)
        write_table_tmdl(table, frame, table_dir)
        refs.append(f"ref table {table}")
    model_text = [
        "model Model",
        "\tculture: en-US",
        "\tdefaultPowerBIDataSourceVersion: powerBI_V3",
        "\tsourceQueryCulture: en-US",
        "\tdataAccessOptions",
        "\t\tlegacyRedirects",
        "\t\treturnErrorValuesAsNull",
        "",
        "annotation PBI_QueryOrder = " + json.dumps(TABLE_ORDER),
        "",
        'annotation PBI_ProTooling = ["DevMode"]',
        "",
        "annotation __PBI_TimeIntelligenceEnabled = 1",
        "",
        *refs,
        "",
    ]
    (definition / "model.tmdl").write_text("\n".join(model_text), encoding="utf-8")


def page_json(name: str, display_name: str) -> dict:
    return {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.1.0/schema.json",
        "name": name,
        "displayName": display_name,
        "displayOption": "FitToPage",
        "height": 1080,
        "width": 1920,
        "objects": {
            "background": [
                {
                    "properties": {
                        "color": {
                            "solid": {
                                "color": {"expr": {"Literal": {"Value": "'#F6F7FB'"}}}
                            }
                        }
                    }
                }
            ]
        },
    }


def write_report() -> None:
    definition = REPORT_DIR / "definition"
    pages_dir = definition / "pages"
    static_resources = REPORT_DIR / "StaticResources" / "RegisteredResources"
    pages_dir.mkdir(parents=True, exist_ok=True)
    static_resources.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / ".pbi").mkdir(parents=True, exist_ok=True)

    theme_name = "Metabolic_Surgery_Clinical_Research.json"
    shutil.copyfile(POWERBI_DIR / "theme-metabolic-surgery.json", static_resources / theme_name)

    (REPORT_DIR / ".platform").write_text(
        json.dumps(
            {
                "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
                "metadata": {"type": "Report", "displayName": PROJECT_NAME},
                "config": {"version": "2.0", "logicalId": str(uuid.uuid4())},
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (REPORT_DIR / "definition.pbir").write_text(
        json.dumps({"version": "4.0", "datasetReference": {"byPath": {"path": f"../{PROJECT_NAME}.SemanticModel"}}}, indent=2),
        encoding="utf-8",
    )
    (definition / "version.json").write_text(
        json.dumps(
            {
                "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/versionMetadata/1.0.0/schema.json",
                "version": "2.0.0",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    page_specs = [
        ("eligibilityOverview", "Eligibility Overview"),
        ("riskProfile", "Risk Profile"),
        ("equityAudit", "Equity Lens"),
    ]
    (pages_dir / "pages.json").write_text(
        json.dumps(
            {
                "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.1.0/schema.json",
                "pageOrder": [name for name, _ in page_specs],
                "activePageName": page_specs[0][0],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    for name, display_name in page_specs:
        page_dir = pages_dir / name
        page_dir.mkdir(parents=True, exist_ok=True)
        (page_dir / "page.json").write_text(json.dumps(page_json(name, display_name), indent=2), encoding="utf-8")

    report_json = {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/report/3.3.0/schema.json",
        "themeCollection": {
            "baseTheme": {
                "name": "Fluent2-CY26SU08",
                "reportVersionAtImport": {"visual": "2.12.0", "report": "3.4.0", "page": "2.3.1"},
                "type": "SharedResources",
            },
            "customTheme": {
                "name": theme_name,
                "reportVersionAtImport": {"visual": "2.12.0", "report": "3.4.0", "page": "2.3.1"},
                "type": "RegisteredResources",
            },
        },
        "resourcePackages": [
            {
                "name": "SharedResources",
                "type": "SharedResources",
                "items": [{"name": "Fluent2-CY26SU08", "path": "BaseThemes/Fluent2-CY26SU08.json", "type": "BaseTheme"}],
            },
            {
                "name": "RegisteredResources",
                "type": "RegisteredResources",
                "items": [{"name": theme_name, "path": theme_name, "type": "CustomTheme"}],
            },
        ],
        "settings": {
            "useStylableVisualContainerHeader": True,
            "exportDataMode": "AllowSummarized",
            "defaultDrillFilterOtherVisuals": True,
            "allowChangeFilterTypes": True,
            "useEnhancedTooltips": True,
            "useDefaultAggregateDisplayName": True,
        },
    }
    (definition / "report.json").write_text(json.dumps(report_json, indent=2), encoding="utf-8")


def write_pbip() -> None:
    POWERBI_DIR.mkdir(parents=True, exist_ok=True)
    PBIP_PATH.write_text(
        json.dumps(
            {
                "version": "1.0",
                "artifacts": [{"report": {"path": f"{PROJECT_NAME}.Report"}}],
                "settings": {"enableAutoRecovery": True},
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def main() -> None:
    clean_existing_project()
    write_semantic_model()
    write_report()
    write_pbip()
    print(f"Created starter Power BI project: {PBIP_PATH}")


if __name__ == "__main__":
    main()
